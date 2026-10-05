#!/usr/bin/env python3
"""Rebuild the Bulgaria ADM2/EKATTE crosswalk from retained original inputs.

Run from the repository root with Python 3 and no third-party packages:
  python3 data/regional-review/regional-review-aa0be1f8b58caec6/reproduce.py

The output is a name/code/parent crosswalk, not a geometry validation.
"""
import csv
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "data/regional-review/regional-review-aa0be1f8b58caec6"
SCOPE = PACKET / "source/issue-scope.json"
GEOB = PACKET / "source/geoBoundaries-BGR-ADM2-2019.geojson"
EKATTE_ZIP = PACKET / "source/NSI-EKATTE-export-20261005.zip"
OUT = PACKET / "validation/bulgaria-municipality-crosswalk.csv"
FULL_OUT = PACKET / "validation/bulgaria-full-source-roster.csv"
SUMMARY_OUT = PACKET / "validation/bulgaria-audit-summary.json"
EXPECTED_HASHES = {
    "source/geoBoundaries-BGR-ADM2-2019.geojson": "9283bb685efb08fa983934f4b986467c5495244cbd554dd9458b51e2857e9335",
    "source/geoBoundaries-BGR-ADM2-metaData-2019.json": "0d5e4e89424d470ff5f17e61606494f13a66842ad9b6ccebffd11f8aecea060b",
    "source/NSI-EKATTE-export-20261005.zip": "6d848e467493f4d6ec6c1c9081bf51266ad888dc8f232c3d1fd2b0a265ace77d",
}
BASELINE_PATH = PACKET / "source/baseline-inputs.json"

# geoBoundaries' 2019 Latin spellings differ from NSI's official English
# transliteration in these cases. Each is matched only with its municipality
# code and district parent, never by name alone.
ALIASES = {
    "dolna mitropoliya": "dolna mitropolia",
    "dobrichka": "dobrich selska",
    "provadiya": "provadia",
    "miziya": "mizia",
    "ruzhinsi": "ruzhintsi",
    "georgi bamyanovo": "georgi damyanovo",
    "strumyarni": "strumyani",
}


def norm(value):
    value = value.lower().replace("ё", "е")
    return re.sub(r"[^a-z0-9]+", "", value)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_registers():
    with zipfile.ZipFile(EKATTE_ZIP) as archive:
        municipality = json.loads(archive.read("ek_obst.json"))
        districts = json.loads(archive.read("ek_obl.json"))
    municipality = [row for row in municipality if row.get("obshtina")]
    districts = [row for row in districts if row.get("oblast")]
    return municipality, districts


def load_atlas():
    features = {}
    for part in (1, 2):
        path = ROOT / ("data/geography/part-%d.json" % part)
        for feature in json.loads(path.read_text(encoding="utf-8"))["features"]:
            props = feature["properties"]
            if props.get("id", "").startswith("gb:BGR:ADM2:"):
                features[props["id"]] = props
    return features


