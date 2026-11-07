import json,tempfile,unittest
from unittest import mock
from pathlib import Path
import prepare_fresh_handoff as p
class PreparationTests(unittest.TestCase):
 def test_source_prefix_remap_is_narrow(self):
  value={'path':'/old/a','other':['/old/shapes.shp','/oldish/no','r2://worldatlas/x']}
  self.assertEqual(p.remap_source_paths(value,'/old','/new'),{'path':'/new/a','other':['/new/shapes.shp','/oldish/no','r2://worldatlas/x']})
 def test_repo_root(self):
  self.assertTrue((p.REPO/'scripts/v7-recovery/land/stage2-geodesic-20261104/contracts.py').is_file())
 def test_rejects_unfinished_and_leaves_destination_absent(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);work=root/'work';out=root/'stage';work.mkdir();out.mkdir();(work/'derived').mkdir();(work/'core-requests').mkdir()
   def put(name,obj):(root/name).write_text(json.dumps(obj))
   put('template.json',{'schema':'stage3-provisional-diagnostic-request-v1','publishable':False});put('outer.json',{'schema':'stage2-fresh-orchestration-v1'});(out/'report.json').write_text('{}');(work/'derived/manifest.json').write_text('{}');(work/'core-requests/config.json').write_text('{}')
   dest=root/'prepared'
   with mock.patch.object(p,'sha',return_value='4668cac041f0dee1257c95a9e60c46d34fff53ffb5ab0010ec3647e114d909d0'):
    with self.assertRaisesRegex(ValueError,'completed provisional'):p.prepare(root/'template.json',root/'outer.json',work,out,dest,root/'regional-output')
   self.assertFalse(dest.exists())
if __name__=='__main__':unittest.main()
