#!/usr/bin/env python3
"""Assemble a simple border chain from pinned OSM way/full JSON responses."""
import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path


def assemble(manifest, directory):
    entries = manifest['ways']
    if not isinstance(entries, list) or not entries:
        raise ValueError('missing way inputs')
    nodes, ways = {}, {}
    for entry in entries:
        way_id, name, expected = entry['id'], entry['file'], entry['sha256']
        if type(way_id) is not int or way_id in ways or Path(name).name != name:
            raise ValueError('invalid or duplicate way input')
        raw = (directory / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('source hash mismatch')
        elements = json.loads(raw)['elements']
        found = [e for e in elements if e['type'] == 'way' and e['id'] == way_id]
        if len(found) != 1 or len(found[0]['nodes']) < 2:
            raise ValueError('missing or invalid way')
        ways[way_id] = found[0]['nodes']
        for e in elements:
            if e['type'] == 'node':
                point = (e['lon'], e['lat'])
                if any(type(v) not in (int, float) or not math.isfinite(v) for v in point) or not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
                    raise ValueError('invalid node coordinates')
                if e['id'] in nodes and nodes[e['id']] != point:
                    raise ValueError('conflicting node coordinates')
                nodes[e['id']] = point
    ends = defaultdict(list)
    for way_id, refs in ways.items():
        ends[refs[0]].append(way_id)
        ends[refs[-1]].append(way_id)
    terminals = [n for n, refs in ends.items() if len(refs) == 1]
    if len(terminals) != 2 or any(len(refs) > 2 for refs in ends.values()):
        raise ValueError('ways do not form one unbranched chain')
    start = manifest['start_node']
    if start not in terminals:
        raise ValueError('start node is not a chain terminal')
    current, remaining, chain = start, set(ways), []
    while remaining:
        candidates = [i for i in ends[current] if i in remaining]
        if len(candidates) != 1:
            raise ValueError('disconnected or ambiguous chain')
        way_id = candidates[0]
        remaining.remove(way_id)
        refs = ways[way_id]
        refs = refs if refs[0] == current else refs[::-1]
        chain.extend(refs if not chain else refs[1:])
        current = refs[-1]
    if current == start or current not in terminals or any(n not in nodes for n in chain):
        raise ValueError('invalid terminal or missing node')
    coords = [[float(v) for v in nodes[n]] for n in chain]
    if any(a == b for a, b in zip(coords, coords[1:])):
        raise ValueError('duplicate adjacent coordinates')
    return {'type': 'LineString', 'coordinates': coords}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path)
    p.add_argument('directory', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    geometry = assemble(json.loads(args.manifest.read_bytes()), args.directory)
    raw = json.dumps(geometry, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    with args.output.open('xb') as f:
        f.write(raw)
    print(json.dumps({'vertices': len(geometry['coordinates']), 'sha256': hashlib.sha256(raw).hexdigest()}))


if __name__ == '__main__':
    main()
