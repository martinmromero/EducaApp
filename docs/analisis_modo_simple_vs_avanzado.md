# Modo simple (asistentes) vs. modo avanzado (ABM) — análisis al 2026-10-05 (revisión 2)

Alcance: relevamiento del código (`material/urls.py`, `views.py`, templates, JS de los asistentes), de la
memoria del proyecto y, en esta segunda revisión, **prueba real en navegador** del Asistente completo con una
cuenta docente (no admin) creada para la ocasión y borrada al terminar. No se modificó código de la app.
Marcas: **[código]** leído hoy en el código · **[navegador]** comprobado hoy en el navegador ·
**[memoria]** viene de notas de sesiones anteriores y no se re-verificó.

---

## 0. Qué cambió desde la primera revisión

| Hecho | Detalle |
|---|---|
| El paso Examen embebido **ya está en `main`** | PR #6 (`660906c` + merge `7982613`): iframe `educaapp-embed-exam`, `embed.js`, `postMessage`, `view_url` en el guardado, `full_wizard_prefill_exam` eliminado, `tests_exam_embed.py` (8 tests) y una fila nueva en el checklist de UAT. Árbol de trabajo limpio salvo `docs/` y `media/`. |
| Tests | `manage.py check` limpio. Corridos módulo por módulo: `tests_qa_smoke` 4 · `tests_exam_embed` 8 · `tests_catalogo_qa` 83 · `tests_upload_wizard` 30 · `tests_xss` 6 · `tests_list_columns` 25 · `tests` 2 = **158 tests, todos OK** **[verificado]**. El bloqueo de "database test_educaapp is being accessed by other users" de ayer ya no aparece. Ningún test cubre los defectos D1–D4. |
| Recorrido completo probado en navegador | Institución → Facultad → Carrera → Materia nueva → Resultado de aprendizaje → pregunta cargada con el asistente embebido → Examen (iframe) → vista previa → "Editar" y vuelta → Guardar → pantalla final del host. **Funciona de punta a punta con una cuenta docente.** Detalle y hallazgos en la sección 2. |
| Sin probar | Generar con IA (no hay proveedor propio en la cuenta de prueba), carga por lote CSV/TXT, tema oscuro, dispositivo móvil real (solo emulación de 375 px), `retomar` entre sesiones. |

---

## 1. Inventario: qué tiene asistente y qué solo tiene ABM

Leyenda: ✅ existe · ◐ parcial · ❌ no existe · 🔒 solo admin

### 1.1 Catálogo académico

| Entidad | Asistente | ABM clásico | Quién puede en el ABM | Editar desde asistente | Observaciones |
|---|---|---|---|---|---|
| Institución | ✅ `create_institution_v2_wizard` (4 pasos, 🔒 admin) + ✅ paso 1 del Asistente completo (cualquier usuario → espacio personal) | crear / editar / detalle / logs / eliminar / favorito | crear = 🔒 admin; los demás, admin o dueño del borrador personal | ❌ | Logo, sedes y facultades solo se editan en el ABM. |
| Facultad | ✅ paso 2 del Asistente completo; ◐ dentro del wizard de institución | `edit_faculty_v2` (colgada de la institución) | admin / dueño | ❌ | No tiene lista propia. |
| Carrera | ✅ paso 3 del Asistente completo | `career_create_simple` 🔒 admin, `career_associations` (editar), eliminar, detalle | crear = 🔒 admin; para el resto: "Solicitar alta" | ❌ | **Un docente (no admin) solo puede crear carreras por el Asistente completo o "Solicitar alta".** |
| Materia | ✅ paso 4 del Asistente completo | `SubjectCreateView` 🔒 admin, `SubjectUpdateView` (admin o dueño personal), eliminar, detalle | igual que Carrera | ❌ | Igual: para un docente el asistente es el único camino directo. |
| Resultados de aprendizaje | ✅ paso 5 del Asistente completo | `LearningOutcome{List,Add,Edit,Delete}` colgados de `CareerSubject` | `_PuedeEditarRAMixin` | ❌ | Opcional en todo el recorrido. |
| Tópicos / subtópicos | ◐ alta inline dentro del asistente de preguntas (`add_topic`/`add_subtopic`) | **No hay ABM de tópicos** | — | — | Pendiente conocido y marcado PRIORIDAD ALTA en memoria: no se puede crear tópico desde la edición de materia sin filtrar entre carreras. Hoy se crean solo al cargar preguntas. |
| Solicitud de alta al catálogo | ◐ (el Asistente completo la genera de fondo) | `catalog_request_create`, "Mis agregados", bandeja admin | cualquiera / admin | — | Es el mecanismo detrás del espacio personal. |

