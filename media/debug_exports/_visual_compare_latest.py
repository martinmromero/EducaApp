from pathlib import Path
import subprocess
from PIL import Image, ImageChops, ImageStat
import win32com.client

root = Path(r"C:/Users/marti/OneDrive/tesis/educaapp")
out = root / 'media' / 'debug_exports'
out.mkdir(parents=True, exist_ok=True)

pdftoppm = Path(r"C:/Users/marti/AppData/Local/Microsoft/WinGet/Packages/oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe/poppler-25.07.0/Library/bin/pdftoppm.exe")

pairs = [
    ('test_single_export_latest.docx', 'test_single_export_latest.pdf', 'cmp_single_latest'),
    ('test_batch_export_latest.docx', 'test_batch_export_latest.pdf', 'cmp_batch_latest'),
]

word = win32com.client.Dispatch('Word.Application')
word.Visible = False
try:
    for docx_name, _, prefix in pairs:
        docx_path = (out / docx_name).resolve()
        if not docx_path.exists():
            continue
        converted_pdf = out / f'{prefix}_from_docx.pdf'
        doc = word.Documents.Open(str(docx_path))
        doc.SaveAs(str(converted_pdf.resolve()), FileFormat=17)
        doc.Close(False)
finally:
    word.Quit()

report_lines = []
for _, native_pdf_name, prefix in pairs:
    native_pdf = out / native_pdf_name
    docx_pdf = out / f'{prefix}_from_docx.pdf'
    if not native_pdf.exists() or not docx_pdf.exists():
        continue

    native_prefix = out / f'{prefix}_native'
    docx_prefix = out / f'{prefix}_docxpdf'

    subprocess.run([str(pdftoppm), '-png', str(native_pdf), str(native_prefix)], check=True)
    subprocess.run([str(pdftoppm), '-png', str(docx_pdf), str(docx_prefix)], check=True)

    native_pages = sorted(out.glob(f'{native_prefix.name}-*.png'))
    docx_pages = sorted(out.glob(f'{docx_prefix.name}-*.png'))
    page_count = min(len(native_pages), len(docx_pages))
    report_lines.append(f'=== {prefix} ===')
    report_lines.append(f'native_pages={len(native_pages)} docx_pdf_pages={len(docx_pages)} compared={page_count}')

    diff_dir = out / f'{prefix}_diff'
    diff_dir.mkdir(parents=True, exist_ok=True)

    for i in range(page_count):
        n_img = Image.open(native_pages[i]).convert('RGB')
        d_img = Image.open(docx_pages[i]).convert('RGB')
        if n_img.size != d_img.size:
            d_img = d_img.resize(n_img.size)

        diff = ImageChops.difference(n_img, d_img)
        stat = ImageStat.Stat(diff)
        mean_diff = sum(stat.mean) / (len(stat.mean) * 255.0)
        diff_pct = mean_diff * 100

        diff_out = diff_dir / f'page_{i+1:03d}.png'
        diff.save(diff_out)
        report_lines.append(f'page {i+1}: mean_diff_pct={diff_pct:.2f} diff_image={diff_out.name}')

report_path = out / 'visual_compare_report_latest.txt'
report_path.write_text('\n'.join(report_lines), encoding='utf-8')
print(report_path)
print('\n'.join(report_lines))
