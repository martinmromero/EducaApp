# Limpieza de código, ronda 2 (parte B): sectores sin marcar, verificados sin llamadores (2026-10-17)

Estado antes de borrar: commit `18be49e`. Se buscaron rutas sin referencias (por nombre y por ruta literal en
plantillas, JS y Python), funciones sin usos y librerías sin imports; estos fueron los que no tenían ninguno.

| # | Sector | Archivo original | Líneas (en 18be49e) | Copia |
|---|---|---|---|---|
| 1 | Vista split_text_chunks | `material/views_document_processor.py` | 310-353 | `01_Vista_split_text_chunks.txt` |
| 2 | Vista serve_doc_file | `material/views_document_processor.py` | 2198-2230 | `02_Vista_serve_doc_file.txt` |
| 3 | URL split_text_chunks | `material/urls.py` | 89-89 | `03_URL_split_text_chunks.txt` |
| 4 | URL serve_doc_file | `material/urls.py` | 104-104 | `04_URL_serve_doc_file.txt` |
| 5 | material/serializers.py (archivo completo) | `material/serializers.py` | 1-8 | `05_material_serializers_py_archivo_completo.txt` |
| 6 | rest_framework en INSTALLED_APPS | `educaapp/settings.py` | 56-56 | `06_rest_framework_en_INSTALLED_APPS.txt` |
| 7 | djangorestframework en requirements.txt | `requirements.txt` | 6-6 | `07_djangorestframework_en_requirements_txt.txt` |
| 8 | djangorestframework en README | `README.md` | 142-142 | `08_djangorestframework_en_README.txt` |

## Cómo restaurar
- Cada `.txt` tiene el texto exacto, el archivo y las líneas de origen. Cualquier archivo completo se ve con `git show 18be49e:<ruta>`.
- Django REST Framework: volver a agregar `djangorestframework==3.16.0` a `requirements.txt`, `'rest_framework'` a
  `INSTALLED_APPS` y restaurar `material/serializers.py` (copia en `05_*.txt`). No hay migraciones involucradas.
- Esta carpeta no es código: los `.txt` no se importan ni los descubre ningún test.
