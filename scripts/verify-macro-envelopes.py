#!/usr/bin/env python3
"""Independently check frozen macro envelopes against every source location."""
import argparse, gzip, hashlib, json
from pathlib import Path
from shapely import STRtree, from_wkb, prepare
from shapely.geometry import shape

parser = argparse.ArgumentParser()
parser.add_argument('--data', default='data')
parser.add_argument('--envelopes', default='data/macro-foundation/envelopes-v3')
parser.add_argument('--output', required=True)
args = parser.parse_args()
data, directory = Path(args.data), Path(args.envelopes)
sha = lambda raw: hashlib.sha256(raw).hexdigest()
index_bytes = (directory / 'envelope-index.json').read_bytes()
index = json.loads(index_bytes)
units = {u['id']: u for u in json.loads((data / 'hierarchy.json').read_bytes())}
if index['hierarchy_sha256'] != sha((data / 'hierarchy.json').read_bytes()):
    raise ValueError('Frozen envelope hierarchy differs from current hierarchy')
macro = {k: u for k, u in units.items() if u['level'] in ('continent', 'subcontinent', 'region')}
rows = {r['id']: r for r in index['groups']}
if len(rows) != len(index['groups']) or set(rows) != set(macro):
    raise ValueError('Envelope inventory is incomplete or duplicated')
geometries = {}
zero_area_overlay_artifacts = []
for identity, row in rows.items():
    asset = directory / row['path']
    if asset.parent != directory or sha(asset.read_bytes()) != row['sha256']:
        raise ValueError('Envelope asset hash or path mismatch')
    raw = gzip.decompress(asset.read_bytes())
    if sha(raw) != row['geometry_sha256']:
        raise ValueError('Envelope geometry hash mismatch')
    geometry = from_wkb(raw)
    if geometry.is_empty or not geometry.is_valid or geometry.area <= 0 or geometry.geom_type not in ('Polygon', 'MultiPolygon', 'GeometryCollection'):
        raise ValueError('Invalid frozen envelope: ' + identity)
    if geometry.geom_type == 'GeometryCollection':
        # make_valid may retain collapsed boundary segments. They have no land
        # area; preserve them exactly rather than silently altering frozen WKB.
        if any(part.geom_type not in ('Polygon', 'MultiPolygon', 'LineString', 'MultiLineString', 'Point', 'MultiPoint') for part in geometry.geoms):
            raise ValueError('Unsupported envelope collection component')
        zero_area_overlay_artifacts.append(identity)
    geometries[identity] = geometry
    prepare(geometry)
    if row['parent_id'] != macro[identity]['parent_id'] or row['name'] != macro[identity]['name']:
        raise ValueError('Stale frozen geographic identity')
member_ids = {identity: [] for identity in macro}
locations = set()
for part in json.loads((data / 'world-index.json').read_bytes())['parts']:
    for feature in json.loads((data / part).read_bytes())['features']:
        identity = feature['id']
        if identity in locations:
            raise ValueError('Duplicate source location')
        locations.add(identity)
        geometry = shape(feature['geometry'])
        parent = feature['properties']['parent_id']
        for tier in ('province', 'area', 'region', 'subcontinent', 'continent'):
            unit = units[parent]
            if unit['level'] != tier:
                raise ValueError('Invalid adjacent-tier chain')
            if parent in geometries:
                member_ids[parent].append(identity)
                envelope = geometries[parent]
                if not envelope.covers(geometry) and not geometry.difference(envelope).buffer(-1e-9).is_empty:
                    raise ValueError('Source land missing from frozen envelope: ' + identity)
            parent = unit['parent_id']
        if parent is not None:
            raise ValueError('Continent has a parent')
for identity, ids in member_ids.items():
    encoded = json.dumps(sorted(ids), separators=(',', ':'), ensure_ascii=False).encode()
    if len(ids) != rows[identity]['locations'] or sha(encoded) != rows[identity]['member_location_ids_sha256']:
        raise ValueError('Frozen envelope membership mismatch')
for identity, unit in macro.items():
    parent = unit['parent_id']
    if parent is not None and not geometries[identity].difference(geometries[parent]).buffer(-1e-9).is_empty:
        raise ValueError('Child envelope lies outside its parent')
for tier in ('continent', 'subcontinent', 'region'):
    shapes = [geometries[k] for k, u in macro.items() if u['level'] == tier]
    tree = STRtree(shapes)
    for i, geometry in enumerate(shapes):
        for j in tree.query(geometry):
            if j > i and not geometry.intersection(shapes[j]).buffer(-1e-6).is_empty:
                raise ValueError('Material same-tier envelope overlap')
report = {'verified': True, 'locations': len(locations), 'macro_groups': len(rows), 'envelopes_manifest_sha256': sha(index_bytes), 'hierarchy_sha256': index['hierarchy_sha256'], 'all_source_land_conserved': True, 'material_same_tier_overlaps': 0, 'child_land_outside_parent': 0, 'retained_zero_area_overlay_artifact_groups': zero_area_overlay_artifacts, 'source_conservation_corridor_degrees': 1e-9, 'source_overlay_ribbon_corridor_degrees': 1e-6, 'source_completeness_approved': False, 'regional_interiors_approved': False}
Path(args.output).write_text(json.dumps(report, separators=(',', ':')) + '\n')
print(json.dumps(report))
