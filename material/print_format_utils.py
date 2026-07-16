from django.db import transaction

from .models import FormatoImpresion, FormatoImpresionAsignado, UserInstitution


def get_user_institution_ids(user):
    return list(UserInstitution.objects.filter(user=user).values_list('institution_id', flat=True))


def get_visible_print_formats(user):
    institution_ids = get_user_institution_ids(user)
    return FormatoImpresion.objects.filter(
        user=user,
    ) | FormatoImpresion.objects.filter(
        institution_id__in=institution_ids,
    ) | FormatoImpresion.objects.filter(
        user__isnull=True,
        institution__isnull=True,
    )


def resolve_print_format_for_context(*, user=None, institution=None, institution_name=''):
    if user:
        formato = FormatoImpresion.objects.filter(user=user, es_default=True, institution__isnull=True).first()
        if formato:
            return formato

    if institution is not None:
        formato = FormatoImpresion.objects.filter(institution=institution, es_default=True, user__isnull=True).first()
        if formato:
            return formato

    if institution_name:
        formato = FormatoImpresion.objects.filter(institution__name__iexact=institution_name, es_default=True, user__isnull=True).first()
        if formato:
            return formato

    return FormatoImpresion.objects.filter(user__isnull=True, institution__isnull=True, es_default=True).first()


def clear_existing_default_for_scope(*, user=None, institution=None, exclude_id=None):
    qs = FormatoImpresion.objects.all()
    if user is not None:
        qs = qs.filter(user=user, institution__isnull=True)
    elif institution is not None:
        qs = qs.filter(institution=institution, user__isnull=True)
    else:
        qs = qs.filter(user__isnull=True, institution__isnull=True)

    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    qs.update(es_default=False)


def resolve_print_format_for_exam(exam, *, explicit_format=None):
    if hasattr(exam, 'formato_impresion_asignado'):
        return exam.formato_impresion_asignado
    if explicit_format is not None:
        return explicit_format
    return resolve_print_format_for_context(
        user=getattr(exam, 'created_by', None),
        institution_name=getattr(exam, 'institution_name', '') or '',
    )


def get_print_style_context(formato):
    fuente = getattr(formato, 'fuente', 'Arial') if formato else 'Arial'
    tamano_pt = getattr(formato, 'tamano_fuente', 11) if formato else 11
    interlineado = getattr(formato, 'interlineado', 1.15) if formato else 1.15
    color_titulo = getattr(formato, 'color_titulo', '') or '#111111'
    color_texto = getattr(formato, 'color_texto', '') or '#111111'
    margen_superior_cm = getattr(formato, 'margen_superior_cm', 2.00) if formato else 2.00
    margen_inferior_cm = getattr(formato, 'margen_inferior_cm', 2.00) if formato else 2.00
    margen_izquierdo_cm = getattr(formato, 'margen_izquierdo_cm', 2.50) if formato else 2.50
    margen_derecho_cm = getattr(formato, 'margen_derecho_cm', 2.00) if formato else 2.00
    base_px = round(float(tamano_pt) * 1.3333, 2)

    return {
        'font_family': fuente,
        'font_size_pt': f'{tamano_pt}pt',
        'line_height': interlineado,
        'title_color': color_titulo,
        'text_color': color_texto,
        'margin_top_cm': f'{margen_superior_cm}cm',
        'margin_bottom_cm': f'{margen_inferior_cm}cm',
        'margin_left_cm': f'{margen_izquierdo_cm}cm',
        'margin_right_cm': f'{margen_derecho_cm}cm',
        'base_px': f'{base_px}px',
        'h3_px': f'{round(base_px * 1.25, 2)}px',
        'list_px': f'{round(base_px * 1.0, 2)}px',
        'theme_px': f'{round(base_px * 1.35, 2)}px',
    }


@transaction.atomic
def assign_print_format_to_exam(exam, formato):
    assigned = getattr(exam, 'formato_impresion_asignado', None)
    if assigned:
        assigned.formato_base = formato
        assigned.nombre_snapshot = formato.nombre
        assigned.fuente = formato.fuente
        assigned.tamano_fuente = formato.tamano_fuente
        assigned.interlineado = formato.interlineado
        assigned.margen_superior_cm = formato.margen_superior_cm
        assigned.margen_inferior_cm = formato.margen_inferior_cm
        assigned.margen_izquierdo_cm = formato.margen_izquierdo_cm
        assigned.margen_derecho_cm = formato.margen_derecho_cm
        assigned.color_titulo = formato.color_titulo
        assigned.color_texto = formato.color_texto
        assigned.save()
        return assigned
    return FormatoImpresionAsignado.crear_desde_formato(exam, formato)


@transaction.atomic
def propagate_print_format_to_exams(formato, exam_ids):
    assigned_qs = FormatoImpresionAsignado.objects.filter(formato_base=formato, exam_id__in=exam_ids)
    updated = 0
    for assigned in assigned_qs:
        assigned.nombre_snapshot = formato.nombre
        assigned.fuente = formato.fuente
        assigned.tamano_fuente = formato.tamano_fuente
        assigned.interlineado = formato.interlineado
        assigned.margen_superior_cm = formato.margen_superior_cm
        assigned.margen_inferior_cm = formato.margen_inferior_cm
        assigned.margen_izquierdo_cm = formato.margen_izquierdo_cm
        assigned.margen_derecho_cm = formato.margen_derecho_cm
        assigned.color_titulo = formato.color_titulo
        assigned.color_texto = formato.color_texto
        assigned.save()
        updated += 1
    return updated