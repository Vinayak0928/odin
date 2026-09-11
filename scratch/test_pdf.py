import sys
sys.stdout.reconfigure(encoding='utf-8')
from pypdf import PdfReader

path = r'd:\odin-dev\odin-dev\data\uploads\2026\09\11\8d30edf4ce874432b738323afde14646.pdf'
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
