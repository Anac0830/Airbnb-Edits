from flask import Flask, request, send_file, jsonify
import fitz
import io
import os
import re

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

@app.route('/')
def index():
    return "PDF Value Editor running 🚀"

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
                text_dict = page.get_text("dict")

                for block in text_dict.get("blocks", []):
                    if block.get("type") != 0:
                        continue

                    for line in block.get("lines", []):
                        for span in line.get("spans", []):

                            span_text = span.get("text", "").strip()

                            # match más robusto
                            if span_text != old_text:
                                continue

                            bbox = span.get("bbox")
                            rect = fitz.Rect(bbox)

                            font_size = span.get("size", 12.0)

                            # 🎯 intentar usar fuente original
                            font_name = span.get("font", "")

                            # fallback seguro (evita crash en Render)
                            valid_fonts = ["helv", "cour", "times", "symbol", "zapfdingbats"]
                            if not font_name or font_name.lower() not in valid_fonts:
                                font_name = "helv"

                            # color
                            c = span.get("color", 0)
                            text_color = (
                                ((c >> 16) & 0xFF) / 255.0,
                                ((c >> 8) & 0xFF) / 255.0,
                                (c & 0xFF) / 255.0
                            )

                            # ajustar ancho si cambia longitud
                            extra_width = max(0, len(new_text) - len(old_text)) * font_size * 0.5
                            rect.x1 += extra_width

                            # borrar área
                            page.draw_rect(rect, color=(1,1,1), fill=(1,1,1))

                            # insertar texto con protección
                            try:
                                page.insert_textbox(
                                    rect,
                                    new_text,
                                    fontname=font_name,
                                    fontsize=font_size,
                                    color=text_color,
                                    align=0
                                )
                            except:
                                # fallback garantizado
                                page.insert_textbox(
                                    rect,
                                    new_text,
                                    fontname="helv",
                                    fontsize=font_size,
                                    color=text_color,
                                    align=0
                                )

                            total += 1

        if total == 0:
            return jsonify({
                'error': 'Text not found. Make sure it matches EXACTLY (including $ and commas).'
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
