import hashlib,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ural_seed_source as gate
from regions import URAL_CONSTRUCTION_INPUTS,geometry_hash


class UralGate(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
  self.recipe=root/'recipe';self.inputs=root/'inputs';self.helpers=root/'helpers';self.work=root/'work'
  for p in (self.recipe,self.inputs,self.helpers,self.work):p.mkdir()
  (self.recipe/'reproduce_raw_boundary.py').write_text('reviewed test runner\n')
  (self.inputs/'review_snapshot.json').write_text('verified selector\n')
  (root/'fresh.json').write_text('authenticated selected snapshot\n');self.freshsha=hashlib.sha256((root/'fresh.json').read_bytes()).hexdigest()
  self.codehash=hashlib.sha256((self.recipe/'reproduce_raw_boundary.py').read_bytes()).hexdigest()
  self.snapsha=hashlib.sha256((self.inputs/'review_snapshot.json').read_bytes()).hexdigest()
  self.geom={'type':'LineString','coordinates':[[0.,0.],[1.,1.]]};self.geomsha=geometry_hash(self.geom)
  refs=[];self.catalog={}
  for rel,(sid,digest,tile) in URAL_CONSTRUCTION_INPUTS.items():
   refs.append({'source_id':sid,'version':'v1','relationship':rel,'role':'construction_input'})
   self.catalog[(sid,'v1')]={'kind':'raw','sha256':digest}
   if tile:self.catalog[(sid,'v1')].update(representation='manifest_of_raw_parts',full_tile_sha256=tile)
  self.boundaries={('boundary',gate.BOUNDARY):{'revision_id':'r','geometry':{'type':'LineString','coordinates':[['0','0'],['1','1']]},'geometry_sha256':self.geomsha,'qualified_source_refs':refs}}
  self.pin={'recipe_dir':str(self.recipe),'inputs_dir':str(self.inputs),'helpers_dir':str(self.helpers),'work_parent':str(self.work),'snapshot':str(root/'fresh.json'),'snapshot_sha256':self.freshsha}
  self.patches=[patch.object(gate,'GEOMETRY_SHA256',self.geomsha),patch.object(gate,'RECIPE_SNAPSHOT_SHA256',self.snapsha),patch.object(gate,'RECIPE_CODE',{'reproduce_raw_boundary.py':self.codehash}),patch.object(gate,'load_pinned_snapshot',return_value={}),patch.object(gate,'boundary_records',side_effect=lambda _:('r','e',self.boundaries,self.catalog)),patch.object(gate.subprocess,'run',side_effect=self.runner)]
  for p in self.patches:p.start()
  self.addCleanup(self.tmp.cleanup)
  for p in self.patches:self.addCleanup(p.stop)
 def runner(self,cmd,**kwargs):
  out=Path(cmd[cmd.index('--workdir')+1]);out.mkdir();(out/'ural-raw-backed-continuous-cop-only.geometry.json').write_text(json.dumps(self.geom))
  return SimpleNamespace(returncode=0,stdout=b'',stderr=b'')
 def test_binding_replays_and_retains_selected_geometry(self):
  b,t=gate.bind(self.boundaries,self.catalog,self.pin)
  self.assertIs(b,self.boundaries);self.assertEqual(t['selected_geometry_sha256'],self.geomsha);self.assertEqual(t['derived_geometry_sha256'],self.geomsha);self.assertEqual(len(t['sources']),7);self.assertEqual(t['selected_revision'],'r')
  self.assertEqual(t['selected_snapshot_sha256'],self.freshsha)
 def test_missing_reference_rejected(self):
  self.boundaries[('boundary',gate.BOUNDARY)]['qualified_source_refs'].pop()
  with self.assertRaisesRegex(ValueError,'source set'):gate.bind(self.boundaries,self.catalog,self.pin)
 def test_manifest_tile_spoof_rejected(self):
  ref=next(x for x in self.boundaries[('boundary',gate.BOUNDARY)]['qualified_source_refs'] if 'manifest' in x['relationship'])
  self.catalog[(ref['source_id'],ref['version'])]['full_tile_sha256']='f'*64
  with self.assertRaisesRegex(ValueError,'manifest mismatch'):gate.bind(self.boundaries,self.catalog,self.pin)
 def test_changed_raw_source_pin_rejected(self):
  ref=self.boundaries[('boundary',gate.BOUNDARY)]['qualified_source_refs'][0]
  self.catalog[(ref['source_id'],ref['version'])]['sha256']='f'*64
  with self.assertRaisesRegex(ValueError,'catalog mismatch'):gate.bind(self.boundaries,self.catalog,self.pin)
 def test_replay_rejects_changed_raw_source_bytes(self):
  with patch.object(gate.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout=b'',stderr=b'raw source hash mismatch')):
   with self.assertRaisesRegex(ValueError,'raw source hash mismatch'):gate.bind(self.boundaries,self.catalog,self.pin)
 def test_selected_line_or_revision_change_rejected(self):
  self.boundaries[('boundary',gate.BOUNDARY)]['geometry']['coordinates'][1]=['2','1']
  with self.assertRaisesRegex(ValueError,'geometry mismatch'):gate.bind(self.boundaries,self.catalog,self.pin)
  self.boundaries[('boundary',gate.BOUNDARY)]['geometry']['coordinates'][1]=['1','1']
  with patch.object(gate,'boundary_records',return_value=('other','e',self.boundaries,self.catalog)):
   with self.assertRaisesRegex(ValueError,'revision mismatch'):gate.bind(self.boundaries,self.catalog,self.pin)
 def test_code_or_selector_tamper_rejected(self):
  (self.recipe/'reproduce_raw_boundary.py').write_text('changed')
  with self.assertRaisesRegex(ValueError,'code pin'):gate.bind(self.boundaries,self.catalog,self.pin)
  (self.recipe/'reproduce_raw_boundary.py').write_text('reviewed test runner\n');(self.inputs/'review_snapshot.json').write_text('changed')
  with self.assertRaisesRegex(ValueError,'selector snapshot'):gate.bind(self.boundaries,self.catalog,self.pin)
 def test_source_replay_difference_rejected(self):
  self.geom={'type':'LineString','coordinates':[[0.,0.],[2.,2.]]}
  with self.assertRaisesRegex(ValueError,'differs from selected'):gate.bind(self.boundaries,self.catalog,self.pin)
 def test_fresh_snapshot_record_must_match_caller(self):
  with patch.object(gate,'boundary_records',return_value=('r','e',{},self.catalog)):
   with self.assertRaisesRegex(ValueError,'differs from pinned fresh snapshot'):gate.bind(self.boundaries,self.catalog,self.pin)
 def test_fresh_snapshot_cannot_change_during_replay(self):
  def change(cmd,**kwargs):
   result=self.runner(cmd,**kwargs);Path(self.pin['snapshot']).write_text('changed');return result
  with patch.object(gate.subprocess,'run',side_effect=change):
   with self.assertRaisesRegex(ValueError,'snapshot changed'):gate.bind(self.boundaries,self.catalog,self.pin)
 def test_no_selected_boundary_does_not_infer_selection(self):
  self.assertEqual(gate.bind({},self.catalog,None),({},None))
  with self.assertRaisesRegex(ValueError,'without selected'):gate.bind({},self.catalog,self.pin)
 def test_trace_verification_replays_and_rejects_changes(self):
  _,trace=gate.bind(self.boundaries,self.catalog,self.pin)
  self.assertEqual(gate.verify_trace(self.boundaries,self.catalog,self.pin,trace),trace)
  trace['selected_revision']='wrong'
  with self.assertRaisesRegex(ValueError,'trace mismatch'):gate.verify_trace(self.boundaries,self.catalog,self.pin,trace)


if __name__=='__main__':unittest.main()
