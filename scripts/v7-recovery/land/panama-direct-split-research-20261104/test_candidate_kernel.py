import tempfile
import unittest
from pathlib import Path
import numpy as np
from candidate_kernel import TripleRows, rasterize_barriers

class CandidateKernelTests(unittest.TestCase):
    def test_triple_rows_reads_bounded_offsets(self):
        with tempfile.TemporaryDirectory() as td:
            rows = Path(td) / 'rows.u32le'
            spans = Path(td) / 'spans.u32le'
            np.array([0, 2], dtype='<u4').tofile(rows)
            np.array([[0, 2, 7], [2, 4, 8]], dtype='<u4').tofile(spans)
            stream = TripleRows(rows, spans, 1)
            self.assertEqual(stream.row(0).tolist(), [[0, 2, 7], [2, 4, 8]])
            with self.assertRaisesRegex(ValueError, 'row out of range'):
                stream.row(1)
            stream.close()

    def test_grid_edge_barrier_is_topological_only(self):
        cuts = rasterize_barriers([[(0.2, 0.2), (2.8, 2.8)]], 4, 4)
        self.assertTrue(cuts.horizontal or cuts.vertical)

if __name__ == '__main__':
    unittest.main()
