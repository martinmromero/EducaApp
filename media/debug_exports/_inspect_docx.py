from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

root = Path('media/debug_exports')
docx_path = root / 'test_batch_export.docx'
if docx_path.exists():
    with zipfile.ZipFile(docx_path, 'r') as zf:
        xml = zf.read('word/document.xml')
    text = xml.decode('utf-8', errors='ignore')
    print('DOCX_HAS_VERSION_WORD', 'Version ' in text)
    print('DOCX_HAS_UNDERSCORES_PLACEHOLDER', '____________________' in text)

single_docx = root / 'test_single_export.docx'
if single_docx.exists():
    with zipfile.ZipFile(single_docx, 'r') as zf:
        xml = zf.read('word/document.xml')
    tree = ET.fromstring(xml)
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    merged_cells = tree.findall('.//w:vMerge', ns)
    print('DOCX_VERTICAL_MERGE_COUNT', len(merged_cells))
    east_asia = tree.findall('.//w:rFonts[@w:eastAsia]', ns)
    print('DOCX_EASTASIA_FONTS', len(east_asia))
