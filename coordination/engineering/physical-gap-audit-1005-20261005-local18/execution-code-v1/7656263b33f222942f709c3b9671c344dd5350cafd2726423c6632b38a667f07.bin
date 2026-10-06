"""Write a new immutable complete-domain land-before-water audit vintage."""
import argparse
import hashlib
import json
import math
import pathlib
import subprocess
import sys

import shapely
from shapely.geometry import mapping

from evidence.geometry import METHOD, land_area_m2
from evidence.immutable import canonical_json, descriptor, deterministic_gzip
from physical_gap_audit import DOMAIN, VERSION, Detector, load_inputs

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Bundles:
    def __init__(self, out, prefix):
        self.out, self.prefix = out, prefix
        self.features, self.size, self.outputs = [], 0, []

    def append(self, feature):
        size = len(canonical_json(feature))
        if size > 32 * 1024 * 1024:
            raise ValueError('A complete feature exceeds the existing byte budget; preserve inputs and partition explicitly')
        if self.features and self.size + size > 8 * 1024 * 1024:
            self.flush()
        self.features.append(feature)
        self.size += size

    def flush(self):
        if not self.features:
            return
        raw = canonical_json({'type': 'FeatureCollection', 'features': self.features})
        if len(raw) > 32 * 1024 * 1024:
            raise ValueError('Complete bundle exceeds byte budget')
        encoded = deterministic_gzip(raw)
        target = self.out / f'{self.prefix}-{len(self.outputs):03d}.geojson.gz'
        with target.open('xb') as stream:
            stream.write(encoded)
        self.outputs.append({**descriptor(str(target.relative_to(ROOT)), encoded),
                             'uncompressed_bytes': len(raw),
                             'uncompressed_sha256': hashlib.sha256(raw).hexdigest()})
        self.features, self.size = [], 0


def tiles(bounds, size):
    west, south, east, north = bounds
    y = south
    while y < north:
        x = west
        while x < east:
            yield (x, y, min(east, x + size), min(north, y + size))
            x += size
        y += size


