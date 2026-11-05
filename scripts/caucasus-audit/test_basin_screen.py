import unittest
from types import SimpleNamespace

from basin_screen import run, terminal


class DownstreamTests(unittest.TestCase):
    def test_chain_and_shared_outlet(self):
        rows = {1: {'NEXT_DOWN': 3}, 2: {'NEXT_DOWN': 3}, 3: {'NEXT_DOWN': 0}}
        self.assertEqual(terminal(rows, 1), 3)
        self.assertEqual(terminal(rows, 2), 3)

    def test_cycle_and_missing_record_are_unresolved(self):
        rows = {1: {'NEXT_DOWN': 2}, 2: {'NEXT_DOWN': 1},
                3: {'NEXT_DOWN': 99}}
        self.assertIsNone(terminal(rows, 1))
        self.assertIsNone(terminal(rows, 3))

    def test_geographic_crs_is_rejected(self):
        with self.assertRaises(ValueError):
            run(SimpleNamespace(epsg=4326))


if __name__ == '__main__':
    unittest.main()
