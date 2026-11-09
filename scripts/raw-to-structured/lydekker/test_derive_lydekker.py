import importlib.util
import json
import tempfile
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('derive', Path(__file__).with_name('derive_lydekker.py'))
derive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(derive)


class DerivationTests(unittest.TestCase):
    def test_straight_line_preserves_endpoints_and_order(self):
        coords = [[10., 1.], [9., 0.], [8., -1.]]
        actual = derive.smooth(coords)
        self.assertEqual(actual[0], coords[0])
        self.assertEqual(actual[-1], coords[-1])
        self.assertTrue(all(a[1] > b[1] for a, b in zip(actual, actual[1:])))
        self.assertEqual(len(actual), 2001)

    def test_smoothing_reduces_corner_and_keeps_endpoints(self):
        coords = [[0., 1.], [1., 0.], [0., -1.]]
        result = derive.smooth(coords)
        self.assertEqual(result[0], coords[0])
        self.assertEqual(result[-1], coords[-1])
        self.assertLess(result[len(result)//2][0], 1.)
        self.assertGreater(result[len(result)//2][0], 0.)

    def test_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'wrong.json'
            path.write_text(json.dumps({'geometry': {'type': 'MultiLineString', 'coordinates': []}}))
            with self.assertRaises(ValueError):
                derive.read_observation(path)


if __name__ == '__main__':
    unittest.main()
