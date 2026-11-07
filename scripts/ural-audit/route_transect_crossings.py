#!/usr/bin/env python3
"""Count crossings between a source route and sampled WGS84 transects.

This is a topology diagnostic, not a watershed classification. Transects are
geodesics approximated by short chords in the source route's projected CRS.
"""
import argparse
import hashlib
import json
import math
from pyproj import Transformer
from shapely.geometry import LineString
from projected_route import GEOD, ProjectedRoute


def screen(coords, crs, stations, offsets, step=5):
    if step <= 0 or any(x <= 0 for x in offsets):
        raise ValueError('step and offsets must be positive')
    route = ProjectedRoute(coords, crs)
    if any(x < 0 or x > route.length for x in stations):
        raise ValueError('station outside route')
    forward = Transformer.from_crs(4326, crs, always_xy=True)
    reverse = Transformer.from_crs(crs, 4326, always_xy=True)
    source = LineString([forward.transform(*p) for p in coords])
    if not source.is_simple:
        raise ValueError('source route must be simple')
    rows = []
    for station in stations:
        lon, lat, azimuth = route.point(station)
        for offset in offsets:
            count = max(1, math.ceil(2 * offset / step))
            samples = [-offset + (2 * offset * i / count) for i in range(count + 1)]
            transect = LineString([forward.transform(*GEOD.fwd(lon, lat, azimuth - 90, value)[:2]) for value in samples])
            intersection = source.intersection(transect)
            points = [intersection] if intersection.geom_type == 'Point' else list(getattr(intersection, 'geoms', []))
            if any(p.geom_type != 'Point' for p in points) or (not points and not intersection.is_empty):
                raise ValueError('transect overlaps source route or has an unsupported intersection')
            distances = sorted(abs(GEOD.inv(lon, lat, *reverse.transform(p.x, p.y))[2]) for p in points)
            rows.append({'station_wgs84_m': station, 'offset_wgs84_m': offset,
                         'intersection_count': len(points), 'intersection_distances_wgs84_m': distances})
    return {'route_length_wgs84_m_approx': route.length, 'transect_chord_max_m': step,
            'results': rows, 'note': 'Topology uses projected-linear source route and chord-approximated WGS84 transects; lengths and crossings have no formal error bound.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--line', required=True)
    p.add_argument('--line-sha', required=True)
    p.add_argument('--crs', required=True)
    p.add_argument('--station', type=float, action='append', required=True)
    p.add_argument('--offset', type=float, action='append', required=True)
    p.add_argument('--step', type=float, default=5)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    with open(a.line, 'rb') as f:
        raw = f.read()
    if hashlib.sha256(raw).hexdigest() != a.line_sha:
        raise ValueError('line SHA-256 mismatch')
    result = screen(json.loads(raw), a.crs, a.station, a.offset, a.step)
    result['line_sha256'] = a.line_sha
    with open(a.output, 'x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))
