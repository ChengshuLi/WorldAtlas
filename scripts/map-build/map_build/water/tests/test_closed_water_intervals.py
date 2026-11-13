"""Sparse enclosed-water stencils and exact interval assignment parity."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from map_build.water import shared_nearest as shore
from map_build.water import streaming_closed_water as stream


class ClosedIntervalTests(unittest.TestCase):
    pairs = [('first', 17, 1), ('second', 18, 2)]

    def test_mixed_assignment_preserves_point_results_and_chunk_boundaries(self):
        rng = np.random.default_rng(9407)
        lats = rng.uniform(-89, 89, 60)
        lons = rng.uniform(-180, 180, 60)
        centers = {
            'lat': lats,
            'lon': lons,
            'mids': shore.unit(lats, lons),
            'category': np.tile(np.array([17, 18], dtype=np.uint8), 30),
        }
        indexes = shore.make_indexes(centers, self.pairs)
        source = [
            (y, a, b) for y in (0, 1, 89, 90, 178, 179) for a, b in ((0, 77), (92, 350), (355, 360))
        ]
        for chunk in (7, 5000):
            db = stream.open_database(':memory:')
            self.addCleanup(db.close)
            expected = sum(b - a for _, a, b in source)
            db.execute(
                "INSERT INTO components(root,expected,reported_cut,boundary_entities) VALUES(1,?,0,?)",
                (expected, '["first","second"]'),
            )
            db.executemany('INSERT INTO spans VALUES(?,?,?,1)', source)
            reference = []
            for y, a, b in source:
                for start in range(a, b, chunk):
                    stop = min(start + chunk, b)
                    xs = np.arange(start, stop)
                    codes = shore.classify(
                        np.full(len(xs), 90 - (y + 0.5)),
                        -180 + (xs + 0.5),
                        (0, 360, 0, 180),
                        360,
                        180,
                        1.0,
                        self.pairs,
                        1e-5,
                        indexes,
                    )[0]
                    cuts = np.r_[0, np.flatnonzero(np.diff(codes) != 0) + 1, len(codes)]
                    reference.extend(
                        (y, start + int(i), start + int(j), int(codes[i]), 1)
                        for i, j in zip(cuts[:-1], cuts[1:])
                    )
            with tempfile.TemporaryDirectory() as td, patch.object(
                shore, 'centers_for_crop', return_value=centers
            ):
                result = stream.assign_components(
                    db,
                    None,
                    None,
                    360,
                    180,
                    self.pairs,
                    1e-5,
                    180.0,
                    chunk,
                    Path(td) / 'pending.gz',
                )
            actual = list(db.execute('SELECT y,a,b,code,root FROM mixed ORDER BY y,a'))
            self.assertEqual(actual, reference)
            self.assertEqual((result['mixed_components'], result['assigned_cells']), (1, expected))

    def test_billion_cell_stencil_never_expands_to_dense_rows_or_points(self):
        width = 1_000_000_000
        rows = np.array([0, 1, 4, 5], dtype=np.uint32)
        physical = (
            rows,
            np.array([width, 17, 1, 17, width - 1, 1, width, 17, width, 17], dtype=np.uint32),
        )
        prefill = (
            rows,
            np.array([width, 17, 1, 17, width - 1, 0, width, 17, width, 17], dtype=np.uint32),
        )
        db = stream.open_database(':memory:')
        self.addCleanup(db.close)
        db.execute('INSERT INTO components(root,expected,reported_cut) VALUES(1,?,0)', (width - 2,))
        db.execute('INSERT INTO spans VALUES(1,1,?,1)', (width - 1,))
        with patch.object(shore, 'crop', side_effect=AssertionError('dense crop')), patch.object(
            np, 'arange', side_effect=AssertionError('per-cell expansion')
        ):
            stream.classify_boundaries(db, physical, prefill, width, 3, self.pairs)
        self.assertEqual(
            db.execute('SELECT boundary_entities,unknown,crop_edge FROM components').fetchone(),
            ('["first"]', 0, 0),
        )


if __name__ == '__main__':
    unittest.main()
