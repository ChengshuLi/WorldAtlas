"""Screen scoped feature sizes against their pinned source ADM1 parents."""
import json
import hashlib
from pathlib import Path
from shapely.geometry import shape

ROOT = Path("data/regional-review/regional-review-626fdf640aab94e2")
parent_path = ROOT / "sources/geoboundaries-rus-adm1-2017-scoped-parent-features.geojson"
atlas_path = ROOT / "sources/current-scoped-features.geojson"
original_path = ROOT / "sources/geoboundaries-rus-adm2-2017-scoped-original-features.geojson"
lineage_path = ROOT / "findings/current-lineage.json"
input_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in [parent_path, atlas_path, original_path, lineage_path]}
expected_hashes = {
    "sources/geoboundaries-rus-adm1-2017-scoped-parent-features.geojson": "4dab95fa1bbb8aa0ffeeecca9bc269ece139aab4368faff8ed2d0890c05d6602",
    "sources/current-scoped-features.geojson": "44aa8bed8c6d3f6b7f4c553007efbaa82d39ff384790e95c06d1e3615ad4f070",
    "sources/geoboundaries-rus-adm2-2017-scoped-original-features.geojson": "7eb4cba61f0d17bfacb634c08aff3ec4873ece62734d518b51614bf061a5a129",
    "findings/current-lineage.json": "0781ff358d8e1e574eaecf1deea1b7fb1931a890105b17468ffecbe20d6f4874",
}
if input_hashes != expected_hashes:
    raise SystemExit(f"Unexpected source-screen inputs: {input_hashes}")
parents = json.loads(parent_path.read_text())["features"]
atlas = json.loads(atlas_path.read_text())["features"]
originals = json.loads(original_path.read_text())["features"]
lineage_doc = json.loads(lineage_path.read_text())
lineage = lineage_doc["rows"]
if lineage_doc["base_commit"] != "8e1162e3e364cebdec700ec796e2730379494922" or len(atlas) != 210 or len(originals) != 203:
    raise SystemExit("Unexpected pinned baseline or scope size")
parent_rows = json.loads((ROOT / "findings/parent-crosswalk.json").read_text())["rows"]
parent_by_id = {next(row["province_id"] for row in parent_rows if row["source_shape_id"] == feature["properties"]["shapeID"]): shape(feature["geometry"]) for feature in parents}
atlas_by_id = {feature["properties"]["id"]: feature for feature in atlas}
original_by_id = {feature["properties"]["shapeID"]: feature for feature in originals}
rows = []
for record in lineage:
    atlas_id = record["id"]
    properties = record["properties"]
    parent_id = properties["parent_id"]
    parent = parent_by_id[parent_id]
    feature = atlas_by_id[atlas_id]
    geometry = shape(feature["geometry"])
    original_id = properties["metadata"].get("original_id")
    source_geometry = shape(original_by_id[original_id]["geometry"])
    rows.append({
        "atlas_id": atlas_id,
        "parent_id": parent_id,
        "source_unit_id": original_id,
        "atlas_geometry_parent_area_fraction": geometry.intersection(parent).area / parent.area,
        "atlas_geometry_fraction_inside_parent": geometry.intersection(parent).area / geometry.area if geometry.area else 0,
        "source_adm2_parent_area_fraction": source_geometry.intersection(parent).area / parent.area,
        "source_adm2_geometry_fraction_inside_parent": source_geometry.intersection(parent).area / source_geometry.area if source_geometry.area else 0,
        "atlas_geometry_type": geometry.geom_type,
        "atlas_geometry_components": len(geometry.geoms) if geometry.geom_type == "MultiPolygon" else 1,
    })
result = {
    "version": 1,
    "issue": 395,
    "base_commit": json.loads((ROOT / "findings/current-lineage.json").read_text())["base_commit"],
    "method": "Shapely 2.1.2 planar intersection-area ratios in GeoJSON longitude/latitude coordinates; source and Atlas polygons are only compared for relative size and parent fit, not legal boundary truth",
    "input_hashes": input_hashes,
    "scope_count": len(rows),
    "unique_source_unit_count": len({row["source_unit_id"] for row in rows}),
    "province_max_source_area_fraction": {},
    "rows": rows,
}
for parent_id in parent_by_id:
    candidates = [row for row in rows if row["parent_id"] == parent_id]
    result["province_max_source_area_fraction"][parent_id] = max(row["source_adm2_parent_area_fraction"] for row in candidates)
unique_source_rows = {row["source_unit_id"]: row for row in rows}.values()
unique_source_rows = list(unique_source_rows)
result["unique_source_units_over_10_percent_of_parent"] = sum(row["source_adm2_parent_area_fraction"] > 0.1 for row in unique_source_rows)
result["unique_source_units_over_50_percent_of_parent"] = sum(row["source_adm2_parent_area_fraction"] > 0.5 for row in unique_source_rows)
(ROOT / "findings/size-screen.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"count": len(rows), "unique_source_units": len(unique_source_rows), "max_source_unit_share_of_parent": max(row["source_adm2_parent_area_fraction"] for row in unique_source_rows), "unique_units_over_10_percent": result["unique_source_units_over_10_percent_of_parent"], "unique_units_over_50_percent": result["unique_source_units_over_50_percent_of_parent"], "largest_units": sorted(({"atlas_id": row["atlas_id"], "fraction": row["source_adm2_parent_area_fraction"]} for row in unique_source_rows), key=lambda row: row["fraction"], reverse=True)[:5]}, indent=2))
