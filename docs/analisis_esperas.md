# Análisis: esperas sin aviso (la app no puede parecer colgada)

Hecho el 2026-10-29. Solo análisis, no se cambió código. Las mediciones son **locales** (base local, sin red a Neon): en Render + Neon cada consulta suma un viaje de red y la primera visita después de un rato de inactividad tarda mucho más (ver `docs/migrar_hosting.md` y la memoria de arranque en frío). No se midió en producción.

## 1. Lo que ya existe

| Mecanismo | Dónde | Qué cubre |
|---|---|---|
| `submit_guard.js` | todas las páginas | Todo formulario POST: bloquea el doble envío y pone "Guardando…" con ruedita en el botón. Se libera solo a los 15 s |
| `descarga_guard.js` | PDF/DOCX | "Preparando…" mientras el servidor arma el archivo |
| `EducaAppLoading` (capa global) | base.html | Solo 3 pantallas lo usan: procesador de documentos, asistente de configuración inicial |
| Avisos propios | login, registro, aceptar invitación, crear cuestionario oral, asistente completo, subir preguntas | Cada uno con su texto |

## 2. Huecos, de mayor a menor impacto

### A. Navegar entre pantallas no avisa nada (el más grave)
- No hay ningún indicador al tocar un enlace del menú o un botón que lleva a otra página. En el navegador común queda el giro de la pestaña; **en la app instalada en el celular (`display: standalone`) no hay barra del navegador: la pantalla queda quieta hasta que llega la nueva.**
- Los 9 listados filtran, ordenan y buscan **recargando la página completa** (formularios GET): Preguntas, Mis exámenes, Materias, Carreras, Instituciones, Plantillas, Cuestionarios orales, Mis contenidos. Hay páginas pesadas: Carreras 710 KB, Subir preguntas 504 KB, Procesador de documentos 231 KB de HTML.
- Medido en local: casi todas responden en menos de 100 ms, pero con 8 a 26 consultas por página; contra Neon cada consulta cuesta decenas de milisegundos, y tras la suspensión de Neon la primera tarda segundos.

### B. Pedidos internos (`fetch`) sin aviso
Hay unas 150 llamadas. Pantallas con muchas llamadas y casi ningún indicador:
- `create_exam.js` (10 llamadas, 0 indicadores): al elegir materia se cargan temas, resultados de aprendizaje y unidades; al elegir institución, facultades, sedes y carreras. Mientras tanto las listas quedan vacías o con lo anterior.
- `create_exam_wizard.js` (6), `create_exam_template_wizard.js` (9), `create_exam_template.js` (8): lo mismo en los asistentes de examen y plantilla.
- `question_upload_wizard.js`: carga de materias, temas, subtemas y contenidos sin indicador (la vista previa del archivo sí lo tiene).
- `wizard_catalog_search.js`: la búsqueda por escritura no muestra "Buscando…".
- `view_exam_batch.html` y `preview_exam_versions.html` (7 llamadas, 0 indicadores): cambiar una pregunta del examen, listar preguntas disponibles, renombrar y guardar.
- Otras con 1 llamada y sin indicador: favoritos, columnas del listado, solicitud de catálogo, asociaciones de carreras.

### C. Arranque en frío de Render (hasta ~1 minuto)
- Si el servicio estaba dormido, el navegador no recibe nada: ninguna regla de la propia app puede mostrar un aviso porque la app todavía no está encendida. Mitigaciones: UptimeRobot a `/health/` (ya existe; mantiene Render despierto sin tocar la base), pasar a un plan pago de Render durante la evaluación, y para quien ya instaló la app, un service worker que muestre "Iniciando el servidor…" tras unos segundos.
- Neon también se suspende a los 5 minutos: la primera consulta después tarda uno o más segundos, aunque Render esté despierto.

### D. Detalles de lo que ya existe
- `submit_guard` se libera a los 15 s aunque el servidor siga trabajando: una operación lenta (generar, guardar un examen grande) deja volver a tocar el botón y duplicar. Debería esperar más (p. ej. 120 s) para los formularios que no descargan archivos.
- El texto es siempre "Guardando…", incluso cuando el botón dice "Generar" o "Ingresar". Conviene poder indicar el texto por botón (`data-texto-espera`).
- El procesador de documentos (`/doc-processor/`) tardó **1,1 s en local** en renderizarse, frente a menos de 100 ms del resto: la vista consulta el estado de la IA (`backend.get_status()`) antes de mostrar la página. En producción puede depender de un servicio externo. Mejor cargar ese estado aparte, con "Verificando conexión…".
- Pedidos en segundo plano (`setInterval`: procesador, creación de examen, asistente completo): revisar que no muestren avisos molestos si se agregan avisos globales.

