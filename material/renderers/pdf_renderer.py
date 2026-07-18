import io
import os
import base64
from PIL import Image as PILImage

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


_FONT_MAP = {
    'Arial': 'Helvetica',
    'Helvetica': 'Helvetica',
    'Calibri': 'Helvetica',
    'Times New Roman': 'Times-Roman',
}


def _to_hex_color(value, default):
    value = (value or '').strip()
    if len(value) == 7 and value.startswith('#'):
        return value
    return default


def render_exam_payload_to_pdf(payload, formato):
    """Renderiza payload neutral de examen a PDF y retorna bytes."""
    buf = io.BytesIO()

    left = float(getattr(formato, 'margen_izquierdo_cm', 2.5) or 2.5) * cm
    right = float(getattr(formato, 'margen_derecho_cm', 2.0) or 2.0) * cm
    top = float(getattr(formato, 'margen_superior_cm', 2.0) or 2.0) * cm
    bottom = float(getattr(formato, 'margen_inferior_cm', 2.0) or 2.0) * cm

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=left,
        rightMargin=right,
        topMargin=top,
        bottomMargin=bottom,
        title='Examen',
    )

    base_font = _FONT_MAP.get(getattr(formato, 'fuente', 'Arial'), 'Helvetica')
    base_size = int(getattr(formato, 'tamano_fuente', 11) or 11)
    leading = max(int(round(base_size * float(getattr(formato, 'interlineado', 1.15) or 1.15))), base_size + 1)
    title_color = colors.HexColor(_to_hex_color(getattr(formato, 'color_titulo', ''), '#111111'))
    text_color = colors.HexColor(_to_hex_color(getattr(formato, 'color_texto', ''), '#111111'))

    style_text, style_title, style_h2 = _build_styles(formato)

    flow = []
    _append_payload(flow, payload, style_text, style_title, style_h2, include_page_break=False)

    doc.build(flow)
    buf.seek(0)
    return buf.read()


def render_exam_batch_payloads_to_pdf(exam_documents):
    """Renderiza varios payloads de examen a un unico PDF y retorna bytes."""
    if not exam_documents:
        return b''

    first_format = exam_documents[0]['formato']
    left = float(getattr(first_format, 'margen_izquierdo_cm', 2.5) or 2.5) * cm
    right = float(getattr(first_format, 'margen_derecho_cm', 2.0) or 2.0) * cm
    top = float(getattr(first_format, 'margen_superior_cm', 2.0) or 2.0) * cm
    bottom = float(getattr(first_format, 'margen_inferior_cm', 2.0) or 2.0) * cm

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=left,
        rightMargin=right,
        topMargin=top,
        bottomMargin=bottom,
        title='Lote de examenes',
    )

    flow = []
    for idx, item in enumerate(exam_documents):
        payload = item['payload']
        formato = item['formato']
        style_text, style_title, style_h2 = _build_styles(formato)
        _append_payload(flow, payload, style_text, style_title, style_h2, include_page_break=idx < (len(exam_documents) - 1))

    doc.build(flow)
    buf.seek(0)
    return buf.read()


def _build_styles(formato):
    styles = getSampleStyleSheet()
    base_font = _FONT_MAP.get(getattr(formato, 'fuente', 'Arial'), 'Helvetica')
    base_size = int(getattr(formato, 'tamano_fuente', 11) or 11)
    leading = max(int(round(base_size * float(getattr(formato, 'interlineado', 1.15) or 1.15))), base_size + 1)
    title_color = colors.HexColor(_to_hex_color(getattr(formato, 'color_titulo', ''), '#111111'))
    text_color = colors.HexColor(_to_hex_color(getattr(formato, 'color_texto', ''), '#111111'))

    style_text = ParagraphStyle(
        'ExamText',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=base_size,
        leading=leading,
        textColor=text_color,
        spaceAfter=6,
    )
    style_title = ParagraphStyle(
        'ExamTitle',
        parent=style_text,
        fontSize=base_size + 4,
        leading=leading + 2,
        textColor=title_color,
        alignment=1,
        spaceAfter=10,
        spaceBefore=4,
    )
    style_h2 = ParagraphStyle(
        'ExamH2',
        parent=style_text,
        fontSize=base_size + 1,
        textColor=title_color,
        spaceBefore=8,
        spaceAfter=6,
        leftIndent=0,
    )

    return style_text, style_title, style_h2


