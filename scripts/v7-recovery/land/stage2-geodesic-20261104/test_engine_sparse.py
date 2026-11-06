import unittest
import numpy as np
import engine


class SparseExactExpansionTests(unittest.TestCase):
    def setUp(self):
        # The first three component IDs are selected components, and 99 is a
        # seed component that must be validated but never exact-expanded.
        self.a = np.asarray([
            [0, 11, 10], [20, 25, 20], [40, 42, 99], [60, 73, 10],
            [80, 84, 20], [100, 104, 99], [0, 9, 10], [20, 27, 20],
        ], dtype=np.uint32)
        self.co = np.asarray([0, 6, 8], dtype=np.uint32)
        self.roots = np.asarray([10, 20, 30], dtype=np.uint32)
        self.seed_roots = np.asarray([99], dtype=np.uint32)
        self.amb = np.asarray([True, False, True])

    def test_sparse_expansion_matches_filtering_full_expansion(self):
        expected = []
        for ys, starts, ends, pos in engine.expanded(
            self.a, 0, self.co, self.roots, self.seed_roots, chunk=4, max_queries=128
        ):
            keep = self.amb[pos]
            expected.extend(a[keep] for a in (ys, starts, ends, pos))
        expected = [np.concatenate(expected[i::4]) for i in range(4)]
        actual = [[], [], [], []]
        for group in engine.expanded_ambiguous(
            self.a, 0, self.co, self.roots, self.seed_roots, self.amb,
            chunk=4, max_queries=128,
        ):
            for i, values in enumerate(group):
                actual[i].append(values)
        actual = [np.concatenate(parts) for parts in actual]
        for got, want in zip(actual, expected):
            np.testing.assert_array_equal(got, want)
        self.assertEqual(len(actual[0]), 10)  # only ID 10's 9 cells are expanded

    def test_long_single_run_is_streamed_without_loss(self):
        a = np.asarray([[0, 300, 10], [300, 302, 20]], dtype=np.uint32)
        co = np.asarray([0, 2], dtype=np.uint32)
        for function, extra in ((engine.expanded, ()), (engine.expanded_ambiguous, (np.asarray([True, True, False]),))):
            groups = list(function(a, 0, co, self.roots, self.seed_roots, *extra, chunk=1, max_queries=128))
            self.assertTrue(all(len(g[0]) <= 128 for g in groups))
            starts = np.concatenate([g[1] for g in groups]); ends = np.concatenate([g[2] for g in groups])
            np.testing.assert_array_equal(starts, np.arange(302)); np.testing.assert_array_equal(ends, np.arange(1, 303))
            np.testing.assert_array_equal(np.concatenate([g[3] for g in groups]), np.r_[np.zeros(300), np.ones(2)])

    def test_global_width_with_minimum_chunk(self):
        a = np.asarray([[0, 131072, 10]], dtype=np.uint32); co = np.asarray([0, 1], dtype=np.uint32)
        for size in (65536, 65535):
            groups = list(engine.expanded(a, 0, co, self.roots, self.seed_roots, chunk=1, max_queries=size))
            starts = np.concatenate([x[1] for x in groups]); ends = np.concatenate([x[2] for x in groups])
            np.testing.assert_array_equal(starts, np.arange(131072)); np.testing.assert_array_equal(ends, starts+1)
    def test_split_nondivisible_run_and_exact_batch_edge(self):
        a = np.asarray([[0, 385, 10], [385, 769, 20]], dtype=np.uint32); co = np.asarray([0, 2], dtype=np.uint32)
        groups = list(engine.expanded_ambiguous(a, 0, co, self.roots, self.seed_roots, np.asarray([True, True, False]), chunk=3, max_queries=128))
        starts = np.concatenate([x[1] for x in groups]); ends = np.concatenate([x[2] for x in groups]); pos = np.concatenate([x[3] for x in groups])
        np.testing.assert_array_equal(starts, np.r_[np.arange(0,385,3), np.arange(385,769,3)])
        np.testing.assert_array_equal(ends, np.r_[np.minimum(np.arange(0,385,3)+3,385), np.minimum(np.arange(385,769,3)+3,769)])
        self.assertEqual(pos.tolist(), [0]*129+[1]*128)

    def test_no_ambiguous_components_yields_no_queries(self):
        self.assertEqual(list(engine.expanded_ambiguous(
            self.a, 0, self.co, self.roots, self.seed_roots,
            np.zeros(3, dtype=bool), chunk=4, max_queries=128,
        )), [])

    def test_sparse_expansion_still_validates_unrecognized_ids(self):
        bad = self.a.copy()
        bad[0, 2] = 123456
        with self.assertRaises(ValueError):
            list(engine.expanded_ambiguous(
                bad, 0, self.co, self.roots, self.seed_roots, self.amb,
                chunk=4, max_queries=128,
            ))


if __name__ == '__main__':
    unittest.main()
