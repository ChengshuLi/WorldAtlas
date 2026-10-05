#!/usr/bin/env python3
"""Reproduce the bounded Serbia name/code crosswalk from retained SORS rosters.

This compares names, register codes and SORS district relationships. It does not
compare polygons or establish legal boundary identity.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "sources"
OUT = SOURCE / "derived"
BASELINE = ROOT.parents[0] / "regional-review-3c4fe25a21fa428d" / "source" / "subject-assessments.json"
ISSUE = ROOT / "source-issue-998.json"
OLD_FILE = SOURCE / "sors-cities-municipalities-2017.xls"
CUR_FILE = SOURCE / "sors-cities-municipalities-current-2026-10-05.xlsx"
GB_FILE = SOURCE / "geoBoundaries-SRB-ADM2-2017.geojson"
GB_METADATA = ROOT.parents[0] / "regional-review-3c4fe25a21fa428d" / "source" / "gb" / "SRB-ADM2-geoBoundaries-SRB-ADM2-metaData.json"
LATIN_TO_CYR = str.maketrans({
    "a":"а", "b":"б", "v":"в", "g":"г", "d":"д", "đ":"ђ", "e":"е", "ž":"ж", "z":"з", "i":"и", "j":"ј", "k":"к", "l":"л", "m":"м", "n":"н", "o":"о", "p":"п", "r":"р", "s":"с", "t":"т", "ć":"ћ", "u":"у", "f":"ф", "h":"х", "c":"ц", "č":"ч", "š":"ш",
})
CYR_TO_LAT = str.maketrans({v:k for k,v in LATIN_TO_CYR.items()})
PARENT_SORS_NAMES = {
    "West Backa District": {"zapadnobacki"}, "North Backa District": {"severnobacki"},
    "South Backa District": {"juznobacki"}, "North Banat District": {"severnobanatski"},
    "Central Banat District": {"srednjobanatski"}, "Syrmia District": {"sremski"},
    "Macva District": {"macvanski"}, "Kolubara District": {"kolubarski"},
    "Zlatibor District": {"zlatiborski"}, "Moravica District": {"moravicki"},
    "Raska District": {"raski"}, "Sumadija District": {"sumadijski"},
}


def norm(value: object) -> str:
    s = unicodedata.normalize("NFKD", str(value or "")).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("њ", "nj").replace("љ", "lj").replace("џ", "dž")
    s = s.translate(CYR_TO_LAT)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("đ", "dj")
    return re.sub(r"[^a-z0-9]+", "", s)


def code(value: object) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    try:
        n = float(s)
        return str(int(n)) if n.is_integer() else s
    except (ValueError, OverflowError):
        return s


def as_records(frame: pd.DataFrame, old: bool) -> list[dict]:
    records = []
    for _, row in frame.iterrows():
        vals = [None if pd.isna(x) else str(x).strip() for x in row.tolist()]
        if old:
            dc, dn, cc, cn, uc, un = vals
            records.append({"district_code": dc, "district_name": dn, "city_code": cc,
                            "city_name": cn, "unit_code": uc, "unit_name": un,
                            "unit_column_categories": "municipality/city municipality/city (combined in workbook header)",
                            "urban_municipality_code": None, "urban_municipality_name": None})
        else:
            dc, dn, uc, un, typ, mc, mn = vals
            records.append({"district_code": dc, "district_name": dn, "city_code": None,
                            "city_name": None, "unit_code": uc, "unit_name": un,
                            "unit_type_in_source": typ,
                            "urban_municipality_code": mc, "urban_municipality_name": mn})
    return records


def main() -> None:
    OUT.mkdir(exist_ok=True, parents=True)
    old = as_records(pd.read_excel(OLD_FILE, sheet_name=0, header=2), True)
    current = as_records(pd.read_excel(CUR_FILE, sheet_name=0, header=2), False)
    gb = json.loads(GB_FILE.read_text(encoding="utf-8"))
    gb_meta = json.loads(GB_METADATA.read_text(encoding="utf-8"))
    gb_features = {f["properties"]["shapeID"]: f for f in gb["features"]}
    if len(gb["features"]) != 145 or len(gb_features) != 145 or gb_meta.get("admUnitCount") != "145":
        raise AssertionError("Pinned SRB ADM2 source must contain 145 unique shape IDs")
    upstream = json.loads(BASELINE.read_text())
    all_subj = {x["location_id"]: x for x in upstream["subjects"]}
    issue = json.loads(ISSUE.read_text())
    body = issue["body"]
    scope_match = re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", body, re.S)
    if not scope_match:
        raise SystemExit("Could not extract declared work scope")
    scope = json.loads(scope_match.group(1))
    ids = scope["evidence_quality"]["subject_ids"]
    parents = {p["province_id"]: p for p in upstream["provinces"]}
    output = []
    for sid in ids:
        s = all_subj[sid]
        name = s["name"]
        original_feature = gb_features.get(s["original_id"])
        if not original_feature or original_feature["properties"].get("shapeName") != s["source_feature_name"]:
            raise AssertionError("Pinned original source ID/name does not match #422 evidence: " + sid)
        label = re.sub(r"\s+(Municipality|City)$", "", name, flags=re.I)
        parent = parents[s["parent_id"]]
        parent_label = parent["name"]
        name_key = norm(label)
        # City names/codes are separate from constituent urban municipalities.
        is_city = name.lower().endswith(" city") or name == "Belgrade"
        if is_city:
            expected = "Beograd" if name == "Belgrade" else label
            key = norm(expected)
            old_hits = [x for x in old if (norm(x["city_name"])[4:] if norm(x["city_name"]).startswith("grad") else norm(x["city_name"])) == key]
            cur_hits = [x for x in current if norm(x["unit_name"]) == key and x.get("unit_type_in_source") == "град"]
            old_hits = list({(x["city_code"], x["city_name"], x["district_code"]): x for x in old_hits}.values())
            cur_hits = list({(x["unit_code"], x["unit_name"], x["district_code"]): x for x in cur_hits}.values())
        else:
            old_hits = [x for x in old if norm(x["unit_name"]) == name_key]
            cur_hits = [x for x in current if norm(x["unit_name"]) == name_key]
        old_hit = old_hits[0] if len(old_hits) == 1 else {}
        cur_hit = cur_hits[0] if len(cur_hits) == 1 else {}
        old_code = old_hit.get("city_code") if is_city else old_hit.get("unit_code")
        old_name = old_hit.get("city_name") if is_city else old_hit.get("unit_name")
        old_district_key = norm(old_hit.get("district_name", ""))
        cur_district_key = norm(cur_hit.get("district_name", ""))
        expected_district_keys = {norm(x) for x in PARENT_SORS_NAMES.get(parent_label, set())}
        # Be explicit about a parent tier that is a repeated singleton city.
        parent_match = (any(old_district_key.startswith(key) for key in expected_district_keys) if expected_district_keys else
                        norm(old_hit.get("city_name", "")) == norm("Grad Beograd"))
        current_parent_match = (code(old_hit.get("district_code")) == code(cur_hit.get("district_code"))) if old_hit and cur_hit else False
        expected_type = "град" if is_city else "општина"
        type_match = cur_hit.get("unit_type_in_source") == expected_type if cur_hit else False
        current_status = "no-unique-name-hit"
        if len(old_hits) == 1 and len(cur_hits) == 1:
            same_code = code(old_code) == code(cur_hit["unit_code"])
            current_status = "same-code-name-type-and-parent" if same_code and type_match and current_parent_match else "code-type-or-parent-changed"
        output.append({
            "location_id": sid, "atlas_name": name, "source_feature_name": s["source_feature_name"],
            "source_original_id": s["original_id"], "source_collection_sha256": s["source_sha256"],
            "source_feature_name_exact_bytes_match": True, "source_geometry_type": original_feature["geometry"]["type"],
            "source_metadata_boundary_year": gb_meta["boundaryYear"],
            "source_metadata_update_date": gb_meta["sourceDataUpdateDate"], "source_metadata_build_date": gb_meta["buildDate"],
            "atlas_parent_id": s["parent_id"], "atlas_parent_name": parent_label,
            "register_tier_matched": "city" if is_city else "municipality",
            "2017_name_match_count": len(old_hits), "sors_2017_unit_code": old_code,
            "sors_2017_unit_name": old_name, "sors_2017_unit_column_categories": "city" if is_city else old_hit.get("unit_column_categories"),
            "sors_2017_district_code": old_hit.get("district_code"), "sors_2017_district_name": old_hit.get("district_name"),
            "sors_2017_city_code": old_hit.get("city_code"), "sors_2017_city_name": old_hit.get("city_name"),
            "current_name_match_count": len(cur_hits), "sors_current_unit_code": cur_hit.get("unit_code"),
            "sors_current_unit_name": cur_hit.get("unit_name"), "sors_current_type": cur_hit.get("unit_type_in_source"),
            "sors_current_district_code": cur_hit.get("district_code"), "sors_current_district_name": cur_hit.get("district_name"),
            "current_type_matches_expected": type_match, "current_parent_code_agrees_with_2017": current_parent_match,
            "current_status": current_status, "district_parent_name_agrees_after_transliteration": parent_match,
            "geometry_identity": "not-established; name/code roster crosswalk only",
            "finding": "unique transliterated name and listed parent relationship; boundary and source-geometry identity remain unverified" if len(old_hits)==len(cur_hits)==1 and parent_match else "insufficient-evidence: ambiguity, unmatched parent, or current roster discrepancy requires official register feature-level reconciliation",
        })
    with (OUT / "subject-crosswalk.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(output[0]), lineterminator="\n")
        w.writeheader(); w.writerows(output)
    with (OUT / "sors-2017-roster-normalized.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(old[0]), lineterminator="\n"); w.writeheader(); w.writerows(old)
    with (OUT / "sors-current-roster-normalized.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(current[0]), lineterminator="\n"); w.writeheader(); w.writerows(current)
    counts = {}
    for row in output:
        k = row["atlas_parent_id"]
        counts.setdefault(k, {"parent_id": k, "parent_name": row["atlas_parent_name"], "scoped_subjects": 0,
                              "distinct_2017_unit_codes": set(), "distinct_2017_district_codes": set(), "unmatched_or_ambiguous": 0})
        c = counts[k]; c["scoped_subjects"] += 1
        if row["sors_2017_unit_code"]: c["distinct_2017_unit_codes"].add(str(row["sors_2017_unit_code"]))
        if row["sors_2017_district_code"]: c["distinct_2017_district_codes"].add(row["sors_2017_district_code"])
        if row["2017_name_match_count"] != 1 or not row["district_parent_name_agrees_after_transliteration"]: c["unmatched_or_ambiguous"] += 1
    parent_rows = []
    for c in counts.values():
        c["distinct_2017_unit_codes"] = len(c["distinct_2017_unit_codes"])
        c["distinct_2017_district_codes"] = sorted(c["distinct_2017_district_codes"])
        c["parent_tier_finding"] = "Belgrade is represented as a one-child Atlas province parent repeating the city entity; the SORS register lists it as a city, so parent role needs hierarchy review." if c["parent_name"] == "Belgrade" else "Name/grouping is roster-consistent; 2017/current polygons and full-parent completeness are not established by this table."
        parent_rows.append(c)
    with (OUT / "parent-summary.json").open("w", encoding="utf-8") as f:
        json.dump(parent_rows, f, ensure_ascii=False, indent=2); f.write("\n")
    report = {"subjects": len(output), "unique_2017_name_matches": sum(x["2017_name_match_count"]==1 for x in output),
              "unique_current_name_matches": sum(x["current_name_match_count"]==1 for x in output),
              "same_code_name_type_and_parent": sum(x["current_status"]=="same-code-name-type-and-parent" for x in output),
              "code_type_or_parent_discrepancies": sum(x["current_status"]=="code-type-or-parent-changed" for x in output),
              "parent_name_agreements": sum(bool(x["district_parent_name_agrees_after_transliteration"]) for x in output),
              "python": sys.version.split()[0], "pandas": pd.__version__}
    if len(output) != 78 or len({x["location_id"] for x in output}) != 78:
        raise AssertionError("Issue scope must contain exactly 78 unique subjects")
    if any(x["current_status"] != "same-code-name-type-and-parent" for x in output):
        raise AssertionError("A subject does not have a unique, type/parent-consistent current roster match")
    # Test completeness only for the 13 exact parent divisions in this issue.
    roster_by_district = {}
    for row in current:
        roster_by_district.setdefault(code(row["district_code"]), {})[code(row["unit_code"])] = row
    parent_inventory = []
    for parent_id, group in counts.items():
        parent_name = group["parent_name"]
        first = next(x for x in output if x["atlas_parent_id"] == parent_id)
        district_code = code(first["sors_current_district_code"])
        official_units = roster_by_district.get(district_code, {})
        atlas_codes = {code(x["sors_current_unit_code"]) for x in output if x["atlas_parent_id"] == parent_id}
        official_codes = set(official_units)
        parent_inventory.append({
            "atlas_parent_id": parent_id, "atlas_parent_name": parent_name,
            "sors_current_parent_code": district_code,
            "sors_current_parent_name": first["sors_current_district_name"],
            "parent_entity_role": "city" if parent_name == "Belgrade" else "administrative district",
            "scoped_children": len(atlas_codes), "official_current_primary_city_or_municipality_count": len(official_codes),
            "scoped_codes_equal_all_primary_roster_codes": atlas_codes == official_codes,
            "missing_current_primary_codes": sorted(official_codes - atlas_codes),
            "extra_atlas_codes": sorted(atlas_codes - official_codes),
            "scoped_location_ids": sorted(x["location_id"] for x in output if x["atlas_parent_id"] == parent_id),
        })
    if len(parent_inventory) != 13 or not all(x["scoped_codes_equal_all_primary_roster_codes"] for x in parent_inventory):
        raise AssertionError("Scoped members do not equal all current primary roster codes in each of 13 parents")
    with (OUT / "parent-completeness.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["atlas_parent_id", "atlas_parent_name", "sors_current_parent_code", "sors_current_parent_name", "parent_entity_role", "scoped_children", "official_current_primary_city_or_municipality_count", "scoped_codes_equal_all_primary_roster_codes", "missing_current_primary_codes", "extra_atlas_codes"]
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n"); w.writeheader()
        for x in parent_inventory:
            y = {k:x[k] for k in fields}; y["missing_current_primary_codes"] = ";".join(y["missing_current_primary_codes"]); y["extra_atlas_codes"] = ";".join(y["extra_atlas_codes"]); w.writerow(y)
    (OUT / "parent-completeness.json").write_text(json.dumps(parent_inventory, ensure_ascii=False, indent=2)+"\n")
    # Current SORS explicitly distinguishes cities and their city municipalities.
    # Retain every scoped city municipality link for the city subjects in scope.
    citycodes = {code(x["sors_current_unit_code"]): x for x in output if x["register_tier_matched"] == "city"}
    city_subunits = []
    for row in current:
        parent_code = code(row["unit_code"])
        child_code = code(row.get("urban_municipality_code"))
        if parent_code in citycodes and child_code:
            city = citycodes[parent_code]
            city_subunits.append({"city_subject_id": city["location_id"], "atlas_city_label": city["atlas_name"],
                                  "sors_city_code": parent_code, "sors_city_name": row["unit_name"],
                                  "urban_municipality_code": child_code, "urban_municipality_name": row["urban_municipality_name"],
                                  "sors_current_district_code": row["district_code"], "sors_current_district_name": row["district_name"],
                                  "separate_issue_subject": False,
                                  "finding": "official urban-municipality child of the scoped city; not a separate issue subject and not individually crosswalked to an Atlas feature"})
    with (OUT / "scoped-city-urban-municipalities.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(city_subunits[0]), lineterminator="\n"); w.writeheader(); w.writerows(city_subunits)
    report["parents"] = len(parent_inventory)
    report["parent_rosters_exactly_covered"] = sum(x["scoped_codes_equal_all_primary_roster_codes"] for x in parent_inventory)
    report["scoped_urban_municipality_rows"] = len(city_subunits)
    (OUT / "reproduction-summary.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
