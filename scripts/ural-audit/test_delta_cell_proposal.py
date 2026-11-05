import unittest
import numpy as np
from delta_cell_proposal import propose


class DeltaCellProposalTest(unittest.TestCase):
    def test_splits_component_and_rejects_stale_candidate(self):
        rows = np.array([0, 3], dtype=np.uint32)
        candidate = np.array([1, 19, 2, 18, 3, 19], dtype=np.uint32)
        physical_rows = np.array([0, 1], dtype=np.uint32)
        physical = np.array([3, 17], dtype=np.uint32)
        screen = {'differences': {'asia_labeled_europe': [{'x': 0, 'y': 0, 'distance_m': 5}],
                                  'europe_labeled_asia': [{'x': 1, 'y': 0, 'distance_m': 6}]},
                  'summary': {'asia_labeled_europe': {'count': 1}, 'europe_labeled_asia': {'count': 1}}}
        cells = propose(screen, rows, candidate, physical_rows, physical, 3, 1, 1)
        self.assertEqual([(c['x'], c['from'], c['to']) for c in cells], [(0, 19, 18), (1, 18, 19)])
        candidate[1] = 18
        with self.assertRaisesRegex(ValueError, 'candidate label'):
            propose(screen, rows, candidate, physical_rows, physical, 3, 1, 1)


if __name__ == '__main__': unittest.main()
