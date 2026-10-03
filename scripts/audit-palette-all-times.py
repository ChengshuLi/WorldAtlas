#!/usr/bin/env python3
"""Derive display contrast constraints for every supported source interval.

This only reads pinned immutable inputs. It does not infer history, revise source
entity IDs, approve geography, or write a replacement historical archive.
"""
import argparse, array, collections, gzip, hashlib, json, pathlib
import importlib.util
_spec = importlib.util.spec_from_file_location("palette_inputs", pathlib.Path(__file__).with_name("audit-palette-inputs.py"))
_inputs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_inputs)
read, key, ROOT = _inputs.read, _inputs.key, _inputs.ROOT

def overlaps(a, b):
    i = j = 0
    while i < len(a) and j < len(b):
        if max(a[i][0], b[j][0]) < min(a[i][1], b[j][1]):
            return True
        if a[i][1] <= b[j][1]:
            i += 1
        else:
            j += 1
    return False

def merge_ranges(ranges):
    out = []
    for start, end in sorted(ranges):
        if out and start <= out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out

def main(directory):
    directory = directory.resolve()
    if not directory.is_relative_to(ROOT / 'data' / 'engineering'):
        raise ValueError('Owned engineering output directory required')
    display = read(directory / 'source-owner-dated-display.json.gz')
    raster = read(directory / 'raster-neighbors.json.gz')
    source = ROOT / 'data' / 'ownership-history'
    index = read(source / 'index.json')
    if hashlib.sha256((source / 'index.json').read_bytes()).hexdigest() != display['source_index_sha256']:
        raise ValueError('Ownership display baseline changed')
    grid_path = ROOT / 'data' / 'canonical-grid' / 'manifest.json'
    if hashlib.sha256(grid_path.read_bytes()).hexdigest() != display['grid_manifest_sha256'] or display['grid_manifest_sha256'] != raster['manifest_sha256']:
        raise ValueError('Raster display baseline changed')
    grid = read(grid_path)
    bounds = read(grid_path.parent / grid['bounds']['path'], grid['bounds']['sha256'])
    ids = {row['id']: row['index'] for row in bounds}
    if len(ids) != len(bounds) or sorted(ids.values()) != list(range(1, len(bounds) + 1)):
        raise ValueError('Noncanonical raster identities')
    names = array.array('h')
    for entry in index['evidence_parts']:
        names.extend(-1 if row[0] is None else row[0] for row in read(source / entry['path'], entry['sha256']))
    numbers = {value: i + 1 for i, value in enumerate(display['keys'])}
    memo = {}
    intervals = [array.array('i') for _ in range(len(bounds) + 1)]
    ranges = [set() for _ in range(len(numbers) + 1)]
    seen = set()
    for entry in index['parts']:
        for location, rows in read(source / entry['path'], entry['sha256']):
            if location in seen or location not in ids:
                raise ValueError('Duplicate or absent ownership subject')
            seen.add(location)
            out = intervals[ids[location]]
            for start, end, owner, status, evidence in rows:
                number = 0
                if owner is not None and names[evidence] >= 0 and index['statuses_order'][status] == 'derived':
                    pair = (owner, names[evidence])
                    if pair not in memo:
                        memo[pair] = numbers[key(index['owner_ids'][owner], index['labels'][pair[1]])]
                    number = memo[pair]
                    ranges[number].add((start, end))
                if out and start < out[-2] or start >= end:
                    raise ValueError('Overlapping or invalid source intervals')
                out.extend((start, end, number))
    stride = len(numbers) + 1
    adjacent, nearby = set(), set()
    def constraints(pairs, output):
        for left, right in pairs:
            a, b = intervals[left], intervals[right]
            i = j = 0
            while i < len(a) and j < len(b):
                if max(a[i], b[j]) < min(a[i+1], b[j+1]):
                    x, y = a[i+2], b[j+2]
                    if x and y and x != y:
                        output.add(min(x, y) * stride + max(x, y))
                if a[i+1] <= b[j+1]:
                    i += 3
                else:
                    j += 3
    constraints(raster['adjacent'], adjacent)
    constraints(raster['nearby'], nearby)
    groups = collections.defaultdict(list)
    for k, value in enumerate(display['keys'], 1):
        groups[json.loads(value)[0]].append(k)
    unions = [merge_ranges(value) for value in ranges]
    aliases = set()
    for values in groups.values():
        for i, a in enumerate(values):
            for b in values[i+1:]:
                if overlaps(unions[a], unions[b]):
                    aliases.add(min(a,b) * stride + max(a,b))
    def decode(edges):
        return [[display['keys'][v // stride - 1], display['keys'][v % stride - 1]] for v in sorted(edges)]
    result = {'version': 1, 'source_index_sha256': display['source_index_sha256'],
              'grid_manifest_sha256': display['grid_manifest_sha256'], 'scope': 'Every exact source ownership interval on the fixed published raster; not historical or geographic approval',
              'location_subjects_read': len(seen), 'keys': display['keys'], 'adjacent': decode(adjacent),
              'nearby': decode(nearby - adjacent), 'concurrent_source_aliases': decode(aliases)}
    with (directory / 'all-time-contrast-constraints.json.gz').open('xb') as stream:
        stream.write(gzip.compress(json.dumps(result, ensure_ascii=False, separators=(',', ':')).encode(), mtime=0))
    print(json.dumps({k: len(result[k]) for k in ['adjacent', 'nearby', 'concurrent_source_aliases']}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=pathlib.Path, required=True)
    main(parser.parse_args().directory)
