"""Repair display geometry without changing source identity or hierarchy."""
import json, pathlib, sys
from shapely import make_valid, union_all
from shapely.geometry import shape, mapping

def polygons(geometry):
    if geometry.geom_type == 'Polygon': return [geometry]
    return [polygon for part in getattr(geometry, 'geoms', []) for polygon in polygons(part)]

target = pathlib.Path(sys.argv[1])
paths = sorted(target.glob('part-*.json')) if target.is_dir() else [target]
count = 0
for path in paths:
    data = json.loads(path.read_text())
    changed = False
    for feature in data['features']:
        geometry = shape(feature['geometry'])
        if geometry.is_valid and not geometry.is_empty: continue
        repaired = union_all(polygons(make_valid(geometry)))
        assert repaired.is_valid and not repaired.is_empty, feature['id']
        assert repaired.geom_type in ('Polygon', 'MultiPolygon'), feature['id']
        feature['geometry'] = mapping(repaired)
        feature['properties'].setdefault('metadata', {})['display_geometry_repaired'] = True
        changed = True
        count += 1
    if changed: path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
print(f'Repaired {count} display geometries in {target}.')
