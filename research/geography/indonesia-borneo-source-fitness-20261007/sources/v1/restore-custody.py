#!/usr/bin/env python3
"""Restore complete authenticated custody shards as ordinary UTF-8 JSON files."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[5]
PACKET = Path('research/geography/indonesia-borneo-source-fitness-20261007')
SOURCE = PACKET / 'sources/v1'
INDEX_PATH = 'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'
FAMILY_PATH = SOURCE.as_posix() + '/family-row.json'
ROSTER_PATH = SOURCE.as_posix() + '/component-roster.txt'
INDEX_SHA = 'dfcca9fe2bb64805b94e784be89b3523f5683b95cbd4a617283965ca6187a77c'
FAMILY_SHA = 'a08249214711d84d7d220a61fe10f2d4582e7bc64f1a5ae811436ddaf22d94b3'
RESTORE_VINTAGE = 'restore-450126d0'
RESTORE_ROOT = PACKET.as_posix() + '/vintages'

sys.path.insert(0, str(REPO / 'scripts'))
from evidence.immutable import Baseline as BootstrapBaseline  # noqa: E402


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(REPO), 'show', f'{commit}:{path}'])


def descriptor(path: str, raw: bytes, **extra) -> dict:
    return {'path': path, 'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'file-bytes', **extra}


def main() -> None:
    code_commit = subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip()
    source_commit = subprocess.check_output(
        ['git', '-C', str(REPO), 'merge-base', 'HEAD', 'origin/main'], text=True).strip()
    current_main = subprocess.check_output(
        ['git', '-C', str(REPO), 'rev-parse', 'origin/main'], text=True).strip()
    if source_commit != current_main:
        raise ValueError('Rebase onto current origin/main before custody restoration')

    index_raw = git_bytes(code_commit, INDEX_PATH)
    if sha(index_raw) != INDEX_SHA or git_bytes(source_commit, INDEX_PATH) != index_raw:
        raise ValueError('Current source custody index is not byte-identical to its pinned main version')
    index = json.loads(index_raw)
    aliases = sorted((row for row in index['aliases']
                     if '/components-v3/components-' in row['original']['path']),
                    key=lambda row: row['original']['path'])
    if len(aliases) != 11:
        raise ValueError('Require the complete eleven-shard components-v3 custody inventory')

    source_paths = [INDEX_PATH, *[row['payload'] for row in aliases],
                    'scripts/evidence/immutable.py', 'scripts/evidence/contracts.py',
                    (SOURCE / 'restore-custody.py').as_posix(), FAMILY_PATH, ROSTER_PATH]
    pins = []
    for path in source_paths:
        raw = git_bytes(code_commit, path)
        extra = {}
        alias = next((row for row in aliases if row['payload'] == path), None)
        if alias:
            extra = {'uncompressed_bytes': alias['original']['uncompressed_bytes'],
                     'uncompressed_sha256': alias['original']['uncompressed_sha256']}
            if git_bytes(source_commit, path) != raw:
                raise ValueError('Custody shard changed between main and the authenticated candidate: ' + path)
        pins.append(descriptor(path, raw, **extra))

    bootstrap = BootstrapBaseline(REPO, code_commit, pins)
    modules = bootstrap.load_modules({
        'evidence.immutable': 'scripts/evidence/immutable.py',
        'evidence.contracts': 'scripts/evidence/contracts.py',
    })
    Baseline = modules['evidence.immutable'].Baseline
    NewVintage = modules['evidence.immutable'].NewVintage
    canonical_json = modules['evidence.immutable'].canonical_json
    baseline = Baseline(REPO, code_commit, pins)
    if baseline.materialized_bytes((SOURCE / 'restore-custody.py').as_posix()) != Path(__file__).read_bytes():
        raise ValueError('Executed restoration code differs from the authenticated candidate')

    family_raw = baseline.materialized_bytes(FAMILY_PATH)
    if sha(family_raw.rstrip(b'\n')) != FAMILY_SHA:
        raise ValueError('Pinned family row changed')
    family = json.loads(family_raw)
    selected = family.get('complete_component_ids')
    if family.get('component_count') != 45 or not isinstance(selected, list) or len(selected) != 45 or len(set(selected)) != 45:
        raise ValueError('Selected family is not the exact complete 45-component source scope')
    roster = baseline.materialized_bytes(ROSTER_PATH).decode('utf-8').splitlines()
    if sorted(selected) != roster or len(roster) != 45 or len(set(roster)) != 45:
        raise ValueError('Selected family row and preserved 45-ID roster differ')

    outputs: dict[str, bytes] = {}
    input_receipts = []
    subject_locations: dict[str, str] = {}
    global_ids = set()
    restored_features = 0
    for alias in aliases:
        path = alias['payload']
        raw = baseline.pinned_bytes(path)
        original = alias['original']
        if len(raw) != original['bytes'] or sha(raw) != original['sha256']:
            raise ValueError('Compressed custody bytes disagree with the index alias: ' + path)
        decoded = gzip.decompress(raw)
        if len(decoded) != original['uncompressed_bytes'] or sha(decoded) != original['uncompressed_sha256']:
            raise ValueError('Decoded custody bytes disagree with the index alias: ' + path)
        document = json.loads(decoded)
        features = document.get('features') if isinstance(document, dict) else None
        if document.get('type') != 'FeatureCollection' or not isinstance(features, list):
            raise ValueError('Decoded shard is not a complete GeoJSON FeatureCollection: ' + path)
        native_name = Path(original['path']).name.removesuffix('.gz')
        output_path = RESTORE_ROOT + '/' + RESTORE_VINTAGE + '/' + native_name
        restored_descriptor = descriptor(output_path, decoded)
        by_feature_id = {}
        for feature in features:
            feature_id = feature.get('id') if isinstance(feature, dict) else None
            if not isinstance(feature_id, str) or not feature_id or feature_id in global_ids:
                raise ValueError('Missing or duplicate full-shard feature identity: ' + str(feature_id))
            global_ids.add(feature_id)
            by_feature_id[feature_id] = True
        for identity in selected:
            if identity in by_feature_id:
                if identity in subject_locations:
                    raise ValueError('Selected component appears in more than one custody shard: ' + identity)
                subject_locations[identity] = output_path
        outputs[native_name] = decoded
        restored_features += len(features)
        input_receipts.append({
            'custody_payload_path': path,
            'custody_payload_sha256': original['sha256'],
            'custody_payload_bytes': original['bytes'],
            'original_source_path': original['path'],
            'decoded_sha256': original['uncompressed_sha256'],
            'decoded_bytes': original['uncompressed_bytes'],
            'restored_output': restored_descriptor,
            'feature_count': len(features),
        })
    if set(subject_locations) != set(selected):
        raise ValueError('Restored full custody shards do not contain the exact selected 45 subjects')
    if len(input_receipts) != 11:
        raise ValueError('Restoration did not include all eleven complete custody shards')

    restoration = {
        'version': 1,
        'status': 'complete',
        'method': 'Exact gzip decompression of each entire custody-v3 components-v3 payload; no filtering, recoding, geometry rewrite, or repair.',
        'source_commit': source_commit,
        'authenticated_candidate_commit': code_commit,
        'custody_index': descriptor(INDEX_PATH, index_raw),
        'family_row_sha256': FAMILY_SHA,
        'selected_subject_count': len(selected),
        'restored_shard_count': len(input_receipts),
        'restored_feature_count': restored_features,
        'source_shards': input_receipts,
        'selected_subject_containing_files': dict(sorted(subject_locations.items())),
    }
    outputs['custody-restoration.json'] = canonical_json(restoration)
    destination = NewVintage(baseline, PACKET.as_posix() + '/', RESTORE_VINTAGE, list(outputs))
    records = destination.publish_bytes(outputs)
    print(json.dumps({'status': 'complete', 'source_commit': source_commit,
                      'shard_count': len(input_receipts), 'restored_features': restored_features,
                      'selected_components': len(subject_locations), 'outputs': records}, sort_keys=True))


if __name__ == '__main__':
    main()
