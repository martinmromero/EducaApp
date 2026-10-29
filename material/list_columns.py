"""
Vista configurable de los listados: cada usuario elige qué columnas ver, en
qué orden y cuántas líneas ocupa el texto largo, por separado para cada
listado.

El servidor solo guarda y valida la preferencia (Profile.list_view_prefs);
las tablas siguen armándose en los templates de siempre, con un
data-col="<clave>" en cada <th>/<td>, y static/js/list_columns.js reordena y
oculta las celdas. Para sumar un listado: registrarlo en LIST_REGISTRY, marcar
las celdas con data-col, y usar los partials components/_list_columns_*.html
(ver questions/lista_preguntas.html como ejemplo).
"""
import json
import unicodedata

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Case, CharField, Count, F, Min, Value, When
from django.db.models.functions import Coalesce, Lower, NullIf
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_POST

from .models import Profile, Question

# Líneas que puede ocupar el texto largo de un listado. 0 = completo.
LINE_OPTIONS = (1, 2, 3, 0)

# Ancho (en píxeles) que se puede darle a una columna arrastrando el borde de su encabezado.
MIN_WIDTH, MAX_WIDTH = 48, 1500


def _col(key, label, default=True, sort=None):
    """`sort` dice cómo se ordena el listado por esta columna (ver
    sort_queryset / sort_items): None = no se puede ordenar; True = la vista
    arma ella misma las claves (listados que se juntan en memoria); o bien una
    expresión / lista de expresiones del ORM, o una función request -> eso."""
    return {'key': key, 'label': label, 'default': default, 'sort': sort}


def _ci(field):
    """Texto sin distinguir mayúsculas, para que "álgebra" y "Álgebra" queden juntas."""
    return Lower(field)


def _first(field):
    """Un valor por fila en relaciones muchos-a-muchos (la materia con varias
    carreras no se repite): el primero por orden alfabético."""
    return Min(Lower(field))


def _label_order(field, choices):
    """Ordena por el texto visible de un campo con opciones, no por su valor interno."""
    return Case(
        *[When(**{field: value}, then=Value(str(label).lower())) for value, label in choices],
        default=Value(''), output_field=CharField(),
    )


def _snapshot_or(snapshot_field, related_field):
    """Plantillas: se muestra el nombre guardado al crearlas y, si no hay, el de la relación."""
    return Lower(Coalesce(NullIf(snapshot_field, Value('')), related_field))


def _mine_first(user_field):
    """Origen: lo propio primero (asc) y después lo compartido, por nombre de quien lo compartió."""
    def build(request):
        return (
            Case(When(**{user_field: request.user.pk}, then=Value(0)), default=Value(1)),
            Lower(user_field.replace('_id', '__username')),
        )
    return build


