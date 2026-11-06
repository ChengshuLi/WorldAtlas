"""Geodesic-only proximity helpers for synthetic boundary fixtures.

These helpers do not produce map metrics. They exclude sample points near a
synthetic boundary so the fixture tests inside/outside classification away
from edge ambiguity.
"""
import math

import numpy as np
from pyproj import Geod

GEOD = Geod(ellps='WGS84')
FIXTURE_CLEARANCE_M = 111_319.49079327357  # approximately the old 1-degree guard
SAMPLE_SPACING_M = 500.0


def fixture_boundary_filter(boundary):
    """Prepare a WGS84 proximity predicate for a synthetic boundary.

    Boundary edges are sampled at <=500 m in their coordinate-linear lon/lat
    representation, and the half-spacing is included as a conservative guard.
    This is a fixture-selection predicate, not a reported point-to-line metric.
    """
    coords = []
    rings = [boundary.coords] if boundary.geom_type == 'LineString' else []
    if boundary.geom_type == 'LinearRing':
        rings = [boundary.coords]
    elif boundary.geom_type == 'Polygon':
        rings = [boundary.exterior.coords, *(ring.coords for ring in boundary.interiors)]
    elif boundary.geom_type in ('MultiLineString', 'GeometryCollection'):
        rings = [part.coords for part in boundary.geoms if part.geom_type in ('LineString', 'LinearRing')]
    for ring in rings:
        for a, b in zip(ring, ring[1:]):
            length = abs(GEOD.inv(a[0], a[1], b[0], b[1])[2])
            # A conservative upper bound on the coordinate-linear path uses
            # the maximum WGS84 metres per degree for both axes.
            path_bound = max(length, 111_700.0 * (abs(b[0] - a[0]) + abs(b[1] - a[1])))
            count = max(1, math.ceil(path_bound / SAMPLE_SPACING_M))
            coords.extend((a[0] + (b[0] - a[0]) * i / count,
                           a[1] + (b[1] - a[1]) * i / count) for i in range(count))
        if ring:
            coords.append(tuple(ring[-1][:2]))
    if not coords:
        raise ValueError('boundary has no line segments')
    lon = np.fromiter((xy[0] for xy in coords), dtype=float)
    lat = np.fromiter((xy[1] for xy in coords), dtype=float)
    def within_clearance(point):
        _, _, distances = GEOD.inv(lon, lat, np.full(len(coords), point.x), np.full(len(coords), point.y))
        return float(np.min(distances)) <= FIXTURE_CLEARANCE_M + SAMPLE_SPACING_M / 2
    return within_clearance
