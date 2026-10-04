#!/usr/bin/env python3
"""Validate inherited BC–Washington sample ledger and derive corrected counts.

This deliberately does not recreate IBC sample coordinates: the archive is
mapping-only, not retained, and its canonical download page returned 404 on
2026-10-04. The inherited projected coordinate/distance ledger is the input.
"""
import gzip
import hashlib
import argparse
import json
import subprocess
from pathlib import Path

BASE = "a1fd3383e89dea4c4497bf3a6f469494871ad758"
PREFIX = "data/regional-review/regional-review-4254da254d94f450/"
OUT = Path(__file__).resolve().parent / "assessment.json"
PINNED = {
    "data/world-index.json": (944, "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03"),
    "data/hierarchy.json": (10165703, "03d23534f87cdd0582bcb228780f00f65090bec2e8a760acbab528383f28549d"),
    "data/geography/part-27.json": (4863162, "e8df7555853e9262162c5e5d5c85e5c30be3fa8f0e6339bafec0e08323054758"),
    "data/geography/part-29.json": (12932167, "077e3bdfb18a42318e27bad840bba823a5049ced449407584fb4b9be2ef67c7a"),
    PREFIX + "scope.json": (19009, "eeeba48c2ac959c2304b31f2008251b2dd8b34751d9aab1b9735d825532bf055"),
    PREFIX + "sources/current-parent-chains.json.gz": (106481, "aa0c1643d376baa9b7478d26886510718d3c0e242782df004e2defd028938290"),
    PREFIX + "sources/current-scope-and-parents.geojson.gz": (280642, "7ac3154985ef3bf5aae5b978481233e3a73c0ef6b2a753e1c7a15cef4c9302bb"),
    PREFIX + "sources/statistics-canada-bc-census-divisions-2021.geojson.gz": (38880150, "8a31cf19ad0694638c88275fec9ff1005970cd8600ca6baed245b8826756e9bf"),
    PREFIX + "sources/tigerline-2024-washington-counties.geojson.gz": (859249, "74c2822d327082e2738a8d93d59bc5eadf42590f7fef0941221e61deb36a4034"),
    "data/regional-review/bc-washington-coastal-edge-followup-2026/sample-assessment.json": (14978, "0f5f8d1a742032c149ce47a8aae01442cc1a5c5dc2e9b6719e11ae2f7080df13"),
}
SUBJECTS = [
    "atlas:district:CAN-5915:BRC",
    "gb:USA:ADM2:52423323B9068998137459",
    "gb:USA:ADM2:52423323B32782252789959",
]

def blob(path):
    return subprocess.run(["git", "show", f"{BASE}:{path}"], check=True, stdout=subprocess.PIPE).stdout

def read_json(raw):
    return json.loads(raw)

def read_gzip_json(path):
    return read_json(gzip.decompress(blob(path)))

def verify_pins():
    for path, (size, digest) in PINNED.items():
        raw = blob(path)
        if (len(raw), hashlib.sha256(raw).hexdigest()) != (size, digest):
            raise ValueError(f"baseline pin mismatch: {path}")

def verify_scope_and_subjects():
    scope = read_json(blob(PREFIX + "scope.json"))
    members = scope.get("member_location_ids", [])
    if len(members) != len(set(members)) or len(members) != 222:
        raise ValueError("pinned scope member roster is not unique and complete")
    chains = read_gzip_json(PREFIX + "sources/current-parent-chains.json.gz")
    chain_by_id = {row.get("id"): row.get("parent_chain") for row in chains}
    if len(chain_by_id) != 222 or set(chain_by_id) != set(members):
        raise ValueError("pinned parent-chain roster differs from complete scope")
    hierarchy = read_json(blob("data/hierarchy.json"))
    hierarchy_ids = {row.get("id") for row in hierarchy if isinstance(row, dict)}
    expected_provinces = {
        SUBJECTS[0]: "framework:province:british-columbia:83abeaaac0ca",
        SUBJECTS[1]: "framework:province:washington:b01ae89096c9",
        SUBJECTS[2]: "framework:province:washington:b01ae89096c9",
    }
    features = read_gzip_json(PREFIX + "sources/current-scope-and-parents.geojson.gz").get("features", [])
    feature_by_id = {feature.get("properties", {}).get("id"): feature for feature in features}
    if len(feature_by_id) != 222 or set(feature_by_id) != set(members):
        raise ValueError("pinned scope geometry roster differs from complete scope")
    parts = {"data/geography/part-27.json": {SUBJECTS[1], SUBJECTS[2]},
             "data/geography/part-29.json": {SUBJECTS[0]}}
    subject_features = {}
    for path, expected_ids in parts.items():
        data = read_json(blob(path))
        found = {f.get("id") or f.get("properties", {}).get("id"): f for f in data.get("features", [])}
        if not expected_ids <= set(found):
            raise ValueError(f"subject missing from pinned containing part {path}")
        subject_features.update({key: found[key] for key in expected_ids})
    hierarchy_by_id = {row["id"]: row for row in hierarchy if isinstance(row, dict) and row.get("id")}
    chains = {}
    for subject, expected_province in expected_provinces.items():
        feature = subject_features[subject]
        props = feature.get("properties", {})
        parent = props.get("parent_id") or feature.get("parent_id")
        chain_ids = [subject]
        while parent:
            if parent in chain_ids or parent not in hierarchy_by_id:
                raise ValueError(f"broken or cyclic parent chain for {subject}: {parent}")
            chain_ids.append(parent)
            parent = hierarchy_by_id[parent].get("parent_id")
        if len(chain_ids) != 6 or chain_ids[1] != expected_province:
            raise ValueError(f"unexpected complete five-tier parent chain for {subject}: {chain_ids}")
        chains[subject] = chain_ids
    return subject_features, chains

