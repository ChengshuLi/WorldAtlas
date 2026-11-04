import fcntl,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import build_coastal_resumable as old
import build_coastal_continuation as cont
import migrate_coastal_partial as migration
from test_coastal_band import make_rle,pin
class ContinuationTest(unittest.TestCase):
 def fixture(self,root):
  i=root/'input';i.mkdir();(i/'p').mkdir();(i/'l').mkdir();g={'width':360,'height':2,'west':-180,'north':90,'step':1}
  pr,pu=make_rle(i/'p',360,2,[(1,10,17)],False);lr,lu=make_rle(i/'l',360,2,[(1,10,17)],True)
  land=i/'land.json';land.write_text(json.dumps({'schema':'simple-v2-land-report-v1','status':'research-not-published','grid':g,'inputs':{'physical_rows':pr,'physical_runs':pu},'output_rows_sha256':lr['sha256'],'output_runs_sha256':lu['sha256']}))
  c={'schema':'simple-v2-coastal-resumable-v1','grid':g,'physical_rows':pr,'physical_runs':pu,'land_rows':lr,'land_runs':lu,'land_report':pin(land),'tile_width':180,'tile_height':1,'pad_degrees':1,'minimum_free_bytes':0}
  a=i/'old.json';a.write_text(json.dumps(c));c['pad_degrees']=.5;b=i/'new.json';b.write_text(json.dumps(c));source=root/'old';old.build(a,source,1)
  return a,b,source,pin(source/'identity.json')['sha256']
 def test_verified_import_resume_and_coverage(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);a,b,source,sha=self.fixture(root);target=root/'new';m=migration.migrate(a,b,source,sha,target)
   self.assertEqual(m['tile_count'],1);self.assertEqual((source/'configs/000000.json').read_bytes(),(target/'configs/000000.json').read_bytes())
   p=cont.build(b,target,1);self.assertEqual(p['status'],'paused-research-partial');self.assertEqual(p['completed_tiles'],2)
   final=cont.build(b,target);self.assertTrue(final['tile_cores_cover_grid']);self.assertEqual(final['tile_count'],4);self.assertEqual(final['migration_sha256'],pin(target/'migration.json')['sha256'])
 def test_source_corruption_blocks_migration(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);a,b,source,sha=self.fixture(root);span=source/'tiles/000000/attempt-0001/coastal-spans.jsonl.gz';span.write_bytes(span.read_bytes()+b'bad');target=root/'new'
   with self.assertRaisesRegex(ValueError,'source span mismatch'):migration.migrate(a,b,source,sha,target)
   self.assertFalse((target/'migration.json').exists())
 def test_copied_corruption_blocks_resume(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);a,b,source,sha=self.fixture(root);target=root/'new';migration.migrate(a,b,source,sha,target)
   span=target/'tiles/000000/attempt-0001/coastal-spans.jsonl.gz';span.write_bytes(span.read_bytes()+b'bad')
   with self.assertRaisesRegex(ValueError,'saved tile failed verification'):cont.build(b,target)
 def test_interrupted_copy_has_no_completion_manifest(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);a,b,source,sha=self.fixture(root);target=root/'new';before=pin(source/'tiles/000000/attempt-0001/report.json')['sha256']
   with patch.object(migration.shutil,'copyfile',side_effect=OSError('interrupted')):
    with self.assertRaisesRegex(OSError,'interrupted'):migration.migrate(a,b,source,sha,target)
   self.assertFalse((target/'migration.json').exists());self.assertEqual(before,pin(source/'tiles/000000/attempt-0001/report.json')['sha256'])
   with self.assertRaisesRegex(ValueError,'verified migration manifest required'):cont.build(b,target)
 def test_held_source_lock_blocks_migration(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);a,b,source,sha=self.fixture(root)
   with (source/'run.lock').open('r+') as f:
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
    with self.assertRaisesRegex(ValueError,'source run is still locked'):migration.migrate(a,b,source,sha,root/'new')
   self.assertFalse((root/'new').exists())
 def test_coverage_code_mismatch_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);a,b,source,sha=self.fixture(root);ip=source/'identity.json';v=json.loads(ip.read_text());v['code_sha256']['coverage_io']='0'*64;ip.write_text(json.dumps(v));sha=pin(ip)['sha256']
   with self.assertRaisesRegex(ValueError,'source code identity mismatch'):migration.migrate(a,b,source,sha,root/'new')
 def test_unapproved_config_change_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);a,b,source,sha=self.fixture(root);c=json.loads(b.read_text());c['tile_width']=90;b.write_text(json.dumps(c))
   with self.assertRaisesRegex(ValueError,'only an explicit halo change'):migration.migrate(a,b,source,sha,root/'new')
if __name__=='__main__':unittest.main()
