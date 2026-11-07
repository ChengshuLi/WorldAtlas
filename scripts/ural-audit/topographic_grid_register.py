#!/usr/bin/env python3
"""Fit a scan's printed projected grid and check independent WGS84 features.

Input JSON supplies a map SHA-256, CRS, pixel/grid control pairs and optional
independent pixel/lon-lat checks. Pixel coordinates refer to the original scan.
Residuals are diagnostic, not an uncertainty bound on unsampled features.
"""
import argparse
import hashlib
import json
import numpy as np
from pyproj import Geod, Transformer


def fit(spec):
    pts = np.asarray([x['pixel'] + [1] for x in spec['controls']], dtype=float)
    coords = np.asarray([x['grid'] for x in spec['controls']], dtype=float)
    if len(pts) < 4 or pts.shape[1:] != (3,) or coords.shape != (len(pts), 2):
        raise ValueError('at least four two-dimensional control pairs required')
    if not np.isfinite(pts).all() or not np.isfinite(coords).all() or np.linalg.matrix_rank(pts) != 3:
        raise ValueError('invalid or collinear controls')
    matrix = np.linalg.lstsq(pts, coords, rcond=None)[0]
    to_wgs = Transformer.from_crs(spec['grid_crs'], 4326, always_xy=True)
    geod = Geod(ellps='WGS84')
    def residual(pixel, expected_lonlat):
        grid = np.asarray(pixel + [1], dtype=float) @ matrix
        lon, lat = to_wgs.transform(*grid)
        return abs(geod.inv(lon, lat, *expected_lonlat)[2])
    controls = [residual(c['pixel'], list(to_wgs.transform(*c['grid']))) for c in spec['controls']]
    checks = [{'name': c['name'], 'residual_wgs84_m': residual(c['pixel'], c['lonlat'])} for c in spec.get('checks', [])]
    return {'affine_pixel_to_grid': matrix.tolist(), 'control_residual_wgs84_m': controls,
            'independent_checks': checks, 'grid_crs': spec['grid_crs'],
            'warning': 'Fit residuals and individual checkpoints are not a positional accuracy bound.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', required=True)
    p.add_argument('--spec', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    with open(a.spec) as f:
        spec = json.load(f)
    h = hashlib.sha256()
    with open(a.image, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    if h.hexdigest() != spec['image_sha256']:
        raise ValueError('image SHA-256 mismatch')
    result = fit(spec)
    result['image_sha256'] = h.hexdigest()
    with open(a.output, 'x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))
