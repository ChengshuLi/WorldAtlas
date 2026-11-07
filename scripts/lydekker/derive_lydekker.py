#!/usr/bin/env python3
"""Reconstruct and smooth the Figure 8.1 review trace from external inputs.

This is a documented manual interpretation, not automatic image extraction.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter1d

GEOMETRY_SHA256 = 'fce7c71b71666d70dae5265eb1fee7102beffdbc37837d93266e8b96c65c1c1e'
# Derived affine parameters from the coarse image-to-land fit, not source data.
OVERVIEW_REGISTRATION = {
    'left_lon': 113.95716170040805,
    'top_lat': 26.750589807071723,
    'degrees_per_pixel_x': 0.04266257553093161,
    'degrees_per_pixel_y': 0.042636060827007494,
}
SIGMA = 0.08
STEP = 0.001


def read_observation(path):
    observation = json.loads(Path(path).read_text())
    geometry = observation['geometry']
    if geometry.get('type') != 'MultiLineString':
        raise ValueError('expected a MultiLineString inset observation')
    raw = json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != GEOMETRY_SHA256:
        raise ValueError(f'geometry SHA-256 {actual}, expected {GEOMETRY_SHA256}')
    return observation


def assemble(observation):
    """Join visible strokes and explicitly inferred links, north to south."""
    obs = observation['geometry']['coordinates']
    reg = OVERVIEW_REGISTRATION
    def geo(p):
        x, y = p
        return [reg['left_lon'] + x * reg['degrees_per_pixel_x'],
                reg['top_lat'] - y * reg['degrees_per_pixel_y']]
    n = [geo(p) for p in [(440, 560), (423, 579)]]
    s1 = [geo(p) for p in [(390, 696), (398, 701), (409, 707),
                            (419, 713), (429, 720), (438, 725)]]
    s2a = [geo(p) for p in [(459, 754), (460, 766)]]
    s2b = [geo(p) for p in [(460, 778), (461, 790), (462, 802), (462, 811)]]
    parts = [n, [n[-1], [130.58, .66], [130.25, .40], obs[0][0]], obs[0],
             [obs[0][-1], [129.52, -1.20], [129.45, -1.42],
              [129.46, -1.65], [129.52, -1.82], obs[1][0]], obs[1],
             [obs[1][-1], [130.41, -2.59], s1[0]], s1,
             [s1[-1], [133.10, -4.55], s2a[0]], s2a,
             [s2a[-1], s2b[0]], s2b]
    result = []
    for part in parts:
        if result and result[-1] != part[0]:
            raise ValueError('discontinuous trace')
        result.extend(part if not result else part[1:])
    if any(a[1] <= b[1] for a, b in zip(result, result[1:])):
        raise ValueError('latitude must be strictly decreasing')
    return result


def smooth(coords):
    """Sample longitude vs latitude, Gaussian filter, and preserve endpoints."""
    lats = np.array([p[1] for p in coords][::-1])
    lons = np.array([p[0] for p in coords][::-1])
    ys = np.linspace(lats[0], lats[-1], int(math.ceil((lats[-1]-lats[0])/STEP))+1)
    delta = ys[1] - ys[0]
    raw = np.interp(ys, lats, lons)
    out = gaussian_filter1d(raw, SIGMA/delta, mode='nearest')
    t0 = np.clip((ys-ys[0])/(4*SIGMA), 0, 1)
    t1 = np.clip((ys[-1]-ys)/(4*SIGMA), 0, 1)
    w0 = 1-3*t0*t0+2*t0*t0*t0
    w1 = 1-3*t1*t1+2*t1*t1*t1
    out += (raw[0]-out[0])*w0 + (raw[-1]-out[-1])*w1
    out[0], out[-1] = raw[0], raw[-1]
    return [[float(x), float(y)] for x, y in zip(out[::-1], ys[::-1])]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation', required=True, help='externally stored inset-trace JSON')
    parser.add_argument('--output', required=True, help='output GeoJSON outside the repository')
    args = parser.parse_args()
    obs = read_observation(args.observation)
    points = smooth(assemble(obs))
    obj = {'type': 'Feature', 'properties': {'method': 'manual interpretation and Gaussian smoothing',
            'source': 'https://press-files.anu.edu.au/downloads/press/n13144/pdf/ch08.pdf#page=2',
            'caveat': 'Schematic; inferred gaps; not a surveyed or legal boundary'},
           'geometry': {'type': 'LineString', 'coordinates': points}}
    Path(args.output).write_text(json.dumps(obj, indent=2) + '\n')


if __name__ == '__main__':
    main()
