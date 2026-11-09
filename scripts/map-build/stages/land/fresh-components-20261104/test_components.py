"""Topology, stable root ordering, malformed streams and in-process execution."""
import itertools
from pathlib import Path
import random
import struct
import tempfile
import unittest
from unittest.mock import patch

import components


class ComponentsTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)

    def build(self, mask):
        width, height = len(mask[0]), len(mask)
        rows, runs = [0], []
        for row in mask:
            for _, group in itertools.groupby(enumerate(row), lambda cell: cell[1]):
                cells = list(group)
                runs.extend((cells[-1][0] + 1, 17 if cells[0][1] else 1))
            rows.append(len(runs) // 2)
        for name, values in [('rows', rows), ('runs', runs)]:
            (self.root / name).write_bytes(struct.pack('<' + 'I' * len(values), *values))
        for name in ('outrows', 'outruns'):
            (self.root / name).unlink(missing_ok=True)
        with patch('subprocess.Popen', side_effect=AssertionError('process launch')), \
                patch('ctypes.CDLL', side_effect=AssertionError('custom native binding')):
            result = components.build(width, height, self.root / 'rows', self.root / 'runs',
                                      self.root / 'outrows', self.root / 'outruns')
        spans = list(struct.iter_unpack('<III', (self.root / 'outruns').read_bytes()))
        output_rows = list(struct.unpack('<' + 'I' * (height + 1), (self.root / 'outrows').read_bytes()))
        labels = {}
        for y in range(height):
            for start, end, label in spans[output_rows[y]:output_rows[y + 1]]:
                labels.update({(y, x): label for x in range(start, end)})
        self.assertEqual(result['land_cells'], sum(sum(row) for row in mask))
        self.assertEqual(result['components'], len(set(labels.values())))
        return result, labels, spans

    def check_topology(self, mask):
        _, labels, _ = self.build(mask)
        remaining = {(y, x) for y, row in enumerate(mask) for x, value in enumerate(row) if value}
        expected = []
        while remaining:
            seed = remaining.pop()
            frontier, connected = [seed], {seed}
            while frontier:
                y, x = frontier.pop()
                for neighbor in ((y, (x - 1) % len(mask[0])), (y, (x + 1) % len(mask[0])),
                                 (y - 1, x), (y + 1, x)):
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        connected.add(neighbor)
                        frontier.append(neighbor)
            expected.append(connected)
        actual = [{cell for cell, value in labels.items() if value == root} for root in set(labels.values())]
        self.assertEqual({frozenset(group) for group in expected}, {frozenset(group) for group in actual})

    def test_exhaustive_small_topologies(self):
        for bits in itertools.product((0, 1), repeat=6):
            self.check_topology([bits[:3], bits[3:]])

    def test_random_larger_topologies(self):
        rng = random.Random(147)
        for _ in range(100):
            width, height = rng.randrange(2, 17), rng.randrange(1, 14)
            self.check_topology([[rng.randrange(2) for _ in range(width)] for _ in range(height)])

    def test_union_by_size_tie_preserves_nonminimum_root(self):
        mask = [[1, 0, 0, 1, 1, 1, 1, 0, 0],
                [1, 0, 0, 1, 0, 0, 1, 0, 0],
                [1, 1, 1, 1, 1, 1, 1, 0, 0]]
        _, labels, spans = self.build(mask)
        self.assertEqual(set(labels.values()), {1})
        self.assertEqual([root for _, _, root in spans], [1] * 6)

    def test_diagonals_and_poles_are_not_connected(self):
        result, _, _ = self.build([[0, 1, 0, 0, 0], [0, 0, 1, 0, 0], [0, 1, 0, 0, 0]])
        self.assertEqual(result['components'], 3)

    def test_longitude_wrap(self):
        result, _, _ = self.build([[1, 0, 0, 1, 1]])
        self.assertEqual(result['components'], 1)

    def test_malformed_and_noncanonical_streams(self):
        cases = [([0, 2], [1, 17, 3, 17]), ([0, 2], [2, 17, 1, 1]),
                 ([0, 1], [2, 1]), ([0, 1], [3, 5]), ([1, 1], [3, 1]),
                 ([0, 2], [3, 1]), ([0, 1, 0, 1], [3, 1])]
        for rows, runs in cases:
            for name, values in [('rows', rows), ('runs', runs)]:
                (self.root / name).write_bytes(struct.pack('<' + 'I' * len(values), *values))
            with self.assertRaises(ValueError):
                components.build(3, len(rows) - 1, self.root / 'rows', self.root / 'runs',
                                 self.root / 'outrows', self.root / 'outruns')
            self.assertFalse((self.root / 'outrows').exists())
            self.assertFalse((self.root / 'outruns').exists())

    def test_existing_output_not_replaced(self):
        self.build([[1, 0]])
        original = (self.root / 'outrows').read_bytes()
        with self.assertRaises(FileExistsError):
            components.build(2, 1, self.root / 'rows', self.root / 'runs',
                             self.root / 'outrows', self.root / 'outruns')
        self.assertEqual((self.root / 'outrows').read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
