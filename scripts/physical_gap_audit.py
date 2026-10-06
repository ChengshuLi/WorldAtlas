"""Independent land before water: diagnostic candidates, never owner assignment.

The old water-screened detector and its immutable products remain unchanged.
All geometry operations use original lon/lat coordinates without repair,
rounding, snapping, buffering, simplification, or minimum-area exclusions.
"""
import gzip
import hashlib
import json
import math
import subprocess

from shapely import STRtree, get_coordinates, union_all
from shapely.geometry import box, mapping, shape
from shapely.validation import explain_validity

from evidence.immutable import Baseline, canonical_json, descriptor

VERSION = 'worldatlas-physical-land-before-water-v1'
DOMAIN = (-180, -60, 180, 85.0511287798066)
LAND_ROOT = 'data/macro-foundation/retained-inspections/retained-geographic-sources/namibia/'
MAX_DECODED = 32 * 1024 * 1024


def decode(raw, layers=1):
    import io
    for _ in range(layers):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(MAX_DECODED + 1)
        if len(raw) > MAX_DECODED:
            raise ValueError('Decoded input exceeds original byte budget')
    return raw


def atoms(geometry):
    """Retain every nonempty leaf, including point/line/zero-area remnants."""
    if geometry.is_empty:
        return
    if hasattr(geometry, 'geoms'):
        for child in geometry.geoms:
            yield from atoms(child)
    else:
        yield geometry


def split_result(geometry):
    candidates, residues = [], []
    for atom in atoms(geometry):
        if atom.geom_type == 'Polygon' and atom.area > 0:
            candidates.append(atom)
        else:
            residues.append(atom)
    return candidates, residues


def bad_record(identity, geometry, reason, input_path):
    bounds = list(geometry.bounds)
    # Unknown/nonfinite bounds block the whole declared domain, not zero tiles.
    bounded = len(bounds) == 4 and all(math.isfinite(x) for x in bounds)
    coordinates = get_coordinates(geometry, include_z=geometry.has_z)
    finite = all(math.isfinite(x) for coordinate in coordinates for x in coordinate)
    return {'id': identity, 'input_path': input_path, 'reason': reason,
            'bounds': bounds if bounded else None,
            'unchecked_bounds': bounds if bounded and finite else list(DOMAIN),
            'source_extent_status': 'finite-bounds' if bounded and finite else 'unknown-nonfinite-extent',
            'geometry_sha256': hashlib.sha256(geometry.wkb).hexdigest(),
            'geometry_hash_kind': 'diagnostic-shapely-wkb-original-source-pinned-separately'}


def load_inputs(repo, commit, water_root, water_commit):
    raw = subprocess.check_output(['git', '-C', str(repo), 'show', commit + ':data/world-index.json'])
    baseline = Baseline(repo, commit, [descriptor('data/world-index.json', raw)])
    pins = dict(baseline.pins)

    def read(path):
        value = baseline.read(path)
        pins[path] = descriptor(path, value)
        return value

    hierarchy = json.loads(read('data/hierarchy.json'))
    grid = read('data/canonical-grid/manifest.json')
    release_pointer = json.loads(read('data/geographic-releases/current-manifest.json'))
    release_raw = read('data/geographic-releases/' + release_pointer['path'])
    if hashlib.sha256(release_raw).hexdigest() != release_pointer['sha256']:
        raise ValueError('Original release index fails its whole-file pointer')
    release_index = json.loads(decode(release_raw))
    receipt = json.loads(decode(read(LAND_ROOT + 'manifest.json.gz')))
    land_source = next(s for s in receipt['sources'] if s['path'] == 'natural-earth-land.geojson.gz')
    retained_land = decode(read(LAND_ROOT + 'natural-earth-land.geojson.gz.gz'))
    land_raw = decode(retained_land)
    if (hashlib.sha256(retained_land).hexdigest() != land_source['retained_sha256']
            or hashlib.sha256(land_raw).hexdigest() != land_source['original_sha256']):
        raise ValueError('Physical land does not match the unchanged original source receipt')
    land, land_metadata, invalid_land = [], [], []
    for i, feature in enumerate(json.loads(land_raw)['features']):
        g = shape(feature['geometry'])
        if g.is_empty or not g.is_valid or g.geom_type not in ('Polygon', 'MultiPolygon'):
            invalid_land.append(bad_record('land-reference:' + str(i), g,
                                           explain_validity(g), LAND_ROOT + 'natural-earth-land.geojson.gz.gz'))
        else:
            land.append(g)
            land_metadata.append({'id': 'land-reference:' + str(i), 'original_feature_index': i,
                                  'input_path': LAND_ROOT + 'natural-earth-land.geojson.gz.gz'})
    locations, metadata, invalid_locations, seen = [], [], [], set()
    for part in json.loads(raw)['parts']:
        path = 'data/' + part
        for feature in json.loads(read(path))['features']:
            identity = feature.get('id') or feature['properties']['id']
            if not isinstance(identity, str) or not identity or identity in seen:
                raise ValueError('Missing or duplicate stable location ID')
            seen.add(identity)
            g = shape(feature['geometry'])
            props = feature['properties']
            record = {'id': identity, 'name': props.get('name'), 'input_path': path,
                      'source': props.get('metadata', {}).get('source_url'),
                      'reference_year': props.get('metadata', {}).get('reference_year')}
            if g.is_empty or not g.is_valid or g.geom_type not in ('Polygon', 'MultiPolygon'):
                invalid_locations.append(bad_record(identity, g, explain_validity(g), path))
            else:
                locations.append(g)
                metadata.append(record)
    water, water_metadata, invalid_water = [], [], []
    receipt_path = water_root + '/receipt.json'
    water_receipt_raw = subprocess.check_output(['git', '-C', str(repo), 'show', water_commit + ':' + receipt_path])
    water_baseline = Baseline(repo, water_commit, [descriptor(receipt_path, water_receipt_raw)])
    water_source = json.loads(water_receipt_raw)
    water_path = water_root + '/natural-earth-lakes.geojson.gz'
    encoded_water = water_baseline.read(water_path)
    water_raw = decode(encoded_water)
    if (hashlib.sha256(encoded_water).hexdigest() != water_source['retained_sha256']
            or hashlib.sha256(water_raw).hexdigest() != water_source['original_sha256']):
        raise ValueError('Water diagnostics do not match the original source receipt')
    for i, feature in enumerate(json.loads(water_raw)['features']):
        g = shape(feature['geometry'])
        identity = 'lake-reference:' + str(i)
        record = {'id': identity, 'name': feature['properties'].get('name')}
        if g.is_empty or not g.is_valid or g.geom_type not in ('Polygon', 'MultiPolygon'):
            invalid_water.append(bad_record(identity, g, explain_validity(g), water_path))
        else:
            water.append(g)
            water_metadata.append(record)
    return {'land': land, 'land_metadata': land_metadata,
            'locations': locations, 'location_metadata': metadata,
            'water': water, 'water_metadata': water_metadata,
            'invalid_land': invalid_land, 'invalid_locations': invalid_locations,
            'invalid_water': invalid_water, 'inputs': list(pins.values()),
            'water_inputs': [descriptor(receipt_path, water_receipt_raw), descriptor(water_path, encoded_water)],
            'land_source': land_source, 'water_source': water_source,
            'location_count': len(seen), 'hierarchy_type': type(hierarchy).__name__,
            'canonical_grid_sha256': hashlib.sha256(grid).hexdigest(),
            'release_index_sha256': hashlib.sha256(release_raw).hexdigest(),
            'release_ids': [r.get('id', r.get('release_id')) for r in release_index['releases']]}