### 1.2 Contenido y preguntas

| Entidad | Asistente | ABM clásico | Editar desde asistente | Observaciones |
|---|---|---|---|---|
| Contenido (documento fuente) | ❌ (se sube solo dentro de "Generar con IA") | `upload_contenido`, `mis_contenidos`, eliminar | ❌ | En el Asistente completo ya no hay paso de contenido (se fusionó con Preguntas). El form clásico sigue siendo el único alta "suelta". |
| Pregunta — carga manual | ✅ `upload_questions_wizard` (una o lote CSV/TXT, con vista previa) y embebido en el paso 6 | `upload_questions` (form + CSV) | ❌ | 30 tests propios. |
| Pregunta — generación con IA | ◐ `document_processor_dashboard` es un flujo por etapas (documento → capítulos → generar → revisar → guardar), **pero no es un asistente del framework** y pesa ~3.500 líneas | — | Revisión/edición dentro de la misma pantalla | Desde el Asistente completo se abre vía link (vuelve con `?retomar=1`). |
| Pregunta — ver/editar/eliminar/exportar | ❌ | `ver_pregunta`, `editar_pregunta`, `eliminar_pregunta`, `bulk`, `exportar_preguntas` | — | Es lo único razonable de dejar como "avanzado". |

### 1.3 Exámenes

| Entidad | Asistente | ABM clásico | Editar desde asistente | Observaciones |
|---|---|---|---|---|
| Examen escrito | ✅ `create_exam_wizard` (**8 pasos**: Plantilla, Materia, Tópicos y preguntas, Uno o varios temas, Docente y fecha, Institución y sede, Tipo y modalidad, Rúbricas; embebido en el Asistente completo arranca en el 3) y embebido en el paso 7 del Asistente completo | `create_exam` (formulario único), vista previa, guardar, lotes, exportar DOCX/PDF | ❌ **`editar_examen` / `editar_lote` redirigen al form clásico** (`create_exam?edit_exam_id=`) | La vista del wizard dice textualmente que no soporta retomar una edición. |
| Plantilla de examen | ✅ `create_exam_template_wizard` (4 pasos) | `create_exam_template` + `save_exam_template` (fetch) | ❌ (`edit_exam_template` clásico) | |
| Cuestionario oral | ✅ `create_oral_exam_wizard` (3 pasos) | `create_oral_exam` | ❌ | La pantalla de **evaluar** (`view_oral_exam`) no es asistente, pero es la "ejecución", no un ABM. **No está dentro del Asistente completo.** |
| Rúbrica | ❌ | `rubric_create/edit/view/delete` (grilla) | ❌ | El asistente de examen la enlaza en pestaña nueva (`target=_blank`). |
| Formato de impresión | ❌ | `formato_impresion_*` | ❌ | Se resuelve **solo** al armar el examen (`resolve_print_format_for_context`: del usuario → de la institución → global). No hace falta paso. |

### 1.4 Cuenta, compartir, administración

