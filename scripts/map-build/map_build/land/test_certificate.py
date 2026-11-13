import unittest, math, numpy as np
from unittest.mock import patch
from map_build.land.certificates import CertificateIndex
from pyproj import Geod

G = Geod(ellps='WGS84')


def build(seeds, w=360):
    # One grid cell per tile; every seed itself is a representative.
    tiles = [(y, x, [code]) for y, x, code in seeds]
    return CertificateIndex(w, w // 2, 360 / w, 90, tiles, seeds, tile_cells=1)


def brute(runs, seeds, w=360, tol=0.001):
    step = 360 / w
    best = {}
    for y, a, b in runs:
        for x in range(a, b):
            for yy, xx, c in seeds:
                d = G.inv(
                    -180 + (x + 0.5) * step,
                    90 - (y + 0.5) * step,
                    -180 + (xx + 0.5) * step,
                    90 - (yy + 0.5) * step,
                )[2]
                best[c] = min(best.get(c, math.inf), d)
    z = min(best.values())
    return {c for c, d in best.items() if d <= z + tol}


class Cert(unittest.TestCase):
    def check(self, seeds, runs, hint, w=360, force_cert=False):
        idx = build(seeds, w)
        upper, _ = idx.witnesses([runs[0][0]], [runs[0][1]], [hint])
        a = np.asarray(runs)
        ok = idx.certify_runs(
            a[:, 0], a[:, 1], a[:, 2], np.full(len(a), upper[0]), np.full(len(a), hint), 0.001
        )
        if np.all(ok):
            self.assertEqual(brute(runs, seeds, w), {hint})
        if force_cert:
            self.assertTrue(np.all(ok))

    def test_far_separated(self):
        self.check(
            [
                (60, 12, 17),
                (60, 60, 18),
                (60, 120, 19),
                (60, 180, 20),
                (60, 240, 21),
                (60, 300, 22),
            ],
            [(60, 11, 12)],
            17,
            force_cert=True,
        )

    def test_missed_category_hint(self):
        seeds = [
            (60, 12, 17),
            (60, 60, 18),
            (60, 120, 19),
            (60, 180, 20),
            (60, 240, 21),
            (60, 300, 22),
        ]
        self.check(seeds, [(60, 11, 12)], 20)
        x = build(seeds)
        u, _ = x.witnesses([60], [11], [20])
        self.assertFalse(x.certify_runs([60], [11], [12], u, [20], 0.001)[0])

    def test_competitor_only_last_run(self):
        seeds = [
            (60, 12, 17),
            (60, 60, 18),
            (60, 120, 19),
            (60, 180, 20),
            (60, 240, 21),
            (60, 300, 22),
        ]
        x = build(seeds)
        u, _ = x.witnesses([60], [11], [17])
        z = x.certify_runs([60, 60], [11, 60], [12, 61], [u[0], u[0]], [17, 17], 0.001)
        self.assertTrue(z[0])
        self.assertFalse(z[1])

    def test_dateline_pole_and_tie(self):
        self.check(
            [(0, 359, 17), (0, 1, 18), (45, 90, 19), (45, 180, 20), (90, 270, 21), (150, 200, 22)],
            [(0, 0, 1)],
            17,
        )
        self.check(
            [
                (90, 179, 17),
                (90, 181, 18),
                (45, 90, 19),
                (45, 180, 20),
                (90, 270, 21),
                (150, 200, 22),
            ],
            [(90, 180, 181)],
            17,
        )

    def test_random_multirun(self):
        rng = np.random.default_rng(2309)
        for i in range(100):
            w = 36
            seeds = [(int(rng.integers(18)), int(rng.integers(w)), 17 + j) for j in range(6)]
            runs = []
            for _ in range(3):
                y = int(rng.integers(18))
                x = int(rng.integers(w - 1))
                runs.append((y, x, min(w, x + int(rng.integers(1, 4)))))
            self.check(seeds, runs, 17 + i % 6, w)

    def test_bad_guard_fails_closed(self):
        with self.assertRaises(ValueError):
            CertificateIndex(360, 180, 1, 90, [], [], tile_cells=1, numerical_guard_m=0)

    def test_hierarchy_only_refines_queries_that_coarse_bounds_cannot_prove(self):
        seeds = [
            (60, 12, 17),
            (60, 60, 18),
            (60, 120, 19),
            (60, 180, 20),
            (60, 240, 21),
            (60, 300, 22),
        ]
        fine = build(seeds)
        tiles = [(y // 16, x // 16, [code]) for y, x, code in seeds]
        coarse = CertificateIndex(360, 180, 1, 90, tiles, seeds, tile_cells=16)
        hierarchy = CertificateIndex(360, 180, 1, 90, tiles, seeds, tile_cells=16, refinement=fine)
        rows = np.full(30, 60)
        starts = np.arange(1, 31)
        ends = starts + 1
        hints = np.full(30, 17)
        upper = coarse.witnesses(rows, starts, hints)[0]
        known = coarse.certify_runs(rows, starts, ends, upper, hints, 0.001)
        refined = fine.certify_runs(rows, starts, ends, upper, hints, 0.001)
        self.assertTrue(known.any())
        self.assertTrue((~known).any())
        with patch.object(fine, '_certify_points', wraps=fine._certify_points) as search:
            actual = hierarchy.certify_runs(rows, starts, ends, upper, hints, 0.001)
            np.testing.assert_array_equal(actual, known | refined)
            self.assertEqual(len(search.call_args.args[0]), int((~known).sum()))
            candidates = search.call_args.args[-1]
            self.assertLess(int(candidates.sum()), len(candidates) * 5)
        with self.assertRaisesRegex(ValueError, 'invalid certificate refinement'):
            CertificateIndex(720, 360, 0.5, 90, [], [], refinement=fine)


if __name__ == '__main__':
    unittest.main()
