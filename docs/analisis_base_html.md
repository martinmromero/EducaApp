# Análisis de `base.html` y plan para ordenarlo

Fecha: 2026-09-30. Archivo analizado: `material/templates/material/base.html`
(1.121 líneas, 61.694 bytes). Solo lectura: no se modificó nada para este análisis.

## 1. Qué es y qué pesa

Es la plantilla raíz de 80 pantallas (más 3 que heredan de `base_exam_preview.html`,
que es un documento aparte). Cada respuesta HTML de la app arrastra sus 62 KB,
porque casi todo está incrustado: no se cachea por separado en el navegador.

| Sección | Líneas | Bytes | Qué contiene |
|---|---|---|---|
| Encabezado y script anti-parpadeo | 1–40 | 2.359 | Metas PWA, tema oscuro previo a pintar, enlaces a CSS |
| `<style>` incrustado | 41–102 | 2.669 | "Fallback crítico" móvil, clases `.border-left-*` y `.text-gray-800` |
| Panel de Modo Testing (HTML) | 109–161 | 3.295 | Solo si `testing_mode_active` |
| Sidebar, barra superior, banner | 163–411 | ~16.400 | Menú, tema visual, recorrido guiado, Área de Pruebas |
| Overlay, modales y contenedor de toasts | 413–479 | 4.240 | `globalLoadingOverlay`, `pageMessageModal`, `eduModal`, toasts |
| Script 1 | 483–668 | 9.147 | `EducaAppLoading`, `EducaAppModal`, `EducaAppToast`, `eduConfirmSubmit`, mensajes a modal |
| Scripts de terceros y propios | 669–671 | — | driver.js, `tour.js`, `favorites.js` |
| Script 2 | 672–944 | 14.586 | Sidebar, modo claro/oscuro, tema visual, menú "?", submenús, service worker |
| Script de Modo Testing | 946–1113 | ~5.200 | Stepper del panel, solo con `testing_mode_active` |
| Bloque `javascript` | 1117 | — | Punto de extensión para páginas hijas |

Comentarios: 5.529 bytes de HTML y 7.929 de JS (el 22% del archivo es comentario).
La mayoría explica decisiones reales, así que conviene conservarlos al mover el código.

## 2. El contrato: de qué depende el resto de la app

### Bloques (6, ninguno huérfano)
`title`, `body_extra_attrs`, `page_title`, `page_actions`, `content`, `javascript`.
Usos entre las 80 hijas: `content` 80, `title` 45, `page_title` 42,
`body_extra_attrs` 21, `page_actions` 11, `javascript` 3.

### Globales de JavaScript que otras pantallas usan
| Símbolo | Archivos que lo usan fuera de `base.html` |
|---|---|
| `EducaAppModal` | 25 |
| `EducaAppTour` (definido en `tour.js`) | 22 |
| `bootstrap.*` | 17 |
| `eduConfirmSubmit` | 12 |
| `EducaAppToast` | 5 |
| `EducaAppLoading` | 2 |
| `toggleSidebar`, `closeSidebarMobile` | 2 cada uno |
| `syncToggleButton` | 1 |
| `toggleSubmenu`, `toggleSidebarHard`, funciones del panel de testing | 0 (solo los usa el propio HTML con `onclick`) |

Cualquier extracción tiene que conservar estos nombres en `window`.

### Variables de contexto que lee
`user`, `visual_theme`, `visual_theme_choices`, `is_admin`, `is_tester`,
`in_training_mode`, `testing_mode_active`, `pending_invites_count`,
`pending_catalog_requests_count`, `pending_catalog_notifications_count`,
`pending_question_deletion_notices_count`, `request.GET.embed`, `request.path`.
(Vienen de `material/context_processors.py`. Esa pieza tiene cambios sin commitear
de otra tarea; conviene no tocarla en paralelo.)

### Django dentro del JavaScript (los únicos 6 puntos que impiden mover el JS tal cual)
1. `{% url "material:set_visual_theme" %}`
2. `{% url "material:toggle_testing_mode" %}` (dos veces)
3. `{% url "material:testing_panel_state" %}`
4. `{% url "material:testing_panel_navigate" %}`
5. `{% url "material:testing_panel_save" %}`
6. El bucle de mensajes `area_pruebas_modal` (líneas 659–667 de `base.html`, al final del script 1).

Todo lo demás del JS es estático y se puede mover sin cambios de lógica.

### Identificadores de los que dependen otras piezas
Los recorridos guiados apuntan a `#tourMenuGenerarIA`, `#tourMenuContenidos`,
`#tourMenuPreguntas`, `#tourMenuExamenes`, `#tourMenuAcademico`, `#tourMenuPlantillas`,
`#tourMenuFormatos`, `#tourMenuGrupos`, `#tourMisDatos`, `#tourSidebarBrand`,
`#tourHelpBtn`. Son 20 recorridos en total: cambiar uno de esos ids rompe su paso.

## 3. Riesgos y acoplamientos encontrados

1. **`const` globales sin encapsular.** El script 2 declara a nivel de script
   `isMobile`, `htmlEl`, `toggleModeButton`, `visualThemeOptions`, `csrfInput` y
   `tourHelpBtn`. Si una pantalla declarara alguno igual, uno de los dos scripts
   falla entero. Hoy no hay ninguna colisión (comprobado), pero es una trampa.
2. **Orden de ejecución.** El `content` de cada página se renderiza antes que los
   scripts de `base.html`. Un script de página que llame a `EducaAppModal` al cargar
   (no dentro de `DOMContentLoaded`) falla. Al mover código a archivos estáticos hay
   que conservar la posición y no agregar `defer`.
