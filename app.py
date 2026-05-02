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
    :root {
      --pink: #FF385C;
      --pink-dark: #e0314f;
      --pink-light: #fff0f2;
      --gray-50: #f9fafb;
      --gray-100: #f3f4f6;
      --gray-200: #e5e7eb;
      --gray-300: #d1d5db;
      --gray-400: #9ca3af;
      --gray-600: #4b5563;
      --gray-700: #374151;
      --gray-900: #111827;
      --green: #10b981;
      --green-light: #ecfdf5;
      --red: #ef4444;
      --red-light: #fef2f2;
      --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
      --shadow: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -1px rgba(0,0,0,0.04);
      --shadow-lg: 0 10px 25px -5px rgba(0,0,0,0.1), 0 4px 10px -5px rgba(0,0,0,0.04);
      --radius: 12px;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--gray-50);
      color: var(--gray-900);
      min-height: 100vh;
    }
    /* NAVBAR */
    nav {
      background: white;
      border-bottom: 1px solid var(--gray-200);
      padding: 0 24px;
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: var(--shadow-sm);
    }
    .nav-brand {
      display: flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
    }
    .nav-logo {
      width: 36px;
      height: 36px;
      background: var(--pink);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 18px;
    }
    .nav-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--gray-900);
    }
    .nav-subtitle {
      font-size: 12px;
      color: var(--gray-400);
    }
    .nav-badge {
      background: var(--pink-light);
      color: var(--pink);
      font-size: 11px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 20px;
    }
    /* MAIN LAYOUT */
    main {
      max-width: 860px;
      margin: 0 auto;
      padding: 40px 24px 80px;
    }
    .hero {
      text-align: center;
      margin-bottom: 40px;
    }
    .hero h1 {
      font-size: 32px;
      font-weight: 800;
      color: var(--gray-900);
      line-height: 1.2;
      margin-bottom: 10px;
    }
    .hero h1 span { color: var(--pink); }
    .hero p {
      font-size: 16px;
      color: var(--gray-600);
      max-width: 520px;
      margin: 0 auto;
      line-height: 1.6;
    }
    /* CARDS */
    .card {
      background: white;
      border-radius: var(--radius);
      border: 1px solid var(--gray-200);
      box-shadow: var(--shadow);
      overflow: hidden;
      margin-bottom: 20px;
    }
    .card-header {
      padding: 20px 24px 16px;
      border-bottom: 1px solid var(--gray-100);
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .card-icon {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 15px;
      flex-shrink: 0;
    }
    .card-icon.pink { background: var(--pink-light); }
    .card-icon.blue { background: #eff6ff; }
    .card-icon.green { background: var(--green-light); }
    .card-title {
      font-size: 15px;
      font-weight: 700;
      color: var(--gray-900);
    }
    .card-desc {
      font-size: 13px;
      color: var(--gray-400);
      margin-top: 2px;
    }
    .card-body { padding: 24px; }
    /* UPLOAD ZONE */
    .upload-zone {
      border: 2px dashed var(--gray-300);
      border-radius: 10px;
      padding: 40px 24px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
      position: relative;
    }
    .upload-zone:hover, .upload-zone.drag-over {
      border-color: var(--pink);
      background: var(--pink-light);
    }
    .upload-zone input[type="file"] {
      position: absolute;
      inset: 0;
      opacity: 0;
      cursor: pointer;
      width: 100%;
    }
    .upload-icon {
      width: 52px;
      height: 52px;
      background: var(--gray-100);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 14px;
      font-size: 24px;
      transition: background 0.2s;
    }
    .upload-zone:hover .upload-icon, .upload-zone.drag-over .upload-icon {
      background: white;
    }
    .upload-zone h3 {
      font-size: 15px;
      font-weight: 600;
      color: var(--gray-700);
      margin-bottom: 6px;
    }
    .upload-zone p {
      font-size: 13px;
      color: var(--gray-400);
    }
    .upload-zone .browse { color: var(--pink); font-weight: 600; }
    /* FILE SELECTED STATE */
    .file-selected {
      display: none;
      align-items: center;
      gap: 14px;
      padding: 16px 20px;
      background: var(--green-light);
      border: 1.5px solid #a7f3d0;
      border-radius: 10px;
    }
    .file-selected.show { display: flex; }
    .file-selected-icon {
      width: 40px;
      height: 40px;
      background: var(--green);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 18px;
      flex-shrink: 0;
    }
    .file-selected-name {
      font-size: 14px;
      font-weight: 600;
      color: #065f46;
    }
    .file-selected-size {
      font-size: 12px;
      color: #6ee7b7;
    }
    .file-change {
      margin-left: auto;
      background: none;
      border: 1.5px solid #6ee7b7;
      color: #065f46;
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 12px;
      cursor: pointer;
      font-weight: 500;
      transition: all 0.2s;
    }
    .file-change:hover { background: white; }
    /* SCAN BUTTON */
    .btn-scan {
      display: block;
      width: 100%;
      margin-top: 14px;
      padding: 11px;
      background: var(--gray-100);
      color: var(--gray-700);
      border: 1px solid var(--gray-200);
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      text-align: center;
    }
    .btn-scan:hover { background: var(--gray-200); }
    .btn-scan.hidden { display: none; }
    /* SCAN RESULTS */
    .scan-results {
      display: none;
      margin-top: 14px;
    }
    .scan-results.show { display: block; }
    .scan-label {
      font-size: 12px;
      font-weight: 600;
      color: var(--gray-400);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 8px;
    }
    .money-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .money-chip {
      background: var(--pink-light);
      color: var(--pink-dark);
      border: 1.5px solid #fecdd3;
      border-radius: 20px;
      padding: 5px 12px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
      font-family: 'Menlo', 'Monaco', monospace;
    }
    .money-chip:hover {
      background: var(--pink);
      color: white;
      border-color: var(--pink);
      transform: translateY(-1px);
    }
    /* REPLACEMENT ROWS */
    .replacements-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .row-wrap {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .row-fields {
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      gap: 8px;
      flex: 1;
      align-items: center;
    }
    .arrow-icon {
      color: var(--gray-400);
      font-size: 16px;
      text-align: center;
    }
    .field-group {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .field-label {
      font-size: 11px;
      font-weight: 600;
      color: var(--gray-400);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .field-input {
      width: 100%;
      padding: 10px 12px;
      border: 1.5px solid var(--gray-200);
      border-radius: 8px;
      font-size: 14px;
      font-family: 'Menlo', 'Monaco', monospace;
      font-weight: 500;
      color: var(--gray-900);
      transition: border-color 0.2s;
      background: white;
    }
    .field-input:focus {
      outline: none;
      border-color: var(--pink);
      box-shadow: 0 0 0 3px rgba(255, 56, 92, 0.1);
    }
    .field-input.find-field { background: #fff8f8; }
    .field-input.replace-field { background: #f0fdf4; }
    .btn-remove {
      width: 32px;
      height: 32px;
      background: var(--gray-100);
      border: 1px solid var(--gray-200);
      border-radius: 6px;
      color: var(--gray-400);
      cursor: pointer;
      font-size: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      transition: all 0.2s;
    }
    .btn-remove:hover { background: var(--red-light); color: var(--red); border-color: #fecaca; }
    .btn-add-row {
      background: none;
      border: 1.5px dashed var(--gray-300);
      border-radius: 8px;
      color: var(--gray-400);
      font-size: 13px;
      font-weight: 600;
      padding: 10px;
      cursor: pointer;
      width: 100%;
      margin-top: 4px;
      transition: all 0.2s;
    }
    .btn-add-row:hover { border-color: var(--pink); color: var(--pink); background: var(--pink-light); }
    /* PROCESS BUTTON */
    .btn-process {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      width: 100%;
      padding: 15px;
      background: var(--pink);
      color: white;
      border: none;
      border-radius: 10px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
      box-shadow: 0 4px 14px rgba(255, 56, 92, 0.35);
    }
    .btn-process:hover {
      background: var(--pink-dark);
      transform: translateY(-1px);
      box-shadow: 0 6px 20px rgba(255, 56, 92, 0.4);
    }
    .btn-process:active { transform: translateY(0); }
    .btn-process:disabled {
      background: var(--gray-300);
      box-shadow: none;
      cursor: not-allowed;
      transform: none;
    }
    /* STATUS */
    .status-box {
      display: none;
      padding: 14px 18px;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 500;
      align-items: center;
      gap: 10px;
      margin-top: 14px;
    }
    .status-box.show { display: flex; }
    .status-box.loading { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .status-box.success { background: var(--green-light); color: #065f46; border: 1px solid #a7f3d0; }
    .status-box.error { background: var(--red-light); color: #991b1b; border: 1px solid #fecaca; }
    .spin {
      width: 16px;
      height: 16px;
      border: 2px solid currentColor;
      border-top-color: transparent;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
      flex-shrink: 0;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    /* TIPS */
    .tips {
      background: #fffbeb;
      border: 1px solid #fde68a;
      border-radius: 10px;
      padding: 16px 18px;
    }
    .tips-title {
      font-size: 13px;
      font-weight: 700;
      color: #92400e;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .tips ul {
      padding-left: 18px;
    }
    .tips li {
      font-size: 13px;
      color: #78350f;
      margin-bottom: 4px;
      line-height: 1.5;
    }
    /* FOOTER */
    footer {
      text-align: center;
      padding: 24px;
      color: var(--gray-400);
      font-size: 13px;
      border-top: 1px solid var(--gray-200);
    }
    /* SPINNER overlay */
    .spinner-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.3);
      z-index: 999;
      align-items: center;
      justify-content: center;
    }
    .spinner-overlay.show { display: flex; }
    .spinner-box {
      background: white;
      border-radius: 14px;
      padding: 32px 40px;
      text-align: center;
      box-shadow: var(--shadow-lg);
    }
    .big-spin {
      width: 48px;
      height: 48px;
      border: 4px solid var(--gray-200);
      border-top-color: var(--pink);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin: 0 auto 16px;
    }
    .spinner-box p {
      font-size: 15px;
      font-weight: 600;
      color: var(--gray-700);
    }
    .spinner-box small {
      display: block;
      font-size: 12px;
      color: var(--gray-400);
      margin-top: 4px;
    }
    @media (max-width: 600px) {
      .hero h1 { font-size: 24px; }
      .row-fields { grid-template-columns: 1fr; }
      .arrow-icon { display: none; }
    }
    /* FORMAT BUTTONS */
    .format-buttons {
      display: flex;
      gap: 6px;
      flex-shrink: 0;
    }
    .format-btn {
      padding: 8px 12px;
      border: 1.5px solid var(--gray-200);
      border-radius: 6px;
      background: white;
      cursor: pointer;
      font-size: 12px;
      font-weight: 500;
      transition: all 0.2s;
      color: var(--gray-600);
    }
    .format-btn.active {
      background: var(--pink);
      border-color: var(--pink);
      color: white;
    }
    .format-btn.semibold.active { background: var(--pink); }
    .format-btn.bold.active { background: var(--pink-dark); }
    .format-btn.normal.active { background: var(--gray-400); border-color: var(--gray-400); }
    .format-btn:hover:not(.active) {
      background: var(--pink-light);
      border-color: var(--pink);
      color: var(--pink);
    }
  </style>
</head>
<body>
<nav>
  <a class="nav-brand" href="/">
    <div class="nav-logo">📄</div>
    <div>
      <div class="nav-title">PDF Value Editor</div>
      <div class="nav-subtitle">Airbnb & more</div>
    </div>
  </a>
  <span class="nav-badge">✦ Smart Replace</span>
</nav>
<main>
  <div class="hero">
    <h1>Edit <span>PDF values</span> without<br>breaking the layout</h1>
    <p>Upload any PDF, auto-detect money values, replace them precisely and download the edited file.</p>
  </div>
  <!-- STEP 1: Upload -->
  <div class="card">
    <div class="card-header">
      <div class="card-icon pink">📤</div>
      <div>
        <div class="card-title">Step 1 — Upload your PDF</div>
        <div class="card-desc">Supports any Airbnb reservation PDF or standard PDF</div>
      </div>
    </div>
    <div class="card-body">
      <div class="upload-zone" id="uploadZone">
        <input type="file" id="pdfFile" accept=".pdf" />
        <div class="upload-icon">📄</div>
        <h3>Drop your PDF here or <span class="browse">browse</span></h3>
        <p>Max file size: 50 MB · PDF files only</p>
      </div>
      <div class="file-selected" id="fileSelected">
        <div class="file-selected-icon">✓</div>
        <div>
          <div class="file-selected-name" id="fileName">—</div>
          <div class="file-selected-size" id="fileSize">—</div>
        </div>
        <button class="file-change" onclick="resetFile()">Change</button>
      </div>
      <button class="btn-scan hidden" id="btnScan" onclick="scanPDF()">
        🔍 Auto-detect money values in this PDF
      </button>
      <div class="scan-results" id="scanResults">
        <div class="scan-label">Values found — click to use</div>
        <div class="money-chips" id="moneyChips"></div>
      </div>
    </div>
  </div>
  <!-- STEP 2: Replacements -->
  <div class="card">
    <div class="card-header">
      <div class="card-icon blue">🔄</div>
      <div>
        <div class="card-title">Step 2 — Set your replacements</div>
        <div class="card-desc">Paste the exact text to find (case-sensitive)</div>
      </div>
    </div>
    <div class="card-body">
      <div class="replacements-list" id="replacementsList">
        <!-- rows inserted by JS -->
      </div>
      <button class="btn-add-row" onclick="addRow()">+ Add another replacement</button>
    </div>
  </div>
  <!-- Tips -->
  <div class="tips">
    <div class="tips-title">💡 Tips for best results</div>
    <ul>
      <li>Use <strong>Auto-detect</strong> to find money values automatically, then click them to fill the "Find" field.</li>
      <li>Copy the value <strong>exactly</strong> as it appears in the PDF, including the <code>$</code> sign and commas.</li>
      <li>For Airbnb PDFs the total usually appears as <code>$1,368.05</code> — match it exactly.</li>
      <li>The original layout, images and fonts are preserved. Only the target text changes.</li>
    </ul>
  </div>
  <!-- STEP 3: Process -->
  <div class="card" style="margin-top:20px">
    <div class="card-header">
      <div class="card-icon green">⬇️</div>
      <div>
        <div class="card-title">Step 3 — Process & Download</div>
        <div class="card-desc">Your edited PDF will download automatically</div>
      </div>
    </div>
    <div class="card-body">
      <button class="btn-process" id="btnProcess" onclick="processPDF()">
        ✦ &nbsp; Edit PDF & Download
      </button>
      <div class="status-box" id="statusBox"></div>
    </div>
  </div>
</main>
<footer>
  PDF Value Editor · Preserves structure · Works with Airbnb, VRBO and more
</footer>
<!-- Spinner overlay -->
<div class="spinner-overlay" id="spinnerOverlay">
  <div class="spinner-box">
    <div class="big-spin"></div>
    <p>Editing your PDF…</p>
    <small>This usually takes just a second</small>
  </div>
</div>
<script>
  let selectedFile = null;
  let rowCounter = 0;
  // --- Upload ---
  const uploadZone = document.getElementById('uploadZone');
  const pdfFileInput = document.getElementById('pdfFile');
  pdfFileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) handleFile(e.target.files[0]);
  });
  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
  });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') handleFile(file);
  });
  function handleFile(file) {
    selectedFile = file;
    document.getElementById('uploadZone').style.display = 'none';
    document.getElementById('fileSelected').classList.add('show');
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = formatBytes(file.size);
    document.getElementById('btnScan').classList.remove('hidden');
    document.getElementById('scanResults').classList.remove('show');
    document.getElementById('moneyChips').innerHTML = '';
  }
  function resetFile() {
    selectedFile = null;
    pdfFileInput.value = '';
    document.getElementById('uploadZone').style.display = '';
    document.getElementById('fileSelected').classList.remove('show');
    document.getElementById('btnScan').classList.add('hidden');
    document.getElementById('scanResults').classList.remove('show');
  }
  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  }
  // --- Scan ---
  async function scanPDF() {
    if (!selectedFile) return;
    const btn = document.getElementById('btnScan');
    btn.textContent = '⏳ Scanning…';
    btn.disabled = true;
    const fd = new FormData();
    fd.append('pdf', selectedFile);
    try {
      const res = await fetch('/scan', { method: 'POST', body: fd });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      const chips = document.getElementById('moneyChips');
      chips.innerHTML = '';
      if (data.money_values && data.money_values.length > 0) {
        data.money_values.forEach(val => {
          const chip = document.createElement('button');
          chip.className = 'money-chip';
          chip.textContent = val;
          chip.title = 'Click to use this value';
          chip.onclick = () => fillFindField(val);
          chips.appendChild(chip);
        });
        document.getElementById('scanResults').classList.add('show');
      } else {
        chips.innerHTML = '<span style="color:var(--gray-400);font-size:13px">No money values detected. Enter text manually below.</span>';
        document.getElementById('scanResults').classList.add('show');
      }
    } catch (err) {
      showStatus('error', '⚠️ Scan failed: ' + err.message);
    } finally {
      btn.textContent = '🔍 Auto-detect money values in this PDF';
      btn.disabled = false;
    }
  }
  function fillFindField(value) {
    // Find the first empty find field or add a new row
    const inputs = document.querySelectorAll('.find-input');
    for (const input of inputs) {
      if (!input.value.trim()) {
        input.value = value;
        input.focus();
        return;
      }
    }
    // All filled — add a new row with this value
    addRow(value);
  }
  // --- Replacement rows ---
  function addRow(prefillFind = '') {
    rowCounter++;
    const id = rowCounter;
    const list = document.getElementById('replacementsList');
    const div = document.createElement('div');
    div.className = 'row-wrap';
    div.id = `row-${id}`;
    div.innerHTML = `
      <div class="row-fields">
        <div class="field-group">
          <div class="field-label">Find (exact text)</div>
          <input type="text" class="field-input find-field find-input" 
                  name="find[]" placeholder='e.g. $1,368.05'
                 value="${escapeHtml(prefillFind)}" />
        </div>
        <div class="arrow-icon">→</div>
        <div class="field-group">
          <div class="field-label">Replace with</div>
          <input type="text" class="field-input replace-field" 
                  name="replace[]" placeholder='e.g. $2,450.00' />
        </div>
        <div class="field-group" style="flex-shrink:0">
          <div class="field-label">Format</div>
          <div class="format-buttons">
            <button type="button" class="format-btn normal" data-format="normal" onclick="setFormat(this, 'normal')">Normal</button>
            <button type="button" class="format-btn semibold active" data-format="semibold" onclick="setFormat(this, 'semibold')">Semi-bold</button>
            <button type="button" class="format-btn bold" data-format="bold" onclick="setFormat(this, 'bold')">Bold</button>
          </div>
          <input type="hidden" name="format[]" value="semibold" />
        </div>
      </div>
      <button class="btn-remove" onclick="removeRow(${id})" title="Remove">×</button>
    `;
    list.appendChild(div);
  }
  
  function setFormat(btn, format) {
    const formatDiv = btn.parentElement;
    const buttons = formatDiv.querySelectorAll('.format-btn');
    buttons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const hiddenInput = formatDiv.parentElement.querySelector('input[name="format[]"]');
    hiddenInput.value = format;
  }
  
  function removeRow(id) {
    const el = document.getElementById(`row-${id}`);
    if (el) el.remove();
  }
  function escapeHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  // --- Process ---
  async function processPDF() {
    if (!selectedFile) {
      showStatus('error', '⚠️ Please upload a PDF first.');
      return;
    }
    const finds = [...document.querySelectorAll('input[name="find[]"]')].map(i => i.value.trim());
    const replaces = [...document.querySelectorAll('input[name="replace[]"]')].map(i => i.value.trim());
    const formats = [...document.querySelectorAll('input[name="format[]"]')].map(i => i.value);
    
    if (finds.every(f => !f)) {
      showStatus('error', '⚠️ Please enter at least one value to find.');
      return;
    }
    document.getElementById('spinnerOverlay').classList.add('show');
    document.getElementById('btnProcess').disabled = true;
    hideStatus();
    const fd = new FormData();
    fd.append('pdf', selectedFile);
    finds.forEach(f => fd.append('find[]', f));
    replaces.forEach(r => fd.append('replace[]', r));
    formats.forEach(f => fd.append('format[]', f));
    
    try {
      const res = await fetch('/process', { method: 'POST', body: fd });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const disposition = res.headers.get('Content-Disposition') || '';
        const match = disposition.match(/filename="?([^"]+)"?/);
        a.download = match ? match[1] : 'edited.pdf';
        a.href = url;
        a.click();
        URL.revokeObjectURL(url);
        showStatus('success', '✅ PDF edited successfully! Check your downloads.');
      } else {
        const data = await res.json();
        showStatus('error', '⚠️ ' + (data.error || 'Unknown error'));
      }
    } catch (err) {
      showStatus('error', '⚠️ Network error: ' + err.message);
    } finally {
      document.getElementById('spinnerOverlay').classList.remove('show');
      document.getElementById('btnProcess').disabled = false;
    }
  }
  function showStatus(type, msg) {
    const box = document.getElementById('statusBox');
    box.className = 'status-box show ' + type;
    box.innerHTML = (type === 'loading' ? '<div class="spin"></div>' : '') + `<span>${msg}</span>`;
  }
  function hideStatus() {
    document.getElementById('statusBox').className = 'status-box';
  }
  // Init with one empty row
  addRow();
