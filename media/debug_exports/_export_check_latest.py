from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'educaapp.settings')
django.setup()

from material.models import Exam, ExamVersionBatch
from material.document_builder import build_document_payload
from material.print_format_utils import resolve_print_format_for_exam
from material.renderers import (
    render_exam_payload_to_pdf,
    render_exam_payload_to_docx,
    render_exam_batch_payloads_to_pdf,
    render_exam_batch_payloads_to_docx,
)

out = ROOT / 'media' / 'debug_exports'
out.mkdir(parents=True, exist_ok=True)
exam = Exam.objects.order_by('-id').first()
assert exam is not None, 'No hay examenes'
formato = resolve_print_format_for_exam(exam)
payload = build_document_payload(exam, kind='exam', include_answers=False, include_rubrics=True)
(out / 'test_single_export_latest.pdf').write_bytes(render_exam_payload_to_pdf(payload, formato))
(out / 'test_single_export_latest.docx').write_bytes(render_exam_payload_to_docx(payload, formato))

batch = ExamVersionBatch.objects.order_by('-id').first()
if batch:
    versions = list(batch.versions.all().order_by('version_number', 'id'))
    docs = [
        {
            'payload': build_document_payload(e, kind='exam', include_answers=False, include_rubrics=True),
            'formato': resolve_print_format_for_exam(e),
            'label': f'Version {e.version_number or i}',
        }
        for i, e in enumerate(versions, start=1)
    ]
    (out / 'test_batch_export_latest.pdf').write_bytes(render_exam_batch_payloads_to_pdf(docs))
    (out / 'test_batch_export_latest.docx').write_bytes(render_exam_batch_payloads_to_docx(docs))

print('OK latest generated', exam.id, bool(batch))
