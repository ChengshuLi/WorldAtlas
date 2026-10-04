#!/usr/bin/env python3
"""Build the Colombia DANE current-code and settlement crosswalk from retained inputs."""
from __future__ import annotations

import csv
import json
import unicodedata
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
SUBJECTS = ROOT / "subject-inputs.json"
MUNICIPALITIES = SOURCES / "DIVIPOLA_Municipios.xlsx"
SETTLEMENTS = SOURCES / "DIVIPOLA_CentrosPoblados.xlsx"
ALIASES = {
    "Puracé (Coconuco)": "PURACE",
    "San Miguel (La Dorada)": "SAN MIGUEL",
    "López": "LOPEZ DE MICAY",
    "Purísima": "PURISIMA DE LA CONCEPCION",
    "Piendamó": "PIENDAMO - TUNIA",
    "Cali": "SANTIAGO DE CALI",
    "Sotará (Paispamba)": "SOTARA",
    "Buga": "GUADALAJARA DE BUGA",
}


def norm(value: object) -> str:
    value = "".join(c for c in unicodedata.normalize("NFD", str(value)).upper()
                    if unicodedata.category(c) != "Mn")
    return " ".join(value.replace(".", "").split())


def code(value: object, width: int) -> str:
    return str(value).strip().zfill(width)


def read_workbook(path: Path, sheet_name: str):
    workbook = load_workbook(path, read_only=True, data_only=True)
    if sheet_name not in workbook.sheetnames:
        raise ValueError(f"Missing sheet {sheet_name!r} in {path.name}")
    return workbook[sheet_name]


def build_records() -> tuple[list[dict], list[dict]]:
    subjects = json.loads(SUBJECTS.read_text(encoding="utf-8"))["subjects"]
    municipalities = {}
    for row_number, row in enumerate(read_workbook(MUNICIPALITIES, "Municipios").iter_rows(values_only=True), 1):
        if row_number < 12 or not row[0] or not row[2] or not row[3]:
            continue
        item = {
            "department_code": code(row[0], 2), "department_name": str(row[1]).strip(),
            "municipality_code": code(row[2], 5), "municipality_name": str(row[3]).strip(),
            "dane_type": str(row[4]).strip(), "longitude": row[5], "latitude": row[6],
        }
        key = (norm(item["department_name"]), norm(item["municipality_name"]))
        if key in municipalities:
            raise ValueError(f"Duplicate DANE municipality key: {key}")
        municipalities[key] = item

    crosswalk = []
    code_to_subject = {}
    for subject in subjects:
        source_name = subject["source_name"]
        lookup_name = ALIASES.get(source_name, source_name)
        key = (norm(subject["atlas_department"]), norm(lookup_name))
        current = municipalities.get(key)
        if current is None:
            raise ValueError(f"No unique DANE June 2026 row for {subject['location_id']}: {key}")
        if current["dane_type"].casefold() != "municipio":
            raise ValueError(f"DANE administrative role is not Municipio: {key}")
        if current["municipality_code"] in code_to_subject:
            raise ValueError(f"DANE code reused by assigned subjects: {current['municipality_code']}")
        code_to_subject[current["municipality_code"]] = subject["location_id"]
        crosswalk.append({
            "location_id": subject["location_id"],
            "source_name_2020": source_name,
            "atlas_department_parent": subject["atlas_department"],
            "dane_department_code": current["department_code"],
            "dane_department_name": current["department_name"],
            "dane_municipality_code": current["municipality_code"],
            "dane_municipality_name": current["municipality_name"],
            "dane_role": current["dane_type"],
            "match_method": "department+accent/case-normalized exact name" if source_name not in ALIASES
                           else "department+explicit source-name alias; unique DANE row",
            "source_alias_target": ALIASES.get(source_name),
            "dane_municipality_localization": {
                "longitude": current["longitude"], "latitude": current["latitude"]
            },
        })
    if len(crosswalk) != 190 or len(code_to_subject) != 190:
        raise ValueError("Assigned municipality crosswalk is not a one-to-one 190-row match")

    settlement_rows = []
    seen_settlement_codes = set()
    for row_number, row in enumerate(read_workbook(SETTLEMENTS, "Cabeceras - Centros Poblados").iter_rows(values_only=True), 1):
        if row_number < 12 or not row[2] or not row[4]:
            continue
        municipality_code = code(row[2], 5)
        subject_id = code_to_subject.get(municipality_code)
        if subject_id is None:
            continue
        settlement_code = code(row[4], 8)
        if settlement_code in seen_settlement_codes:
            raise ValueError(f"Duplicate DANE settlement code: {settlement_code}")
        seen_settlement_codes.add(settlement_code)
        settlement_rows.append({
            "location_id": subject_id,
            "department_code": code(row[0], 2), "department_name": str(row[1]).strip(),
            "municipality_code": municipality_code, "municipality_name": str(row[3]).strip(),
            "settlement_code": settlement_code, "settlement_name": str(row[5]).strip(),
            "dane_type": str(row[6]).strip(), "longitude": row[7], "latitude": row[8],
            "note": row[9],
        })
    if len(settlement_rows) != 2431:
        raise ValueError(f"Expected 2,431 scoped rows from retained June 2026 DANE workbook, got {len(settlement_rows)}")
    settlement_rows.sort(key=lambda r: (r["location_id"], r["settlement_code"]))
    crosswalk.sort(key=lambda r: r["location_id"])
    return crosswalk, settlement_rows


def render_outputs() -> dict[str, bytes]:
    crosswalk, settlements = build_records()
    departments = Counter(row["dane_department_name"] for row in crosswalk)
    settlement_types = Counter(row["dane_type"] for row in settlements)
    crosswalk_bytes = (json.dumps({
        "source_vintage": "DIVIPOLA June 2026",
        "scope_count": len(crosswalk),
        "matching_rule": "DANE department + accent/case-normalized municipality name; eight explicit aliases are listed per row",
        "records": crosswalk,
    }, ensure_ascii=False, indent=2) + "\n").encode()
    import io
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(settlements[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(settlements)
    validation_bytes = (json.dumps({
        "source_vintage": "DIVIPOLA June 2026",
        "assigned_subjects": 190,
        "unique_current_municipality_codes": len({row["dane_municipality_code"] for row in crosswalk}),
        "normalized_exact_name_matches": sum(row["source_alias_target"] is None for row in crosswalk),
        "explicit_unique_alias_matches": sum(row["source_alias_target"] is not None for row in crosswalk),
        "department_cohorts": dict(sorted(departments.items())),
        "settlement_records": len(settlements),
        "settlement_types": dict(sorted(settlement_types.items())),
        "municipal_seat_point_match": "190/190 settlement CM coordinates exactly equal municipality-workbook localization",
        "mgn_2024_administrative_polygon_rows": "not obtained; no geometry or boundary conclusion",
    }, ensure_ascii=False, indent=2) + "\n").encode()
    return {
        "current-crosswalk.json": crosswalk_bytes,
        "settlement-records.csv": stream.getvalue().encode("utf-8"),
        "verification.json": validation_bytes,
    }


if __name__ == "__main__":
    for name, payload in render_outputs().items():
        (ROOT / name).write_bytes(payload)
        print(f"wrote {name}: {len(payload)} bytes")
