"""WGS84 area of polygons with straight longitude/latitude source edges.

Integrate the ellipsoid's latitude-strip antiderivative around each ring rather
than replacing source edges with finite geodesic chords. The centered difference
formula and compensated sums retain precision for small/high-latitude parcels.
"""
import math
import numpy as np

A = 6378137.0
FLATTENING = 1 / 298.257223563
E2 = FLATTENING * (2 - FLATTENING)
E = math.sqrt(E2)
C = A * A * (1 - E2) / 2
NODES, WEIGHTS = np.polynomial.legendre.leggauss(16)
NODES = (NODES + 1) / 2
WEIGHTS = WEIGHTS / 2


def ring_area(ring, nodes=NODES, weights=WEIGHTS):
    coordinates = np.deg2rad(np.asarray(ring.coords))
    if len(coordinates) < 4:
        return 0.0
    latitude, longitude = coordinates[:, 1], coordinates[:, 0]
    center = (latitude.min() + latitude.max()) / 2
    u0 = math.sin(center)
    sums = []
    # Limit quadrature temporaries even for long coastlines.
    for start in range(0, len(coordinates) - 1, 8192):
        end = min(start + 8192, len(coordinates) - 1)
        p = latitude[start:end, None]
        phi = p + (latitude[start+1:end+1] - latitude[start:end])[:, None] * nodes
        u = np.sin(phi)
        difference = 2 * np.cos((phi + center) / 2) * np.sin((phi - center) / 2)
        strip = C * (difference * (1 + E2 * u * u0) / ((1 - E2 * u * u) * (1 - E2 * u0 * u0)) + np.arctanh(E * difference / (1 - E2 * u * u0)) / E)
        edges = (longitude[start+1:end+1] - longitude[start:end]) * np.dot(strip, weights)
        sums.append(math.fsum(edges.tolist()))
    return math.fsum(sums)


def area(geometry):
    if geometry.is_empty:
        return 0.0
    if geometry.geom_type == 'Polygon':
        return max(0.0, abs(ring_area(geometry.exterior)) - math.fsum(abs(ring_area(r)) for r in geometry.interiors))
    return math.fsum(area(g) for g in getattr(geometry, 'geoms', []) if g.geom_type in ('Polygon', 'MultiPolygon', 'GeometryCollection'))
