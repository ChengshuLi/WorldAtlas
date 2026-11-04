import json,tempfile,unittest
from pathlib import Path
import build_components
import test_build_land as fixture_module

class ComponentsTest(unittest.TestCase):
 def fixture(self,root):
  helper=fixture_module.TestBuild('runTest');_,land=helper.fixture(root);config={'schema':'simple-v2-components-v1','grid':land['grid'],'physical_rows':land['physical_rows'],'physical_runs':land['physical_runs'],'physical_report':land['physical_report'],'minimum_free_bytes':0};path=root/'config'/'components.json';path.write_text(json.dumps(config));return path,config
 def test_build_matches_independent_components(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);path,_=self.fixture(root);r=build_components.build(path,root/'components');self.assertEqual(r['rows_sha256'],fixture_module.pin(root/'provenance'/'cr')['sha256']);self.assertEqual(r['runs_sha256'],fixture_module.pin(root/'provenance'/'cu')['sha256']);self.assertEqual(r['status'],'research-not-published')
 def test_report_and_space_guards(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);path,c=self.fixture(root);c['minimum_free_bytes']=1<<60;path.write_text(json.dumps(c))
   with self.assertRaisesRegex(ValueError,'free disk'):build_components.build(path,root/'out')
   self.assertFalse((root/'out').exists());c['minimum_free_bytes']=0;report=Path(c['physical_report']['path']);data=json.loads(report.read_text());data['grid']['north']=29;report.write_text(json.dumps(data));c['physical_report']=fixture_module.pin(report);path.write_text(json.dumps(c))
   with self.assertRaisesRegex(ValueError,'physical report mismatch'):build_components.build(path,root/'out')
   self.assertFalse((root/'out').exists())
if __name__=='__main__':unittest.main()
