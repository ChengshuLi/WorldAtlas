"""Randomized comparison of batched and prior per-component boundary scans."""

import tempfile, unittest, json
from pathlib import Path
import numpy as np
from map_build.water.closed_water_core import policy
from map_build.water.tests import closed_water_reference as ref
from map_build.water import streaming_closed_water as stream
from map_build.water.tests.test_closed_water_core import policy_snapshot
from map_build.water.tests.helpers import rle


class BoundaryEquivalence(unittest.TestCase):
    def test_randomized_rows_cuts_and_wrap(self):
        _, pairs, _ = policy(policy_snapshot())
        for seed in range(40):
            rng = np.random.default_rng(seed)
            h, w = 12, 24
            p = np.where(rng.random((h, w)) < 0.45, 17, 1).astype(np.uint32)
            q = np.where(p == 17, rng.integers(17, 23, (h, w)), rng.integers(0, 7, (h, w))).astype(
                np.uint32
            )
            # Assign every residual water cell an arbitrary root; adjacent roots model cuts.
            roots = rng.integers(0, 9, (h, w))
            by = {}
            allroots = set()
            for y in range(h):
                row = []
                x = 0
                while x < w:
                    if p[y, x] != 1 or q[y, x] != 0:
                        x += 1
                        continue
                    a = x
                    root = int(roots[y, x])
                    x += 1
                    while x < w and p[y, x] == 1 and q[y, x] == 0 and roots[y, x] == root:
                        x += 1
                    row.append((a, x, root))
                    allroots.add(root)
                if row:
                    by[y] = row
            _, expected = ref.adjacency(by, rle(p), rle(q), w, h, pairs)
            with tempfile.TemporaryDirectory() as d:
                db = stream.open_database(Path(d) / 'work.sqlite')
                try:
                    db.executemany(
                        'INSERT INTO components(root,expected,reported_cut) VALUES(?,1,0)',
                        [(r,) for r in allroots],
                    )
                    db.executemany(
                        'INSERT INTO spans VALUES(?,?,?,?)',
                        [(y, a, b, r) for y, rows in by.items() for a, b, r in rows],
                    )
                    stream.classify_boundaries(db, rle(p), rle(q), w, h, pairs, batch_cells=7)
                    actual = {
                        r: (set(json.loads(entities)), unknown, crop)
                        for r, entities, unknown, crop in db.execute(
                            'SELECT root,boundary_entities,unknown,crop_edge FROM components'
                        )
                    }
                    for root, rec in expected.items():
                        self.assertEqual(
                            actual[root],
                            (
                                set(rec['codes']),
                                int(rec['unknown_zero_edges'] > 0),
                                int(rec['crop_edge']),
                            ),
                            f'seed {seed}, root {root}',
                        )
                finally:
                    db.close()


if __name__ == '__main__':
    unittest.main()
