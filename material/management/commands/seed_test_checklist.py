"""
Semilla los ítems del checklist de testing (Modo Testing / panel de UAT) a
partir del Plan de Pruebas EducaApp acordado con el usuario. Idempotente:
borra y vuelve a crear todo, así que es seguro re-correrlo si cambia el
alcance del testing — no editar TestChecklistItem a mano vía shell/admin
para cambios que deban persistir, actualizar esta lista en su lugar.

target_url_name se guarda "pelado" (sin el prefijo de namespace) porque
algunos apuntan a material: (la inmensa mayoría) y otros al urlconf raíz
(login, password_reset_request) — la vista que resuelve el link intenta
"material:<name>" primero y cae a "<name>" si no existe ese namespace.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from material.models import TestChecklistItem

# (area_number, area_name, texto, target_url_name, admin_only, stage)
# Los primeros 3 ítems del área 01 pasan ANTES de que este panel exista para
# el tester (recién se activa una vez logueado y marcado is_tester) — se
# marcan en retrospectiva, apenas entra por primera vez. No hace falta
# ninguna pantalla previa al login: el texto ya deja claro que es "contá
# cómo te fue", no "hacé esto ahora".
#
# stage=None → aparece para cualquier tester sin importar la etapa asignada
# (áreas 01, 15 y 16 son transversales: alta, apariencia y administración).
# Las demás áreas quedan repartidas en 3 etapas de ~18-21 ítems cada una
# (contra los 74 totales) para que un solo tester no tenga que hacer todo el
# checklist de punta a punta — ver [[project_uat_testing_plan]].
ITEMS = [
    (1, "Alta y primer acceso", "Recordá cómo te fue creando la cuenta (signup abierto o por invitación) — contalo acá", "signup", False, None),
    (1, "Alta y primer acceso", "Recordá cómo te fue configurando la pregunta de seguridad — contalo acá", "security_question_setup", False, None),
    (1, "Alta y primer acceso", "Recordá cómo te fue con el asistente de bienvenida (onboarding): pasos, contenido demo, resumen final", "onboarding_v2_page", False, None),
    (1, "Alta y primer acceso", "Cerrar sesión, volver a entrar con usuario/contraseña, y volver a activar Modo Testing para seguir", "login", False, None),
    (1, "Alta y primer acceso", "Cerrar sesión y probar \"olvidé mi contraseña\" sobre tu propia cuenta — al volver a entrar, reactivá Modo Testing y contá cómo te fue", "password_reset_request", False, None),

    (2, "Generar preguntas con IA", "Subir un documento (PDF, DOCX o PPTX) y revisar la metadata extraída", "document_processor_dashboard", False, 1),
    (2, "Generar preguntas con IA", "Elegir páginas/diapositivas/párrafos específicos antes de generar", "document_processor_dashboard", False, 1),
    (2, "Generar preguntas con IA", "Generar en modo progresivo y en modo todas juntas", "document_processor_dashboard", False, 1),
    (2, "Generar preguntas con IA", "Revisar que cada pregunta traiga nivel de Bloom y fragmento de origen", "document_processor_dashboard", False, 1),
    (2, "Generar preguntas con IA", "Probar \"Incluir imágenes del documento\"", "document_processor_dashboard", False, 1),
    (2, "Generar preguntas con IA", "Aprobar, editar y descartar preguntas generadas; guardarlas al banco", "document_processor_dashboard", False, 1),

    (3, "Mis Contenidos", "Ver la lista de contenidos subidos", "mis_contenidos", False, 1),
    (3, "Mis Contenidos", "Eliminar un contenido y confirmar que desaparece de la lista", "mis_contenidos", False, 1),

    (4, "Banco de Preguntas", "Filtrar por materia, estado y nivel de Bloom", "lista_preguntas", False, 1),
    (4, "Banco de Preguntas", "Ver el detalle de una pregunta", "lista_preguntas", False, 1),
    (4, "Banco de Preguntas", "Editar una pregunta existente", "lista_preguntas", False, 1),
    (4, "Banco de Preguntas", "Eliminar una pregunta individual y varias a la vez", "lista_preguntas", False, 1),
    (4, "Banco de Preguntas", "Cargar una pregunta a mano con el formulario manual", "upload_questions", False, 1),
    (4, "Banco de Preguntas", "Descargar la plantilla CSV/TXT e importar preguntas en bloque", "upload_questions", False, 1),
    (4, "Banco de Preguntas", "Exportar el banco de preguntas", "lista_preguntas", False, 1),

    (5, "Mis Exámenes", "Crear un examen nuevo (\"Crear Examen\" / \"Nuevo Examen\" — no el asistente nuevo)", "create_exam", False, 2),
    (5, "Mis Exámenes", "Ver, editar y eliminar un examen existente", "mis_examenes", False, 2),
    (5, "Mis Exámenes", "Reemplazar una pregunta dentro de una versión del examen", "mis_examenes", False, 2),
    (5, "Mis Exámenes", "Exportar un examen a PDF", "mis_examenes", False, 2),
    (5, "Mis Exámenes", "Exportar un examen a DOCX", "mis_examenes", False, 2),
    (5, "Mis Exámenes", "Trabajar con un lote de varias versiones: renombrar, editar, eliminar", "mis_examenes", False, 2),
    (5, "Mis Exámenes", "Eliminar varios exámenes a la vez", "mis_examenes", False, 2),

    (6, "Cuestionarios Orales (Bolillero Digital)", "Crear un cuestionario oral — caso chico: 8 alumnos/2 preguntas/2 grupos", "create_oral_exam", False, 2),
    (6, "Cuestionarios Orales (Bolillero Digital)", "Crear un cuestionario oral — caso grande: 30 alumnos/3 preguntas/6 grupos", "create_oral_exam", False, 2),
    (6, "Cuestionarios Orales (Bolillero Digital)", "Revisar el panel de validación (preguntas/sub-tópicos disponibles, avisos)", "create_oral_exam", False, 2),
    (6, "Cuestionarios Orales (Bolillero Digital)", "Intercambiar/pedir otra pregunta durante la evaluación", "list_oral_exams", False, 2),
    (6, "Cuestionarios Orales (Bolillero Digital)", "Evaluar en tiempo real (Bien/Regular/Mal) y revisar la nota final automática", "list_oral_exams", False, 2),
    (6, "Cuestionarios Orales (Bolillero Digital)", "Eliminar un cuestionario y eliminar varios a la vez", "list_oral_exams", False, 2),

    (7, "Plantillas de Examen", "Crear una plantilla con logo institucional, resultados de aprendizaje y temas a evaluar", "create_exam_template", False, 2),
    (7, "Plantillas de Examen", "Editar y previsualizar una plantilla", "list_exam_templates", False, 2),
    (7, "Plantillas de Examen", "Generar un examen a partir de una plantilla", "list_exam_templates", False, 2),
    (7, "Plantillas de Examen", "Eliminar una plantilla", "list_exam_templates", False, 2),

    (8, "Rúbricas", "Crear una rúbrica (grilla de niveles × criterios)", "rubric_create", False, 2),
    (8, "Rúbricas", "Ver, editar y eliminar una rúbrica", "rubric_list", False, 2),
    (8, "Rúbricas", "Asociar una rúbrica a un examen existente", "rubric_list", False, 2),

    (9, "Formatos de Impresión", "Crear un formato (tamaño de papel, fuente, márgenes, color)", "formato_impresion_create", False, 3),
    (9, "Formatos de Impresión", "Marcarlo como predeterminado", "formato_impresion_list", False, 3),
    (9, "Formatos de Impresión", "Revisar la vista previa con zoom", "formato_impresion_list", False, 3),
    (9, "Formatos de Impresión", "Editar y eliminar un formato", "formato_impresion_list", False, 3),

    (10, "Mi Espacio Académico", "Crear una institución, con sus sedes y facultades en el mismo formulario", "create_institution_v2", False, 3),
    (10, "Mi Espacio Académico", "Editar una institución, marcarla favorita, subir/quitar logo, eliminarla", "institution_v2_list", False, 3),
    (10, "Mi Espacio Académico", "Crear una carrera y asociarla a facultades y materias", "career_create_simple", False, 3),
    (10, "Mi Espacio Académico", "Crear, editar y eliminar una materia", "subject_list", False, 3),
    (10, "Mi Espacio Académico", "Agregar/editar/eliminar resultados de aprendizaje de una materia", "subject_list", False, 3),
    (10, "Mi Espacio Académico", "Confirmar que los filtros en cascada (institución→sede→facultad→carrera→materia) funcionan", "institution_v2_list", False, 3),

    (11, "Grupos de Confianza", "Crear un grupo", "grupo_crear", False, 3),
    (11, "Grupos de Confianza", "Invitar a otro tester (usuario/email real)", "grupos_list", False, 3),
    (11, "Grupos de Confianza", "Aceptar una invitación pendiente desde la otra cuenta", "invitaciones_pendientes", False, 3),
    (11, "Grupos de Confianza", "Compartir una materia dentro del grupo", "grupos_list", False, 3),
    (11, "Grupos de Confianza", "Compartir una rúbrica dentro del grupo", "grupos_list", False, 3),

    (12, "Favoritos", "Marcar algo como favorito", "index", False, 3),
    (12, "Favoritos", "Ver la lista de favoritos (card en Inicio)", "favoritos_list", False, 3),
    (12, "Favoritos", "Quitar un favorito", "favoritos_list", False, 3),

    (13, "Proveedor de IA", "Cargar una clave propia (OpenAI / Anthropic / Google)", "ai_config", False, 3),
    (13, "Proveedor de IA", "Ver el estado y los modelos disponibles", "ai_config", False, 3),
    (13, "Proveedor de IA", "Eliminar la clave guardada con el botón nuevo y confirmar que vuelve a \"sin clave\"", "ai_config", False, 3),

    (14, "Taxonomía de Bloom", "Ver la pirámide y los verbos de cada nivel", "bloom_taxonomy", False, 1),
    (14, "Taxonomía de Bloom", "Ver el gráfico de distribución propia", "bloom_taxonomy", False, 1),
    (14, "Taxonomía de Bloom", "Revisar la tabla comparativa Bloom 1956 vs. Anderson & Krathwohl 2001", "bloom_taxonomy", False, 1),

    (15, "Apariencia", "Cambiar el tema/paleta visual desde el pie del menú", "", False, None),
    (15, "Apariencia", "Alternar modo claro/oscuro", "", False, None),
    (15, "Apariencia", "Revisar en modo oscuro al menos 3-4 pantallas usadas", "", False, None),
    (15, "Apariencia", "Probar en el celular/tablet, no solo en la computadora", "", False, None),

    (16, "Administración", "Gestión de usuarios: listar, crear, editar, bloquear/eliminar", "user_list", True, None),
    (16, "Administración", "Invitaciones: generar una y ver su estado", "mis_invitaciones", True, None),
    (16, "Administración", "Monitoreo Groq: confirmar que carga sin error", "groq_monitor_page", True, None),
    (16, "Administración", "Uso de Neon (DB): confirmar que carga sin error", "neon_usage_page", True, None),
    (16, "Administración", "Prompt de generación IA: revisar que se pueda ver/editar", "question_generation_prompt_config", True, None),
    (16, "Administración", "IA Institucional: configurar clave a nivel institución", "institution_ai_config", True, None),
]


class Command(BaseCommand):
    """
    Idempotente vía update_or_create, clave natural (area_number, text) — NO
    borra y recrea todo. Un TestResult ya cargado por un tester apunta al PK
    de un TestChecklistItem; si este comando corriera con delete-all en cada
    deploy (queda en el buildCommand de Render, se re-ejecuta en cada push
    durante toda la ronda de UAT) borraría en cascada los resultados ya
    cargados. Solo se eliminan los ítems cuya (area_number, text) ya no
    aparece en ITEMS — es decir, los que de verdad salieron de alcance.
    """
    help = 'Semilla (crea o actualiza, sin perder resultados ya cargados) los ítems del checklist de Modo Testing.'

    @transaction.atomic
    def handle(self, *args, **options):
        seen_keys = set()
        created, updated = 0, 0
        for idx, (area_number, area_name, text, url_name, admin_only, stage) in enumerate(ITEMS, start=1):
            seen_keys.add((area_number, text))
            obj, was_created = TestChecklistItem.objects.update_or_create(
                area_number=area_number,
                text=text,
                defaults={
                    'area_name': area_name,
                    'order': idx,
                    'target_url_name': url_name,
                    'admin_only': admin_only,
                    'stage': stage,
                },
            )
            created += was_created
            updated += not was_created

        # No hay lookup directo por tupla (area_number, text) en el ORM — se
        # filtra en Python, la tabla es chica (unas pocas decenas de filas).
        stale_ids = [
            item.id for item in TestChecklistItem.objects.all()
            if (item.area_number, item.text) not in seen_keys
        ]
        removed = len(stale_ids)
        if stale_ids:
            TestChecklistItem.objects.filter(id__in=stale_ids).delete()

        self.stdout.write(self.style.SUCCESS(
            f'Checklist de testing: {created} creados, {updated} actualizados, {removed} fuera de alcance eliminados.'
        ))
