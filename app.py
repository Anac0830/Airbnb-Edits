from flask import Flask, request, send_file, jsonify
import fitz
import io
import os
import re

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# ... [MANTENER EL MISMO BLOQUE HTML QUE TENÍAS ANTERIORMENTE] ...

@app.route('/')
def index():
    return HTML

@app.route('/scan', methods=['POST'])
def scan_pdf():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    pdf_bytes = request.files['pdf'].read()
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        money_values = []
        money_pattern = re.compile(r'\$[\d,]+\.?\d*')
        for page in doc:
            for val in money_pattern.findall(page.get_text()):
                if val not in money_values:
                    money_values.append(val)
        return jsonify({'money_values': money_values, 'pages': len(doc)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process', methods=['POST'])
def process_pdf():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    pdf_file = request.files['pdf']
    finds   = request.form.getlist('find[]')
    replaces = request.form.getlist('replace[]')
    bolds   = request.form.getlist('bold[]')

    if not finds or all(f.strip() == '' for f in finds):
        return jsonify({'error': 'No replacements specified'}), 400
    
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        total = 0
        
        for i, (old_text, new_text) in enumerate(zip(finds, replaces)):
            old_text = old_text.strip()
            new_text = new_text.strip()
            if not old_text: continue
            
            for page in doc:
                instances = page.search_for(old_text)
                
                # Obtener propiedades de estilo original
                font_size = 12.0
                text_color = (0, 0, 0)
                font_name_original = 'helv'
                
                for block in page.get_text('dict').get('blocks', []):
                    if block.get('type') != 0: continue
                    for line in block.get('lines', []):
                        for span in line.get('spans', []):
                            if old_text in span.get('text', ''):
                                font_size = span.get('size', 12.0)
                                c = span.get('color', 0)
                                text_color = (((c>>16)&0xFF)/255.0, ((c>>8)&0xFF)/255.0, (c&0xFF)/255.0)
                                # Detección inteligente de negrita
                                if 'Bold' in span.get('font', ''):
                                    font_name_original = 'hebo'
                
                # Aplicar edición
                for inst in instances:
                    # Sobrescribir con blanco
                    page.draw_rect(fitz.Rect(inst.x0-1, inst.y0-2, inst.x1+5, inst.y1+2), color=(1,1,1), fill=(1,1,1))
                    
                    # Usar negrita forzada si el usuario lo pidió en el UI, si no, mantener original
                    font_to_use = 'hebo' if (bolds[i] == '1') else font_name_original
                    
                    page.insert_text(
                        (inst.x0, inst.y0 + (inst.y1-inst.y0)*0.8),
                        new_text, fontname=font_to_use, fontsize=font_size, color=text_color
                    )
                    total += 1
                    
        if total == 0:
            return jsonify({'error': 'Text not found in PDF. Copy the exact text including $ sign.'}), 404
            
        output = io.BytesIO()
        doc.save(output, deflate=True, garbage=4)
        output.seek(0)
        name = pdf_file.filename.rsplit('.', 1)[0] + '_edited.pdf'
        return send_file(output, mimetype='application/pdf', as_attachment=True, download_name=name)
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
