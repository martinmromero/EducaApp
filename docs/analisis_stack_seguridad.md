# Estado del stack y sugerencias de actualización (31/10/2026)

Pedido (V32): no solo Python; evaluar todo el stack y decir qué conviene actualizar, sobre todo por seguridad. Con eso se
actualiza el stack y, después, el texto de la tesis.

Qué está verificado y qué no: los hallazgos 1, 2 y 3 los confirmé en fuentes oficiales o en los avisos de seguridad
(enlaces al final). Los demás salen de comparar la versión del repositorio con la última publicada (`pip list --outdated`,
31/10/2026) y **no afirmo vulnerabilidades que no pude confirmar**; se marcan «revisar».

## 0. Estado: aplicado el 31/10/2026

Se actualizó lo urgente y lo de la tabla 2 que no tiene riesgo, **y se probó antes de subirlo**: entorno nuevo con Python 3.13,
suite completa (**487 pruebas en verde**), `manage.py check` y `check --deploy` (con `DEBUG` apagado) sin observaciones,
páginas principales, exportación a PDF/DOCX y los asistentes recorridos en el navegador.

| Componente | Antes | Ahora |
|---|---|---|
| Django | 4.2.20 | **5.2.18 (LTS)** |
| gunicorn | 21.2.0 | **26.2.0** |
| requests | 2.31.0 | **2.34.2** |
| cryptography | ≥ 42 (sin tope) | **50.0.2** |
| whitenoise / psycopg2-binary / dj-database-url | 6.7.0 / 2.9.9 / 2.2.0 | 6.12.0 / 2.9.13 / 3.1.2 |
| python-docx / python-pptx | 0.8.11 / 0.6.23 | **1.2.0 / 1.0.2** |
| reportlab / django-crispy-forms / django-extensions | ≥4,<5 / 2.4 / 3.2.3 | 5.1.0 / 2.7 / 4.1 |
| tiktoken / pdf-inspector | 0.12.0 / 1.14.1 | 0.14.0 / 1.25.2 |
| PyMuPDF | 1.26.5 | 1.26.5 (se deja: 2.0 es un salto mayor) |
| Python (`render.yaml`, `Dockerfile`) | 3.11.0 / 3.11 | **3.13.3 / 3.13** |

Cambios de código que hicieron falta: en Django 5.1 desapareció `STATICFILES_STORAGE` (ahora va en `STORAGES`) y se agregó
`FORMS_URLFIELD_ASSUME_HTTPS = True` (transición a Django 6). Nada más falló.

`requirements.txt` quedó con **versiones exactas** y `requirements.lock` guarda el conjunto completo probado, para que el
despliegue instale lo mismo que se probó. **Todo corre también con Python 3.11** (el mínimo que exige alguna dependencia es
3.11): aunque en el panel de Render siga `PYTHON_VERSION` en 3.11, el despliegue funciona. Subirla a 3.13.3 en el panel es
una mejora opcional.

Queda pendiente del punto 2: vendorizar Bootstrap, los iconos y las fuentes (o agregar SRI), y la revisión del aviso
CVE-2024-47081 de requests (ya queda cubierto: se instaló 2.34.2).

## 1. Urgente

| # | Componente | En el repositorio | Situación | Qué hacer |
|---|---|---|---|---|
| 1 | **Django** | 4.2.20 | **4.2 LTS dejó de recibir correcciones el 7/4/2026.** Además 4.2.20 es anterior a todas las correcciones de seguridad posteriores de la rama 4.2 (la última fue la 4.2.30). | Pasar a **Django 5.2 LTS** (soporte extendido hasta abril de 2028). No conviene 6.0 (seguridad solo hasta abril de 2027) ni 6.1 (no es LTS). La próxima LTS (6.2) sale en abril de 2027. |
| 2 | **gunicorn** | 21.2.0 | Vulnerable a **CVE-2024-1135** (contrabando de pedidos HTTP por validación débil de `Transfer-Encoding`); corregido en 22.0.0. Render pone un proxy delante, lo que baja el riesgo, pero no hay motivo para dejarlo. | Subir a la última 23.x. Revisar que no dependamos de pedidos con `Transfer-Encoding` y `Content-Length` juntos (22 los rechaza). |
| 3 | **requests** | 2.31.0 | Alcanzada por **CVE-2024-35195** (corregida en 2.32.2). Existe también un aviso posterior sobre credenciales de `.netrc` (CVE-2024-47081) que recuerdo corregido en 2.32.4: **revisar en el aviso oficial**. | Subir a 2.34.x (la última). Se usa para hablar con los proveedores de IA. |
| 4 | **Python en producción** | `render.yaml` dice `3.11.0`; el `Dockerfile` usa 3.11-slim; en tu PC corre 3.13.3; la tesis dice 3.13+ | 3.11.0 es la primera versión de la rama (octubre de 2022) y ya tiene muchas correcciones de seguridad posteriores; la rama 3.11 recibe seguridad hasta octubre de 2027. **La variable real es la del panel de Render** (no `render.yaml`): hoy no sé cuál tiene. | Unificar en una sola versión para desarrollo, Docker y Render: **3.13** (soporte hasta octubre de 2029), usando el último parche. Es lo que ya usa tu equipo y lo que dice la tesis. |

