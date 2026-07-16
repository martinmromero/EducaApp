import io


def render_exam_payload_to_docx(payload, formato):
    """Renderiza payload neutral de examen a DOCX y retorna bytes."""
    from docx import Document

    doc = Document()
    _apply_margins(doc, formato)
    _append_payload(doc, payload, formato)

    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out.read()


def render_exam_batch_payloads_to_docx(exam_documents):
    """Renderiza varios payloads de examen a un unico DOCX y retorna bytes."""
    from docx import Document

    doc = Document()
    if not exam_documents:
        out = io.BytesIO()
        doc.save(out)
        out.seek(0)
        return out.read()

    _apply_margins(doc, exam_documents[0]['formato'])

    for idx, item in enumerate(exam_documents):
        formato = item['formato']
        payload = item['payload']
        label = item.get('label') or f'Version {idx + 1}'
        base_size = int(getattr(formato, 'tamano_fuente', 11) or 11)
        title_rgb = _hex_to_rgb(getattr(formato, 'color_titulo', '') or '#111111')
        text_rgb = _hex_to_rgb(getattr(formato, 'color_texto', '') or '#111111')

        if idx > 0:
            doc.add_page_break()

        label_paragraph = _add_line(
            doc,
            label,
            base_size=base_size,
            text_rgb=text_rgb,
            bold=True,
            size=base_size + 3,
            color=title_rgb,
        )
        label_paragraph.alignment = 1
        _append_payload(doc, payload, formato)

    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out.read()


def _apply_margins(doc, formato):
    from docx.shared import Cm

    for section in doc.sections:
        section.top_margin = Cm(float(getattr(formato, 'margen_superior_cm', 2.0) or 2.0))
        section.bottom_margin = Cm(float(getattr(formato, 'margen_inferior_cm', 2.0) or 2.0))
        section.left_margin = Cm(float(getattr(formato, 'margen_izquierdo_cm', 2.5) or 2.5))
        section.right_margin = Cm(float(getattr(formato, 'margen_derecho_cm', 2.0) or 2.0))


def _add_line(doc, text, *, base_size, text_rgb, bold=False, size=None, color=None):
    from docx.shared import Pt, RGBColor

    paragraph = doc.add_paragraph()
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.size = Pt(size or base_size)
    run.font.color.rgb = RGBColor(*(color or text_rgb))
    return paragraph


def _append_payload(doc, payload, formato):
    base_size = int(getattr(formato, 'tamano_fuente', 11) or 11)
    title_rgb = _hex_to_rgb(getattr(formato, 'color_titulo', '') or '#111111')
    text_rgb = _hex_to_rgb(getattr(formato, 'color_texto', '') or '#111111')

    def add_line(text, bold=False, size=None, color=None):
        return _add_line(doc, text, base_size=base_size, text_rgb=text_rgb, bold=bold, size=size, color=color)

    for block in payload:
        tipo = block.get('tipo')

        if tipo == 'encabezado':
            for value in [
                block.get('institucion', ''),
                ' - '.join([v for v in [block.get('facultad', ''), block.get('carrera', '')] if v]),
                block.get('materia', ''),
            ]:
                if value:
                    p = add_line(value, bold=True, size=base_size + 1, color=title_rgb)
                    p.alignment = 1

            meta = []
            if block.get('profesor'):
                meta.append(f"Profesor/a: {block['profesor']}")
            if block.get('fecha'):
                meta.append(f"Fecha: {block['fecha']}")
            if block.get('duracion_minutos'):
                meta.append(f"Duracion: {block['duracion_minutos']} min")
            if meta:
                add_line(' | '.join(meta))

        elif tipo == 'titulo' and block.get('texto'):
            p = add_line(block['texto'], bold=True, size=base_size + 4, color=title_rgb)
            p.alignment = 1

        elif tipo == 'instrucciones' and block.get('texto'):
            add_line('Instrucciones generales', bold=True, size=base_size + 1, color=title_rgb)
            add_line(block['texto'])

        elif tipo == 'lista_outcomes' and block.get('items'):
            add_line('Resultados de aprendizaje evaluados', bold=True, size=base_size + 1, color=title_rgb)
            for item in block['items']:
                add_line(f"- {item}")

        elif tipo == 'lista_temas' and block.get('items'):
            add_line('Temas a evaluar', bold=True, size=base_size + 1, color=title_rgb)
            for item in block['items']:
                add_line(f"- {item}")

        elif tipo == 'pregunta':
            add_line(f"{block.get('numero', '')}. {block.get('texto', '')}", bold=True)
            subtype = block.get('subtipo')
            if subtype == 'opcion_multiple':
                for idx, opt in enumerate(block.get('opciones', []), start=1):
                    add_line(f"   {idx}) {opt}")
            elif subtype == 'verdadero_falso':
                add_line('   ( ) Verdadero      ( ) Falso')
            elif subtype in ('completar_blank', 'desarrollo'):
                add_line('   ___________________________________________')
                add_line('   ___________________________________________')
            if block.get('respuesta'):
                add_line(f"Respuesta: {block['respuesta']}", bold=True, color=title_rgb)

        elif tipo == 'tabla_rubrica' and block.get('filas'):
            add_line(block.get('titulo', 'Rubrica'), bold=True, size=base_size + 1, color=title_rgb)
            headers = ['Criterio'] + list(block.get('columnas', []))
            table = doc.add_table(rows=1, cols=len(headers))
            for i, h in enumerate(headers):
                table.rows[0].cells[i].text = h
            for row in block['filas']:
                cells = table.add_row().cells
                cells[0].text = row.get('criterio', '')
                for i, value in enumerate(row.get('celdas', []), start=1):
                    if i < len(cells):
                        cells[i].text = value


def _hex_to_rgb(hex_color):
    value = (hex_color or '').strip()
    if not (len(value) == 7 and value.startswith('#')):
        value = '#111111'
    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)
