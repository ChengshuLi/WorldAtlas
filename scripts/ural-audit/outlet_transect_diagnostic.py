#!/usr/bin/env python3
"""Compare exact local D8 roots of geodesic transect samples.

An identical root is a model result and does not establish a surveyed divide.
The optional basin crosswalk is intentionally not used in this diagnostic.
"""
import argparse
import hashlib
import json
import numpy as np
import rasterio
from pyproj import Transformer
from priority_d8 import drainage
from projected_route import ProjectedRoute, GEOD


def digest(data):
    return hashlib.sha256(data).hexdigest()


def screen(elevation, valid, transform, crs, coordinates, station, offsets, tangent_window=None):
    route = ProjectedRoute(coordinates, crs)
    if station < 0 or station > route.length or any(x <= 0 for x in offsets):
        raise ValueError('invalid station or offset')
    roots, _, _ = drainage(elevation, valid, transform, crs)
    lon, lat, azimuth = route.point(station)
    segment_azimuth = azimuth
    if tangent_window is not None:
        if not np.isfinite(tangent_window) or tangent_window <= 0 or station - tangent_window < 0 or station + tangent_window > route.length:
            raise ValueError('invalid tangent window')
        left = route.point(station - tangent_window)[:2]
        right = route.point(station + tangent_window)[:2]
        azimuth, _, chord = GEOD.inv(*left, *right)
        if not np.isfinite(chord) or chord <= 0:
            raise ValueError('undefined window tangent')
    to_grid = Transformer.from_crs(4326, crs, always_xy=True)
    to_geo = Transformer.from_crs(crs, 4326, always_xy=True)
    results = []
    for offset in offsets:
        values = []
        for sign in (-1, 1):
            point = GEOD.fwd(lon, lat, azimuth - 90, sign * offset)[:2]
            row, col = rasterio.transform.rowcol(transform, *to_grid.transform(*point))
            if not (0 <= row < elevation.shape[0] and 0 <= col < elevation.shape[1]) or not valid[row, col]:
                values.append(None)
                continue
            root = int(roots[row, col])
            if root < 0:
                values.append(None)
                continue
            rr, cc = divmod(root, elevation.shape[1])
            outlet = to_geo.transform(*rasterio.transform.xy(transform, rr, cc))
            values.append({'root_index': root, 'outlet_lonlat': list(outlet), 'elevation': float(elevation[row, col])})
        results.append({'offset_wgs84_m': offset, 'samples': values,
                        'same_local_root': None if None in values else values[0]['root_index'] == values[1]['root_index']})
    return {'station_wgs84_m': station, 'station_lonlat': [lon, lat], 'segment_azimuth_degrees': segment_azimuth,
            'transect_azimuth_basis_degrees': azimuth, 'tangent_window_wgs84_m': tangent_window, 'results': results,
            'note': 'D8 roots are local model outputs. Route stationing approximates projected-linear geometry by WGS84 chord sums; no formal error bound.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dem', required=True)
    p.add_argument('--dem-sha', required=True)
    p.add_argument('--line', required=True)
    p.add_argument('--line-sha', required=True)
    p.add_argument('--station', type=float, required=True)
    p.add_argument('--offset', type=float, action='append', required=True)
    p.add_argument('--tangent-window', type=float, help='WGS84 distance on each side for the chord-direction tangent')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    with open(a.line, 'rb') as f:
        raw = f.read()
    if digest(raw) != a.line_sha:
        raise ValueError('line hash mismatch')
    h = hashlib.sha256()
    with open(a.dem, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    if h.hexdigest() != a.dem_sha:
        raise ValueError('DEM hash mismatch')
    with rasterio.open(a.dem) as ds:
        z = ds.read(1).astype('float64')
        valid = np.isfinite(z) & (ds.read_masks(1) != 0)
        if ds.nodata is not None and np.isfinite(ds.nodata):
            valid &= z != ds.nodata
        result = screen(z, valid, ds.transform, ds.crs, json.loads(raw), a.station, a.offset, a.tangent_window)
    result.update({'line_sha256': a.line_sha, 'dem_sha256': a.dem_sha})
    with open(a.output, 'x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))
