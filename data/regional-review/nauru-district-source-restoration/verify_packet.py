#!/usr/bin/env python3
"""Verify Nauru source inventory and reproduce the cautious area screen."""
import hashlib
import json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "data/regional-review/nauru-district-source-restoration"
PRIOR = ROOT / "data/regional-review/regional-review-4857646bb9b55df5"
crosswalk = json.loads((PACKET / "district-crosswalk.json").read_text())
assert len(crosswalk["districts"]) == 15
assert sum(row["geoboundaries_shape_id"] is not None for row in crosswalk["districts"]) == 14
assert len({row["geoboundaries_shape_id"] for row in crosswalk["districts"] if row["geoboundaries_shape_id"]}) == 14
assert crosswalk["districts"][-1]["official_popgis_name"] == "Location"

geo_path = PRIOR / "sources/geoBoundaries-NRU-ADM1.geojson"
geo_doc = json.loads(geo_path.read_text())
assert len(geo_doc["features"]) == 14
feature_map = {f["properties"]["shapeID"]: f for f in geo_doc["features"]}
assert set(feature_map) == {r["geoboundaries_shape_id"] for r in crosswalk["districts"] if r["geoboundaries_shape_id"]}

receipts = json.loads((PACKET / "source-receipts.json").read_text())
retained = {Path(r["path"]).name: r for r in receipts["existing_retained_sources"]}
for name, receipt in retained.items():
    payload = (ROOT / receipt["path"]).read_bytes()
    assert len(payload) == receipt["bytes"], name
    assert hashlib.sha256(payload).hexdigest() == receipt["sha256"], name

baseline = json.loads((PRIOR / "baseline-extract.json").read_text())
current = shape(baseline["locations"]["atlas:territory:NRU"]["geometry"])
district_union = unary_union([shape(f["geometry"]) for f in geo_doc["features"]])
project = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform
area = lambda g: transform(project, g).area / 1e6
result = {
    "district_features": len(geo_doc["features"]),
    "current_atlas_km2_equal_area": round(area(current), 6),
    "secondary_district_union_km2_equal_area": round(area(district_union), 6),
    "symmetric_difference_km2_equal_area": round(area(current.symmetric_difference(district_union)), 6),
    "current_fraction_overlapped_by_district_union": round(area(current.intersection(district_union)) / area(current), 8),
    "district_union_fraction_inside_current": round(area(current.intersection(district_union)) / area(district_union), 8),
    "popgis_polygon_overlay": "not attempted: proprietary binary decoder was not validated",
}
print(json.dumps(result, indent=2))
assert abs(result["current_atlas_km2_equal_area"] - 19.841771) < 0.00001
assert abs(result["secondary_district_union_km2_equal_area"] - 21.451447) < 0.00001
assert abs(result["symmetric_difference_km2_equal_area"] - 2.392553) < 0.00001
