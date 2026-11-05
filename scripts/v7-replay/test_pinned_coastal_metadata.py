import hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest import mock
import pinned_coastal_metadata as m
import build_prefill_plan as old
H=lambda b:hashlib.sha256(b).hexdigest()
class PinnedMetadataTest(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);self.grid={'width':16,'height':8,'west':-180,'north':90,'step':22.5};self.physical={'rows_sha256':'1'*64,'runs_sha256':'2'*64};self.snapshot='3'*64;self.revision={'id':'d','status':'draft','entity_revision':'e'};base=self.root/'land-report';base.mkdir();(base/'land').mkdir();self.rp=base/'report.json';self.land={'rows_sha256':'4'*64,'runs_sha256':'5'*64,'resolved_rows':(base/'land/rows.u32le').resolve(),'resolved_runs':(base/'land/runs.u32le').resolve()}
  v={'builder_source_sha256':'6'*64,'compiler_version':'c','builder_output':'o'}
  for name,key in [('component-builder','builder_binary_sha256'),('verified-component-rows.u32le','rows_sha256'),('verified-component-runs.u32le','runs_sha256')]:
   p=base/name;p.write_bytes(name.encode());v[key]=H(p.read_bytes())
  cfg={'grid':self.grid,'snapshot':{'sha256':self.snapshot},'physical_rows':{'sha256':self.physical['rows_sha256']},'physical_runs':{'sha256':self.physical['runs_sha256']}};self.cp=base/'config.json';self.cp.write_text(json.dumps(cfg));self.doc={'schema':'direct-neon-land-build-report-v1','status':'unverified-research-not-published','snapshot_sha256':self.snapshot,'decision_revision':'d','decision_revision_asserted_status':'draft','entity_revision':'e','config_sha256':H(self.cp.read_bytes()),'component_verification':v,'compiler_report':{'schema':'land-decision-compiler-prototype-report-v1','input_sha256':{'component_rows':v['rows_sha256'],'component_runs':v['runs_sha256'],'physical_rows':self.physical['rows_sha256'],'physical_runs':self.physical['runs_sha256']},'output_rows_sha256':self.land['rows_sha256'],'output_runs_sha256':self.land['runs_sha256']}};self.rp.write_text(json.dumps(self.doc))
  self.phys={'status':'candidate-only','grid':self.grid,'output_sha256':{'rows.u32le':self.physical['rows_sha256'],'runs.u32le':self.physical['runs_sha256']},'configuration_sha256':'7'*64,'inputs':{'land':{'path':'land','sha256':'8'*64},'water':{'path':'water','sha256':'9'*64}}}
 def validate(self,doc=None):return m.validate_legacy_direct(doc or self.doc,self.rp,self.physical,self.land,self.snapshot,self.revision,self.root,self.grid)
 def test_same_decisions_as_legacy_validator(self):
  self.validate();m.validate_physical(self.phys,self.physical,self.grid)
  with mock.patch.object(old,'canonical_physical_grid',return_value=self.grid):old.validate_land_report(self.doc,self.rp,self.physical,self.land,self.snapshot,self.revision,self.root)
 def test_unsupported_schemas_fail_closed(self):
  for schema in ('stage3-selected-mixed-land-report-v1','single-generation-direct-land-report-v1','single-generation-nearest-report-v1'):
   with self.subTest(schema=schema),self.assertRaisesRegex(ValueError,'legacy direct only'):self.validate({**self.doc,'schema':schema})
 def test_each_metadata_path_same_size_swap_is_not_consumed(self):
  for name in ('snapshot','plan','physical-report','land-report','config'):
   with self.subTest(name=name):
    p=self.root/('case-'+name);original=b'{"a":1}';replacement=b'{"a":2}';p.write_bytes(original);q=self.root/('case-'+name+'-new');q.write_bytes(replacement);real=os.read;ino=p.stat().st_ino;changed=[False]
    def read(fd,n):
     if os.fstat(fd).st_ino==ino and not changed[0]:os.replace(q,p);changed[0]=True
     return real(fd,n)
    with mock.patch.object(m.os,'read',side_effect=read):self.assertEqual(m.pinned_json(p,H(original)),{'a':1})
    self.assertTrue(changed[0]);self.assertEqual(p.read_bytes(),replacement)
    with self.assertRaisesRegex(ValueError,'hash mismatch'):m.pinned_json(p,H(original))
 def test_oversize_and_growth_are_bounded(self):
  p=self.root/'big';p.write_bytes(b'x'*9)
  with self.assertRaisesRegex(ValueError,'cap'):m.pinned_bytes(p,H(p.read_bytes()),8)
  p.write_bytes(b'12345678');real=os.read;ino=p.stat().st_ino;changed=[False]
  def read(fd,n):
   z=real(fd,n)
   if z and os.fstat(fd).st_ino==ino and not changed[0]:
    with p.open('ab') as f:f.write(b'9')
    changed[0]=True
   return z
  with mock.patch.object(m.os,'read',side_effect=read),self.assertRaisesRegex(ValueError,'cap|changed'):m.pinned_bytes(p,H(b'12345678'),8)
 def test_config_hash_and_component_tamper_fail(self):
  self.cp.write_text(self.cp.read_text().replace('22.5','23.5'))
  with self.assertRaisesRegex(ValueError,'hash mismatch'):self.validate()
  self.cp.write_text(self.cp.read_text().replace('23.5','22.5'));(self.rp.parent/'component-builder').write_text('tampered')
  with self.assertRaisesRegex(ValueError,'artifact pin mismatch'):self.validate()
 def test_bad_snapshot_grid_or_physical_binding_fail(self):
  for changed in ({**self.doc,'snapshot_sha256':'a'*64},{**self.doc,'decision_revision':'wrong'}):
   with self.assertRaisesRegex(ValueError,'lineage mismatch'):self.validate(changed)
  with self.assertRaisesRegex(ValueError,'physical report'):m.validate_physical({**self.phys,'grid':{}},self.physical,self.grid)