| Área | Asistente | Observaciones |
|---|---|---|
| Alta de cuenta | ◐ invitación por link (admin) / `signup` | `signup` usa `UserCreationForm` (solo usuario + clave). |
| Pregunta de seguridad, Mis datos | ❌ | Formularios chicos, no necesitan asistente. |
| Proveedor de IA (`ai_config`) | ◐ solo `onboarding_v2_connect_gemini` | **El Asistente completo no verifica ni guía la IA** antes de ofrecer "Generar con IA". El default de cada usuario es `ollama_local`, que en Render no existe y cae al fallback global compartido **[verificado en `ai_router._resolve_backend_for_user`]**; si no hay `GlobalAIConfig` activa con key, genera con Ollama inexistente y falla. |
| Grupos de confianza (crear / invitar / compartir ×4) | ❌ | Todo ABM. Es "avanzado" por naturaleza. |
| Favoritos, Espacio personal, Avisos de borrado | n/a | Listados. |
| Administración (usuarios, invitaciones, bandeja, carga masiva, Groq, Neon, prompt, IA institucional, resultados de testing) | n/a | Siempre avanzado/admin. |

### 1.5 Dos asistentes que se pisan

Hay **dos puertas de entrada de "asistente"** en Inicio y en el menú: "Asistente guiado" (`/comenzar/`, onboarding v2, 7 pasos + demo) y
"Asistente completo" (`/asistente-completo/`, 7 pasos). Hacen casi lo mismo con código distinto. Para alguien nuevo no hay forma de saber
cuál elegir — y la elección ya está hecha por el sistema: `OnboardingGateMiddleware` manda a todo usuario no-staff que entra a Inicio sin
`onboarding_completed` a `/comenzar/?first=1` (verificado en navegador; ver D1/D2 en la sección 2). Además el onboarding v2 tiene cosas que el completo no (nombre, conectar Gemini, ejemplo enlatado) y viceversa (espacio personal
con auditoría, precarga del examen, preguntas embebidas).

---

## 2. Hallazgos de la prueba en navegador (cuenta docente, 2026-10-05)

### 2.1 Lo que funciona **[navegador]**
- Pasos 1–4 con una cuenta no admin: se eligen institución, facultad y carrera del catálogo y se **crea una materia personal** sin tocar ningún ABM.
- Paso 5: se crea un resultado de aprendizaje para esa materia (queda vinculado a la carrera del catálogo).
- Paso 6: la advertencia de "saltear" aparece como modal; saltear con 0 preguntas lleva al bloqueo del paso 7 con el mensaje correcto y un botón de vuelta.
- Paso 6 → "Cargar a mano" → una pregunta (tipo, enunciado, tópico nuevo, revisión, guardado): el contador del host se actualiza ("1 pregunta disponible").
- Paso 7: el iframe carga con **materia, institución, facultad, carrera y RA ya precargados**, arranca en "Tópicos", y la vista previa y el guardado ocurren adentro. El "Editar" de la vista previa vuelve al paso 8 con todo lo cargado. "Guardar Examen" dispara `educaapp:exam-saved` y el host muestra la pantalla final con "Ver el examen" (`/examenes/102/`) y "Armar otro examen".

### 2.2 Defectos reales (ordenados por gravedad)

