from flask import Flask, request, send_file, jsonify
import fitz
import io
import os
import re

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>PDF Value Editor</title>
    <!-- (El HTML completo se mantiene igual, no lo copio aquí para ahorrar espacio) -->
    <!-- ... todo el HTML anterior sin cambios ... -->
</head>
<body>
    <!-- ... todo el HTML anterior sin cambios ... -->
</body>
</html>
"""

# === HTML se mantiene exactamente igual (lo omito aquí por brevedad) ===
# Copia el HTML completo de la versión anterior

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
    finds = request.form.getlist('find[]')
    replaces = request.form.getlist('replace[]')
   
    if not finds or all(f.strip() == '' for f in finds):
        return jsonify({'error': 'No replacements specified'}), 400
   
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        total = 0
       
        for old_text, new_text in zip(finds, replaces):
            old_text = old_text.strip()
            new_text = new_text.strip()
            if not old_text:
                continue
           
            for page in doc:
                instances = page.search_for(old_text)
                for inst in instances:
                    # Configuración segura por defecto
                    font_name = "helv"      # Helvetica normal
                    font_size = 11.0
                    text_color = (0, 0, 0)
                    is_bold = False

                    # Detectar formato original
                    text_dict = page.get_text("dict")
                    for block in text_dict.get('blocks', []):
                        if block.get('type') != 0:
                            continue
                        for line in block.get('lines', []):
                            for span in line.get('spans', []):
                                span_text = span.get('text', '')
                                if old_text in span_text or span_text.strip() == old_text.strip():
                                    font_size = span.get('size', 11.0)
                                    color_int = span.get('color', 0)
                                    text_color = (
                                        ((color_int >> 16) & 0xFF) / 255.0,
                                        ((color_int >> 8) & 0xFF) / 255.0,
                                        (color_int & 0xFF) / 255.0
                                    )
                                    
                                    # Detección mejorada de negrita
                                    fontname = span.get('font', '').lower()
                                    flags = span.get('flags', 0)
                                    
                                    if (any(x in fontname for x in ['bold', 'black', 'heavy', 'semibold', '700', '600']) or 
                                        (flags & 4)):   # Flag de bold
                                        is_bold = True
                                    
                                    break
                            if is_bold: break
                        if is_bold: break
                    
                    # Usar solo fuentes seguras de PyMuPDF
                    font_name = "hebo" if is_bold else "helv"

                    # Espacio extra
                    extra = max(0, len(new_text) - len(old_text)) * font_size * 0.65
                    
                    # Cubrir texto original
                    page.draw_rect(
                        fitz.Rect(inst.x0-1, inst.y0-2, inst.x1 + extra + 8, inst.y1+3),
                        color=(1,1,1), 
                        fill=(1,1,1)
                    )
                    
                    # Insertar nuevo texto
                    page.insert_text(
                        fitz.Point(inst.x0, inst.y0 + (inst.y1 - inst.y0) * 0.78),
                        new_text,
                        fontname=font_name,
                        fontsize=font_size,
                        color=text_color,
                        render_mode=0
                    )
                    total += 1
       
        if total == 0:
            return jsonify({'error': 'Text not found in PDF. Copy the exact text including $ sign.'}), 404
       
        output = io.BytesIO()
        doc.save(output, deflate=True, garbage=4, clean=True)
        output.seek(0)
        
        name = pdf_file.filename.rsplit('.', 1)[0] + '_edited.pdf'
        return send_file(output, mimetype='application/pdf', as_attachment=True, download_name=name)
    
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
