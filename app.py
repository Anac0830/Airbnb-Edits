from flask import Flask, request, send_file, jsonify
import fitz  # PyMuPDF
import io
import os
import re

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# =========================
# FUENTES (AUTO-FALLBACK)
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FONT_REGULAR = os.path.join(BASE_DIR, "fonts/Inter-Regular.ttf")
FONT_MEDIUM  = os.path.join(BASE_DIR, "fonts/Inter-Medium.ttf")

def get_font(is_bold=True):
    """
    Devuelve fontfile si existe (Inter),
    si no, usa Helvetica fallback (no rompe nada).
    """
    if is_bold and os.path.exists(FONT_MEDIUM):
        return {"fontfile": FONT_MEDIUM}
    elif not is_bold and os.path.exists(FONT_REGULAR):
        return {"fontfile": FONT_REGULAR}
    else:
        return {"fontname": "hebo" if is_bold else "helv"}  # fallback seguro


# =========================
# FRONTEND (simple)
# =========================
HTML = """
<h2 style='font-family:sans-serif;text-align:center;margin-top:40px'>
PDF Value Editor running 🚀<br>
<small>Backend activo</small>
</h2>
"""


@app.route('/')
def index():
    return HTML


# =========================
# SCAN MONEY VALUES
# =========================
@app.route('/scan', methods=['POST'])
def scan_pdf():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    pdf_bytes = request.files['pdf'].read()

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        money_values = []
        pattern = re.compile(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?')

        for page in doc:
            text = page.get_text()
            found = pattern.findall(text)

            for val in found:
                if val not in money_values:
                    money_values.append(val)

        return jsonify({
            'money_values': money_values,
            'pages': len(doc)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =========================
# PROCESS PDF (TIPOGRAFÍA FIX)
# =========================
@app.route('/process', methods=['POST'])
def process_pdf():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    pdf_file = request.files['pdf']
    finds = request.form.getlist('find[]')
    replaces = request.form.getlist('replace[]')
    bolds = request.form.getlist('bold[]')

    if not finds or all(f.strip() == '' for f in finds):
        return jsonify({'error': 'No replacements specified'}), 400

    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        total = 0

        for i, (old_text, new_text) in enumerate(zip(finds, replaces)):
            old_text = old_text.strip()
            new_text = new_text.strip()

            if not old_text:
                continue

            is_bold = (bolds[i] == '1') if i < len(bolds) else True
            font_config = get_font(is_bold)

            for page in doc:
                instances = page.search_for(old_text)

                for inst in instances:

                    # =========================
                    # DETECTAR ESTILO ORIGINAL
                    # =========================
                    font_size = 12.0
                    text_color = (0, 0, 0)

                    blocks = page.get_text("dict").get("blocks", [])
                    for b in blocks:
                        if b.get("type") != 0:
                            continue
                        for line in b.get("lines", []):
                            for span in line.get("spans", []):
                                if old_text in span.get("text", ""):
                                    font_size = span.get("size", 12.0)
                                    c = span.get("color", 0)
                                    text_color = (
                                        ((c >> 16) & 255) / 255.0,
                                        ((c >> 8) & 255) / 255.0,
                                        (c & 255) / 255.0
                                    )

                    # =========================
                    # AJUSTE DE ANCHO (CLAVE)
                    # =========================
                    extra = max(0, len(new_text) - len(old_text)) * font_size * 0.55

                    # =========================
                    # BORRAR TEXTO ORIGINAL
                    # =========================
                    page.draw_rect(
                        fitz.Rect(inst.x0 - 1, inst.y0 - 2, inst.x1 + extra + 4, inst.y1 + 2),
                        color=(1, 1, 1),
                        fill=(1, 1, 1)
                    )

                    # =========================
                    # INSERTAR NUEVO TEXTO
                    # =========================
                    insert_kwargs = {
                        "fontsize": font_size,
                        "color": text_color
                    }

                    insert_kwargs.update(font_config)

                    page.insert_text(
                        (inst.x0, inst.y0 + (inst.y1 - inst.y0) * 0.8),
                        new_text,
                        **insert_kwargs
                    )

                    total += 1

        if total == 0:
            return jsonify({
                'error': 'Text not found. Copy exact value including $'
            }), 404

        output = io.BytesIO()
        doc.save(output, deflate=True, garbage=4)
        output.seek(0)

        name = pdf_file.filename.rsplit('.', 1)[0] + '_edited.pdf'

        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=name
        )

    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


# =========================
# RUN
# =========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
