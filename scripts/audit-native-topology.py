"""Read-only native planar validity accounting, separate from geographic truth."""
import argparse
import gzip
import io
import json
from pathlib import Path
import platform
import subprocess

import numpy
import shapely
from shapely.geometry import shape
from shapely.validation import explain_validity

from evidence.immutable import Baseline, MAX_FILE_BYTES, canonical_json, sha256


def controls():
    shell = [[0, 0], [8, 0], [8, 8], [0, 8], [0, 0]]
    hole = [[2, 2], [2, 6], [6, 6], [6, 2], [2, 2]]
    valid = shape({'type': 'Polygon', 'coordinates': [shell, hole]})
    crossed = shape({'type': 'Polygon', 'coordinates': [
        [[0, 0], [8, 8], [0, 8], [8, 0], [0, 0]]]})
    overlapping = shape({'type': 'MultiPolygon', 'coordinates': [[shell], [shell]]})
    assert valid.is_valid and not valid.is_empty and len(valid.interiors) == 1
    assert not crossed.is_valid and not overlapping.is_valid
    return {'positive_hole': explain_validity(valid),
            'negative_crossing': explain_validity(crossed),
            'negative_overlapping_parts': explain_validity(overlapping)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--inputs', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    if repo != Path(__file__).resolve().parent.parent:
        raise ValueError('Execute the actual declared repository')
    if shapely.__version__ != '2.1.2' or numpy.__version__ != '2.3.5':
        raise ValueError('Use the committed geographic preparation dependency versions')
    head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD']).decode().strip()
    execution = []
    for name in ['scripts/audit-native-topology.py', 'scripts/evidence/immutable.py', 'requirements.txt']:
        raw = (repo / name).read_bytes()
        committed = subprocess.check_output(['git', '-C', str(repo), 'show', head + ':' + name])
        if raw != committed:
            raise ValueError('Commit exact topology implementation before generation')
        execution.append({'path': name, 'bytes': len(raw), 'sha256': sha256(raw)})
    original_inventory = Path(args.inputs).read_bytes()
    if len(original_inventory) > MAX_FILE_BYTES:
        raise ValueError('Oversized inventory')
    inventory = json.loads(original_inventory)
    baseline = Baseline(repo, inventory['baseline_commit'],
                        [dict(f, hash_kind='file-bytes') for f in inventory['source_files']])

    def read(name):
        if name not in baseline.pins:
            raise ValueError('Unpinned original topology input')
        raw = baseline.read(name)
        if name.endswith('.gz'):
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw = stream.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError('Oversized decoded original')
        return json.loads(raw)

    passed_controls = controls()
    parts = read('data/world-index.json')['parts']
    if len(parts) != len(set(parts)):
        raise ValueError('Duplicate original world parts')
    manifest = read('data/canonical-grid/manifest.json')
    bounds = read('data/canonical-grid/' + manifest['bounds']['path'])
    owners = {r['id']: r for r in bounds}
    if len(owners) != len(bounds):
        raise ValueError('Duplicate original identities')
    seen, partition_results, failures = set(), [], []
    for part in parts:
        name = 'data/' + part
        collection = read(name)
        checked = valid = vertices = 0
        for feature in collection['features']:
            identity = feature['id']
            owner = owners.get(identity)
            if identity in seen or not owner or feature['properties']['parent_id'] != owner['province_id']:
                raise ValueError('Original identity/parent crosswalk differs')
            seen.add(identity)
            geometry = feature['geometry']
            if geometry['type'] not in ('Polygon', 'MultiPolygon'):
                raise ValueError('Unexpected original geometry type')
            polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
            vertices += sum(len(ring) for polygon in polygons for ring in polygon)
            native = shape(geometry)
            checked += 1
            if native.is_valid and not native.is_empty:
                valid += 1
            else:
                failures.append({'id': identity, 'index': owner['index'], 'path': name,
                                 'empty': native.is_empty, 'reason': explain_validity(native)})
        partition_results.append({'path': name, 'checked_features': checked,
                                  'valid_nonempty_features': valid, 'vertices': vertices})
    if seen != set(owners) or len(seen) != inventory['locations']:
        raise ValueError('Incomplete original native topology accounting')
    if sum(r['vertices'] for r in partition_results) != inventory['vertices']:
        raise ValueError('Original vertex accounting differs')
    report = {'version': 1, 'method': 'geos-native-planar-validity-v1',
              'evaluation_commit': head, 'baseline_commit': baseline.commit,
              'inputs_sha256': sha256(original_inventory), 'executed_sources': execution,
              'software': {'python': platform.python_version(), 'shapely': shapely.__version__,
                           'numpy': numpy.__version__, 'geos': shapely.geos_version_string},
              'checked_features': len(seen), 'unchecked_features': 0,
              'valid_nonempty_features': len(seen) - len(failures),
              'invalid_or_empty_features': len(failures), 'partitions': partition_results,
              'failures': failures, 'controls': passed_controls, 'scientific_approval': False,
              'limits': ['Planar validity of unchanged native lon/lat polygons; no repair or MakeValid.',
                         'No geodesic, antimeridian unwrap or projected geometry validity assertion.',
                         'Validity does not establish source authority, shared-border completeness, physical water or territorial truth.',
                         'No candidate installation, live operation or publication.']}
    raw = canonical_json(report)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('Oversized topology report')
    with Path(args.out).open('xb') as output:
        output.write(raw)
    print(json.dumps({'checked_features': len(seen), 'failures': len(failures), 'sha256': sha256(raw)}))


if __name__ == '__main__':
    main()
