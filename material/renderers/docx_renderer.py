import io
import os
import base64


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

        if tipo in {'letterhead', 'encabezado'}:
            _append_letterhead_table(doc, block, base_size, title_rgb, text_rgb)

        elif tipo == 'datos_alumno':
            _append_student_data_table(doc, block, base_size, title_rgb, text_rgb)

        elif tipo == 'titulo' and block.get('texto'):
            p = add_line(block['texto'], bold=True, size=base_size + 4, color=title_rgb)
            p.alignment = 1

        elif tipo in {'instrucciones', 'instrucciones_generales'} and block.get('texto'):
            add_line('Instrucciones generales', bold=True, size=base_size + 1, color=title_rgb)
            add_line(block['texto'])

        elif tipo in {'lista_outcomes', 'resultados_aprendizaje'} and block.get('items'):
            add_line('Resultados de aprendizaje evaluados', bold=True, size=base_size + 1, color=title_rgb)
            for item in block['items']:
                add_line(f"- {item}")

        elif tipo == 'requisitos_aprobar' and block.get('texto'):
            add_line('Requisitos para aprobar', bold=True, size=base_size + 1, color=title_rgb)
            add_line(block['texto'])

        elif tipo == 'tiempo' and block.get('texto'):
            add_line(f"Tiempo: {block['texto']}", bold=False)

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


def _decode_data_uri(data_uri):
    if not data_uri or not str(data_uri).startswith('data:'):
        return None
    try:
        _, encoded = str(data_uri).split(',', 1)
        return base64.b64decode(encoded)
    except Exception:
        return None


def _resolve_logo_bytes_or_path(block):
    logo_b64 = block.get('logo_b64') or ''
    logo_url = block.get('logo_url') or ''
    logo_path = block.get('logo_path') or ''

    img_bytes = _decode_data_uri(logo_b64) or _decode_data_uri(logo_url)
    if img_bytes:
        return io.BytesIO(img_bytes), None

    for candidate in [logo_path, logo_url]:
        if candidate and os.path.exists(candidate):
            return None, candidate
    return None, None


def _apply_table_borders(table):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    tbl = table._tbl
    tbl_pr = tbl.tblPr
    if tbl_pr is None:
        tbl_pr = OxmlElement('w:tblPr')
        tbl.insert(0, tbl_pr)

    borders = OxmlElement('w:tblBorders')
    for name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        edge = OxmlElement(f'w:{name}')
        edge.set(qn('w:val'), 'single')
        edge.set(qn('w:sz'), '8')
        edge.set(qn('w:space'), '0')
        edge.set(qn('w:color'), '444444')
        borders.append(edge)
    tbl_pr.append(borders)


def _append_letterhead_table(doc, block, base_size, title_rgb, text_rgb):
    from docx.shared import Cm, Pt, RGBColor

    table = doc.add_table(rows=2, cols=3)
    _apply_table_borders(table)

    table.columns[0].width = Cm(2.1)
    table.columns[2].width = Cm(2.3)

    institution = (block.get('institucion') or '-').upper()
    career = block.get('carrera') or '-'
    subject = block.get('materia') or '-'
    professor = block.get('profesor') or '-'
    exam_type = block.get('tipo_examen') or 'Examen'
    year = str(block.get('anio') or '-')

    logo_stream, logo_path = _resolve_logo_bytes_or_path(block)
    logo_paragraph = table.rows[0].cells[0].paragraphs[0]
    if logo_stream or logo_path:
        run = logo_paragraph.add_run()
        try:
            run.add_picture(logo_stream or logo_path, width=Cm(1.6))
        except Exception:
            pass

    center_top = table.rows[0].cells[1].paragraphs[0]
    center_top.alignment = 1
    run = center_top.add_run(institution)
    run.bold = True
    run.font.size = Pt(base_size + 1)
    run.font.color.rgb = RGBColor(*title_rgb)

    right_top = table.rows[0].cells[2].paragraphs[0]
    right_top.alignment = 1
    rt1 = right_top.add_run('Año\n')
    rt1.bold = True
    rt1.font.size = Pt(base_size - 1 if base_size > 9 else base_size)
    rt1.font.color.rgb = RGBColor(*text_rgb)
    rt2 = right_top.add_run(year)
    rt2.font.size = Pt(base_size)
    rt2.font.color.rgb = RGBColor(*text_rgb)

    meta_cell = table.rows[1].cells[1]
    p_meta = meta_cell.paragraphs[0]
    m1 = p_meta.add_run(f'Carrera: {career}    Profesor: {professor}')
    m1.font.size = Pt(base_size)
    m1.font.color.rgb = RGBColor(*text_rgb)
    p_meta = meta_cell.add_paragraph()
    m2 = p_meta.add_run(f'Materia: {subject}    {exam_type}')
    m2.bold = True
    m2.font.size = Pt(base_size)
    m2.font.color.rgb = RGBColor(*text_rgb)


def _append_student_data_table(doc, block, base_size, title_rgb, text_rgb):
    from docx.shared import Pt, RGBColor

    table = doc.add_table(rows=2, cols=4)
    _apply_table_borders(table)

    table.rows[0].cells[0].text = 'Nombre'
    table.rows[0].cells[1].text = '____________________'
    table.rows[0].cells[2].text = 'Apellido'
    table.rows[0].cells[3].text = '____________________'

    table.rows[1].cells[0].text = 'Fecha'
    table.rows[1].cells[1].text = block.get('fecha') or ''
    merged = table.rows[1].cells[2].merge(table.rows[1].cells[3])
    merged.text = (block.get('tipo_examen') or 'EXAMEN').upper()

    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(base_size)
                    run.font.color.rgb = RGBColor(*text_rgb)
                    if (row_idx == 0 and col_idx in [0, 2]) or (row_idx == 1 and col_idx == 0):
                        run.bold = True
                if row_idx == 1 and col_idx >= 2:
                    paragraph.alignment = 1
                    for run in paragraph.runs:
                        run.bold = True
                        run.font.color.rgb = RGBColor(*title_rgb)
