from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

for name in ['test_single_export_latest.docx', 'test_batch_export_latest.docx']:
    p = Path('media/debug_exports') / name
    if not p.exists():
        continue
    with zipfile.ZipFile(p, 'r') as zf:
        xml = zf.read('word/document.xml')
    text = xml.decode('utf-8', errors='ignore')
    tree = ET.fromstring(xml)
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    merged_cells = tree.findall('.//w:vMerge', ns)
    east_asia = tree.findall('.//w:rFonts[@w:eastAsia]', ns)
    print('---', name)
    print('HAS_UNDERSCORE_PLACEHOLDER', '____________________' in text)
    print('VERTICAL_MERGE_COUNT', len(merged_cells))
    print('EASTASIA_COUNT', len(east_asia))
    print('HAS_2DO_PARCIAL_SLUG', '2do_parcial' in text)
