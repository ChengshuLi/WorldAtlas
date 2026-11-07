import hashlib,json,tempfile,unittest
from pathlib import Path
from polygon_source import extract,canonical
class SourceTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)/'raw.json';self.g={'type':'Polygon','coordinates':[[[0,0],[1,0],[1,1],[0,0]]]};self.f={'id_property':'id','source_feature_id':'X','geometry_sha256':hashlib.sha256(canonical(self.g)).hexdigest()};self.d={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'id':'X'},'geometry':self.g}]};self.save()
 def save(self):
  self.p.write_text(json.dumps(self.d));self.h=hashlib.sha256(self.p.read_bytes()).hexdigest()
 def test_extract(self):self.assertEqual(extract(self.p,self.h,self.f)[1]['vertices'],4)
 def test_wrong_hash(self):
  with self.assertRaisesRegex(ValueError,'hash mismatch'):extract(self.p,'0'*64,self.f)
 def test_duplicate_feature(self):
  self.d['features'].append(self.d['features'][0]);self.save()
  with self.assertRaisesRegex(ValueError,'ambiguous'):extract(self.p,self.h,self.f)
 def test_unsupported_crs(self):
  self.d['crs']={'type':'name','properties':{'name':'EPSG:3857'}};self.save()
  with self.assertRaisesRegex(ValueError,'CRS'):extract(self.p,self.h,self.f)
 def test_explicit_null_crs_rejected(self):
  self.d['crs']=None;self.save()
  with self.assertRaisesRegex(ValueError,'CRS'):extract(self.p,self.h,self.f)
 def test_null_feature_id_cannot_match(self):
  self.d['features'][0]['properties']['id']=None;self.f['source_feature_id']='None';self.save()
  with self.assertRaisesRegex(ValueError,'ambiguous'):extract(self.p,self.h,self.f)
 def test_dateline_rejected(self):
  self.g['coordinates'][0][1]=[179,0];self.g['coordinates'][0][2]=[-179,1];self.save()
  with self.assertRaisesRegex(ValueError,'dateline'):extract(self.p,self.h,self.f)
 def test_size_guard(self):
  with self.assertRaisesRegex(ValueError,'too large'):extract(self.p,self.h,self.f,max_bytes=5)
if __name__=='__main__':unittest.main()