def _append_payload(flow, payload, style_text, style_title, style_h2, *, include_page_break):
    base_font = style_text.fontName
    base_size = style_text.fontSize
    title_color = style_h2.textColor

    for block in payload:
        tipo = block.get('tipo')

        if tipo in {'letterhead', 'encabezado'}:
            flow.append(_build_letterhead_table(block, style_text, style_h2))
            flow.append(Spacer(1, 6))

        elif tipo == 'datos_alumno':
            flow.append(_build_student_data_table(block, style_text, style_h2))
            flow.append(Spacer(1, 8))

        elif tipo == 'titulo' and block.get('texto'):
            flow.append(Paragraph(block['texto'], style_title))

        elif tipo in {'instrucciones', 'instrucciones_generales'} and block.get('texto'):
            flow.append(Paragraph('Instrucciones generales', style_h2))
            flow.append(Paragraph(block['texto'].replace('\n', '<br/>'), style_text))

        elif tipo in {'lista_outcomes', 'resultados_aprendizaje'} and block.get('items'):
            flow.append(Paragraph('Resultados de aprendizaje evaluados', style_h2))
            for item in block['items']:
                flow.append(Paragraph(f"• {item}", style_text))

        elif tipo == 'requisitos_aprobar' and block.get('texto'):
            flow.append(Paragraph('Requisitos para aprobar', style_h2))
            flow.append(Paragraph(block['texto'].replace('\n', '<br/>'), style_text))

        elif tipo == 'tiempo' and block.get('texto'):
            flow.append(Paragraph(f"Tiempo: {block['texto']}", style_text))

        elif tipo == 'lista_temas' and block.get('items'):
            flow.append(Paragraph('Temas a evaluar', style_h2))
            for item in block['items']:
                flow.append(Paragraph(f"• {item}", style_text))

        elif tipo == 'pregunta':
            num = block.get('numero', '')
            text = block.get('texto', '')
            flow.append(Paragraph(f"<b>{num}. {text}</b>", style_text))
            subtype = block.get('subtipo')
            if subtype == 'opcion_multiple':
                for idx, opt in enumerate(block.get('opciones', []), start=1):
                    flow.append(Paragraph(f"   {idx}) {opt}", style_text))
            elif subtype == 'verdadero_falso':
                flow.append(Paragraph('   ( ) Verdadero      ( ) Falso', style_text))
            elif subtype == 'completar_blank':
                flow.append(Paragraph('   ___________________________________________', style_text))
            elif subtype == 'desarrollo':
                flow.append(Paragraph('   ___________________________________________', style_text))
                flow.append(Paragraph('   ___________________________________________', style_text))

            if block.get('respuesta'):
                flow.append(Paragraph(f"<b>Respuesta:</b> {block['respuesta']}", style_text))
            flow.append(Spacer(1, 5))

        elif tipo == 'tabla_rubrica' and block.get('filas'):
            flow.append(Paragraph(block.get('titulo', 'Rubrica'), style_h2))
            headers = ['Criterio'] + list(block.get('columnas', []))
            rows = [headers]
            for row in block['filas']:
                rows.append([row.get('criterio', '')] + list(row.get('celdas', [])))

            table = Table(rows, hAlign='LEFT')
            table_style = TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), title_color),
                ('FONTNAME', (0, 0), (-1, 0), base_font),
                ('FONTNAME', (0, 1), (-1, -1), base_font),
                ('FONTSIZE', (0, 0), (-1, -1), base_size - 1 if base_size > 9 else base_size),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ])
            table.setStyle(table_style)
            flow.append(table)
            flow.append(Spacer(1, 8))

    if include_page_break:
        flow.append(PageBreak())


def _decode_data_uri(data_uri):
    if not data_uri or not str(data_uri).startswith('data:'):
        return None
    try:
        _, encoded = str(data_uri).split(',', 1)
        return base64.b64decode(encoded)
    except Exception:
        return None


