"""Complete immutable prepared-domain validation; no geography is written."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
CASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
import numpy
import pyproj
import shapely
from shapely.geometry import shape, mapping
from evidence import geometry
from evidence.immutable import Baseline, canonical_json, descriptor, deterministic_gzip, safe_path

PINNED = {'python': '3.12.14', 'numpy': '2.3.5', 'shapely': '2.1.2',
          'geos': '3.13.1', 'pyproj': '3.7.2'}
MAX = 32 * 1024 * 1024


def hash_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def read_git(commit, path):
    safe_path(path)
    entry = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-z', commit, '--', path]).decode().rstrip('\0')
    if not entry.startswith(('100644 ', '100755 ')) or entry[entry.find('\t'):] != '\t' + path:
        raise ValueError('Executed/config input must be an ordinary immutable Git file')
    oid = entry.split()[2]
    size = int(subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', '-s', oid]))
    if size > MAX:
        raise ValueError('Executed/config input exceeds ordinary bound')
    return subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', 'blob', oid])


def authenticate(code_commit):
    if not isinstance(code_commit, str) or not re.fullmatch('[a-f0-9]{40}', code_commit):
        raise ValueError('Execution requires an immutable lowercase 40-character commit')
    runtime = {'python': '.'.join(map(str, sys.version_info[:3])), 'numpy': numpy.__version__,
               'shapely': shapely.__version__, 'geos': shapely.geos_version_string,
               'pyproj': pyproj.__version__}
    if runtime != PINNED:
        raise ValueError('Pinned scientific runtime mismatch')
    config_path = str((CASE / 'config.json').relative_to(ROOT))
    raw = read_git(code_commit, config_path)
    if (CASE / 'config.json').read_bytes() != raw:
        raise ValueError('Actual config differs from frozen execution')
    config = json.loads(raw)
    pins = []
    for path in config['execution_code_paths']:
        local = ROOT / path
        if any(p.is_symlink() for p in [local, *local.parents]):
            raise ValueError('Executed code/config cannot have symlink ancestors')
        body = read_git(code_commit, path)
        if local.read_bytes() != body:
            raise ValueError('Actual execution bytes differ: ' + path)
        pins.append(descriptor(path, body))
    # Manual import is registered so the actual imported closure remains visible.
    spec = importlib.util.spec_from_file_location('prepared_domain_detector', ROOT / 'scripts/check-geographic-regression.py')
    detector = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = detector
    spec.loader.exec_module(detector)
    declared = set(config['execution_code_paths'])
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        local = Path(filename).resolve()
        if local.is_relative_to(ROOT) and local.suffix == '.py':
            path = str(local.relative_to(ROOT))
            if path not in declared or local.read_bytes() != read_git(code_commit, path):
                raise ValueError('Unbound actual project import: ' + path)
    return config, pins, runtime, detector


def checked_retained(pin):
    path = safe_path(pin['path'])
    if not path.startswith(str(CASE.relative_to(ROOT)) + '/'):
        raise ValueError('Retained input outside declared owned prefix')
    target = ROOT / path
    if any(p.is_symlink() for p in [target, *target.parents]):
        raise ValueError('Retained input cannot have symlink ancestors')
    raw = target.read_bytes()
    if len(raw) > MAX or len(raw) != pin['bytes'] or hash_bytes(raw) != pin['sha256']:
        raise ValueError('Retained input whole-byte mismatch')
    if target.name.endswith('.gz'):
        import gzip
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            decoded = stream.read(MAX + 1)
        if len(decoded) > MAX or len(decoded) != pin['uncompressed_bytes'] or hash_bytes(decoded) != pin['uncompressed_sha256']:
            raise ValueError('Retained input decoded-byte mismatch')
        return decoded
    return raw


def validate_feature(feature, path, ordinal):
    raw = feature['geometry']
    row = {'id': feature['id'], 'containing_file': path, 'feature_ordinal': ordinal,
           'original_feature_sha256': hash_bytes(canonical_json(feature)),
           'original_geometry_sha256': hash_bytes(canonical_json(raw)),
           'domain': geometry.PREPARED_DOMAIN}
    for name, operation in [('strict_default', geometry.canonical_land),
                            ('prepared', geometry.canonical_prepared_land)]:
        contacts = []
        try:
            if not isinstance(raw, dict):
                raise ValueError('Missing ordinary GeoJSON geometry')
            value = shape(raw)
            result = operation(value, seam_contacts=contacts) if name == 'prepared' else operation(value)
            row[name] = {'status': 'valid', 'canonical_geometry_sha256': hash_bytes(canonical_json(mapping(result)))}
            if name == 'prepared':
                row[name]['seam_contacts'] = contacts
        except (ValueError, TypeError, OverflowError, shapely.errors.ShapelyError) as error:
            row[name] = {'status': 'unsupported-or-invalid', 'exception': type(error).__name__,
                         'error': str(error), 'original_geometry': raw}
    return row


def run(code_commit, output):
    started = datetime.now(timezone.utc).isoformat()
    config, code_pins, runtime, detector = authenticate(code_commit)
    output = Path(output)
    if not output.is_absolute() or '..' in output.parts:
        raise ValueError('Output must be an absolute nonescaping owned-cache path')
    allowed = ROOT / '.cache' / '1293'
    if not output.is_relative_to(allowed) or output == allowed or output.exists():
        raise ValueError('Use an absent owned-cache run directory')
    if any(p.is_symlink() for p in [output, *output.parents]):
        raise ValueError('Output cannot have symlink ancestors')
    baseline = Baseline(ROOT, config['input_commit'], config['snapshot_files'] + config['source_files'])
    fji = checked_retained(config['retained_fji'])
    for pin in config['complete_diagnosis_files']:
        checked_retained(pin)
    index = json.loads(baseline.read('data/world-index.json'))
    expected_paths = {'data/world-index.json', *['data/' + p for p in index['parts']]}
    if not expected_paths.issubset({p['path'] for p in config['snapshot_files']}):
        raise ValueError('Incomplete pinned part closure')
    pointer = json.loads(baseline.read('data/geographic-releases/current-manifest.json'))
    pointed = pointer['path'] if pointer['path'].startswith('data/') else 'data/geographic-releases/' + pointer['path']
    if hash_bytes(baseline.read(pointed)) != pointer['sha256']:
        raise ValueError('Original release pointer mismatch')
    # Authenticate full source bodies and exact predecessor-feature ordinals.
    lineage = json.loads((CASE / 'diagnosis/complete-source-predecessor-lineage.json').read_bytes())
    source_rows = []
    source_payloads = {'gb:FJI:ADM2': json.loads(fji)['features'],
                      'gb:RUS:ADM2': json.loads(baseline.read(config['source_files'][1]['path']))['features']}
    for row in lineage['matches']:
        original = source_payloads[row['original_source_key']][row['source_ordinal']]
        if canonical_json(original) != canonical_json(row['whole_original_feature']):
            raise ValueError('Full original source feature mismatch')
        contacts = []
        try:
            geometry.canonical_prepared_land(shape(original['geometry']), seam_contacts=contacts)
            status = {'status': 'prepared-representation-valid', 'seam_contacts': contacts}
        except (ValueError, shapely.errors.ShapelyError) as error:
            status = {'status': 'unsupported-original-source', 'exception': type(error).__name__, 'error': str(error)}
        source_rows.append({'id': row['current_id'], 'source_geometry_sha256': row['source_geometry_sha256'],
                            'original_members': row['source_members'], **status})
    del source_payloads
    # All input/code/runtime/source authentication precedes any scientific output.
    output.mkdir(parents=True)
    rows, failures, seen = [], [], set()
    begin = time.monotonic()
    file_pins = {p['path']: p for p in config['snapshot_files']}
    for part in index['parts']:
        path = 'data/' + part
        collection = json.loads(baseline.read(path))
        if collection.get('type') != 'FeatureCollection' or not isinstance(collection.get('features'), list):
            raise ValueError('Malformed complete feature collection')
        for ordinal, feature in enumerate(collection['features']):
            if not isinstance(feature, dict) or feature.get('type') != 'Feature' or 'geometry' not in feature:
                raise ValueError('Malformed complete feature wrapper')
            identity = feature.get('id')
            if not isinstance(identity, str) or not identity or identity in seen:
                raise ValueError('Duplicate or missing complete inventory identity')
            seen.add(identity)
            row = validate_feature(feature, path, ordinal)
            if row['strict_default']['status'] != 'valid':
                failures.append(identity)
            rows.append(row)
        print(json.dumps({'processed_features': len(rows), 'complete_part': path}), flush=True)
    if len(rows) != config['expected_features'] or sorted(failures) != config['expected_default_failures']:
        raise ValueError('Full inventory/default failure closure disagreement')
    prepared_failures = sorted(row['id'] for row in rows if row['prepared']['status'] != 'valid')
    rows.sort(key=lambda r: r['id'])
    value = {'kind': 'Complete immutable current-world method validation', 'input_commit': config['input_commit'],
             'domain': geometry.PREPARED_DOMAIN, 'feature_count': len(rows), 'strict_default_failure_ids': sorted(failures),
             'prepared_failure_ids': prepared_failures, 'source_predecessor_observations': source_rows,
             'containing_file_pins': config['snapshot_files'],
             'limits': ['No stored location geometry changed. Strict source defaults and original unsupported evidence remain explicit.',
                        'Prepared seam validity is representation validation only; no physical-water, authority, ownership, original-cause, repair or deployment approval.']}
    shards = []
    for ordinal, start in enumerate(range(0, len(rows), 10000)):
        selected = rows[start:start + 10000]
        raw = canonical_json({'domain': geometry.PREPARED_DOMAIN, 'rows': selected})
        if len(raw) > MAX:
            raise ValueError('Complete row shard exceeds ordinary decoded bound')
        encoded = deterministic_gzip(raw)
        name = f'features-{ordinal:03d}.json.gz'
        (output / name).write_bytes(encoded)
        pin = descriptor(name, encoded)
        pin.update(uncompressed_bytes=len(raw), uncompressed_sha256=hash_bytes(raw),
                   rows=len(selected), first_id=selected[0]['id'], last_id=selected[-1]['id'])
        shards.append(pin)
    value['complete_row_shards'] = shards
    raw = canonical_json(value)
    (output / 'complete-world-index.json').write_bytes(raw)
    scientific_hash = hash_bytes(raw)
    report = {'code_commit': code_commit, 'input_commit': config['input_commit'], 'started_utc': started,
              'finished_utc': datetime.now(timezone.utc).isoformat(), 'elapsed_seconds': time.monotonic() - begin,
              'runtime': runtime, 'execution_code': code_pins, 'input_files': config['snapshot_files'] + config['source_files'],
              'retained_fji': config['retained_fji'], 'domain': geometry.PREPARED_DOMAIN,
              'feature_count': len(rows), 'strict_default_failures': len(failures), 'prepared_failures': len(prepared_failures),
              'scientific_sha256': scientific_hash, 'outputs': [descriptor('complete-world-index.json', raw), *shards],
              'complete_command': sys.argv, 'outcome': 'failed' if prepared_failures else 'passed'}
    (output / 'report.json').write_bytes(canonical_json(report))
    print(json.dumps({k: report[k] for k in ['outcome', 'feature_count', 'strict_default_failures', 'prepared_failures', 'scientific_sha256']}), flush=True)
    if prepared_failures:
        raise ValueError('Complete prepared validation retains unresolved geometry failures')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code-commit', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    run(args.code_commit, args.out)
