import fcntl,hashlib,json,shutil,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import build_land,build_land_checkpoint as ck
import numpy as np
from test_build_land import TestBuild,pin,rle

class CheckpointTests(unittest.TestCase):
 def test_resume_matches_uninterrupted(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);cfg,_=TestBuild().fixture(p);ref=build_land.build(cfg,p/'reference')
   real=ck.checkpoint_write;events=[]
   def stop_after_two(path,payload,reserve):
    real(path,payload,reserve);events.append(payload['next_row'])
    if payload['next_row']==2:raise RuntimeError('simulated interruption')
   with patch.object(ck,'checkpoint_write',stop_after_two):
    with self.assertRaisesRegex(RuntimeError,'simulated interruption'):ck.build(cfg,p/'interrupted',p/'checkpoint',checkpoint_seconds=1e-9)
   self.assertEqual(events,[1,2]);self.assertFalse((p/'interrupted/report.json').exists())
   got=ck.build(cfg,p/'resumed',p/'checkpoint',resume=True,checkpoint_seconds=1e-9)
   self.assertEqual(got['resumed_from_row'],2);self.assertEqual(ref['output_rows_sha256'],got['output_rows_sha256']);self.assertEqual(ref['output_runs_sha256'],got['output_runs_sha256']);self.assertEqual(ref['ties'],got['ties'])
 def test_two_workers_equal_serial(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);path,cfg=TestBuild().fixture(p);ref=build_land.build(path,p/'reference')
   cfg['workers']=2;path.write_text(json.dumps(cfg));got=ck.build(path,p/'parallel',p/'parallel-checkpoint')
   self.assertEqual(ref['output_rows_sha256'],got['output_rows_sha256']);self.assertEqual(ref['output_runs_sha256'],got['output_runs_sha256']);self.assertEqual(ref['ties'],got['ties'])
 def test_four_workers_equal_serial(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);path,cfg=TestBuild().fixture(p)
   cfg['grid'].update(height=18,north=90)
   physical=np.ones((18,36),dtype=np.uint32);seed_grid=np.zeros_like(physical)
   xs=[1,6,11,16,21,26];physical[1,xs]=17;seed_grid[1,xs]=range(17,23)
   physical[3:17:2,1:36:2]=17
   cfg['physical_rows'],cfg['physical_runs']=rle(physical,p/'phys')
   cfg['mainland_rows'],cfg['mainland_runs']=rle(seed_grid,p/'seed')
   report=Path(cfg['physical_report']['path']);doc=json.loads(report.read_text());doc['grid']=cfg['grid'];doc['output_sha256']={'rows.u32le':cfg['physical_rows']['sha256'],'runs.u32le':cfg['physical_runs']['sha256']};report.write_text(json.dumps(doc));cfg['physical_report']=pin(report)
   cr=p/'provenance/cr';cu=p/'provenance/cu';cr.unlink();cu.unlink();subprocess.run([str(p/'provenance/builder'),'36','18',cfg['physical_rows']['path'],cfg['physical_runs']['path'],str(cr),str(cu)],check=True,capture_output=True)
   seed=Path(cfg['seed_provenance']['path']);doc=json.loads(seed.read_text());doc['grid']={k:cfg['grid'][k] for k in ('width','height','step')};doc['inputs']={'physical_component_rows_sha256':pin(cr)['sha256'],'physical_component_runs_sha256':pin(cu)['sha256']};doc['outputs']={'rows_sha256':cfg['mainland_rows']['sha256'],'runs_sha256':cfg['mainland_runs']['sha256']};seed.write_text(json.dumps(doc));cfg['seed_provenance']=pin(seed);path.write_text(json.dumps(cfg))
   ref=ck.build(path,p/'serial',p/'serial-checkpoint');self.assertGreaterEqual(ref['queries'],64)
   saved=json.loads((p/'serial-checkpoint').read_text())['payload'];self.assertGreaterEqual(len(saved['best']),10)
   resumed=ck.build(path,p/'serial-resumed',p/'serial-checkpoint',resume=True)
   self.assertEqual((p/'serial/rows.u32le').read_bytes(),(p/'serial-resumed/rows.u32le').read_bytes());self.assertEqual((p/'serial/runs.u32le').read_bytes(),(p/'serial-resumed/runs.u32le').read_bytes());self.assertEqual(ref['ties'],resumed['ties'])
   real=ck.checkpoint_write
   def stop_after_islands(checkpoint,payload,reserve):
    real(checkpoint,payload,reserve)
    if payload['next_row']==8:raise RuntimeError('simulated interruption after island queries')
   with patch.object(ck,'checkpoint_write',stop_after_islands):
    with self.assertRaisesRegex(RuntimeError,'simulated interruption'):ck.build(path,p/'partial',p/'partial-checkpoint',checkpoint_seconds=1e-9)
   partial=json.loads((p/'partial-checkpoint').read_text())['payload'];self.assertGreaterEqual(len(partial['best']),10);self.assertGreater(partial['queries'],0)
   resumed_partial=ck.build(path,p/'partial-resumed',p/'partial-checkpoint',resume=True)
   self.assertEqual((p/'serial/runs.u32le').read_bytes(),(p/'partial-resumed/runs.u32le').read_bytes());self.assertEqual(ref['ties'],resumed_partial['ties'])
   cfg['workers']=4;path.write_text(json.dumps(cfg));got=ck.build(path,p/'parallel',p/'parallel-checkpoint')
   self.assertEqual((p/'serial/rows.u32le').read_bytes(),(p/'parallel/rows.u32le').read_bytes());self.assertEqual((p/'serial/runs.u32le').read_bytes(),(p/'parallel/runs.u32le').read_bytes());self.assertEqual(ref['ties'],got['ties']);self.assertEqual(ref['queries'],got['queries'])
 def test_tampered_checkpoint_fails(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);cfg,_=TestBuild().fixture(p);ck.build(cfg,p/'initial',p/'checkpoint');data=json.loads((p/'checkpoint').read_text());data['payload']['queries']+=1;(p/'checkpoint').write_text(json.dumps(data))
   with self.assertRaisesRegex(ValueError,'checksum mismatch'):ck.build(cfg,p/'resumed',p/'checkpoint',resume=True)
   self.assertFalse((p/'resumed/report.json').exists())
 def test_rechecks_cursor_and_query_count_even_with_valid_checksum(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);cfg,_=TestBuild().fixture(p);ck.build(cfg,p/'initial',p/'checkpoint');checkpoint=p/'checkpoint';data=json.loads(checkpoint.read_text());data['payload']['queries']-=1
   body=json.dumps(data['payload'],separators=(',',':'),sort_keys=True,allow_nan=False).encode();data['sha256']=hashlib.sha256(body).hexdigest();checkpoint.write_text(json.dumps(data))
   with self.assertRaisesRegex(ValueError,'cursor, query count, or roots mismatch'):ck.build(cfg,p/'resumed',checkpoint,resume=True)
   self.assertFalse((p/'resumed/report.json').exists())
 def test_checkpoint_lock_rejects_second_writer(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);cfg,_=TestBuild().fixture(p);checkpoint=p/'checkpoint'
   with open(str(checkpoint)+'.lock','a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    with self.assertRaises(BlockingIOError):ck.build(cfg,p/'out',checkpoint)
   self.assertFalse((p/'out').exists());self.assertFalse(checkpoint.exists())
 def test_checkpoint_disk_reserve_preserves_previous_checkpoint(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);checkpoint=p/'checkpoint';ck.checkpoint_write(checkpoint,{'cursor':1},0);before=checkpoint.read_bytes()
   usage=shutil.disk_usage(p)
   low=shutil._ntuple_diskusage(usage.total,usage.used,0)
   with patch.object(ck.shutil,'disk_usage',side_effect=[usage,low]):
    with self.assertRaisesRegex(ValueError,'checkpoint disk reserve breached'):ck.checkpoint_write(checkpoint,{'cursor':2},1)
   self.assertEqual(before,checkpoint.read_bytes())
   self.assertEqual(sorted(x.name for x in p.iterdir()),['checkpoint'])
 def test_checkpoint_hash_uses_json_key_order(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'checkpoint';ck.checkpoint_write(p,{'best':{2:{17:1.0},10:{18:2.0}}},0);envelope=json.loads(p.read_text())
   body=json.dumps(envelope['payload'],separators=(',',':'),sort_keys=True,allow_nan=False).encode()
   self.assertEqual(envelope['sha256'],hashlib.sha256(body).hexdigest())
if __name__=='__main__':unittest.main()