def write_full_source_roster(source, atlas, municipalities, districts):
    """Crosswalk every 2019 source feature to the date-stamped EKATTE roster."""
    hierarchy = json.loads((ROOT / "data/hierarchy.json").read_text(encoding="utf-8"))
    hierarchy_by_id = {row["id"]: row for row in hierarchy}
    district_by_code = {row["oblast"]: row for row in districts}
    municipality_by_name_parent = {
        (norm(row.get("name_en", "")), row["obshtina"][:3]): row
        for row in municipalities
    }
    rows = []
    for feature in source:
        props = feature["properties"]
        location_id = "gb:BGR:ADM2:" + props["shapeID"]
        atlas_row = atlas.get(location_id)
        parent_id = atlas_row.get("parent_id") if atlas_row else ""
        parent_row = hierarchy_by_id.get(parent_id, {})
        parent_name = parent_row.get("name", "")
        # EKATTE calls the capital district Sofia (stolitsa); the retained
        # Atlas source-parent unit is named Sofia City.
        district_name = "Sofia (stolitsa)" if parent_name == "Sofia City" else parent_name
        district = next((row for row in districts if norm(row.get("name_en", "")) == norm(district_name)), None)
        source_name = props["shapeName"]
        target_name = ALIASES.get(source_name.lower(), source_name)
        match = municipality_by_name_parent.get((norm(target_name), district["oblast"])) if district else None
        points = [point for ring in feature["geometry"]["coordinates"] for point in ring]
        rows.append({
            "source_shape_id": props["shapeID"],
            "source_2019_name": source_name,
            "atlas_location_id": location_id if atlas_row else "",
            "atlas_parent_id": parent_id,
            "atlas_parent_name": parent_name,
            "ekatte_district_code": district.get("oblast", "") if district else "",
            "ekatte_municipality_code": match.get("obshtina", "") if match else "",
            "ekatte_municipality_name_en": match.get("name_en", "") if match else "",
            "match_status": "matched" if match else "unmatched source feature",
            "geometry_type": feature["geometry"]["type"],
            "bbox_wgs84": json.dumps([
                min(point[0] for point in points), min(point[1] for point in points),
                max(point[0] for point in points), max(point[1] for point in points),
            ], separators=(",", ":")),
        })
    counts = {}
    for row in rows:
        code = row["ekatte_municipality_code"]
        if code:
            counts[code] = counts.get(code, 0) + 1
    for row in rows:
        code = row["ekatte_municipality_code"]
        if code and counts[code] > 1:
            row["match_status"] = "duplicate source candidate for one municipality"
    known_codes = {row["obshtina"] for row in municipalities}
    missing_official = [
        row for row in municipalities if row["obshtina"] not in counts
    ]
    FULL_OUT.parent.mkdir(parents=True, exist_ok=True)
    with FULL_OUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: row["source_shape_id"]))
    return {
        "geoBoundaries_feature_count": len(rows),
        "NSI_EKATTE_municipality_count": len(known_codes),
        "source_features_matched_to_EKATTE": sum(bool(row["ekatte_municipality_code"]) for row in rows),
        "unique_EKATTE_municipality_codes_matched": len(counts),
        "duplicate_source_candidates": [
            {"code": code, "features": [row["source_shape_id"] for row in rows if row["ekatte_municipality_code"] == code]}
            for code, count in counts.items() if count > 1
        ],
        "source_features_unmatched": [
            {"shape_id": row["source_shape_id"], "source_name": row["source_2019_name"], "parent": row["atlas_parent_name"]}
            for row in rows if not row["ekatte_municipality_code"]
        ],
        "official_municipalities_without_source_candidate": [
            {"code": row["obshtina"], "name_en": row.get("name_en", ""), "name_bg": row.get("name", "")}
            for row in missing_official
        ],
        "roster_comparison_note": "The official register's in-archive data-current-as-of date is 2023-12-12. Name/code/parent comparison does not validate any polygon boundary.",
        "roster_output": str(FULL_OUT.relative_to(ROOT)),
    }


