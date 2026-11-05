import random
import struct
import tempfile
import unittest
from pathlib import Path
from audit_existing_predicates import Grid, spans


class SparseMembershipTests(unittest.TestCase):
    def test_randomized_span_roundtrip_preserves_every_label(self):
        rng = random.Random(741)
        for _ in range(100):
            cells = []
            for y in range(5):
                for x in range(30):
                    if rng.random() < .5:
                        a = rng.choice([18,19])
                        cells.append([x,y,a,37-a,rng.choice([18,19]),rng.choice([0,18,19])])
            rng.shuffle(cells)
            restored = [[x,y,*labels] for y,a,b,*labels in spans(cells) for x in range(a,b)]
            self.assertEqual(sorted(cells),sorted(restored))

    def test_rle_boundaries_and_membership_zero(self):
        with tempfile.TemporaryDirectory() as d:
            rows, runs = Path(d)/'rows', Path(d)/'runs'
            rows.write_bytes(struct.pack('<III',0,2,4))
            runs.write_bytes(struct.pack('<8I',2,19,4,0,1,0,4,18))
            g = Grid(rows,runs,4,2)
            self.assertEqual([g.at(x,0) for x in range(4)],[19,19,0,0])
            self.assertEqual([g.at(x,1) for x in range(4)],[0,18,18,18])
            with self.assertRaises(ValueError): g.at(4,0)
            g.data.close(); g.file.close()

    def test_bad_queried_row_fails(self):
        with tempfile.TemporaryDirectory() as d:
            rows, runs = Path(d)/'rows', Path(d)/'runs'
            rows.write_bytes(struct.pack('<II',0,2))
            runs.write_bytes(struct.pack('<4I',2,19,2,18))
            g = Grid(rows,runs,4,1)
            with self.assertRaises(ValueError): g.at(1,0)
            g.data.close(); g.file.close()


if __name__ == '__main__': unittest.main()
