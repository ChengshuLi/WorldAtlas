import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from map_build.core.grid import Grid
from map_build.core.layers import layer_rows, patch_rows, write_layer
from map_build.core.rle import open_grid
from map_build.water.shared_nearest import crop


class LayersTests(unittest.TestCase):
    def test_wrapped_patch_roundtrip_preserves_unrelated_zero_cells(self):
        grid = Grid(36, 18, 10.)
        values = np.array([[4321, 4321, 902], [0, 902, 902]], dtype='u4')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'layer'
            write_layer(path, grid, patch_rows(values, (35, 38, 8, 10), grid))
            with open_grid(path, grid) as data:
                self.assertTrue(np.array_equal(crop(*data, 8, 35, 38, 36), values[0]))
                self.assertTrue(np.array_equal(crop(*data, 9, 35, 38, 36), values[1]))
                self.assertFalse(crop(*data, 0, 0, 36, 36).any())

    def test_tile_checksums_and_category_bindings_are_verified(self):
        grid = Grid(36, 18, 10.)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = gzip.compress(b'{"row":3,"spans":[{"start":4,"end":6,"code":4321}]}\n')
            (root / 'tile.gz').write_bytes(data)
            manifest = {'grid': {'width': 36, 'height': 18}, 'tiles': [{
                'core_rows': [0, 18], 'core_cols': [0, 36],
                'span_file': {'path': 'tile.gz', 'sha256': hashlib.sha256(data).hexdigest()}}]}
            path = root / 'manifest.json'
            path.write_text(json.dumps(manifest))
            self.assertEqual(list(layer_rows(path, grid, {4321})), [(3, [(4, 6, 4321)])])
            manifest['tiles'] *= 2
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'overlap'):
                list(layer_rows(path, grid, {4321}))
            manifest['tiles'] = manifest['tiles'][:1]
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'unbound'):
                list(layer_rows(path, grid, {1}))
            (root / 'tile.gz').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                list(layer_rows(path, grid, {4321}))

    def test_overlapping_tiles_and_duplicate_output_rows_are_rejected(self):
        grid = Grid(36, 18, 10.)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'ordered and unique'):
                write_layer(Path(directory) / 'layer', grid, [(3, [(1, 2, 700)]), (3, [(2, 3, 700)])])
