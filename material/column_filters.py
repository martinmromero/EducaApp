"""
column_filters.py

Motor generico y reutilizable para filtros por columna estilo Excel
(multi-seleccion, en cascada) sobre listados con tabla. Usado hoy por
las plantillas de examen (material/views.py) y por "Mis examenes";
pensado para sumarse a cualquier otro listado sin duplicar logica.

Uso tipico en una vista:

    FIELDS = [
        ColumnFilterField('subject', 'Materia', value_field='subject_id', label_field='subject__name'),
        ColumnFilterField('year', 'Año', value_field='year'),
    ]

    selected_filters = get_selected_filters(request, FIELDS)
    filter_options = get_filter_options(base_qs, FIELDS, selected_filters)
    qs = apply_column_filters(request, base_qs, FIELDS).order_by(...)
    context = {
        'filter_options': filter_options,
        'selected_filters': selected_filters,
        'active_filter_count': get_active_filter_count(selected_filters),
        'filter_querystring': get_filter_querystring(request),
        'filter_columns': [{'field': f.name, 'label': f.label} for f in FIELDS],
    }

En el template, cada columna incluye:

    {% include 'material/components/_column_filter_dropdown.html' with
        field='subject' label='Materia' options=filter_options.subject
        selected=selected_filters.subject prefix='d' %}

y una sola vez por pagina:

    {% include 'material/components/_column_filters_assets.html' %}
    {% include 'material/components/_column_filters_offcanvas.html' with columns=filter_columns %}

con un <form method="get" id="templateFiltersForm"> vacio en algun lugar de la
pagina (los checkboxes se asocian via el atributo form="templateFiltersForm",
asi no hace falta anidarlos dentro de otro <form> ya existente, p.ej. el de
borrado multiple).
"""


class ColumnFilterField:
    """Describe una columna filtrable.

    - name: nombre del parametro en el querystring (?name=valor).
    - label: texto mostrado en el dropdown/acordeon.
    - value_field: campo (o expresion tipo 'created_at__year') que identifica
      cada valor distinto. Por defecto, `f'{name}_id'` si hay label_field(s)
      (asumiendo FK), o `name` si no.
    - lookup: lookup ORM usado para filtrar, p.ej. 'subject_id__in'.
      Por defecto `f'{value_field}__in'`.
    - label_field: campo relacionado para el texto mostrado (p.ej.
      'subject__name'), cuando el valor es el id de una FK.
    - label_fields: lista de campos a combinar para el texto (p.ej. nombre y
      apellido de un profesor). Tiene prioridad sobre label_field.
    - choices: lista estatica [(valor, etiqueta), ...] para campos tipo
      choices (CharField). Si se da, solo se muestran los valores que
      realmente aparecen en los datos (cascada), con su etiqueta mapeada.
    """

    def __init__(
        self,
        name,
        label,
        *,
        value_field=None,
        lookup=None,
        label_field=None,
        label_fields=None,
        choices=None,
    ):
        self.name = name
        self.label = label
        self.label_field = label_field
        self.label_fields = label_fields
        self.choices = choices
        self.value_field = value_field or (f'{name}_id' if (label_field or label_fields) else name)
        self.lookup = lookup or f'{self.value_field}__in'


def get_selected_filters(request, fields):
    """dict field.name -> set(valores) leidos del querystring."""
    return {f.name: set(request.GET.getlist(f.name)) for f in fields}


def get_active_filter_count(selected_filters):
    return sum(len(values) for values in selected_filters.values())


def get_filter_querystring(request):
    """Querystring con los filtros activos, sin 'page' (para links de paginacion)."""
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()


def apply_column_filters(request, qs, fields):
    """Aplica los filtros por columna (multi-seleccion) recibidos por querystring."""
    for f in fields:
        values = request.GET.getlist(f.name)
        if values:
            qs = qs.filter(**{f.lookup: values})
    return qs


def _scoped_querysets(querysets, fields, selected_filters, exclude_field):
    """Devuelve las querysets con todos los filtros activos aplicados,
    excepto el de `exclude_field` (para que una columna no se autoexcluya)."""
    scoped = []
    for qs in querysets:
        for f in fields:
            if f.name == exclude_field:
                continue
            values = selected_filters.get(f.name)
            if values:
                qs = qs.filter(**{f.lookup: list(values)})
        scoped.append(qs)
    return scoped


def _field_options(scoped_querysets, field):
    if field.choices is not None:
        present = set()
        for qs in scoped_querysets:
            qs = qs.exclude(**{f'{field.value_field}__isnull': True})
            try:
                # Descarta '' ademas de NULL para choices de texto (p.ej.
                # exam_type). En choices numericos (p.ej. bloom_level,
                # IntegerField) este exclude no aplica -- Django no puede
                # preparar '' como valor de comparacion -- asi que se ignora.
                qs = qs.exclude(**{field.value_field: ''})
            except (ValueError, TypeError):
                pass
            present.update(qs.values_list(field.value_field, flat=True).distinct())
        labels = dict(field.choices)
        return sorted(
            # 'value' se castea a str: los filtros seleccionados llegan como
            # strings desde el querystring (request.GET.getlist), y choices
            # numericos (p.ej. bloom_level, IntegerField) devolverian ints
            # de la DB que nunca matchean contra ese set de strings.
            ({'value': str(v), 'label': labels.get(v, v)} for v in present),
            key=lambda o: o['label'],
        )

    value_keys = [field.value_field] + (field.label_fields or ([field.label_field] if field.label_field else []))
    seen = {}
    for qs in scoped_querysets:
        rows = qs.exclude(**{f'{field.value_field}__isnull': True}).values(*value_keys).distinct()
        for row in rows:
            value = str(row[field.value_field])
            if value in seen:
                continue
            if field.label_fields:
                label = ' '.join(str(row[lf]) for lf in field.label_fields if row.get(lf)).strip()
            elif field.label_field:
                label = (row.get(field.label_field) or '').strip()
            else:
                label = str(row[field.value_field])
            seen[value] = label or f"{field.label} #{value}"
    return sorted(({'value': v, 'label': l} for v, l in seen.items()), key=lambda o: o['label'])


def get_filter_options(base_qs_or_list, fields, selected_filters):
    """Calcula, para cada columna, los valores distintos disponibles EN CASCADA:
    solo se consideran las filas que ya cumplen los filtros activos en las
    DEMAS columnas (nunca el propio, para no autoexcluirse).

    `base_qs_or_list` puede ser una unica QuerySet o una lista de QuerySets
    (por ejemplo cuando un listado combina mas de un modelo, como examenes
    individuales + lotes en "Mis examenes"); en ese caso las opciones son la
    union de lo que aparece en cada una.
    """
    querysets = base_qs_or_list if isinstance(base_qs_or_list, (list, tuple)) else [base_qs_or_list]
    options = {}
    for field in fields:
        scoped = _scoped_querysets(querysets, fields, selected_filters, exclude_field=field.name)
        options[field.name] = _field_options(scoped, field)
    return options
