"""Summarize hypothetical face-screen cells around a candidate join.

This consumes a precomputed research artifact, not the current map or an
exception list. It does not establish that a candidate is geographically
correct, or that a different candidate would affect the same cells.
"""
import argparse
import collections
import hashlib
import json
import math

from pyproj import Geod


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--impact', required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--lon', required=True, type=float)
    p.add_argument('--lat', required=True, type=float)
    p.add_argument('--radius-m', required=True, type=float)
    a = p.parse_args()
    if not (math.isfinite(a.lon) and math.isfinite(a.lat) and math.isfinite(a.radius_m)
            and -180 <= a.lon <= 180 and -90 <= a.lat <= 90 and a.radius_m > 0):
        raise ValueError('invalid coordinate or radius')
    with open(a.impact, 'rb') as f:
        raw = f.read()
    if hashlib.sha256(raw).hexdigest() != a.sha256:
        raise ValueError('impact input digest mismatch')
    impact = json.loads(raw)
    cells = impact['cells']
    if not isinstance(cells, list) or any(not isinstance(row, list) or len(row) != 6 for row in cells):
        raise ValueError('invalid impact cells')
    if len({(row[0], row[1]) for row in cells}) != len(cells):
        raise ValueError('duplicate cells')
    step = 360 / 131072
    geod = Geod(ellps='WGS84')
    within = []
    nearest = None
    for row in cells:
        r, c = row[:2]
        if type(r) is not int or type(c) is not int or not 0 <= r < 54614 or not 0 <= c < 131072:
            raise ValueError('invalid grid cell')
        lon = -180 + (c + .5) * step
        lat = 90 - (r + .5) * step
        distance = geod.inv(a.lon, a.lat, lon, lat)[2]
        nearest = distance if nearest is None else min(nearest, distance)
        if distance <= a.radius_m:
            within.append(row)
    counts = collections.Counter((r[2], r[3], r[4], r[5]) for r in within)
    print(json.dumps({'impact_sha256': a.sha256, 'join_lonlat': [a.lon, a.lat],
                      'radius_m': a.radius_m, 'grid_step_degrees': step,
                      'artifact_cells': len(cells), 'nearest_center_m': nearest,
                      'within_radius': len(within),
                      'counts': [{'candidate_code': k[0], 'v7_code': k[1],
                                  'source_side': k[2], 'alternative_side': k[3], 'cells': v}
                                 for k, v in sorted(counts.items())],
                      'limitations': 'historical bounded-face screen; not current labels or approved changes'},
                     sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
