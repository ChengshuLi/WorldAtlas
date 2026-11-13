import json, tempfile, unittest
from pathlib import Path
import numpy as np
from osgeo import gdal, osr
from worldatlas.map_build.physical import union as c


class AggregateTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.d = Path(self.t.name)
        self.inputs = self.d / 'inputs'
        self.inputs.mkdir()
        self.cfg = {
            'schema': 'water-union-comparison-v1',
            'grid': {'width': 8, 'height': 4, 'west': -180, 'north': 90, 'step': 45},
            'shard_count': 2,
            'selection_notes': 'synthetic test',
            'minimum_free_bytes': 0,
        }
        reference = np.zeros((4, 8), dtype=np.uint8)
        reference[0, 1:4] = 1
        reference[1, 1] = 1
        one = np.zeros((4, 8), dtype=np.uint8)
        one[0, 2:5] = 1
        two = np.zeros((4, 8), dtype=np.uint8)
        two[1, 1] = 1
        self.cfg['reference'] = self.tif('ref', reference)
        self.cfg['shards'] = [self.tif('one', one), self.tif('two', two)]
        manifest = {'file_count': 2, 'files': [{'sha256': '1' * 64}, {'sha256': '2' * 64}]}
        mp = self.inputs / 'manifest.json'
        mp.write_text(json.dumps(manifest))
        self.cfg['source_manifest'] = {'path': str(mp), 'sha256': c.sha(mp)}
        for i, shard in enumerate(self.cfg['shards']):
            shard['status'] = 'candidate-only'
            doc = {
                'status': 'candidate-only',
                'source_sha256': str(i + 1) * 64,
                'output_sha256': shard['sha256'],
                'grid': self.cfg['grid'],
                'policy': 'synthetic',
                'script_sha256': 'c' * 64,
                'rows_in_source': 10,
                'counts': {'rows': 10},
                'invalid_feature_ids': None,
            }
            rp = self.inputs / ('report' + str(i) + '.json')
            rp.write_text(json.dumps(doc))
            shard['report'] = {'path': str(rp), 'sha256': c.sha(rp)}
        self.config = self.inputs / 'config.json'
        self.config.write_text(json.dumps(self.cfg))

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
        return {'path': str(p), 'sha256': c.sha(p)}

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

    def test_exact_comparison(self):
        out = self.d / 'out'
        c.run(self.config, out)
        r = json.loads((out / 'report.json').read_text())
        self.assertEqual(
            (
                r['candidate_water_cells'],
                r['reference_water_cells'],
                r['candidate_extra_cells'],
                r['candidate_missing_cells'],
            ),
            (4, 4, 1, 1),
        )
        self.assertEqual(r['mismatch_spans'], 2)
        spans = [json.loads(x) for x in (out / 'mismatch-spans.jsonl').read_text().splitlines()]
        self.assertEqual({(x['reference'], x['candidate']) for x in spans}, {(1, 0), (0, 1)})
        with self.assertRaises(FileExistsError):
            c.run(self.config, out)
        with self.assertRaises(ValueError):
            c.run(self.config, self.inputs / 'nested')
        with self.assertRaises(ValueError):
            c.run(self.config, self.d)

    def test_without_reference(self):
        self.cfg.pop('reference')
        self.config.write_text(json.dumps(self.cfg))
        out = self.d / 'no-reference'
        c.run(self.config, out)
        r = json.loads((out / 'report.json').read_text())
        self.assertEqual(r['candidate_water_cells'], 4)
        self.assertNotIn('reference_water_cells', r)
        self.assertEqual(r['grid'], self.cfg['grid'])
        self.assertEqual(r['shard_count'], 2)

    def test_fails_closed_on_incomplete_or_changed(self):
        self.cfg['shards'][0]['status'] = 'incomplete'
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaises(ValueError):
            c.run(self.config, self.d / 'bad')
        self.cfg['shards'][0]['status'] = 'candidate-only'
        self.cfg['shards'][0]['sha256'] = '0' * 64
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaises(ValueError):
            c.run(self.config, self.d / 'bad')
        self.assertFalse((self.d / 'bad').exists())

    def test_requires_complete_pinned_lineage(self):
        # Duplicate source records, absent reports, and incomplete reports must fail closed.
        original = self.cfg['shards'][1]['report']
        self.cfg['shards'][1]['report'] = self.cfg['shards'][0]['report']
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'inconsistent shard report|cover'):
            c.run(self.config, self.d / 'duplicate')
        self.cfg['shards'][1]['report'] = original
        rp = Path(original['path'])
        doc = json.loads(rp.read_text())
        doc['status'] = 'incomplete-input-issues'
        rp.write_text(json.dumps(doc))
        original['sha256'] = c.sha(rp)
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'incomplete or inconsistent'):
            c.run(self.config, self.d / 'incomplete')
        doc['status'] = 'candidate-only'
        doc['policy'] = 'different'
        rp.write_text(json.dumps(doc))
        original['sha256'] = c.sha(rp)
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'inconsistent shard selection policy'):
            c.run(self.config, self.d / 'policy')
        self.assertFalse((self.d / 'policy').exists())
        doc['policy'] = 'synthetic'
        doc['script_sha256'] = 'd' * 64
        rp.write_text(json.dumps(doc))
        original['sha256'] = c.sha(rp)
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'inconsistent shard rasterizer'):
            c.run(self.config, self.d / 'script')
        doc['script_sha256'] = 'c' * 64
        doc.pop('rows_in_source')
        doc['counts'].pop('rows')
        rp.write_text(json.dumps(doc))
        original['sha256'] = c.sha(rp)
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'incomplete or inconsistent'):
            c.run(self.config, self.d / 'missing-counts')

    def test_rejects_nonbinary(self):
        p = Path(self.cfg['shards'][0]['path'])
        ds = gdal.Open(str(p), gdal.GA_Update)
        a = ds.ReadAsArray()
        a[0, 0] = 2
        ds.GetRasterBand(1).WriteArray(a)
        ds = None
        self.cfg['shards'][0]['sha256'] = c.sha(p)
        rp = Path(self.cfg['shards'][0]['report']['path'])
        doc = json.loads(rp.read_text())
        doc['output_sha256'] = c.sha(p)
        rp.write_text(json.dumps(doc))
        self.cfg['shards'][0]['report']['sha256'] = c.sha(rp)
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'nonbinary'):
            c.run(self.config, self.d / 'bad')
        self.assertFalse((self.d / 'bad' / 'report.json').exists())

    def test_rejects_negative_values(self):
        for name in ('candidate', 'reference'):
            p = self.inputs / (name + '-negative.tif')
            ds = gdal.GetDriverByName('GTiff').Create(str(p), 8, 4, 1, gdal.GDT_Int16)
            ds.SetGeoTransform((-180, 45, 0, 90, 0, -45))
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(4326)
            ds.SetSpatialRef(srs)
            values = np.zeros((4, 8), dtype=np.int16)
            values[1, 1] = -1
            ds.GetRasterBand(1).WriteArray(values)
            ds = None
            item = {'path': str(p), 'sha256': c.sha(p)}
            if name == 'candidate':
                item['status'] = 'candidate-only'
                item['report'] = self.cfg['shards'][0]['report']
                rp = Path(item['report']['path'])
                doc = json.loads(rp.read_text())
                doc['output_sha256'] = c.sha(p)
                rp.write_text(json.dumps(doc))
                item['report']['sha256'] = c.sha(rp)
                self.cfg['shards'][0] = item
            else:
                self.cfg['reference'] = item
            self.config.write_text(json.dumps(self.cfg))
            with self.assertRaisesRegex(ValueError, 'nonbinary'):
                c.run(self.config, self.d / ('bad-' + name))
            if name == 'candidate':
                report = self.cfg['shards'][0]['report']
                self.cfg['shards'][0] = self.tif('recovered', np.zeros((4, 8), dtype=np.uint8))
                self.cfg['shards'][0]['status'] = 'candidate-only'
                self.cfg['shards'][0]['report'] = report
                rp = Path(report['path'])
                doc = json.loads(rp.read_text())
                doc['output_sha256'] = self.cfg['shards'][0]['sha256']
                rp.write_text(json.dumps(doc))
                report['sha256'] = c.sha(rp)


if __name__ == '__main__':
    unittest.main()
