from pathlib import Path
try:
    from pypdf import PdfReader
except Exception as e:
    print('PYPDF_IMPORT_ERROR', e)
    raise SystemExit(0)

for name in ['test_single_export.pdf', 'test_batch_export.pdf']:
    path = Path('media/debug_exports') / name
    if not path.exists():
        continue
    reader = PdfReader(str(path))
    text = '\n'.join((page.extract_text() or '') for page in reader.pages)
    print('---', name)
    print('HAS_UNDERSCORE_PLACEHOLDER', '____________________' in text)
    first_lines = [ln.strip() for ln in text.splitlines() if ln.strip()][:12]
    for i, ln in enumerate(first_lines, start=1):
        print(i, ln)