def blocked_sources(bounds, invalid):
    tile = box(*bounds)
    return [record for record in invalid if box(*record['unchecked_bounds']).intersects(tile)]


class Detector:
    def __init__(self, inputs):
        self.inputs = inputs
        self.land_tree = STRtree(inputs['land'])
        self.land_boundaries = [g.boundary for g in inputs['land']]
        self.location_tree = STRtree(inputs['locations'])
        self.water_tree = STRtree(inputs['water'])

    def tile(self, bounds):
        data = self.inputs
        blocked = blocked_sources(bounds, data['invalid_land'] + data['invalid_locations'])
        if blocked:
            return {'status': 'unchecked', 'blocked_sources': blocked, 'bounds': list(bounds)}
        tile = box(*bounds)
        land_indices = [int(i) for i in self.land_tree.query(tile, predicate='intersects')]
        location_indices = [int(i) for i in self.location_tree.query(tile, predicate='intersects')]
        land_clips = [data['land'][i].intersection(tile) for i in land_indices]
        location_clips = [data['locations'][i].intersection(tile) for i in location_indices]
        physical = union_all(land_clips)
        occupied = union_all(location_clips)
        # Deliberately no water operand: it cannot suppress discovery or block a tile.
        missing = physical.difference(occupied)
        candidates, remnants = split_result(missing)
        residues = [{'stage': 'land-minus-locations', 'geometry': mapping(g)} for g in remnants]
        for stage, clips, indexes, records in [
                ('physical-land-clipping', land_clips, land_indices, data['land_metadata']),
                ('location-clipping', location_clips, location_indices, data['location_metadata'])]:
            for i, clip in enumerate(clips):
                for residue in split_result(clip)[1]:
                    residues.append({'stage': stage, 'clip_index': i, 'source': records[indexes[i]],
                                     'geometry': mapping(residue)})
        # Original shoreline survives even when it exactly coincides with a tile
        # edge. Boundaries created by clipping are never promoted to coastline.
        shore = union_all([self.land_boundaries[i].intersection(tile) for i in land_indices])
        return {'status': 'checked', 'bounds': list(bounds), 'candidates': candidates,
                'residues': residues, 'physical_shore': shore,
                'missing_geometry_sha256': hashlib.sha256(canonical_json(mapping(missing))).hexdigest(),
                'invalid_water_diagnostics': blocked_sources(bounds, data['invalid_water'])}

    def contacts(self, piece):
        """Exact source contacts, never proximity-based adjacency or ownership."""
        result = []
        for i in sorted(self.location_tree.query(piece, predicate='intersects')):
            intersection = piece.intersection(self.inputs['locations'][int(i)])
            kind = ('positive-area-intersection-flag' if intersection.area > 0 else
                    'positive-length-boundary' if intersection.length > 0 else 'point-only-ambiguous')
            result.append({**self.inputs['location_metadata'][int(i)], 'kind': kind,
                           'geometry': mapping(intersection)})
        return result

    def water_diagnostics(self, piece):
        result = []
        for i in sorted(self.water_tree.query(piece, predicate='intersects')):
            intersection = piece.intersection(self.inputs['water'][int(i)])
            result.append({**self.inputs['water_metadata'][int(i)], 'geometry': mapping(intersection),
                           'status': 'reference-overlap-unverified-water', 'planar_area': intersection.area})
        return result
