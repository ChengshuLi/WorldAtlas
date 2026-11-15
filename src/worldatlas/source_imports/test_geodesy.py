"""Check declared rhumb interpolation independently of source readers and map rasterization."""
import math
import unittest
from worldatlas.source_imports.geodesy import spherical_rhumb_points


class RhumbTests(unittest.TestCase):
    def test_endpoints_and_constant_mercator_bearing(self):
        points=[(-29.4122,68.2254),(-23.1371290446,66.4303932484)]
        dense=spherical_rhumb_points(points,1)
        self.assertEqual((dense[0],dense[-1]),tuple(points))
        psi=lambda lat:math.asinh(math.tan(math.radians(lat)))
        for point in dense:
            t=(point[0]-points[0][0])/(points[1][0]-points[0][0])
            self.assertAlmostEqual(psi(point[1]),psi(points[0][1])+t*(psi(points[1][1])-psi(points[0][1])),places=12)
        for ends,step in [([(179,30),(-179,30)],1),([(0,90),(1,80)],1),(points,0)]:
            with self.assertRaises(ValueError):spherical_rhumb_points(ends,step)

    def test_published_s130_middle_vertex_lies_on_declared_rhumb(self):
        first=(66.4303932484076,-23.137129044586)
        middle=(67.3328552063905,-26.2331485568407)
        last=(68.2254,-29.4122)
        psi=lambda lat:math.asinh(math.tan(math.radians(lat)))
        t=(middle[1]-first[1])/(last[1]-first[1])
        self.assertAlmostEqual(psi(middle[0]),psi(first[0])+t*(psi(last[0])-psi(first[0])),places=12)
