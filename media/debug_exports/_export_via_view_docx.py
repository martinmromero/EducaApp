from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'educaapp.settings')
django.setup()

from django.test import RequestFactory
from material.models import Exam
from material.views_export import exportar_examen_docx

exam = Exam.objects.order_by('-id').first()
assert exam is not None, 'No hay examenes para exportar'
assert exam.created_by is not None, 'El examen no tiene created_by'

rf = RequestFactory()
request = rf.get('/material/examen/export/docx/')
request.user = exam.created_by

response = exportar_examen_docx(request, exam.pk)
assert response.status_code == 200, f'Status inesperado: {response.status_code}'

out_dir = ROOT / 'media' / 'debug_exports'
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / 'test_export_via_view_width_fix.docx'
out_path.write_bytes(response.content)
print(out_path)
