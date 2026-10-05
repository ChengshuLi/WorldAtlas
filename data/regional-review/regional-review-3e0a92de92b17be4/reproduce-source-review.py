#!/usr/bin/env python3
"""Reproduce the scoped Croatia ADM2 name/parent crosswalk for issue #418.

Inputs are deliberately not redistributed with this packet because the source
license metadata conflicts with the source provider's current license terms.
Restore exact bytes from the URLs recorded in findings.md, then pass their
paths to this script. The script uses only Python's standard library.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import posixpath
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SCOPE = HERE / "scope-from-issue.json"
ISSUE = HERE / "issue-418-api-snapshot.json"
INVENTORY = REPO / "data/macro-foundation/current-membership-inventory.json.gz"
GEBOUNDARY_SHA256 = "bfcda6087b26678f026c2a1ac5c4fe903bd67ad24a7c9761519f7929b3915d16"
DZS_SHA256 = "c2b1cff240a19b5bfbf6dcb5e919a264284dfa444a326adae5517bf39b6d7d42"
MURTER_KORNATI_NAME_CANDIDATE = "gb:HRV:ADM2:41942358B86068104638384"
COUNTY_NAMES = {
    "Istria": "Istarska",
    "Karlovac": "Karlovačka",
    "Krapina-Zagorje": "Krapinsko-zagorska",
    "Lika-Senj": "Ličko-senjska",
    "Primorje-Gorski Kotar": "Primorsko-goranska",
    "Šibenik-Knin": "Šibensko-kninska",
    "Zadar County": "Zadarska",
}
NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized_name(value: str) -> str:
    # DZS may publish the Croatian and Italian forms separated by an en dash.
    primary = re.split(r"\s+[–—]\s+", value.strip(), maxsplit=1)[0]
    primary = re.sub(r"^(Općina|Grad|Otok|Opicina)\s+", "", primary, flags=re.I)
    decomposed = unicodedata.normalize("NFD", primary.lower())
    return "".join(char for char in decomposed if char.isalnum())


def embedded_issue_scope() -> dict:
    issue = json.loads(ISSUE.read_text(encoding="utf-8"))
    body = issue.get("body", "")
    for match in re.finditer(r"```json\s*(\{[\s\S]*?\})\s*```", body):
        candidate = json.loads(match.group(1))
        if candidate.get("batch_id") == "regional-review:3e0a92de92b17be4":
            return candidate
    raise ValueError("Exact #418 workload scope JSON was not found in the API snapshot")


def shared_strings(book: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(book.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(node.text or "" for node in item.findall(".//m:t", NS))
            for item in root.findall("m:si", NS)]


def census_sheet_path(book: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(book.read("xl/workbook.xml"))
    sheet = next((node for node in workbook.findall(".//m:sheet", NS)
                  if node.attrib.get("name") == sheet_name), None)
    if sheet is None:
        raise ValueError(f"DZS workbook has no {sheet_name!r} worksheet")
    relationship_id = sheet.attrib[f"{{{NS['r']}}}id"]
    relations = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
    target = next(node.attrib["Target"] for node in relations.findall("pkg:Relationship", NS)
                  if node.attrib.get("Id") == relationship_id)
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join("xl", target))


def read_dzs_local_units(path: Path) -> dict[str, set[str]]:
    with zipfile.ZipFile(path) as book:
        strings = shared_strings(book)
        sheet_path = census_sheet_path(book, "7.")
        root = ET.fromstring(book.read(sheet_path))
    roster: dict[str, set[str]] = defaultdict(set)
    for row in root.findall(".//m:sheetData/m:row", NS):
        values: dict[str, str] = {}
        for cell in row.findall("m:c", NS):
            ref = cell.attrib.get("r", "")
            col = re.match(r"[A-Z]+", ref)
            if not col:
                continue
            cell_value = cell.find("m:v", NS)
            if cell_value is None or cell_value.text is None:
                inline = cell.find("m:is", NS)
                text = "" if inline is None else "".join(
                    node.text or "" for node in inline.findall(".//m:t", NS))
            elif cell.attrib.get("t") == "s":
                text = strings[int(cell_value.text)]
            else:
                text = cell_value.text
            values[col.group(0)] = text.strip()
        county, unit_type, unit_name = values.get("A"), values.get("B"), values.get("E")
        if county and unit_type in {"Grad", "Općina"} and unit_name:
            roster[county].add(unit_name)
    return roster


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--geoboundaries", required=True, type=Path,
                        help="exact geoBoundaries HRV ADM2 simplified GeoJSON")
    parser.add_argument("--dzs-census", required=True, type=Path,
                        help="exact DZS 2021 population-by-town/municipality XLSX")
    args = parser.parse_args()
    for path, expected, label in (
        (args.geoboundaries, GEBOUNDARY_SHA256, "geoBoundaries simplified GeoJSON"),
        (args.dzs_census, DZS_SHA256, "DZS 2021 census workbook"),
    ):
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"{label} SHA-256 mismatch: expected {expected}, got {actual}")

    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    issue_scope = embedded_issue_scope()
    ids = scope["member_location_ids"]
    if len(ids) != 206 or len(set(ids)) != 206 or set(ids) != set(issue_scope["member_location_ids"]):
        raise ValueError("scope-from-issue.json does not reproduce the exact 206 issue IDs")

    with gzip.open(INVENTORY, "rt", encoding="utf-8") as stream:
        inventory = json.load(stream)
    parents: dict[str, tuple[str, str]] = {}
    for item in inventory:
        if item.get("level") != "province":
            continue
        for member in item.get("member_location_ids", []):
            if member in set(ids):
                if member in parents:
                    raise ValueError(f"multiple direct province parents for {member}")
                parents[member] = (item["id"], item["name"])
    if set(parents) != set(ids):
        raise ValueError("not every scoped ID has exactly one direct province parent")

    geo = json.loads(args.geoboundaries.read_text(encoding="utf-8"))
    features = {
        "gb:HRV:ADM2:" + feature.get("properties", {}).get("shapeID", ""): feature["properties"]
        for feature in geo.get("features", [])
    }
    source_ids = set(ids) - {"atlas:city:HRV-1589"}
    if len(geo.get("features", [])) != 560 or not source_ids.issubset(features):
        raise ValueError("pinned simplified source does not contain all 205 scoped source IDs")
    if len(source_ids.intersection(features)) != 205:
        raise ValueError("expected 205 exact geoBoundaries feature joins")

    roster = read_dzs_local_units(args.dzs_census)
    report_rows = []
    county_summary = {}
    missing_units = {}
    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for member in source_ids:
        parent_id, parent_name = parents[member]
        children_by_parent[parent_name].append(member)
    for parent_name, children in sorted(children_by_parent.items()):
        dzs_county = COUNTY_NAMES[parent_name]
        official_units = roster[dzs_county]
        matched_names = set()
        candidate_names = set()
        for member in sorted(children):
            source_name = features[member]["shapeName"]
            match = next((name for name in official_units
                          if normalized_name(name) == normalized_name(source_name)), None)
            if source_name.startswith("Otok ") and match:
                assessment = "correction-needed"
                role = f"island-labeled feature normalizes to DZS 2021 local-government name {match!r}; name correspondence does not establish that the feature is the municipality extent or verify legal host, identity, parent, or boundary"
                roster_match = "candidate"
                candidate_names.add(match)
            elif source_name.startswith("Otok "):
                assessment = "correction-needed"
                role = "island-labeled feature has no normalized DZS 2021 town/municipality name match within the inherited parent county; legal host/identity unresolved"
                roster_match = "no"
            elif match:
                assessment = "insufficient-evidence"
                role = "DZS 2021 local-government name/type match conditional on existing Atlas parent county alias; parent relationship unverified"
                roster_match = "yes"
                matched_names.add(match)
            elif member == MURTER_KORNATI_NAME_CANDIDATE and any(
                    normalized_name(name) == normalized_name("Murter-Kornati")
                    for name in official_units):
                assessment = "insufficient-evidence"
                role = "probable Murter-Kornati name candidate conditional on existing Atlas parent county alias; source-local ID lineage and parent relationship unverified"
                roster_match = "candidate"
                candidate_names.add("Murter-Kornati")
            else:
                assessment = "insufficient-evidence"
                role = "name or identity lineage unresolved; inherited parent county relationship unverified"
                roster_match = "no"
            report_rows.append({
                "subject_id": member,
                "parent_id": parents[member][0],
                "parent_name": parent_name,
                "source_collection": "geoBoundaries HRV ADM2 (2021 represented)",
                "territorial_role_finding": role,
                "roster_comparison_basis": "conditional on the existing framework province parent alias; geoBoundaries feature has no independently inspected county-parent field",
                "inherited_parent_county_dzs_2021_roster_match": roster_match,
                "overall_assessment": assessment,
                "boundary_verification": "insufficient-evidence: official DGU geometry was not lawfully retrieved",
            })
        absent = sorted(unit for unit in official_units if unit not in matched_names)
        absent_with_candidates = sorted(unit for unit in official_units
                                        if unit not in matched_names and unit not in candidate_names)
        county_summary[parent_name] = {
            "scoped_source_features": len(children),
            "official_2021_town_municipality_roster": len(official_units),
            "exact_roster_matches": len(matched_names),
            "probable_name_candidates": len(official_units.intersection(candidate_names)),
            "unmatched_source_features": len(children) - len(matched_names) - len(candidate_names),
            "roster_units_not_exactly_matched_in_this_issue_scope": len(absent),
            "roster_units_not_represented_even_by_name_candidate_in_this_issue_scope": len(absent_with_candidates),
        }
        if absent_with_candidates:
            missing_units[parent_name] = absent_with_candidates

    city_id = "atlas:city:HRV-1589"
    report_rows.append({
        "subject_id": city_id,
        "parent_id": parents[city_id][0],
        "parent_name": parents[city_id][1],
        "source_collection": "Natural Earth 10m Admin 1; local extraction version unpinned",
        "territorial_role_finding": "Croatian law recognizes Grad Zagreb as a distinct territorial and administrative unit; the existing Atlas record names Grad Zagreb, but Natural Earth source lineage and identity remain unverified",
        "roster_comparison_basis": "not applicable: separate city/county-equivalent unit",
        "inherited_parent_county_dzs_2021_roster_match": "not applicable",
        "overall_assessment": "insufficient-evidence",
        "boundary_verification": "insufficient-evidence: source vintage/hash and official comparison unavailable",
    })
    report_rows.sort(key=lambda row: row["subject_id"])
    csv_path = HERE / "subject-review.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(report_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(report_rows)
    summary = {
        "issue": 418,
        "scope_id_count": len(ids),
        "source_feature_count": len(source_ids),
        "source_feature_joins": len(source_ids.intersection(features)),
        "roster_matches_conditional_on_inherited_parent": sum(row["inherited_parent_county_dzs_2021_roster_match"] == "yes" for row in report_rows),
        "probable_name_candidates_conditional_on_inherited_parent": sum(row["inherited_parent_county_dzs_2021_roster_match"] == "candidate" for row in report_rows),
        "island_label_name_candidates_conditional_on_inherited_parent": sum(row["inherited_parent_county_dzs_2021_roster_match"] == "candidate" and row["territorial_role_finding"].startswith("island-labeled feature") for row in report_rows),
        "island_label_correction_candidates": sum(row["territorial_role_finding"].startswith("island-labeled feature") for row in report_rows),
        "overall_status_counts": dict(Counter(row["overall_assessment"] for row in report_rows)),
        "county_summary": county_summary,
        "official_2021_units_not_matched_in_this_issue_scope": missing_units,
        "boundary_license_limits": [
            "geoBoundaries/Atlas metadata reports CC BY-SA 2.0 for an OSM-derived source, while OSM's current official notice says ODbL; no license change is proposed.",
            "DGU's official INSPIRE Administrative Units feed carries an explicit public-access restriction; its polygon archive was not downloaded.",
        ],
        "boundary_verification": "No scoped Croatia polygon is certified by this reproduction.",
        "roster_name_matches_are_not_extent_or_identity_proof": "Two island-labeled source features normalize to DZS local-government names (Krk and Cres); feature identity and geometry still require authoritative review.",
    }
    (HERE / "reproduction.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
