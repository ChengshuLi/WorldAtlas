#!/usr/bin/env python3
"""Rebuild an exact-issue-scope Zambia OSG/GRID3 source crosswalk."""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import pathlib
import subprocess
import sys
import types
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[2]
BASE = "bc0d30ce3945a7dd7158af67aad05a236bc1f51a"
OWNED = "data/regional-review/zambia-2022-feature-kind-reconciliation-20261006/"
OSG = "data/regional-review/regional-review-f4badb23f78b69b7/source/zambia-grid3-2022/zambia-administrative-boundaries-2022.geojson"
GB_INVENTORY = "data/regional-review/regional-review-f4badb23f78b69b7/phase-2/source-inventory.json"
GB_SOURCE = "data/regional-review/regional-review-f4badb23f78b69b7/source/geoboundaries/ZMB/geoBoundaries-ZMB-ADM2.geojson"
GB_META = "data/regional-review/regional-review-f4badb23f78b69b7/source/geoboundaries/ZMB/geoBoundaries-ZMB-ADM2-metaData.json"
FEATURE_CLASSES = {"District Town", "Provincial Town", "City", "District Tiwn"}


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()
    return "".join(c for c in value if c.isalnum())


def verify_source_bytes(raw: bytes, descriptor: dict) -> None:
    if len(raw) != descriptor["bytes"] or hashlib.sha256(raw).hexdigest() != descriptor["sha256"]:
        raise ValueError("source byte pin mismatch")


