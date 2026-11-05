#!/usr/bin/env python3
"""Screen a closure against a pinned physical RLE using exact cell contacts.

This research diagnostic is not the formal terminal-closure verifier. It uses
the existing checker's exact rational closed-cell traversal and reports all
contacts, including the stored terminal policy; it never changes a grid.
"""
import argparse
import collections
from decimal import Decimal
from fractions import Fraction
import hashlib
import importlib.util
import json
import numpy as np


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def run(rows_path, runs_path, geometry_path, checker_path, expected):
    paths = {'rows': rows_path, 'runs': runs_path, 'checker': checker_path}
    if any(sha(paths[k]) != expected[k] for k in paths):
        raise ValueError('pinned input checksum mismatch')
    with open(geometry_path) as f:
        numeric_points = json.load(f, parse_float=Decimal)
    with open(geometry_path) as f:
        points = json.load(f)
    geometry = {'type': 'LineString', 'coordinates': points}
    raw = json.dumps(geometry, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    geometry_sha = hashlib.sha256(raw).hexdigest()
    if geometry_sha != expected['geometry']:
        raise ValueError('geometry checksum mismatch')
    spec = importlib.util.spec_from_file_location('closure_checker', checker_path)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    width, height, step = 131072, 54614, Fraction(360, 131072)
    rows = np.memmap(rows_path, dtype='<u4', mode='r')
    runs = np.memmap(runs_path, dtype='<u4', mode='r').reshape(-1, 2)
    if len(rows) != height + 1 or rows[0] != 0 or rows[-1] != len(runs):
        raise ValueError('invalid row index')
    gridpoints = [((Fraction(lon) + 180) / step, (Fraction(90) - Fraction(lat)) / step) for lon, lat in numeric_points]
    terminals = [{'cell': [int(p[0] // 1), int(p[1] // 1)],
                  'on_grid_edge': p[0].denominator == 1 or p[1].denominator == 1} for p in (gridpoints[0], gridpoints[-1])]
    visited, land = set(), set()
    land_by_segment, codes = collections.defaultdict(set), collections.Counter()
    visits = 0
    for index, (a, b) in enumerate(zip(gridpoints, gridpoints[1:])):
        for x, y in checker.touched_segment(*a, *b):
            if not 0 <= x < width or not 0 <= y < height:
                raise ValueError('route touches outside grid')
            visits += 1
            if visits > 2000000:
                raise ValueError('contact limit exceeded')
            row = runs[int(rows[y]):int(rows[y + 1])]
            if not len(row) or row[-1, 0] != width:
                raise ValueError('invalid row')
            code = int(row[np.searchsorted(row[:, 0], x, side='right'), 1])
            if code not in (1, 17):
                raise ValueError('unexpected physical code')
            if code == 17:
                land.add((x, y))
                land_by_segment[index].add((x, y))
            if (x, y) not in visited:
                visited.add((x, y))
                codes[code] += 1
    start, end = tuple(terminals[0]['cell']), tuple(terminals[1]['cell'])
    terminal_ok = not any(x['on_grid_edge'] for x in terminals) and all(
        len(cells) <= 1 and ((i == 0 and cells == {start}) or (i == len(gridpoints)-2 and cells == {end}))
        for i, cells in land_by_segment.items())
    if any(sha(paths[k]) != expected[k] for k in paths):
        raise ValueError('input changed during screen')
    return {'geometry_sha256': geometry_sha, 'physical_rows_sha256': expected['rows'],
            'physical_runs_sha256': expected['runs'], 'checker_sha256': expected['checker'],
            'vertices': len(gridpoints), 'segments': len(gridpoints) - 1, 'cell_visits': visits,
            'unique_cells': len(visited), 'cell_code_counts': dict(codes), 'terminals': terminals,
            'land_cells': [list(p) for p in sorted(land)],
            'land_cells_by_segment': {str(i): [list(p) for p in sorted(v)] for i, v in sorted(land_by_segment.items())},
            'terminal_policy_satisfied_in_screen': terminal_ok,
            'note': 'Research screen of pinned mask; not a formal production proof, source validation or classification audit.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ('rows', 'runs', 'geometry', 'checker', 'rows-sha', 'runs-sha', 'geometry-sha', 'checker-sha', 'output'):
        p.add_argument('--' + arg, required=True)
    a = p.parse_args()
    result = run(a.rows, a.runs, a.geometry, a.checker,
                 {'rows': a.rows_sha, 'runs': a.runs_sha, 'geometry': a.geometry_sha, 'checker': a.checker_sha})
    with open(a.output, 'x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))