def verify_reference_rosters():
    cd = read_gzip_json(PREFIX + "sources/statistics-canada-bc-census-divisions-2021.geojson.gz").get("features", [])
    wa = read_gzip_json(PREFIX + "sources/tigerline-2024-washington-counties.geojson.gz").get("features", [])
    cd_ids = [f.get("properties", {}).get("CDUID") for f in cd]
    wa_ids = [f.get("properties", {}).get("GEOID") for f in wa]
    if len(cd_ids) != 29 or len(set(cd_ids)) != 29 or "5915" not in cd_ids:
        raise ValueError("Statistics Canada BC Census Division roster is incomplete/duplicated")
    if len(wa_ids) != 39 or len(set(wa_ids)) != 39 or not {"53073", "53055"} <= set(wa_ids):
        raise ValueError("TIGER Washington county roster is incomplete/duplicated")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--new-vintage", action="store_true", help="create assessment.json exclusively after every input check")
    args = parser.parse_args()
    if args.new_vintage and OUT.exists():
        raise SystemExit(f"refusing existing output before reading project inputs: {OUT}")
    verify_pins()
    subject_features, subject_chains = verify_scope_and_subjects()
    verify_reference_rosters()
    original = read_json(blob("data/regional-review/bc-washington-coastal-edge-followup-2026/sample-assessment.json"))
    rows = original["samples"]
    ids = [r.get("sample") for r in rows]
    if ids != list(range(50, 68)) or len(set(ids)) != 18:
        raise ValueError("sample roster is not exactly 50–67")
    if any(not isinstance(r.get("epsg3347_m"), list) or len(r["epsg3347_m"]) != 2 for r in rows):
        raise ValueError("sample coordinate pair missing")
    if any(not all(isinstance(v, (int, float)) for v in r["epsg3347_m"]) for r in rows):
        raise ValueError("non-numeric sample coordinate")
    if any(r.get("nearest_current_bc_location_id") != SUBJECTS[0] for r in rows):
        raise ValueError("unexpected nearest BC subject")
    if any(r.get("nearest_2024_tiger_wa_county_geoid") != "53073" for r in rows):
        raise ValueError("unexpected nearest Washington county")
    no_containment = [r["sample"] for r in rows if not r.get("tiger_wa_county_polygons_containing_point")]
    distances = [r["nearest_current_bc_location_boundary_m"] for r in rows]
    if len(no_containment) != 5 or min(distances) != 1011.9:
        raise ValueError("inherited ledger does not support corrected count/range")
    result = {
        "version": 1,
        "baseline_commit": BASE,
        "input": "inherited #657 sample-assessment.json; source-line coordinates not regenerated",
        "sample_ids": ids,
        "subjects": [
            {"id": SUBJECTS[0], "source_name": subject_features[SUBJECTS[0]]["properties"].get("name"), "parent_chain": subject_chains[SUBJECTS[0]], "assessment": "Current BC assigned comparison feature; its 18 ledger distances are 1,011.90–5,888.53 m. Source grouping is Statistics Canada CD 5915-derived; not a legal line."},
            {"id": SUBJECTS[1], "source_name": subject_features[SUBJECTS[1]]["properties"].get("name"), "parent_chain": subject_chains[SUBJECTS[1]], "assessment": "Current Washington member corresponding to 2024 TIGER Whatcom county GEOID 53073, nearest county in all 18 inherited rows."},
            {"id": SUBJECTS[2], "source_name": subject_features[SUBJECTS[2]]["properties"].get("name"), "parent_chain": subject_chains[SUBJECTS[2]], "assessment": "Current Washington member corresponding to 2024 TIGER San Juan county GEOID 53055; included as assigned neighbor, not nearest in any inherited sample row."}
        ],
        "sample_count": len(rows),
        "nearest_bc_location_id_all_samples": SUBJECTS[0],
        "nearest_wa_geoid_all_samples": "53073",
        "nearest_bc_distance_m": {"minimum": min(distances), "maximum": max(distances)},
        "strict_tiger_polygon_noncontainment_sample_ids": no_containment,
        "strict_tiger_polygon_noncontainment_count": len(no_containment),
        "legacy_narrative_errors": [
            {"field": "noncontainment count", "legacy": 4, "ledger": 5},
            {"field": "minimum BC distance meters", "legacy": 1011.91, "ledger": 1011.9, "display": "1,011.90"},
        ],
        "interpretation": "The retained row ledger establishes these arithmetic corrections only. It does not establish why the source line is offset, legal boundary, ownership, or a geometry correction.",
        "unresolved": "IBC v1.3 line archive was not restored because current canonical page returned HTTP 404 and retained terms permit mapping-only use. Inherited sample coordinates and source-line generation remain unverified.",
    }
    encoded = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.new_vintage:
        with OUT.open("xb") as stream:
            stream.write(encoded)
    else:
        if not OUT.is_file() or OUT.read_bytes() != encoded:
            raise ValueError("read-only check failed: stored assessment differs; use an unused fresh output path to create a new vintage")
    print(json.dumps({"output": str(OUT), "sha256": hashlib.sha256(encoded).hexdigest(), "samples": len(rows), "uncontained": len(no_containment), "mode": "created" if args.new_vintage else "read-only-verified"}))

if __name__ == "__main__":
    main()
