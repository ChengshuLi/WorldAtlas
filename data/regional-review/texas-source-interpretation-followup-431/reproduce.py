#!/usr/bin/env python3
"""Reproduce the Texas 254-row CBF component and retained-source erratum."""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import re
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / "data/regional-review/regional-review-508c7e9f3a462f8f"
CONTRACT = json.loads((HERE / "issue-1138-contract.json").read_text())
WORK = json.loads(re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", CONTRACT["body"], re.S).group(1))
SCOPE = WORK["evidence_quality"]["subject_ids"]
SOURCE = BASE / "runs/twelve/county-assessments.jsonl"
ZIP = BASE / "source/census-2018/cb_2018_us_county_500k.zip"

rows = [json.loads(line) for line in SOURCE.read_text().splitlines() if line]
assert len(SCOPE) == len(set(SCOPE)) == 254
assert len(rows) == len({r["subject_id"] for r in rows}) == 254
by_id = {r["subject_id"]: r for r in rows}
assert set(by_id) == set(SCOPE), "county roster differs from issue contract"

component_counts = collections.Counter(r["multipart_components"]["census2018_cbf_500k"] for r in rows)
type_counts = collections.Counter(r["geometry_types"]["census2018_cbf_500k"] for r in rows)
expected = {1: 243, 3: 5, 4: 1, 5: 1, 6: 1, 7: 2, 26: 1}
assert dict(component_counts) == expected
assert type_counts == {"Polygon": 243, "MultiPolygon": 11}
assert sum(k * v for k, v in component_counts.items()) == 313

with zipfile.ZipFile(ZIP) as archive:
    prj_name = "cb_2018_us_county_500k.prj"
    prj = archive.read(prj_name).decode("ascii")
    assert 'GCS_North_American_1983' in prj and 'D_North_American_1983' in prj
    assert 'GRS_1980' in prj

retrieval = json.loads((BASE / "source/census-api-retrieval-manifest.json").read_text())
census_crs = {}
for item in retrieval:
    if item["file"].endswith("texas-counties.geojson"):
        census_crs[str(item["vintage"])] = {
            "request_url": item["url"],
            "retrieved_at": item["retrieved_at"],
            "requested_output_crs": "EPSG:4326 (outSR parameter)",
        }
    elif item["file"].endswith("counties-layer-metadata.json"):
        metadata = json.loads((BASE / "source" / item["file"]).read_text())
        census_crs[f"{item['vintage']}_service_layer"] = {
            "url": item["url"],
            "retrieved_at": item["retrieved_at"],
            "native_and_latest_spatial_reference": metadata["spatialReference"],
        }
assert {"2018", "2025", "2018_service_layer", "2025_service_layer"} == set(census_crs)
api_features = {}
for year in ("2018", "2025"):
    collection = json.loads((BASE / f"source/census-{year}/texas-counties.geojson").read_text())
    assert collection["type"] == "FeatureCollection" and len(collection["features"]) == 254
    key = "GEOID" if year == "2018" else "GEOID"
    by_geoid = {f["properties"][key]: f for f in collection["features"]}
    assert len(by_geoid) == 254
    assert all(f["geometry"]["type"] == "Polygon" for f in collection["features"])
    api_features[year] = by_geoid
geoboundaries = json.loads((BASE / "source/geoBoundaries-USA-ADM2.geojson").read_text())
geoboundaries_crs = geoboundaries.get("crs", {}).get("properties", {}).get("name")
assert geoboundaries_crs == "urn:ogc:def:crs:OGC:1.3:CRS84"

scope_hash = hashlib.sha256(json.dumps(sorted(SCOPE), separators=(",", ":")).encode()).hexdigest()
out = HERE / "county-interpretation-erratum.jsonl"
with out.open("w") as f:
    for sid in sorted(SCOPE):
        row = by_id[sid]
        components = row["multipart_components"]["census2018_cbf_500k"]
        api_2018 = api_features["2018"][row["census_geoid_2018"]]
        api_2025 = api_features["2025"][row["census_geoid_2025"]]
        assert api_2018["geometry"]["type"] == row["geometry_types"]["census2018"] == "Polygon"
        assert api_2025["geometry"]["type"] == row["geometry_types"]["census2025"] == "Polygon"
        record = {
            "subject_id": sid,
            "name": row["atlas_name"],
            "source_id": row["source_id"],
            "parent_id": row["parent_id"],
            "census_geoid_2018": row["census_geoid_2018"],
            "census_geoid_2025": row["census_geoid_2025"],
            "census_2018_tigerweb_record_geometry_type": api_2018["geometry"]["type"],
            "census_2018_tigerweb_polygon_component_count": 1,
            "census_2025_tigerweb_record_geometry_type": api_2025["geometry"]["type"],
            "census_2025_tigerweb_polygon_component_count": 1,
            "census_2018_cbf_record_geometry_type": row["geometry_types"]["census2018_cbf_500k"],
            "census_2018_cbf_polygon_component_count": components,
            "record_is_not_component": True,
            "geometry_interpretation": "one county feature/record; Polygon has one component; MultiPolygon has the stated number of polygon components",
            "source_crs": "GCS_North_American_1983; datum D_North_American_1983; GRS_1980 ellipsoid; geographic degrees, per archive .prj",
            "legacy_transform_note": "The 2018 CBF shapes were passed to the legacy EPSG:4326-to-6933 transformer as if their coordinates were WGS 84. This is an undocumented NAD83-as-WGS84 coordinate approximation; no datum operation or accuracy was recorded.",
            "numerical_effect_measured": False,
            "boundary_completeness_established": False,
            "historical_assessment_preserved": row["classification"],
        }
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

summary = {
    "issue": 1138,
    "scope_count": len(SCOPE),
    "scope_subject_ids_sha256_lf_sorted": scope_hash,
    "source_rows": len(rows),
    "tigerweb_2018_query_features": 254,
    "tigerweb_2018_geometry_type_counts": {"Polygon": 254},
    "tigerweb_2018_polygon_components_total": 254,
    "tigerweb_2025_query_features": 254,
    "tigerweb_2025_geometry_type_counts": {"Polygon": 254},
    "tigerweb_2025_polygon_components_total": 254,
    "record_geometry_type_counts": dict(sorted(type_counts.items())),
    "polygon_component_count_distribution": {str(k): component_counts[k] for k in sorted(component_counts)},
    "polygon_components_total": 313,
    "crs_prj_member": prj_name,
    "crs_prj_text": prj,
    "other_input_crs_declarations": {
        "census_tigerweb": census_crs,
        "geoboundaries_geojson": geoboundaries_crs,
        "texas_government_guide": "PDF text; no coordinate reference system applies.",
        "texas_constitution": "No provision bytes retained; no coordinate reference system applies.",
    },
    "numerical_effect_measured": False,
    "original_assessments_modified": False,
    "boundary_completeness_or_legal_validity_inferred": False,
}
(HERE / "reproduction-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
print(json.dumps({"rows": len(rows), "types": dict(type_counts), "components": dict(component_counts), "total_components": 313, "scope_sha256": scope_hash}, sort_keys=True))
