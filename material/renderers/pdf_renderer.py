import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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
        label = item.get('label') or f'Version {idx + 1}'
        style_text, style_title, style_h2 = _build_styles(formato)
        flow.append(Paragraph(label, style_title))
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

        if tipo == 'encabezado':
            for line in [
                block.get('institucion', ''),
                ' - '.join([v for v in [block.get('facultad', ''), block.get('carrera', '')] if v]),
                block.get('materia', ''),
            ]:
                if line:
                    centered = ParagraphStyle('Centered', parent=style_text, alignment=1)
                    flow.append(Paragraph(line, centered))
            meta = []
            if block.get('profesor'):
                meta.append(f"Profesor/a: {block['profesor']}")
            if block.get('fecha'):
                meta.append(f"Fecha: {block['fecha']}")
            if block.get('duracion_minutos'):
                meta.append(f"Duracion: {block['duracion_minutos']} min")
            if meta:
                flow.append(Spacer(1, 4))
                flow.append(Paragraph(' | '.join(meta), style_text))
            flow.append(Spacer(1, 8))

        elif tipo == 'titulo' and block.get('texto'):
            flow.append(Paragraph(block['texto'], style_title))

        elif tipo == 'instrucciones' and block.get('texto'):
            flow.append(Paragraph('Instrucciones generales', style_h2))
            flow.append(Paragraph(block['texto'].replace('\n', '<br/>'), style_text))

        elif tipo == 'lista_outcomes' and block.get('items'):
            flow.append(Paragraph('Resultados de aprendizaje evaluados', style_h2))
            for item in block['items']:
                flow.append(Paragraph(f"• {item}", style_text))

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
