#!/usr/bin/env python3
"""Check the first segment's native-grid contacts against a pinned physical mask.

The checker is research evidence for a candidate geometry, not a replacement
for validating the complete closure or the geographic source decisions.
"""
import argparse
import hashlib
import importlib.util
import json
from fractions import Fraction
from pathlib import Path

import numpy as np

WIDTH, HEIGHT = 131072, 54614
STEP = Fraction(360, WIDTH)


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def grid(point):
    return ((Fraction(str(point[0])) + 180) / STEP,
            (90 - Fraction(str(point[1]))) / STEP)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('geometry', 'checker', 'rows', 'runs'):
        parser.add_argument('--' + name, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    args = parser.parse_args()
    paths = {name: getattr(args, name) for name in ('geometry', 'checker', 'rows', 'runs')}
    expected = {name: getattr(args, name + '_sha256') for name in paths}
    for name, path in paths.items():
        if digest(path) != expected[name]:
            raise ValueError('input hash mismatch: ' + name)
    spec = importlib.util.spec_from_file_location('closure_checker', paths['checker'])
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    geometry = json.loads(Path(paths['geometry']).read_text())
    if geometry.get('type') != 'LineString' or len(geometry.get('coordinates', [])) < 2:
        raise ValueError('expected a LineString with at least two points')
    segment = geometry['coordinates'][:2]
    rows = np.memmap(paths['rows'], mode='r', dtype='<u4')
    runs = np.memmap(paths['runs'], mode='r', dtype='<u4').reshape(-1, 2)
    if len(rows) != HEIGHT + 1 or rows[0] != 0 or rows[-1] != len(runs):
        raise ValueError('invalid physical row index')
    contacts = []
    for x, y in checker.touched_segment(*grid(segment[0]), *grid(segment[1])):
        if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
            raise ValueError('contact outside grid')
        row = runs[int(rows[y]):int(rows[y + 1])]
        if len(row) == 0 or row[-1, 0] != WIDTH:
            raise ValueError('invalid physical row')
        code = int(row[np.searchsorted(row[:, 0], x, side='right'), 1])
        if code not in (1, 17):
            raise ValueError('unexpected physical code')
        contacts.append([x, y, code])
    for name, path in paths.items():
        if digest(path) != expected[name]:
            raise ValueError('input changed during check: ' + name)
    print(json.dumps({'segment': segment, 'contacts': contacts, 'input_sha256': expected,
                      'limitation': 'Grid-mask contact does not establish a surveyed shoreline.'},
                     sort_keys=True))


if __name__ == '__main__':
    main()
