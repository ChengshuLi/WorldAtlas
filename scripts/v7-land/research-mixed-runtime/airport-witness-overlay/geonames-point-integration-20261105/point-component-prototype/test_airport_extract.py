import hashlib, io, json, unittest, zipfile
from geonames_airport_extract import extract

def archive(row):
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('ZZ.txt', row)
 return b.getvalue()
def row(cl='S',code='AIRP',name='Test Airport',lat='22.5',lon='-112.5',rid='123'):
 return '\t'.join([rid,name,name,'',lat,lon,cl,code,'ZZ','','','','','','0','','','Pacific/Test','2020-01-01'])+'\n'
def geomhash(lon=-112.5,lat=22.5):
 return hashlib.sha256(json.dumps({'type':'Point','coordinates':[lon,lat]},sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
class ExtractTest(unittest.TestCase):
 def run_source(self, r, rid='123', name='Test Airport', country='ZZ', gh=None):
  raw=archive(r);return extract(raw,hashlib.sha256(raw).hexdigest(),rid,name,country,gh or geomhash())
 def test_airport(self):
  x=self.run_source(row());self.assertEqual((x['schema'],x['feature_class'],x['feature_code']),('geonames-airport-point-extraction-v1','S','AIRP'));self.assertIn('does not identify an island',x['limitations'][0])
 def test_island_rejected(self):
  with self.assertRaisesRegex(ValueError,'airport identity mismatch'):self.run_source(row('T','ISL'))
 def test_wrong_name_rejected(self):
  with self.assertRaisesRegex(ValueError,'airport identity mismatch'):self.run_source(row(name='Other'))
 def test_duplicate_rejected(self):
  with self.assertRaisesRegex(ValueError,'not unique'):self.run_source(row()+row())
 def test_bad_coordinate_rejected(self):
  with self.assertRaisesRegex(ValueError,'coordinate range'):self.run_source(row(lat='91'))
 def test_changed_geometry_rejected(self):
  with self.assertRaisesRegex(ValueError,'geometry hash'):self.run_source(row(lon='-112.4'))
 def test_tampered_source_rejected(self):
  with self.assertRaisesRegex(ValueError,'source hash'):extract(archive(row()),'0'*64,'123','Test Airport','ZZ',geomhash())
if __name__=='__main__':unittest.main()