| # | Defecto | Evidencia | Arreglo sugerido |
|---|---|---|---|
| **D1** | **"Terminar" devuelve al asistente viejo.** Tras completar todo el Asistente completo (incluido el examen guardado), el botón "Terminar" lleva a Inicio y `OnboardingGateMiddleware` redirige a `/comenzar/?first=1` (pregunta "¿Cómo empezar?" + recorrido de 13 pasos), porque solo `onboarding_v2` marca `profile.onboarding_completed`. | **[navegador]** repetido tras el examen guardado. **[código]** `material/middleware.py:61-73`; la bandera solo se escribe en `views.py` ~8631 y ~8860 (onboarding). | Marcar `onboarding_completed=True` desde el Asistente completo (al primer paso guardado o en "Terminar"/"Salir"). |
| **D2** | **Primer ingreso de un usuario nuevo = el asistente viejo.** Pregunta de seguridad → `/comenzar/?first=1` → ventana "Bienvenido, 1 de 13" encima. El Asistente completo no es la puerta de entrada. | **[navegador]** + **[código]** `middleware.py`. | Cambiar el destino del gate a `/asistente-completo/` (o fusionar). Ver P0.2. |
| **D3** | **Callejón sin salida dentro del iframe.** `preview_exam` redirige a `create_exam` cuando la sesión no tiene datos (`views.py:92-93`) o cuando no se encontró ninguna pregunta (`views.py:283-288`). `create_exam` responde `X-Frame-Options: DENY`, así que dentro del iframe queda un **recuadro en blanco** sin ninguna salida (la barra inferior del host está oculta mientras el iframe está abierto). Pasa también si la sesión vence y el redirect va al login. | **[navegador]** reproducido: con la sesión sin datos, `/preview-exam/` termina en `/create-exam/` (DENY) y el iframe queda blanco. **[código]** `tests_exam_embed.py::test_otras_pantallas_siguen_sin_poder_enmarcarse` afirma justamente que `create_exam` es DENY. | (a) En modo embebido, redirigir a `create_exam_wizard?fw=1` en vez de `create_exam`; (b) que el host detecte "no llegó el aviso de carga" y muestre un botón "Volver"; (c) idem para el login. Ajustar el test. |
| **D4** | **El examen sale con 1 sola pregunta si no se completa "Preguntas por tema".** Con tópicos elegidos y ese campo vacío (opcional, placeholder "Ej: 10", sin explicación), el servidor usa `max(1, cantidad_de_tópicos)`. Con 1 tópico de 4 preguntas, el examen salió con **1 pregunta**; el resumen del paso 8 decía "Preguntas elegidas: 0". | **[navegador]** + **[código]** `views.py:184-186` (vista previa) y `2058-2060` (guardado). | Por defecto, tomar todas las preguntas de los tópicos (o pedir el número con valor inicial y una frase de ayuda). Mostrar en el resumen cuántas preguntas va a tener cada tema. |
| D5 | En móvil (375 px) el contenido útil del paso Examen empieza **debajo de la primera pantalla**: párrafo de introducción + 7 pastillas + migas + 8 pastillas internas + título. En escritorio, cargar una pregunta ocupa ~55 % de la pantalla con tres barras de pasos apiladas (host, migas, asistente embebido). | **[navegador]** capturas. | En los pasos 6–7 ocultar el párrafo introductorio y las migas (o plegarlos); un solo stepper visible. |
| D6 | La pastilla "Preguntas" queda con el ícono de **salteada** (`is-skipped`) aunque después se cargaron preguntas en ese mismo paso. | **[navegador]** clases `is-done is-skipped is-active`. | Quitar `is-skipped` al guardar la primera pregunta. |
| D7 | Las listas de chips de cada paso se completan **de forma asíncrona sin indicador de carga**: un clic inmediato cae sobre un elemento que todavía no estaba (me pasó una vez: elegí una facultad sin querer). | **[navegador]** | Spinner o texto "Cargando…" mientras llega la lista. |
| D8 | `?retomar=1` no retoma: tras completar y volver a entrar, el asistente arranca de nuevo en el paso 1. | **[navegador]** | Ya listado como pendiente (reanudar entre sesiones). |
| D9 | Detalles visuales: la etiqueta "Catálogo" se parte en dos líneas en el chip de "Universidad Abierta Interamericana" a 375 px; el stepper del host ocupa dos filas en 1024 px. | **[navegador]** | Cosmético. |

### 2.2.1 Corregido el 2026-10-06 (rama `fix/asistente-completo-hallazgos`, sin commitear)

