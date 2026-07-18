from pathlib import Path
import zipfile

docx_path = Path('media/debug_exports/test_export_via_view_width_fix.docx')
with zipfile.ZipFile(docx_path, 'r') as zf:
    xml = zf.read('word/document.xml').decode('utf-8', errors='ignore')
print('HAS_TBLIND_ZERO', '<w:tblInd w:w="0" w:type="dxa"' in xml)
print('HAS_LAYOUT_FIXED', '<w:tblLayout w:type="fixed"' in xml)
