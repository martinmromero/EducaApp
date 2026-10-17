# Limpieza de código, ronda 2: sectores eliminados (2026-10-17)

Estado del código ANTES de borrar: commit `b90b896`. Cada sector marcado como "CANDIDATO A BORRAR" se
copió acá con su ubicación exacta y recién después se quitó del código.

| # | Sector | Archivo original | Líneas (en b90b896) | Copia |
|---|---|---|---|---|
| 1 | Modelo InstitutionLog | `material/models.py` | 234-259 | `01_Modelo_InstitutionLog.txt` |
| 2 | Vista institution_v2_logs | `material/views.py` | 6203-6216 | `02_Vista_institution_v2_logs.txt` |
| 3 | Lectura de InstitutionLog en institution_v2_detail | `material/views.py` | 6232-6238 | `03_Lectura_de_InstitutionLog_en_institution_v2_detail.txt` |
| 4 | InstitutionLog.create en create_exam_template | `material/views.py` | 2547-2552 | `04_InstitutionLog_create_en_create_exam_template.txt` |
| 5 | Borrado de InstitutionLog al eliminar institución (1 de 2) | `material/views.py` | 6127-6130 | `05_Borrado_de_InstitutionLog_al_eliminar_instituci_n_1_de_2.txt` |
| 6 | Borrado de InstitutionLog al eliminar institución (2 de 2) | `material/views.py` | 6172-6174 | `06_Borrado_de_InstitutionLog_al_eliminar_instituci_n_2_de_2.txt` |
| 7 | Import de InstitutionLog en views.py | `material/views.py` | 634-634 | `07_Import_de_InstitutionLog_en_views_py.txt` |
| 8 | Vista download_template | `material/views.py` | 5453-5518 | `08_Vista_download_template.txt` |
| 9 | Rama POST de edit_exam_template | `material/views.py` | 2723-2810 | `09_Rama_POST_de_edit_exam_template.txt` |
| 10 | URL institution_v2_logs | `material/urls.py` | 122-122 | `10_URL_institution_v2_logs.txt` |
| 11 | URL download_template | `material/urls.py` | 72-72 | `11_URL_download_template.txt` |
| 12 | Comentario "tal vez sea obsoleto" de get-learning-outcomes | `material/urls.py` | 196-196 | `12_Comentario_tal_vez_sea_obsoleto_de_get_learning_outcomes.txt` |
| 13 | Comentario CANDIDATO A BORRAR en UserEditForm | `material/forms.py` | 482-492 | `13_Comentario_CANDIDATO_A_BORRAR_en_UserEditForm.txt` |
| 14 | InstitutionLog en wipe_production_content (import) | `material/management/commands/wipe_production_content.py` | 38-38 | `14_InstitutionLog_en_wipe_production_content_import.txt` |
| 15 | InstitutionLog en wipe_production_content (lista de modelos) | `material/management/commands/wipe_production_content.py` | 56-56 | `15_InstitutionLog_en_wipe_production_content_lista_de_modelos.txt` |
| 16 | Import de InstitutionLog en tests.py | `material/tests.py` | 6-6 | `16_Import_de_InstitutionLog_en_tests_py.txt` |
| 17 | institution_v2_logs en tests_qa_smoke | `material/tests_qa_smoke.py` | 46-46 | `17_institution_v2_logs_en_tests_qa_smoke.txt` |
| 18 | Plantilla institutions_v2/logs.html | `material/templates/material/institutions_v2/logs.html` | 1-75 | `18_Plantilla_institutions_v2_logs_html.txt` |

## Cómo restaurar
- Todo el texto exacto de cada sector está en su archivo `.txt` de esta carpeta, con el archivo y las líneas de origen.
- También se puede ver cualquier archivo completo como estaba: `git show b90b896:<ruta>`.
- Modelo `InstitutionLog`: además de pegar la clase en `material/models.py`, hay que revertir la migración
  `0108_delete_institutionlog` (`python manage.py migrate material 0107`) o escribir una migración `CreateModel` nueva.
  La tabla se eliminó con los datos que tuviera (nada los escribía).
- Esta carpeta no es código: los `.txt` no se importan ni los descubre ningún test.