# Cada listado declara sus columnas en el orden por defecto. 'default' dice si
# la columna se ve mientras el usuario no haya elegido nada. Las columnas
# fijas (casilla de selección y Acciones) no entran acá: siempre quedan en los
# extremos. 'text_column' es la columna de texto largo (la que se recorta por
# líneas) y 'default_lines' cuántas líneas muestra por defecto.
LIST_REGISTRY = {
    'preguntas': {
        'columns': [
            _col('materia', 'Materia', sort=_first('subjects__name')),
            _col('topico', 'Tópico', sort=_ci('topic__name')),
            _col('subtopico', 'Sub-tópico', sort=_ci('subtopic__name')),
            _col('pregunta', 'Pregunta', sort=_ci('question_text')),
            _col('bloom', 'Bloom', sort='bloom_level'),
            # Manual, sin revisar, aprobada, rechazada.
            _col('estado', 'Estado IA', sort=Case(
                When(generated_by_ai=False, then=Value(0)),
                When(ai_approved__isnull=True, then=Value(1)),
                When(ai_approved=True, then=Value(2)),
                default=Value(3),
            )),
            _col('origen', 'Origen', sort=_mine_first('user_id')),
            _col('tipo', 'Tipo de pregunta', default=False,
                 sort=_label_order('question_type', Question.QUESTION_TYPE_CHOICES)),
            _col('creada', 'Creada', default=False, sort='created_at'),
        ],
        'text_column': 'pregunta',
        'default_lines': 3,
    },
    'mis_examenes': {
        'columns': [
            _col('nombre', 'Nombre', sort=True),
            _col('materia', 'Materia', sort=True),
            _col('tipo', 'Tipo', sort=True),
            _col('creado', 'Creado', sort=True),
        ],
        'text_column': None,
        'default_lines': 0,
    },
    'plantillas': {
        'columns': [
            _col('nombre', 'Nombre', sort=_ci('name')),
            _col('institucion', 'Institución', sort=_snapshot_or('institution_name_snapshot', 'institution__name')),
            _col('facultad', 'Facultad', sort=_snapshot_or('faculty_name_snapshot', 'faculty__name')),
            _col('carrera', 'Carrera', sort=_snapshot_or('career_name_snapshot', 'career__name')),
            _col('materia', 'Materia', sort=_snapshot_or('subject_name_snapshot', 'subject__name')),
            _col('docente', 'Docente', sort=(_ci('professor__first_name'), _ci('professor__last_name'))),
            _col('anio', 'Año', sort='year'),
            _col('creada', 'Creada', default=False, sort='created_at'),
        ],
        'text_column': None,
        'default_lines': 0,
    },
    'orales': {
        'columns': [
            _col('nombre', 'Nombre', sort=_ci('name')),
            _col('materia', 'Materia', sort=_ci('subject__name')),
            _col('grupos', 'Grupos', sort='num_groups'),
            _col('est_grupo', 'Estudiantes por grupo', sort='students_per_group'),
            _col('preg_est', 'Preguntas por estudiante', sort='questions_per_student'),
            _col('total', 'Total de estudiantes', sort=F('num_groups') * F('students_per_group')),
            _col('creado', 'Creado', sort='created_at'),
        ],
        'text_column': None,
        'default_lines': 0,
    },
    'instituciones': {
        'columns': [
            _col('nombre', 'Nombre', sort=_ci('name')),
            _col('logo', 'Logo'),
            _col('sedes', 'Sedes', sort=_first('campusv2_set__name')),
            _col('facultades', 'Facultades', sort=_first('facultyv2_set__name')),
        ],
        'text_column': None,
        'default_lines': 0,
    },
    'materias': {
        'columns': [
            _col('nombre', 'Nombre', sort=_ci('name')),
            _col('carreras', 'Carrera', sort=_first('careers__name')),
            _col('origen', 'Origen', sort=Case(When(es_catalogo_institucional=True, then=Value(0)), default=Value(1))),
            _col('resultados', 'Resultados de aprendizaje'),
        ],
        'text_column': 'resultados',
        'default_lines': 0,
    },
    'carreras': {
        'columns': [
            _col('nombre', 'Nombre', sort=_ci('name')),
            _col('facultades', 'Facultades', sort=_first('faculties__name')),
            _col('campus', 'Campus', sort=_first('campus__name')),
            _col('materias', 'Materias', sort=Count('subjects', distinct=True)),
        ],
        'text_column': None,
        'default_lines': 0,
    },
    'favoritos': {
        'columns': [
            _col('tipo', 'Tipo', sort=True),
            _col('nombre', 'Nombre', sort=True),
            _col('detalle', 'Detalle', sort=True),
            _col('favoriteado', 'Favoriteado', sort=True),
        ],
        'text_column': None,
        'default_lines': 0,
    },
    'rubricas': {
        'columns': [
            _col('titulo', 'Título', sort=_ci('title')),
            _col('origen', 'Origen', sort=_mine_first('created_by_id')),
            _col('niveles', 'Niveles', sort='level_count'),
            _col('criterios', 'Criterios', sort='criterion_count'),
            _col('modificada', 'Modificada', sort='updated_at'),
        ],
        'text_column': None,
        'default_lines': 0,
    },
    'formatos': {
        'columns': [
            _col('nombre', 'Nombre', sort=_ci('nombre')),
            _col('alcance', 'Alcance', sort=Case(
                When(user__isnull=False, then=Value('usuario')),
                When(institution__isnull=False, then=Lower('institution__name')),
                default=Value('global'), output_field=CharField(),
            )),
            _col('fuente', 'Fuente', sort=_ci('fuente')),
            _col('tamano', 'Tamaño', sort='tamano_fuente'),
            _col('predeterminado', 'Predeterminado', sort='es_default'),
        ],
        'text_column': None,
        'default_lines': 0,
    },
    'contenidos': {
        'columns': [
            _col('titulo', 'Título', sort=_ci('title')),
            _col('archivo', 'Archivo', sort=_ci('file')),
            _col('fecha', 'Fecha de subida', sort='uploaded_at'),
            _col('estado', 'Estado del archivo'),
        ],
        'text_column': None,
        'default_lines': 0,
    },
    'espacio_personal': {
        'columns': [
            _col('tipo', 'Tipo', sort=True),
            _col('nombre', 'Nombre', sort=True),
        ],
        'text_column': None,
        'default_lines': 0,
    },
    'usuarios': {
        'columns': [
            _col('id', 'ID', default=False, sort='id'),
            _col('usuario', 'Nombre de usuario', sort=_ci('username')),
            _col('nombre', 'Nombre', sort=_ci('first_name')),
            _col('apellido', 'Apellido', sort=_ci('last_name')),
            _col('email', 'Email', sort=_ci('email')),
            _col('rol', 'Rol', sort=_label_order('profile__role', Profile.ROLE_CHOICES)),
            _col('estado', 'Estado', sort='is_active'),
            _col('ultima_conexion', 'Última conexión', sort='last_login'),
            _col('registro', 'Fecha de registro', default=False, sort='date_joined'),
            _col('area_pruebas', 'Área de Pruebas', sort=Case(
                When(training_link__isnull=False, then=Value(0)), default=Value(1))),
        ],
        'text_column': None,
        'default_lines': 0,
    },
}