def main():
    for relative, expected in EXPECTED_HASHES.items():
        actual = sha256(PACKET / relative)
        assert actual == expected, "%s SHA-256 mismatch: %s" % (relative, actual)
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    for relative, expected in baseline["inputs"].items():
        actual = sha256(ROOT / relative)
        assert actual == expected, "%s baseline SHA-256 mismatch: %s" % (relative, actual)
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    ids = scope["member_location_ids"]
    assert len(ids) == 213 and len(set(ids)) == 213
    assert hashlib.sha256(("\n".join(ids)).encode()).hexdigest() == (
        scope["member_location_ids_sha256"]
    )
    source = json.loads(GEOB.read_text(encoding="utf-8"))["features"]
    assert len(source) == 265
    by_shape = {feature["properties"]["shapeID"]: feature for feature in source}
    assert len(by_shape) == 265
    atlas = load_atlas()
    municipalities, districts = load_registers()
    full_audit = write_full_source_roster(source, atlas, municipalities, districts)
    district_by_code = {row["oblast"]: row for row in districts}
    municipality_by_name_parent = {}
    for row in municipalities:
        key = (norm(row.get("name_en", "")), row["obshtina"][:3])
        municipality_by_name_parent[key] = row
    province_names = {row["id"]: row["name"] for row in scope["province_scopes"]}

    rows = []
    for location_id in sorted(ids):
        source_id = location_id.rsplit(":", 1)[1]
        feature = by_shape[source_id]
        name = feature["properties"]["shapeName"]
        atlas_row = atlas[location_id]
        province_id = atlas_row["parent_id"]
        province_name = province_names[province_id]
        district = next(
            (row for row in districts if norm(row.get("name_en", "")) == norm(province_name)),
            None,
        )
        if district is None:
            raise AssertionError("No EKATTE district matches Atlas parent: " + province_name)
        target_name = ALIASES.get(name.lower(), name)
        register = municipality_by_name_parent.get((norm(target_name), district["oblast"]))
        if register is None:
            raise AssertionError("No EKATTE municipality+district match: %s / %s" % (name, province_name))
        geometry = feature["geometry"]
        rings = geometry["coordinates"]
        vertex_count = sum(len(ring) for ring in rings)
        points = [point for ring in rings for point in ring]
        bounds = (
            min(point[0] for point in points), min(point[1] for point in points),
            max(point[0] for point in points), max(point[1] for point in points),
        )
        rows.append({
            "location_id": location_id,
            "source_shape_id": source_id,
            "source_2019_name": name,
            "atlas_name": atlas_row["name"],
            "atlas_parent_id": province_id,
            "atlas_parent_name": province_name,
            "ekatte_municipality_code": register["obshtina"],
            "ekatte_municipality_name_en": register["name_en"],
            "ekatte_municipality_name_bg": register["name"],
            "ekatte_district_code": district["oblast"],
            "ekatte_district_name_en": district["name_en"],
            "ekatte_district_name_bg": district["name"],
            "name_crosswalk": "normalized exact" if norm(name) == norm(register["name_en"]) else "documented transliteration/name alias",
            "parent_name_match": "yes" if province_name == district["name_en"] else "review alias",
            "geometry_type": geometry["type"],
            "polygon_ring_count": len(rings),
            "polygon_vertex_count": vertex_count,
            "bbox_wgs84_min_longitude": bounds[0],
            "bbox_wgs84_min_latitude": bounds[1],
            "bbox_wgs84_max_longitude": bounds[2],
            "bbox_wgs84_max_latitude": bounds[3],
            "assessment": "insufficient-evidence",
            "assessment_reason": "official roster and role match; no reusable authoritative municipality geometry was available to validate this 2019 polygon",
        })
    assert len(rows) == len(ids)
    code_counts = {}
    for row in rows:
        code_counts[row["ekatte_municipality_code"]] = code_counts.get(row["ekatte_municipality_code"], 0) + 1
    duplicates = {code: count for code, count in code_counts.items() if count > 1}
    for row in rows:
        if row["ekatte_municipality_code"] in duplicates:
            row["assessment"] = "correction-needed"
            row["assessment_reason"] = (
                "two distinct 2019 polygon features crosswalk to this single official municipality code; "
                "resolve whether these are disconnected components to aggregate or a bad duplicate before use"
            )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "scoped_location_count": len(rows),
        "unique_official_municipality_codes": len({r["ekatte_municipality_code"] for r in rows}),
        "exact_2019_to_EKATTE_English_name_matches": sum(r["name_crosswalk"] == "normalized exact" for r in rows),
        "documented_name_aliases": sum(r["name_crosswalk"] != "normalized exact" for r in rows),
        "district_parent_name_matches": sum(r["parent_name_match"] == "yes" for r in rows),
        "duplicate_official_municipality_codes_in_scope": duplicates,
        "geometry_types": sorted({r["geometry_type"] for r in rows}),
        "assessment": "all scoped units remain insufficient-evidence for polygon correctness",
        "output": str(OUT.relative_to(ROOT)),
        "verified_source_hashes": EXPECTED_HASHES,
        "baseline_base_commit": baseline["base_commit"],
        "verified_baseline_hashes": baseline["inputs"],
        "full_source_roster_audit": full_audit,
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
