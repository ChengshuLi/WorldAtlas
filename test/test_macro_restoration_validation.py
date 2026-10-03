import importlib.util,pathlib,sys,unittest,subprocess,tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from shapely.geometry import Polygon
spec=importlib.util.spec_from_file_location('macro',pathlib.Path(__file__).resolve().parents[1]/'scripts/validate-macro-restoration.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Validation(unittest.TestCase):
 def test_source_water_hole_cannot_be_filled(self):
  coast=Polygon([(0,0),(1,0),(1,1),(0,1)],holes=[[(.2,.2),(.4,.2),(.4,.4),(.2,.4)]]);filled=Polygon([(0,0),(1,0),(1,1),(0,1)])
  with self.assertRaisesRegex(ValueError,'Source footprint'):module.exact(filled,coast,'lake')
 def test_source_polygon_cannot_be_shifted(self):
  source=Polygon([(0,0),(.1,0),(.1,.1),(0,.1)]);shifted=Polygon([(.01,0),(.11,0),(.11,.1),(.01,.1)])
  with self.assertRaisesRegex(ValueError,'Source footprint'):module.exact(shifted,source,'offset')
 def test_shared_border_allowed_positive_land_overlap_rejected(self):
  a=Polygon([(0,0),(1,0),(1,1),(0,1)]);border=Polygon([(1,0),(2,0),(2,1),(1,1)])
  module.check_overlap(a,border,'border')
  with self.assertRaisesRegex(ValueError,'positive-area'):module.check_overlap(a,a,'duplicate')
 def test_tampered_source_pin_rejected_before_stage_materialization(self):
  with tempfile.TemporaryDirectory() as directory:
   root=pathlib.Path(directory)/'checkout';(root/'data').mkdir(parents=True);(root/'data/hierarchy.json').write_text('{}');(root/'data/world-index.json').write_text('{"parts":[]}');output=pathlib.Path(directory)/'output'
   result=subprocess.run([sys.executable,str(pathlib.Path(__file__).resolve().parents[1]/'scripts/compose-macro-restoration.py'),'--root',str(root),'--output',str(output)],capture_output=True,text=True)
   self.assertNotEqual(result.returncode,0);self.assertIn('Pinned source bytes changed',result.stderr);self.assertFalse(output.exists())
if __name__=='__main__':unittest.main()
