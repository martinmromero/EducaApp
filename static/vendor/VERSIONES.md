# Librerías de terceros incluidas en el proyecto

Se sirven desde el propio servidor (antes se pedían a CDN y a Google Fonts sin verificación de integridad). Para actualizar una,
descargar la versión nueva con el mismo nombre de archivo y correr `collectstatic`.

| Carpeta | Librería | Versión | Origen |
|---|---|---|---|
| bootstrap | Bootstrap (CSS y JS con Popper) | 5.3.0 | npm `bootstrap` |
| bootstrap-icons | Bootstrap Icons | 1.11.3 | npm `bootstrap-icons` |
| fonts | Inter, Montserrat, Public Sans, Bricolage Grotesque (latin) | fontsource 5.3.0 | npm `@fontsource/*` |
| pdfjs | PDF.js | 3.11.174 | npm `pdfjs-dist` (última con script clásico; se abre con `isEvalSupported:false`, ver CVE-2024-4367) |
| jszip | JSZip | 3.10.1 | npm `jszip` |
| docx-preview | docx-preview | 0.4.1 | npm `docx-preview` |
| jquery | jQuery | 3.7.1 | npm `jquery` (solo la pantalla clásica de subir preguntas) |

Fuera de esta carpeta: `static/js/vendor/driver.js.iife.js` y `static/css/vendor/driver.css` (driver.js, recorridos guiados).
