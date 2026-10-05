"""Inventory physical-reference land missing from immutable atlas footprints.

This diagnostic never assigns locations, changes geography, or certifies water.
Tile fragments are deliberately retained without area filtering or simplification.
They are not counts of globally connected gaps. Invalid source geometry blocks
affected tiles; it is never silently repaired. All coordinates are lon/lat WGS84.
"""
import argparse
import gzip
import hashlib
import json
import math
import pathlib
import subprocess
import sys

import shapely
from shapely import STRtree, union_all
from shapely.geometry import box, mapping, shape
from shapely.validation import explain_validity
from evidence.geometry import METHOD, land_area_m2
from evidence.immutable import Baseline, canonical_json, descriptor, deterministic_gzip

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_ROOT = 'data/macro-foundation/retained-inspections/retained-geographic-sources/namibia/'
LAND = SOURCE_ROOT + 'natural-earth-land.geojson.gz.gz'
SOURCE_MANIFEST = SOURCE_ROOT + 'manifest.json.gz'
VERSION = 'worldatlas-geographic-gap-audit-v1'


def bundle_outputs(report, out):
    """Losslessly consolidate tile fragments into reviewable, bounded files."""
    original = report['outputs']
    report['outputs'] = []
    features, budget = [], 0

    def flush():
        nonlocal features, budget
        if not features:
            return
        raw = canonical_json({'type': 'FeatureCollection', 'features': features})
        if len(raw) > 32 * 1024 * 1024:
            raise ValueError('Candidate bundle exceeds byte budget')
        encoded = deterministic_gzip(raw)
        path = out / f'candidates-{len(report["outputs"]):03d}.geojson.gz'
        with path.open('xb') as stream:
            stream.write(encoded)
        report['outputs'].append({**descriptor(str(path.relative_to(ROOT)), encoded),
                                  'uncompressed_sha256': hashlib.sha256(raw).hexdigest(), 'uncompressed_bytes': len(raw)})
        features, budget = [], 0

    for entry in original:
        path = ROOT / entry['path']
        for feature in json.loads(gzip.decompress(path.read_bytes()))['features']:
            size = len(canonical_json(feature))
            if budget + size > 16 * 1024 * 1024:
                flush()
            features.append(feature)
            budget += size
    flush()
    # Only regenerable tile intermediates are removed after all final bundles exist.
    for entry in original:
        (ROOT / entry['path']).unlink()


def decode(raw, layers=1):
    for _ in range(layers):
        raw = gzip.decompress(raw)
        if len(raw) > 32 * 1024 * 1024:
            raise ValueError('Decoded source exceeds 32 MiB budget')
    return raw


def polygons(geometry):
    if geometry.geom_type == 'Polygon':
        if not geometry.is_empty and geometry.area > 0:
            yield geometry
    elif hasattr(geometry, 'geoms'):
        for child in geometry.geoms:
            yield from polygons(child)


def difference_tile(tile, land, locations, water=()):
    """Clip before union: bounded working geometry, exact source holes preserved."""
    physical = union_all([g.intersection(tile) for g in land])
    occupied = union_all([g.intersection(tile) for g in locations])
    return physical.difference(union_all([occupied, *[g.intersection(tile) for g in water]]))


def tiles(bounds, size):
    west, south, east, north = bounds
    y = south
    while y < north:
        x = west
        while x < east:
            yield (x, y, min(east, x + size), min(north, y + size))
            x += size
        y += size


