#!/usr/bin/env python3
"""Research check of both selected Europe closures against a candidate Ural line.

Inputs are the previously verified snapshot and stage-1 physical mask. The
terminal policy permits land only in each route's exact terminal cell on its
first or last segment. This independently screens physical contact; it is not
the production closure proof and does not certify geographical authority.
"""
import hashlib
import importlib.util
import json
from fractions import Fraction

import numpy as np

SNAPSHOT = '/tmp/review_snapshot.json'
BOUNDARY = '/tmp/ural-raw-backed-continuous.geometry.json'
CHECKER = '/tmp/ural-closure-checker.py'
ROWS = '/tmp/ural-draft82/physical-rows.u32le'
RUNS = '/tmp/ural-draft82/physical-runs.u32le'
PINS = {SNAPSHOT: '615bc1aaa67d099ebd140dc172fd54885d66e82ef595a57a97e5a284f483f7cc',
        BOUNDARY: 'c7e8476d10d0ab95da6dc717e0b5aa3852d967a9c1a19ea6932a460b0a31a2d4',
        CHECKER: '18e9f7ef5effbb56e9cc83c588f015121ef9673bb4acecda353bb92fb7f462b2',
        ROWS: '6cf4b928b6609b4d9c8fdd9264bb6f463a38a5d7376d6ffb0ffc43502284a468',
        RUNS: '1396fe9dfde48b65b6e5884089a5445682511fb47f9560ce06edd53c95d928d7'}
W, H = 131072, 54614
STEP = Fraction(360, W)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def canonical(g):
    return hashlib.sha256(json.dumps(g, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def grid(p):
    return ((Fraction(str(p[0])) + 180) / STEP, (90 - Fraction(str(p[1]))) / STEP)


for path, expected in PINS.items():
    if sha(path) != expected:
        raise ValueError('hash mismatch: ' + path)
snap = json.load(open(SNAPSHOT))
boundary = json.load(open(BOUNDARY))
if canonical(boundary) != '68390aa6ce5352226777adde3979315e1de85ca26d662c4b1c32610d1d73da66':
    raise ValueError('candidate geometry hash mismatch')
caucasus = next(b for b in snap['mainland_boundaries'] if b['boundary_id'] == 'caucasus_blacksea_anapa_to_caspian')
if canonical(caucasus['geometry']) != caucasus['geometry_sha256']:
    raise ValueError('Caucasus geometry hash mismatch')
spec = importlib.util.spec_from_file_location('closure_checker', CHECKER)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
rows = np.memmap(ROWS, mode='r', dtype='<u4')
runs = np.memmap(RUNS, mode='r', dtype='<u4').reshape(-1, 2)
if len(rows) != H + 1 or rows[0] != 0 or rows[-1] != len(runs):
    raise ValueError('invalid physical row index')


def cellcode(x, y):
    if not (0 <= x < W and 0 <= y < H):
        raise ValueError('contact outside physical grid')
    row = runs[int(rows[y]):int(rows[y + 1])]
    if len(row) == 0 or row[-1, 0] != W:
        raise ValueError('invalid physical row')
    return int(row[np.searchsorted(row[:, 0], x, side='right'), 1])


results = []
for routeid, start, end in (
    ('europe_exterior_closure_v1', boundary['coordinates'][0], caucasus['geometry']['coordinates'][0]),
    ('europe_caspian_closure_v1', boundary['coordinates'][-1], caucasus['geometry']['coordinates'][-1]),
):
    route = next(r for r in snap['routes'] if r['route_id'] == routeid)
    geom = route['geometry']
    if canonical(geom) != route['geometry_sha256']:
        raise ValueError('route hash mismatch')
    points = geom['coordinates']
    if points[0] != start or points[-1] != end:
        raise ValueError('route does not bind the candidate endpoints')
    xy = [grid(p) for p in points]
    if any(v.denominator == 1 for p in (xy[0], xy[-1]) for v in p):
        raise ValueError('terminal on grid edge')
    terminal = [(int(x // 1), int(y // 1)) for x, y in (xy[0], xy[-1])]
    if terminal[0] == terminal[1]:
        raise ValueError('terminals share a cell')
    visits, land = 0, set()
    for i, (a, b) in enumerate(zip(xy, xy[1:])):
        segment_land = set()
        for x, y in checker.touched_segment(*a, *b):
            visits += 1
            code = cellcode(x, y)
            if code == 1:
                continue
            if code != 17:
                raise ValueError('unexpected physical code')
            if not ((i == 0 and (x, y) == terminal[0]) or
                    (i == len(xy) - 2 and (x, y) == terminal[1])):
                raise ValueError('nonterminal land contact')
            segment_land.add((x, y))
            land.add((x, y))
        if len(segment_land) > 1:
            raise ValueError('segment touches multiple land cells')
    results.append({'route_id': routeid, 'route_sha256': route['geometry_sha256'],
                    'cell_visits': visits, 'terminals': terminal,
                    'terminal_land_cells': sorted(land), 'policy_satisfied': True})
for path, expected in PINS.items():
    if sha(path) != expected:
        raise ValueError('input changed during validation: ' + path)
print(json.dumps({'status': 'research-check-passed', 'candidate_sha256': canonical(boundary),
                  'closures': results, 'input_sha256': PINS,
                  'limitations': ['Not a production closure proof; source authority and full ring geography are separate.',
                                  'Uses the pinned stage-1 research physical mask.']}, sort_keys=True))
