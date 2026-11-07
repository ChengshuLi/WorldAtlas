import hashlib
from pathlib import Path
import random
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'lydekker-regional-rule'))
import component_scan as reference
from component_index import ComponentIndex
from regional_rule import Line


def pin(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


class ComponentIndexTests(unittest.TestCase):
    def fixture(self, root, data, grid):
        rows, runs = root / 'rows', root / 'runs'
        offsets = [0]
        with runs.open('wb') as stream:
            for row in data:
                for run in row:
                    stream.write(struct.pack('<III', *run))
                offsets.append(offsets[-1] + len(row))
        rows.write_bytes(struct.pack('<' + 'I'*len(offsets), *offsets))
        return pin(rows), pin(runs), ComponentIndex(pin(rows), pin(runs), grid)

    def test_random_windows_counts_order_and_complete_runs(self):
        rng = random.Random(20261107)
        grid = {'width': 72, 'height': 36, 'west': -180, 'north': 90, 'step': 5}
        data = []
        for _ in range(grid['height']):
            row, x = [], 0
            while x < grid['width'] - 4:
                x += rng.randrange(1, 4)
                end = min(grid['width'], x + rng.randrange(1, 5))
                row.append((x, end, rng.choice([0, 1, 5, 19, 0xfffffffe])))
                x = end
            data.append(row if rng.randrange(5) else [])
        line = Line({'type': 'LineString', 'coordinates': [[10, 65], [0, 0], [-7, -50]]})
        with tempfile.TemporaryDirectory() as directory:
            rows, runs, index = self.fixture(Path(directory), data, grid)
            windows = [[-180, -90, 180, 90], [-177.5, -52.5, 7.5, 67.5], [170, 80, 180, 90]]
            for _ in range(30):
                west, east = sorted([rng.uniform(-180, 180), rng.uniform(-180, 180)])
                south, north = sorted([rng.uniform(-90, 90), rng.uniform(-90, 90)])
                windows.append([west, south, east, north])
            for bounds in windows:
                expected = reference.scan(rows, runs, grid, bounds, line)
                actual = index.scan(rows, runs, grid, bounds, line)
                self.assertEqual(actual, expected)
                self.assertEqual(list(actual), list(expected))
                counts = {root: values['total'] for root, values in expected.items()}
                selected = index.collect_runs(rows, runs, grid, counts)
                self.assertEqual(selected, reference.collect_runs(rows, runs, grid, counts))
                self.assertIs(index.collect_runs(rows, runs, grid, counts), selected)
            for y, row in enumerate(data):
                for lo, _, root in row:
                    self.assertEqual(index.component_at(rows, runs, grid, -180 + (lo + .5)*5, 90 - (y + .5)*5), root)
            index.verify()

    def test_empty_and_corrupt_streams(self):
        grid = {'width': 4, 'height': 2, 'west': -2, 'north': 1, 'step': 1}
        line = Line({'type': 'LineString', 'coordinates': [[0, 1], [0, -1]]})
        for data in [[[], []], [[(0, 2, 1), (1, 3, 2)], []], [[(0, 5, 1)], []], [[(0, 1, 0xffffffff)], []]]:
            with tempfile.TemporaryDirectory() as directory:
                if any(data):
                    with self.assertRaisesRegex(ValueError, 'invalid component run'):
                        self.fixture(Path(directory), data, grid)
                else:
                    rows, runs, index = self.fixture(Path(directory), data, grid)
                    self.assertEqual(index.scan(rows, runs, grid, [-2, -1, 2, 1], line), {})
                    self.assertEqual(index.collect_runs(rows, runs, grid, {}), {})

    def test_changed_input_and_generation_fail_closed(self):
        grid = {'width': 4, 'height': 1, 'west': -2, 'north': 1, 'step': 1}
        with tempfile.TemporaryDirectory() as directory:
            rows, runs, index = self.fixture(Path(directory), [[(0, 2, 1)]], grid)
            with self.assertRaisesRegex(ValueError, 'generation mismatch'):
                index.collect_runs(rows, runs, {**grid, 'north': 0}, {1: 2})
            Path(runs['path']).write_bytes(struct.pack('<III', 0, 3, 1))
            with self.assertRaisesRegex(ValueError, 'input changed'):
                index.collect_runs(rows, runs, grid, {1: 2})
            with self.assertRaisesRegex(ValueError, 'input changed'):
                index.verify()


if __name__ == '__main__':
    unittest.main()
