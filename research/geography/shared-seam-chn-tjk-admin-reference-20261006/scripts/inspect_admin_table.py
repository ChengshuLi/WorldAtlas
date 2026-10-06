#!/usr/bin/env python3
"""Inspect the retained official Tajik statistics workbook without third-party packages."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import zipfile
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
XLSX = ROOT / "sources/tajik-stat-admin-units-2025.xlsx"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def parse(path: pathlib.Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        strings = ["".join(t.text or "" for t in item.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
                   for item in shared_root]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        cells: dict[str, str] = {}
        for row in sheet.findall(".//m:row", NS):
            for cell in row.findall("m:c", NS):
                value = cell.find("m:v", NS)
                if value is not None and cell.attrib.get("t") == "s":
                    text = strings[int(value.text or "0")]
                elif value is not None:
                    text = value.text or ""
                else:
                    inline = cell.find("m:is", NS)
                    text = "".join(t.text or "" for t in inline.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")) if inline is not None else ""
                if text:
                    cells[cell.attrib["r"]] = text
    if "A1" not in cells:
        raise ValueError("Workbook has no title row")
    return cells


def check(cells: dict[str, str]) -> bool:
    # Bind literal source headers and values to worksheet coordinates. Do not infer
    # administrative classes from a possibly translated or ambiguous column label.
    expected = {
        "A1": "Number of administrative area units as of January 1, 2025",
        "B3": "Regions",
        "C3": "Towns",
        "E3": "Districts",
        "F3": "Colonies",
        "G3": "Number of",
        "C4": "total",
        "D4": "o/w  republican and regional submission",
        "G4": "jamoats",
        "A6": "GBAO",
        "B6": "7",
        "C6": "1",
        "D6": "1",
        "E6": "-",
        "F6": "4",
        "G6": "42",
    }
    return all(cells.get(coord) == value for coord, value in expected.items())


def main() -> None:
    raw = XLSX.read_bytes()
    with zipfile.ZipFile(XLSX) as archive:
        decoded_member_bytes = sum(member.file_size for member in archive.infolist())
    cells = parse(XLSX)
    if not check(cells):
        raise SystemExit("positive source/table assertions failed")
    mutated_header = dict(cells)
    mutated_header["B3"] = "Administrative districts"
    header_mutation_rejected = not check(mutated_header)
    mutated_value = dict(cells)
    mutated_value["B6"] = "8"
    value_mutation_rejected = not check(mutated_value)
    if not header_mutation_rejected or not value_mutation_rejected:
        raise SystemExit("negative control failed: altered header or cell was accepted")
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
        "source_title": cells["A1"],
        "reference_date": "2025-01-01",
        "gbao_row": {
            "Regions": 7,
            "Towns_total": 1,
            "Towns_of_which_republican_and_regional_submission": 1,
            "Districts": "-",
            "Colonies": 4,
            "Number_of_jamoats": 42,
        },
        "worksheet_headers": {
            "B3": cells["B3"], "C3": cells["C3"], "E3": cells["E3"],
            "F3": cells["F3"], "G3": cells["G3"], "C4": cells["C4"],
            "D4": cells["D4"], "G4": cells["G4"],
        },
        "gbao_cell_coordinates": {f"{column}6": cells[f"{column}6"] for column in "ABCDEFG"},
        "positive_control": "literal worksheet header coordinates and GBAO value coordinates parsed and linked exactly",
        "negative_controls": {
            "header_mutation_rejected": header_mutation_rejected,
            "value_mutation_rejected": value_mutation_rejected,
        },
        "negative_controls_passed": header_mutation_rejected and value_mutation_rejected,
        "geometry_present": False,
        "interpretation_limit": "Raw publisher column labels and values only; no reclassification into districts/towns or entity-level geometry inference.",
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