def _registry_keys(list_key):
    return [c['key'] for c in LIST_REGISTRY[list_key]['columns']]


def resolve_config(profile, list_key):
    """Configuración efectiva de un listado para un usuario: lo que guardó,
    completado con los defaults. Tolera claves que ya no existen en el
    registro y columnas nuevas que el usuario todavía no vio (quedan al
    final con su visibilidad por defecto)."""
    spec = LIST_REGISTRY[list_key]
    columns = spec['columns']
    by_key = {c['key']: c for c in columns}
    saved = {}
    if profile is not None:
        raw = getattr(profile, 'list_view_prefs', None) or {}
        saved = raw.get(list_key) or {}
        if not isinstance(saved, dict):
            saved = {}

    saved_order = [k for k in saved.get('order', []) if k in by_key]
    order = list(dict.fromkeys(saved_order))
    order += [c['key'] for c in columns if c['key'] not in order]

    saved_visible = saved.get('visible')
    if isinstance(saved_visible, list) and saved_order:
        # Una columna que el usuario nunca vio (no estaba en su 'order')
        # toma el valor por defecto en vez de quedar oculta o forzada.
        known = set(saved_order)
        visible = {k for k in saved_visible if k in by_key}
        visible |= {k for k in by_key if k not in known and by_key[k]['default']}
    else:
        visible = {c['key'] for c in columns if c['default']}
    if not visible:
        visible = {c['key'] for c in columns if c['default']} or {columns[0]['key']}

    lines = saved.get('lines', spec['default_lines'])
    if lines not in LINE_OPTIONS:
        lines = spec['default_lines']

    widths = {}
    saved_widths = saved.get('widths')
    if isinstance(saved_widths, dict):
        for k, v in saved_widths.items():
            if k in by_key and isinstance(v, int) and not isinstance(v, bool) and MIN_WIDTH <= v <= MAX_WIDTH:
                widths[k] = v

    return {
        'key': list_key,
        'columns': [
            {'key': k, 'label': by_key[k]['label'], 'visible': k in visible,
             'sortable': bool(by_key[k]['sort'])}
            for k in order
        ],
        'text_column': spec['text_column'],
        'lines': lines,
        'widths': widths,
        'line_options': list(LINE_OPTIONS) if spec['text_column'] else [],
        # CSS que oculta de entrada las columnas apagadas, para que no se
        # vean un instante antes de que corra list_columns.js. Las claves
        # vienen del registro (nunca del usuario), así que es seguro.
        'hidden_css': ''.join(
            '.lc-table [data-col="%s"]{display:none}' % k for k in order if k not in visible
        ),
    }


# Parámetros de la URL que eligen el orden del listado: ?sort=<columna>&dir=asc|desc.
SORT_PARAM, DIR_PARAM = 'sort', 'dir'


def get_sort(request, list_key):
    """(columna, 'asc'|'desc') pedidos en la URL, o (None, None) si no hay
    pedido o la columna no existe / no se puede ordenar en este listado.
    Lo que llega de la URL solo se usa como clave del registro, nunca como
    nombre de campo."""
    key = request.GET.get(SORT_PARAM)
    column = next((c for c in LIST_REGISTRY[list_key]['columns'] if c['key'] == key), None)
    if column is None or not column['sort']:
        return None, None
    return key, 'desc' if request.GET.get(DIR_PARAM) == 'desc' else 'asc'