| # | Estado | Qué se hizo |
|---|---|---|
| D1 | ✅ corregido y probado en navegador | `full_wizard_page` marca `profile.onboarding_completed` al entrar. "Terminar" ya lleva a Inicio sin rebotar. |
| D2 | ✅ corregido y probado en navegador | La pantalla "¿Cómo empezar?" de `/comenzar/` conserva el ejemplo armado y el recorrido de bienvenida, pero **"Cargar mi propia información" lleva al Asistente completo**. En Inicio el orden pasó a "Asistente completo" · "Probar con un ejemplo". El asistente de 7 pasos viejo sigue existiendo solo por `?step=N`. |
| D3 | ✅ corregido y probado en navegador | (a) `preview_exam` vuelve al asistente de examen (`create_exam_wizard?fw=1`) cuando la petición viene de un iframe (`Sec-Fetch-Dest`); el borrador repone lo cargado y el aviso aparece como diálogo. (b) Red de seguridad en el host: `embed.js` avisa `educaapp:embed-ready` y el host vigila que el iframe siga siendo de su origen; si no, muestra "No se pudo mostrar el armado del examen" con *Reintentar* (arma un iframe nuevo y conserva el borrador), *Recargar la página* y *Volver a Preguntas*. |
| D4 | ✅ corregido, con tests y probado en navegador | `_default_questions_per_version`: sin cantidad, se usan todas las preguntas elegibles de los tópicos elegidos, repartidas entre los temas (antes: una por tópico). Afecta vista previa y guardado, asistente y formulario clásico. Se agregó el texto de ayuda en ambos y el resumen del paso 8 dice qué va a pasar en vez de "0". |
| D5 | ✅ probado en navegador (emulación 375 px) | Desde el paso 2 se oculta la introducción; en pantallas angostas, desde el paso 6 se ocultan también las migas. El contenido del paso Examen pasó de empezar debajo de la primera pantalla a empezar a 175 px. El stepper interno del examen entra en una fila en celular (verificado inyectando el CSS: el archivo servido en el navegador de pruebas estaba en caché). |
| D6 | ◐ corregido, no probado en navegador | `onCreated` del asistente de preguntas ahora llama a `refreshPills()` tras limpiar la marca de "salteada". Probarlo exige saltear con una materia sin preguntas y luego cargar una. |
| D7 | ✅ corregido | Las listas de chips muestran "Cargando…" y reservan altura mientras llegan. |
| D8 | ❌ no se tocó | Reanudar entre sesiones es una función nueva (hoy solo hay recuperación en la misma pestaña, vía `sessionStorage`, que sí funcionó al recargar). Queda en P2. |
| D9 | ✅ probado | La etiqueta "Catálogo" ya no se parte; el stepper del host entra en una fila y desde < 1200 px se nombra solo la pastilla activa. |

Observación sobre el flujo de examen (no es un bug): los pasos 5, 6 y 7 del asistente de examen ("Docente y fecha", "Institución, sede y curso", "Tipo y modalidad") **se pueden recorrer sin completar nada**; la vista previa sale con "Fecha: -" y sin tipo de examen. Es coherente con "mínimo para probar", pero para un examen real conviene sugerir al menos la fecha y el tipo.

### 2.3 Lo que hoy NO es "simple" (sin cambios respecto de la primera revisión)
1. **~12 pantallas por el camino largo**: 7 del host + 6 del asistente de examen embebido (3 a 8) + vista previa + pantalla final. La precarga solo saltea Plantilla y Materia; "Institución, sede y curso" se vuelve a mostrar con institución, facultad y carrera ya elegidas.
2. **El menú lateral expone todo a todos.** No existe un "modo": existe una lista de links.
3. **Editar siempre cae en el formulario viejo** (`editar_examen` / `editar_lote` → `create_exam?edit_exam_id=`).
4. **"Nuevo" y "Asistente" conviven al mismo nivel** en 5 listados (Exámenes, Orales, Plantillas, Instituciones, Preguntas); el asistente es el botón secundario.
5. **Dos asistentes que se pisan** (`/comenzar/` y `/asistente-completo/`), y el que se impone al usuario nuevo es el viejo (D1, D2).

---

## 3. Qué debería entrar al Asistente completo

