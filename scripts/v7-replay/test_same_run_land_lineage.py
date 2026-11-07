"""Use the real synthetic same-run land generator and shared planner validator."""
import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
REPO=HERE.parent if (HERE/'build_prefill_plan.py').is_file() else HERE.parent/'worldatlas-pr4-resume/scripts'
sys.path.insert(0,str(REPO/'v7-land/direct-neon-land'))
sys.path.insert(0,str(REPO/'v7-replay'))
import test_single_generation as scenario
import build_prefill_plan as planner
import direct_lineage

class SameRunLineageTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):scenario.OneGeneration.setUpClass()
 @classmethod
 def tearDownClass(cls):scenario.OneGeneration.tearDownClass()
 def test_real_same_run_report_is_bound(self):
  f=scenario.OneGeneration('runTest');f.setUp()
  try:
   req=f.request();request=json.loads(req.read_text());scenario.single.run(req,f.out,True)
   rp=f.out/'report.json';report=json.loads(rp.read_text())
   rows=f.out/'assignment/land/rows.u32le';runs=f.out/'assignment/land/runs.u32le'
   phys={'rows_sha256':f.f.cfg['physical_rows']['sha256'],'runs_sha256':f.f.cfg['physical_runs']['sha256']}
   land={'resolved_rows':rows.resolve(),'resolved_runs':runs.resolve(),'rows_sha256':direct_lineage.sha(rows),'runs_sha256':direct_lineage.sha(runs)}
   with patch.object(planner,'canonical_physical_grid',return_value=f.f.cfg['grid']):
    result=direct_lineage.validate_direct_land(rp,direct_lineage.sha(rp),phys,land,f.f.cfg['snapshot']['sha256'],
             f.f.snap['decision_revision'],f.f.base,request['physical_report']['sha256'])
    self.assertEqual(result,'single-generation-direct-land-report-v1')
    with self.assertRaisesRegex(ValueError,'different physical report'):
     direct_lineage.validate_direct_land(rp,direct_lineage.sha(rp),phys,land,f.f.cfg['snapshot']['sha256'],
             f.f.snap['decision_revision'],f.f.base,'0'*64)
  finally:f.tearDown()

if __name__=='__main__':unittest.main()
