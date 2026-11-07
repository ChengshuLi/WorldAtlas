import hashlib,importlib.util,io,json,unittest,warnings,zipfile
from pathlib import Path
HERE=Path(__file__).parent
import geonames_extract as batch
single=batch
def geom(lon,lat):return hashlib.sha256(json.dumps({'type':'Point','coordinates':[lon,lat]},sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def row(rid='123',name='Island',lat='1.25',lon='127.5',fclass='T',feature='ISL',country='ZZ'):
 a=[rid,name,'','',lat,lon,fclass,feature,country]+['']*10;assert len(a)==19;return '\t'.join(a)+'\n'
def archive(data,name='ZZ.txt',extra=None):
 f=io.BytesIO()
 with warnings.catch_warnings():
  warnings.simplefilter('ignore')
  with zipfile.ZipFile(f,'w',zipfile.ZIP_DEFLATED) as z:
   z.writestr(name,data)
   if extra:z.writestr(*extra)
 return f.getvalue()
def digest(b):return hashlib.sha256(b).hexdigest()
class Tests(unittest.TestCase):
 def setUp(self):self.raw=archive(row());self.s={'record_id':'123','expected_name':'Island','expected_point_sha256':geom(127.5,1.25)}
 def b(self,raw=None,s=None,sha=None,country='ZZ'):
  raw=self.raw if raw is None else raw;return batch.extract_many(raw,sha or digest(raw),country,s if s is not None else [self.s])
 def test_valid_and_single_parity(self):self.assertEqual(self.b(),[single.extract(self.raw,digest(self.raw),'123','Island','ZZ',self.s['expected_point_sha256'])])
 def test_multiple_order(self):
  raw=archive(row()+row('456','Two',lat='-1',lon='128'));s2={'record_id':'456','expected_name':'Two','expected_point_sha256':geom(128.0,-1.0)}
  out=self.b(raw,[s2,self.s]);self.assertEqual([x['record_id'] for x in out],['456','123'])
  for s,x in zip([s2,self.s],out):self.assertEqual(x,single.extract(raw,digest(raw),s['record_id'],s['expected_name'],'ZZ',s['expected_point_sha256']))
 def test_duplicate_selected_id(self):
  with self.assertRaises(ValueError):self.b(s=[self.s,self.s])
 def test_missing(self):
  with self.assertRaises(ValueError):self.b(s=[dict(self.s,record_id='999')])
 def test_duplicate_record(self):
  with self.assertRaises(ValueError):self.b(raw=archive(row()+row()))
 def test_nonselected_duplicate_allowed(self):self.assertEqual(len(self.b(raw=archive(row()+row('456')+row('456')))),1)
 def test_wrong_name(self):
  with self.assertRaises(ValueError):self.b(s=[dict(self.s,expected_name='Wrong')])
 def test_wrong_geometry(self):
  with self.assertRaises(ValueError):self.b(s=[dict(self.s,expected_point_sha256='0'*64)])
 def test_bad_source_hash(self):
  with self.assertRaises(ValueError):self.b(sha='0'*64)
 def test_bad_zip(self):
  with self.assertRaises(ValueError):self.b(raw=b'notzip')
 def test_wrong_country_member(self):
  with self.assertRaises(ValueError):self.b(raw=archive(row(),name='XX.txt'))
 def test_duplicate_country_member(self):
  with self.assertRaises(ValueError):self.b(raw=archive(row(),extra=('ZZ.txt',row())))
 def test_bad_utf8_anywhere(self):
  with self.assertRaises(ValueError):self.b(raw=archive(row().encode()+b'999\t\xff\n'))
 def test_oversized_line(self):
  with self.assertRaises(ValueError):self.b(raw=archive(row()+('x'*(1024*1024+1))))
 def test_bad_field_count(self):
  with self.assertRaises(ValueError):self.b(raw=archive('123\tIsland\n'))
 def test_bad_class(self):
  with self.assertRaises(ValueError):self.b(raw=archive(row(fclass='P')))
 def test_bad_coordinate(self):
  for x in ('nan','180','1e2','181'):
   with self.subTest(x=x),self.assertRaises(ValueError):self.b(raw=archive(row(lon=x)))
 def test_one_bad_aborts_batch(self):
  raw=archive(row()+row('456','Two'));s2={'record_id':'456','expected_name':'Bad','expected_point_sha256':self.s['expected_point_sha256']}
  with self.assertRaises(ValueError):self.b(raw=raw,s=[self.s,s2])
if __name__=='__main__':unittest.main()
