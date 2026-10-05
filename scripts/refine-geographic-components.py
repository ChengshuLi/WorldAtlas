"""Refine a whole-file pinned, immutable gap audit without altering its inputs."""
import argparse
import gzip
import io
import json
import math
import pathlib
import sys

import shapely

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.immutable import (Baseline, MAX_FILE_BYTES, canonical_json, descriptor,
                                deterministic_gzip, safe_path, sha256)
from geographic_components import VERSION, components

def decoded(raw):
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        result = stream.read(MAX_FILE_BYTES + 1)
    if len(result) > MAX_FILE_BYTES:
        raise ValueError('Decoded bundle exceeds 32 MiB')
    return result


def write_bundles(out, name, rows, collection=False):
    """Bounded deterministic outputs; originals remain referenced in place."""
    outputs, batch, budget = [], [], 0

    def flush():
        if not batch:
            return
        body = {'type': 'FeatureCollection', 'features': batch} if collection else batch
        raw = canonical_json(body)
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError('Output exceeds 32 MiB; do not truncate geometry')
        target = out / f'{name}-{len(outputs):03d}.json.gz'
        encoded = deterministic_gzip(raw)
        with target.open('xb') as stream:
            stream.write(encoded)
        outputs.append({**descriptor(str(target.relative_to(ROOT)), encoded),
                        'uncompressed_bytes': len(raw), 'uncompressed_sha256': sha256(raw)})

    for row in rows:
        size = len(canonical_json(row))
        if batch and budget + size > 16 * 1024 * 1024:
            flush()
            batch, budget = [], 0
        batch.append(row)
        budget += size
    flush()
    return outputs


def refine(commit, report_path, report_bytes, report_sha256, destination):
    report_pin = {'path': safe_path(report_path), 'bytes': report_bytes,
                  'sha256': report_sha256, 'hash_kind': 'file-bytes'}
    source = Baseline(ROOT, commit, [report_pin])
    original = json.loads(source.read(report_path))
    if original.get('version') != 'worldatlas-geographic-gap-audit-v1':
        raise ValueError('Unsupported audit version')
    if len(original['outputs']) > 64 or original['candidate_fragments'] > 250000:
        raise ValueError('Audit exceeds declared working budget')
    source = Baseline(ROOT, commit, [report_pin, *original['outputs']])
    # Check original evaluation inputs at their true evaluation commit. A current
    # comparison is an explicit compatibility result, never a relabeled vintage.
    evaluation = Baseline(ROOT, original['baseline_commit'], original['inputs'])
    water = original['water_reference']
    Baseline(ROOT, water['input_commit'], water['input_files'])
    compatibility = []
    for pin in original['inputs']:
        raw = source.read(pin['path'])
        compatibility.append({'path': pin['path'], 'expected_sha256': pin['sha256'],
                              'actual_sha256': sha256(raw), 'bytes': len(raw),
                              'same_bytes': len(raw) == pin['bytes'] and sha256(raw) == pin['sha256']})
    features, locations = [], []
    for pin in original['outputs']:
        raw = decoded(source.read(pin['path']))
        if len(raw) != pin['uncompressed_bytes'] or sha256(raw) != pin['uncompressed_sha256']:
            raise ValueError('Decoded input pin mismatch')
        collection = json.loads(raw)
        if collection.get('type') != 'FeatureCollection':
            raise ValueError('Expected original FeatureCollection')
        for f in collection['features']:
            features.append(f)
            locations.append({'id': f['id'], 'path': pin['path'],
                              'file_sha256': pin['sha256'], 'feature_sha256': sha256(canonical_json(f))})
    if len(features) != original['candidate_fragments']:
        raise ValueError('Incomplete fragment accounting')
    expected_unknown = sorted(f"{e['tile']}:{e['fragment']}" for e in original['measurement_errors'])
    actual_unknown = sorted(f['id'] for f in features if f['properties'].get('area_m2') is None)
    if actual_unknown != expected_unknown:
        raise ValueError('Unmeasured fragment accounting changed')
    records, contacts = components(features, original['tiles_blocked'], original['bounds'])
    # Destination is exclusive. No existing original or prior result is replaced.
    out = ROOT / safe_path(destination)
    if out.exists() or any(p.is_symlink() for p in [out, *out.parents]):
        raise ValueError('Output must be a new nonsymlink vintage')
    out.mkdir(parents=True)
    outputs = [*write_bundles(out, 'components', records, True),
               *write_bundles(out, 'contacts', contacts),
               *write_bundles(out, 'fragment-sources', sorted(locations, key=lambda f: f['id']))]
    result = {
        'version': VERSION, 'status': 'partial', 'input_commit': commit,
        'original_evaluation_commit': evaluation.commit, 'original_report': report_pin,
        'original_inputs': original['inputs'], 'original_candidate_bundles': original['outputs'],
        'original_water_reference': water, 'current_input_compatibility': compatibility,
        'bounds': original['bounds'], 'tiles_scanned': original['tiles_scanned'],
        'tiles_blocked': original['tiles_blocked'], 'measurement_errors': original['measurement_errors'],
        'fragment_count': len(features), 'component_count': len(records),
        'measured_fragment_count': len(features) - len(actual_unknown),
        'measured_fragment_area_sum_m2': math.fsum(f['properties']['area_m2'] for f in features
                                                 if f['properties']['area_m2'] is not None),
        'unmeasured_fragment_ids': actual_unknown,
        'contact_counts': {kind: sum(c['kind'] == kind for c in contacts) for kind in
                           ['shared-edge', 'point-only-ambiguous', 'positive-area-input-overlap']},
        'dateline_contact_count': sum(c['dateline'] for c in contacts),
        'outputs': outputs,
        'software': {'shapely': shapely.__version__, 'geos': shapely.geos_version_string},
        'limits': [
            'Connectivity is exact for the retained continuous polygons; no snapping or sliver cutoff.',
            'Point-only contacts do not themselves join components and remain explicitly ambiguous.',
            'Dateline components retain original coordinates as potentially disconnected planar MultiPolygon.',
            'Measured area is a sum of original measured fragments, not a newly certified physical area.',
            'Three blocked tiles and all original measurement failures remain unresolved.',
            'Nearby locations are inherited diagnostics, not certified neighbors or an administrative assignment.',
            'Independent detailed water classification and canonical integer-grid comparison remain outstanding.',
            *original['limits']]}
    raw = canonical_json(result)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('Report exceeds byte budget')
    with (out / 'report.json').open('xb') as stream:
        stream.write(raw)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--report-bytes', type=int, required=True)
    parser.add_argument('--report-sha256', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    result = refine(args.commit, args.report, args.report_bytes, args.report_sha256, args.out)
    print(json.dumps({k: result[k] for k in ['version', 'fragment_count', 'component_count',
                                           'contact_counts', 'dateline_contact_count']}))
