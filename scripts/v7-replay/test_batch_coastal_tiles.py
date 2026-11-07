import errno,fcntl,hashlib,json,os,signal,subprocess,sys,tempfile,textwrap,time,unittest
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
 def run_batch(self,**kw):return b.run_batch(self.snapshot,'a'*64,self.paths,self.pins,self.plan,'b'*64,kw.pop('out',self.d/'batch'),self.width,self.height,self.check,metadata_pins={'physical_report':'c'*64,'land_report':'d'*64},**kw)
 def test_end_to_end_two_tiles_and_single_completion(self):
  with mock.patch.object(b,'sealed_copy',wraps=b.sealed_copy) as copies:result=self.run_batch()
  self.assertEqual(copies.call_count,4);self.assertEqual(self.calls,2);self.assertEqual(len(result['tiles']),2);self.assertTrue((self.d/'batch/batch-complete.json').is_file());self.assertEqual(result['status'],'complete-research-not-published')
  self.assertEqual(result['shoreline_index']['coastal_cells'],16)
  self.assertGreaterEqual(result['shoreline_index']['processing_elapsed_seconds'],0)
  for x in result['tiles']:
   p=self.d/'batch'/('tile-%04d'%x['tile'])/'manifest.json';self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),x['manifest_sha256']);self.assertEqual(json.loads(p.read_bytes())['status'],'partial-unverified-research-not-published')
 def test_caller_timer_includes_preflight(self):
  result=self.run_batch(processing_started=time.perf_counter()-5)
  self.assertGreaterEqual(result['processing_elapsed_seconds'],5)
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
  plan={'tiles':[[x,x+1,0,1] for x in range(546)],'pad_degrees':181,'chunk':100001}
  self.assertEqual(len(b.validate_plan(plan,546,1)),546)
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
 def interrupt_batch(self,out=None):
  original=b.tile.run
  calls=[]
  def interrupted(*args,**kw):
   calls.append(args[4])
   if len(calls)==2:
    Path(args[4]).mkdir();(Path(args[4])/'coastal-assignments.jsonl.gz').write_bytes(b'interrupted stream')
    raise KeyboardInterrupt('synthetic interruption')
   return original(*args,**kw)
  with mock.patch.object(b.tile,'run',side_effect=interrupted):
   with self.assertRaises(KeyboardInterrupt):self.run_batch(out=out or self.d/'batch',processing_started=time.perf_counter()-5)
  return out or self.d/'batch'
 def test_resume_regenerates_only_interrupted_tile_and_preserves_source(self):
  source=self.interrupt_batch()
  before={str(p.relative_to(source)):p.read_bytes() for p in source.rglob('*') if p.is_file()}
  self.assertTrue((source/'tile-0000/tile-complete.json').is_file())
  self.assertFalse((source/'tile-0001/tile-complete.json').exists())
  with mock.patch.object(b.tile,'run',wraps=b.tile.run) as generated:
   result=self.run_batch(out=self.d/'resumed',resume_from=source)
  self.assertEqual(generated.call_count,1);self.assertEqual(result['resumed_tiles'],1)
  self.assertEqual(before,{str(p.relative_to(source)):p.read_bytes() for p in source.rglob('*') if p.is_file()})
  self.assertFalse(result['timing_complete']);self.assertIsNone(result['processing_elapsed_seconds'])
  self.assertGreaterEqual(result['recorded_processing_elapsed_seconds'],5)
  self.assertEqual(len(result['timing_attempts']),2)
 def test_complete_batch_can_be_copied_after_source_directory_rename(self):
  original=self.run_batch();renamed=self.d/'preserved';(self.d/'batch').rename(renamed)
  with mock.patch.object(b.tile,'run',side_effect=AssertionError('completed tile regenerated')):
   result=self.run_batch(out=self.d/'resumed',resume_from=renamed)
  self.assertEqual(result['tiles'],original['tiles']);self.assertEqual(result['resumed_tiles'],2)
  self.assertTrue(result['timing_complete']);self.assertIsInstance(result['processing_elapsed_seconds'],float)
 def test_corrupted_checkpoint_fails_before_creating_output(self):
  source=self.interrupt_batch();(source/'tile-0000/tile-complete.json').write_text('{broken')
  with self.assertRaises(ValueError):self.run_batch(out=self.d/'resumed',resume_from=source)
  self.assertFalse((self.d/'resumed').exists())
 def test_corrupted_manifest_or_span_fails_closed(self):
  for filename in ('manifest.json','coastal-assignments.jsonl.gz'):
   with self.subTest(filename=filename):
    source=self.d/('source-'+filename);self.run_batch(out=source)
    (source/'tile-0000'/filename).write_bytes(b'corrupted')
    out=self.d/('out-'+filename)
    with self.assertRaises(ValueError):self.run_batch(out=out,resume_from=source)
    self.assertFalse(out.exists())
 def test_resume_rejects_changed_input_plan_snapshot_and_code_identity(self):
  source=self.interrupt_batch();start=source/'batch-start.json';original=json.loads(start.read_bytes())
  for key in ('snapshot_sha256','plan_sha256','sealed_input_sha256','metadata_sha256','driver_sha256','tile_code_sha256','support_code_sha256'):
   with self.subTest(key=key):
    changed=json.loads(json.dumps(original));changed['identity'][key]='0'*64;start.write_text(json.dumps(changed))
    with self.assertRaisesRegex(ValueError,'identity mismatch'):self.run_batch(out=self.d/'resumed',resume_from=source)
    self.assertFalse((self.d/'resumed').exists())
  start.write_text(json.dumps(original))
 def test_legacy_tiles_without_producer_identity_are_not_adopted(self):
  source=self.d/'legacy';source.mkdir();(source/'tile-0000').mkdir()
  with self.assertRaises(FileNotFoundError):self.run_batch(out=self.d/'resumed',resume_from=source)
  self.assertFalse((self.d/'resumed').exists())
 def test_pending_checkpoint_after_interrupted_publication_is_not_reused(self):
  original=b.os.link
  def interrupted_link(src,dst,**kw):
   if Path(dst).name=='tile-complete.json' and Path(dst).parent.name=='tile-0001':raise KeyboardInterrupt()
   return original(src,dst,**kw)
  with mock.patch.object(b.os,'link',side_effect=interrupted_link):
   with self.assertRaises(KeyboardInterrupt):self.run_batch()
  self.assertTrue(list((self.d/'batch/tile-0001').glob('tile-complete.json.*.pending')))
  self.assertFalse((self.d/'batch/tile-0001/tile-complete.json').exists())
  with mock.patch.object(b.tile,'run',wraps=b.tile.run) as generated:
   self.run_batch(out=self.d/'resumed',resume_from=self.d/'batch')
  self.assertEqual(generated.call_count,1)
 def test_restart_gap_is_excluded_and_overlapping_ancestry_deduplicated(self):
  source=self.interrupt_batch();prior=json.loads((source/'tile-0000/tile-complete.json').read_bytes())['attempt_processing_elapsed_seconds']
  # Arbitrary filesystem timestamps represent a long offline gap, not processing.
  for path in source.rglob('*'):os.utime(path,(1,1))
  middle=self.d/'middle'
  original=b.verified_copy
  def interrupted_copy(src,dst,digest):
   original(src,dst,digest)
   if Path(dst).name=='manifest.json':raise KeyboardInterrupt()
  with mock.patch.object(b,'verified_copy',side_effect=interrupted_copy):
   with self.assertRaises(KeyboardInterrupt):self.run_batch(out=middle,resume_from=source)
  with mock.patch.object(b.tile,'run',wraps=b.tile.run) as generated:
   result=self.run_batch(out=self.d/'resumed',resume_from=[middle,source])
  self.assertEqual(generated.call_count,1)
  self.assertEqual(len(result['timing_attempts']),3)
  self.assertGreaterEqual(result['recorded_processing_elapsed_seconds'],prior)
  self.assertLess(result['recorded_processing_elapsed_seconds'],prior+5)
  forward=self.run_batch(out=self.d/'forward',resume_from=[source,middle])
  self.assertEqual(result['timing_attempts'][:-1],forward['timing_attempts'][:-1])
  self.assertEqual(result['tiles'][0],forward['tiles'][0])
 def test_multiple_completed_sources_are_independent_of_source_order(self):
  first=self.d/'first';second=self.d/'second';self.run_batch(out=first);self.run_batch(out=second)
  with mock.patch.object(b.tile,'run',side_effect=AssertionError('completed tile regenerated')):
   forward=self.run_batch(out=self.d/'forward',resume_from=[first,second])
   reverse=self.run_batch(out=self.d/'reverse',resume_from=[second,first])
  self.assertEqual(forward['tiles'],reverse['tiles'])
  self.assertEqual(forward['timing_attempts'][:-1],reverse['timing_attempts'][:-1])
 def test_conflicting_completed_attempt_times_are_rejected(self):
  ident='a'*32
  with self.assertRaisesRegex(ValueError,'inconsistent completed'):
   b.merge_attempts([{'attempt_id':ident,'processing_elapsed_seconds':1,'timing_complete':True}],
                    [{'attempt_id':ident,'processing_elapsed_seconds':2,'timing_complete':True}])
 def test_resume_has_exact_assignment_and_scientific_manifest_parity(self):
  from test_helpers import rle
  self.width=360;self.height=180
  physical=np.ones((180,360),dtype=np.uint32);land=np.zeros_like(physical)
  physical[89,180]=physical[91,181]=17;land[89,180]=17;land[91,181]=18
  for name,grid in (('physical',physical),('land',land)):
   rows,runs=rle(grid)
   for suffix,array in (('rows',rows),('runs',runs)):
    key=name+'_'+suffix;data=np.asarray(array,dtype='<u4').tobytes();self.paths[key].write_bytes(data);self.pins[key]=hashlib.sha256(data).hexdigest()
  self.plan={'tiles':[[177,184,88,90],[177,184,90,93]],'pad_degrees':5,'chunk':10}
  clean=self.d/'clean';self.run_batch(out=clean)
  source=self.interrupt_batch();resumed=self.d/'resumed';self.run_batch(out=resumed,resume_from=source)
  assigned=0
  for index in range(2):
   name='tile-%04d'%index
   self.assertEqual((clean/name/'coastal-assignments.jsonl.gz').read_bytes(),(resumed/name/'coastal-assignments.jsonl.gz').read_bytes())
   a=json.loads((clean/name/'manifest.json').read_bytes());c=json.loads((resumed/name/'manifest.json').read_bytes())
   assigned+=a['assigned_cells']
   for manifest in (a,c):
    manifest.pop('processing_elapsed_seconds');manifest.pop('stage_processing_elapsed_seconds')
   self.assertEqual(a,c)
  self.assertGreater(assigned,0)
 def test_sigkill_with_partial_tile_resumes_from_last_durable_tile(self):
  config={'snapshot':self.snapshot,'paths':{k:str(p) for k,p in self.paths.items()},'pins':self.pins,'plan':self.plan,'out':str(self.d/'killed')}
  request=self.d/'request.json';request.write_text(json.dumps(config));marker=self.d/'inside-tile'
  program=textwrap.dedent("""
   import json,sys,time
   from pathlib import Path
   import batch_coastal_tiles as b
   c=json.loads(Path(sys.argv[1]).read_bytes());original=b.tile.run;count=0
   def interrupted(*args,**kw):
       global count
       count+=1
       if count==2:
           out=Path(args[4]);out.mkdir();(out/'coastal-assignments.jsonl.gz').write_bytes(b'partial')
           Path(sys.argv[2]).write_text('ready')
           while True:time.sleep(1)
       return original(*args,**kw)
   b.tile.run=interrupted
   b.run_batch(c['snapshot'],'a'*64,c['paths'],c['pins'],c['plan'],'b'*64,c['out'],16,8,lambda:None,metadata_pins={'physical_report':'c'*64,'land_report':'d'*64})
  """)
  process=subprocess.Popen([sys.executable,'-c',program,str(request),str(marker)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  try:
   deadline=time.monotonic()+15
   while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
   if not marker.exists():
    process.kill();stdout,stderr=process.communicate(timeout=5);self.fail('child never reached interrupted tile: '+stderr.decode())
   process.send_signal(signal.SIGKILL);process.communicate(timeout=5)
   self.assertEqual(process.returncode,-signal.SIGKILL)
  finally:
   if process.poll() is None:process.kill();process.communicate(timeout=5)
  with mock.patch.object(b.tile,'run',wraps=b.tile.run) as generated:
   result=self.run_batch(out=self.d/'resumed',resume_from=self.d/'killed')
  self.assertEqual(generated.call_count,1);self.assertEqual(result['resumed_tiles'],1)
  self.assertFalse(result['timing_complete'])
if __name__=='__main__':unittest.main()
