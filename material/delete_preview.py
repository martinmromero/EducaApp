"""
Vista previa de impacto de borrado, reusable para cualquier entidad.

Se apoya en `django.contrib.admin.utils.NestedObjects` -- el mismo Collector
interno que usa el propio /admin/ de Django para armar su pantalla de
confirmacion de borrado -- en vez de reimplementar a mano la logica de
cascada por modelo. Esto garantiza que el preview siempre coincide con lo
que Django realmente va a hacer (CASCADE / SET_NULL / PROTECT), sin importar
cuantos modelos nuevos se agreguen en el futuro.
"""
from collections import defaultdict

from django.contrib.admin.utils import NestedObjects
from django.db import router


def get_delete_preview(obj):
    """
    Calcula, SIN BORRAR NADA, el impacto de borrar `obj`.

    Devuelve un dict:
      - can_delete (bool): False si algo con on_delete=PROTECT/RESTRICT lo bloquea.
      - blocked_by: {"Plantillas De Examen": 2, ...} -- lo que impide el borrado.
      - to_delete: {"Sedes V2": 3, "Facultades": 2, ...} -- se borra en cascada.
      - to_nullify: {"Exámenes": 5, ...} -- sobreviven, pierden la referencia (SET_NULL/SET_DEFAULT).
    """
    collector = NestedObjects(using=router.db_for_write(obj.__class__))
    collector.collect([obj])

    to_delete = defaultdict(int)
    for model, instances in collector.model_objs.items():
        if model._meta.auto_created:
            # Tabla intermedia de un M2M (ej. Question<->Subject): es un
            # detalle de implementación, no una entidad que le importe al
            # usuario -- se omite del preview.
            continue
        count = len(instances - {obj}) if model is obj.__class__ else len(instances)
        if count:
            to_delete[model._meta.verbose_name_plural.title()] += count

    to_nullify = defaultdict(int)
    for (field, _value), instances_list in collector.field_updates.items():
        etiqueta = field.model._meta.verbose_name_plural.title()
        for instances in instances_list:
            count = len(instances)
            if count:
                to_nullify[etiqueta] += count

    blocked_by = defaultdict(int)
    for protected_obj in collector.protected:
        blocked_by[protected_obj.__class__._meta.verbose_name_plural.title()] += 1

    return {
        'can_delete': not collector.protected,
        'blocked_by': dict(blocked_by),
        'to_delete': dict(to_delete),
        'to_nullify': dict(to_nullify),
    }
