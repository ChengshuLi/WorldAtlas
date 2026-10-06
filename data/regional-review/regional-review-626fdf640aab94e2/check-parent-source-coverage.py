"""Compare source ADM2 feature coverage to the seven pinned ADM1 parent units.

Requires Shapely 2.1.2 (listed in repository requirements.txt). The full raw
ADM2 source is restored using the URL in README.md and passed as argv[1].
"""
import hashlib
import json
import sys
from pathlib import Path
from shapely.geometry import shape

ROOT = Path("data/regional-review/regional-review-626fdf640aab94e2")
source_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/geoboundaries-RUS-ADM2-pinned.geojson")
raw = source_path.read_bytes()
raw_sha = hashlib.sha256(raw).hexdigest()
expected_sha = "74012237384e53061aa63b6e20b9be24f94facfe615b52bbe72e62a81fa68ff0"
if raw_sha != expected_sha:
    raise SystemExit(f"Pinned ADM2 source SHA mismatch: {raw_sha}")
units = json.loads(raw)["features"]
unit_geometries = [(f["properties"]["shapeID"], f["properties"]["shapeName"], shape(f["geometry"])) for f in units]
parent_features = json.loads((ROOT / "sources/geoboundaries-rus-adm1-2017-scoped-parent-features.geojson").read_text())["features"]
parent_rows = json.loads((ROOT / "findings/parent-crosswalk.json").read_text())["rows"]
parent_path = ROOT / "sources/geoboundaries-rus-adm1-2017-scoped-parent-features.geojson"
parent_sha = hashlib.sha256(parent_path.read_bytes()).hexdigest()
if parent_sha != "4dab95fa1bbb8aa0ffeeecca9bc269ece139aab4368faff8ed2d0890c05d6602":
    raise SystemExit(f"Unexpected ADM1 parent extract hash: {parent_sha}")
lineage_doc = json.loads((ROOT / "findings/current-lineage.json").read_text())
lineage = lineage_doc["rows"]
if lineage_doc["base_commit"] != "8e1162e3e364cebdec700ec796e2730379494922":
    raise SystemExit("Current Atlas source lineage is not pinned to the declared main baseline")
rows = []
for parent in parent_features:
    props = parent["properties"]
    atlas_parent = next(row["province_id"] for row in parent_rows if row["source_shape_id"] == props["shapeID"])
    parent_geometry = shape(parent["geometry"])
    expected_ids = sorted({
        row["properties"]["metadata"].get("original_id")
        for row in lineage
        if row["properties"].get("parent_id") == atlas_parent
        and row["properties"]["metadata"].get("original_id")
    })
    expected_set = set(expected_ids)
    overlaps = []
    for source_id, name, geometry in unit_geometries:
        intersection_area = geometry.intersection(parent_geometry).area
        if intersection_area <= 0:
            continue
        fraction = intersection_area / geometry.area if geometry.area else 0
        overlaps.append({"source_id": source_id, "source_name": name, "source_area_fraction_in_parent": fraction})
    # Ignore machine-precision slivers below 1e-6 of a source feature. The
    # retained fractions still expose these cases and the threshold is explicit.
    overlapping_ids = {row["source_id"] for row in overlaps if row["source_area_fraction_in_parent"] > 1e-6}
    missing = sorted(overlapping_ids - expected_set)
    unexpected = sorted(expected_set - overlapping_ids)
    rows.append({
        "atlas_parent_id": atlas_parent,
        "parent_name": props["shapeName"],
        "parent_source_id": props["shapeID"],
        "atlas_original_source_unit_count": len(expected_set),
        "source_units_overlapping_parent_above_1e-6": len(overlapping_ids),
        "missing_from_atlas_source_ids": missing,
        "unexpected_atlas_source_ids": unexpected,
        "units": sorted((row for row in overlaps if row["source_id"] in expected_set), key=lambda row: row["source_id"]),
    })
if sum(row["atlas_original_source_unit_count"] for row in rows) != 203:
    raise SystemExit("Expected 203 unique in-scope original source units")
if any(row["missing_from_atlas_source_ids"] or row["unexpected_atlas_source_ids"] for row in rows):
    raise SystemExit("Source ADM2 units overlapping parent do not exactly match Atlas source lineage")
result = {
    "version": 1,
    "issue": 395,
    "base_commit": "8e1162e3e364cebdec700ec796e2730379494922",
    "source_sha256": raw_sha,
    "parent_extract_sha256": parent_sha,
    "source_feature_count": len(units),
    "source_metadata_unit_count": 2328,
    "source_feature_metadata_discrepancy": 1,
    "spatial_method": "Shapely planar intersection area in source GeoJSON longitude/latitude coordinates; include source unit if its fraction of area intersecting the ADM1 parent is > 1e-6; exact source IDs compared to Atlas source lineage, with ecological fragments mapped to original administrative IDs",
    "all_parent_unit_sets_match": True,
    "total_scoped_original_source_units": 203,
    "parents": rows,
}
(ROOT / "findings/parent-source-coverage.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"source_features": len(units), "parent_source_units": sum(row["atlas_original_source_unit_count"] for row in rows), "all_parent_unit_sets_match": True, "per_parent_counts": {row["parent_name"]: row["atlas_original_source_unit_count"] for row in rows}}, ensure_ascii=False, indent=2))
