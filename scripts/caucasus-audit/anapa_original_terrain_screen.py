"""Screen two Anapa line candidates against quality-screened original AW3D30.

The lines are research inputs, not decisions. Perpendicular offsets and sample
stations use WGS84 meters. Center-high profiles do not prove flow direction or
the connected watershed. Sea, vegetation and urban features can bias DSMs.
"""
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import rasterio

from geodesic_line import GEOD, GeodesicLine


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('dsm', 'mask', 'stack', 'selected', 'candidate'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args()
    with rasterio.open(a.dsm) as d, rasterio.open(a.mask) as m, rasterio.open(a.stack) as k:
        if d.crs is None or d.crs.to_epsg() != 4326 or any(
                (x.crs != d.crs or x.transform != d.transform or x.shape != d.shape) for x in (m, k)):
            raise ValueError('terrain layers must share one EPSG:4326 grid')
        z, mask, stack = d.read(1), m.read(1), k.read(1)
        transform, nodata = d.transform, d.nodata

    def terrain(point):
        col, row = ~transform * point
        row, col = math.floor(row), math.floor(col)
        if row < 2 or col < 2 or row + 2 >= z.shape[0] or col + 2 >= z.shape[1]:
            return None
        vals = z[row-2:row+3, col-2:col+3]
        ok = (mask[row-2:row+3, col-2:col+3] == 0) & (stack[row-2:row+3, col-2:col+3] > 0) & np.isfinite(vals)
        if nodata is not None:
            ok &= vals != nodata
        return float(np.median(vals)) if bool(ok.all()) else None

    output = {}
    for name in ('selected', 'candidate'):
        path = getattr(a, name)
        line = GeodesicLine(json.loads(Path(path).read_bytes())['coordinates'])
        summary = {}
        for offset in (100, 250, 500):
            counts = Counter()
            details = []
            for station in range(0, int(line.length) + 1, 100):
                pos = line.point(station)
                lo, hi = line.point(max(0, station - 20)), line.point(min(line.length, station + 20))
                azimuth, _, dist = GEOD.inv(*lo, *hi)
                if not math.isfinite(dist) or dist <= 0:
                    counts['undefined_normal'] += 1
                    continue
                points = [GEOD.fwd(*pos, azimuth - 90, offset)[:2], pos,
                          GEOD.fwd(*pos, azimuth + 90, offset)[:2]]
                heights = [terrain(pt) for pt in points]
                if any(x is None for x in heights):
                    counts['quality_invalid'] += 1
                    continue
                left, center, right = heights
                if center > left and center > right:
                    kind = 'center_high'
                elif center < left and center < right:
                    kind = 'center_low'
                elif min(left, right) < center < max(left, right):
                    kind = 'slope'
                else:
                    kind = 'tie'
                counts[kind] += 1
                if station <= 500 or station >= max(0, line.length - 500):
                    details.append({'station_m': station, 'heights_left_center_right_m': heights, 'kind': kind})
            summary[str(offset)] = {'counts': dict(counts), 'endpoint_nearby_valid': details}
        output[name] = {'line_sha256': sha(path), 'length_m': line.length, 'offsets_m': summary}
    print(json.dumps({'schema': 'anapa-original-terrain-screen-v1', 'lines': output,
                      'source_sha256': {k: sha(getattr(a, k)) for k in ('dsm', 'mask', 'stack')},
                      'limitations': 'One DSM, 5x5 fully valid mask/stack, 100 m stations; not a routed watershed.'},
                     sort_keys=True, allow_nan=False, indent=2))


if __name__ == '__main__':
    main()