### P0 — sin esto no se puede declarar "funcionando al 100%"

| # | Qué | Estado / detalle | Esfuerzo |
|---|---|---|---|
| P0.1 | ~~Commitear y probar el paso 7~~ | **Hecho en `main`** y probado hoy en el camino feliz. Falta probar: móvil real, tema oscuro, sesión vencida a mitad del iframe (D3) y varios temas (lote). | 0,5 día |
| P0.2 | ✅ Hecho (06/10) — Arreglar **D1 + D2**: un solo gate de primer ingreso que lleve al Asistente completo y que se marque como completado al terminar o salir. | Es lo primero que vive cualquier usuario nuevo o tester. Hoy el recorrido termina en el asistente viejo. | 0,5 día |
| P0.3 | ✅ Hecho (06/10) — Arreglar **D3**: ningún redirect desde una pantalla enmarcada puede apuntar a una no enmarcable. | Callejón sin salida, silencioso. | 0,5 día |
| P0.4 | ✅ Hecho (06/10) — Arreglar **D4**: el examen debe llevar por defecto todas las preguntas de los tópicos elegidos (o pedir la cantidad con un valor inicial y ayuda). | Un docente que sigue el camino feliz obtiene un examen de 1 pregunta. Afecta también al formulario clásico (`views.py:184`, `2058`). | 0,25 día |
| P0.5 | **Estado de la IA en el paso 6**: consultar `ai_config_status` y mostrar *lista* / *usa el cupo compartido* / *falta configurar* antes de "Generar con IA". | El default de cada usuario es `ollama_local` (`models.py:2499`), que en Render no existe; solo funciona por el fallback compartido. **Localmente hay 2 `GlobalAIConfig` activas (Gemini y Groq, con key)**; en producción **no se verificó**. | 0,5 día + confirmar en prod |
| P0.6 | Pendientes de despliegue de la memoria (**[memoria]**, no re-verificados): migración `0101` en Neon, deploy manual en Render, `render.yaml` ≠ build real, `wipe_production_content` nunca corrido contra Neon, carga masiva OGE/STFI/TFI sin hacer. | Un asistente perfecto sobre una base sin contenido o sin migrar no sirve. | a confirmar |

### P1 — lo que hace que realmente se sienta "simple"

| # | Qué | Detalle | Esfuerzo |
|---|---|---|---|
| P1.1 | **Colapsar el encabezado del examen embebido**: reemplazar "Docente y fecha", "Institución, sede y curso" y "Tipo y modalidad" por **una pantalla** con valores por defecto (docente = yo, fecha = hoy, institución/carrera = lo elegido; pedir solo sede/curso/tipo). Rúbricas queda como sección plegada. | ~12 → ~8 pantallas. Mismos nombres de campo, el guardado no cambia. | 1 día |
| P1.2 | **Interruptor Simple/Avanzado por usuario** (campo en `Profile`). Simple = menú reducido (Inicio, Generar con IA, Preguntas, Exámenes, Cuestionarios orales, Mis datos) y los botones "Nuevo X" llevan al asistente. Avanzado = el menú actual. | Es lo que convierte "tener asistentes" en "tener un modo". Se toca `base.html` y los 5 `list.html` que ya tienen el botón "Asistente". | 1 día |
| P1.3 | **Reducir el chrome en móvil** (D5, D6, D7): ocultar la introducción y las migas en pasos 6–7, un solo stepper, indicador de carga. | La demo con jurado y los testers usan celular. | 0,5 día |
| P1.4 | **Cuestionario oral como alternativa en el paso 7.** | Reutiliza el patrón de iframe (`embed.js`); falta `xframe_options_sameorigin` y un modo `fw=1` en `create_oral_exam_wizard`. | 0,5–1 día |
| P1.5 | **Editar examen desde el asistente** (el payload ya existe: `_build_preview_exam_payload_from_exam`) o, como mínimo, ocultar "Editar" en modo simple y ofrecer "Duplicar". | Es la fuga más visible hacia el formulario viejo. | 1 día (0,25 si solo se oculta) |
| P1.6 | **Entrada al asistente desde Materias/Carreras para no-admin**: "Agregar con el asistente" en lugar de "Solicitar alta". | Hoy el docente solo llega a crear materia/carrera por el Asistente completo. | 0,5 día |