def load_inputs(repo, commit, water_reference=None):
    raw = subprocess.check_output(['git', '-C', str(repo), 'show', commit + ':data/world-index.json'])
    baseline = Baseline(repo, commit, [descriptor('data/world-index.json', raw)])
    pins = dict(baseline.pins)

    def read(path):
        data = baseline.read(path)
        pins[path] = descriptor(path, data)
        return data

    read('data/hierarchy.json')
    read('data/canonical-grid/manifest.json')
    source = next(s for s in json.loads(decode(read(SOURCE_MANIFEST)))['sources']
                  if s['path'] == 'natural-earth-land.geojson.gz')
    retained = decode(read(LAND))
    original = decode(retained)
    if hashlib.sha256(retained).hexdigest() != source['retained_sha256'] or hashlib.sha256(original).hexdigest() != source['original_sha256']:
        raise ValueError('Retained land reference fails original source receipt')
    land = [shape(f['geometry']) for f in json.loads(original)['features']]
    # Fail explicitly if a reference is invalid: it cannot define reliable land.
    for g in land:
        if not g.is_valid:
            raise ValueError('Invalid physical reference: ' + explain_validity(g))
    water, water_source = [], None
    if water_reference:
        water_source = json.loads(read(water_reference + '/receipt.json'))
        water_encoded = read(water_reference + '/natural-earth-lakes.geojson.gz')
        water_raw = decode(water_encoded)
        if hashlib.sha256(water_encoded).hexdigest() != water_source['retained_sha256'] or hashlib.sha256(water_raw).hexdigest() != water_source['original_sha256']:
            raise ValueError('Water reference fails original source receipt')
        water = [shape(f['geometry']) for f in json.loads(water_raw)['features']]
        if any(not g.is_valid for g in water):
            raise ValueError('Invalid water reference; no implicit repair allowed')
    locations, metadata, invalid, seen = [], [], [], set()
    for part in json.loads(raw)['parts']:
        for f in json.loads(read('data/' + part))['features']:
            identity = f.get('id') or f['properties']['id']
            if identity in seen:
                raise ValueError('Duplicate location ID: ' + identity)
            seen.add(identity)
            g = shape(f['geometry'])
            record = {'id': identity, 'name': f['properties']['name'],
                      'source': f['properties'].get('metadata', {}).get('source_url'),
                      'reference_year': f['properties'].get('metadata', {}).get('reference_year')}
            if not g.is_valid or g.geom_type not in ('Polygon', 'MultiPolygon'):
                invalid.append({**record, 'bounds': list(g.bounds), 'reason': explain_validity(g)})
            else:
                locations.append(g)
                metadata.append(record)
    return land, water, locations, metadata, invalid, list(pins.values()), source, water_source


