import sys
import os
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent.parent
if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
    path = sys.argv[1]
else:
    candidates = list((BASE_DIR / 'data' / 'uploads').glob('**/*.pdf'))
    if not candidates:
        print("No PDF files found in data/uploads. Pass a path as an argument: python test_pdf.py <file.pdf>")
        sys.exit(0)
    path = str(candidates[0])

print(f"Loading PDF: {path}")
reader = PdfReader(path)
print(f"Total pages: {len(reader.pages)}")
for i, page in enumerate(reader.pages):
    txt = page.extract_text() or ""
    print(f"Page {i+1}: text_len={len(txt)}")
    if txt:
        print(f"--- Page {i+1} Sample ---\n{txt[:200]}\n--------------------")
    try:
        imgs = list(page.images)
        print(f"Page {i+1}: images={len(imgs)}")
    except Exception as e:
        print(f"Page {i+1}: images error: {e}")
