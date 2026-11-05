import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from refine_asia_oceania import open_ocean_baseline


class AsiaOceaniaAlgorithmTest(unittest.TestCase):
    def test_ocean_fallback_preserves_verified_parent(self):
        actual = open_ocean_baseline(
            np.array([8, 8, 9, 2, 6]),
            np.array([False, False, False, False, True]),
        )
        self.assertEqual(actual.tolist(), [8, 8, 9, 8, 9])


if __name__ == '__main__':
    unittest.main()
