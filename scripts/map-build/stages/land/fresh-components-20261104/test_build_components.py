import hashlib,importlib.util,json,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fresh_components',HERE/'build_components.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def packed(fmt,items):return b''.join(struct.pack(fmt,*x) for x in items)
def pin(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
class FreshComponentsTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);self.src=self.root/'inputs';self.src.mkdir();self.w=self.root/'work';self.out=self.root/'out';self.grid={'width':8,'height':4,'west':-180,'north':90,'step':45}
  (self.src/'rows').write_bytes(packed('<I',[(0,),(1,),(4,),(5,),(6,)]));(self.src/'runs').write_bytes(packed('<II',[(8,1),(2,1),(6,17),(8,1),(8,1),(8,1)]));r=pin(self.src/'rows');s=pin(self.src/'runs');(self.src/'physical.json').write_text(json.dumps({'status':'candidate-only','grid':self.grid,'candidate_dry_cells':4,'output_sha256':{'rows.u32le':r['sha256'],'runs.u32le':s['sha256']}}));source=HERE/'components.py';self.cfg={'schema':'fresh-physical-components-v1','grid':self.grid,'inputs':{'physical_rows':r,'physical_runs':s,'physical_report':pin(self.src/'physical.json'),'component_source':pin(source)},'controls':{'minimum_free_bytes':2*1024**3}};self.cp=self.src/'request.json';self.cp.write_text(json.dumps(self.cfg))
 def test_real_tiny_builder_and_coverage(self):
  with patch.object(m.shutil,'disk_usage',return_value=type('D',(),{'free':4*1024**3})()):report=m.run(self.cp,self.w,self.out)
  self.assertEqual(report['land_cells'],4);self.assertEqual(report['status'],'research-awaiting-review');self.assertFalse(report['publishable']);self.assertEqual(report['component_rows_sha256'],pin(self.out/'rows.u32le')['sha256']);manifest=json.loads((self.out/'manifest.json').read_text());self.assertEqual(manifest['pins']['component_rows']['path'],str(self.out/'rows.u32le'));self.assertEqual(manifest['physical_report'],self.cfg['inputs']['physical_report']);self.assertFalse((self.out/'monitor.json').exists());self.assertFalse((self.out/'builder.cpp').exists())
 def test_existing_dangling_work_or_output_link_is_never_followed(self):
  for target in (self.w,self.out):
   target.symlink_to(self.root/'missing')
   with self.assertRaisesRegex(ValueError,'fresh work/output'):m.run(self.cp,self.w,self.out)
   self.assertTrue(target.is_symlink());self.assertFalse((self.root/'missing').exists())
   target.unlink()
 def test_unreviewed_source_fails_before_work(self):
  self.cfg['inputs']['component_source']['sha256']='0'*64;self.cp.write_text(json.dumps(self.cfg))
  with self.assertRaisesRegex(ValueError,'input hash mismatch|unreviewed'):m.run(self.cp,self.w,self.out)
  self.assertFalse(self.w.exists());self.assertFalse(self.out.exists())
 def test_runner_has_no_memory_floor_control(self):
  self.assertEqual(set(self.cfg['controls']),{'minimum_free_bytes'})
  self.assertEqual(set(self.cfg['controls']),{'minimum_free_bytes'})
  self.assertFalse(self.w.exists());self.assertFalse(self.out.exists())
 def test_disk_headroom_includes_output_bound(self):
  with patch.object(m.shutil,'disk_usage') as usage:
   from collections import namedtuple
   D=namedtuple('D','total used free');usage.return_value=D(100,0,2*1024**3+64*1024**2)
   with self.assertRaisesRegex(ValueError,'disk headroom'):m.require_disk_headroom(self.root,self.src/'runs',self.src/'rows',2*1024**3)
 def test_distinct_filesystems_rejected(self):
  from types import SimpleNamespace
  with patch.object(m.os,'stat',side_effect=[SimpleNamespace(st_dev=1),SimpleNamespace(st_dev=2)]):
   with self.assertRaisesRegex(ValueError,'share a filesystem'):m.require_same_filesystem('/a','/b')
if __name__=='__main__':unittest.main()
