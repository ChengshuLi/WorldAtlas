import math, random, unittest
import numpy as np
from worldatlas.geodesy.wgs84 import MIN_RADIUS, geodesic_distances
from worldatlas.map_build.core.distances import (
    DISTANCE_BOUND_ROUNDING_METRES,
    run_pairs_batch,
)


def reference_run_pair(y, a, b, yy, c, d, width, incumbent):
    """Calculate one run pair by enumerating its unique longitude gaps."""
    step = 360 / width
    lat1 = 90 - (y + 0.5) * step
    lat2 = 90 - (yy + 0.5) * step
    diffs = np.arange(c - (b - 1), (d - 1) - a + 1, dtype=np.int64)
    mod = diffs % width
    gaps = np.unique(np.minimum(mod, width - mod))
    dl = np.deg2rad(gaps * step)
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    xx = math.cos(p2) * np.sin(dl)
    yy0 = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * np.cos(dl)
    dot = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * np.cos(dl)
    angles = np.arctan2(np.hypot(xx, yy0), dot)
    keep = np.flatnonzero(
        angles * MIN_RADIUS <= incumbent + DISTANCE_BOUND_ROUNDING_METRES
    )
    if not len(keep):
        return None
    return float(geodesic_distances(0.0, lat1, gaps[keep] * step, lat2).min())


class RunPairBatchTests(unittest.TestCase):
    def test_validates_runs_and_latitudes(self):
        cases = (
            ("invalid runs", 2, 1, [(0, 1, 2, 17)]),
            ("invalid runs", 0, 1, [(0, 1, 2, 0)]),
            ("invalid records", 0, 1, [(0, 1, 2)]),
            ("invalid latitude", 0, 1, [(180, 1, 2, 17)]),
        )
        for error, start, stop, records in cases:
            with self.subTest(records=records), self.assertRaisesRegex(ValueError, error):
                run_pairs_batch(0, start, stop, records, 360, incumbent=1e7)
        self.assertEqual(run_pairs_batch(0, 0, 1, [], 360, incumbent=1e7), ({}, 0))

    def test_distance_bound_can_prune_every_run(self):
        self.assertEqual(
            run_pairs_batch(0, 0, 1, [(100, 0, 1, 17)], 360, incumbent=0),
            ({}, 1),
        )

    def test_bound_prunes_a_candidate_hundreds_of_metres_past_the_best(self):
        y, width = 32768, 131072
        records = [(y, 0, 1, 17), (y, 1, 2, 18)]
        self.assertEqual(
            run_pairs_batch(y, 0, 1, records, width, incumbent=0),
            ({17: 0.0}, 2),
        )

    def test_bound_keeps_a_tied_candidate_when_a_near_equator_bound_rounds_up(self):
        width = 2**32 - 1
        source_row, reference_row = 1073741799, 1073741804
        step = 360 / width
        distance = float(geodesic_distances(
            0, 90 - (source_row + 0.5) * step,
            0, 90 - (reference_row + 0.5) * step,
        ))
        self.assertEqual(
            run_pairs_batch(
                source_row, 0, 1, [(reference_row, 0, 1, 17)], width,
                incumbent=distance,
            ),
            ({17: distance}, 1),
        )

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
            (
                rng.randrange(180),
                rng.randrange(340),
                rng.randrange(340, 361),
                rng.uniform(1e4, 2e7),
            )
            for _ in range(15)
        ]:
            want = {}
            for yy, c, d, code in records:
                v = reference_run_pair(y, a, b, yy, c, d, width, upper)
                if v is not None:
                    want[code] = min(want.get(code, math.inf), v)
            got, n = run_pairs_batch(
                y, a, b, np.array(records, dtype=np.uint32), width, incumbent=upper
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


if __name__ == "__main__":
    unittest.main()
