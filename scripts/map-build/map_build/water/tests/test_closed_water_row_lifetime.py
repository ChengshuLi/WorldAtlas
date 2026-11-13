"""Boundary row storage follows the geometric stencil, not scan history."""

import collections
import json
import struct
import tempfile
import unittest
import weakref
from pathlib import Path
from unittest.mock import patch

import numpy as np
from map_build.water import closed_water_core as reference
from map_build.water import streaming_closed_water as stream
from map_build.water.tests.helpers import rle


class RowDatabase:
    def __init__(self, db):
        self.db = db
        self.row = None
        self.reads = collections.Counter()

    def execute(self, sql, args=()):
        if sql.startswith('SELECT a,b,root FROM spans WHERE y='):
            self.row = args[0]
            self.reads[self.row] += 1
        return self.db.execute(sql, args)

    def executemany(self, *args):
        return self.db.executemany(*args)


class RowLifetimeTests(unittest.TestCase):
    pairs = [(i, 17 + i, 1 + i) for i in range(6)]

    def test_dense_and_sparse_stencils_release_consumed_rows(self):
        for selected in (range(40), (2, 3, 20, 39)):
            with self.subTest(selected=selected):
                height, width = 40, 31
                physical = np.full((height, width), 17, dtype=np.uint32)
                prefill = physical.copy()
                by_row = {}
                for y in selected:
                    physical[y, 15] = 1
                    prefill[y, 15] = 0
                    by_row[y] = [(15, 16, y)]
                db = stream.open_database(':memory:')
                self.addCleanup(db.close)
                db.executemany(
                    'INSERT INTO components(root,expected,reported_cut) VALUES(?,1,0)',
                    [(y,) for y in selected],
                )
                db.executemany(
                    'INSERT INTO spans VALUES(?,?,?,?)',
                    [(y, a, b, root) for y, spans in by_row.items() for a, b, root in spans],
                )
                tracked = RowDatabase(db)
                dense_refs, index_refs = [], []
                crop, fromiter = stream.core.shore.crop, np.fromiter

                def check_stencil(refs):
                    live = {y for y, ref in refs if ref() is not None}
                    self.assertLessEqual(max(live) - min(live), 2)

                def observe_crop(rows, runs, y, *args):
                    result = crop(rows, runs, y, *args)
                    dense_refs.append((y, weakref.ref(result)))
                    check_stencil(dense_refs)
                    return result

                def observe_index(*args, **kwargs):
                    result = fromiter(*args, **kwargs)
                    index_refs.append((tracked.row, weakref.ref(result)))
                    check_stencil(index_refs)
                    return result

                with patch.object(stream.core.shore, 'crop', observe_crop), patch.object(
                    np, 'fromiter', observe_index
                ):
                    stream.classify_boundaries(
                        tracked,
                        rle(physical),
                        rle(prefill),
                        width,
                        height,
                        self.pairs,
                        batch_cells=1,
                    )
                self.assertTrue(all(ref() is None for _, ref in dense_refs + index_refs))
                self.assertTrue(all(count == 1 for count in tracked.reads.values()))
                _, expected = reference.adjacency(
                    by_row, rle(physical), rle(prefill), width, height, self.pairs
                )
                actual = {
                    root: (set(json.loads(entities)), unknown, crop_edge)
                    for root, entities, unknown, crop_edge in db.execute(
                        'SELECT root,boundary_entities,unknown,crop_edge FROM components'
                    )
                }
                self.assertEqual(
                    actual,
                    {
                        root: (
                            set(value['codes']),
                            int(value['unknown_zero_edges'] > 0),
                            int(value['crop_edge']),
                        )
                        for root, value in expected.items()
                    },
                )

    def test_cut_scan_reuses_only_current_endpoint_rows_across_kind_resets(self):
        height, width = 40, 5
        by_row = {y: [(0, width, y)] for y in range(height)}
        records = (
            [(0, y, x) for y in range(height) for x in (0, 2)]
            + [(1, y, x) for y in range(height - 1) for x in (0, 2)]
            + [(2, y, 0) for y in range(height)]
        )
        db = stream.open_database(':memory:')
        self.addCleanup(db.close)
        db.executemany(
            'INSERT INTO components(root,expected,reported_cut) VALUES(?,?,1)',
            [(y, width) for y in range(height)],
        )
        db.executemany(
            'INSERT INTO spans VALUES(?,?,?,?)', [(y, 0, width, y) for y in range(height)]
        )
        tracked = RowDatabase(db)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cuts.u32le'
            path.write_bytes(b''.join(struct.pack('<III', *record) for record in records))
            stream.mark_cut_contacts(tracked, path, width, height, batch_size=3)
        expected = reference.cut_contacts(by_row, records, width, height)
        self.assertEqual(
            dict(db.execute('SELECT root,cut FROM components')),
            {root: int(count > 0) for root, count in expected.items()},
        )
        # All rows are revisited for each kind. An all-history cache would
        # incorrectly retain their indexes instead of releasing consumed rows.
        self.assertEqual(tracked.reads, {y: 3 for y in range(height)})


if __name__ == '__main__':
    unittest.main()
