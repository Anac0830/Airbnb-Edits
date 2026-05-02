from flask import Flask, request, send_file, jsonify
import fitz
import io
import os
import re

app = Flask(__name__)
# Aumentamos el límite para permitir PDFs más grandes
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

HTML = """
<!DOCTYPE html>
<html>
<body>
    <h1>PDF Value Editor</h1>
    <form action="/process" method="post" enctype="multipart/form-data">
        <input type="file" name="pdf" accept=".pdf" required><br><br>
        <input type="text" name="find[]" placeholder="Texto a encontrar (ej. $436.02)" required><br>
        <input type="text" name="replace[]" placeholder="Nuevo valor (ej. $923.79)" required><br>
        <label><input type="checkbox" name="bold[]" value="1" checked> ¿Usar negrita?</label><br><br>
        <button type="submit">Procesar y Descargar</button>
    </form>
</body>
</html>
"""

@app.route('/')
def index():
    return HTML

@app.route('/process', methods=['POST'])
def process_pdf():
    if 'pdf' not in request.files:
        return "No se subió archivo", 400
    
    pdf_file = request.files['pdf']
    finds = request.form.getlist('find[]')
    replaces = request.form.getlist('replace[]')
    bolds = request.form.getlist('bold[]')

    try:
        # Abrimos el PDF directamente desde el stream
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        
        for i, (old_text, new_text) in enumerate(zip(finds, replaces)):
            old_text = old_text.strip()
            if not old_text: continue
            
            # Si el checkbox está marcado, 'bolds' tendrá el valor '1'
            is_bold = (i < len(bolds) and bolds[i] == '1')
            font_name = 'hebo' if is_bold else 'helv'

            for page in doc:
                # Buscamos el texto exacto
                text_instances = page.search_for(old_text)
                for inst in text_instances:
                    # 1. Dibujamos un rectángulo blanco para borrar lo anterior
                    # Añadimos un poco de margen al rectángulo (inst)
                    page.draw_rect(inst, color=(1, 1, 1), fill=(1, 1, 1))
                    
                    # 2. Insertamos el nuevo texto justo encima
                    # Usamos una fuente estándar de PyMuPDF
                    page.insert_text(
                        (inst.x0, inst.y1 - 1), 
                        new_text, 
                        fontname=font_name, 
                        fontsize=11, 
                        color=(0, 0, 0)
                    )
        
        # Guardamos el resultado en memoria
        output = io.BytesIO()
        doc.save(output, garbage=4, deflate=True)
        output.seek(0)
        
        return send_file(
            output, 
            mimetype='application/pdf', 
            as_attachment=True, 
            download_name='archivo_editado.pdf'
        )
    except Exception as e:
        return f"Error en el servidor: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
