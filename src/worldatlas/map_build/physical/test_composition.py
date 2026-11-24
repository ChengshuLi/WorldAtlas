import json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from osgeo import gdal, osr
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution.runtime import RunFilePins
from worldatlas.map_build.physical import composition as b
from worldatlas.shared.files import sha256_file


class ComposeTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.d = Path(self.t.name)
        self.inputs = self.d / 'inputs'
        self.inputs.mkdir()
        self.cfg = {
            'schema': 'candidate-physical-composition-v1',
            'selection_notes': 'synthetic test',
            'minimum_free_bytes': 0,
            'grid': {'width': 8, 'height': 4, 'west': -180, 'north': 90, 'step': 45},
        }
        land = np.zeros((4, 8), dtype=np.uint8)
        land[:2, :3] = 1
        water = np.zeros((4, 8), dtype=np.uint8)
        water[0, 0] = 1
        for name, values in [('land', land), ('water', water)]:
            path = self.inputs / (name + '.tif')
            ds = gdal.GetDriverByName('GTiff').Create(str(path), 8, 4, 1, gdal.GDT_Byte)
            ds.SetGeoTransform((-180, 45, 0, 90, 0, -45))
            s = osr.SpatialReference()
            s.ImportFromEPSG(4326)
            ds.SetSpatialRef(s)
            ds.GetRasterBand(1).WriteArray(values)
            ds = None
            self.cfg[name] = {'path': str(path), 'sha256': sha256_file(path)}
        self.p = self.inputs / 'config.json'
        self.p.write_text(json.dumps(self.cfg))

    def build(self, output, **options):
        settings = json.loads(self.p.read_bytes())
        return b.run(
            sha256_file(self.p), output, Grid(**settings['grid']), land=settings['land'], water=settings['water'],
            minimum_free_bytes=settings['minimum_free_bytes'],
            rows_per_block=settings.get('rows_per_block', 128), files=RunFilePins(), **options,
        )

    def tearDown(self):
        self.t.cleanup()

    def test_vectorized_runs_match_row_encoder(self):
        rng = np.random.default_rng(42)
        for height, width in [(1, 1), (4, 8), (17, 31), (3, 128)]:
            for mode in ('zero', 'one', 'random'):
                if mode == 'zero':
                    dry_land = np.zeros((height, width), dtype=np.uint8)
                elif mode == 'one':
                    dry_land = np.ones((height, width), dtype=np.uint8)
                else:
                    dry_land = rng.integers(0, 2, (height, width), dtype=np.uint8)
                path = self.d / 'runs-test'
                offsets = [0]
                with path.open('wb') as stream:
                    for start in range(0, height, 3):
                        b.write_run_block(dry_land[start : start + 3], stream, offsets)
                pairs = np.fromfile(path, dtype='<u4').reshape(-1, 2).tolist()
                expected = []
                expected_offsets = [0]
                for row in dry_land:
                    ends = np.flatnonzero(np.r_[row[1:] != row[:-1], True])
                    expected.extend([int(end + 1), 17 if row[end] else 1] for end in ends)
                    expected_offsets.append(len(expected))
                self.assertEqual(pairs, expected)
                self.assertEqual(offsets, expected_offsets)

    def test_composition_writes_raster_and_run_streams(self):
        out = self.d / 'out'
        self.build(out)
        r = json.loads((out / 'report.json').read_text())
        self.assertEqual(r['candidate_dry_cells'], 5)
        self.assertFalse((out / 'mismatch-spans.jsonl').exists())
        with self.assertRaises(FileExistsError):
            self.build(out)
        self.assertNotIn('historic_dry_cells', r)
        self.assertEqual(r['grid'], self.cfg['grid'])
        self.assertEqual(r['inputs']['land'], self.cfg['land'])
        rows = np.fromfile(out / 'rows.u32le', dtype='<u4')
        runs = np.fromfile(out / 'runs.u32le', dtype='<u4').reshape(-1, 2)
        self.assertEqual(rows.tolist(), [0, 3, 5, 6, 7])
        self.assertEqual(
            runs.tolist(), [[1, 1], [3, 17], [8, 1], [3, 17], [8, 1], [8, 1], [8, 1]]
        )

    def test_composition_requires_distinct_masks(self):
        self.p.write_text(json.dumps(dict(self.cfg, water=self.cfg['land'])))
        out = self.d / 'invalid'
        with self.assertRaisesRegex(ValueError, 'inputs must be distinct'):
            self.build(out)
        self.assertFalse(out.exists())

    def test_run_offsets_reject_overflow_before_appending_a_batch(self):
        path = self.d / 'runs.u32le'
        offsets = [2**32 - 1]
        with path.open('wb') as stream:
            with self.assertRaisesRegex(ValueError, 'too many runs for u32 offsets'):
                b.write_run_block(np.array([[1]], dtype=np.uint8), stream, offsets)
        self.assertEqual(offsets, [2**32 - 1])
        self.assertEqual(path.read_bytes(), b'')

    def test_report_is_withheld_if_a_mask_changes_during_composition(self):
        path = Path(self.cfg['land']['path'])
        original = path.read_bytes()
        output = self.d / 'changed-land'

        def change(*_, **__):
            path.write_bytes(original + b'\n')

        with self.assertRaisesRegex(
            ValueError, r'checkpoint/input hash mismatch: .*land\.tif'
        ):
            self.build(output, emit=change)
        self.assertFalse((output / 'report.json').exists())

    def test_low_disk_space_or_failed_mask_read_leaves_composition_incomplete(self):
        self.cfg['minimum_free_bytes'] = 1
        self.p.write_text(json.dumps(self.cfg))
        low_disk = self.d / 'low-disk'
        with patch.object(
            b.shutil,
            'disk_usage',
            side_effect=lambda path: SimpleNamespace(
                free=0 if Path(path) == low_disk.resolve() else 1024
            ),
        ):
            with self.assertRaisesRegex(ValueError, 'partial output preserved'):
                self.build(low_disk)
        self.assertFalse((low_disk / 'report.json').exists())

        unreadable = self.d / 'unreadable'
        with patch.object(gdal.Dataset, 'ReadAsArray', return_value=None):
            with self.assertRaisesRegex(ValueError, 'could not read a physical mask'):
                self.build(unreadable)
        self.assertFalse((unreadable / 'report.json').exists())

    def test_rejects_float_and_signed_masks_before_creating_output(self):
        for name, kind in [('land', gdal.GDT_Float32), ('water', gdal.GDT_Int16)]:
            original = self.cfg[name]
            with gdal.Open(original['path']) as old:
                values = old.ReadAsArray()
            p = self.inputs / (name + '-typed.tif')
            ds = gdal.GetDriverByName('GTiff').Create(str(p), 8, 4, 1, kind)
            ds.SetGeoTransform((-180, 45, 0, 90, 0, -45))
            sr = osr.SpatialReference()
            sr.ImportFromEPSG(4326)
            ds.SetSpatialRef(sr)
            ds.GetRasterBand(1).WriteArray(values)
            ds = None
            self.cfg[name] = {'path': str(p), 'sha256': sha256_file(p)}
            self.p.write_text(json.dumps(self.cfg))
            out = self.d / ('typed-' + name)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'one uint8 band'):
                self.build(out)
            self.assertFalse(out.exists())
            self.cfg[name] = original

    def test_rejects_values_above_one_in_either_mask(self):
        for name in ('land', 'water'):
            original = self.cfg[name]
            p = self.inputs / (name + '-nonbinary.tif')
            with gdal.Open(original['path']) as source:
                with gdal.GetDriverByName('GTiff').CreateCopy(str(p), source) as mask:
                    mask.GetRasterBand(1).WriteArray(np.array([[2]], dtype=np.uint8), 0, 0)
            self.cfg[name] = {'path': str(p), 'sha256': sha256_file(p)}
            self.p.write_text(json.dumps(self.cfg))
            with self.assertRaisesRegex(ValueError, 'nonbinary'):
                self.build(self.d / ('bad-' + name))
            self.cfg[name] = original

    def test_bad_grid_and_hash_fail_before_output(self):
        self.cfg['grid']['step'] = 0
        self.p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'aligned global'):
            self.build(self.d / 'bad-grid')
        self.assertFalse((self.d / 'bad-grid').exists())
        self.cfg['grid']['step'] = 45
        self.cfg['land']['sha256'] = '0' * 64
        self.p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'input hash mismatch'):
            self.build(self.d / 'bad-hash')
        self.assertFalse((self.d / 'bad-hash').exists())


if __name__ == '__main__':
    unittest.main()