class CliIntegrationTest(unittest.TestCase):
 def setUp(self):
  import numpy as np
  from test_coastal_core import snap
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);direct=self.root/'direct';direct.mkdir();landdir=direct/'land';landdir.mkdir();w,h=131072,54614;grid={'width':w,'height':h,'west':-180,'north':90,'step':360/w};self.files={}
  def put(name,data):
   p=self.root/name;p.write_bytes(data);return p
  rows=(np.arange(h+1,dtype='<u4')*2).tobytes();pruns=np.tile(np.array([65536,17,w,1],dtype='<u4'),h).tobytes();lruns=np.tile(np.array([65536,17,w,0],dtype='<u4'),h).tobytes()
  self.files['physical_rows']=put('physical-rows',rows);self.files['physical_runs']=put('physical-runs',pruns);self.files['land_rows']=put('direct/land/rows.u32le',rows);self.files['land_runs']=put('direct/land/runs.u32le',lruns)
  snapshot=snap();snapshot.update(schema='worldatlas-geography-decision-draft-evidence-v1',source='neon-export',entity_revision={'id':'entities','status':'draft'});self.files['snapshot']=put('snapshot.json',json.dumps(snapshot).encode());sh=H(self.files['snapshot'].read_bytes());ph={k:H(self.files['physical_'+k].read_bytes()) for k in ('rows','runs')};lh={k:H(self.files['land_'+k].read_bytes()) for k in ('rows','runs')}
  phys={'status':'candidate-only','grid':grid,'output_sha256':{'rows.u32le':ph['rows'],'runs.u32le':ph['runs']},'configuration_sha256':'7'*64,'inputs':{'land':{'path':'land','sha256':'8'*64},'water':{'path':'water','sha256':'9'*64}}};self.files['physical_report']=put('physical-report.json',json.dumps(phys).encode());v={'builder_source_sha256':'6'*64,'compiler_version':'c','builder_output':'o'}
  for name,key in [('component-builder','builder_binary_sha256'),('verified-component-rows.u32le','rows_sha256'),('verified-component-runs.u32le','runs_sha256')]:v[key]=H(put('direct/'+name,name.encode()).read_bytes())
  cfg={'grid':grid,'snapshot':{'sha256':sh},'physical_rows':{'sha256':ph['rows']},'physical_runs':{'sha256':ph['runs']}};self.config=put('direct/config.json',json.dumps(cfg).encode());landreport={'schema':'direct-neon-land-build-report-v1','status':'unverified-research-not-published','snapshot_sha256':sh,'decision_revision':'draft','decision_revision_asserted_status':'draft','entity_revision':'entities','config_sha256':H(self.config.read_bytes()),'component_verification':v,'compiler_report':{'schema':'land-decision-compiler-prototype-report-v1','input_sha256':{'component_rows':v['rows_sha256'],'component_runs':v['runs_sha256'],'physical_rows':ph['rows'],'physical_runs':ph['runs']},'output_rows_sha256':lh['rows'],'output_runs_sha256':lh['runs']}};self.files['land_report']=put('direct/report.json',json.dumps(landreport).encode());plan={'tiles':[[65535,65537,27306,27307],[65535,65537,27307,27308]],'pad_degrees':2,'chunk':10,'max_coastal_centers':10000};self.files['plan']=put('plan.json',json.dumps(plan).encode());self.args=['batch_coastal_tiles','--input-root',str(self.root),'--out',str(self.root/'result'),'--allow-unverified-snapshot','--allow-draft','--allow-selected-research-policy']
  for k,p in self.files.items():self.args.extend(['--'+k.replace('_','-'),str(p),'--'+k.replace('_','-')+'-sha256',H(p.read_bytes())])
 def test_cli_valid_legacy_and_tampered_config(self):
  import contextlib,io,sys,batch_coastal_tiles as batch
  with mock.patch.object(sys,'argv',self.args),contextlib.redirect_stdout(io.StringIO()):batch.main()
  self.assertTrue((self.root/'result/batch-complete.json').is_file());self.assertEqual(len(json.loads((self.root/'result/batch-complete.json').read_bytes())['tiles']),2)
  self.config.write_bytes(self.config.read_bytes().replace(b'131072',b'131073'));args=self.args.copy();args[args.index('--out')+1]=str(self.root/'rejected')
  with mock.patch.object(sys,'argv',args),self.assertRaisesRegex(ValueError,'hash mismatch'):batch.main()
  self.assertFalse((self.root/'rejected').exists())

if __name__=='__main__':unittest.main()
