# Modo simple (asistentes) vs. modo avanzado (ABM) — análisis (revisión 3, 2026-10-08)

Alcance: relevamiento del código (`material/urls.py`, `views.py`, templates, JS de los asistentes), de la
memoria del proyecto y, en esta segunda revisión, **prueba real en navegador** del Asistente completo con una
cuenta docente (no admin) creada para la ocasión y borrada al terminar. No se modificó código de la app.
Marcas: **[código]** leído hoy en el código · **[navegador]** comprobado hoy en el navegador ·
**[memoria]** viene de notas de sesiones anteriores y no se re-verificó.

---

## 0. Qué cambió desde la primera revisión

> **Revisión 3 (08/10):** las secciones 3 en adelante se reescribieron con las decisiones del 08/10 (tópicos por carrera-materia, IA pública como principal, administración fuera de alcance, oral en el asistente). Los hallazgos D1 a D9 de la sección 2 están corregidos y mergeados (PR #7); la sección 2 queda como registro histórico.

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

## 3b. Respuestas y cambios de rumbo (08/10, tarde)

Reemplaza lo que contradiga en las secciones 4 y 5.

1. **Ollama.** Se llama **"Servidor de IA propio (Ollama)"**: puede ser el de la institución o uno propio, no necesariamente "mi computadora". Ya está en la pantalla y en el modelo.
2. **Tópicos: cambia la relación, no solo la pantalla.** "Inglés I" de Arquitectura no es el de Sistemas, así que los tópicos pertenecen a la **asociación carrera-materia**. El diseño con "vacío = común" (4.1) queda como respaldo. La regla, igual que con los resultados de aprendizaje:
   - **Materia personal:** los tópicos son solo del dueño.
   - **Materia del catálogo:** los tópicos son del catálogo, unificados para todos los docentes de esa carrera-materia, y los administra un admin.
   - Un docente que necesita un tópico que el catálogo no tiene crea uno **personal** en esa carrera-materia (solo lo ve él) y puede proponerlo al catálogo por el circuito de solicitudes que ya existe (proponer, aprobar, rechazar, fusionar). Sin esto, quien carga preguntas en una materia del catálogo quedaría bloqueado.
   - Cambios: `Topic.career_subject` (clave a `CareerSubject`) y una marca de catálogo; los selectores de tópicos pasan la carrera; ABM de tópicos y subtópicos dentro del bloque de cada carrera en la ficha de la materia. Los subtópicos siguen a su tópico.
   - Datos existentes: relleno razonable (materias con una sola carrera quedan asignadas; las compartidas se duplican por carrera-materia y las preguntas quedan con el primero). **Neon todavía no es producción**, así que no hace falta que sea perfecto y se puede reiniciar.
3. **Oral con preguntas propias: pasa dentro y fuera del asistente.** El asistente envía al mismo formulario y a las mismas vistas. Está en cuatro lugares del código: las materias que ofrece el formulario, `validate_oral_exam`, `generate_oral_exam_questions` y el cambio de pregunta. **No hay una decisión detrás:** el módulo oral es del 19/09/2025 y el sistema de compartir (`content_visibility.py`) es del 29/07/2026; el oral nunca se pasó a usarlo. Además usa todas las preguntas del docente, aprobadas o no. Corrección: usar `get_visible_questions` con las mismas reglas que el examen escrito.
4. **Plantillas: sí conviene cambiar el orden.** Una plantilla guarda institución, facultad, carrera, materia, sede, docente, cátedra, año, tipo, resultados de aprendizaje, rúbricas y notas: es todo lo de los pasos 1 a 5 y el encabezado. Su lugar natural es **el comienzo** del Asistente completo: "¿Partir de una plantilla?" completa los pasos 1 a 5 y lleva directo a Preguntas o Examen, y el examen embebido recibe el resto (docente, sede, formato, rúbricas, notas). Si no se elige ninguna, el paso funciona como hoy. Es lo recomendado frente a la alternativa mínima (no saltear el paso "Plantilla" del examen embebido).
5. **IA pública agotada o no disponible:** el texto es el que indicaste (no hay más cupo compartido; se puede cargar una conexión propia o, si la institución tiene un servidor Ollama propio, conectarlo consultando con el administrador). Implementado.
6. **Pregunta sobre producción:** retirada. Neon no es producción, así que el diseño no depende de cuántos datos haya.
7. **Fecha:** cuanto antes.
8. **Estimaciones.** Las de la sección 5 eran en días de un desarrollador, con margen. El trabajo real de esta sesión es más corto: la IA pública (cambio de modelo, migración de datos, mensajes, estado en el asistente, 11 tests y prueba en el navegador) se hizo en una sola tanda. Lo que de verdad frena es revisar y mergear cada cambio, el deploy manual a Render y los cambios de modelo que tocan muchos lugares. Estimación actual de trabajo mío: tópicos con la nueva relación, aproximadamente una jornada; plantilla al comienzo, 2 a 3 horas; oral y corrección de preguntas compartidas, 2 a 3 horas; interruptor Simple/Avanzado, 2 horas.

### Estado de implementación (08/10 noche)
Todo en la rama `feat/ia-publica-principal`, sin commitear. 210 tests en verde (incluye 31 nuevos de tópicos y oral y 11 de IA pública). Migraciones nuevas: 0102 (IA pública), 0103 (tópicos por carrera-materia, con relleno) y 0104 (solicitud de tópico).

| Cambio | Estado |
|---|---|
| IA pública como principal (default, mensajes, estado en el paso Preguntas, "Servidor de IA propio (Ollama)") | Hecho y probado en el navegador |
| Tópicos por carrera-materia con espacio personal / catálogo | Hecho: `Topic.career_subject` y `es_catalogo_institucional` (también en sub-tópicos), `get_visible_topics`, ABM en la ficha de la materia, proponer al catálogo, aprobar / rechazar / fusionar en la bandeja. Probado en el navegador con un docente y un admin |
| Oral con preguntas compartidas (y sus tópicos y sub-tópicos) | Hecho: `get_oral_questions` en los siete lugares, solo aprobadas, igual que el examen escrito |
| Plantilla al comienzo del asistente | Pendiente |
| Oral dentro del Asistente completo | Pendiente |
| Interruptor Simple/Avanzado | Pendiente |

**Reglas que quedaron** (mismo criterio que los resultados de aprendizaje):
- Materia personal: sus tópicos son solo del dueño.
- Materia del catálogo: los tópicos del catálogo los administra un admin y los ven todos los docentes de esa carrera-materia (y los que no tienen carrera asignada). Un docente crea tópicos **personales** (solo los ve él, y quien reciba la materia por un grupo de confianza) y puede **proponerlos al catálogo**.
- Aprobar un tópico lo pasa al catálogo con sus sub-tópicos personales. Rechazarlo lo deja personal. Fusionarlo lo une con uno existente: las preguntas, los exámenes y los cuestionarios orales pasan al tópico del catálogo, y los sub-tópicos se unen por nombre.
- Fusionar materias o carreras reubica los tópicos en la carrera-materia destino.
- Los datos que ya existían se rellenaron así: materias personales, tópicos personales del dueño; materias del catálogo con una sola carrera, tópico asignado a esa carrera; materias en varias carreras, tópico sin carrera asignada (se ve en todas) hasta que se lo asigne desde la ficha.

**Límites conocidos:**
- "Generar con IA" crea sus tópicos sin carrera asignada cuando la materia está en varias carreras (el generador no recibe la carrera). Se asignan después desde la ficha.
- Los sub-tópicos personales sobre un tópico del catálogo no tienen circuito de propuesta propio: solo viajan con la propuesta de su tópico.
- El formulario clásico de examen, el cuestionario oral suelto y "subir preguntas" suelto, sin carrera elegida, listan todos los tópicos visibles de la materia, como antes.

### Pregunta resuelta
En una materia del catálogo el docente **sí** puede crear tópicos personales y proponerlos al catálogo, con el mismo criterio que el resto de los objetos.

---

## 3. Decisiones del 08/10 y cómo cambian el plan

| Decisión | Efecto en el plan |
|---|---|
| Tópicos y subtópicos necesitan un ABM muy simple, dentro de la materia, y deberían ser únicos de cada asociación carrera-materia. | Nuevo bloque de trabajo con análisis propio (4.1). Pasa de "P2" a prioridad alta. |
| La administración no necesita asistente. | Sale del alcance. Usuarios, invitaciones, bandeja, carga masiva, Groq, Neon, prompt, IA institucional y resultados de testing quedan como están. |
| La IA pública tiene que ser la principal. Ollama pasa a ser una opción más. | Cambio de default y de mensajes (4.2). Reemplaza al punto P0.5 anterior. |
| Formatos de impresión y Rúbricas sin asistente está bien. | Prioridad baja. Ya no aparecen en el plan. |
| Cuestionario oral: evaluar sumarlo al Asistente completo. | Evaluado en 4.3. |
| Editar desde el asistente importa menos que cargar lo ya creado y crear lo nuevo. | "Editar examen desde el asistente" baja a P2. Sube "usar lo ya creado" (4.4). |

---

## 4. Análisis de viabilidad

### 4.1 Tópicos y subtópicos por carrera-materia

**Cómo está hoy [código]**
- `Topic.subject` apunta a la materia, no a la asociación carrera-materia (`CareerSubject`). Los tópicos de una materia los ven todas las carreras que la comparten.
- `Topic` ya tiene `created_by` y un `unique_together (nombre, materia, creador)`, y el modelo de `Unidad` dice que los tópicos son "privados por usuario". En la práctica no es así: `add_topic` no guarda `created_by`, rechaza nombres repetidos en toda la materia y `get_topics` no filtra por creador. Hay un desfasaje entre lo que el modelo dice y lo que el código hace.
- Los resultados de aprendizaje, en cambio, **ya** son únicos de cada carrera-materia, y la ficha de la materia (`subjects/detail.html`) los muestra agrupados por carrera con sus botones de alta, edición y baja. Los tópicos encajan en ese mismo bloque.
- Al borrar un tópico, sus preguntas pasan a "sin tópico" (`SET_NULL`), y desaparece de los exámenes y cuestionarios orales que lo usaban (relaciones M2M).
- No existe ninguna pantalla de tópicos. Se crean solo desde cargar o editar una pregunta, o desde "Generar con IA".

**¿La materia comparte carreras? [datos locales, no producción]**

| Dato | Valor |
|---|---|
| Materias con alguna carrera | 989 de 992 |
| Materias que están en más de una carrera | **48 (4,9 %)** |
| Las más compartidas | Inglés I e Inglés II (8 carreras cada una), Seminario de Trabajo de Integración y Trabajo Final de Graduación (5), Programación I (3) |
| Materias con tópicos y en más de una carrera | 7 (de 41 tópicos en total) |
| Preguntas sin tópico | 10 de 323 |

Conclusión: sí se comparten, pero son una minoría y casi todas con pocos tópicos. Hay que confirmar con la base de producción. Si se va a borrar antes de la defensa (`wipe_production_content`), el catálogo se vuelve a cargar y el problema se define de cero.

**Diseño propuesto**
1. Agregar `Topic.career_subject`, una clave a `CareerSubject` que puede quedar vacía. **Vacío significa "común a todas las carreras de la materia"**: todo lo existente, las materias sin carrera y los tópicos creados sin contexto de carrera. No hace falta migrar datos ni duplicar tópicos.
2. El nombre pasa a ser único por (materia, carrera-materia, creador) y la comprobación de duplicados de `add_topic` se hace dentro del mismo alcance.
3. En la ficha de la materia, dentro del bloque de cada carrera (junto a los resultados de aprendizaje), una lista de tópicos con sus subtópicos: agregar, renombrar y borrar. Antes de borrar, un aviso con la cantidad de preguntas, exámenes y cuestionarios afectados. Si la materia está en más de una carrera, un bloque "Comunes a todas las carreras".
4. Dónde se listan los tópicos:
   - Con carrera conocida (el Asistente completo, el asistente de examen embebido, la ficha de la materia): los comunes más los de esa carrera.
   - Con carrera desconocida (subir preguntas suelto, formulario clásico de examen, cuestionario oral, generar con IA): se listan todos, como hoy. Así el cambio no rompe ningún flujo existente.
5. Permisos: quien puede ver la materia puede crear tópicos (como hoy, y como pide el flujo de cargar preguntas). Renombrar y borrar queda para el dueño de la materia personal o un admin. Para el borrado de tópicos ajenos de una materia del catálogo hay que definir una regla (pregunta abierta 1).

**Riesgos**
- Las preguntas pertenecen a la materia, no a la carrera. Una pregunta con un tópico de la carrera A no se ofrece al armar un examen de la carrera B si se filtra por tópico. Es coherente con la regla pedida, pero hay que decirlo en pantalla ("este tópico es solo de la carrera X").
- Los lugares que leen tópicos son unos 36 (`views.py` 19, `forms.py` 7, `views_document_processor.py` 6, más modelos, contexto y cuentas de entrenamiento). Con el valor vacío como "todos", ninguno se rompe, pero hay que revisar los 5 selectores de tópicos: `get_topics`, `get_questions_by_topics`, el asistente de examen, el oral y el generador.
- Si el alcance es "carrera-materia" y no "docente", los tópicos de un docente pasan a ser visibles para los demás docentes de esa carrera-materia. Hoy ya lo son (global por materia), así que no empeora, pero conviene decidirlo a propósito (pregunta abierta 2).

**Estimación**

| Fase | Contenido | Esfuerzo |
|---|---|---|
| 1 | ABM de tópicos y subtópicos en la ficha de la materia, sin tocar el modelo, con aviso de "esta materia se usa en N carreras" y permisos (`_puede_editar_catalogo`) | 0,5 a 1 día |
| 2 | `Topic.career_subject`, migración, selectores con contexto de carrera, tests | 1,5 a 2 días |

**Recomendación:** hacer la Fase 1 ya (resuelve el pedido visible y deja la pantalla donde hará falta) y la Fase 2 enseguida detrás, porque es aditiva y no cambia el comportamiento por defecto.

### 4.2 IA pública como principal, Ollama como una opción más

**Cómo está hoy [código]**
- `UserAIConfig.source` tiene por defecto `ollama_local` (`models.py:2499`) y los cuatro valores posibles ya existen: IA pública (`shared_demo`), Ollama, API propia y la de la institución.
- En la pantalla "Proveedor de IA" la IA pública ya aparece primera, pero **el formulario guarda `ollama_local` si no llega ningún valor** (`views.py:9388`), y el mensaje de estado y el procesador de documentos usan `ollama_local` como valor de respaldo.
- Si el usuario tiene `ollama_local` y no hay un servidor Ollama, el sistema ya cae solo a la IA pública (`ai_router.py`). Funciona, pero la pantalla muestra "Ollama" y el usuario ve un estado que no es el real.
- Si el usuario elige IA pública y no hay una `GlobalAIConfig` activa con clave, el sistema vuelve a Ollama y falla con un error confuso en vez de decir que la IA pública no está disponible.
- En la base local hay 3 configuraciones, todas en `ollama_local` y sin URL propia. Localmente hay 2 `GlobalAIConfig` activas (Gemini y Groq). **En producción no se verificó.**

**Cambios**
1. Default del modelo a `shared_demo` y migración de datos: las filas en `ollama_local` sin URL propia pasan a `shared_demo`. Las que tienen una URL propia no se tocan.
2. Cambiar `ollama_local` por `shared_demo` en los respaldos de `ai_config_view`, de `ai_config.html` y de `views_document_processor.py`.
3. Con IA pública seleccionada y sin configuración activa, mostrar "La IA pública no está disponible ahora" con el camino a "usar mi propia clave". Dejar de caer en Ollama en ese caso.
4. Estado visible en el paso Preguntas del Asistente completo, antes de "Generar con IA": usar `ai_config_status` (ya existe) y mostrar uno de tres estados: *lista* (con el cupo restante si hay), *cupo agotado* o *no disponible, usar mi propia clave*. "Cargar a mano" queda siempre disponible.
5. Dejar Ollama en la pantalla como "IA en mi computadora (avanzado)".

**Riesgos**
- La IA pública tiene cupo limitado y compartido. Con muchos docentes probando a la vez se agota. El estado visible y el aviso de cupo existen para eso, pero conviene confirmar los límites de las cuentas gratuitas antes de la defensa.
- Hay textos viejos con tuteo en esa pantalla ("Mientras no cargues una nueva…"). Aprovechar para corregirlos (regla de la casa).
- Migración de datos: tocar filas de usuarios reales. Es de bajo riesgo, pero hay que correrla en Neon como cualquier otra.

**Estimación:** 0,5 a 1 día, con tests.

### 4.3 Cuestionario oral dentro del Asistente completo

**Qué necesita el cuestionario oral [código]**
- Materia, tópicos, cantidad de estudiantes, preguntas por estudiante y cantidad de grupos. Un panel en vivo (`validate_oral_exam`) avisa si no alcanzan las preguntas.
- Genera las preguntas **solo con las preguntas propias** del docente (`user=oral_exam.user`), a diferencia del examen escrito, que también usa las compartidas por grupos.
- Agrupa las preguntas por **subtópico**, o por tópico si no hay subtópicos. Para que dos estudiantes del mismo grupo no reciban lo mismo hacen falta, como mínimo, estudiantes por grupo × preguntas por estudiante subtópicos (o tópicos) distintos. Hoy, localmente, hay 3 subtópicos en toda la base. **El oral con un solo tópico no sirve.**
- El formulario guarda por un POST nativo a `create_oral_exam`, que al terminar redirige a `view_oral_exam`, una pantalla que no se puede enmarcar.

**Viabilidad:** sí, con el mismo patrón del iframe del examen. Es el segundo caso del mismo mecanismo.

| Pieza | Trabajo |
|---|---|
| Elegir "Examen escrito" o "Cuestionario oral" en el paso 7 | Dos tarjetas en el host; el escrito sigue igual |
| `create_oral_exam_wizard` enmarcable y con `?fw=1` (materia precargada, se saltea el paso de materia) | Decorador `xframe_options_sameorigin`, parámetros, JS |
| Guardado dentro del iframe | Con `fw=1`, el éxito vuelve a una pantalla propia que avisa `educaapp:oral-saved` con la dirección del cuestionario; los errores de validación vuelven al asistente, no al formulario clásico (mismo problema que se arregló en el examen) |
| Pantalla final del host | Tarjeta "Cuestionario guardado" con "Ver el cuestionario" |
| Aviso previo | Si la materia no tiene al menos 2 tópicos o subtópicos con preguntas propias, avisarlo antes de abrir el asistente |
| Tests | Prefill, enmarcado, errores y guardado |

**Estimación:** 1 día. Conviene hacerlo después de los tópicos: cuanto mejor se carguen los tópicos y subtópicos, mejor funciona el oral.

### 4.4 Cargar lo ya creado y crear lo nuevo

Cobertura actual del Asistente completo [código y navegador]:

| Paso | Usar lo ya creado | Crear nuevo |
|---|---|---|
| Institución, Facultad, Carrera, Materia | Sí: chips "Catálogo" y "Personal" más búsqueda | Sí |
| Resultados de aprendizaje | Sí: lista de la carrera-materia | Sí |
| Preguntas | Sí, pero solo se ve el conteo ("tiene 5 preguntas disponibles"); no hay forma de mirarlas ni elegirlas | Sí: a mano (una o por lote) o con IA |
| Examen | **No.** El asistente embebido **saltea el paso "Plantilla"** (`startEmbedded` avanza dos pasos), aunque ya filtra las plantillas de la materia elegida | Sí |

Huecos:
1. **Plantilla existente.** Una plantilla guarda institución, carrera, formato de impresión, resultados de aprendizaje, rúbricas y notas. Es justamente "lo ya creado" del examen y hoy no se puede usar desde el asistente. Arreglo: no saltear el paso 1 cuando la materia tiene plantillas (0,25 a 0,5 día).
2. **Partir de un examen anterior.** No existe "duplicar un examen". Es lo más pedido por un docente real (el mismo parcial con otras preguntas). Va al plan como mejora posterior.
3. **Mirar las preguntas existentes** desde el paso Preguntas: un enlace "Ver mis preguntas de esta materia" a la lista filtrada. Mínimo.

---

## 5. Plan priorizado (revisado el 08/10)

Hoy es jueves. Si la semana de liberación termina el viernes, **no entra todo**. Propuesta de corte:

### Para liberar (en este orden)
| # | Trabajo | Esfuerzo | Por qué |
|---|---|---|---|
| 1 | IA pública por defecto, mensajes y estado en el paso Preguntas (4.2) | 0,5 a 1 día | Sin IA que funcione, el camino más prometedor del asistente falla |
| 2 | Tópicos: ABM en la ficha de la materia (4.1, Fase 1) | 0,5 a 1 día | Pedido directo, hoy no hay dónde ver ni ordenar los tópicos |
| 3 | Plantilla existente dentro del paso Examen (4.4) | 0,25 a 0,5 día | Es "cargar lo ya creado" |
| 4 | Interruptor Simple/Avanzado por usuario | 1 día | Es lo que convierte los asistentes en un modo |
| 5 | Pendientes de despliegue: migración 0101, build de Render, base de datos de Neon, carga de preguntas | a confirmar | Nada de lo anterior sirve sin esto |

### Inmediatamente después
| # | Trabajo | Esfuerzo |
|---|---|---|
| 6 | Tópicos por carrera-materia (4.1, Fase 2) | 1,5 a 2 días |
| 7 | Cuestionario oral en el Asistente completo (4.3) | 1 día |
| 8 | Encabezado del examen en una sola pantalla (de ~12 a ~8 pantallas) | 1 día |
| 9 | "Agregar con el asistente" en Materias y Carreras para quien no es admin | 0,5 día |

### Después / baja prioridad
- Duplicar un examen como punto de partida.
- Editar desde el asistente (examen, preguntas).
- Asistentes para Rúbricas y Formatos de impresión (decisión: no hacen falta).
- Reanudar el Asistente completo entre sesiones.
- Convertir "Generar con IA" en un módulo embebible.
- Retirar o fusionar el asistente viejo de `/comenzar/`.

### Fuera de alcance
- Toda la Administración (usuarios, invitaciones, bandeja, carga masiva, Groq, Neon, prompt, IA institucional, resultados de testing).
- Grupos de confianza, favoritos, espacio personal, avisos de borrado.

---

## 6. Preguntas abiertas

1. **Borrar o renombrar tópicos en una materia del catálogo:** ¿solo admin, o también el docente que lo creó?
2. **Alcance de los tópicos:** ¿los comparten todos los docentes de la misma carrera-materia (como los resultados de aprendizaje), o cada docente tiene los suyos? El modelo dice "privados por usuario", el código funciona como "compartidos por materia", y la regla que pediste ("únicos de cada asociación carrera-materia") apunta a lo primero.
3. **Datos de producción:** ¿cuántas materias compartidas hay realmente en Neon? El 4,9 % es de la base local.
4. **IA pública:** ¿cuál es el cupo diario real de las cuentas gratuitas, y qué se le muestra a un docente cuando se agota?
5. **Fecha de liberación:** ¿sigue siendo esta semana? De eso depende cuánto de la segunda tabla entra.

---

## 7. Qué no se probó (para no dar por cerrado lo que no se vio)

- Generar con IA de punta a punta (la cuenta de prueba no tiene proveedor propio) y el estado real de la `GlobalAIConfig` en producción.
- Carga por lote CSV o TXT en el asistente de preguntas.
- Varios temas (lote de exámenes) dentro del iframe, tema oscuro y celular real.
- El conteo de materias compartidas y de tópicos se hizo sobre la base local, no sobre producción.
- Nada de lo propuesto en las secciones 4 y 5 está implementado todavía.
