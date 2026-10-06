#!/usr/bin/env python3
"""Inspect the retained official Tajik statistics workbook without third-party packages."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
XLSX = ROOT / "sources/tajik-stat-admin-units-2025.xlsx"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def parse(path: pathlib.Path) -> tuple[str, list[list[str]]]:
    with zipfile.ZipFile(path) as archive:
        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        strings = ["".join(t.text or "" for t in item.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
                   for item in shared_root]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows: list[list[str]] = []
        for row in sheet.findall(".//m:row", NS):
            values: list[str] = []
            for cell in row.findall("m:c", NS):
                value = cell.find("m:v", NS)
                if value is None:
                    values.append("")
                elif cell.attrib.get("t") == "s":
                    values.append(strings[int(value.text or "0")])
                else:
                    values.append(value.text or "")
            rows.append(values)
    if not rows or not rows[0]:
        raise ValueError("Workbook has no title row")
    return rows[0][0], rows


def check(rows: list[list[str]]) -> bool:
    if not rows or rows[0][0] != "Number of administrative area units as of January 1, 2025":
        return False
    row = next((r for r in rows if r and r[0] == "GBAO"), None)
    # Preserve the publisher's literal English headers. Do not infer administrative
    # classes from a possibly translated or ambiguous column label.
    if row is None or row[1:] != ["7", "1", "1", "-", "4", "42"]:
        return False
    return not any("geometry" in cell.lower() or "boundary coordinates" in cell.lower()
                   for row in rows for cell in row)


def main() -> None:
    raw = XLSX.read_bytes()
    with zipfile.ZipFile(XLSX) as archive:
        decoded_member_bytes = sum(member.file_size for member in archive.infolist())
    title, rows = parse(XLSX)
    if not check(rows):
        raise SystemExit("positive source/table assertions failed")
    mutated = [row[:] for row in rows]
    gbao = next(row for row in mutated if row and row[0] == "GBAO")
    gbao[1] = "8"
    negative_mutation_rejected = not check(mutated)
    if not negative_mutation_rejected:
        raise SystemExit("negative control failed: mutated GBAO count was accepted")
    execution_commit = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    result = {
        "version": 1,
        "execution_commit": execution_commit,
        "script_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_encoded_bytes": len(raw),
        "decoded_zip_member_bytes_sum": decoded_member_bytes,
        "source_title": title,
        "reference_date": "2025-01-01",
        "gbao_row": {
            "Regions": 7,
            "Towns_total": 1,
            "Towns_of_which_republican_and_regional_submission": 1,
            "Districts": "-",
            "Colonies": 4,
            "Number_of_jamoats": 42,
        },
        "positive_control": "official workbook title, literal headers and GBAO cells parsed exactly",
        "negative_control": "mutated GBAO cell under literal Regions header rejected by the same table assertion",
        "negative_control_passed": negative_mutation_rejected,
        "geometry_present": False,
        "interpretation_limit": "Raw publisher column labels and values only; no reclassification into districts/towns or entity-level geometry inference.",
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
