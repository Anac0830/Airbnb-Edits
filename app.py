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
    <style>
        :root { --pink: #FF385C; --pink-dark: #e0314f; --pink-light: #fff0f2; --gray-50: #f9fafb; --gray-900: #111827; }
        body { font-family: sans-serif; background: var(--gray-50); padding: 20px; }
        .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 600px; margin: 0 auto; }
        .row-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
        .field-input { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
        .btn-process { width: 100%; padding: 12px; background: var(--pink); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
    </style>
</head>
<body>
    <main class="card">
        <h3>PDF Value Editor</h3>
        <input type="file" id="pdfFile" accept=".pdf" />
        <div id="replacementsList" style="margin: 20px 0;">
            <div class="row-fields"><input type="text" class="field-input" name="find[]" placeholder="Find">
            <input type="text" class="field-input" name="replace[]" placeholder="Replace"></div>
        </div>
        <button class="btn-process" onclick="processPDF()">Edit & Download</button>
    </main>
    <script>
        async function processPDF() {
            const file = document.getElementById('pdfFile').files[0];
            const fd = new FormData();
            fd.append('pdf', file);
            document.querySelectorAll('input[name="find[]"]').forEach(i => fd.append('find[]', i.value));
            document.querySelectorAll('input[name="replace[]"]').forEach(i => fd.append('replace[]', i.value));
            const res = await fetch('/process', { method: 'POST', body: fd });
            if(res.ok) {
                const b = await res.blob();
                const a = document.createElement('a');
                a.href = URL.createObjectURL(b);
                a.download = 'edited.pdf';
                a.click();
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index(): return HTML

@app.route('/process', methods=['POST'])
def process_pdf():
    if 'pdf' not in request.files: return "No file", 400
    pdf_file = request.files['pdf']
    finds = request.form.getlist('find[]')
    replaces = request.form.getlist('replace[]')
    
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    
    for old_text, new_text in zip(finds, replaces):
        if not old_text.strip(): continue
        for page in doc:
            instances = page.search_for(old_text)
            for inst in instances:
                # 1. Obtener tamaño original
                blocks = page.get_text("dict", clip=inst)["blocks"]
                font_size = 10
                if blocks and "lines" in blocks[0]:
                    spans = blocks[0]["lines"][0].get("spans", [])
                    if spans: font_size = spans[0].get("size", 10)
                
                # 2. Redactar original
                page.add_redact_annot(inst)
                page.apply_redactions()
                
                # 3. Insertar texto en negrita forzada
                # render_mode=2 aplica trazo (bold) a la fuente base 'helv'
                page.insert_text(inst.tl, new_text, 
                                 fontsize=font_size, 
                                 fontname="helv", 
                                 color=(0, 0, 0), 
                                 render_mode=2)
    
    output = io.BytesIO()
    doc.save(output, deflate=True)
    output.seek(0)
    return send_file(output, mimetype='application/pdf', as_attachment=True, download_name="edited.pdf")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
