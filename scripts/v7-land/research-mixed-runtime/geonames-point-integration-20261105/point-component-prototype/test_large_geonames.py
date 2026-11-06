import hashlib,io,json,unittest,zipfile
from unittest.mock import patch
from types import SimpleNamespace
from geonames_extract import extract
class T(unittest.TestCase):
 def test_large_archive_small_island_record(self):
  row='987654321\tFictional Test Island\tFictional Test Island\t\t-45.678\t12.345\tT\tISL\tID\t\t\t\t\t\t0\t\t1\tAsia/Jakarta\t2023-05-11\n';b=io.BytesIO()
  with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_STORED) as z:z.writestr('readme.txt',b'x'*(5*1024*1024));z.writestr('ID.txt',row)
  raw=b.getvalue();g={'type':'Point','coordinates':[12.345,-45.678]};h=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest();r=extract(raw,hashlib.sha256(raw).hexdigest(),'987654321','Fictional Test Island','ID',h);self.assertEqual(r['geometry'],g)
 def test_compressed_limit(self):
  with self.assertRaisesRegex(ValueError,'source size'):extract(b'x'*(16*1024*1024+1),'0'*64,'1','x','ID','0'*64)
 def test_member_limit_before_open(self):
  fake=SimpleNamespace(filename='ID.txt',file_size=64*1024*1024+1,is_dir=lambda:False)
  class Z:
   def __enter__(self):return self
   def __exit__(self,*_):pass
   def infolist(self):return [fake]
   def open(self,*_):raise AssertionError('must reject oversized member first')
  raw=b'x'
  with patch('geonames_extract.zipfile.ZipFile',return_value=Z()):
   with self.assertRaisesRegex(ValueError,'country archive'):extract(raw,hashlib.sha256(raw).hexdigest(),'1','x','ID','0'*64)
 def test_duplicate_rejected_before_third_read(self):
  class Stream(io.BytesIO):
   count=0
   def readline(self,*args):
    self.count+=1
    if self.count>2:raise AssertionError('continued after second match')
    return super().readline(*args)
  row=b'1\tduplicate\n';stream=Stream(row*10000);fake=SimpleNamespace(filename='ID.txt',file_size=len(row)*10000,is_dir=lambda:False)
  class Z:
   def __enter__(self):return self
   def __exit__(self,*_):pass
   def infolist(self):return [fake]
   def open(self,*_):return stream
  raw=b'x'
  with patch('geonames_extract.zipfile.ZipFile',return_value=Z()):
   with self.assertRaisesRegex(ValueError,'record not unique'):extract(raw,hashlib.sha256(raw).hexdigest(),'1','x','ID','0'*64)
 def test_record_length_bound(self):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:z.writestr('ID.txt',b'x'*(1024*1024+1))
  raw=b.getvalue()
  with self.assertRaisesRegex(ValueError,'record too long'):extract(raw,hashlib.sha256(raw).hexdigest(),'1','x','ID','0'*64)
if __name__=='__main__':unittest.main()
