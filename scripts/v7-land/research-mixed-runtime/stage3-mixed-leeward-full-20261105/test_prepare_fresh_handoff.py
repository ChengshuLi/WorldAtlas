import json,tempfile,unittest
from unittest import mock
from pathlib import Path
import prepare_fresh_handoff as p
class PreparationTests(unittest.TestCase):
 def test_code_inventory_is_fixed_and_preserves_policy_hashes(self):
  paths=p.regional_code_paths();specs={name:{'path':'/unavailable/old-checkout/'+name,'sha256':p.sha(path)} for name,path in paths.items()}
  bound=p.bind_regional_code(specs)
  self.assertEqual(set(bound),set(paths))
  for name,path in paths.items():self.assertEqual(bound[name],p.pin(path))
  specs['run_pair']['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'policy code pin mismatch'):p.bind_regional_code(specs)
  specs.pop('adapter')
  with self.assertRaisesRegex(ValueError,'inventory mismatch'):p.bind_regional_code(specs)
 def test_repo_root(self):
  self.assertTrue((p.REPO/'scripts/v7-recovery/land/stage2-geodesic-20261104/contracts.py').is_file())
 def test_template_pin_is_required_and_checked_before_output(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);template=root/'template';template.write_text('{}')
   with self.assertRaisesRegex(ValueError,'template hash mismatch'):
    p.prepare(template,root/'outer',root/'work',root/'stage',root/'prepared',root/'out',template_sha256='0'*64)
   self.assertFalse((root/'prepared').exists())
 def test_rejects_unfinished_and_leaves_destination_absent(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);work=root/'work';out=root/'stage';work.mkdir();out.mkdir();(work/'derived').mkdir();(work/'core-requests').mkdir()
   def put(name,obj):(root/name).write_text(json.dumps(obj))
   put('template.json',{'schema':'stage3-provisional-diagnostic-request-v1','publishable':False});put('outer.json',{'schema':'stage2-fresh-orchestration-v1'});(out/'report.json').write_text('{}');(work/'derived/manifest.json').write_text('{}');(work/'core-requests/config.json').write_text('{}')
   dest=root/'prepared'
   with mock.patch.object(p,'sha',return_value='4668cac041f0dee1257c95a9e60c46d34fff53ffb5ab0010ec3647e114d909d0'):
    with self.assertRaisesRegex(ValueError,'completed provisional'):p.prepare(root/'template.json',root/'outer.json',work,out,dest,root/'regional-output',template_sha256='4668cac041f0dee1257c95a9e60c46d34fff53ffb5ab0010ec3647e114d909d0')
   self.assertFalse(dest.exists())
if __name__=='__main__':unittest.main()