def run(args):
    if not math.isfinite(args.tile_degrees) or not 0.25 <= args.tile_degrees <= 10:
        raise ValueError('Tile size must be 0.25..10 degrees')
    out = pathlib.Path(args.output).resolve()
    if ROOT / 'coordination/engineering' not in out.parents or out.exists():
        raise ValueError('Use a new owned engineering output vintage')
    for parent in [pathlib.Path(args.output), *pathlib.Path(args.output).parents]:
        if parent.is_symlink():
            raise ValueError('Output must not traverse a symlink')
    executed = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    code_paths = ['scripts/audit-physical-gaps.py', 'scripts/physical_gap_audit.py',
                  'scripts/evidence/immutable.py', 'scripts/evidence/geometry.py', 'scripts/ellipsoidal_area.py']
    code = []
    for path in code_paths:
        original = subprocess.check_output(['git', 'show', executed + ':' + path], cwd=ROOT)
        if (ROOT / path).read_bytes() != original:
            raise ValueError('Commit exact executed code before generating evidence: ' + path)
        code.append(descriptor(path, original))
    data = load_inputs(ROOT, args.commit, args.water_reference, args.water_commit)
    detector = Detector(data)
    out.mkdir(parents=True, exist_ok=False)
    candidates, residues = Bundles(out, 'candidates'), Bundles(out, 'residues')
    report = {'version': VERSION, 'baseline_commit': args.commit, 'executed_code_commit': executed,
              'code_inputs': code, 'inputs': data['inputs'], 'water_commit': args.water_commit,
              'water_inputs': data['water_inputs'], 'physical_reference': data['land_source'],
              'water_reference': data['water_source'], 'bounds': list(DOMAIN),
              'tile_degrees': args.tile_degrees, 'locations': data['location_count'],
              'canonical_grid_sha256': data['canonical_grid_sha256'],
              'release_index_sha256': data['release_index_sha256'], 'release_ids': data['release_ids'],
              'invalid_land': data['invalid_land'], 'invalid_locations': data['invalid_locations'],
              'invalid_water_reference': data['invalid_water'], 'method': METHOD,
              'software': {'python': sys.version.split()[0], 'shapely': shapely.__version__,
                           'geos': shapely.geos_version_string},
              'tiles': [], 'candidate_fragments': 0, 'residues': 0, 'measurement_errors': [],
              'limits': ['Natural Earth 1:10m physical reference is not a complete island or fine-shoreline inventory.',
                         'Modern water reference is diagnostic only, not year-specific water truth or owner approval.',
                         'Invalid water never suppresses discovery; invalid land/location bounds remain unchecked.',
                         'Original geographic bytes/IDs/releases are unchanged; no repair, affiliation or deployment.',
                         'Point/line and clipping remnants are retained separately, never silently filtered.',
                         'Tile fragment counts are not connected-component counts; original/new crosswalk follows separately.',
                         'Coordinates use the original planar lon/lat set; exact contacts are diagnostic, not source authority.']}
    measured = []
    for number, bounds in enumerate(tiles(DOMAIN, args.tile_degrees)):
        try:
            result = detector.tile(bounds)
        except shapely.errors.GEOSException as error:
            report['tiles'].append({'id': number, 'bounds': list(bounds), 'status': 'unchecked',
                                    'reason': 'original-geometry-operation-failed', 'error': str(error)})
            continue
        row = {k: result[k] for k in ('status', 'bounds')}
        row['id'] = number
        if result['status'] == 'unchecked':
            row['blocked_sources'] = result['blocked_sources']
            report['tiles'].append(row)
            continue
        row.update({'candidate_fragments': len(result['candidates']), 'residues': len(result['residues']),
                    'missing_geometry_sha256': result['missing_geometry_sha256'],
                    'invalid_water_diagnostics': result['invalid_water_diagnostics']})
        for j, piece in enumerate(result['candidates']):
            geometry = mapping(piece)
            digest = hashlib.sha256(canonical_json(geometry)).hexdigest()
            identity = f'physical-gap:{number}:{j}:{digest}'
            try:
                area = land_area_m2(piece)
                if not math.isfinite(area) or area <= 0:
                    raise ValueError('Nonpositive/nonfinite measurement of positive planar candidate')
                measured.append(area)
            except (ValueError, OverflowError) as error:
                area = None
                report['measurement_errors'].append({'fragment': identity, 'error': str(error),
                                                      'original_planar_area': piece.area})
            candidates.append({'type': 'Feature', 'id': identity, 'geometry': geometry,
                               'properties': {'status': 'uncovered-physical-reference-candidate',
                                              'tile': list(bounds), 'area_m2': area,
                                              'original_planar_area': piece.area,
                                              'touches_reference_shore': piece.intersects(result['physical_shore']),
                                              'exact_location_contacts': detector.contacts(piece),
                                              'water_diagnostics': detector.water_diagnostics(piece),
                                              'water_status': 'unverified', 'administrative_assignment': None}})
        for j, residue in enumerate(result['residues']):
            residues.append({'type': 'Feature', 'id': f'physical-residue:{number}:{j}',
                             'geometry': residue['geometry'],
                             'properties': {**{k: v for k, v in residue.items() if k != 'geometry'},
                                            'tile': list(bounds), 'status': 'retained-nonpolygon-residue'}})
        report['candidate_fragments'] += len(result['candidates'])
        report['residues'] += len(result['residues'])
        report['tiles'].append(row)
        if number % 50 == 0:
            print(json.dumps({'tile': number, 'candidates': report['candidate_fragments'],
                              'residues': report['residues']}), flush=True)
    candidates.flush()
    residues.flush()
    report['outputs'] = candidates.outputs
    report['residue_outputs'] = residues.outputs
    report['measured_candidate_area_m2'] = math.fsum(measured)
    report['tiles_checked'] = sum(r['status'] == 'checked' for r in report['tiles'])
    report['tiles_unchecked'] = sum(r['status'] == 'unchecked' for r in report['tiles'])
    report['status'] = 'declared-domain-detection-complete' if not report['tiles_unchecked'] else 'partial-unknown-domain'
    with (out / 'report.json').open('xb') as stream:
        stream.write(canonical_json(report))
    print(json.dumps({k: report[k] for k in ('status', 'tiles_checked', 'tiles_unchecked',
                                            'candidate_fragments', 'residues')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--water-reference', required=True)
    parser.add_argument('--water-commit', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--tile-degrees', type=float, default=5)
    run(parser.parse_args())
