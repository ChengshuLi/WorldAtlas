import json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from osgeo import gdal, osr
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution.runtime import RunFilePins
from worldatlas.map_build.physical import union as c
from worldatlas.map_build.physical.sources import open_mask
from worldatlas.shared.files import sha256_file


class AggregateTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.d = Path(self.t.name)
        self.inputs = self.d / 'inputs'
        self.inputs.mkdir()
        self.cfg = {
            'schema': 'water-union-v1',
            'grid': {'width': 8, 'height': 4, 'west': -180, 'north': 90, 'step': 45},
            'shard_count': 2,
            'selection_notes': 'synthetic test',
            'minimum_free_bytes': 0,
        }
        one = np.zeros((4, 8), dtype=np.uint8)
        one[0, 2:5] = 1
        two = np.zeros((4, 8), dtype=np.uint8)
        two[1, 1] = 1
        self.cfg['shards'] = [self.tif('one', one), self.tif('two', two)]
        manifest = {
            'file_count': 2,
            'files': [{'sha256': '1' * 64}, {'sha256': '2' * 64}],
        }
        mp = self.inputs / 'manifest.json'
        mp.write_text(json.dumps(manifest))
        self.cfg['source_manifest'] = {'path': str(mp), 'sha256': sha256_file(mp)}
        for i, shard in enumerate(self.cfg['shards']):
            shard['status'] = 'candidate-only'
            doc = {
                'status': 'candidate-only',
                'source_sha256': str(i + 1) * 64,
                'output_sha256': shard['sha256'],
                'grid': self.cfg['grid'],
                'policy': 'synthetic',
                'script_sha256': 'c' * 64,
                'rasterizer': 'gdal',
                'rows_in_source': 10,
                'counts': {'rows': 10},
                'invalid_feature_rows': None,
            }
            rp = self.inputs / ('report' + str(i) + '.json')
            rp.write_text(json.dumps(doc))
            shard['report'] = {'path': str(rp), 'sha256': sha256_file(rp)}
        self.config = self.inputs / 'config.json'
        self.config.write_text(json.dumps(self.cfg))

    def build(self, output, **options):
        settings = json.loads(self.config.read_bytes())
        return c.run(
            sha256_file(self.config), output, Grid(**settings['grid']),
            source_manifest=settings['source_manifest'], shards=settings['shards'],
            minimum_free_bytes=settings['minimum_free_bytes'],
            rows_per_block=settings.get('rows_per_block', 128), files=RunFilePins(), **options,
        )

    def tearDown(self):
        self.t.cleanup()

    def tif(self, name, array):
        p = self.inputs / (name + '.tif')
        ds = gdal.GetDriverByName('GTiff').Create(str(p), 8, 4, 1, gdal.GDT_Byte)
        ds.SetGeoTransform((-180, 45, 0, 90, 0, -45))
        s = osr.SpatialReference()
        s.ImportFromEPSG(4326)
        ds.SetSpatialRef(s)
        ds.GetRasterBand(1).WriteArray(array)
        ds = None
        return {'path': str(p), 'sha256': sha256_file(p)}

    def test_sparse_union_matches_full_read_across_block_boundaries(self):
        path = self.inputs / 'sparse.tif'
        ds = gdal.GetDriverByName('GTiff').Create(
            str(path),
            64,
            48,
            1,
            gdal.GDT_Byte,
            options=['TILED=YES', 'BLOCKXSIZE=16', 'BLOCKYSIZE=16', 'SPARSE_OK=YES'],
        )
        values = np.zeros((48, 64), dtype=np.uint8)
        values[5:19, 14:19] = 1
        values[36:40, 50:55] = 1
        ds.GetRasterBand(1).WriteArray(values[5:19, 14:19], 14, 5)
        ds.GetRasterBand(1).WriteArray(values[36:40, 50:55], 50, 36)
        ds.FlushCache()
        ds = None
        ds = gdal.Open(str(path))
        expected = np.zeros_like(values)
        expected[:, 3] = 1
        actual = expected.copy()
        for y in range(0, 48, 7):
            c.union_mask(ds, actual[y : y + 7], y)
        np.bitwise_or(expected, values, out=expected)
        np.testing.assert_array_equal(actual, expected)

    def test_sparse_union_reads_nonzero_nodata_and_rejects_nonbinary(self):
        path = self.inputs / 'nodata.tif'
        ds = gdal.GetDriverByName('GTiff').Create(
            str(path),
            32,
            16,
            1,
            gdal.GDT_Byte,
            options=['TILED=YES', 'BLOCKXSIZE=16', 'BLOCKYSIZE=16', 'SPARSE_OK=YES'],
        )
        ds.GetRasterBand(1).SetNoDataValue(1)
        ds = None
        ds = gdal.Open(str(path))
        actual = np.zeros((16, 32), dtype=np.uint8)
        c.union_mask(ds, actual, 0)
        np.testing.assert_array_equal(actual, ds.ReadAsArray())
        self.assertTrue(np.all(actual == 1))
        ds = None
        ds = gdal.Open(str(path), gdal.GA_Update)
        ds.GetRasterBand(1).WriteArray(np.array([[2]], dtype=np.uint8), 0, 0)
        ds = None
        ds = gdal.Open(str(path))
        actual.fill(0)
        with self.assertRaisesRegex(ValueError, 'nonbinary'):
            c.union_mask(ds, actual, 0)

    def test_union_writes_only_the_candidate_mask_and_receipt(self):
        out = self.d / 'out'
        self.build(out)
        r = json.loads((out / 'report.json').read_text())
        self.assertEqual(r['candidate_water_cells'], 4)
        self.assertEqual(
            set(p.name for p in out.iterdir()),
            {'water-union.tif', 'report.json'},
        )
        with self.assertRaises(FileExistsError):
            self.build(out)
        self.assertEqual(r['grid'], self.cfg['grid'])
        self.assertEqual(r['shard_count'], 2)

    def test_mask_reader_rejects_a_raster_with_two_bands(self):
        path = self.inputs / 'two-bands.tif'
        with gdal.GetDriverByName('GTiff').Create(str(path), 8, 4, 2, gdal.GDT_Byte) as mask:
            mask.SetGeoTransform((-180, 45, 0, 90, 0, -45))
        pin = dict(path=str(path), sha256=sha256_file(path))
        with self.assertRaisesRegex(ValueError, 'must have one uint8 band'):
            open_mask(pin, Grid(**self.cfg['grid']), RunFilePins())

    def test_union_keeps_partial_output_when_disk_space_drops_mid_run(self):
        self.cfg["minimum_free_bytes"] = 1
        self.config.write_text(json.dumps(self.cfg))
        out = self.d / "low-space"

        def disk_usage(path):
            free = 0 if Path(path) == out.resolve() else 1024
            return SimpleNamespace(free=free)

        with patch.object(c.shutil, "disk_usage", side_effect=disk_usage):
            with self.assertRaisesRegex(ValueError, "partial output preserved"):
                self.build(out)
        self.assertTrue((out / "water-union.tif").exists())
        self.assertFalse((out / "report.json").exists())

    def test_union_refuses_to_publish_when_an_input_changes(self):
        for filename, message in (
            (Path(self.cfg['shards'][0]['report']['path']), 'checkpoint/input hash mismatch'),
            (Path(self.cfg['shards'][0]['path']), 'checkpoint/input hash mismatch'),
        ):
            with self.subTest(filename=filename):
                original = filename.read_bytes()
                out = self.d / (filename.stem + '-changed')

                def change_input(*_, **__):
                    filename.write_bytes(original + b'\n')

                with self.assertRaisesRegex(ValueError, message):
                    self.build(out, emit=change_input)
                self.assertFalse((out / 'report.json').exists())
                filename.write_bytes(original)

    def test_raster_pin_requires_matching_bytes_grid_and_crs(self):
        grid = self.cfg['grid']
        spec = self.cfg['shards'][0]
        path = spec['path']
        with self.assertRaisesRegex(ValueError, 'input hash mismatch'):
            open_mask(dict(spec, sha256='0' * 64), Grid(**grid), RunFilePins())
        with self.assertRaisesRegex(ValueError, 'grid mismatch'):
            open_mask(spec, Grid(4, 2, 90), RunFilePins())
        for epsg, message in ((None, 'missing CRS'), (3857, 'CRS mismatch')):
            with self.subTest(epsg=epsg):
                with gdal.Open(path, gdal.GA_Update) as raster:
                    if epsg is None:
                        raster.SetProjection('')
                    else:
                        crs = osr.SpatialReference()
                        crs.ImportFromEPSG(epsg)
                        raster.SetSpatialRef(crs)
                with self.assertRaisesRegex(ValueError, message):
                    open_mask(dict(spec, sha256=sha256_file(path)), Grid(**grid), RunFilePins())

    def test_union_requires_distinct_masks(self):
        self.cfg['shards'][1]['path'] = self.cfg['shards'][0]['path']
        self.config.write_text(json.dumps(self.cfg))
        out = self.d / 'duplicate'
        with self.assertRaisesRegex(ValueError, 'input paths must be unique'):
            self.build(out)
        self.assertFalse(out.exists())

    def test_fails_closed_on_incomplete_or_changed(self):
        self.cfg['shards'][0]['sha256'] = '0' * 64
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaises(ValueError):
            self.build(self.d / 'bad')
        self.assertFalse((self.d / 'bad').exists())

    def test_rejects_nonbinary(self):
        p = Path(self.cfg['shards'][0]['path'])
        ds = gdal.Open(str(p), gdal.GA_Update)
        a = ds.ReadAsArray()
        a[0, 0] = 2
        ds.GetRasterBand(1).WriteArray(a)
        ds = None
        self.cfg['shards'][0]['sha256'] = sha256_file(p)
        rp = Path(self.cfg['shards'][0]['report']['path'])
        doc = json.loads(rp.read_text())
        doc['output_sha256'] = sha256_file(p)
        rp.write_text(json.dumps(doc))
        self.cfg['shards'][0]['report']['sha256'] = sha256_file(rp)
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'nonbinary'):
            self.build(self.d / 'bad')
        self.assertFalse((self.d / 'bad' / 'report.json').exists())


if __name__ == '__main__':
    unittest.main()
