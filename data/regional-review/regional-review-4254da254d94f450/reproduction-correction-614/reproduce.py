#!/usr/bin/env python3
"""Pinned, read-only reproduction of #485's exact baseline extracts."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import zlib

HERE = Path(__file__).resolve().parent
PACKET = HERE.parent
ROOT = HERE.parents[3]
SPEC_PATH = HERE / 'correction-spec.json'
SPEC_SHA256 = '49703a180bf3bd9561aae864890f44429a9be7bc65cdb76f3f0f7098f3f55f2d'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], stderr=subprocess.PIPE)


def read_commit(commit, path):
    if path.startswith('/') or '\\' in path or any(x in ('', '.', '..') for x in path.split('/')):
        raise ValueError(f'Unsafe repository path: {path!r}')
    return git('show', f'{commit}:{path}')


def verify_descriptor(commit, item):
    raw = read_commit(commit, item['path'])
    if len(raw) != item['bytes'] or sha(raw) != item['sha256']:
        raise ValueError(f'Pinned input mismatch: {item["path"]}')
    if item['path'].endswith('.gz') and 'uncompressed_sha256' in item:
        expanded = gzip.decompress(raw)
        if len(expanded) != item['uncompressed_bytes'] or sha(expanded) != item['uncompressed_sha256']:
            raise ValueError(f'Expanded input mismatch: {item["path"]}')
    return raw


def load_json(raw, label):
    try:
        return json.loads(raw)
    except Exception as error:
        raise ValueError(f'Invalid JSON in {label}: {error}') from error


def verify_spec():
    raw = SPEC_PATH.read_bytes()
    if sha(raw) != SPEC_SHA256:
        raise ValueError(f'Correction-spec pin mismatch: expected {SPEC_SHA256}, got {sha(raw)}')
    spec = load_json(raw, str(SPEC_PATH))
    if spec.get('version') != 1 or spec.get('correction_issue') != 614 or spec.get('parent_issue') != 485:
        raise ValueError('Unsupported correction identity')
    runtime = spec['runtime']
    if (sys.version.split()[0] != runtime['python_version'] or zlib.ZLIB_VERSION != runtime['zlib_build_version'] or
            zlib.ZLIB_RUNTIME_VERSION != runtime['zlib_runtime_version']):
        raise ValueError('Reproduction runtime differs from the pinned Python/zlib versions')
    return spec, sha(raw)


def validate_commit_overrides(args, spec):
    expected = spec['source_baseline']['commit']
    expected_scope = spec['original_artifact_snapshot']['commit']
    if args.baseline_commit and args.baseline_commit != expected:
        raise ValueError(f'Baseline override mismatch: expected {expected}')
    if args.artifact_snapshot_commit and args.artifact_snapshot_commit != expected_scope:
        raise ValueError(f'Artifact-snapshot override mismatch: expected {expected_scope}')
    for commit in (expected, expected_scope):
        if not re.fullmatch(r'[0-9a-f]{40}', commit):
            raise ValueError(f'Invalid immutable commit identity: {commit!r}')
        git('cat-file', '-e', f'{commit}^{{commit}}')


def canonical_gzip(raw):
    """RFC 1952: fixed MTIME/XFL/OS, raw DEFLATE, CRC32 and ISIZE."""
    compressor = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    deflated = compressor.compress(raw) + compressor.flush()
    header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff'
    trailer = struct.pack('<II', zlib.crc32(raw) & 0xffffffff, len(raw) & 0xffffffff)
    return header + deflated + trailer


def extract(spec):
    baseline_commit = spec['source_baseline']['commit']
    artifact_commit = spec['original_artifact_snapshot']['commit']

    # Verify the complete input manifest, including all geography parts and all retained
    # original packet-source bytes, before any destination directory/file is opened.
    baseline_raw = {}
    for item in spec['source_baseline']['files']:
        data = verify_descriptor(baseline_commit, item)
        if item['path'] in ('data/world-index.json', 'data/hierarchy.json',
                            'data/canonical-grid/manifest.json',
                            'data/macro-foundation/macro-certificate.json',
                            'data/macro-foundation/regional-handoffs.json.gz',
                            'data/macro-foundation/current-membership-inventory.json.gz'):
            baseline_raw[item['path']] = data
    original_raw = {}
    for item in spec['original_artifact_snapshot']['files']:
        original_raw[item['path']] = verify_descriptor(artifact_commit, item)
    for item in spec['original_artifact_snapshot']['source_files']:
        verify_descriptor(artifact_commit, {'path': spec['scope_snapshot']['owned_evidence_path'] + item['path'],
                                            **{k: item[k] for k in ('bytes', 'sha256')}})

    # Scope snapshot is a separately pinned packet artifact; it is not mislabeled as an
    # input generated at the earlier source baseline.
    scope_desc = spec['scope_snapshot']['scope_file']
    issue_desc = spec['scope_snapshot']['issue_metadata_file']
    scope = load_json(original_raw[scope_desc['path']], scope_desc['path'])
    issue = load_json(original_raw[issue_desc['path']], issue_desc['path'])
    ids = scope.get('member_location_ids', [])
    if (scope.get('batch_id') != spec['scope_snapshot']['batch_id'] or
            len(ids) != spec['scope_snapshot']['member_count'] or len(ids) != len(set(ids)) or
            len(ids) != scope.get('location_count') or len(ids) != 222):
        raise ValueError('Retained scope identity/count/member list mismatch')
    member_digest = hashlib.sha256('\n'.join(ids).encode()).hexdigest()
    if member_digest != spec['scope_snapshot']['member_ids_sha256'] or scope.get('member_location_ids_sha256') != member_digest:
        raise ValueError('Retained exact member-ID digest mismatch')
    if issue.get('number') != 485:
        raise ValueError('Pinned source packet issue metadata is not issue #485')
    blocks = []
    for match in re.finditer(r'```json\s*(\{[\s\S]*?\})\s*```', issue.get('body', '')):
        try:
            blocks.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            pass
    issue_scopes = [x for x in blocks if 'member_location_ids' in x]
    if len(issue_scopes) != 1 or issue_scopes[0].get('member_location_ids') != ids:
        raise ValueError('Pinned issue metadata scope does not match retained scope.json')
    if (scope.get('owned_evidence_path') != spec['scope_snapshot']['owned_evidence_path'] or
            scope.get('region_id') != spec['scope_snapshot']['region_id'] or
            scope.get('release') != spec['scope_snapshot']['release']):
        raise ValueError('Pinned region/owned-path/release scope mismatch')
    for key in ('macro_certificate_sha256', 'frozen_region_geometry_sha256', 'frozen_region_member_ids_sha256'):
        if scope.get(key) != spec['scope_snapshot'][key]:
            raise ValueError(f'Pinned scope field mismatch: {key}')

    hierarchy_raw = baseline_raw['data/hierarchy.json']
    grid_raw = baseline_raw['data/canonical-grid/manifest.json']
    cert_raw = baseline_raw['data/macro-foundation/macro-certificate.json']
    if sha(hierarchy_raw) != scope['release']['hierarchy_sha256']:
        raise ValueError('Pinned baseline hierarchy does not match assigned release')
    grid = load_json(grid_raw, 'canonical-grid manifest')
    if grid.get('hierarchy_sha256') != sha(hierarchy_raw) or grid.get('footprints_sha256') != scope['release']['footprints_sha256']:
        raise ValueError('Pinned canonical-grid release pins do not match assigned scope')
    if sha(cert_raw) != scope['macro_certificate_sha256']:
        raise ValueError('Pinned macro certificate hash mismatch')
    certificate = load_json(cert_raw, 'macro certificate')
    if certificate.get('release') != scope['release'] or certificate.get('regional_interiors_approved') is not False:
        raise ValueError('Macro certificate release or research-only status mismatch')
    handoffs = json.loads(gzip.decompress(baseline_raw['data/macro-foundation/regional-handoffs.json.gz']))
    region = next((x for x in handoffs['regions'] if x.get('region_id') == scope['region_id']), None)
    if not region:
        raise ValueError('Pinned region is absent from regional handoffs')
    envelope = region['envelope']
    if (envelope.get('geometry_sha256') != scope['frozen_region_geometry_sha256'] or
            envelope.get('member_location_ids_sha256') != scope['frozen_region_member_ids_sha256']):
        raise ValueError('Pinned frozen regional envelope mismatch')

    world = load_json(baseline_raw['data/world-index.json'], 'world index')
    expected_parts = ['data/' + p for p in world['parts']]
    if expected_parts != spec['source_baseline']['geography_parts_scanned']:
        raise ValueError('World-index part inventory differs from the pinned scan manifest')
    descriptor_map = {x['path']: x for x in spec['source_baseline']['files']}
    if set(expected_parts) - descriptor_map.keys():
        raise ValueError('One or more world-index parts lack pinned byte descriptors')

    occurrences = {identifier: [] for identifier in ids}
    features = {}
    for path in expected_parts:
        raw = verify_descriptor(baseline_commit, descriptor_map[path])
        collection = load_json(raw, path)
        for feature in collection.get('features', []):
            identifier = feature.get('properties', {}).get('id')
            if identifier in occurrences:
                occurrences[identifier].append(path)
                features.setdefault(identifier, feature)
    bad = {identifier: paths for identifier, paths in occurrences.items() if len(paths) != 1}
    if bad:
        raise ValueError(f'Exact scope IDs do not occur exactly once across all parts: {bad}')

    inventory = json.loads(gzip.decompress(baseline_raw['data/macro-foundation/current-membership-inventory.json.gz']))
    units = {row['id']: row for row in inventory}
    hierarchy = load_json(hierarchy_raw, 'hierarchy')
    hierarchy_by_id = {row['id']: row for row in hierarchy}
    rows = []
    for identifier in ids:
        feature = features[identifier]
        chain = [feature['properties']]
        parent = feature['properties'].get('parent_id')
        seen = {identifier}
        while parent:
            if parent in seen:
                raise ValueError(f'Parent cycle for {identifier}: {parent}')
            seen.add(parent)
            if parent not in units:
                raise ValueError(f'Missing parent membership record {parent} for {identifier}')
            unit = units[parent]
            definition = hierarchy_by_id.get(parent, {})
            if not definition:
                raise ValueError(f'Parent missing from pinned hierarchy: {parent}')
            if (definition.get('parent_id') != unit.get('parent_id') or
                    definition.get('level') != unit.get('level') or
                    definition.get('name') != unit.get('name')):
                raise ValueError(f'Parent identity differs between inventory and hierarchy: {parent}')
            chain.append({'id': unit['id'], 'name': unit['name'], 'level': unit['level'],
                          'parent_id': unit['parent_id'],
                          'member_location_ids': unit['member_location_ids'] if unit['level'] in ('province', 'area') else None,
                          'metadata': definition.get('metadata', {})})
            parent = unit['parent_id']
        rows.append({'feature': feature, 'parent_chain': chain})

    feature_collection = {'type': 'FeatureCollection', 'features': [row['feature'] for row in rows]}
    feature_json = (json.dumps(feature_collection, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    chain_json = (json.dumps([{'id': row['feature']['properties']['id'], 'parent_chain': row['parent_chain']}
                              for row in rows], ensure_ascii=False, separators=(',', ':')) + '\n').encode()

    receipt_path = spec['original_artifact_snapshot']['baseline_receipt_path']
    receipt = load_json(original_raw[receipt_path], receipt_path)
    manifest_path = spec['original_artifact_snapshot']['sources_manifest_path']
    manifest = load_json(original_raw[manifest_path], manifest_path)
    if manifest.get('issue') != 485:
        raise ValueError('Original source manifest issue identity mismatch')
    source_registry = {row['path']: row for row in manifest.get('files', [])}
    old_feature = spec['original_artifact_snapshot']['original_extracts']['feature_path']
    old_chain = spec['original_artifact_snapshot']['original_extracts']['chain_path']
    new_feature_gz = canonical_gzip(feature_json)
    new_chain_gz = canonical_gzip(chain_json)
    for key, old_path, raw_json, compressed in (
            ('feature_data', old_feature, feature_json, new_feature_gz),
            ('chain_data', old_chain, chain_json, new_chain_gz)):
        old_bytes = original_raw[old_path]
        old_receipt = receipt[key]
        registered = source_registry.get(old_path.removeprefix(spec['scope_snapshot']['owned_evidence_path']))
        if not registered:
            raise ValueError(f'Original sources manifest lacks {old_path}')
        if (len(old_bytes) != old_receipt['compressed_bytes'] or sha(old_bytes) != old_receipt['compressed_sha256'] or
                len(old_bytes) != registered['bytes'] or sha(old_bytes) != registered['sha256']):
            raise ValueError(f'Original extract receipt/manifest bytes disagree: {old_path}')
        original_uncompressed = gzip.decompress(old_bytes)
        if (original_uncompressed != raw_json or len(raw_json) != old_receipt['uncompressed_bytes'] or
                sha(raw_json) != old_receipt['uncompressed_sha256']):
            raise ValueError(f'Pinned baseline does not reproduce original uncompressed artifact: {old_path}')
        if gzip.decompress(compressed) != original_uncompressed:
            raise ValueError(f'Deterministic gzip changed uncompressed content: {old_path}')

    artifacts = {
        spec['new_artifacts']['feature_path']: new_feature_gz,
        spec['new_artifacts']['chain_path']: new_chain_gz,
    }
    output_manifest = {
        'version': 1, 'issue': 614, 'corrects_issue': 485,
        'source_baseline_commit': baseline_commit,
        'source_baseline_commit_date_utc': spec['source_baseline']['commit_date_utc'],
        'original_artifact_snapshot_commit_date_utc': spec['original_artifact_snapshot']['commit_date_utc'],
        'reproduction_runtime': spec['runtime'],
        'scope_snapshot': {'issue': 485, 'commit': artifact_commit,
                           'path': spec['scope_snapshot']['path'],
                           'sha256': spec['scope_snapshot']['scope_file']['sha256'],
                           'member_ids': len(ids), 'member_ids_sha256': member_digest},
        'region_release': scope['release'],
        'macro_certificate_sha256': scope['macro_certificate_sha256'],
        'frozen_region_geometry_sha256': scope['frozen_region_geometry_sha256'],
        'frozen_region_member_ids_sha256': scope['frozen_region_member_ids_sha256'],
        'part_scan': {'parts_scanned': len(expected_parts),
                      'method': spec['method']['part_scan'],
                      'occurrence_count_by_id': {identifier: len(occurrences[identifier]) for identifier in ids},
                      'actual_containing_files': {identifier: paths[0] for identifier, paths in occurrences.items()}},
        'rows': {'features': len(rows), 'parent_chains': len(rows)},
        'artifacts': {name: {'bytes': len(data), 'sha256': sha(data),
                             'uncompressed_bytes': len(gzip.decompress(data)),
                             'uncompressed_sha256': sha(gzip.decompress(data)),
                             'compression': spec['method']['gzip']}
                      for name, data in artifacts.items()},
        'original_extracts': {path: {'bytes': len(original_raw[path]), 'sha256': sha(original_raw[path]),
                                     'preserved_in_artifact_snapshot': True}
                             for path in (old_feature, old_chain)},
        'original_receipt_path': receipt_path,
        'original_sources_manifest_path': manifest_path,
        'correction_spec_sha256': SPEC_SHA256,
        'method': spec['method'],
        'limits': ['Reproduction/provenance correction only; source/geographic claims in #485 are unchanged.',
                   'No current-main geography refresh is represented; source and scope vintages are separately pinned.'],
    }
    artifacts[spec['new_artifacts']['manifest_path']] = (json.dumps(output_manifest, indent=2, ensure_ascii=False) + '\n').encode()
    return artifacts, output_manifest


def safe_output_dir(value):
    candidate = Path(value)
    if candidate.is_absolute() or any(part in ('..', '') for part in candidate.parts):
        raise ValueError('Output directory must be a safe relative path within this correction directory')
    resolved = (HERE / candidate).resolve(strict=False)
    if not resolved.is_relative_to(HERE.resolve()):
        raise ValueError('Output directory escapes the owned correction path')
    return resolved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-commit', help='negative control; must equal immutable source baseline')
    parser.add_argument('--artifact-snapshot-commit', help='negative control; must equal pinned original artifact snapshot')
    parser.add_argument('--output-dir', default='.', help='new output directory inside this correction directory')
    parser.add_argument('--check', action='store_true', help='verify exact existing output bytes without writing')
    args = parser.parse_args()
    spec, _ = verify_spec()
    validate_commit_overrides(args, spec)
    destination = safe_output_dir(args.output_dir)
    outputs, manifest = extract(spec)
    if args.check:
        if not destination.is_dir() or any(not (destination / name).is_file() or
                                           (destination / name).is_symlink() or
                                           (destination / name).read_bytes() != data
                                           for name, data in outputs.items()):
            raise ValueError('Pinned reproduction differs from existing output set')
        status = 'passed'
    else:
        if destination.exists() and (destination.is_symlink() or not destination.is_dir()):
            raise ValueError('Output destination is not an ordinary directory')
        if any((destination / name).exists() for name in outputs):
            raise FileExistsError('Refusing to overwrite existing deterministic output')
        # All source/scope/release/legacy checks are complete before creating a destination.
        destination.mkdir(parents=True, exist_ok=True)
        for name, data in outputs.items():
            target = destination / name
            if target.is_symlink():
                raise ValueError(f'Refusing symlink output: {name}')
            with target.open('xb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        status = 'written'
    print(json.dumps({'result': status, 'output_dir': str(destination.relative_to(HERE)),
                      'source_baseline_commit': spec['source_baseline']['commit'],
                      'artifact_snapshot_commit': spec['original_artifact_snapshot']['commit'],
                      'rows': manifest['rows'],
                      'output_sha256': {name: sha(data) for name, data in outputs.items()}}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'ERROR: {error}', file=sys.stderr)
        raise SystemExit(1)