### P2 — después de liberar (no bloquean)
- Rúbricas inline en el paso de examen (hoy: "Crear una" en pestaña nueva; el asistente de Plantilla ya refresca al volver con `focus`, el de examen no).
- Guardar el examen recién armado como **plantilla** al final.
- Tópicos: ABM mínimo o alta desde la ficha de materia (problema de fuga entre carreras documentado en memoria).
- Asistentes para Rúbrica y Grupos.
- Reanudar el Asistente completo entre sesiones (D8).
- Convertir "Generar con IA" (~3.500 líneas) en un módulo `mount()` como el de subir preguntas.
- Retirar o fusionar `onboarding_v2` una vez que el Asistente completo cubra su demo.

---

## 4. Qué NO debe tener asistente (queda como modo avanzado)

Edición de pregunta, importación CSV clásica, detalle/edición de institución con sedes y facultades, asociaciones de carrera, formatos de impresión,
grupos de confianza, favoritos, espacio personal, avisos de borrado, y todo el submenú de Administración. Son tareas de mantenimiento,
no de "primer uso".

---

## 5. Plan sugerido para la semana (revisado)

| Día | Trabajo | Resultado |
|---|---|---|
| 1 | P0.2 (gate de primer ingreso + marcar completado), P0.3 (redirects del iframe), P0.4 (cantidad por defecto) — los tres son cambios chicos y localizados | El recorrido completo ya no se rompe ni se desvía |
| 2 | P0.5 (estado de IA en el paso 6) + confirmar `GlobalAIConfig` en producción + P0.6 (migración, deploy, base de datos) | IA operativa y base lista |
| 3 | P1.1 (encabezado colapsado) + P1.3 (móvil) | Recorrido corto y usable en celular |
| 4 | P1.2 (interruptor Simple/Avanzado) + P1.6 | Existe el "modo simple" como tal |
| 5 | P1.5 (o su versión mínima) + P1.4 si da el tiempo + UAT final + actualizar tours driver.js y checklist | Congelado para liberar |

Reglas de la casa para todo lo que se toque: sin tuteo/voseo en la UI, "Docente" y no "Profesor", actualizar los tours
driver.js en el mismo turno que cambie la UI, nunca commitear `media/`, y correr `collectstatic` local antes de probar JS/CSS nuevos.

---

## 6. Preguntas abiertas para decidir antes de empezar

1. ¿El modo simple es **por usuario** (interruptor) o **por rol**? Recomendación: por usuario, con default "simple".
2. ¿Se retira `/comenzar/` o queda solo como ejemplo de la primera visita? (Hoy es la primera pantalla de todo usuario nuevo, y su recorrido de 13 pasos se superpone.)
3. ¿El cuestionario oral entra al recorrido principal esta semana o queda como entrada aparte?
4. ¿Cuántas pantallas de encabezado se aceptan en el examen embebido (1 vs. las 3 actuales)?
5. ¿"Preguntas por tema" vacío debe significar "todas" o hay que obligar a indicar un número?

---

## 7. Qué no se probó (para no dar por cerrado lo que no se vio)

- **Generar con IA** de punta a punta (la cuenta de prueba no tiene proveedor propio; el fallback compartido existe localmente pero no se ejecutó una generación).
- Carga **por lote** (CSV/TXT) en el asistente de preguntas.
- **Varios temas** (lote de exámenes) dentro del iframe.
- Tema oscuro y dispositivo móvil real (solo emulación de 375 px).
- Exportación PDF/DOCX del examen creado por el asistente.
- Producción (Render/Neon): nada de esto se ejecutó contra producción.
