"""Lossless envelopes for complete immutable audit inputs, never extracts.

This is an evidence transport stage. Existing scientific runs read original Git
blobs; no historical run is reinterpreted as consuming this later envelope.
The validator restores every byte and binds the entire roster to those reports
and original ordinary Git blobs. Hash equality establishes transport, not truth.
"""
import argparse
import gzip
import hashlib
import io
import json
import pathlib
import subprocess

from evidence.immutable import Baseline, canonical_json, descriptor, deterministic_gzip, safe_path

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = 'worldatlas-lossless-audit-input-envelope-v1'
LIMIT = 32 * 1024 * 1024
LAND_ROOT = 'data/macro-foundation/retained-inspections/retained-geographic-sources/namibia/'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def blob_id(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def restore_payload(encoded, row):
    if len(encoded) > LIMIT or len(encoded) != row['encoded']['bytes'] or digest(encoded) != row['encoded']['sha256']:
        raise ValueError('Lossless envelope encoded bytes changed')
    with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('Lossless original exceeds the existing decoded-file budget')
    original = row['original']
    if (len(raw) != original['bytes'] or digest(raw) != original['sha256']
            or blob_id(raw) != row['original_git_blob']):
        raise ValueError('Envelope does not restore the complete original bytes')
    return raw


def report_roster(report):
    rows = [(report['baseline_commit'], row) for row in report['inputs']]
    rows += [(report['water_commit'], row) for row in report['water_inputs']]
    keys = [(commit, safe_path(row['path'])) for commit, row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate original source in audit input roster')
    return {key: row for key, (_, row) in zip(keys, rows)}


def require_complete_roster(restored, baseline, water_commit, water_root):
    def read(path):
        return json.loads(restored[(baseline, path)])
    index = read('data/world-index.json')
    release = read('data/geographic-releases/current-manifest.json')
    expected = {(baseline, path) for path in [
        'data/world-index.json', 'data/hierarchy.json', 'data/canonical-grid/manifest.json',
        'data/geographic-releases/current-manifest.json',
        'data/geographic-releases/' + safe_path(release['path']),
        LAND_ROOT + 'manifest.json.gz', LAND_ROOT + 'natural-earth-land.geojson.gz.gz']}
    expected |= {(baseline, 'data/' + safe_path(part)) for part in index['parts']}
    if len(index['parts']) != len(set(index['parts'])):
        raise ValueError('Duplicate original world partition')
    expected |= {(water_commit, water_root + '/' + name)
                 for name in ['receipt.json', 'natural-earth-lakes.geojson.gz']}
    if set(restored) != expected:
        raise ValueError('Incomplete or expanded original world/land/water/release source roster')


def ordinary(path):
    name = safe_path(path)
    target = ROOT / name
    for ancestor in [target, *target.parents]:
        if ancestor.is_symlink():
            raise ValueError('Symlink in evidence input path')
        if ancestor == ROOT:
            break
    if not target.is_file() or target.stat().st_size > LIMIT:
        raise ValueError('Require an ordinary bounded evidence file')
    return target.read_bytes()


def verify_manifest(manifest_path, expected_sha256, report_path, report_sha256):
    encoded_manifest = ordinary(manifest_path)
    report_raw = ordinary(report_path)
    if digest(encoded_manifest) != expected_sha256 or digest(report_raw) != report_sha256:
        raise ValueError('Pinned envelope or audit report changed')
    manifest, report = json.loads(encoded_manifest), json.loads(report_raw)
    if manifest['version'] != VERSION:
        raise ValueError('Unknown lossless input-envelope method')
    roster = report_roster(report)
    rows = manifest['entries']
    keys = [(row['source_commit'], row['original']['path']) for row in rows]
    if len(keys) != len(set(keys)) or set(keys) != set(roster):
        raise ValueError('Envelope does not account for every exact audit input')
    restored, restored_bytes = {}, 0
    for row, key in zip(rows, keys):
        if row['original'] != roster[key]:
            raise ValueError('Envelope original pin differs from actual audit input')
        prefix = str(pathlib.PurePosixPath(manifest_path).parent) + '/'
        if not row['encoded']['path'].startswith(prefix):
            raise ValueError('Envelope payload outside its owned stage')
        raw = restore_payload(ordinary(row['encoded']['path']), row)
        commit, path = key
        baseline = Baseline(ROOT, commit, [descriptor(path, raw)])
        # Baseline independently verifies original ordinary-file type and every
        # restored byte against the immutable Git blob, not just this index.
        if blob_id(baseline.read(path)) != row['original_git_blob']:
            raise ValueError('Original Git blob identity changed')
        restored[key] = raw if key[1] in ('data/world-index.json', 'data/geographic-releases/current-manifest.json') else None
        restored_bytes += len(raw)
    require_complete_roster(restored, report['baseline_commit'], report['water_commit'], manifest['water_root'])
    return {'version': VERSION, 'status': 'complete-original-byte-restoration',
            'files_restored': len(restored), 'original_bytes': restored_bytes,
            'manifest_sha256': expected_sha256, 'audit_report_sha256': report_sha256,
            'limits': ['Transport only; original source authority, water truth and geographic approval are unverified.',
                       'The archived scientific run consumed original Git inputs; this is a later lossless evidence envelope.']}


def produce(report_path, output, water_root):
    report_raw = ordinary(report_path)
    report = json.loads(report_raw)
    roster = report_roster(report)
    out = pathlib.Path(output).resolve()
    if ROOT / 'coordination/engineering' not in out.parents or out.exists():
        raise ValueError('Use a new owned envelope vintage; never overwrite originals')
    for ancestor in [pathlib.Path(output), *pathlib.Path(output).parents]:
        if ancestor.is_symlink():
            raise ValueError('Output must not traverse a symlink')
    executed = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    code_paths = ['scripts/lossless_audit_inputs.py', 'scripts/evidence/immutable.py']
    code = []
    for path in code_paths:
        raw = subprocess.check_output(['git', 'show', executed + ':' + path], cwd=ROOT)
        if (ROOT / path).read_bytes() != raw:
            raise ValueError('Commit exact source-envelope code before generation')
        code.append(descriptor(path, raw))
    manifest = {'version': VERSION, 'executed_code_commit': executed, 'code_inputs': code,
                'audit_report': descriptor(report_path, report_raw), 'water_root': safe_path(water_root),
                'entries': [], 'limits': ['Lossless container, not a source extract or factual approval.']}
    restored = {}
    out.mkdir(parents=True, exist_ok=False)
    for i, (key, original) in enumerate(sorted(roster.items())):
        commit, path = key
        baseline = Baseline(ROOT, commit, [original])
        raw = baseline.read(path)
        encoded = deterministic_gzip(raw)
        target = out / f'original-{i:03d}.bytes.gz'
        with target.open('xb') as stream:
            stream.write(encoded)
        row = {'source_commit': commit, 'original': original, 'original_git_blob': blob_id(raw),
               'encoded': descriptor(str(target.relative_to(ROOT)), encoded)}
        assert restore_payload(encoded, row) == raw
        restored[key] = raw if key[1] in ('data/world-index.json', 'data/geographic-releases/current-manifest.json') else None
        manifest['entries'].append(row)
    require_complete_roster(restored, report['baseline_commit'], report['water_commit'], water_root)
    target = out / 'manifest.json'
    manifest_raw = canonical_json(manifest)
    with target.open('xb') as stream:
        stream.write(manifest_raw)
    return verify_manifest(str(target.relative_to(ROOT)), digest(manifest_raw), report_path, digest(report_raw))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--water-reference', required=True)
    args = parser.parse_args()
    result = produce(args.report, args.output, args.water_reference)
    print(json.dumps(result, sort_keys=True))
