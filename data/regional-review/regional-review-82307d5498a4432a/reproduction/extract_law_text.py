#!/usr/bin/env python3
"""Extract embedded text from the retained 2025-05-05 regional law PDF."""
import pathlib
from pypdf import PdfReader
root = pathlib.Path(__file__).resolve().parents[1]
pdf = root / "source/kemerovo-law-104-OZ-consolidated-to-2025-05-05.pdf"
out = root / "source/kemerovo-law-104-OZ-consolidated-to-2025-05-05.txt"
reader = PdfReader(str(pdf))
text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
out.write_text(text, encoding="utf-8")
print(f"pages={len(reader.pages)} characters={len(text)}")