</script>
</body>
</html>
"""

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
    formats = request.form.getlist('format[]')
    
    if not finds or all(f.strip() == '' for f in finds):
        return jsonify({'error': 'No replacements specified'}), 400
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        total = 0
        
        # Mapeo de formatos a fuentes
        # Para semi-bold usamos la misma fuente regular pero con un pequeño ajuste
        # Como no hay fuente semi-bold nativa, simulamos con un stroke delgado
        for i, (old_text, new_text) in enumerate(zip(finds, replaces)):
            old_text = old_text.strip()
            new_text = new_text.strip()
            if not old_text:
                continue
            
            format_type = formats[i] if i < len(formats) else 'semibold'
            
            for page in doc:
                instances = page.search_for(old_text)
                for inst in instances:
                    # Extraer el tamaño y color de fuente original
                    font_size = 12.0
                    text_color = (0, 0, 0)
                    for block in page.get_text('dict').get('blocks', []):
                        if block.get('type') != 0: continue
                        for line in block.get('lines', []):
                            for span in line.get('spans', []):
                                if old_text in span.get('text', ''):
                                    font_size = span.get('size', 12.0)
                                    c = span.get('color', 0)
                                    text_color = (((c>>16)&0xFF)/255.0, ((c>>8)&0xFF)/255.0, (c&0xFF)/255.0)
                    
                    # Calcular espacio extra para texto más largo
                    extra = max(0, len(new_text) - len(old_text)) * font_size * 0.6
                    
                    # Borrar el texto original con un rectángulo blanco
                    page.draw_rect(
                        fitz.Rect(inst.x0-1, inst.y0-2, inst.x1+extra+5, inst.y1+2),
                        color=(1,1,1), fill=(1,1,1)
                    )
                    
                    # Insertar texto según el formato seleccionado
                    if format_type == 'normal':
                        # Texto normal
                        page.insert_text(
                            (inst.x0, inst.y0 + (inst.y1-inst.y0)*0.8),
                            new_text, fontname='helv', fontsize=font_size, color=text_color
                        )
                    elif format_type == 'semibold':
                        # Semi-bold: texto normal + stroke delgado para simular semi-negrita
                        page.insert_text(
                            (inst.x0, inst.y0 + (inst.y1-inst.y0)*0.8),
                            new_text, fontname='helv', fontsize=font_size, color=text_color,
                            stroke_width=0.3, stroke_color=text_color
                        )
                    elif format_type == 'bold':
                        # Bold completo
                        page.insert_text(
                            (inst.x0, inst.y0 + (inst.y1-inst.y0)*0.8),
                            new_text, fontname='hebo', fontsize=font_size, color=text_color
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
