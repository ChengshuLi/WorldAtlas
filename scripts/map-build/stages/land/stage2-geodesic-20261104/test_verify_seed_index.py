import tempfile,struct,pathlib,unittest
from verify_seed_index import verify
class Verify(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.d=pathlib.Path(self.tmp.name);self.tiles=self.d/'tiles';self.tiles.mkdir();rows=[[(2,0),(6,18),(16,0)],[(4,17),(12,0),(16,20)]]+[[(16,0)] for _ in range(6)];offs=[0];run=[];parts={}
  for y,seq in enumerate(rows):
   a=0
   for b,code in seq:
    run.append((b,code))
    if code:
     x=a
     while x<b:
      z=min(b,(x//4+1)*4);p=(y//4,x//4);parts.setdefault(p,[]).append((y,x,z,code));x=z
    a=b
   offs.append(len(run))
  (self.d/'rows').write_bytes(b''.join(struct.pack('<I',x) for x in offs));(self.d/'runs').write_bytes(b''.join(struct.pack('<II',*x) for x in run))
  for (y,x),z in parts.items():(self.tiles/f'{y:05}-{x:05}.bin').write_bytes(b''.join(struct.pack('<IIII',*v) for v in z))
 def tearDown(self):self.tmp.cleanup()
 def runv(self):return verify(self.d/'rows',self.d/'runs',self.tiles,16,8,4)
 def test_valid(self):self.assertEqual(self.runv()['status'],'verified')
 def test_corruption(self):
  f=next(self.tiles.glob('*.bin'));z=bytearray(f.read_bytes());z[-1]^=1;f.write_bytes(z)
  with self.assertRaisesRegex(ValueError,'mismatch'):self.runv()
 def test_missing(self):
  next(self.tiles.glob('*.bin')).unlink()
  with self.assertRaisesRegex(ValueError,'mismatch'):self.runv()
 def test_extra(self):
  (self.tiles/'00001-00002.bin').write_bytes(b'1234')
  with self.assertRaises(ValueError):self.runv()
 def test_every_offset_is_validated(self):
  raw=bytearray((self.d/'rows').read_bytes());raw[8:12]=struct.pack('<I',0);(self.d/'rows').write_bytes(raw)
  with self.assertRaisesRegex(ValueError,'offsets'):self.runv()
 def test_incomplete_and_redundant_rows_rejected(self):
  path=self.d/'runs';raw=path.read_bytes()
  for location,value in ((0,0),(8,16),(4,99),(12,0)):
   changed=bytearray(raw);changed[location:location+4]=struct.pack('<I',value);path.write_bytes(changed)
   with self.assertRaises(ValueError):self.runv()
  path.write_bytes(raw)
 def test_no_process_or_ctypes(self):
  from unittest import mock
  with mock.patch('subprocess.Popen',side_effect=AssertionError('no process')),mock.patch('ctypes.CDLL',side_effect=AssertionError('no bridge')):
   self.assertEqual(self.runv()['status'],'verified')
 def test_random_dense_oracle_across_tile_shapes(self):
  import numpy as np
  random=np.random.default_rng(84319)
  for width,height,tile in ((1,1,1),(7,11,3),(20,9,4),(31,17,8),(9,5,0xffffffff)):
   with self.subTest(width=width,height=height,tile=tile),tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td);directory=root/'tiles';directory.mkdir();dense=random.choice([0,17,18,19,20,21,22],size=(height,width))
    offsets=[0];runs=[];tiles={}
    for y,row in enumerate(dense):
     # Independent cell oracle groups each row, then splits at tile edges.
     x=0
     while x<width:
      stop=x+1
      while stop<width and row[stop]==row[x]:stop+=1
      runs.append((stop,int(row[x])))
      if row[x]:
       cursor=x
       while cursor<stop:
        end=min(stop,(cursor//tile+1)*tile);key=(y//tile,cursor//tile)
        tiles.setdefault(key,[]).append((y,cursor,end,int(row[x])));cursor=end
      x=stop
     offsets.append(len(runs))
    np.asarray(offsets,dtype='<u4').tofile(root/'rows');np.asarray(runs,dtype='<u4').tofile(root/'runs')
    for (ty,tx),values in tiles.items():np.asarray(values,dtype='<u4').tofile(directory/f'{ty:05d}-{tx:05d}.bin')
    report=verify(root/'rows',root/'runs',directory,width,height,tile)
    self.assertEqual(report,{'status':'verified','tiles':len(tiles),'tile_records':sum(map(len,tiles.values()))})
if __name__=='__main__':unittest.main()