def _build_logo_flowable(block):
    logo_b64 = block.get('logo_b64') or ''
    logo_url = block.get('logo_url') or ''
    logo_path = block.get('logo_path') or ''

    max_width = 1.6 * cm
    max_height = 1.2 * cm
    img_bytes = _decode_data_uri(logo_b64) or _decode_data_uri(logo_url)
    if img_bytes:
        width, height = _fit_logo_size(img_bytes=img_bytes, max_width=max_width, max_height=max_height)
        return Image(io.BytesIO(img_bytes), width=width, height=height)

    for path_value in [logo_path, logo_url]:
        if path_value and os.path.exists(path_value):
            try:
                width, height = _fit_logo_size(path=path_value, max_width=max_width, max_height=max_height)
                return Image(path_value, width=width, height=height)
            except Exception:
                continue

    return Paragraph('', ParagraphStyle('EmptyLogo', fontSize=1))


def _build_letterhead_table(block, style_text, style_h2):
    institution = (block.get('institucion') or '-').upper()
    career = block.get('carrera') or '-'
    subject = block.get('materia') or '-'
    professor = block.get('profesor') or '-'
    exam_type = block.get('tipo_examen') or 'Examen'
    year = block.get('anio') or '-'

    center_style = ParagraphStyle('LetterCenter', parent=style_h2, alignment=1, spaceBefore=0, spaceAfter=0)
    meta_style = ParagraphStyle('LetterMeta', parent=style_text, spaceBefore=0, spaceAfter=0)
    right_style = ParagraphStyle('LetterYear', parent=style_text, alignment=1, spaceBefore=0, spaceAfter=0)

    meta_html = (
        f"<b>Carrera:</b> {career} &nbsp;&nbsp;&nbsp; <b>Profesor:</b> {professor}<br/>"
        f"<b>Materia:</b> {subject} &nbsp;&nbsp;&nbsp; <b>{exam_type}</b>"
    )

    data = [
        [_build_logo_flowable(block), Paragraph(institution, center_style), Paragraph(f"Año<br/>{year}", right_style)],
        ['', Paragraph(meta_html, meta_style), ''],
    ]
    table = Table(data, colWidths=[2.1 * cm, None, 2.3 * cm], hAlign='LEFT')
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#444444')),
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (2, 0), (2, 1)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 1), 'CENTER'),
        ('ALIGN', (2, 0), (2, 1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return table


def _build_student_data_table(block, style_text, style_h2):
    exam_type = block.get('tipo_examen_mayusculas') or (block.get('tipo_examen') or 'EXAMEN').upper()
    fecha = block.get('fecha') or ''
    label_style = ParagraphStyle('StudentLabel', parent=style_text, alignment=0)
    value_style = ParagraphStyle('StudentValue', parent=style_text, alignment=0)
    exam_style = ParagraphStyle('StudentExamType', parent=style_h2, alignment=1)

    data = [
        [Paragraph('<b>Nombre</b>', label_style), Paragraph('', value_style), Paragraph('<b>Apellido</b>', label_style), Paragraph('', value_style)],
        [Paragraph('<b>Fecha</b>', label_style), Paragraph(fecha, value_style), Paragraph(exam_type, exam_style), ''],
    ]
    table = Table(data, colWidths=[2.4 * cm, None, 2.4 * cm, None], hAlign='LEFT')
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#444444')),
        ('SPAN', (2, 1), (3, 1)),
        ('BACKGROUND', (0, 0), (0, 1), colors.HexColor('#f6f6f6')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#f6f6f6')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return table


def _fit_logo_size(*, img_bytes=None, path=None, max_width=1.6 * cm, max_height=1.2 * cm):
    try:
        if img_bytes is not None:
            image = PILImage.open(io.BytesIO(img_bytes))
        else:
            image = PILImage.open(path)
        original_width, original_height = image.size
        image.close()
        if not original_width or not original_height:
            return max_width, max_height

        scale = min(max_width / float(original_width), max_height / float(original_height), 1.0)
        return original_width * scale, original_height * scale
    except Exception:
        return max_width, max_height
