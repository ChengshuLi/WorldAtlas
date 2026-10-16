"""Derive explicit views using the unchanged retained periodic canonicalizer.

Original source and physical evidence stay byte-identical. Only geometries with
an actual out-of-frame longitude are requested; the native verifier rejects any
material overrun or changed cell/boundary outcome separately.
"""
import json
import sys
from pathlib import Path
from shapely.geometry import shape, mapping

root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(root / 'scripts'))
from majority import canonical

prefix = root / 'coordination/engineering/fiji-current-cell-20261016'
records = []

def overrun(value):
    if isinstance(value, list):
        if len(value) == 2 and all(isinstance(n, (int, float)) for n in value):
            return abs(value[0]) > 180
        return any(overrun(child) for child in value)
    return False

def add(role, source_id, pointer, geometry):
    if overrun(geometry.get('coordinates', [])):
        records.append(dict(role=role, source_id=source_id, pointer=pointer,
                            original_geometry=geometry,
                            geometry=mapping(canonical(shape(geometry)))))

for source in json.loads((prefix / 'original-stage-inputs.json').read_text()):
    add('source', source['target'], '/geometry', source['consumed']['geometry'])
for result in json.loads((prefix / 'physical-001/whole-target-support.json').read_text())['results']:
    for field in ('mapped_land_support', 'mapped_inland_water_support', 'outside_mapped_L1_context'):
        add('physical', result['target'], '/support/' + field, result['support'][field])
    for ordinal, query in enumerate(result['query_relations']):
        geometry = query.get('witness_geometry')
        if geometry and geometry['type'] in ('Polygon', 'MultiPolygon'):
            add('physical', result['target'], f'/query_relations/{ordinal}/witness_geometry', geometry)
print(json.dumps(records, separators=(',', ':')))
