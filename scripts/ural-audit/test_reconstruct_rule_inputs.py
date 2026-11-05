import copy,hashlib,json,unittest
from unittest.mock import patch
import reconstruct_rule_inputs as mod
class TestReconstruction(unittest.TestCase):
 def setUp(self):
  b={'type':'LineString','coordinates':[[0,2],[0,1],[0,0]]};c={'type':'LineString','coordinates':[[0,0],[1,0],[2,0],[3,0],[4,0]]};bh=mod.digest(mod.raw(b));ch=mod.digest(mod.raw(c));div=mod.digest(mod.raw([[0,1],[0,0],[1,0],[2,0],[3,0]]));cfg={'bounds':[0,0,1,1],'sha256':{'divider':div}};cfgh=mod.digest(json.dumps(cfg,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False).encode());self.snap={'mainland_boundaries':[{'boundary_id':'ural_kara_coast_to_caspian','geometry_sha256':bh,'geometry':b}],'routes':[{'route_id':'europe_caspian_closure_v1','geometry_sha256':ch,'geometry':c}]};self.obs={'apply':{'config':cfg},'lineage':{'selected_boundary_sha256':bh,'selected_closure_sha256':ch}};self.patcher=patch.multiple(mod,BOUNDARY=bh,CLOSURE=ch,DIVIDER=div,CONFIG=cfgh,START=[0,1]);self.patcher.start();self.addCleanup(self.patcher.stop)
 def test_reconstruct_exact_bytes(self):
  d,c=mod.derive(self.snap,self.obs);self.assertEqual(mod.digest(d),mod.DIVIDER);self.assertEqual(mod.digest(c),mod.CONFIG)
 def test_reject_changed_source(self):
  s=copy.deepcopy(self.snap);s['mainland_boundaries'][0]['geometry']['coordinates'][-1][0]+=.01
  with self.assertRaises(AssertionError):mod.derive(s,self.obs)
 def test_reject_changed_policy(self):
  o=copy.deepcopy(self.obs);o['apply']['config']['bounds'][0]+=.01
  with self.assertRaises(AssertionError):mod.derive(self.snap,o)
if __name__=='__main__':unittest.main()
