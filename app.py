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
        :root { --pink: #FF385C; --pink-dark: #e0314f; --pink-light: #fff0f2; --gray-50: #f9fafb; --gray-100: #f3f4f6; --gray-200: #e5e7eb; --gray-300: #d1d5db; --gray-400: #9ca3af; --gray-600: #4b5563; --gray-700: #374151; --gray-900: #111827; --green: #10b981; --green-light: #ecfdf5; --red: #ef4444; --red-light: #fef2f2; --shadow-sm: 0 1px 2px rgba(0,0,0,0.05); --shadow: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -1px rgba(0,0,0,0.04); --radius: 12px; }
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--gray-50); color: var(--gray-900); min-height: 100vh; }
        nav { background: white; border-bottom: 1px solid var(--gray-200); padding: 0 24px; height: 64px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; box-shadow: var(--shadow-sm); }
        .nav-brand { display: flex; align-items: center; gap: 10px; text-decoration: none; }
        .nav-logo { width: 36px; height: 36px; background: var(--pink); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-size: 18px; }
        .nav-title { font-size: 16px; font-weight: 700; color: var(--gray-900); }
        .nav-subtitle { font-size: 12px; color: var(--gray-400); }
        .nav-badge { background: var(--pink-light); color: var(--pink); font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 20px; }
        main { max-width: 860px; margin: 0 auto; padding: 40px 24px 80px; }
        .hero { text-align: center; margin-bottom: 40px; }
        .hero h1 { font-size: 32px; font-weight: 800; color: var(--gray-900); line-height: 1.2; margin-bottom: 10px; }
        .hero h1 span { color: var(--pink); }
        .hero p { font-size: 16px; color: var(--gray-600); max-width: 520px; margin: 0 auto; line-height: 1.6; }
        .card { background: white; border-radius: var(--radius); border: 1px solid var(--gray-200); box-shadow: var(--shadow); overflow: hidden; margin-bottom: 20px; }
        .card-header { padding: 20px 24px 16px; border-bottom: 1px solid var(--gray-100); display: flex; align-items: center; gap: 10px; }
        .card-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; }
        .card-icon.pink { background: var(--pink-light); }
        .card-icon.blue { background: #eff6ff; }
        .card-icon.green { background: var(--green-light); }
        .card-title { font-size: 15px; font-weight: 700; color: var(--gray-900); }
        .card-desc { font-size: 13px; color: var(--gray-400); margin-top: 2px; }
        .card-body { padding: 24px; }
        .upload-zone { border: 2px dashed var(--gray-300); border-radius: 10px; padding: 40px 24px; text-align: center; cursor: pointer; transition: all 0.2s; position: relative; }
        .upload-zone:hover, .upload-zone.drag-over { border-color: var(--pink); background: var(--pink-light); }
        .upload-zone input[type="file"] { position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; }
        .upload-icon { width: 52px; height: 52px; background: var(--gray-100); border-radius: 12px; display: flex; align-items: center; justify-content: center; margin: 0 auto 14px; font-size: 24px; transition: background 0.2s; }
        .upload-zone:hover .upload-icon, .upload-zone.drag-over .upload-icon { background: white; }
        .upload-zone h3 { font-size: 15px; font-weight: 600; color: var(--gray-700); margin-bottom: 6px; }
        .upload-zone p { font-size: 13px; color: var(--gray-400); }
        .upload-zone .browse { color: var(--pink); font-weight: 600; }
        .file-selected { display: none; align-items: center; gap: 14px; padding: 16px 20px; background: var(--green-light); border: 1.5px solid #a7f3d0; border-radius: 10px; }
        .file-selected.show { display: flex; }
        .file-selected-icon { width: 40px; height: 40px; background: var(--green); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-size: 18px; flex-shrink: 0; }
        .file-selected-name { font-size: 14px; font-weight: 600; color: #065f46; }
        .file-selected-size { font-size: 12px; color: #6ee7b7; }
        .file-change { margin-left: auto; background: none; border: 1.5px solid #6ee7b7; color: #065f46; border-radius: 6px; padding: 6px 12px; font-size: 12px; cursor: pointer; font-weight: 500; transition: all 0.2s; }
        .file-change:hover { background: white; }
        .btn-scan { display: block; width: 100%; margin-top: 14px; padding: 11px; background: var(--gray-100); color: var(--gray-700); border: 1px solid var(--gray-200); border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s; text-align: center; }
        .btn-scan:hover { background: var(--gray-200); }
        .btn-scan.hidden { display: none; }
        .scan-results { display: none; margin-top: 14px; }
        .scan-results.show { display: block; }
        .scan-label { font-size: 12px; font-weight: 600; color: var(--gray-400); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
        .money-chips { display: flex; flex-wrap: wrap; gap: 8px; }
        .money-chip { background: var(--pink-light); color: var(--pink-dark); border: 1.5px solid #fecdd3; border-radius: 20px; padding: 5px 12px; font-size: 13px; font-weight: 700; cursor: pointer; transition: all 0.2s; font-family: 'Menlo', 'Monaco', monospace; }
        .money-chip:hover { background: var(--pink); color: white; border-color: var(--pink); transform: translateY(-1px); }
        .replacements-list { display: flex; flex-direction: column; gap: 10px; }
        .row-wrap { display: flex; align-items: center; gap: 8px; }
        .row-fields { display: grid; grid-template-columns: 1fr auto 1fr; gap: 8px; flex: 1; align-items: center; }
        .arrow-icon { color: var(--gray-400); font-size: 16px; text-align: center; }
        .field-group { display: flex; flex-direction: column; gap: 4px; }
        .field-label { font-size: 11px; font-weight: 600; color: var(--gray-400); text-transform: uppercase; letter-spacing: 0.05em; }
        .field-input { width: 100%; padding: 10px 12px; border: 1.5px solid var(--gray-200); border-radius: 8px; font-size: 14px; font-family: 'Menlo', 'Monaco', monospace; font-weight: 500; color: var(--gray-900); transition: border-color 0.2s; background: white; }
        .field-input:focus { outline: none; border-color: var(--pink); box-shadow: 0 0 0 3px rgba(255, 56, 92, 0.1); }
        .btn-remove { width: 32px; height: 32px; background: var(--gray-100); border: 1px solid var(--gray-200); border-radius: 6px; color: var(--gray-400); cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: all 0.2s; }
        .btn-remove:hover { background: var(--red-light); color: var(--red); border-color: #fecaca; }
        .btn-add-row { background: none; border: 1.5px dashed var(--gray-300); border-radius: 8px; color: var(--gray-400); font-size: 13px; font-weight: 600; padding: 10px; cursor: pointer; width: 100%; margin-top: 4px; transition: all 0.2s; }
        .btn-add-row:hover { border-color: var(--pink); color: var(--pink); background: var(--pink-light); }
        .btn-process { display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%; padding: 15px; background: var(--pink); color: white; border: none; border-radius: 10px; font-size: 15px; font-weight: 700; cursor: pointer; transition: all 0.2s; box-shadow: 0 4px 14px rgba(255, 56, 92, 0.35); }
        .btn-process:hover { background: var(--pink-dark); transform: translateY(-1px); box-shadow: 0 6px 20px rgba(255, 56, 92, 0.4); }
        .btn-process:disabled { background: var(--gray-300); box-shadow: none; cursor: not-allowed; }
        .status-box { display: none; padding: 14px 18px; border-radius: 10px; font-size: 14px; font-weight: 500; align-items: center; gap: 10px; margin-top: 14px; }
        .status-box.show { display: flex; }
        .status-box.success { background: var(--green-light); color: #065f46; border: 1px solid #a7f3d0; }
        .status-box.error { background: var(--red-light); color: #991b1b; border: 1px solid #fecaca; }
        .spinner-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 999; align-items: center; justify-content: center; }
        .spinner-overlay.show { display: flex; }
        .spinner-box { background: white; border-radius: 14px; padding: 32px 40px; text-align: center; box-shadow: var(--shadow-lg); }
        .big-spin { width: 48px; height: 48px; border: 4px solid var(--gray-200); border-top-color: var(--pink); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 16px; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <nav><a class="nav-brand" href="/"><div class="nav-logo">📄</div><div><div class="nav-title">PDF Value Editor</div><div class="nav-subtitle">Airbnb & more</div></div></a></nav>
    <main>
        <div class="card">
            <div class="card-header"><div class="card-icon pink">📤</div><div><div class="card-title">Step 1 — Upload your PDF</div></div></div>
            <div class="card-body">
                <div class="upload-zone" id="uploadZone"><input type="file" id="pdfFile" accept=".pdf" /><h3>Drop your PDF here or browse</h3></div>
                <button class="btn-scan hidden" id="btnScan" onclick="scanPDF()">🔍 Auto-detect money values</button>
                <div class="scan-results" id="scanResults"><div class="money-chips" id="moneyChips"></div></div>
            </div>
        </div>
        <div class="card">
            <div class="card-header"><div class="card-icon blue">🔄</div><div><div class="card-title">Step 2 — Set replacements</div></div></div>
            <div class="card-body"><div class="replacements-list" id="replacementsList"></div><button class="btn-add-row" onclick="addRow()">+ Add another replacement</button></div>
        </div>
        <div class="card"><div class="card-body"><button class="btn-process" id="btnProcess" onclick="processPDF()">Edit & Download</button><div class="status-box" id="statusBox"></div></div></div>
    </main>
    <div class="spinner-overlay" id="spinnerOverlay"><div class="spinner-box"><div class="big-spin"></div><p>Editing your PDF…</p></div></div>
    <script>
        let selectedFile = null; let rowCounter = 0;
        const pdfFileInput = document.getElementById('pdfFile');
        pdfFileInput.addEventListener('change', (e) => { if (e.target.files[0]) handleFile(e.target.files[0]); });
        function handleFile(file) { selectedFile = file; document.getElementById('uploadZone').style.display = 'none'; document.getElementById('btnScan').classList.remove('hidden'); }
        async function scanPDF() { if (!selectedFile) return; const fd = new FormData(); fd.append('pdf', selectedFile); const res = await fetch('/scan', { method: 'POST', body: fd }); const data = await res.json(); const chips = document.getElementById('moneyChips'); chips.innerHTML = ''; data.money_values.forEach(val => { const btn = document.createElement('button'); btn.className = 'money-chip'; btn.textContent = val; btn.onclick = () => fillFindField(val); chips.appendChild(btn); }); document.getElementById('scanResults').classList.add('show'); }
        function fillFindField(val) { const inputs = document.querySelectorAll('.find-input'); for(const i of inputs) { if(!i.value) { i.value = val; return; } } addRow(val); }
        function addRow(val = '') { rowCounter++; const list = document.getElementById('replacementsList'); const div = document.createElement('div'); div.className = 'row-wrap'; div.id = `row-${rowCounter}`; div.innerHTML = `<div class="row-fields"><input type="text" class="field-input find-input" name="find[]" value="${val}"><input type="text" class="field-input" name="replace[]"></div><button class="btn-remove" onclick="removeRow(${rowCounter})">×</button>`; list.appendChild(div); }
        function removeRow(id) { document.getElementById(`row-${id}`).remove(); }
        async function processPDF() { if(!selectedFile) return; document.getElementById('spinnerOverlay').classList.add('show'); const fd = new FormData(); fd.append('pdf', selectedFile); document.querySelectorAll('input[name="find[]"]').forEach(i => fd.append('find[]', i.value)); document.querySelectorAll('input[name="replace[]"]').forEach(i => fd.append('replace[]', i.value)); const res = await fetch('/process', { method: 'POST', body: fd }); document.getElementById('spinnerOverlay').classList.remove('show'); if(res.ok) { const b = await res.blob(); const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = 'edited.pdf'; a.click(); showStatus('success', 'PDF saved!'); } else { showStatus('error', 'Error processing'); } }
        function showStatus(t, m) { const b = document.getElementById('statusBox'); b.className = 'status-box show ' + t; b.textContent = m; }
        addRow();
    </script>
</body>
</html>
"""

@app.route('/')
def index(): return HTML

@app.route('/scan', methods=['POST'])
def scan_pdf():
    pdf_bytes = request.files['pdf'].read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    vals = []
    pattern = re.compile(r'\$[\d,]+\.?\d*')
    for page in doc:
        for val in pattern.findall(page.get_text()):
            if val not in vals: vals.append(val)
    return jsonify({'money_values': vals})

@app.route('/process', methods=['POST'])
def process_pdf():
    pdf_file = request.files['pdf']
    finds = request.form.getlist('find[]')
    replaces = request.form.getlist('replace[]')
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    
    for old_text, new_text in zip(finds, replaces):
        if not old_text.strip(): continue
        for page in doc:
            instances = page.search_for(old_text)
            # Primero redactamos todas las instancias
            for inst in instances:
                page.add_redact_annot(inst)
            page.apply_redactions()
            
            # Luego insertamos el texto nuevo forzando negrita
            for inst in instances:
                # Usamos helv-bold para forzar la negrita y mantener el formato limpio
                page.insert_text(inst.tl, new_text, fontname="helv-bold", fontsize=10, color=(0,0,0))
    
    output = io.BytesIO()
    doc.save(output, deflate=True)
    output.seek(0)
    return send_file(output, mimetype='application/pdf', as_attachment=True, download_name="edited.pdf")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
