import math, random, unittest
import numpy as np
from map_build.core.distances import run_pair, run_pairs_batch


class RunPairBatchTests(unittest.TestCase):
    def test_matches_individual_wgs84_results_random_and_seams(self):
        rng = random.Random(61724)
        width = 360
        records = []
        for _ in range(200):
            row = rng.randrange(180)
            start = rng.randrange(width)
            end = min(width, start + rng.randrange(1, 35))
            records.append((row, start, end, rng.randrange(17, 23)))
        for y, a, b, upper in [
            (0, 0, 1, 1e7),
            (179, 359, 360, 2e7),
            (90, 0, 30, 1e6),
            (100, 330, 360, 2e7),
            (30, 5, 60, 1e5),
        ] + [
            (rng.randrange(180), rng.randrange(340), rng.randrange(340, 361), rng.uniform(1e4, 2e7))
            for _ in range(15)
        ]:
            want = {}
            for yy, c, d, code in records:
                v, _ = run_pair(y, a, b, yy, c, d, width, incumbent=upper, tol=1e-5)
                if v is not None:
                    want[code] = min(want.get(code, math.inf), v)
            got, n = run_pairs_batch(
                y, a, b, np.array(records, dtype=np.uint32), width, incumbent=upper, tol=1e-5
            )
            self.assertEqual(n, len(records))
            self.assertEqual(set(got), set(want))
            for code in want:
                self.assertAlmostEqual(got[code], want[code], places=7)

    def test_empty_records_and_reject_bad_inputs(self):
        self.assertEqual(run_pairs_batch(0, 0, 1, [], 360, incumbent=1), ({}, 0))
        with self.assertRaises(ValueError):
            run_pairs_batch(0, 0, 1, [(0, 1, 2, 0)], 360, incumbent=1)
        with self.assertRaises(ValueError):
            run_pairs_batch(0, 0, 1, [(0, 1, 2, 17)], 360, incumbent=math.inf)


if __name__ == '__main__':
    unittest.main()
