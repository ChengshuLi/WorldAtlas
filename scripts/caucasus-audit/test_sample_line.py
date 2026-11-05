import unittest
import sample_line
from geodesic_tools import GEOD, METHOD, transformer


class SamplingTest(unittest.TestCase):
    def test_generates_and_validates(self):
        result = sample_line.generate([[1, 1], [1.01, 1]], 0, 1, 7, 500, 32631)
        self.assertEqual(result['distance_method'],METHOD)
        features = result['features']
        self.assertGreaterEqual(len(features), 2)
        self.assertEqual(features[0]['properties']['source_edge_index'], 0)
        self.assertEqual(features[0]['properties']['section'], 7)
        self.assertAlmostEqual(features[1]['properties']['distance_along_section_m'], 500)
        a=features[0]['geometry']['coordinates'];b=features[1]['geometry']['coordinates']
        self.assertAlmostEqual(GEOD.inv(*a,*b)[2],500,delta=.01)
        with self.assertRaises(ValueError):
            sample_line.generate([[1, 1], [1, 1]], 0, 1, 7, 500, 32631)
        with self.assertRaises(ValueError):
            sample_line.generate([[1, 1], [1.01, 1]], 0, 1, 7, 0, 32631)

    def test_source_projection_geometry_is_preserved(self):
        line=[[1,1],[1.1,1.05]];result=sample_line.generate(line,0,1,3,500,32631)
        forward,_=transformer(32631);a=forward.TransformPoint(*line[0]);b=forward.TransformPoint(*line[1])
        for feature in result['features']:
            p=forward.TransformPoint(*feature['geometry']['coordinates']);cross=(p[0]-a[0])*(b[1]-a[1])-(p[1]-a[1])*(b[0]-a[0])
            self.assertLess(abs(cross),.01)

    def test_equal_vertex_sample_uses_preceding_edge(self):
        line=[[0,0],[.01,0],[.02,0]];spacing=GEOD.inv(*line[0],*line[1])[2]
        result=sample_line.generate(line,0,2,3,spacing,3857)
        self.assertEqual(result['features'][1]['properties']['source_edge_index'],0)


if __name__ == '__main__':
    unittest.main()