## 2. Conviene (sin urgencia de seguridad confirmada)

| Componente | Repositorio → última | Comentario |
|---|---|---|
| python-docx | 0.8.11 → 1.2.0 | La 0.8.11 es de 2021; la 1.x es la rama mantenida. Se usa para exportar DOCX: probar los exámenes exportados. |
| python-pptx | 0.6.23 → 1.0.2 | Igual: rama 1.x mantenida. Se usa solo para leer presentaciones. |
| psycopg2-binary | 2.9.9 → 2.9.13 | Actualización de rutina. |
| whitenoise | 6.7.0 → versión actual 6.x | Compatible con Django 5.2; subir junto con Django. |
| dj-database-url | 2.2.0 → 3.x | Revisar cambios antes de subir. |
| django-crispy-forms / crispy-bootstrap5 | 2.4 → 2.7 / 2026.9 | Subir con Django 5.2 (versiones compatibles). |
| django-extensions | 3.2.3 → 4.1 | Solo desarrollo. |
| reportlab | `>=4,<5` (local tiene 5.0) | El rango no coincide con lo instalado localmente: **fijar la versión** y probar los PDF. |
| tiktoken, pdf-inspector, PyMuPDF | 0.12 → 0.14 / 1.14 → 1.25 / 1.26.5 → 2.0 | PyMuPDF 2.0 es salto mayor: no subir sin probar la lectura de PDF. |
| Bootstrap (CDN) | 5.3.0 → última 5.3.x; bootstrap-icons 1.10.0 → 1.13.x | Se cargan de jsDelivr **sin verificación de integridad (SRI)**: o se vendorizan (como driver.js) o se agrega el hash. Mejora seguridad y también la contingencia sin internet. |
| Google Fonts | CDN | Ya piden solo la fuente del tema; vendorizarlas también evita depender de un tercero (y de la privacidad que la tesis defiende). |
| sqlparse, certifi, cryptography, Pillow | pequeñas diferencias | Se actualizan solas al reinstalar; `cryptography>=42` sin tope está bien. |

## 3. Cosas que no son versiones pero afectan la seguridad

- **Licencia de PyMuPDF**: es AGPL-3.0 (o comercial). Para el código abierto de una tesis no es problema; si algún día se ofrece como servicio a terceros hay que revisarlo. Dejarlo anotado en la tesis (sección de tecnologías).
- **Build sin fijar todo**: `requirements.txt` fija solo algunos paquetes; el resto se instala en la última versión que haya el día del despliegue. Para reproducibilidad: generar un `requirements.lock` (o `pip freeze`) y desplegar con ese.
- **Cabeceras de seguridad** (`SECURE_*`, HSTS, cookies seguras): revisar `settings.py` antes de publicar al jurado; es un chequeo de 15 minutos con `manage.py check --deploy`.

## 4. Plan propuesto (en este orden)

1. **Rama de prueba**: crear un entorno nuevo con Django 5.2, gunicorn 23, requests 2.34 y Python 3.13, y correr los 470 tests ya existentes. Cualquier fallo me dice exactamente qué cambió.
2. Corregir lo que falle (lo esperable: avisos de funciones retiradas en Django 5.x, pequeñas diferencias en `crispy` y en las fechas).
3. Subir python-docx/pptx y probar a mano una exportación a DOCX y la lectura de un PPTX.
4. Fijar versiones en un `requirements.lock`, actualizar `Dockerfile`, `render.yaml` y la variable `PYTHON_VERSION` en el panel de Render.
5. Vendorizar Bootstrap, iconos y fuentes (o SRI).
6. Desplegar y probar el recorrido del jurado (V23).
7. Recién entonces actualizar el texto de la tesis (versiones reales, Django 5.2 LTS, Python 3.13).

Costo estimado: pasos 1 a 4, una jornada de trabajo si los tests alcanzan; el 5 y el 6, media jornada más.

## Fuentes

- Django, versiones soportadas y fin del soporte de 4.2: https://www.djangoproject.com/download/ y https://endoflife.date/django
- Avisos de seguridad de Django (4.2.30, 5.2.13, 6.0.4): https://www.djangoproject.com/weblog/2026/apr/07/security-releases/
- gunicorn, CVE-2024-1135: https://advisories.gitlab.com/pypi/gunicorn/CVE-2024-1135/ y https://www.github.com/benoitc/gunicorn/releases
- requests, CVE-2024-35195 (corregido en 2.32.2): https://codeberg.org/saaste/fmi-weather-client/issues/56
