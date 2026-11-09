import hashlib
import math
import struct
import tempfile
import unittest
from pathlib import Path

from exact_index import ExactIndex
from run_pair import run_pair


class ExactIndexSpeedTests(unittest.TestCase):
    def test_fine_leaves_preserve_all_cells_codes_and_exact_minimum(self):
        width, height, tile_cells = 1024, 512, 256
        records = [
            (0, 0, 256, 17), (126, 70, 239, 18), (128, 120, 255, 19),
            (255, 257, 510, 20), (300, 768, 1024, 21), (511, 0, 250, 22),
        ]
        groups = {}
        for record in records:
            y, a, b, code = record
            groups.setdefault((y // tile_cells, a // tile_cells), []).append(record)
        with tempfile.TemporaryDirectory() as td:
            tiles = []
            for (ty, tx), values in groups.items():
                raw = b''.join(struct.pack('<IIII', *value) for value in values)
                (Path(td) / f'{ty:05d}-{tx:05d}.bin').write_bytes(raw)
                tiles.append((ty, tx, sorted({v[3] for v in values}), len(values),
                              hashlib.sha256(raw).hexdigest()))
            index = ExactIndex(td, width, height, 360 / width, 90, tiles,
                               tile_cells=tile_cells)
            certificate_tiles = index.certificate_tiles
            self.assertGreater(len(certificate_tiles), len(tiles))
            expected_cells = {(y, x, c) for y, a, b, c in records for x in range(a, b)}
            actual_cells = set()
            for i, (_, sy, ey, sx, ex, selected) in enumerate(index.leaves):
                data = index._load_leaf(i)
                self.assertEqual(set(map(int, data[:, 3])), set(certificate_tiles[i][2]))
                for y, a, b, code in data:
                    self.assertTrue(sy <= y < ey and sx <= a < b <= ex)
                    actual_cells.update((int(y), x, int(code)) for x in range(int(a), int(b)))
            self.assertEqual(actual_cells, expected_cells)
            for query in [(0, 1010, 1024), (127, 112, 139), (260, 490, 530), (511, 300, 340)]:
                expected = {}
                for y, a, b, code in records:
                    distance, _ = run_pair(*query, y, a, b, width, incumbent=math.inf)
                    expected[code] = min(expected.get(code, math.inf), distance)
                actual, _ = index.nearest_run(*query, max(expected.values()))
                winner = min(expected, key=lambda c: (expected[c], c))
                self.assertAlmostEqual(min(actual.values()), expected[winner], delta=1e-5)
                self.assertEqual(min(actual, key=lambda c: (actual[c], c)), winner)

    def test_dynamic_bound_preserves_nearest_wgs84_category(self):
        width, height, step, north, tile_cells = 360, 180, 1.0, 90.0, 10
        # One authenticated seed run per continent at representative positions.
        seeds = [
            (89, 200, 17),   # Africa
            (59, 280, 18),   # Asia
            (39, 190, 19),   # Europe
            (49, 80, 20),    # North America
            (109, 120, 21),  # South America
            (109, 310, 22),  # Oceania
        ]
        query = (80, 230, 231)
        expected = {}
        for y, x, code in seeds:
            d, _ = run_pair(query[0], query[1], query[2], y, x, x + 1,
                            width, north=north, incumbent=math.inf, tol=0)
            expected[code] = d
        expected_min = min(expected.values())
        expected_code = min(code for code, d in expected.items() if d <= expected_min + 1e-5)

        with tempfile.TemporaryDirectory() as td:
            tile_dir = Path(td)
            tiles = []
            for y, x, code in seeds:
                ty, tx = y // tile_cells, x // tile_cells
                raw = struct.pack('<IIII', y, x, x + 1, code)
                path = tile_dir / f'{ty:05d}-{tx:05d}.bin'
                path.write_bytes(raw)
                tiles.append((ty, tx, {code}, 1, hashlib.sha256(raw).hexdigest()))
            index = ExactIndex(tile_dir, width, height, step, north, tiles,
                               tile_cells=tile_cells, guard_m=1000)
            actual, stats = index.nearest_run(*query, max(expected.values()), tolerance=1e-5)
            self.assertTrue(actual)
            actual_min = min(actual.values())
            actual_winners = [code for code, distance in actual.items()
                              if distance <= actual_min + 1e-5]
            self.assertEqual(min(actual_winners), expected_code)
            self.assertAlmostEqual(actual_min, expected_min, delta=1e-5)
            self.assertLess(stats['run_pairs_wgs84_tested'], len(seeds))

            # Verified immutable tiles stay available after loading the full
            # index; this path has no artificial cache-size or memory-floor cap.
            for key in index.ids:
                index._load(key)
            self.assertEqual(len(index.cache), len(seeds))


if __name__ == '__main__':
    unittest.main()