def run(args):
    if not all(math.isfinite(n) for n in args.bounds) or not (-180 <= args.bounds[0] < args.bounds[2] <= 180 and -60 <= args.bounds[1] < args.bounds[3] <= 85.0511287798066):
        raise ValueError('Bounds must be within the declared non-Antarctic Mercator audit domain')
    if not math.isfinite(args.tile_degrees) or not 0.25 <= args.tile_degrees <= 10:
        raise ValueError('Tile size must be between 0.25 and 10 degrees')
    out = pathlib.Path(args.output).resolve()
    owned = ROOT / 'coordination/engineering'
    if owned not in out.parents or out.exists():
        raise ValueError('Use a NEW output directory beneath coordination/engineering; never overwrite a vintage')
    land, water, locations, metadata, invalid, pins, source, water_source = load_inputs(ROOT, args.commit, args.water_reference)
    lt, wt, ft = STRtree(land), STRtree(water), STRtree(locations)
    out.mkdir(parents=True, exist_ok=False)
    report = {'version': VERSION, 'baseline_commit': args.commit, 'inputs': pins,
              'physical_reference': source, 'water_reference': water_source, 'bounds': args.bounds, 'tile_degrees': args.tile_degrees,
              'method': METHOD, 'software': {'python': sys.version.split()[0], 'shapely': shapely.__version__, 'geos': shapely.geos_version_string},
              'locations': len(locations) + len(invalid), 'invalid_locations': invalid,
              'tiles_scanned': 0, 'tiles_blocked': [], 'candidate_fragments': 0,
              'candidate_area_m2': 0, 'measurement_errors': [], 'outputs': [],
              'limits': ['Reference is Natural Earth 1:10m physical land, not detailed hydrography or a complete island inventory.',
                         'Every result is a candidate: rivers, reservoirs, coast and source vintages remain unverified.',
                         'No political affiliation, boundary repair, geographic approval or deployment.',
                         'Tile fragments are not globally connected component counts; joining and actual canonical-grid comparison remain separate checks.',
                         'Antarctica/south of 60S and north of the Mercator limit are excluded; this is a declared-domain audit.',
                         'Nearest location uses planar degrees for identification only, never a claimed physical distance or adjacency.']}
    for i, bounds in enumerate(tiles(args.bounds, args.tile_degrees)):
        tile = box(*bounds)
        bad = [r['id'] for r in invalid if box(*r['bounds']).intersects(tile)]
        if bad:
            report['tiles_blocked'].append({'bounds': bounds, 'invalid_location_ids': bad})
            continue
        li = lt.query(tile, predicate='intersects')
        if not len(li):
            report['tiles_scanned'] += 1
            continue
        fi = ft.query(tile, predicate='intersects')
        physical = union_all([land[int(j)].intersection(tile) for j in li])
        wi = wt.query(tile, predicate='intersects')
        if len(wi):
            physical = physical.difference(union_all([water[int(j)].intersection(tile) for j in wi]))
        missing = physical.difference(union_all([locations[int(j)].intersection(tile) for j in fi]))
        # Remove artificial tile edges before marking reference coastline contact.
        shore = physical.boundary.difference(tile.boundary)
        features = []
        for j, piece in enumerate(polygons(missing)):
            point = piece.representative_point()
            nearest = metadata[int(ft.nearest(point))] if locations else None
            near = ft.query(piece.buffer(.02), predicate='intersects')
            try:
                area = land_area_m2(piece)
                report['candidate_area_m2'] += area
            except ValueError as error:
                area = None
                report['measurement_errors'].append({'tile': i, 'fragment': j, 'error': str(error)})
            features.append({'type': 'Feature', 'id': f'{i}:{j}', 'properties': {
                'status': 'reference-supported-uncovered-candidate', 'tile': list(bounds),
                'sample_lonlat': list(point.coords)[0], 'area_m2': area,
                'touches_tile_edge': piece.intersects(tile.boundary), 'nearest_location': nearest,
                'touches_reference_shore': piece.intersects(shore),
                'nearby_locations': [metadata[int(k)] for k in sorted(near)],
                'water_status': 'unverified'}, 'geometry': mapping(piece)})
        if features:
            name = f'tile-{i:04d}.geojson.gz'
            value = {'type': 'FeatureCollection', 'features': features}
            raw = canonical_json(value)
            if len(raw) > 32 * 1024 * 1024:
                raise ValueError('Tile output exceeds byte budget; use smaller tiles')
            encoded = deterministic_gzip(raw)
            (out / name).write_bytes(encoded)
            report['outputs'].append({**descriptor(str((out / name).relative_to(ROOT)), encoded),
                                      'uncompressed_sha256': hashlib.sha256(raw).hexdigest(), 'uncompressed_bytes': len(raw)})
            report['candidate_fragments'] += len(features)
        report['tiles_scanned'] += 1
        if i % 50 == 0:
            print(json.dumps({'tile': i, 'candidate_fragments': report['candidate_fragments']}), flush=True)
    bundle_outputs(report, out)
    report['status'] = 'partial' if report['tiles_blocked'] or report['measurement_errors'] else 'declared-domain-scan-complete'
    (out / 'report.json').write_bytes(canonical_json(report))
    print(json.dumps({k: report[k] for k in ('status', 'tiles_scanned', 'candidate_fragments', 'candidate_area_m2')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True, help='Exact immutable 40-character input commit')
    parser.add_argument('--output', required=True)
    parser.add_argument('--bounds', nargs=4, type=float, default=[-180, -60, 180, 85.0511287798066])
    parser.add_argument('--tile-degrees', type=float, default=5)
    parser.add_argument('--water-reference', help='Immutable Git source directory containing lake GeoJSON and its receipt')
    run(parser.parse_args())
