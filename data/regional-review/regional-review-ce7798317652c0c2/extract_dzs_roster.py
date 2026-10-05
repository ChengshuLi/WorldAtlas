#!/usr/bin/env python3
"""Restore and extract the complete DZS 2021 town/municipality detail roster."""
import argparse
import csv
import hashlib
from pathlib import Path

from build_assessment import read_xlsx_sheet

DETAIL_SHA256 = 'c2b1cff240a19b5bfbf6dcb5e919a264284dfa444a326adae5517bf39b6d7d42'


def extract(workbook: Path, output: Path):
    raw = workbook.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DETAIL_SHA256:
        raise ValueError('Restored official DZS workbook bytes differ from pinned SHA-256')
    rows = []
    for row_no, row in read_xlsx_sheet(workbook, '1.'):
        if row_no < 9:
            continue
        county, kind, county_en, kind_en, name = (row.get(k, '') for k in 'ABCDE')
        if kind in ('Grad', 'Općina') and name:
            rows.append({'source_row': row_no, 'county': county, 'kind': kind,
                         'county_en': county_en, 'kind_en': kind_en, 'name': name})
    if len(rows) != 555:
        raise ValueError(f'Expected 555 official local-government rows, received {len(rows)}')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    print(f'rows={len(rows)} source_sha256={hashlib.sha256(raw).hexdigest()} extract_sha256={hashlib.sha256(output.read_bytes()).hexdigest()} bytes={output.stat().st_size}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workbook', required=True, help='Exact DZS workbook restored from SOURCES.md')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    extract(Path(args.workbook), Path(args.output))
