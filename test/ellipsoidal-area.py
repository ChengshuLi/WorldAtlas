"""Independent analytic/convergence checks for the source-edge area integral."""
import math
import pathlib
import random
import sys
import numpy as np
from shapely import segmentize
from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient
from pyproj import Geod

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from ellipsoidal_area import area, ring_area
from majority import canonical

geod = Geod(ellps='WGS84')
a = 6378137.0
f = 1 / 298.257223563
e2 = f * (2 - f)
e = math.sqrt(e2)


def latitude_strip(phi):
    u = math.sin(math.radians(phi))
    return a*a*(1-e2)/2*(u/(1-e2*u*u) + math.atanh(e*u)/e)


def analytic_rectangle(west, south, east, north):
    return math.radians(east-west)*(latitude_strip(north)-latitude_strip(south))


for latitude in [0, 30, 60, 85, 89]:
    rectangle = box(0, latitude, 1.01, latitude+.01)
    expected = analytic_rectangle(0, latitude, 1.01, latitude+.01)
    assert math.isclose(area(rectangle), expected, rel_tol=1e-10)
    assert area(box(0, latitude, .505, latitude+.01))/area(rectangle) == .5
    assert area(Polygon(list(reversed(rectangle.exterior.coords)))) == area(rectangle)

rng = random.Random(137)
nodes, weights = np.polynomial.legendre.leggauss(32)
nodes, weights = (nodes+1)/2, weights/2
max_quadrature_drift = 0
max_geodesic_drift = 0
for _ in range(300):
    x, y = rng.uniform(-150, 150), rng.uniform(-80, 60)
    width, height = rng.uniform(.000001, 20), rng.uniform(.000001, 20)
    polygon = Polygon([(x,y), (x+width,y+height*.05), (x+width*.8,y+height), (x+width*.1,y+height*.95), (x,y)])
    result = area(polygon)
    finer = abs(ring_area(polygon.exterior, nodes, weights))
    drift = abs(result/finer-1)
    max_quadrature_drift = max(max_quadrature_drift, drift)
    assert drift < 1e-12
    # A progressively dense geodesic perimeter approaches the same straight
    # source-edge surface, providing a separately implemented numerical check.
    dense = segmentize(polygon, .001)
    reference = abs(geod.geometry_area_perimeter(orient(dense, sign=1))[0])
    max_geodesic_drift = max(max_geodesic_drift, abs(reference/result-1))
    assert math.isclose(reference, result, rel_tol=1e-6)

outer = box(0, 60, 1, 61)
hole = box(.2, 60.2, .8, 60.8)
holed = Polygon(outer.exterior.coords, [hole.exterior.coords])
assert math.isclose(area(holed), area(outer)-area(hole), rel_tol=1e-14)
crossing = canonical(Polygon([(179,0),(-179,0),(-179,2),(179,2),(179,0)], [[(179.5,.5),(-179.5,.5),(-179.5,1.5),(179.5,1.5),(179.5,.5)]]))
expected = analytic_rectangle(179,0,181,2)-analytic_rectangle(179.5,.5,180.5,1.5)
assert math.isclose(area(crossing), expected, rel_tol=1e-13)
assert math.isclose(area(box(0,0,1e-6,1e-6)), .012309072079294861, rel_tol=1e-12)
print({'checks':'WGS84 analytic rectangles, symmetry, ring direction, holes, antimeridian, tiny parcels and 300 convergence comparisons passed','max_16_vs_32_relative_drift':max_quadrature_drift,'max_dense_geodesic_relative_drift':max_geodesic_drift})
