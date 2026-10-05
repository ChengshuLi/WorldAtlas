#!/usr/bin/env python3
"""Extract the commune columns from INSD's 2019 local poverty table."""
import csv
import hashlib
import pathlib
import re
import argparse

import pdfplumber

ROOT = pathlib.Path(__file__).resolve().parents[4]
OWNED = ROOT / "data/regional-review/regional-review-088ef1b8992c5b6c"
DEFAULT_PDF = OWNED / "sources/official-bfa/INSD-local-poverty-2019-report.pdf"
EXPECTED_PDF_SHA256 = "6e7c672523bd633189646e953a22586da0cb3b7940b4545478cad242649eb55a"
parser = argparse.ArgumentParser()
parser.add_argument("--source-pdf", type=pathlib.Path, default=DEFAULT_PDF,
                    help="exact restored original; verify the recorded hash before extraction")
PDF = parser.parse_args().source_pdf
if not PDF.is_file():
    raise SystemExit(f"Official PDF unavailable. Restore from https://www.insd.bf/sites/default/files/2024-10/EHCVM%202021_Rapport_IPM.pdf and verify SHA-256 {EXPECTED_PDF_SHA256}")

raw = PDF.read_bytes()
actual = hashlib.sha256(raw).hexdigest()
if actual != EXPECTED_PDF_SHA256:
    raise SystemExit(f"Official PDF hash mismatch: {actual}")


def normalize_words(words):
    text = " ".join(w["text"] for w in words).strip()
    text = re.sub(r"\s+", " ", text)
    return text.replace(" - ", "-").replace("- ", "-").replace(" -", "-")


rows = []
with pdfplumber.open(PDF) as pdf:
    # Annex 6 is printed pp. 53–62; zero-based PDF pages 70–79.
    if len(pdf.pages) != 130:
        raise SystemExit(f"Unexpected page count: {len(pdf.pages)}")
    for page_number in range(70, 80):
        page = pdf.pages[page_number]
        lines = {}
        for word in page.extract_words(x_tolerance=1, y_tolerance=2):
            if word["top"] < 205 or word["top"] > 780 or word["x0"] >= 285:
                continue
            y = round(word["top"] / 2) * 2
            group = lines.setdefault(y, [[], [], []])
            if word["x0"] < 130:
                group[0].append(word)
            elif word["x0"] < 195:
                group[1].append(word)
            else:
                group[2].append(word)
        for y in sorted(lines):
            region, province, commune = lines[y]
            if not commune:
                continue
            vals = [normalize_words(col) for col in (region, province, commune)]
            if vals[0].casefold() in ("région", "region") or vals[2].casefold() == "commune":
                continue
            rows.append({"page": page_number + 1, "region": vals[0], "province": vals[1], "commune": vals[2]})

if len(rows) > 351:
    raise SystemExit(f"Extracted more than the report's stated 351 commune rows: {len(rows)}")

output = OWNED / "evidence/bfa-insd-2019-commune-roster.csv"
with output.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["page", "region", "province", "commune"], lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
print(f"extracted_rows={len(rows)} stated_source_rows=351 csv_sha256={hashlib.sha256(output.read_bytes()).hexdigest()}")