3. **CSS duplicado con `!important`.** El bloque "fallback crítico" (41–102) repite
   reglas de `styles.css`. Su comentario dice que existe por caché de producción.
   Hay que confirmar con el despliegue actual (WhiteNoise con manifiesto) que ya no
   hace falta antes de borrarlo.
4. **Clases definidas aquí y usadas en otros lados.** `.border-left-*` y `.text-gray-800`
   (líneas 94–101) se usan en `lista_preguntas.html`. En un análisis anterior dije que
   no estaban definidas: estaba equivocado, están en este archivo.
5. **Layout calculado con estilos en línea.** `syncToggleButton` mide la barra superior
   y fija alturas en el botón y en el logo con `style`. Es frágil ante cambios de tema
   y de tipografía (justo lo que se tocó en esta sesión).
6. **14 `onclick` en línea.** Dificultan mover el JS y una política de contenido
   (CSP) futura.
7. **Textos con problemas.** Dos `aria-label="Close"` en inglés (líneas 448 y 469),
   "Cerrar menu lateral" sin tilde (línea 740) y voseo en el panel de testing
   ("segui", "elegí", línea 142). Es lo que ven los testers.
8. **Sin pruebas de JavaScript ni de interfaz.** Solo existen los 4 tests de humo de
   Django (`material/tests_qa_smoke.py`), que verifican que las páginas rendericen.
   No detectan un sidebar roto ni un modal que no abre.
9. **Service worker.** Se registra en cada carga (`/sw.js`); es de alcance raíz.
   Hay que tenerlo en cuenta al cambiar rutas de estáticos.

## 4. Plan por etapas (riesgo creciente)

Cada etapa se hace en su propia rama y commit, sin cambiar comportamiento visible.

### Etapa 0 — Red de seguridad (antes de tocar nada)
- Script de "contrato": una página de prueba (o comprobación en consola) que liste los
  globales de la sección 2 y los ids de recorridos, y falle si falta alguno.
- Conservar el escáner de contraste y el barrido de pantallas de esta sesión como
  herramienta repetible (hoy vive solo en `localStorage` del navegador de pruebas).
- Lista de comprobación manual corta: sidebar (teclado y móvil), modo oscuro, cambio de
  tema, un toast, un modal de confirmación, menú "?" y recorrido, Área de Pruebas,
  Modo Testing con un usuario tester.
- Criterio de salida: `check`, `makemigrations --check`, `tests_qa_smoke` y el contrato
  en verde sobre la rama, verificado en un `git worktree` limpio.

### Etapa 1 — Higiene sin riesgo
- Corregir los textos de la sección 3.7.
- Mover el `<style>` incrustado a `styles.css` o `theme.css` (respetando el orden de carga),
  y borrar el duplicado solo si se confirma lo de la sección 3.3.
- Criterio: barrido de contraste y captura de comparación en 3 pantallas.

### Etapa 2 — Script 1 a archivo propio
- Mover las líneas 483–668 a `static/js/edu-ui.js` (nombre a confirmar), cargado en la
  misma posición y sin `defer`.
- Pasar los mensajes `area_pruebas_modal` como `<script type="application/json">` o
  atributo `data-`; el resto del archivo no tiene Django.
- Criterio: contrato en verde, prueba de toast y modal, `collectstatic` sin errores.

### Etapa 3 — Script 2 a archivo propio
- Mover 672–944 a `static/js/edu-shell.js` dentro de una función autoejecutable, exponiendo
  explícitamente `toggleSidebar`, `closeSidebarMobile`, `syncToggleButton`, `toggleSubmenu`.
  Eso elimina el riesgo de la sección 3.1.
- URL de `set_visual_theme` por `data-` en `<body>` o en el selector de tema.
- Sustituir los `onclick` por listeners de forma gradual (2 o 3 por vez).
- Criterio: sidebar en escritorio y móvil, teclado, tema, modo oscuro, los 20 recorridos.

### Etapa 4 — Modo Testing separado
- HTML a `_testing_panel.html` (con `{% include %}`) y JS a `static/js/testing-panel.js`,
  cargados solo si `testing_mode_active`. Las 4 URLs van por `data-` en `#testPanel`.
- Criterio: probar con un usuario tester que se abre, navega, guarda y sale.

### Etapa 5 — Partir el HTML
- Extraer `_sidebar.html`, `_topbar.html` y `_global_modals.html`, sin cambiar el marcado.
  Es solo organización: ids, clases y orden se conservan.
- Criterio: diff de HTML renderizado idéntico antes y después en 5 pantallas.

### Etapa 6 — Opcional
- Reducir el peso por respuesta (ya habría ~35 KB menos en línea tras las etapas 1 a 4) y
  revisar la política de caché de estáticos y del service worker.

## 5. Decisiones que dependen de ti
1. **Momento.** Recomiendo hacer solo las etapas 0 y 1 antes de la defensa y dejar 2 a 5
   para después: tocan código que hoy funciona y las pruebas automáticas son pocas.
2. **Nombres y ubicación** de los archivos nuevos (`edu-ui.js`, `edu-shell.js`,
   `testing-panel.js`).
3. **Lo del "fallback crítico":** ¿sigue habiendo problemas de caché de estáticos en Render?
   Si sí, se conserva (o se resuelve con el manifiesto de WhiteNoise).

## 6. Orden de lectura para entender el archivo
1. Los bloques: líneas 105, 319–321, 408–409 y 1117 (qué puede rellenar una página).
2. Sidebar (175–312) y barra superior (317–381): el marcado que usan los recorridos.
3. Script 1 (483–668): las cuatro piezas de interfaz que usa toda la app.
4. Script 2 (672–944): cómo se comporta el esqueleto (sidebar, tema, menú "?").
5. Modo Testing (109–161 y 946–1113): aislado, solo para testers.
