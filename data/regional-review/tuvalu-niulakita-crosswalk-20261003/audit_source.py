#!/usr/bin/env python3
"""Read-only audit of all eight pinned Tuvalu ADM1 features."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data/regional-review/regional-review-a5b86fc6ff2463cd/sources/TUV/geoBoundaries-TUV-ADM1.geojson"
EXPECTED = {
    "Nanumanga": "17741764B49308440506872",
    "Nanumea": "17741764B36602748519227",
    "Niutao": "17741764B1294645335794",
    "Nui": "17741764B90379454256238",
    "Vaitupu": "17741764B83632895409465",
    "Nukufetau": "17741764B30576374901893",
    "Funafuti": "17741764B42950471856320",
    "Nukulaelae": "17741764B45323499156113",
}
NIULAKITA = (179.47402778, -10.78578333)  # first WGS84 point, baseline order Schedule 1 Part 6


def coordinate_pairs(value):
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and all(isinstance(v, (int, float)) for v in value[:2]):
            yield value[0], value[1]
        else:
            for child in value:
                yield from coordinate_pairs(child)


def component_count(geometry):
    if geometry["type"] == "MultiPolygon":
        return len(geometry["coordinates"])
    if geometry["type"] == "Polygon":
        return 1
    raise ValueError(f"Unexpected geometry type: {geometry['type']}")


data = json.loads(SOURCE.read_text(encoding="utf-8"))
assert data["type"] == "FeatureCollection"
assert len(data["features"]) == len(EXPECTED), len(data["features"])
seen = {}
for feature in data["features"]:
    props = feature["properties"]
    name, shape_id = props["shapeName"], props["shapeID"]
    assert name in EXPECTED and EXPECTED[name] == shape_id, (name, shape_id)
    assert name not in seen
    coords = list(coordinate_pairs(feature["geometry"]["coordinates"]))
    assert coords
    bbox = [min(p[0] for p in coords), min(p[1] for p in coords), max(p[0] for p in coords), max(p[1] for p in coords)]
    seen[name] = {
        "source_feature_id": f"gb:TUV:ADM1:{shape_id}",
        "geometry_type": feature["geometry"]["type"],
        "connected_polygon_parts": component_count(feature["geometry"]),
        "coordinate_vertex_count": len(coords),
        "bbox_wgs84": [round(x, 8) for x in bbox],
        "rounded_niulakita_point_inside_bbox": bbox[0] <= NIULAKITA[0] <= bbox[2] and bbox[1] <= NIULAKITA[1] <= bbox[3],
    }
assert set(seen) == set(EXPECTED)
assert not any(v["rounded_niulakita_point_inside_bbox"] for v in seen.values())
print(json.dumps({
    "source": str(SOURCE.relative_to(ROOT)),
    "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "feature_count": len(seen),
    "niulakita_screen_point_wgs84": list(NIULAKITA),
    "features": seen,
    "limitations": "BBox exclusion is a reproducible separation screen, not a cadastral boundary or legal coverage test. The point is one maritime baseline point rounded to 1e-8 degrees; source polygons are 2017 ADM1 cartographic data.",
}, indent=2, sort_keys=True))
