#!/usr/bin/env python3
"""Screen two published federal basin control points against the Ural line.

The order's control points are regional descriptions, not a surveyed
Europe-Asia line. Distances use WGS84 to sampled coordinate-linear segments;
they do not prove a closest point or positional accuracy of either source.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from pyproj import Geod

G = Geod(ellps='WGS84')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('geometry', type=Path)
    p.add_argument('--geometry-sha256', required=True)
    p.add_argument('--point', action='append', nargs=3, metavar=('ID', 'LONGITUDE', 'LATITUDE'), required=True)
    args = p.parse_args()
    geom = json.loads(args.geometry.read_bytes())
    digest = hashlib.sha256(json.dumps(geom, sort_keys=True, separators=(',', ':'),
                                       allow_nan=False).encode()).hexdigest()
    if digest != args.geometry_sha256 or geom['type'] != 'LineString':
        raise ValueError('unexpected boundary geometry')
    results = {}
    for name, lon_str, lat_str in args.point:
        lon, lat = float(lon_str), float(lat_str)
        if name in results or not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError('duplicate name or invalid coordinates')
        best = (float('inf'), None)
        for a, b in zip(geom['coordinates'], geom['coordinates'][1:]):
            if min(a[1], b[1]) > lat + .1 or max(a[1], b[1]) < lat - .1:
                continue
            length = G.inv(*a, *b)[2]
            steps = max(1, math.ceil(length / 20))
            for i in range(steps + 1):
                t = i / steps
                pt = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
                distance = G.inv(lon, lat, *pt)[2]
                if distance < best[0]:
                    best = distance, pt
        if best[1] is None:
            raise ValueError('no candidate segment near ' + name)
        results[name] = {'published_lonlat': [lon, lat], 'nearest_sample_lonlat': best[1],
                         'distance_m': best[0]}
    print(json.dumps({'geometry_sha256': digest, 'sample_spacing_m': 20,
                      'latitude_screen_degrees': .1, 'points': results,
                      'limits': 'Sampled distances; published control points are not a precision survey or a complete divider.'},
                     sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
