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

                            span_text = span.get("text", "")

                            # 🔥 Match exacto (evita errores)
                            if span_text != old_text:
                                continue

                            bbox = span.get("bbox")
                            rect = fitz.Rect(bbox)

                            font_size = span.get("size", 12.0)
                            font_name = span.get("font", "helv")

                            c = span.get("color", 0)
                            text_color = (
                                ((c >> 16) & 0xFF) / 255.0,
                                ((c >> 8) & 0xFF) / 255.0,
                                (c & 0xFF) / 255.0
                            )

                            # Ajuste de ancho si el texto cambia
                            extra_width = max(0, len(new_text) - len(old_text)) * font_size * 0.5
                            rect.x1 += extra_width

                            # 🧼 Borrar SOLO esa área
                            page.draw_rect(rect, color=(1,1,1), fill=(1,1,1))

                            # ✨ Insertar con fuente REAL
                            page.insert_textbox(
                                rect,
                                new_text,
                                fontname=font_name,
                                fontsize=font_size,
                                color=text_color,
                                align=0
                            )

                            total += 1

        if total == 0:
            return jsonify({'error': 'Text not found in PDF. Copy exact text including $'}), 404

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
