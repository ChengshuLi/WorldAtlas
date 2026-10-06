"""Fail-closed reuse decisions for immutable physical-gap audit snapshots.

This module is deliberately a decision layer, not a detector. A caller must
construct each snapshot from the complete immutable source closure and record
the exact ordered geometry operands supplied to each tile computation. The
module verifies every declared file byte before allowing reuse. It never uses
bounding boxes, source revision labels, or a caller-provided ``verified`` flag
as proof that a tile is unchanged.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import zlib
from typing import Mapping

from evidence.immutable import MAX_FILE_BYTES, canonical_json, safe_path

VERSION = 'worldatlas-physical-gap-successor-reuse-v1'
HEX256 = re.compile(r'^[a-f0-9]{64}$')
HEX40 = re.compile(r'^[a-f0-9]{40}$')


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _exact_keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'{label} has an unknown or missing field')


def _descriptor(row, label):
    _exact_keys(row, ('path', 'bytes', 'sha256', 'hash_kind'), label)
    path = safe_path(row['path'])
    if (row['hash_kind'] != 'file-bytes' or type(row['bytes']) is not int
            or row['bytes'] < 0 or row['bytes'] > MAX_FILE_BYTES
            or not isinstance(row['sha256'], str) or not HEX256.fullmatch(row['sha256'])):
        raise ValueError(f'{label} is not a complete whole-file descriptor')
    return path


def _read_verified(files: Mapping[str, bytes], commit, row, label, allowed_commits):
    if not isinstance(commit, str) or commit not in allowed_commits:
        raise ValueError(f'{label} is not bound to a pinned source/execution commit')
    path = _descriptor(row, label)
    key = commit + ':' + path
    raw = files.get(key)
    if not isinstance(raw, bytes):
        raise ValueError(f'{label} has no retained ordinary-byte payload: {key}')
    if len(raw) > MAX_FILE_BYTES or len(raw) != row['bytes'] or _sha(raw) != row['sha256']:
        raise ValueError(f'{label} bytes do not match their immutable descriptor: {key}')
    return key


def decode_gzip_layers(encoded: bytes, layers: int) -> bytes:
    """Decode an exact stack of single-member gzip layers within file limits."""
    if type(layers) is not int or layers < 1 or layers > 3:
        raise ValueError('Gzip layer count must be an explicit integer from one through three')
    if not isinstance(encoded, bytes) or len(encoded) > MAX_FILE_BYTES:
        raise ValueError('Encoded source exceeds the existing per-file budget')
    raw = encoded
    for _ in range(layers):
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            decoded = decoder.decompress(raw, MAX_FILE_BYTES + 1)
            if len(decoded) > MAX_FILE_BYTES or decoder.unconsumed_tail:
                raise ValueError('Decoded source exceeds the existing per-file budget')
            decoded += decoder.flush(MAX_FILE_BYTES + 1 - len(decoded))
        except zlib.error as error:
            raise ValueError('Source bytes are not a valid gzip layer') from error
        if (len(decoded) > MAX_FILE_BYTES or not decoder.eof or decoder.unused_data
                or decoder.unconsumed_tail):
            raise ValueError('Gzip layer is truncated, has trailing bytes, or exceeds its decoded budget')
        raw = decoded
    return raw


def verify_decoded_relation(encoded_descriptor, encoded, decoded_descriptor, decoded, layers):
    """Verify retained encoded and decoded source bytes and their exact gzip relation."""
    _descriptor(encoded_descriptor, 'encoded source')
    _descriptor(decoded_descriptor, 'decoded source')
    if (len(encoded) != encoded_descriptor['bytes'] or _sha(encoded) != encoded_descriptor['sha256']
            or len(decoded) != decoded_descriptor['bytes'] or _sha(decoded) != decoded_descriptor['sha256']):
        raise ValueError('Encoded or decoded source bytes differ from their retained descriptors')
    if decode_gzip_layers(encoded, layers) != decoded:
        raise ValueError('Decoded source bytes do not equal the retained gzip-layer result')
    return {'encoded_bytes': len(encoded), 'encoded_sha256': _sha(encoded),
            'decoded_bytes': len(decoded), 'decoded_sha256': _sha(decoded), 'gzip_layers': layers}


def verify_snapshot(snapshot, files: Mapping[str, bytes], *, require_outputs=True):
    """Verify a complete typed snapshot and return its path-to-bytes mapping.

    Snapshot schema (all required): ``version``, ``snapshot_id`` (40-hex
    commit), ``source_commits`` (nonempty list of 40-hex commits), ``files``
    (the complete source/code/release/hierarchy/native-owner/output closure,
    each row binding a role and whole-file descriptor to a source commit),
    ``semantics`` (algorithm, parameters, software, domain and other global
    nonspatial inputs), and ``tiles``. Each tile has bounds, ordered
    ``query_order``, ordered ``members`` with stable IDs and exact per-member
    geometry-byte descriptors, ``status``/``unknowns``, and
    one or more complete output descriptors. File descriptors point to the
    exact bytes in ``files``.
    """
    _exact_keys(snapshot, ('version', 'snapshot_id', 'source_commits', 'files', 'semantics', 'provenance', 'tiles'), 'snapshot')
    if snapshot['version'] != VERSION or not HEX40.fullmatch(snapshot['snapshot_id']):
        raise ValueError('Unknown successor method or invalid immutable snapshot commit')
    commits = snapshot['source_commits']
    if (not isinstance(commits, list) or not commits
            or any(not isinstance(x, str) or not HEX40.fullmatch(x) for x in commits)
            or len(commits) != len(set(commits))):
        raise ValueError('Snapshot source commit closure is incomplete or duplicated')
    semantic_keys = ('algorithm', 'parameters', 'software', 'domain', 'land_input_policy',
                     'location_input_policy', 'invalid_input_policy', 'tile_query_policy', 'physical_union_policy')
    _exact_keys(snapshot['semantics'], semantic_keys, 'geometry computation semantics')
    object_keys = semantic_keys[1:3] + semantic_keys[4:]
    domain = snapshot['semantics']['domain']
    if (not isinstance(snapshot['semantics']['algorithm'], str) or not snapshot['semantics']['algorithm']
            or any(not isinstance(snapshot['semantics'][key], dict) for key in object_keys)
            or not isinstance(domain, list) or len(domain) != 4
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in domain)
            or domain[0] >= domain[2] or domain[1] >= domain[3]):
        raise ValueError('Snapshot lacks typed detector/software/domain computation semantics')
    _exact_keys(snapshot['provenance'], ('hierarchy', 'release', 'native_owner'), 'source provenance')
    if not isinstance(snapshot['files'], list) or not snapshot['files']:
        raise ValueError('Snapshot lacks its complete immutable file closure')
    allowed_commits = set(commits) | {snapshot['snapshot_id']}
    paths = []
    roles = []
    for row in snapshot['files']:
        _exact_keys(row, ('source_commit', 'role', 'file'), 'snapshot file binding')
        if not isinstance(row['role'], str) or not row['role']:
            raise ValueError('Snapshot file has no provenance role')
        roles.append(row['role'])
        paths.append(_read_verified(files, row['source_commit'], row['file'],
                                    'snapshot closure file', allowed_commits))
    if len(paths) != len(set(paths)) or set(files) != set(paths):
        raise ValueError('Snapshot payload inventory is duplicated, incomplete, or expanded')
    if len(roles) != len(set(roles)):
        raise ValueError('Snapshot provenance roles are duplicated')
    source_commits_bound = {row['source_commit'] for row in snapshot['files'] if row['role'].startswith('source:')}
    if source_commits_bound != set(commits):
        raise ValueError('Declared source commits do not exactly match source-file provenance bindings')
    if any(row['source_commit'] != snapshot['snapshot_id'] for row in snapshot['files']
           if row['role'].startswith('code:') or row['role'].startswith('tile-output:')):
        raise ValueError('Executed code and tile outputs must bind to the snapshot execution commit')
    mandatory = {'software', 'domain', 'hierarchy', 'release', 'native_owner', 'tile-roster'}
    if not mandatory.issubset(set(roles)) or not any(x.startswith('source:') for x in roles) or not any(x.startswith('code:') for x in roles):
        raise ValueError('Snapshot lacks source, code, software, domain, hierarchy, release, native-owner, or tile-roster pins')
    roster_rows = [row for row in snapshot['files'] if row['role'] == 'tile-roster']
    if len(roster_rows) != 1:
        raise ValueError('Snapshot tile roster must be pinned exactly once')
    roster_key = roster_rows[0]['source_commit'] + ':' + roster_rows[0]['file']['path']
    try:
        roster_ids = json.loads(files[roster_key])['tile_ids']
    except (KeyError, ValueError, TypeError) as error:
        raise ValueError('Snapshot tile roster is not valid JSON') from error
    if not isinstance(roster_ids, list) or any(not isinstance(x, str) or not x for x in roster_ids):
        raise ValueError('Snapshot tile roster is malformed')
    for key in ('hierarchy', 'release', 'native_owner'):
        binding = snapshot['provenance'][key]
        _exact_keys(binding, ('source_commit', 'file'), f'{key} provenance binding')
        binding_key = _read_verified(files, binding['source_commit'], binding['file'],
                                     f'{key} provenance bytes', allowed_commits)
        if binding_key not in paths:
            raise ValueError(f'{key} provenance bytes are absent from the complete closure')
        matches = [row for row in snapshot['files'] if row['role'] == key
                   and row['source_commit'] == binding['source_commit']
                   and row['file'] == binding['file']]
        if len(matches) != 1:
            raise ValueError(f'{key} provenance does not resolve to exactly one retained source file')
    if not isinstance(snapshot['tiles'], list) or not snapshot['tiles']:
        raise ValueError('Snapshot has no tile inventory')
    tile_ids = []
    for tile in snapshot['tiles']:
        _exact_keys(tile, ('tile_id', 'bounds', 'query_order', 'members', 'status', 'unknowns', 'outputs'), 'tile')
        tile_id = tile['tile_id']
        if not isinstance(tile_id, str) or not tile_id:
            raise ValueError('Tile lacks a stable identifier')
        tile_ids.append(tile_id)
        bounds = tile['bounds']
        if (not isinstance(bounds, list) or len(bounds) != 4
                or any(type(x) not in (int, float) or not math.isfinite(x) for x in bounds)
                or bounds[0] >= bounds[2] or bounds[1] >= bounds[3]):
            raise ValueError(f'Invalid tile bounds: {tile_id}')
        order, members = tile['query_order'], tile['members']
        query_groups = ('land', 'locations', 'invalid_land', 'invalid_locations', 'invalid_water', 'shorelines')
        _exact_keys(order, query_groups, f'{tile_id} layered query order')
        if any(not isinstance(order[k], list) or any(not isinstance(x, str) or not x for x in order[k])
               or len(order[k]) != len(set(order[k])) for k in query_groups):
            raise ValueError(f'Duplicate or malformed layered query order: {tile_id}')
        if not isinstance(members, list):
            raise ValueError(f'Malformed member inventory: {tile_id}')
        member_ids = {key: [] for key in query_groups}
        for member in members:
            _exact_keys(member, ('kind', 'id', 'source_commit', 'geometry_file', 'metadata_file'), 'query member')
            if member['kind'] not in query_groups or not isinstance(member['id'], str) or not member['id']:
                raise ValueError(f'Invalid exact query-member identifier: {tile_id}')
            geometry_key = _read_verified(files, member['source_commit'], member['geometry_file'],
                                          f'tile {tile_id} exact geometry operand', allowed_commits)
            metadata_key = _read_verified(files, member['source_commit'], member['metadata_file'],
                                          f'tile {tile_id} exact metadata operand', allowed_commits)
            if geometry_key not in paths or metadata_key not in paths:
                raise ValueError(f'Exact geometry operand is absent from the complete closure: {tile_id}')
            member_ids[member['kind']].append(member['id'])
        if any(member_ids[k] != order[k] for k in query_groups):
            raise ValueError(f'Layered query order does not exactly cover the geometry and metadata operands: {tile_id}')
        if tile['status'] not in ('checked', 'unchecked'):
            raise ValueError(f'Unknown tile status: {tile_id}')
        if not isinstance(tile['unknowns'], list):
            raise ValueError(f'Unknown inventory is malformed: {tile_id}')
        if tile['status'] == 'unchecked' and not tile['unknowns']:
            raise ValueError(f'Unchecked tile discarded its blocking/unknown cause: {tile_id}')
        if tile['status'] == 'checked' and tile['unknowns']:
            raise ValueError(f'Checked tile carries unaccounted blockers: {tile_id}')
        if not isinstance(tile['outputs'], list) or (require_outputs and not tile['outputs']):
            raise ValueError(f'Tile output bytes are not retained: {tile_id}')
        roles = []
        output_paths = []
        for output in tile['outputs']:
            roles.append(output.get('role') if isinstance(output, dict) else None)
            if not isinstance(output, dict) or set(output) != {'role', 'source_commit', 'file'}:
                raise ValueError(f'Malformed tile output descriptor: {tile_id}')
            if not isinstance(output['role'], str) or not output['role']:
                raise ValueError(f'Missing tile output role: {tile_id}')
            key = _read_verified(files, output['source_commit'], output['file'],
                                 f'tile {tile_id} output', allowed_commits)
            if key not in paths:
                raise ValueError(f'Tile output is absent from the complete closure: {tile_id}')
            output_paths.append(key)
        if len(roles) != len(set(roles)):
            raise ValueError(f'Duplicate tile output role: {tile_id}')
        if len(output_paths) != len(set(output_paths)):
            raise ValueError(f'Tile output roles alias the same retained bytes: {tile_id}')
        if require_outputs:
            expected = ({'blocked_sources'} if tile['status'] == 'unchecked' else
                        {'candidates', 'residues', 'physical_shore',
                         'missing_geometry_sha256', 'invalid_water_diagnostics'})
            if not expected.issubset(set(roles)):
                raise ValueError(f'Tile output closure omits required detector products: {tile_id}')
    if len(tile_ids) != len(set(tile_ids)) or tile_ids != roster_ids:
        raise ValueError('Duplicate tile identifier')
    return {key: files[key] for key in paths}


def _tile(snapshot, tile_id):
    matches = [row for row in snapshot['tiles'] if row['tile_id'] == tile_id]
    if len(matches) != 1:
        raise ValueError(f'Tile is missing or duplicated in snapshot: {tile_id}')
    return matches[0]


def _member_fingerprints(tile, verified_files):
    """Bind each ordered layered query ID to exact geometry and metadata bytes."""
    return [(member['kind'], member['id'],
             _sha(verified_files[member['source_commit'] + ':' + member['geometry_file']['path']]),
             _sha(verified_files[member['source_commit'] + ':' + member['metadata_file']['path']]))
            for member in tile['members']]


def _execution_fingerprints(snapshot):
    """Exact executable/runtime/domain files that can change detector behavior."""
    return sorted((row['role'], row['file']['path'], row['file']['bytes'], row['file']['sha256'])
                  for row in snapshot['files']
                  if row['role'].startswith('code:') or row['role'] in ('software', 'domain'))


def reuse_decision(original, successor, original_files, successor_files, tile_id,
                   force_recompute=()):
    """Return a reuse proof only when all exact tile operands and semantics match.

    Both complete closures are rehashed first. An unknown/unchecked tile is
    reusable only when its exact unknown records are unchanged; it remains
    unknown in the result. ``force_recompute`` is useful for production
    safeguards and controls. No geographic equality or authority is inferred.
    """
    verified_original = verify_snapshot(original, original_files)
    verified_successor = verify_snapshot(successor, successor_files, require_outputs=False)
    return _reuse_verified(original, successor, verified_original, verified_successor,
                           tile_id, set(force_recompute))


def _reuse_verified(original, successor, verified_original, verified_successor, tile_id, forced,
                    before=None, after=None, original_execution=None, successor_execution=None):
    if tile_id in forced:
        return {'status': 'recompute', 'reason': 'explicit-force-recompute', 'tile_id': tile_id}
    if canonical_json(original['semantics']) != canonical_json(successor['semantics']):
        return {'status': 'recompute', 'reason': 'global-semantics-changed', 'tile_id': tile_id}
    if original_execution is None:
        original_execution = _execution_fingerprints(original)
    if successor_execution is None:
        successor_execution = _execution_fingerprints(successor)
    if original_execution != successor_execution:
        return {'status': 'recompute', 'reason': 'execution-code-runtime-or-domain-bytes-changed', 'tile_id': tile_id}
    before = _tile(original, tile_id) if before is None else before
    after = _tile(successor, tile_id) if after is None else after
    if (any(before[key] != after[key] for key in ('bounds', 'query_order', 'status'))
            or canonical_json(before['unknowns']) != canonical_json(after['unknowns'])
            or _member_fingerprints(before, verified_original) != _member_fingerprints(after, verified_successor)):
        return {'status': 'recompute', 'reason': 'tile-operands-or-unknown-state-changed', 'tile_id': tile_id}
    output_receipts = []
    for output in before['outputs']:
        path = output['file']['path']
        raw = verified_original[output['source_commit'] + ':' + path]
        output_receipts.append({'role': output['role'], 'source_commit': output['source_commit'], 'path': path,
                                'bytes': len(raw), 'sha256': _sha(raw)})
    return {'status': 'reuse-original-output-bytes', 'reason': 'exact-semantics-and-ordered-operands-match',
            'tile_id': tile_id, 'original_snapshot': original['snapshot_id'],
            'successor_snapshot': successor['snapshot_id'], 'outputs': output_receipts,
            'preserved_status': before['status'], 'preserved_unknowns': before['unknowns']}


def build_reuse_plan(original, successor, original_files, successor_files, force_recompute=()):
    """Produce a complete preview plan after validating both full snapshots once.

    Only geometry-tile outputs are considered. The result is not a successor
    scientific run: every ``recompute`` row remains pending, global
    components/contacts/crosswalks are outside this plan, and native context
    statuses must be refreshed independently even for reused tiles.
    """
    verified_original = verify_snapshot(original, original_files)
    verified_successor = verify_snapshot(successor, successor_files, require_outputs=False)
    old_rows = {row['tile_id']: row for row in original['tiles']}
    new_rows = {row['tile_id']: row for row in successor['tiles']}
    new_ids = list(new_rows)
    original_execution = _execution_fingerprints(original)
    successor_execution = _execution_fingerprints(successor)
    forced = set(force_recompute)
    decisions = []
    for tile_id in new_ids:
        if tile_id not in old_rows:
            decisions.append({'status': 'recompute', 'reason': 'new-tile', 'tile_id': tile_id})
        else:
            decisions.append(_reuse_verified(original, successor, verified_original,
                                             verified_successor, tile_id, forced,
                                             before=old_rows[tile_id], after=new_rows[tile_id],
                                             original_execution=original_execution,
                                             successor_execution=successor_execution))
    old_ids = [row['tile_id'] for row in original['tiles']]
    new_id_set = set(new_ids)
    counts = {}
    for row in decisions:
        counts[row['status']] = counts.get(row['status'], 0) + 1
    return {'version': 'worldatlas-physical-gap-successor-plan-v1',
            'status': 'preview-not-installed', 'method': VERSION,
            'original_snapshot': original['snapshot_id'], 'successor_snapshot': successor['snapshot_id'],
            'original_tile_count': len(old_ids), 'successor_tile_count': len(new_ids),
            'tile_decision_count': len(decisions), 'decision_counts': counts,
            'retired_tile_ids': [tile_id for tile_id in old_ids if tile_id not in new_id_set],
            'tiles': decisions,
            'limits': ['Preview plan only; no tile was declared installed or current.',
                       'Unchanged tile reuse does not reuse global connectivity, contacts, crosswalks, priorities, or native-context statuses.',
                       'Source authority, physical-water truth, ownership, and geographic approval are not established.']}
