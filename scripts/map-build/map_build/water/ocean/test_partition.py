from pathlib import Path
import tempfile
import unittest

from map_build.water.ocean.partition_core import CutEdges, floodfill_run_graph


class OceanPartitionTests(unittest.TestCase):
    def test_nonconsecutive_seed_codes_appear_in_counts_and_streams(self):
        def eligible(y):
            return [(0, 2), (3, 5)]
        with tempfile.TemporaryDirectory() as directory:
            result = floodfill_run_graph(eligible, 6, 2, CutEdges(),
                                        {81: (0, 0), 70000: (3, 0)}, Path(directory)/'partition')
            self.assertEqual(result['assigned_cells_by_ocean_code'], {'81': 4, '70000': 4})
            self.assertEqual(result['assigned_cells_total'], 8)
            self.assertEqual(result['unseeded_cell_count'], 0)
