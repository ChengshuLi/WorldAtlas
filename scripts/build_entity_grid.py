#!/usr/bin/env python3
"""Convert a V7 review RLE to a stable-entity RLE, without publishing it."""
import argparse
import hashlib
import json
import mmap
import struct
from pathlib import Path

U32 = struct.Struct('<I')
PAIR = struct.Struct('<II')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def build(meta, rows_path, runs_path, output):
    registry = meta['entity_registry']
    if (registry.get('schema_version') != 'worldatlas-entity-registry-v1' or not registry.get('revision')
            or registry.get('status') not in ('draft', 'accepted', 'rejected')):
        raise ValueError('Invalid registry snapshot')
    entities = {e['id']: e for e in registry['entities']}
    if not entities or len(entities) != len(registry['entities']):
        raise ValueError('Missing or duplicate entity ID')
    levels = ('continent', 'subcontinent', 'region', 'area', 'province', 'location')
    for entity in entities.values():
        entity_id, level = entity['id'], entity.get('level')
        if (type(entity_id) is not int or not 0 < entity_id <= 0xffffffff
                or not isinstance(entity.get('name'), str) or not entity['name'].strip() or level not in levels):
            raise ValueError('Invalid registry entity')
        parent = entity.get('parent_id')
        if level == 'continent':
            if parent is not None:
                raise ValueError('Invalid registry parent')
        elif parent not in entities or entities[parent].get('level') != levels[levels.index(level) - 1]:
            raise ValueError('Invalid registry parent')
        if ((level == 'location' and entity.get('physical_class') not in ('land', 'water'))
                or (level != 'location' and entity.get('physical_class') is not None)):
            raise ValueError('Invalid registry physical class')
    bindings = {}
    for category in meta['categories']:
        code, entity_id = category['id'], category['entity_id']
        if code in bindings or entity_id not in entities or not isinstance(entity_id, int) or not 0 < entity_id <= 0xffffffff:
            raise ValueError('Invalid category binding')
        if entities[entity_id]['level'] != 'continent':
            raise ValueError('V7 assignments must bind to continent-level entities')
        if category['physical_class'] != ('land' if 17 <= code <= 22 else 'water'):
            raise ValueError('Invalid V7 physical class')
        if code not in (*range(1, 11), *range(17, 23)):
            raise ValueError('Invalid V7 category code')
        bindings[code] = entity_id
    for code in range(17, 23):
        if code in bindings and bindings.get(code - 16) != bindings[code]:
            raise ValueError('Land and water must bind to the same entity')
    width, height = meta['width'], meta['height']
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        raise ValueError('Invalid dimensions')
    if rows_path.stat().st_size != 4 * (height + 1) or runs_path.stat().st_size % 8:
        raise ValueError('Invalid input stream sizes')
    output.mkdir(parents=True, exist_ok=False)
    out_rows, out_runs = output / 'rows.u32le', output / 'runs.u32le'
    total_runs = runs_path.stat().st_size // 8
    count = 0
    with rows_path.open('rb') as rf, runs_path.open('rb') as gf, \
         out_rows.open('xb') as ro, out_runs.open('xb') as go:
        grid = mmap.mmap(gf.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            prev_row = U32.unpack(rf.read(4))[0]
            if prev_row != 0:
                raise ValueError('First row offset is not zero')
            ro.write(U32.pack(0))
            for _ in range(height):
                end_row = U32.unpack(rf.read(4))[0]
                if end_row <= prev_row or end_row > total_runs:
                    raise ValueError('Invalid row offsets')
                start, last_id, last_end = 0, None, 0
                for r in range(prev_row, end_row):
                    end, code = PAIR.unpack_from(grid, r * 8)
                    if end <= start or end > width or code not in bindings:
                        raise ValueError('Invalid or unbound V7 run')
                    entity_id = bindings[code]
                    if last_id is not None and entity_id != last_id:
                        go.write(PAIR.pack(last_end, last_id)); count += 1
                    start, last_end, last_id = end, end, entity_id
                if start != width:
                    raise ValueError('Incomplete row')
                go.write(PAIR.pack(last_end, last_id)); count += 1
                if count > 0xffffffff:
                    raise ValueError('Run count exceeds u32 row offsets')
                ro.write(U32.pack(count)); prev_row = end_row
            if prev_row != total_runs:
                raise ValueError('Unreferenced runs')
        finally:
            grid.close()
    manifest = {
        'schema_version': 'worldatlas-entity-grid-v1', 'status': 'staged-not-published',
        'registry_revision': registry['revision'],
        'registry_and_bindings_sha256': hashlib.sha256(json.dumps(
            {'entity_registry': registry, 'bindings': sorted(bindings.items())},
            sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf8')).hexdigest(),
        'hierarchy_level': 'continent',
        'width': width, 'height': height, 'encoding': 'row-runs-u32le', 'run_count': count,
        'rows': {'file': out_rows.name, 'sha256': digest(out_rows)},
        'runs': {'file': out_runs.name, 'sha256': digest(out_runs)},
        'source_rows_sha256': digest(rows_path), 'source_runs_sha256': digest(runs_path),
    }
    with (output / 'manifest.json').open('x') as f:
        json.dump(manifest, f, indent=2); f.write('\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metadata', type=Path, help='prepared proposal JSON with registry and category bindings')
    parser.add_argument('rows', type=Path, help='V7 uncompressed row offsets (u32 little-endian)')
    parser.add_argument('runs', type=Path, help='V7 uncompressed endpoint/code pairs (u32 little-endian)')
    parser.add_argument('output', type=Path, help='new output directory')
    args = parser.parse_args()
    print(json.dumps(build(json.loads(args.metadata.read_text()), args.rows, args.runs, args.output), indent=2))

if __name__ == '__main__':
    main()
