"""Extract readable text from the Major/Minor handbook PDF.

Usage:
  python src/extract_handbook_text.py \
    --pdf data/IISER-P/Major-Minor-Req/maj-min.pdf \
    --out data/IISER-P/Major-Minor-Req/maj-min_extracted.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pypdf import PdfReader


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract text from handbook PDF")
    parser.add_argument("--pdf", required=True, help="Path to handbook PDF")
    parser.add_argument("--out", required=True, help="Path to extracted text file")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    out_path = Path(args.out)

    reader = PdfReader(str(pdf_path))
    pages = []
    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(f"\n\n===== PAGE {idx} =====\n\n{text}")

    combined = "".join(pages)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(combined, encoding="utf-8")

    print(f"pages={len(reader.pages)} chars={len(combined)} out={out_path}")


if __name__ == "__main__":
    main()
