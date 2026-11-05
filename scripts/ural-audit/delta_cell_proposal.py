#!/usr/bin/env python3
"""Build a guarded cell-level Ural delta proposal from a pinned side screen.

This emits a review artifact only; it never writes a candidate grid. A connected
land component can contain cells on both sides of a continental divider.
"""
import argparse
import hashlib
import json
import numpy as np
from delta_side_screen import read_grid


def propose(screen, candidate_rows, candidate_runs, physical_rows, physical_runs, width, height, step):
    def validate(rows, runs):
        if len(rows) != height + 1 or rows[0] != 0 or rows[-1] * 2 != len(runs) or np.any(rows[1:] <= rows[:-1]):
            raise ValueError('invalid RLE row index')
        return runs.reshape(-1, 2)
    candidate_runs = validate(candidate_rows, candidate_runs)
    physical_runs = validate(physical_rows, physical_runs)
    def value(rows, runs, x, y):
        row = runs[rows[y]:rows[y+1]]
        if row[-1, 0] != width or np.any(row[1:, 0] <= row[:-1, 0]):
            raise ValueError('invalid RLE row')
        return int(row[np.searchsorted(row[:, 0], x, side='right'), 1])
    mappings = [('asia_labeled_europe', 19, 18), ('europe_labeled_asia', 18, 19)]
    cells, seen = [], set()
    for key, old, new in mappings:
        entries = screen['differences'][key]
        if len(entries) != screen['summary'][key]['count']:
            raise ValueError('screen count mismatch')
        for entry in entries:
            x, y = entry['x'], entry['y']
            if not (isinstance(x, int) and isinstance(y, int) and 0 <= x < width and 0 <= y < height):
                raise ValueError('invalid cell index')
            if (x, y) in seen:
                raise ValueError('duplicate cell')
            seen.add((x, y))
            if value(candidate_rows, candidate_runs, x, y) != old:
                raise ValueError('candidate label no longer matches screen')
            if value(physical_rows, physical_runs, x, y) != 17:
                raise ValueError('screen cell is not stage-1 physical land')
            cells.append({'x': x, 'y': y, 'longitude_center': -180 + (x + .5) * step,
                          'latitude_center': 90 - (y + .5) * step, 'from': old, 'to': new,
                          'distance_to_boundary_m': entry['distance_m']})
    return sorted(cells, key=lambda c: (c['y'], c['x']))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('screen', 'candidate-rows', 'candidate-runs', 'physical-rows', 'physical-runs',
                 'physical-rows-sha', 'physical-runs-sha', 'output'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--width', type=int, required=True)
    p.add_argument('--height', type=int, required=True)
    p.add_argument('--step', type=float, required=True)
    a = p.parse_args()
    with open(a.screen, 'rb') as f: screen_bytes = f.read()
    screen = json.loads(screen_bytes)
    cr = read_grid(a.candidate_rows, screen['rows_sha256'])
    cv = read_grid(a.candidate_runs, screen['runs_sha256'])
    pr = read_grid(a.physical_rows, a.physical_rows_sha)
    pv = read_grid(a.physical_runs, a.physical_runs_sha)
    cells = propose(screen, cr, cv, pr, pv, a.width, a.height, a.step)
    result = {'schema': 'ural-delta-cell-side-proposal-v1', 'status': 'review-only',
              'rule': 'label each physical-land cell by its center side of the supplied divider; connectivity does not override side',
              'screen_sha256': hashlib.sha256(screen_bytes).hexdigest(), 'screen': {k: screen[k] for k in ('rows_sha256', 'runs_sha256', 'line_file_sha256', 'bounds')},
              'physical_rows_sha256': a.physical_rows_sha, 'physical_runs_sha256': a.physical_runs_sha,
              'width': a.width, 'height': a.height, 'step_degrees': a.step,
              'counts': {'europe_to_asia': sum(c['from'] == 19 for c in cells), 'asia_to_europe': sum(c['from'] == 18 for c in cells)},
              'limitations': ['Conditional on supplied selected line, water closure and candidate grid.', 'A cell center on the divider requires a separate tie policy.', 'This artifact does not modify the grid.'], 'cells': cells}
    with open(a.output, 'x') as f: json.dump(result, f, sort_keys=True, separators=(',', ':'))
    print(json.dumps(result['counts']))

if __name__ == '__main__': main()
