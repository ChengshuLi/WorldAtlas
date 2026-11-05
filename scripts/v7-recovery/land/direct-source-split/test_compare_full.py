"""Synthetic RLE fixtures only; no project geographic records."""
import builtins, hashlib, io, json, random, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import compare_full, watch_compare

class CompareTest(unittest.TestCase):
 def test_monitor_rejects_low_memory_before_launch(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);cfg=root/'request';cfg.write_text(json.dumps({'limits':{'minimum_memory_kib':1887437,'minimum_free_bytes':2*1024**3,'max_rss_kib':524288}}))
   with patch.object(watch_compare,'memory_available',return_value=1887436):
    with self.assertRaisesRegex(ValueError,'resource floor before launch'):watch_compare.run(cfg,root/'out',524288)
   self.assertFalse((root/'out').exists())
 def test_direct_comparison_requires_guardian(self):
  with self.assertRaisesRegex(ValueError,'monitored guardian'):compare_full.run('/not-a-request','/not-an-output')
 def test_strict_json_rejects_duplicate_and_nonfinite(self):
  with self.assertRaisesRegex(ValueError,'duplicate JSON key'):compare_full.strict_json('{"a":1,"a":2}')
  with self.assertRaisesRegex(ValueError,'nonfinite JSON number'):compare_full.strict_json('{"a":NaN}')
 def test_different_segmentation_equal_cells(self):
  a=np.array([[2,1],[5,1]],dtype='<u4');b=np.array([[5,1]],dtype='<u4');self.assertEqual(compare_full.compare_row(a,b,5),(5,[]))
 def test_random_rows_against_dense_reference(self):
  rng=random.Random(773)
  def encode(values):
   out=[]
   for i,v in enumerate(values):
    if i and v!=values[i-1]:out.append((i,values[i-1]))
   out.append((len(values),values[-1]));return np.array(out,dtype='<u4')
  for _ in range(200):
   aa=[rng.randrange(4) for _ in range(37)];bb=[rng.randrange(4) for _ in range(37)];matches,_=compare_full.compare_row(encode(aa),encode(bb),len(aa));self.assertEqual(matches,sum(x==y for x,y in zip(aa,bb)))
 def test_full_check_and_bad_pin(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);inp=root/'input';inp.mkdir();paths={}
   for tag in ('baseline','candidate'):
    r=inp/(tag+'rows');v=inp/(tag+'runs');np.array([0,1,2],dtype='<u4').tofile(r);np.array([[4,1],[4,2 if tag=='baseline' else 3]],dtype='<u4').tofile(v);paths[tag+'_rows']=r;paths[tag+'_runs']=v
   sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pins={k:{'path':str(v),'sha256':sha(v)} for k,v in paths.items()};cfg={'schema':'full-grid-comparison-request-v1','grid':{'width':4,'height':2},'inputs':pins,'limits':{'minimum_memory_kib':1887437,'minimum_free_bytes':2*1024**3,'max_rss_kib':870400}};request=inp/'request';request.write_text(json.dumps(cfg));original_open=builtins.open
   def fake_open(path,*args,**kwargs):
    if str(path)=='/proc/meminfo':return io.StringIO('MemAvailable: 4000000 kB\n')
    return original_open(path,*args,**kwargs)
   with patch('builtins.open',side_effect=fake_open),patch.object(compare_full,'require_guardian'):
    result=compare_full.run(request,root/'out');self.assertEqual((result['status'],result['total_cells'],result['different_cells']),('different',8,4))
    paths['candidate_runs'].write_bytes(b'tamper')
    with self.assertRaisesRegex(ValueError,'input pin mismatch'):compare_full.run(request,root/'bad')
    self.assertFalse((root/'bad').exists())
if __name__=='__main__':unittest.main()
