#!/usr/bin/env python3
"""Reproduce #399's exact IDs from pinned Git commits; write only a fresh owned output."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SPEC_PATH = OUT / 'correction-spec.json'
# Pin the complete policy/scope/source inventory. Editing a pin requires a separately reviewed vintage.
SPEC_SHA256 = '54a8b325983fc40bf3e09537e39d0f2e46ee6c617598957172f3f2a45b5f3554'
DEFAULT_OUTPUT = 'corrected-baseline-extract.json'
IDS = ['SHN-4865', 'atlas:coverage:BVT+00?']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], stderr=subprocess.PIPE)


def commit_exists(commit):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError(f'Invalid commit identity: {commit!r}')
    git('cat-file', '-e', f'{commit}^{{commit}}')


def read_commit_file(commit, path):
    if path.startswith('/') or '\\' in path or any(x in ('', '.', '..') for x in path.split('/')):
        raise ValueError(f'Unsafe repository path: {path!r}')
    return git('show', f'{commit}:{path}')


def descriptor(path, raw):
    item = {'path': path, 'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'file-bytes'}
    if path.endswith('.gz'):
        unpacked = gzip.decompress(raw)
        item.update(uncompressed_bytes=len(unpacked), uncompressed_sha256=sha(unpacked))
    return item


def verify_spec():
    raw = SPEC_PATH.read_bytes()
    if sha(raw) != SPEC_SHA256:
        raise ValueError(f'Correction spec pin mismatch: expected {SPEC_SHA256}, got {sha(raw)}')
    spec = json.loads(raw)
    if spec.get('version') != 1 or spec.get('correction_issue') != 643:
        raise ValueError('Unsupported correction spec identity')
    if spec.get('subjects') != IDS:
        raise ValueError('Exact subject scope changed')
    return spec


def validate_overrides(args, spec):
    expected_base = spec['baseline']['commit']
    expected_scope = spec['scope_snapshot']['commit']
    if args.baseline_commit and args.baseline_commit != expected_base:
        raise ValueError(f'Baseline override mismatch: expected {expected_base}')
    if args.scope_snapshot_commit and args.scope_snapshot_commit != expected_scope:
        raise ValueError(f'Scope snapshot override mismatch: expected {expected_scope}')
    commit_exists(expected_base)
    commit_exists(expected_scope)


def source_bytes(commit, descriptors):
    contents = {}
    for item in descriptors:
        raw = read_commit_file(commit, item['path'])
        if len(raw) != item['bytes'] or sha(raw) != item['sha256']:
            raise ValueError(f'Immutable input mismatch before output write: {item["path"]}')
        if item.get('hash_kind') != 'file-bytes':
            raise ValueError(f'Invalid whole-file descriptor: {item["path"]}')
        if 'uncompressed_sha256' in item:
            unpacked = gzip.decompress(raw)
            if len(unpacked) != item['uncompressed_bytes'] or sha(unpacked) != item['uncompressed_sha256']:
                raise ValueError(f'Compressed input expansion mismatch: {item["path"]}')
        contents[item['path']] = raw
    return contents


def load_json(contents, path):
    return json.loads(contents[path])


def load_gzip_json(contents, path):
    return json.loads(gzip.decompress(contents[path]))


def point_list(geometry):
    points = []
    def walk(value):
        if isinstance(value, (list, tuple)):
            if len(value) >= 2 and all(isinstance(x, (int, float)) for x in value[:2]):
                points.append(value[:2])
            else:
                for child in value:
                    walk(child)
    walk(geometry['coordinates'])
    if not points:
        raise ValueError('Subject has no coordinates')
    return points


def feature_summary(feature):
    props = feature['properties']
    geometry = feature['geometry']
    points = point_list(geometry)
    metadata = props.get('metadata', {})
    fields = ('source_name', 'source_id', 'source_url', 'license', 'reference_year',
              'administrative_level', 'location_basis', 'source_role', 'hierarchy_source',
              'parent_match', 'geographic_area_code', 'geographic_region_code', 'semantic_review')
    return {
        'id': props.get('id'),
        'name': props.get('name'),
        'parent_id': props.get('parent_id'),
        'reference_owner': props.get('reference_owner'),
        'geometry_type': geometry.get('type'),
        'geometry_sha256': sha(json.dumps(geometry, sort_keys=True, separators=(',', ':'),
                                          ensure_ascii=False).encode()),
        'vertices': len(points),
        'bounds': [min(x for x, y in points), min(y for x, y in points),
                   max(x for x, y in points), max(y for x, y in points)],
        'metadata': {key: metadata[key] for key in fields if key in metadata},
    }


def build(spec):
    base = spec['baseline']['commit']
    scope_commit = spec['scope_snapshot']['commit']
    # All pinned files, including every candidate part, are hashed before any destination is opened.
    baseline = source_bytes(base, spec['baseline']['source_files'])
    prior = source_bytes(scope_commit, spec['original_packet_snapshot']['files'])
    scope_path = spec['scope_snapshot']['path']
    if scope_path not in prior or len(prior[scope_path]) != spec['scope_snapshot']['bytes'] or \
            sha(prior[scope_path]) != spec['scope_snapshot']['sha256']:
        raise ValueError('Issue scope snapshot descriptor is not bound to the preserved packet snapshot')
    issue = json.loads(prior[scope_path])
    if issue.get('number') != spec['scope_snapshot']['issue_number']:
        raise ValueError('Scope snapshot issue number differs')
    blocks = [json.loads(match.group(1)) for match in
              re.finditer(r'```json\s*(\{[\s\S]*?\})\s*```', issue.get('body', ''))]
    scopes = [item for item in blocks if 'member_location_ids' in item]
    if len(scopes) != 1:
        raise ValueError('Expected exactly one immutable issue scope block')
    scope = scopes[0]
    ids = scope['member_location_ids']
    if ids != IDS or len(set(ids)) != len(IDS):
        raise ValueError('Immutable issue member list differs from corrected exact IDs')
    scope_sha = hashlib.sha256('\n'.join(ids).encode()).hexdigest()
    if scope_sha != spec['scope_snapshot']['scope_sha256'] or \
            scope.get('member_location_ids_sha256') != scope_sha:
        raise ValueError('Issue scope member-ID digest mismatch')
    if scope.get('release') != spec['scope_snapshot']['release'] or \
            scope.get('region_id') != spec['scope_snapshot']['region_id']:
        raise ValueError('Immutable issue scope release/region changed')
    if scope.get('original_scope_release') != spec['scope_snapshot']['original_scope_release']:
        raise ValueError('Archived original-scope release snapshot changed')
    if (scope.get('macro_certificate_sha256') != spec['scope_snapshot']['macro_certificate_sha256'] or
            scope.get('frozen_region_geometry_sha256') != spec['scope_snapshot']['frozen_region_geometry_sha256'] or
            scope.get('frozen_region_member_ids_sha256') != spec['scope_snapshot']['frozen_region_member_ids_sha256']):
        raise ValueError('Issue macro/frozen-scope pin mismatch')

    # Check every v5 release pin against the immutable baseline files before extraction.
    hierarchy = load_json(baseline, 'data/hierarchy.json')
    hierarchy_sha = sha(baseline['data/hierarchy.json'])
    grid = load_json(baseline, 'data/canonical-grid/manifest.json')
    certificate = load_json(baseline, 'data/macro-foundation/macro-certificate.json')
    release = spec['scope_snapshot']['release']
    if hierarchy_sha != release['hierarchy_sha256'] or grid.get('hierarchy_sha256') != hierarchy_sha:
        raise ValueError('Hierarchy release pin does not match immutable baseline')
    if grid.get('footprints_sha256') != release['footprints_sha256']:
        raise ValueError('Footprint release pin does not match immutable canonical-grid manifest')
    if sha(baseline['data/macro-foundation/macro-certificate.json']) != \
            spec['scope_snapshot']['macro_certificate_sha256']:
        raise ValueError('Macro certificate whole-file hash mismatch')
    if certificate.get('release') != release or certificate.get('regional_interiors_approved') is not False:
        raise ValueError('Macro certificate release or research-only status mismatch')

    handoffs = load_gzip_json(baseline, 'data/macro-foundation/regional-handoffs.json.gz')
    region = next((x for x in handoffs['regions'] if x.get('region_id') == scope['region_id']), None)
    if not region:
        raise ValueError('Pinned region absent from immutable handoffs')
    envelope = region['envelope']
    if envelope.get('geometry_sha256') != scope['frozen_region_geometry_sha256'] or \
            envelope.get('member_location_ids_sha256') != scope['frozen_region_member_ids_sha256']:
        raise ValueError('Frozen region envelope pins differ from issue snapshot')

    hierarchy_map = {x['id']: x for x in hierarchy}
    inventory = {x['id']: x for x in load_gzip_json(
        baseline, 'data/macro-foundation/current-membership-inventory.json.gz')}
    projection = load_gzip_json(baseline, 'data/macro-foundation/current-membership-projection.json.gz')
    projection_rows = {x['id']: x for x in projection['locations'] if x['id'] in IDS}
    if set(projection_rows) != set(IDS):
        raise ValueError('Scope IDs are missing from immutable membership projection')

    # Scan all part files as committed; never infer a file path from optional properties.part.
    occurrences = {identifier: [] for identifier in IDS}
    features = {}
    for path in spec['baseline']['geography_parts_scanned']:
        collection = load_json(baseline, path)
        for feature in collection.get('features', []):
            props = feature.get('properties', {})
            identifier = feature.get('id', props.get('id'))
            if identifier in occurrences:
                occurrences[identifier].append(path)
                features[identifier] = feature
    actual_files = {identifier: paths for identifier, paths in occurrences.items()}
    expected_files = spec['baseline']['expected_unique_containing_files']
    if actual_files != {identifier: expected_files[identifier] for identifier in IDS}:
        raise ValueError(f'Unique containing-file check failed: {actual_files}')

    locations = {identifier: feature_summary(features[identifier]) for identifier in IDS}
    legacy = json.loads(prior[spec['original_packet_snapshot']['legacy_extract_path']])
    if set(legacy.get('locations', {})) != set(IDS):
        raise ValueError('Legacy extract subject IDs do not match immutable issue scope')
    for identifier in IDS:
        # Preserve the prior factual/geographic inspection as a consistency check, not as source input.
        if (locations[identifier]['geometry_sha256'] != legacy['locations'][identifier]['geometry_sha256'] or
                locations[identifier]['parent_id'] != legacy['locations'][identifier]['parent_id'] or
                locations[identifier]['name'] != legacy['locations'][identifier]['name']):
            raise ValueError(f'Pinned baseline does not reproduce preserved location identity: {identifier}')

    chains = {}
    parent_ids = set()
    for identifier in IDS:
        chain = [features[identifier]['properties']]
        parent = features[identifier]['properties'].get('parent_id')
        seen = {identifier}
        while parent:
            if parent in seen or parent not in hierarchy_map:
                raise ValueError(f'Invalid immutable parent chain for {identifier}: {parent}')
            seen.add(parent)
            node = hierarchy_map[parent]
            chain.append(node)
            parent_ids.add(parent)
            parent = node.get('parent_id')
        chains[identifier] = [{'id': node.get('id'), 'name': node.get('name'),
                               'level': node.get('level'), 'parent_id': node.get('parent_id')}
                              for node in chain]
    if not parent_ids.issubset(inventory):
        raise ValueError('Immutable membership inventory lacks one or more source parents')
    group_ids = {x for x in parent_ids if hierarchy_map[x].get('level') in ('province', 'area', 'region')}
    group_members = {x: inventory[x].get('member_location_ids', []) for x in sorted(group_ids)}
    region_members = group_members.get(scope['region_id'])
    if region_members is None:
        raise ValueError('Region membership row missing from the derived hierarchy chain')

    target_paths = {identifier: paths[0] for identifier, paths in occurrences.items()}
    corrected_files = list(spec['baseline']['source_files'])
    result = {
        'version': 1,
        'issue': 643,
        'corrects_issue': 399,
        'baseline_commit': base,
        'scope_snapshot': {'issue': 399, 'commit': scope_commit, 'path': scope_path,
                           'sha256': spec['scope_snapshot']['sha256'],
                           'scope_member_ids_sha256': scope_sha},
        'vintage_policy': 'Geography inputs are read only from baseline_commit. The scope snapshot is a separately pinned issue-metadata artifact; no current-main geography refresh is represented here.',
        'region': {'id': region['region_id'], 'name': region['name'],
                   'continent_id': region['continent_id'], 'subcontinent_id': region['subcontinent_id'],
                   'frozen_geometry_sha256': envelope['geometry_sha256'],
                   'frozen_member_ids_sha256': envelope['member_location_ids_sha256'],
                   'location_count': envelope['locations']},
        'scope_location_ids': IDS,
        'locations': locations,
        'actual_containing_files': target_paths,
        'part_scan': {'method': 'Enumerate every ordinary data/geography/part-N.json at the pinned commit and inspect exact feature IDs; every requested ID must occur once.',
                      'parts_scanned': spec['baseline']['geography_parts_scanned'],
                      'occurrence_count_by_id': {identifier: len(occurrences[identifier]) for identifier in IDS}},
        'projection_rows': projection_rows,
        'complete_parent_chains': chains,
        'review_group_member_location_ids': group_members,
        'region_member_location_ids': region_members,
        'release_pins_verified': {'release': release, 'hierarchy_sha256': hierarchy_sha,
                                  'canonical_grid_manifest_sha256': sha(baseline['data/canonical-grid/manifest.json']),
                                  'macro_certificate_sha256': sha(baseline['data/macro-foundation/macro-certificate.json']),
                                  'macro_certificate_regional_interiors_approved': False},
        'baseline_files': corrected_files,
        'prior_extract': {'path': spec['original_packet_snapshot']['legacy_extract_path'],
                          'sha256': spec['original_packet_snapshot']['legacy_extract_sha256'],
                          'preserved_unchanged': True,
                          'known_fault': 'Prior baseline-extract.json listed data/geography/part-0.json even though both subject features occur exactly once in data/geography/part-28.json.'},
        'method': spec['method'],
        'limits': ['This is a provenance/containing-file correction only; it does not re-review geography or source accuracy.',
                   'A separately pinned issue-metadata snapshot provides the scope/release expectations; source geography is still from baseline_commit.'],
    }
    return json.dumps(result, indent=2, ensure_ascii=False) + '\n', result


def safe_destination(value):
    candidate = Path(value)
    if candidate.is_absolute():
        raise ValueError('Output path must be relative to the owned correction directory')
    resolved = (OUT / candidate).resolve(strict=False)
    if not resolved.is_relative_to(OUT.resolve()):
        raise ValueError('Output path escapes the declared owned directory')
    if candidate.parts and any(part in ('', '.', '..') for part in candidate.parts):
        raise ValueError('Output path contains unsafe components')
    return resolved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-commit', help='negative control; must equal pinned original commit')
    parser.add_argument('--scope-snapshot-commit', help='negative control; must equal pinned immutable scope snapshot')
    parser.add_argument('--output', default=DEFAULT_OUTPUT, help='new file inside this owned directory')
    parser.add_argument('--check', action='store_true', help='compare existing output; do not write')
    args = parser.parse_args()
    spec = verify_spec()
    validate_overrides(args, spec)
    target = safe_destination(args.output)
    if not args.check and target.exists():
        raise FileExistsError(f'Refusing to overwrite existing evidence: {target.name}')
    if target.is_symlink():
        raise ValueError('Evidence output may not be a symlink')
    payload, result = build(spec)
    if args.check:
        if not target.is_file() or target.read_bytes() != payload.encode():
            raise ValueError('Immutable extraction differs from existing output')
        status = 'passed'
    else:
        # Exclusive creation is the final operation; all baseline/release/scope checks precede this.
        with target.open('xb') as stream:
            stream.write(payload.encode())
            stream.flush()
            os.fsync(stream.fileno())
        status = 'written'
    print(json.dumps({'result': status, 'output': str(target.relative_to(OUT)),
                      'output_sha256': sha(payload.encode()), 'baseline_commit': spec['baseline']['commit'],
                      'scope_snapshot_commit': spec['scope_snapshot']['commit'],
                      'subjects': result['actual_containing_files']}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'ERROR: {error}', file=sys.stderr)
        raise SystemExit(1)
