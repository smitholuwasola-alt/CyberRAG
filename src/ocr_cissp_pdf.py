"""
OCR the scanned CISSP 250 PDF into a plain-text file the existing parser can read.

Uses PyMuPDF (fitz) to rasterize each page, then easyocr (pure-Python, no Tesseract
binary needed) to recognize text. Writes one "--- PAGE N ---" separator per page.

    python src/ocr_cissp_pdf.py \
      --pdf "data/0 CISSP Final 250  Exam Ques.pdf" \
      --out data/qa/cissp_ocr.txt
"""

from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path


def ocr_pdf(pdf_path: Path, out_path: Path, dpi: int = 220, gpu: bool = True) -> None:
    import fitz  # PyMuPDF
    import easyocr
    import numpy as np
    from PIL import Image

    if not pdf_path.is_file():
        raise SystemExit(f"PDF not found: {pdf_path}")

    use_gpu = gpu
    if use_gpu:
        try:
            import torch
            if not torch.cuda.is_available():
                use_gpu = False
        except Exception:
            use_gpu = False
    print(f"Loading easyocr model (GPU={use_gpu})…", flush=True)
    reader = easyocr.Reader(["en"], gpu=use_gpu, verbose=False)

    doc = fitz.open(str(pdf_path))
    total = len(doc)
    print(f"Rasterizing + OCR-ing {total} pages at {dpi} dpi…", flush=True)

    parts = []
    t0 = time.time()
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        arr = np.array(img)
        lines = reader.readtext(arr, detail=0, paragraph=True)
        parts.append(f"--- PAGE {i + 1} ---\n" + "\n".join(lines))
        if (i + 1) % 3 == 0 or (i + 1) == total:
            elapsed = time.time() - t0
            per_page = elapsed / (i + 1)
            eta = per_page * (total - (i + 1))
            print(f"  page {i+1}/{total}  ({per_page:.1f}s/page, ETA {eta:.0f}s)", flush=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n\n".join(parts), encoding="utf-8")
    print(f"Wrote {total} pages -> {out_path}  ({out_path.stat().st_size} bytes)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dpi", type=int, default=220)
    ap.add_argument("--no-gpu", action="store_true", help="Force CPU OCR")
    args = ap.parse_args()
    ocr_pdf(Path(args.pdf), Path(args.out), dpi=args.dpi, gpu=not args.no_gpu)


if __name__ == "__main__":
    main()
