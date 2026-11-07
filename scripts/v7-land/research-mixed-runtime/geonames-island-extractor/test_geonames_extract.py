import hashlib,io,json,unittest,zipfile
from geonames_extract import extract
def make(records):
 f=io.BytesIO()
 with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr('ZZ.txt','\n'.join(records)+'\n')
 return f.getvalue()
def row(id='123',name='Sample',lat='-9.5',lon='-140.5',code='ISL'):
 return '\t'.join([id,name,name,'',lat,lon,'T',code,'ZZ','','','','','','0','','','Pacific/Test','2020-01-01'])
def call(raw,id='123',name='Sample',point=None):
 if point is None:point={'type':'Point','coordinates':[-140.5,-9.5]}
 return extract(raw,hashlib.sha256(raw).hexdigest(),id,name,'ZZ',hashlib.sha256(json.dumps(point,sort_keys=True,separators=(',',':')).encode()).hexdigest())
class Test(unittest.TestCase):
 def test_exact(self):self.assertEqual(call(make([row()]))['record_id'],'123')
 def test_duplicate(self):
  with self.assertRaises(ValueError):call(make([row(),row()]))
 def test_wrong_name(self):
  with self.assertRaises(ValueError):call(make([row()]),name='Other')
 def test_wrong_class(self):
  with self.assertRaises(ValueError):call(make([row(code='ADM2')]))
 def test_wrong_geometry(self):
  with self.assertRaises(ValueError):call(make([row()]),point={'type':'Point','coordinates':[1,2]})
 def test_bad_coordinate(self):
  with self.assertRaises(ValueError):call(make([row(lat='nan')]))
 def test_corrupt(self):
  with self.assertRaises(ValueError):call(b'not zip')
 def test_wrong_hash(self):
  with self.assertRaises(ValueError):extract(make([row()]),'0'*64,'123','Sample','ZZ','0'*64)
if __name__=='__main__':unittest.main()
