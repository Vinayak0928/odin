import sys
import os
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
import pypdfium2 as pdfium
from rapidocr_onnxruntime import RapidOCR

BASE_DIR = Path(__file__).resolve().parent.parent
if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
    pdf_path = sys.argv[1]
else:
    candidates = list((BASE_DIR / 'data' / 'uploads').glob('**/*.pdf'))
    if not candidates:
        print("No PDF files found in data/uploads. Pass a path as an argument: python test_ocr.py <file.pdf>")
        sys.exit(0)
    pdf_path = str(candidates[0])

print(f"Loading PDF via pypdfium2: {pdf_path}")
pdf = pdfium.PdfDocument(pdf_path)
print(f"Total pages: {len(pdf)}")

engine = RapidOCR()

for page_idx in range(len(pdf)):
    page = pdf[page_idx]
    # Render page to PIL image at 200 DPI (scale 200/72 ≈ 2.77)
    bitmap = page.render(scale=2.0)
    pil_img = bitmap.to_pil()
    print(f"Page {page_idx + 1} rendered: {pil_img.size}")
    
    import numpy as np
    ocr_result, elapse = engine(np.array(pil_img))
    print(f"OCR finished in {elapse}s. Total detected text lines: {len(ocr_result) if ocr_result else 0}")
    if ocr_result:
        for item in ocr_result[:10]: # preview first 10
            print("  Line:", item[1], "Confidence:", round(float(item[2]), 2))