def crosswalk(osg_features, source_features, scope_ids):
    if len(osg_features) != 116 or len(source_features) != 116 or len(scope_ids) != 116:
        raise ValueError("expected exactly 116 OSG rows, 116 indexed subjects and 116 issue subjects")
    by_name = {}
    for feature in source_features:
        p = feature.get("properties", {})
        if p.get("metadata", {}).get("source_id") != "gb:ZMB:ADM2":
            continue
        name, original_id = p.get("name"), p.get("metadata", {}).get("original_id")
        if not name or not original_id or feature.get("id") != f"gb:ZMB:ADM2:{original_id}":
            raise ValueError("reference ID/name fields are incomplete or conflict")
        if norm(name) in by_name:
            raise ValueError("duplicate normalized name in pinned subject source")
        by_name[norm(name)] = (name, original_id, p["metadata"])
    if len(by_name) != 116:
        raise ValueError("pinned subject source does not contain 116 Zambia ADM2 identities")

    rows, seen = [], set()
    for feature in osg_features:
        p = feature.get("properties", {})
        name, value = p.get("DISTRICT"), p.get("FEATURE_TY")
        key = norm(name)
        if not name or key in seen or key not in by_name:
            raise ValueError(f"duplicate or unmatched OSG district name: {name!r}")
        seen.add(key)
        gb_name, original_id, metadata = by_name[key]
        if value not in FEATURE_CLASSES:
            raise ValueError(f"unexpected FEATURE_TY literal: {value!r}")
        subject_id = f"gb:ZMB:ADM2:{original_id}"
        source_url = metadata.get("source_url", "")
        if subject_id not in scope_ids or metadata.get("reference_year") != "2020" or "ZMB/ADM2/geoBoundaries-ZMB-ADM2.geojson" not in source_url:
            raise ValueError(f"source identity is outside pinned issue scope or source lineage: {subject_id}")
        note = {
            "District Town": "literal retained; the data do not establish whether this means unit type, settlement/seat role, cartographic label, or other",
            "Provincial Town": "literal retained; the data do not establish whether this means unit type, settlement/seat role, cartographic label, or other",
            "City": "literal retained; the data do not establish whether this means unit type, settlement/seat role, cartographic label, or other",
            "District Tiwn": "singleton spelling variant on Shiwang'Andu; likely typo for District Town, but intended correction and semantics are unverified",
        }[value]
        rows.append({
            "subject_id": subject_id,
            "osg_district": name,
            "osg_province": p.get("PROVINCE", ""),
            "feature_ty_literal": value,
            "feature_ty_assessment": note,
            "osg_district_code": p.get("DIST_CODE", ""),
            "reference_name": gb_name,
            "reference_year": metadata["reference_year"],
            "reference_adm_level": metadata.get("administrative_level", ""),
            "reference_role": metadata.get("source_role", ""),
            "name_join": "unique normalized-name match; identity only",
            "area_km_source_value": p.get("Area_km", ""),
            "area_km_assessment": "unvalidated; no source method, units, precision, projection, or geometry relationship documented",
            "administrative_role": "OSG item says district boundaries; FEATURE_TY category meaning unresolved",
            "boundary_accuracy": "not assessed",
        })
    if seen != set(by_name) or {r["subject_id"] for r in rows} != set(scope_ids):
        raise ValueError("source names/IDs do not form the exact issue-declared 116-row bijection")
    return sorted(rows, key=lambda row: row["subject_id"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", choices=("run-one", "run-two"), required=True)
    args = parser.parse_args()

    manifest_path = ROOT / "evidence-quality.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    helper_path = "scripts/evidence/immutable.py"
    helper_entry = next(row for row in manifest["baseline"]["files"] if row["path"] == helper_path)
    helper_raw = subprocess.check_output(["git", "-C", str(REPO), "show", f"{BASE}:{helper_path}"])
    if len(helper_raw) != helper_entry["bytes"] or hashlib.sha256(helper_raw).hexdigest() != helper_entry["sha256"]:
        raise ValueError("pinned immutable helper mismatch")
    helper = types.ModuleType("worldatlas_pinned_immutable")
    exec(compile(helper_raw, helper_path, "exec"), helper.__dict__)

    baseline = helper.Baseline(REPO, BASE, manifest["baseline"]["files"])
    scope_ids = manifest["subject_ids"]
    expected = manifest["baseline"]["subject_files"]
    if set(expected) != set(scope_ids):
        raise ValueError("manifest subject-file inventory disagrees with issue subject IDs")
    # The shared helper reads the complete pinned world index and proves each
    # ID occurs exactly once in its actual containing part.
    subjects, containing = baseline.subjects(scope_ids)
    if set(subjects) != set(scope_ids) or any(expected[i] != containing[i]["path"] for i in scope_ids):
        raise ValueError("actual containing files do not match the manifest subject inventory")
    osg_raw = baseline.pinned_bytes(OSG)
    osg_pin = next(row for row in manifest["baseline"]["files"] if row["path"] == OSG)
    damaged = bytearray(osg_raw)
    damaged[len(damaged) // 2] ^= 1
    try:
        verify_source_bytes(bytes(damaged), osg_pin)
    except ValueError:
        pass
    else:
        raise AssertionError("modified source bytes passed the actual source-byte guard")
    osg_data = json.loads(osg_raw)
    subject_features = [subjects[i] for i in scope_ids]
    rows = crosswalk(osg_data["features"], subject_features, set(scope_ids))

    # Exercise adverse inputs against real records: a modified byte buffer,
    # one changed district name, one duplicate actual name, and one unknown type.
    def must_fail(osg_rows, source_rows):
        try:
            crosswalk(osg_rows, source_rows, set(scope_ids))
        except (ValueError, KeyError):
            return
        raise AssertionError("adverse source fixture was accepted")
    mutated = json.loads(osg_raw)["features"]
    mutated[0]["properties"]["DISTRICT"] = "Definitely not the source name"
    must_fail(mutated, subject_features)
    duplicate = json.loads(osg_raw)["features"]
    duplicate[1]["properties"]["DISTRICT"] = duplicate[0]["properties"]["DISTRICT"]
    must_fail(duplicate, subject_features)
    unknown = json.loads(osg_raw)["features"]
    unknown[0]["properties"]["FEATURE_TY"] = "Unrecorded category"
    must_fail(unknown, subject_features)
    # Controls use the actual computed rows and their observed values.
    counts = dict(sorted(collections.Counter(row["feature_ty_literal"] for row in rows).items()))
    if counts != {"City": 4, "District Tiwn": 1, "District Town": 100, "Provincial Town": 11}:
        raise ValueError(f"unexpected source category inventory: {counts}")
    fields = list(rows[0])
    def encode_csv():
        from io import StringIO
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return stream.getvalue().encode("utf-8")
    summary = {
        "metrics": {
            "district_features": {"value": len(rows), "unit": "source records"},
            "district_town_literal": {"value": counts["District Town"], "unit": "source records"},
            "provincial_town_literal": {"value": counts["Provincial Town"], "unit": "source records"},
            "city_literal": {"value": counts["City"], "unit": "source records"},
            "district_tiwn_literal": {"value": counts["District Tiwn"], "unit": "source records"},
            "matched_reference_ids": {"value": len({r["subject_id"] for r in rows}), "unit": "native IDs"},
        },
        "source_categories": counts,
        "area_km": "source values preserved; method and units not validated",
    }
    positive = {
        "method_id": "zambia-116-name-crosswalk",
        "kind": "positive-control",
        "outcome": "passed",
        "osg_records": len(osg_data["features"]),
        "issue_subjects": len(scope_ids),
        "crosswalk_rows": len(rows),
        "unique_subject_ids": len({r["subject_id"] for r in rows}),
        "categories": counts,
        "subject_file": next(iter(containing.values())),
    }
    negative = {
        "method_id": "zambia-116-name-crosswalk",
        "kind": "negative-control",
        "outcome": "passed",
        "cases": [
            {"case": "altered OSG district name", "tested_value": "Definitely not the source name", "result": "rejected unmatched identity"},
            {"case": "duplicate OSG name", "tested_records": 2, "result": "rejected duplicate identity"},
            {"case": "unknown FEATURE_TY", "tested_value": "Unrecorded category", "result": "rejected undocumented literal"},
            {"case": "altered source bytes", "tested_source": OSG, "result": "SHA-256 differed from pinned original"},
        ],
    }
    out_files = ["feature-type-crosswalk.csv", "summary.json", "positive-control.json", "negative-control.json"]
    if args.run_id == "run-two":
        first = ROOT / "vintages" / "run-one"
        first_publication = json.loads((first / "publication.json").read_text(encoding="utf-8"))
        first_hashes = {row["path"].rsplit("/", 1)[-1]: row["sha256"] for row in first_publication["outputs"]}
        if set(first_hashes) != set(out_files) or any(
            hashlib.sha256((first / name).read_bytes()).hexdigest() != first_hashes[name] for name in out_files
        ):
            raise ValueError("run-one outputs do not match their complete publication receipt")
        now_values = {
            "feature-type-crosswalk.csv": encode_csv(),
            "summary.json": (json.dumps(summary, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode(),
            "positive-control.json": (json.dumps(positive, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode(),
            "negative-control.json": (json.dumps(negative, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode(),
        }
        first_digest = hashlib.sha256(json.dumps(first_hashes, sort_keys=True).encode()).hexdigest()
        second_digest = hashlib.sha256(json.dumps({name: hashlib.sha256(raw).hexdigest() for name, raw in now_values.items()}, sort_keys=True).encode()).hexdigest()
        reproducibility = {"method_id": "zambia-116-name-crosswalk", "kind": "reproducibility", "outcome": "passed", "run_one_sha256": first_digest, "run_two_sha256": second_digest, "compared_outputs": sorted(out_files)}
        if first_digest != second_digest:
            raise ValueError("fresh run outputs differ")
        out_files.append("reproducibility.json")
    run = helper.NewVintage(baseline, OWNED, args.run_id, out_files)
    products = {
        "feature-type-crosswalk.csv": encode_csv(),
        "summary.json": (json.dumps(summary, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        "positive-control.json": (json.dumps(positive, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        "negative-control.json": (json.dumps(negative, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    }
    if args.run_id == "run-two":
        products["reproducibility.json"] = (json.dumps(reproducibility, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    records = run.publish_bytes(products)
    print(f"PASS: {len(rows)} source features map bijectively to the exact 116 issue subjects by normalized district name")
    print(f"PASS: literal FEATURE_TY counts are {counts}; no category recoded")
    print("PASS: source Area_km retained unvalidated")
    print(f"PASS: {len(baseline.consumed)} complete baseline files authenticated; {sum(baseline.consumed.values())} bytes admitted")
    print("PASS: altered-name, duplicate-name, unknown-category and modified-byte adverse controls rejected")
    print("OUTPUTS:", json.dumps(records, sort_keys=True))


if __name__ == "__main__":
    main()
