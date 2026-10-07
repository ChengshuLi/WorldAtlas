#!/usr/bin/env python3
"""Build the validator's identity-only inventory from the pinned family record."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'sources' / 'v1'
FAMILY_SHA = 'a08249214711d84d7d220a61fe10f2d4582e7bc64f1a5ae811436ddaf22d94b3'
ROSTER_SHA = '88831aad22806bf4f461197a12cb8309bf9a0139e5bd82b967a55e8255ad26ec'
PREFIX = 'physical-component:'


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    row_raw = (SOURCE / 'family-row.json').read_bytes().rstrip(b'\n')
    if sha(row_raw) != FAMILY_SHA:
        raise ValueError('Family record hash differs from the complete source scan')
    row = json.loads(row_raw)
    ids = row.get('complete_component_ids')
    roster = (SOURCE / 'component-roster.txt').read_text(encoding='utf-8').splitlines()
    roster_bytes = ''.join(value + '\n' for value in roster).encode()
    if (row.get('component_count') != 45 or not isinstance(ids, list) or len(ids) != 45 or
            len(set(ids)) != 45 or sorted(ids) != roster or sha(roster_bytes.rstrip(b'\n')) != ROSTER_SHA):
        raise ValueError('Family row and complete sorted 45-ID roster disagree')
    native = sorted(value[len(PREFIX):] for value in ids if value.startswith(PREFIX))
    if len(native) != 45 or len(set(native)) != 45:
        raise ValueError('Unexpected component ID namespace')
    inventory = {'version': 1, 'source_family_id': row['id'], 'source_row_sha256': FAMILY_SHA,
                 'component_roster_sha256': ROSTER_SHA, 'component_ids': native}
    registry = {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'id': PREFIX + value,
         'properties': {'source_value': value, 'id': PREFIX + value, 'source_property': 'component_id'},
         'geometry': None} for value in native]}
    for name, value in [('subject-inventory.json', inventory), ('subject-registry.json', registry)]:
        path = SOURCE / name
        if path.exists():
            raise FileExistsError(path)
        path.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'complete', 'subjects': len(native),
                      'inventory_sha256': sha((SOURCE/'subject-inventory.json').read_bytes()),
                      'registry_sha256': sha((SOURCE/'subject-registry.json').read_bytes())}, sort_keys=True))


if __name__ == '__main__':
    main()
