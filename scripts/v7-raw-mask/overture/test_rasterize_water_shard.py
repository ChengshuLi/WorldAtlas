import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from osgeo import gdal, ogr
import rasterize_water_shard as build

class WaterShardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.path = Path(self.tmp.name)
        self.inputs=self.path/'inputs';self.inputs.mkdir()
        cfg={'schema':'water-shard-candidate-v2', 'grid':{'width':32,'height':16,'west':-180,'north':90,'step':11.25},
             'tile_size':4, 'selection_notes':'synthetic test',
             'policy':{'method':'overture-inland-subtype-v1'}}
        self.config=self.inputs/'config.json';self.config.write_text(json.dumps(cfg))
    def tearDown(self):
        self.tmp.cleanup()
    def fixture(self):
        def wkt(s): return bytes(ogr.CreateGeometryFromWkt(s).ExportToWkb())
        osm = [{'property':'', 'dataset':'OpenStreetMap'}]; alt = [{'property':'', 'dataset':'Other'}]
        polygon = wkt('POLYGON ((-170 80,-120 80,-120 40,-170 40,-170 80))')
        rows = [
          {'id':'lake', 'subtype':'lake','class':'lake','sources':osm,'geometry':polygon},
          {'id':'ocean', 'subtype':'ocean','class':'ocean','sources':osm,'geometry':polygon},
          {'id':'label', 'subtype':'physical','class':'bay','sources':osm,'geometry':polygon},
          {'id':'other', 'subtype':'lake','class':'sea','sources':alt,'geometry':polygon},
          {'id':'line', 'subtype':'river','class':'river','sources':osm,'geometry':wkt('LINESTRING (-170 80,-120 40)')},
          {'id':'pool', 'subtype':'human_made','class':'swimming_pool','sources':osm,'geometry':polygon}]
        table = pa.Table.from_pylist(rows).replace_schema_metadata({b'geo':json.dumps({'primary_column':'geometry','columns':{'geometry':{'encoding':'WKB'}}}).encode()})
        p = self.inputs/'water.parquet'; pq.write_table(table,p)
        return p, hashlib.sha256(p.read_bytes()).hexdigest()
    def test_policy_and_batch_invariance(self):
        p, digest = self.fixture()
        for n in (1, 10):
            out = self.path/f'o{n}'; build.run(p,digest,out,self.config,n)
            report = json.loads((out/'report.json').read_text())
            self.assertEqual(report['counts']['polygons'],3)
            self.assertEqual(report['counts']['excluded_classification'],2)
            self.assertEqual(report['counts']['non_polygon'],1)
            self.assertNotIn('no_selected_geometry_provenance',report['counts'])
            self.assertEqual(report['status'],'candidate-only')
        a = gdal.Open(str(self.path/'o1/water.tif')).ReadAsArray()
        b = gdal.Open(str(self.path/'o10/water.tif')).ReadAsArray()
        np.testing.assert_array_equal(a,b); self.assertGreater(a.sum(),0); self.assertLess(a.sum(),a.size)
        target = gdal.GetDriverByName('MEM').Create('', 32,16,1,gdal.GDT_Byte)
        target.SetGeoTransform((-180,11.25,0,90,0,-11.25))
        ds = ogr.GetDriverByName('Memory').CreateDataSource(''); layer = ds.CreateLayer('x',geom_type=ogr.wkbPolygon)
        feat = ogr.Feature(layer.GetLayerDefn()); feat.SetGeometry(ogr.CreateGeometryFromWkt('POLYGON ((-170 80,-120 80,-120 40,-170 40,-170 80))')); layer.CreateFeature(feat)
        gdal.RasterizeLayer(target,[1],layer,burn_values=[1])
        np.testing.assert_array_equal(a,target.ReadAsArray())
    def test_batch_config_and_override(self):
        p,digest=self.fixture();cfg=json.loads(self.config.read_text());cfg['batch_size']=2
        self.config.write_text(json.dumps(cfg))
        for name,override,expected in [('config',None,2),('override',3,3)]:
            out=self.path/name;build.run(p,digest,out,self.config,override)
            self.assertEqual(json.loads((out/'report.json').read_text())['batch_size'],expected)
        cfg['batch_size']=True;self.config.write_text(json.dumps(cfg))
        with self.assertRaisesRegex(ValueError,'positive integer'):
            build.run(p,digest,self.path/'invalid-batch',self.config)
        self.assertFalse((self.path/'invalid-batch').exists())

    def test_subtype_only_accepts_without_sources_or_class(self):
        polygon=bytes(ogr.CreateGeometryFromWkt('POLYGON ((-170 80,-120 80,-120 40,-170 40,-170 80))').ExportToWkb())
        rows=[{'id':'valid','subtype':'lake','geometry':polygon},{'id':'ocean','subtype':'ocean','geometry':polygon}, {'id':'label','subtype':'physical','geometry':polygon}]
        table=pa.Table.from_pylist(rows).replace_schema_metadata({b'geo':json.dumps({'primary_column':'geometry','columns':{'geometry':{'encoding':'WKB'}}}).encode()})
        p=self.inputs/'minimal.parquet';pq.write_table(table,p);out=self.path/'minimal-output';build.run(p,hashlib.sha256(p.read_bytes()).hexdigest(),out,self.config)
        report=json.loads((out/'report.json').read_text());self.assertEqual(report['counts']['polygons'],1);self.assertEqual(report['counts']['excluded_classification'],2)
        self.assertEqual(build.selected('lake'),None);self.assertEqual(build.selected(None),'missing_classification');self.assertEqual(build.selected(''),'missing_classification')
    def test_old_policy_rejected_instead_of_silently_reinterpreted(self):
        p,digest=self.fixture();cfg=json.loads(self.config.read_text());cfg['schema']='water-shard-candidate-v1';self.config.write_text(json.dumps(cfg));out=self.path/'old-policy'
        with self.assertRaisesRegex(ValueError,'supported configuration'):build.run(p,digest,out,self.config)
        self.assertFalse(out.exists())
    def test_invalid_geometry_is_reported_and_not_claimed_complete(self):
        p,_ = self.fixture()
        table = pq.read_table(p).to_pylist()
        table[0]['geometry'] = bytes(ogr.CreateGeometryFromWkt('POLYGON ((-170 80,-120 40,-170 40,-120 80,-170 80))').ExportToWkb())
        table = pa.Table.from_pylist(table).replace_schema_metadata({b'geo':json.dumps({'primary_column':'geometry','columns':{'geometry':{'encoding':'WKB'}}}).encode()})
        p = self.inputs/'invalid.parquet'; pq.write_table(table,p)
        digest = hashlib.sha256(p.read_bytes()).hexdigest(); out=self.path/'invalid-output'
        build.run(p,digest,out,self.config,10)
        report=json.loads((out/'report.json').read_text())
        self.assertEqual(report['status'],'incomplete-input-issues')
        self.assertEqual(json.loads((out/'invalid-feature-ids.json').read_text()), ['lake'])

    def test_free_space_guard(self):
        p,digest=self.fixture();cfg=json.loads(self.config.read_text());cfg['minimum_free_bytes']=1 << 60
        self.config.write_text(json.dumps(cfg));out=self.path/'no-space'
        with self.assertRaisesRegex(ValueError,'free disk below configured reserve'):
            build.run(p,digest,out,self.config)
        self.assertFalse(out.exists())

    def test_integrity_and_collision(self):
        p,digest = self.fixture()
        with self.assertRaises(ValueError): build.run(p, '0'*64, self.path/'bad',self.config)
        self.assertFalse((self.path/'bad').exists())
        existing=self.path/'existing';existing.mkdir()
        with self.assertRaises(FileExistsError): build.run(p,digest,existing,self.config)
        with self.assertRaises(ValueError): build.run(p,digest,self.path,self.config)
        with self.assertRaises(ValueError): build.run(p,digest,self.inputs/'nested-output',self.config)
        self.config.write_text('{}')
        with self.assertRaises(ValueError): build.run(p,digest,self.path/'badconfig',self.config)
        self.assertFalse((self.path/'badconfig').exists())
if __name__ == '__main__': unittest.main()