def sort_queryset(request, list_key, queryset):
    """Aplica al queryset el orden pedido en la URL; sin pedido lo devuelve
    como vino (el orden por defecto de cada listado). Llamarlo recién al final,
    después de filtrar y de calcular conteos, y antes de paginar. Desempata por
    pk para que la paginación sea estable."""
    key, direction = get_sort(request, list_key)
    if key is None:
        return queryset
    spec = next(c for c in LIST_REGISTRY[list_key]['columns'] if c['key'] == key)['sort']
    if spec is True:
        return queryset
    if callable(spec):
        spec = spec(request)
    if not isinstance(spec, (list, tuple)):
        spec = (spec,)
    annotations, order = {}, []
    for i, expr in enumerate(spec):
        if isinstance(expr, str):
            expr = F(expr)
        if getattr(expr, 'contains_aggregate', False):
            # Las agregaciones (mínimo, cuenta) se anotan y se ordena por el alias.
            alias = '_sort_%s_%d' % (key, i)
            annotations[alias] = expr
            expr = F(alias)
        order.append(expr.desc(nulls_last=True) if direction == 'desc' else expr.asc(nulls_last=True))
    if annotations:
        queryset = queryset.annotate(**annotations)
    return queryset.order_by(*order, 'pk')


def text_key(value):
    """Clave para ordenar texto sin distinguir mayúsculas ni tildes."""
    decomposed = unicodedata.normalize('NFD', str(value or '').casefold())
    return ''.join(ch for ch in decomposed if not unicodedata.combining(ch))


def sort_items(request, list_key, items, getters):
    """Igual que sort_queryset pero para listados que se arman en memoria.
    `getters` asocia cada columna con una función item -> valor comparable
    (None o '' = vacío). Los vacíos quedan siempre al final."""
    key, direction = get_sort(request, list_key)
    if key is None or key not in getters:
        return items
    keyed = [(getters[key](item), item) for item in items]
    present = [(v, item) for v, item in keyed if v is not None and v != '']
    absent = [item for v, item in keyed if v is None or v == '']
    present.sort(key=lambda pair: pair[0], reverse=direction == 'desc')
    return [item for _v, item in present] + absent


def _clean_keys(value, valid, field):
    if not isinstance(value, list) or not all(isinstance(k, str) for k in value):
        raise ValueError('"%s" tiene que ser una lista de columnas' % field)
    unknown = [k for k in value if k not in valid]
    if unknown:
        raise ValueError('Columna desconocida en "%s": %s' % (field, unknown[0]))
    return list(dict.fromkeys(value))


def sanitize(list_key, payload):
    """Valida lo que manda el navegador y devuelve el dict a guardar.
    Levanta ValueError con un mensaje legible si algo no corresponde."""
    spec = LIST_REGISTRY[list_key]
    valid = set(_registry_keys(list_key))
    order = _clean_keys(payload.get('order', []), valid, 'order')
    visible = _clean_keys(payload.get('visible', []), valid, 'visible')
    if not visible:
        raise ValueError('Tiene que quedar al menos una columna visible')
    clean = {'order': order, 'visible': visible}
    widths = payload.get('widths', {})
    if not isinstance(widths, dict):
        raise ValueError('"widths" tiene que ser un diccionario de columnas')
    clean_widths = {}
    for k, v in widths.items():
        if k not in valid:
            raise ValueError('Columna desconocida en "widths": %s' % k)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not (MIN_WIDTH <= v <= MAX_WIDTH):
            raise ValueError('Ancho de columna no válido')
        clean_widths[k] = int(round(v))
    if clean_widths:
        clean['widths'] = clean_widths
    if spec['text_column']:
        lines = payload.get('lines', spec['default_lines'])
        if isinstance(lines, bool) or lines not in LINE_OPTIONS:
            raise ValueError('Cantidad de líneas no válida')
        clean['lines'] = lines
    return clean


@login_required
@require_POST
def save_list_view(request, list_key):
    """Guarda (o restablece, con {"reset": true}) la vista del usuario para un
    listado. Responde con la configuración efectiva resultante."""
    if list_key not in LIST_REGISTRY:
        raise Http404('Listado desconocido')
    try:
        payload = json.loads(request.body or b'{}')
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'Datos no válidos'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'ok': False, 'error': 'Datos no válidos'}, status=400)

    clean = None
    if not payload.get('reset'):
        try:
            clean = sanitize(list_key, payload)
        except ValueError as exc:
            return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    with transaction.atomic():
        profile, _ = Profile.objects.select_for_update().get_or_create(user=request.user)
        prefs = dict(profile.list_view_prefs or {})
        if clean is None:
            prefs.pop(list_key, None)
        else:
            prefs[list_key] = clean
        profile.list_view_prefs = prefs
        profile.save(update_fields=['list_view_prefs'])

    config = resolve_config(profile, list_key)
    config.pop('hidden_css')
    return JsonResponse({'ok': True, 'config': config})
