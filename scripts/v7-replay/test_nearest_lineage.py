import importlib.util,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
REPO=HERE.parent;DIRECT=REPO/'v7-land'/'direct-neon-land'
for p in (REPO,DIRECT,HERE):sys.path.insert(0,str(p))
import test_derive_seed as fixture_module
import nearest_mainland as nearest
import build_prefill_plan as planner
import run_single_generation_nearest as staged_runner

class NearestLineage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f=fixture_module.Joined('runTest');cls.f.setUp()
        with patch.dict(sys.modules,{'run_single_generation_nearest':staged_runner}):cls.f.test_actual_direct_resolver_to_nearest()
        cls.base=cls.f.base/'one-integrated';cls.rp=cls.base/'report.json';cls.report=json.loads(cls.rp.read_bytes())
        cls.physical={'rows_sha256':cls.f.pins['physical_rows']['sha256'],'runs_sha256':cls.f.pins['physical_runs']['sha256']}
        rows=cls.base/'integrated/land/rows.u32le';runs=cls.base/'integrated/land/runs.u32le'
        cls.land={'resolved_rows':rows.resolve(),'resolved_runs':runs.resolve(),'rows_sha256':nearest.sha(rows),'runs_sha256':nearest.sha(runs)}
        cls.revision=cls.f.snapshot['decision_revision'];cls.snapshot_sha=nearest.sha(cls.f.sp)
    @classmethod
    def tearDownClass(cls):cls.f.tearDown()
    def validate(self,report=None,physical=None,land=None,revision=None,grid=None):
        with patch.object(planner,'canonical_physical_grid',return_value=grid or self.f.grid):
            return planner.validate_land_report(report or self.report,self.rp,physical or self.physical,land or self.land,self.snapshot_sha,revision or self.revision,self.f.base)
    def test_valid_complete_report(self):self.assertIsNone(self.validate())
    def test_shifted_grid_rejected(self):
        with self.assertRaises(ValueError):self.validate(grid={**self.f.grid,'west':-179})
    def test_wrong_physical_input_rejected(self):
        with self.assertRaises(ValueError):self.validate(physical={**self.physical,'rows_sha256':'0'*64})
    def test_mismatched_physical_report_pin_rejected(self):
        with self.assertRaises(ValueError):self.validate(report={**self.report,'physical_report_sha256':'0'*64})
    def test_code_hash_mismatch_rejected(self):
        bad={**self.report,'code_sha256':{**self.report['code_sha256'],'compile_land.py':'0'*64}}
        with self.assertRaises(ValueError):self.validate(report=bad)
    def test_partial_resolver_report_rejected(self):
        with self.assertRaises(ValueError):self.validate(report={**self.report,'schema':'single-generation-land-resolution-report-v1'})
    def test_accepted_revision_rejected(self):
        with self.assertRaises(ValueError):self.validate(revision={**self.revision,'status':'accepted'})
    def mutate_rejected(self,relative):
        p=self.base/relative;data=p.read_bytes()
        try:
            p.write_bytes(data+b'x')
            with self.assertRaises(ValueError):self.validate()
        finally:p.write_bytes(data)
    def test_component_bytes_rejected(self):self.mutate_rejected('single/components/runs.u32le')
    def test_builder_bytes_rejected(self):self.mutate_rejected('single/components/component-builder')
    def test_merged_config_bytes_rejected(self):self.mutate_rejected('integrated/configs/merged.json')
    def test_final_rows_bytes_rejected(self):self.mutate_rejected('integrated/land/rows.u32le')
    def test_final_runs_bytes_rejected(self):self.mutate_rejected('integrated/land/runs.u32le')
    def test_rehashed_forged_merged_rules_rejected(self):
        import hashlib
        paths=[self.base/'integrated/configs/merged.json',self.base/'integrated/land/config.json',self.base/'integrated/land/report.json',self.base/'integrated/report.json']
        original={p:p.read_bytes() for p in paths}
        try:
            merged=json.loads(original[paths[0]]);merged['rules'].append({'component_id':999999,'rule_id':'forged','source_evidence':['forged'],'kind':'whole_component','code':17})
            payload=(json.dumps(merged,sort_keys=True,separators=(',',':'))+'\n').encode();paths[0].write_bytes(payload);paths[1].write_bytes(payload);merged_sha=hashlib.sha256(payload).hexdigest()
            land_report=json.loads(original[paths[2]]);land_report['config_sha256']=merged_sha;paths[2].write_text(json.dumps(land_report))
            adapter=json.loads(original[paths[3]]);adapter['merged_config_sha256']=merged_sha;adapter['land_report_sha256']=nearest.sha(paths[2]);paths[3].write_text(json.dumps(adapter))
            forged={**self.report,'adapter_report_sha256':nearest.sha(paths[3])}
            with self.assertRaisesRegex(ValueError,'merged rules do not preserve'):self.validate(report=forged)
        finally:
            for p,data in original.items():p.write_bytes(data)
    def test_water_lineage_rejects_different_physical_report(self):
        import direct_lineage
        with patch.object(planner,'canonical_physical_grid',return_value=self.f.grid):
            self.assertEqual(direct_lineage.validate_direct_land(self.rp,nearest.sha(self.rp),self.physical,self.land,self.snapshot_sha,self.revision,self.f.base,self.report['physical_report_sha256']),'single-generation-nearest-report-v1')
            with self.assertRaisesRegex(ValueError,'different physical report'):direct_lineage.validate_direct_land(self.rp,nearest.sha(self.rp),self.physical,self.land,self.snapshot_sha,self.revision,self.f.base,'0'*64)
    def test_wrong_snapshot_hash_rejected(self):
        with patch.object(planner,'canonical_physical_grid',return_value=self.f.grid):
            with self.assertRaises(ValueError):planner.validate_land_report(self.report,self.rp,self.physical,self.land,'0'*64,self.revision,self.f.base)
    def test_partial_report_file_rejected(self):
        bad=self.base/'single/resolution-report.json';data=json.loads(bad.read_bytes())
        with self.assertRaises(ValueError):self.validate(report=data)

if __name__=='__main__':unittest.main()
