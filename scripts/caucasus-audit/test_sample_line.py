import unittest
import sample_line


class SamplingTest(unittest.TestCase):
    def test_generates_and_validates(self):
        result = sample_line.generate([[1, 1], [1.01, 1]], 0, 1, 7, 500, 32631)
        features = result['features']
        self.assertGreaterEqual(len(features), 2)
        self.assertEqual(features[0]['properties']['source_edge_index'], 0)
        self.assertEqual(features[0]['properties']['section'], 7)
        self.assertAlmostEqual(features[1]['properties']['distance_along_section_m'], 500)
        with self.assertRaises(ValueError):
            sample_line.generate([[1, 1], [1, 1]], 0, 1, 7, 500, 32631)
        with self.assertRaises(ValueError):
            sample_line.generate([[1, 1], [1.01, 1]], 0, 1, 7, 0, 32631)


if __name__ == '__main__':
    unittest.main()
