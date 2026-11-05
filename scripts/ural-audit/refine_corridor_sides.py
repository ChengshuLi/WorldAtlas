#!/usr/bin/env python3
"""Numerically refine local sides for a sampled corridor comparison.

Nearby segment selection and bounded minimization are numerical sensitivity
checks, not a certified global nearest-line or polygon classification proof.
"""
import argparse
import collections
import hashlib
import json
import math
import numpy as np
from pyproj import Geod, Transformer
from scipy.optimize import minimize_scalar
from scipy.spatial import cKDTree

G = Geod(ellps='WGS84')
STEP = 360 / 131072


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def refine(line_path, line_sha, input_path, input_sha, margin):
    if digest(line_path) != line_sha or digest(input_path) != input_sha:
        raise ValueError('input checksum mismatch')
    if not math.isfinite(margin) or margin <= 0:
        raise ValueError('invalid search margin')
    with open(line_path) as f:
        line = np.asarray(json.load(f), dtype=float)
    with open(input_path) as f:
        baseline = json.load(f)
    if baseline['input_sha256']['line'] != line_sha:
        raise ValueError('baseline line does not match')
    spacing, windows = baseline['target_sampling_wgs84_m'], baseline['half_windows_wgs84_m']
    samples, owners = [], []
    for ordinal, (a, b) in enumerate(zip(line, line[1:]), 1):
        _, _, length = G.inv(*a, *b)
        n = max(1, math.ceil(length / spacing))
        if len(samples) + n > 2000000:
            raise ValueError('sample limit exceeded')
        for j in range(n):
            samples.append(tuple(a + (b-a) * (j/n)))
            owners.append(ordinal)
    samples.append(tuple(line[-1]))
    owners.append(len(line)-1)
    samples = np.asarray(samples)
    lon, lat = samples[:, 0], samples[:, 1]
    _, _, lengths = G.inv(lon[:-1], lat[:-1], lon[1:], lat[1:])
    station = np.r_[0, np.cumsum(lengths)]
    ecef = Transformer.from_crs(4979, 4978, always_xy=True)
    tree = cKDTree(np.column_stack(ecef.transform(lon, lat, np.zeros(len(lon)))))
    results = []
    summary = collections.Counter()
    for record in baseline['corridor_cells']:
        x, y = record['x'], record['y']
        cell = (-180 + (x + 0.5) * STEP, 90 - (y + 0.5) * STEP)
        ids = tree.query_ball_point(ecef.transform(*cell, 0), record['sampled_wgs84_m'] + margin + 0.001)
        segments = set()
        for k in ids:
            i = owners[k] - 1
            segments.update(j for j in (i-1, i, i+1) if 0 <= j < len(line)-1)
        if not segments:
            raise ValueError('no candidate source segment')
        best = None
        for index in segments:
            a, b = line[index], line[index+1]
            def distance(t):
                return G.inv(*cell, *(a + (b-a)*t))[2]
            solution = minimize_scalar(distance, bounds=(0, 1), method='bounded', options={'xatol': 1e-12})
            if not solution.success:
                raise ValueError('bounded nearest search failed')
            for fraction in (0., float(solution.x), 1.):
                value = distance(fraction)
                if not math.isfinite(value):
                    raise ValueError('invalid nearest distance')
                if best is None or value < best[0]:
                    best = (value, index, fraction)
        distance, index, fraction = best
        if distance > record['sampled_wgs84_m'] + 1e-5:
            raise ValueError('refinement exceeds sampled distance')
        point = line[index] + fraction * (line[index+1] - line[index])
        bearing, _, _ = G.inv(*point, *cell)
        near = tree.query_ball_point(ecef.transform(*point, 0), margin + 0.001)
        if not near:
            raise ValueError('nearest point lacks tangent samples')
        subset = samples[near]
        _, _, ds = G.inv(subset[:, 0], subset[:, 1], np.full(len(near), point[0]), np.full(len(near), point[1]))
        position = station[near[int(np.argmin(ds))]]
        labels = []
        for window in windows:
            left = np.searchsorted(station, max(0, position-window), side='left')
            right = min(np.searchsorted(station, min(station[-1], position+window), side='left'), len(station)-1)
            azimuth, _, separation = G.inv(*samples[left], *samples[right])
            if not math.isfinite(separation) or separation <= 0:
                raise ValueError('undefined tangent')
            turn = (bearing - azimuth + 180) % 360 - 180
            labels.append(19 if turn > 0 else 18)
        outcome = 'unstable' if len(set(labels)) != 1 else ('candidate_matches' if labels[0] == record['candidate'] else 'reference_matches')
        summary[outcome] += 1
        results.append({'x': x, 'y': y, 'candidate': record['candidate'], 'reference': record['reference'],
                        'refined_wgs84_m': distance, 'source_segment_start_ordinal': index+1,
                        'source_segment_fraction': fraction, 'candidate_segments_considered': len(segments),
                        'local_side_labels': labels, 'outcome': outcome})
    if digest(line_path) != line_sha or digest(input_path) != input_sha:
        raise ValueError('input changed during refinement')
    return {'line_sha256': line_sha, 'sampled_comparison_sha256': input_sha, 'search_margin_m': margin,
            'half_windows_wgs84_m': windows, 'summary': dict(summary), 'cells': results,
            'caveat': 'Numerical WGS84 nearest search uses sample-based segment candidates and bounded minimization plus endpoints. Neither floating-point pruning, continuous global optimality nor local side topology is formally certified; this does not select a boundary.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--line', required=True)
    p.add_argument('--line-sha', required=True)
    p.add_argument('--sampled-comparison', required=True)
    p.add_argument('--sampled-comparison-sha', required=True)
    p.add_argument('--margin', type=float, default=100)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    result = refine(a.line, a.line_sha, a.sampled_comparison, a.sampled_comparison_sha, a.margin)
    with open(a.output, 'x') as f:
        json.dump(result, f)
    print(json.dumps({'cells': len(result['cells']), 'summary': result['summary'], 'status': 'research only'}))