## 3. Propuesta

1. **Barra de actividad global** en `base.html` (un solo archivo de JavaScript, sin tocar cada pantalla):
   - Barra fina arriba que aparece a los ~300 ms al: tocar un enlace interno, enviar un formulario (GET o POST), o cuando cualquier `fetch` tarda más de ese tiempo. Se oculta al terminar o al volver de la caché ("pageshow").
   - Mensaje escalonado si sigue esperando: a los 5 s "Está tardando más de lo habitual, sigue en proceso" y a los 20 s "El servidor puede estar iniciándose; puede llevar hasta un minuto".
   - Con opción para que un pedido en segundo plano no la dispare (`data-sin-aviso` o encabezado).
   - Cubre los puntos A y gran parte de B y D de una vez, también en el celular instalado.
2. **Indicadores en las listas dependientes** (B): al elegir materia o institución, la lista afectada se deshabilita y muestra "Cargando…" hasta que llegan los datos. Pantallas: crear examen, asistentes de examen y plantilla, subir preguntas, vista de lotes.
3. **Ajustar `submit_guard`** (D): tiempo de espera más largo para formularios que no descargan y texto de espera por botón.
4. **Procesador de documentos**: sacar la consulta del estado de la IA del render de la página.
5. **Arranque en frío** (C): decisión de hosting (ver `docs/migrar_hosting.md`) y, si se quiere, service worker con pantalla "Iniciando el servidor…".
6. **Páginas pesadas** (Carreras, Subir preguntas): paginar o cargar en diferido (ya está anotado como "etapa 3" de los selectores).

## 4. Cómo verificarlo después
Con el servidor local, simular red lenta (herramientas del navegador: "Slow 3G") y recorrer: menú lateral, filtros de los 9 listados, cada asistente en celular, crear examen, descargar PDF, generar con IA, login y alta por invitación. Criterio de aceptación: **en ningún momento pasan más de ~400 ms sin algún cambio visible en pantalla.**

## 5. Implementado (2026-10-29)

- `static/js/actividad.js` (cargado desde `base.html`): barra fina arriba a los 300 ms ante enlaces internos, envíos de formularios y cualquier `fetch`; mensajes a los 5 s y a los 20 s. Opciones por pedido: `{ sinAviso: true }` y `{ cargando: '#lista' }` (la lista se atenúa con "Cargando…" y los `select` se deshabilitan a partir de los 250 ms). No se activa en anclas, descargas, enlaces externos ni pestañas nuevas.
- Listas dependientes marcadas: Crear examen (temas, preguntas, resultados de aprendizaje, unidades, facultades, sedes, carreras), asistente de examen, asistentes de plantilla y plantilla (facultades, sedes, carreras, materias, resultados, rúbricas) y Subir preguntas (materias, temas, subtemas, contenidos).
- Vista de lotes y vista previa de versiones: capa "Cambiando la pregunta…" y "Buscando alternativas…" (antes no había aviso ni protección contra el doble clic).
- `submit_guard.js`: espera máxima de 60 s (antes 15 s) y texto propio por botón con `data-texto-espera`.
- Estado de la IA pública (`GlobalFallbackBackend.get_status`): se guarda 90 s si está conectado. Antes cada apertura de `/doc-processor/` y cada verificación hacía una llamada a Groq de 0,5 a 2 s.
- Pruebas: `material/tests_esperas.py`. Verificado en el navegador (celular, 375 px): la barra no aparece antes de 300 ms, aparece con un pedido lento y se apaga al terminar; el mensaje de 5 s aparece; enlaces ancla, de descarga, externos y de pestaña nueva no la activan; `cargando` marca y desmarca la lista.
- Pendiente: probar con red lenta real en Render; búsqueda del catálogo en los asistentes (`wizard_catalog_search.js`, 2 llamadas) y favoritos/columnas no marcan lista (la barra sí los cubre); páginas pesadas (Carreras 710 KB) y arranque en frío siguen igual.
