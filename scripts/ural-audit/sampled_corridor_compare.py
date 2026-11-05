#!/usr/bin/env python3
"""Compare two pinned land grids near a sampled geographic source line.

This is a research sensitivity screen, not a classification or a pipeline
change. Local side bearings do not establish globally correct polygon sides.
"""
import argparse
import collections
import hashlib
import json
import math
import numpy as np
from pyproj import Geod, Transformer
from scipy.spatial import cKDTree

WIDTH, HEIGHT, STEP = 131072, 54614, 360 / 131072
G = Geod(ellps='WGS84')


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def screen(paths, expected, bbox, spacing, radius, windows):
    if any(digest(paths[k]) != expected[k] for k in paths):
        raise ValueError('input checksum mismatch')
    if not all(math.isfinite(x) and x > 0 for x in [spacing, radius, *windows]) or not windows:
        raise ValueError('invalid spacing, radius or window')
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -60 < south < north <= 90):
        raise ValueError('invalid scan bounds')
    with open(paths['line']) as f:
        line = json.load(f)
    if len(line) < 2:
        raise ValueError('line must contain at least two points')
    samples, owners = [], []
    for index, (a, b) in enumerate(zip(line, line[1:]), 1):
        _, _, length = G.inv(*a, *b)
        if not math.isfinite(length):
            raise ValueError('invalid line coordinates')
        count = max(1, math.ceil(length / spacing))
        if len(samples) + count > 2000000:
            raise ValueError('source sample limit exceeded')
        for j in range(count):
            t = j / count
            samples.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            owners.append(index)
    samples.append(tuple(line[-1]))
    owners.append(len(line) - 1)
    samples = np.asarray(samples)
    lon, lat = samples[:, 0], samples[:, 1]
    _, _, steps = G.inv(lon[:-1], lat[:-1], lon[1:], lat[1:])
    positions = np.r_[0, np.cumsum(steps)]
    tangent = {}
    for window in windows:
        left = np.searchsorted(positions, np.maximum(0, positions - window), side='left')
        right = np.minimum(np.searchsorted(positions, np.minimum(positions[-1], positions + window), side='left'), len(positions) - 1)
        tangent[window] = np.asarray(G.inv(lon[left], lat[left], lon[right], lat[right])[0])
    ecef = Transformer.from_crs(4979, 4978, always_xy=True)
    tree = cKDTree(np.column_stack(ecef.transform(lon, lat, np.zeros(len(lon)))))
    row1 = np.memmap(paths['candidate_rows'], dtype='<u4', mode='r')
    run1 = np.memmap(paths['candidate_runs'], dtype='<u4', mode='r').reshape(-1, 2)
    row2 = np.memmap(paths['reference_rows'], dtype='<u4', mode='r')
    run2 = np.memmap(paths['reference_runs'], dtype='<u4', mode='r').reshape(-1, 2)
    for rows, runs in ((row1, run1), (row2, run2)):
        if len(rows) != HEIGHT + 1 or rows[0] != 0 or rows[-1] != len(runs):
            raise ValueError('invalid row index')
    xlo, xhi = int((west + 180) / STEP), min(WIDTH, int((east + 180) / STEP) + 1)
    ylo, yhi = int((90 - north) / STEP), min(HEIGHT, int((90 - south) / STEP) + 1)
    bbox_counts = collections.Counter()
    matches = []
    visits = 0
    for y in range(ylo, yhi):
        a = run1[int(row1[y]):int(row1[y+1])]
        b = run2[int(row2[y]):int(row2[y+1])]
        if not len(a) or not len(b) or a[-1, 0] != WIDTH or b[-1, 0] != WIDTH:
            raise ValueError('invalid run row')
        ends = np.union1d(a[:, 0], b[:, 0])
        stops = np.r_[xlo, ends[(ends > xlo) & (ends < xhi)], xhi]
        left, right = stops[:-1], stops[1:]
        va = a[np.searchsorted(a[:, 0], left, side='right'), 1]
        vb = b[np.searchsorted(b[:, 0], left, side='right'), 1]
        differing = np.isin(va, (18, 19)) & np.isin(vb, (18, 19)) & (va != vb)
        cell_lat = 90 - (y + 0.5) * STEP
        for first, last, candidate, reference in zip(left[differing], right[differing], va[differing], vb[differing]):
            bbox_counts[f'{int(candidate)}-{int(reference)}'] += int(last - first)
            for x in range(int(first), int(last)):
                visits += 1
                if visits > 2000000:
                    raise ValueError('difference-cell limit exceeded')
                cell_lon = -180 + (x + 0.5) * STEP
                ids = tree.query_ball_point(ecef.transform(cell_lon, cell_lat, 0), radius + 0.001)
                if not ids:
                    continue
                subset = samples[ids]
                azimuth, _, distances = G.inv(subset[:, 0], subset[:, 1], np.full(len(ids), cell_lon), np.full(len(ids), cell_lat))
                j = int(np.argmin(distances))
                if float(distances[j]) > radius:
                    continue
                source_index = ids[j]
                labels = []
                for window in windows:
                    turn = (float(azimuth[j]) - tangent[window][source_index] + 180) % 360 - 180
                    labels.append(19 if turn > 0 else 18)
                matches.append({'x': x, 'y': y, 'candidate': int(candidate), 'reference': int(reference),
                                'sampled_wgs84_m': float(distances[j]), 'source_segment_start_ordinal': owners[source_index],
                                'local_side_labels': labels})
    if any(digest(paths[k]) != expected[k] for k in paths):
        raise ValueError('input changed during comparison')
    return {'input_sha256': expected, 'bbox': bbox, 'target_sampling_wgs84_m': spacing,
            'source_samples': len(samples), 'radius_wgs84_m': radius, 'half_windows_wgs84_m': windows,
            'bbox_both_land_disagreements': dict(bbox_counts), 'corridor_cells': matches,
            'caveat': 'WGS84 distances are to source samples, not exact continuous-line minima. ECEF pruning uses a 1mm numerical cushion; sampling and chord stationing have no formal error bound. Local tangent sides can disagree with global topology. Historical comparison is not a classification decision.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('candidate-rows', 'candidate-runs', 'reference-rows', 'reference-runs', 'line'):
        p.add_argument('--' + name, required=True)
        p.add_argument('--' + name + '-sha', required=True)
    p.add_argument('--bbox', nargs=4, type=float, required=True)
    p.add_argument('--spacing', type=float, default=50)
    p.add_argument('--radius', type=float, default=1000)
    p.add_argument('--window', type=float, action='append', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    keys = ('candidate_rows', 'candidate_runs', 'reference_rows', 'reference_runs', 'line')
    paths = {k: getattr(a, k) for k in keys}
    hashes = {k: getattr(a, k + '_sha') for k in keys}
    result = screen(paths, hashes, a.bbox, a.spacing, a.radius, a.window)
    with open(a.output, 'x') as f:
        json.dump(result, f)
    print(json.dumps({'bbox_both_land_disagreements': result['bbox_both_land_disagreements'],
                      'corridor_cells': len(result['corridor_cells']), 'status': 'research only'}))
