import unittest
import numpy as np
from map_build.water import streaming_closed_water as s


def rle(values):
    values = np.asarray(values, dtype=np.uint32)
    ends = np.flatnonzero(np.r_[values[1:] != values[:-1], True]) + 1
    rows = np.asarray([0, len(ends)], dtype=np.uint64)
    runs = np.asarray(
        [item for i, end in enumerate(ends) for item in (int(end), int(values[end - 1]))],
        dtype=np.uint32,
    )
    return rows, runs


class ClassCodeDomainTests(unittest.TestCase):
    def test_all_supported_and_invalid_physical_prefill_pairs(self):
        pairs = [(i, 17 + i, 1 + i) for i in range(6)]
        values = list(range(23)) + [23, 255, 2**32 - 1]
        cases = valid = 0
        for physical_neighbor in values:
            for prefill_neighbor in values:
                allowed = (physical_neighbor == 1 and prefill_neighbor in [0, *range(1, 7)]) or (
                    physical_neighbor == 17 and prefill_neighbor in range(17, 23)
                )
                db = s.open_database(':memory:')
                db.execute('INSERT INTO components(root,expected,reported_cut) VALUES(1,1,0)')
                db.execute('INSERT INTO spans(y,a,b,root) VALUES(0,0,1,1)')
                try:
                    s.classify_boundaries(
                        db, rle([1, physical_neighbor]), rle([0, prefill_neighbor]), 2, 1, pairs
                    )
                    self.assertTrue(allowed, (physical_neighbor, prefill_neighbor))
                    valid += 1
                except ValueError as exc:
                    self.assertFalse(allowed, (physical_neighbor, prefill_neighbor, str(exc)))
                finally:
                    db.close()
                cases += 1
        self.assertEqual(cases, 676)
        self.assertEqual(valid, 13)

    def test_negative_signed_codes_are_rejected_before_lookup(self):
        pairs = [(0, 17, 1), (1, 18, 2)]
        cases = [
            (np.array([-6], dtype=np.int32), np.array([17], dtype=np.int32)),
            (np.array([17], dtype=np.int32), np.array([-6], dtype=np.int32)),
        ]
        for physical_row, prefill_row in cases:
            db = s.open_database(':memory:')
            db.execute('INSERT INTO components(root,expected,reported_cut) VALUES(1,1,0)')
            db.execute('INSERT INTO spans(y,a,b,root) VALUES(0,0,1,1)')
            rows = np.array([0, 1], dtype=np.uint32)
            physical = (rows, np.array([1, int(physical_row[0])], dtype=np.int32))
            prefill = (rows, np.array([1, int(prefill_row[0])], dtype=np.int32))
            with self.assertRaisesRegex(ValueError, 'physical/prefill relationship'):
                s.classify_boundaries(db, physical, prefill, 1, 1, pairs)
            db.close()


if __name__ == '__main__':
    unittest.main()
