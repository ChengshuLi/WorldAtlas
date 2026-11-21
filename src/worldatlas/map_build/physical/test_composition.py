import json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from osgeo import gdal, osr
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
        ref = np.zeros((4, 8), dtype=np.uint8)
        ref[:2, :2] = 1
        for name, values in [('land', land), ('water', water), ('reference_mask', ref)]:
            path = self.inputs / (name + '.tif')
            ds = gdal.GetDriverByName('GTiff').Create(str(path), 8, 4, 1, gdal.GDT_Byte)
            ds.SetGeoTransform((-180, 45, 0, 90, 0, -45))
            s = osr.SpatialReference()
            s.ImportFromEPSG(4326)
            ds.SetSpatialRef(s)
            ds.GetRasterBand(1).WriteArray(values)
            ds = None
            self.cfg[name] = {'path': str(path), 'sha256': sha256_file(path)}
        rows = [0]
        pairs = []
        for row in ref:
            codes = np.where(row, 17, 1)
            ends = np.flatnonzero(np.r_[codes[1:] != codes[:-1], True])
            pairs.extend((int(x + 1), int(codes[x])) for x in ends)
            rows.append(len(pairs))
        rp = self.inputs / 'rows.u32'
        up = self.inputs / 'runs.u32'
        np.asarray(rows, dtype='<u4').tofile(rp)
        np.asarray(pairs, dtype='<u4').tofile(up)
        self.cfg['reference_streams'] = {
            'rows': {'path': str(rp), 'sha256': sha256_file(rp)},
            'runs': {'path': str(up), 'sha256': sha256_file(up)},
        }
        self.p = self.inputs / 'config.json'
        self.p.write_text(json.dumps(self.cfg))

    def tearDown(self):
        self.t.cleanup()

    def test_vectorized_runs_match_row_encoder(self):
        rng = np.random.default_rng(42)
        for height, width in [(1, 1), (4, 8), (17, 31), (3, 128)]:
            for mode in ('zero', 'one', 'random'):
                if mode == 'zero':
                    codes = np.ones((height, width), dtype=np.uint8)
                elif mode == 'one':
                    codes = np.full((height, width), 17, dtype=np.uint8)
                else:
                    codes = np.where(rng.integers(0, 2, (height, width)), 17, 1).astype(np.uint8)
                path = self.d / 'runs-test'
                offsets = [0]
                with path.open('wb') as stream:
                    for start in range(0, height, 3):
                        b.write_run_block(codes[start : start + 3], stream, offsets, width)
                pairs = np.fromfile(path, dtype='<u4').reshape(-1, 2).tolist()
                expected = []
                expected_offsets = [0]
                for row in codes:
                    ends = np.flatnonzero(np.r_[row[1:] != row[:-1], True])
                    expected.extend((int(end + 1), int(row[end])) for end in ends)
                    expected_offsets.append(len(expected))
                self.assertEqual(pairs, [list(pair) for pair in expected])
                self.assertEqual(offsets, expected_offsets)
                offsets = [0]
                with path.open('wb') as stream:
                    for start in range(0, height, 3):
                        b.write_run_block(
                            (codes[start : start + 3] == 17).astype(np.uint8),
                            stream,
                            offsets,
                            width,
                            binary=True,
                        )
                self.assertEqual(np.fromfile(path, dtype='<u4').reshape(-1, 2).tolist(), pairs)
                self.assertEqual(offsets, expected_offsets)

    def test_compose_and_compare(self):
        out = self.d / 'out'
        b.main(self.p, out)
        r = json.loads((out / 'report.json').read_text())
        self.assertEqual(
            (
                r['candidate_dry_cells'],
                r['historic_dry_cells'],
                r['candidate_extra_land_cells'],
                r['candidate_missing_land_cells'],
            ),
            (5, 4, 2, 1),
        )
        self.assertEqual(r['mismatch_spans'], 3)
        with self.assertRaises(FileExistsError):
            b.main(self.p, out)
        with self.assertRaises(ValueError):
            b.main(self.p, self.inputs / 'nested')
        with self.assertRaises(ValueError):
            b.main(self.p, self.d)

    def test_without_reference(self):
        self.cfg.pop('reference_mask')
        self.cfg.pop('reference_streams')
        self.p.write_text(json.dumps(self.cfg))
        out = self.d / 'no-reference'
        b.main(self.p, out)
        r = json.loads((out / 'report.json').read_text())
        self.assertEqual(r['candidate_dry_cells'], 5)
        self.assertNotIn('historic_dry_cells', r)
        self.assertEqual(r['grid'], self.cfg['grid'])
        self.assertEqual(r['inputs']['land'], self.cfg['land'])
        rows = np.fromfile(out / 'rows.u32le', dtype='<u4')
        runs = np.fromfile(out / 'runs.u32le', dtype='<u4').reshape(-1, 2)
        self.assertEqual(rows.tolist(), [0, 3, 5, 6, 7])
        self.assertEqual(runs.tolist(), [[1, 1], [3, 17], [8, 1], [3, 17], [8, 1], [8, 1], [8, 1]])

    def test_rejects_partial_reference(self):
        self.cfg.pop('reference_streams')
        self.p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'provided together'):
            b.main(self.p, self.d / 'partial')
        self.assertFalse((self.d / 'partial').exists())

    def test_composition_checks_distinct_inputs_and_valid_controls(self):
        for changes, message in (
            ({'selection_notes': ''}, 'schema and selection notes'),
            ({'minimum_free_bytes': -1}, 'invalid free-space reserve'),
            ({'rows_per_block': 0}, 'invalid rows_per_block'),
            ({'water': self.cfg['land']}, 'inputs must be distinct'),
        ):
            with self.subTest(changes=changes):
                self.p.write_text(json.dumps(dict(self.cfg, **changes)))
                out = self.d / 'invalid'
                with self.assertRaisesRegex(ValueError, message):
                    b.main(self.p, out)
                self.assertFalse(out.exists())

    def test_invalid_comparison_offsets_are_rejected_before_composition(self):
        row_pin = self.cfg['reference_streams']['rows']
        path = Path(row_pin['path'])
        original = np.fromfile(path, dtype='<u4')
        for values, message in (
            (original[1:], 'invalid reference stream lengths/offsets'),
            (original[[0, 2, 1, 3, 4]], 'reference offsets not monotone'),
        ):
            with self.subTest(values=values):
                values.tofile(path)
                row_pin['sha256'] = sha256_file(path)
                self.p.write_text(json.dumps(self.cfg))
                with self.assertRaisesRegex(ValueError, message):
                    b.main(self.p, self.d / 'invalid')
        path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'reference rows digest mismatch'):
            b.main(self.p, self.d / 'invalid')

    def test_run_offsets_reject_overflow_before_appending_a_batch(self):
        path = self.d / 'runs.u32le'
        offsets = [2**32 - 1]
        with path.open('wb') as stream:
            with self.assertRaisesRegex(ValueError, 'too many runs for u32 offsets'):
                b.write_run_block(np.array([[17]], dtype=np.uint8), stream, offsets, 1)
        self.assertEqual(offsets, [2**32 - 1])
        self.assertEqual(path.read_bytes(), b'')

    def test_report_is_withheld_if_an_input_changes_during_composition(self):
        for path, message in (
            (self.p, 'config changed during processing'),
            (Path(self.cfg['land']['path']), 'land changed during processing'),
        ):
            with self.subTest(path=path):
                original = path.read_bytes()
                output = self.d / (path.stem + '-changed')

                def change(*_, **__):
                    path.write_bytes(original + b'\n')

                with self.assertRaisesRegex(ValueError, message):
                    b.main(self.p, output, emit=change)
                self.assertFalse((output / 'report.json').exists())
                path.write_bytes(original)

    def test_low_disk_space_or_failed_mask_read_leaves_composition_incomplete(self):
        self.cfg['minimum_free_bytes'] = 1
        self.p.write_text(json.dumps(self.cfg))
        low_disk = self.d / 'low-disk'
        with patch.object(
            b.shutil, 'disk_usage',
            side_effect=lambda path: SimpleNamespace(free=0 if Path(path) == low_disk.resolve() else 1024),
        ):
            with self.assertRaisesRegex(ValueError, 'partial output preserved'):
                b.main(self.p, low_disk)
        self.assertFalse((low_disk / 'report.json').exists())

        unreadable = self.d / 'unreadable'
        with patch.object(gdal.Dataset, 'ReadAsArray', return_value=None):
            with self.assertRaisesRegex(ValueError, 'could not read a physical mask'):
                b.main(self.p, unreadable)
        self.assertFalse((unreadable / 'report.json').exists())

    def test_binary_float_and_signed_masks_keep_original_support(self):
        for name, kind in [('land', gdal.GDT_Float32), ('water', gdal.GDT_Int16)]:
            old = gdal.Open(self.cfg[name]['path'])
            values = old.ReadAsArray()
            old = None
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
        out = self.d / 'typed'
        b.main(self.p, out)
        self.assertEqual(json.loads((out / 'report.json').read_text())['candidate_dry_cells'], 5)
        self.assertEqual(
            np.fromfile(out / 'runs.u32le', dtype='<u4').reshape(-1, 2).tolist(),
            [[1, 1], [3, 17], [8, 1], [3, 17], [8, 1], [8, 1], [8, 1]],
        )

    def test_rejects_negative_in_every_mask(self):
        for name in ('land', 'water', 'reference_mask'):
            original = self.cfg[name]
            p = self.inputs / (name + '-negative.tif')
            ds = gdal.GetDriverByName('GTiff').Create(str(p), 8, 4, 1, gdal.GDT_Int16)
            ds.SetGeoTransform((-180, 45, 0, 90, 0, -45))
            sr = osr.SpatialReference()
            sr.ImportFromEPSG(4326)
            ds.SetSpatialRef(sr)
            a = np.zeros((4, 8), dtype=np.int16)
            a[0, 0] = -1
            ds.GetRasterBand(1).WriteArray(a)
            ds = None
            self.cfg[name] = {'path': str(p), 'sha256': sha256_file(p)}
            self.p.write_text(json.dumps(self.cfg))
            with self.assertRaisesRegex(ValueError, 'nonbinary'):
                b.main(self.p, self.d / ('bad-' + name))
            self.cfg[name] = original

    def test_rejects_zero_length_first_run(self):
        p = Path(self.cfg['reference_streams']['runs']['path'])
        x = np.fromfile(p, dtype='<u4')
        x[0] = 0
        x.tofile(p)
        self.cfg['reference_streams']['runs']['sha256'] = sha256_file(p)
        self.p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'invalid reference row'):
            b.main(self.p, self.d / 'zero-run')

    def test_bad_grid_and_hash_fail_before_output(self):
        self.cfg['grid']['step'] = 0
        self.p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'invalid grid'):
            b.main(self.p, self.d / 'bad-grid')
        self.assertFalse((self.d / 'bad-grid').exists())
        self.cfg['grid']['step'] = 45
        self.cfg['land']['sha256'] = '0' * 64
        self.p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'input hash mismatch'):
            b.main(self.p, self.d / 'bad-hash')
        self.assertFalse((self.d / 'bad-hash').exists())

    def test_reject_reference_mismatch(self):
        p = Path(self.cfg['reference_mask']['path'])
        ds = gdal.Open(str(p), gdal.GA_Update)
        a = ds.ReadAsArray()
        a[3, 3] = 1
        ds.GetRasterBand(1).WriteArray(a)
        ds = None
        self.cfg['reference_mask']['sha256'] = sha256_file(p)
        self.p.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'historic binary mask disagrees'):
            b.main(self.p, self.d / 'bad')
        self.assertFalse((self.d / 'bad' / 'report.json').exists())


if __name__ == '__main__':
    unittest.main()
