import hashlib,json,tempfile,unittest,zipfile
from unittest.mock import patch
from pathlib import Path
from osgeo import ogr,osr
import land_archive_source as t
class Contract(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.dir=Path(self.tmp.name)/'land-polygons-split-4326';self.dir.mkdir();self.shp=self.dir/'land_polygons.shp';d=ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(str(self.shp));s=osr.SpatialReference();s.ImportFromEPSG(4326);l=d.CreateLayer('land_polygons',s,ogr.wkbPolygon);f=ogr.Feature(l.GetLayerDefn());f.SetGeometry(ogr.CreateGeometryFromWkt('POLYGON ((0 0, 0 1, 1 1, 1 0, 0 0))'));l.CreateFeature(f);d=None
  self.zip=Path(self.tmp.name)/'source.zip'
  with zipfile.ZipFile(self.zip,'w',zipfile.ZIP_DEFLATED) as z:
   for p in self.dir.iterdir():z.write(p,'land-polygons-split-4326/'+p.name)
  self.sha=hashlib.sha256(self.zip.read_bytes()).hexdigest();d=ogr.Open(str(self.shp));f=d.GetLayer(0).GetFeature(0);g=json.loads(f.GetGeometryRef().ExportToJson());self.feature={'source_feature_id':'0','geometry_sha256':hashlib.sha256(t.canonical(g)).hexdigest()};d=None
 def tearDown(self):self.tmp.cleanup()
 def go(self,features=None,sha=None,guard=lambda:None):return t.extract(self.zip,self.shp,sha or self.sha,features or [self.feature],guard)
 def test_valid(self):
  g,trace=self.go()[0];self.assertEqual(g['type'],'Polygon');self.assertEqual(trace['source_feature_id'],'0');self.assertEqual(trace['source_sha256'],self.sha)
 def test_wrong_archive_hash(self):
  with self.assertRaises(ValueError):self.go(sha='0'*64)
 def test_wrong_geometry_hash(self):
  with self.assertRaisesRegex(ValueError,'geometry hash'):self.go([dict(self.feature,geometry_sha256='0'*64)])
 def test_missing_feature(self):
  with self.assertRaises((ValueError,RuntimeError)):self.go([dict(self.feature,source_feature_id='999')])
 def test_duplicate_and_leading_zero_fids(self):
  with self.assertRaises(ValueError):self.go([self.feature,self.feature])
  with self.assertRaises(ValueError):self.go([dict(self.feature,source_feature_id='00')])
 def test_materialized_byte_mismatch(self):
  with self.shp.open('r+b') as f:f.seek(-1,2);x=f.read(1);f.seek(-1,2);f.write(bytes([x[0]^1]))
  with self.assertRaisesRegex(ValueError,'member hash mismatch'):self.go()
 def test_shx_substitution(self):
  p=self.shp.with_suffix('.shx');p.write_bytes(b'x'*p.stat().st_size)
  with self.assertRaisesRegex(ValueError,'member hash mismatch'):self.go()
 def test_archive_mutation(self):
  with self.zip.open('ab') as f:f.write(b'x')
  with self.assertRaisesRegex(ValueError,'archive hash'):self.go()
 def test_same_size_mutation_after_parsing(self):
  original=t.path_hash;hits=0
  def mutate(path,guard):
   nonlocal hits
   if path==self.shp:
    hits+=1
    if hits==2:
     with path.open('r+b') as f:f.seek(-1,2);v=f.read(1);f.seek(-1,2);f.write(bytes([v[0]^1]))
   return original(path,guard)
  with patch.object(t,'path_hash',side_effect=mutate):
   with self.assertRaisesRegex(ValueError,'changed during extraction'):self.go()
 def test_non_ascii_fid_and_bad_digest(self):
  with self.assertRaises(ValueError):self.go([dict(self.feature,source_feature_id='١')])
  with self.assertRaises(ValueError):self.go([dict(self.feature,geometry_sha256='z'*64)])
 def test_duplicate_zip_member_rejected(self):
  import warnings
  with warnings.catch_warnings():
   warnings.simplefilter('ignore')
   with zipfile.ZipFile(self.zip,'a') as z:z.write(self.shp.with_suffix('.shx'),'land-polygons-split-4326/land_polygons.shx')
  sha=hashlib.sha256(self.zip.read_bytes()).hexdigest()
  with self.assertRaisesRegex(ValueError,'missing or oversized'):self.go(sha=sha)
 def test_validly_archived_wrong_crs(self):
  s=osr.SpatialReference();s.ImportFromEPSG(3857);self.shp.with_suffix('.prj').write_text(s.ExportToWkt())
  with zipfile.ZipFile(self.zip,'w',zipfile.ZIP_DEFLATED) as z:
   for p in self.dir.iterdir():z.write(p,'land-polygons-split-4326/'+p.name)
  sha=hashlib.sha256(self.zip.read_bytes()).hexdigest()
  with self.assertRaisesRegex(ValueError,'CRS'):self.go(sha=sha)
 def test_wrong_crs(self):
  p=self.shp.with_suffix('.prj');p.write_text('invalid CRS')
  with self.assertRaises((ValueError,RuntimeError)):self.go()
if __name__=='__main__':unittest.main()
