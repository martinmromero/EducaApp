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

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_POST

from .models import Profile

# Líneas que puede ocupar el texto largo de un listado. 0 = completo.
LINE_OPTIONS = (1, 2, 3, 0)


def _col(key, label, default=True):
    return {'key': key, 'label': label, 'default': default}


# Cada listado declara sus columnas en el orden por defecto. 'default' dice si
# la columna se ve mientras el usuario no haya elegido nada. Las columnas
# fijas (casilla de selección y Acciones) no entran acá: siempre quedan en los
# extremos. 'text_column' es la columna de texto largo (la que se recorta por
# líneas) y 'default_lines' cuántas líneas muestra por defecto.
LIST_REGISTRY = {
    'preguntas': {
        'columns': [
            _col('materia', 'Materia'),
            _col('topico', 'Tópico'),
            _col('subtopico', 'Sub-tópico'),
            _col('pregunta', 'Pregunta'),
            _col('bloom', 'Bloom'),
            _col('estado', 'Estado IA'),
            _col('origen', 'Origen'),
            _col('tipo', 'Tipo de pregunta', default=False),
            _col('creada', 'Creada', default=False),
        ],
        'text_column': 'pregunta',
        'default_lines': 3,
    },
    'mis_examenes': {
        'columns': [
            _col('nombre', 'Nombre'),
            _col('materia', 'Materia'),
            _col('tipo', 'Tipo'),
            _col('creado', 'Creado'),
        ],
        'text_column': None,
        'default_lines': 0,
    },
    'plantillas': {
        'columns': [
            _col('nombre', 'Nombre'),
            _col('institucion', 'Institución'),
            _col('facultad', 'Facultad'),
            _col('carrera', 'Carrera'),
            _col('materia', 'Materia'),
            _col('docente', 'Docente'),
            _col('anio', 'Año'),
            _col('creada', 'Creada', default=False),
        ],
        'text_column': None,
        'default_lines': 0,
    },
    'orales': {
        'columns': [
            _col('nombre', 'Nombre'),
            _col('materia', 'Materia'),
            _col('grupos', 'Grupos'),
            _col('est_grupo', 'Estudiantes por grupo'),
            _col('preg_est', 'Preguntas por estudiante'),
            _col('total', 'Total de estudiantes'),
            _col('creado', 'Creado'),
        ],
        'text_column': None,
        'default_lines': 0,
    },
    'instituciones': {
        'columns': [
            _col('nombre', 'Nombre'),
            _col('logo', 'Logo'),
            _col('sedes', 'Sedes'),
            _col('facultades', 'Facultades'),
        ],
        'text_column': None,
        'default_lines': 0,
    },
    'materias': {
        'columns': [
            _col('nombre', 'Nombre'),
            _col('resultados', 'Resultados de aprendizaje'),
        ],
        'text_column': 'resultados',
        'default_lines': 0,
    },
    'carreras': {
        'columns': [
            _col('nombre', 'Nombre'),
            _col('facultades', 'Facultades'),
            _col('campus', 'Campus'),
            _col('materias', 'Materias'),
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

    return {
        'key': list_key,
        'columns': [
            {'key': k, 'label': by_key[k]['label'], 'visible': k in visible}
            for k in order
        ],
        'text_column': spec['text_column'],
        'lines': lines,
        'line_options': list(LINE_OPTIONS) if spec['text_column'] else [],
        # CSS que oculta de entrada las columnas apagadas, para que no se
        # vean un instante antes de que corra list_columns.js. Las claves
        # vienen del registro (nunca del usuario), así que es seguro.
        'hidden_css': ''.join(
            '.lc-table [data-col="%s"]{display:none}' % k for k in order if k not in visible
        ),
    }


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
