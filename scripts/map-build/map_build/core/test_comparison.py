from pathlib import Path
import tempfile
import unittest

import numpy as np

from map_build.core.comparison import compare
from map_build.core.grid import Grid
from map_build.core.layers import file_hash, write_layer


class ComparisonTests(unittest.TestCase):
    def test_exact_changed_spans_and_row_offsets(self):
        grid = Grid(4, 2, 90.)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_layer(root/'before', grid, [(0, [(0, 4, 81)]), (1, [(0, 4, 81)])])
            write_layer(root/'after', grid, [(0, [(0, 1, 81), (1, 3, 70000), (3, 4, 81)]),
                                            (1, [(0, 4, 81)])])
            hashes = {name: file_hash(root/'before'/name) for name in ('rows.u32le', 'runs.u32le')}
            report = compare(root/'after', root/'before', grid, root/'diff', hashes)
            self.assertEqual(report['changed_cells'], 2)
            self.assertEqual(report['pair_counts'], {'81->70000': 2})
            self.assertEqual(np.fromfile(root/'diff/changes.u32le', dtype='<u4').tolist(),
                             [0, 1, 3, 81, 70000])
            self.assertEqual(np.fromfile(root/'diff/change-rows.u64le', dtype='<u8').tolist(), [0, 1, 1])
            same = compare(root/'before', root/'before', grid, root/'same', hashes)
            self.assertTrue(same['byte_identical'])
            self.assertEqual(same['changed_cells'], 0)
            self.assertEqual((root/'same/changes.u32le').stat().st_size, 0)
