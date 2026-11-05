#!/usr/bin/env python3
"""Apply a bounded, cell-center divider rule to a pinned RLE candidate grid.

All outputs are new files. Water and non-Europe/Asia labels are preserved.
The input divider must already contain the selected river and water closure.
"""
import argparse
import hashlib
import json
import os
import numpy as np
from shapely import contains_xy
from shapely.geometry import LineString, Point, box
from shapely.ops import split
from grid_io import read_grid


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def sides(line, bounds, europe_witness, asia_witness):
    path = LineString(line)
    if not path.is_simple or path.is_empty: raise ValueError('divider must be a simple nonempty line')
    pieces = split(box(*bounds), path)
    if len(pieces.geoms) != 2: raise ValueError('divider must split scope into exactly two polygons')
    e = [p for p in pieces.geoms if p.contains(Point(*europe_witness))]
    a = [p for p in pieces.geoms if p.contains(Point(*asia_witness))]
    if len(e) != 1 or len(a) != 1 or e[0].equals(a[0]): raise ValueError('invalid side witnesses')
    return e[0], a[0]


def update_row(old, physical, xs, lat, europe, asia, bounds, codec):
    w, s, e, n = bounds
    ec, ac, lands = codec['europe_code'], codec['asia_code'], codec['land_codes']
    inside = (xs > w) & (xs < e) & (lat > s) & (lat < n)
    ep = contains_xy(europe, xs, lat) & inside
    ap = contains_xy(asia, xs, lat) & inside
    if np.any(inside & ~(ep | ap) & (physical == 17)): raise ValueError('land center on divider or scope boundary')
    if np.any(inside & ((physical == 17) != np.isin(old, lands))): raise ValueError('candidate and physical land masks differ in scope')
    allowed = inside & (physical == 17) & np.isin(old, (ec, ac))
    new = old.copy()
    new[allowed & ep] = ec
    new[allowed & ap] = ac
    return new, {'land_centers': int(np.count_nonzero(inside & (physical == 17))),
                 'other_land_labels': int(np.count_nonzero(inside & (physical == 17) & ~np.isin(old, (ec, ac)))),
                 'europe_to_asia': int(np.count_nonzero((old == ec) & (new == ac))),
                 'asia_to_europe': int(np.count_nonzero((old == ac) & (new == ec)))}


def apply(candidate_rows, candidate_runs, physical_rows, physical_runs, line, cfg, out_rows, out_runs):
    width, height, step = cfg['width'], cfg['height'], cfg['step_degrees']
    west, north = cfg['west'], cfg['north']
    for rows, runs in ((candidate_rows, candidate_runs), (physical_rows, physical_runs)):
        if len(rows) != height + 1 or rows[0] != 0 or rows[-1] * 2 != len(runs) or np.any(rows[1:] <= rows[:-1]):
            raise ValueError('invalid grid row index')
    candidate_runs, physical_runs = candidate_runs.reshape(-1, 2), physical_runs.reshape(-1, 2)
    bounds = cfg['bounds']; europe, asia = sides(line, bounds, cfg['europe_witness'], cfg['asia_witness'])
    w, s, e, n = bounds
    if not (west <= w < e <= west + width * step and north - height * step <= s < n <= north): raise ValueError('scope outside grid')
    x0, x1 = max(0, int((w - west) // step)), min(width, int((e - west) // step) + 1)
    y0, y1 = max(0, int((north - n) // step)), min(height, int((north - s) // step) + 1)
    all_x = np.arange(width, dtype=np.int64); scope_x = all_x[x0:x1]; lons = west + (scope_x + .5) * step
    offsets = np.zeros(height + 1, dtype='<u4'); totals = dict.fromkeys(('land_centers','other_land_labels','europe_to_asia','asia_to_europe'), 0)
    with open(out_runs, 'xb') as out:
        for y in range(height):
            row = candidate_runs[candidate_rows[y]:candidate_rows[y+1]]
            if row[-1, 0] != width or np.any(row[1:, 0] <= row[:-1, 0]): raise ValueError('invalid candidate RLE row')
            if y0 <= y < y1:
                pro = physical_runs[physical_rows[y]:physical_rows[y+1]]
                if pro[-1, 0] != width or np.any(pro[1:, 0] <= pro[:-1, 0]): raise ValueError('invalid physical RLE row')
                old_scope = row[np.searchsorted(row[:, 0], scope_x, side='right'), 1]
                physical = pro[np.searchsorted(pro[:, 0], scope_x, side='right'), 1]
                new_scope, counts = update_row(old_scope, physical, lons, north - (y + .5) * step, europe, asia, bounds, cfg)
                for key in totals: totals[key] += counts[key]
                if np.any(old_scope != new_scope):
                    values = row[np.searchsorted(row[:, 0], all_x, side='right'), 1].copy()
                    values[x0:x1] = new_scope
                    ends = np.r_[np.flatnonzero(values[1:] != values[:-1]) + 1, width]
                    row = np.column_stack((ends, values[ends - 1])).astype('<u4')
            if int(offsets[y]) + len(row) > np.iinfo(np.uint32).max: raise OverflowError('row index exceeds u32')
            out.write(np.asarray(row, dtype='<u4').tobytes()); offsets[y+1] = int(offsets[y]) + len(row)
    with open(out_rows, 'xb') as out: out.write(offsets.tobytes())
    return totals


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('config','divider','candidate-rows','candidate-runs','physical-rows','physical-runs','output-prefix'): p.add_argument('--'+n, required=True)
    a = p.parse_args(); cfg = json.load(open(a.config));
    for name, path in [('divider',a.divider),('candidate_rows',a.candidate_rows),('candidate_runs',a.candidate_runs),('physical_rows',a.physical_rows),('physical_runs',a.physical_runs)]:
        if sha(path) != cfg['sha256'][name]: raise ValueError(name + ' SHA-256 mismatch')
    outputs = [a.output_prefix + x for x in ('.rows.u32le','.runs.u32le','.report.json')]
    if any(os.path.exists(x) for x in outputs): raise FileExistsError('output already exists')
    line = json.load(open(a.divider))
    arrays = [read_grid(p, cfg['sha256'][n]) for n,p in [('candidate_rows',a.candidate_rows),('candidate_runs',a.candidate_runs),('physical_rows',a.physical_rows),('physical_runs',a.physical_runs)]]
    counts = apply(*arrays, line, cfg, outputs[0], outputs[1])
    report = {'schema':'ural-delta-divider-apply-v1','status':'research-candidate','config':cfg,'counts':counts,
              'output_sha256':{'rows':sha(outputs[0]),'runs':sha(outputs[1])},
              'limitations':['Assignment is bounded by config scope and selected divider; ties on the divider fail.', 'Other continental labels and water are preserved.', 'Current-candidate status must be verified independently before integration.']}
    with open(outputs[2], 'x') as f: json.dump(report,f,sort_keys=True,indent=2)
    print(json.dumps(report))

if __name__ == '__main__': main()
