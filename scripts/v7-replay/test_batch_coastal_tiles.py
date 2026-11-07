import errno,fcntl,hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest import mock
import numpy as np
import batch_coastal_tiles as b
from test_coastal_core import snap

class BatchTest(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.d=Path(self.t.name);self.width=16;self.height=8
  rows=(np.arange(9,dtype='<u4')*2).tobytes();physical=np.tile(np.array([8,17,16,1],dtype='<u4'),8).tobytes();land=np.tile(np.array([8,17,16,0],dtype='<u4'),8).tobytes();blobs={'physical_rows':rows,'physical_runs':physical,'land_rows':rows,'land_runs':land};self.paths={};self.pins={}
  for k,data in blobs.items():
   p=self.d/k;p.write_bytes(data);self.paths[k]=p;self.pins[k]=hashlib.sha256(data).hexdigest()
  self.plan={'tiles':[[7,9,3,4],[7,9,4,5]],'pad_degrees':30,'chunk':10};self.snapshot=snap();self.calls=0
 def check(self):self.calls+=1
 def run_batch(self,**kw):return b.run_batch(self.snapshot,'a'*64,self.paths,self.pins,self.plan,'b'*64,self.d/'batch',self.width,self.height,self.check,metadata_pins={'physical_report':'c'*64,'land_report':'d'*64},**kw)
 def test_end_to_end_two_tiles_and_single_completion(self):
  with mock.patch.object(b,'sealed_copy',wraps=b.sealed_copy) as copies:result=self.run_batch()
  self.assertEqual(copies.call_count,4);self.assertEqual(self.calls,2);self.assertEqual(len(result['tiles']),2);self.assertTrue((self.d/'batch/batch-complete.json').is_file());self.assertEqual(result['status'],'complete-research-not-published')
  for x in result['tiles']:
   p=self.d/'batch'/('tile-%04d'%x['tile'])/'manifest.json';self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),x['manifest_sha256']);self.assertEqual(json.loads(p.read_bytes())['status'],'partial-unverified-research-not-published')
 def test_independent_tile_halos_and_elapsed_time(self):
  self.plan={'tiles':[{'core':[7,9,3,4],'latitude_pad_degrees':30,'longitude_pad_degrees':180}], 'chunk':10}
  result=self.run_batch()
  manifest=json.loads((self.d/'batch/tile-0000/manifest.json').read_bytes())
  self.assertGreaterEqual(result['processing_elapsed_seconds'],0)
  self.assertGreaterEqual(manifest['processing_elapsed_seconds'],0)
  self.assertEqual(manifest['shore_crop_bounds'],[0,16,1,6])
 def test_sealed_content_cannot_change(self):
  fd,n=b.sealed_copy(self.paths['physical_runs'],self.pins['physical_runs']);self.addCleanup(os.close,fd);self.assertEqual(fcntl.fcntl(fd,fcntl.F_GET_SEALS)&b.F_SEALS,b.F_SEALS)
  with self.assertRaises(OSError):os.write(fd,b'x')
  with self.assertRaises(OSError):os.ftruncate(fd,0)
  with self.assertRaises(OSError):fcntl.fcntl(fd,fcntl.F_ADD_SEALS,0)
 def test_bad_hash_fails_before_outputs(self):
  self.pins['physical_runs']='0'*64
  with self.assertRaisesRegex(ValueError,'SHA-256 mismatch'):self.run_batch()
  self.assertFalse((self.d/'batch').exists())
 def test_large_plan_and_chunk_are_not_rejected(self):
  plan={'tiles':[[x,x+1,0,1] for x in range(300)],'pad_degrees':181,'chunk':100001}
  self.assertEqual(len(b.validate_plan(plan,300,1)),300)
 def test_plan_rejects_overlapping_or_invalid_tiles(self):
  self.plan['tiles']=[[7,10,3,5],[8,11,4,6]]
  with self.assertRaisesRegex(ValueError,'overlapping'):self.run_batch()
  self.plan['tiles']=[[7,100,3,5]]
  with self.assertRaisesRegex(ValueError,'outside grid'):self.run_batch()
  self.assertEqual(self.calls,0)
 def test_changed_metadata_no_completion_record(self):
  def metadata():
   self.calls+=1
   if self.calls==2:raise ValueError('metadata changed')
  with self.assertRaisesRegex(ValueError,'metadata changed'):
   b.run_batch(self.snapshot,'a'*64,self.paths,self.pins,self.plan,'b'*64,self.d/'batch',self.width,self.height,metadata,metadata_pins={'physical_report':'c'*64,'land_report':'d'*64})
  self.assertFalse((self.d/'batch/batch-complete.json').exists());self.assertTrue((self.d/'batch/tile-0000/manifest.json').is_file())
 def test_tile_code_changed_during_batch_fails_closed(self):
  original=b.tile.run
  def changed(*args,**kw):
   result=original(*args,**kw);result['core_sha256']='0'*64;return result
  with mock.patch.object(b.tile,'run',side_effect=changed):
   with self.assertRaisesRegex(ValueError,'tile code pin changed'):self.run_batch()
  self.assertFalse((self.d/'batch/batch-complete.json').exists())
 def test_grid_source_replaced_after_snapshot_does_not_affect_tiles(self):
  original=b.tile.run;seen=[]
  def interpose(snapshot,sd,physical,land,*args,**kw):
   if not seen:self.paths['physical_runs'].write_bytes(b'mutated original')
   self.assertEqual(physical[1].tolist(),np.tile(np.array([8,17,16,1],dtype='<u4'),8).tolist());seen.append(True)
   return original(snapshot,sd,physical,land,*args,**kw)
  with mock.patch.object(b.tile,'run',side_effect=interpose):self.run_batch()
  self.assertEqual(len(seen),2)
 def test_existing_output_not_overwritten(self):
  (self.d/'batch').mkdir();(self.d/'batch/keep').write_text('keep')
  with self.assertRaises(FileExistsError):self.run_batch()
  self.assertEqual((self.d/'batch/keep').read_text(),'keep')
if __name__=='__main__':unittest.main()
