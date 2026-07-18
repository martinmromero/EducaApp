from pathlib import Path
from docx import Document

for name in ['test_single_export.docx', 'test_batch_export.docx']:
    path = Path('media/debug_exports') / name
    if not path.exists():
        continue
    doc = Document(path)
    print('---', name)
    for i, p in enumerate(doc.paragraphs[:12], start=1):
        t = p.text.strip()
        if t:
            print(i, t)
