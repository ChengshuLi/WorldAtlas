import importlib.util,json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
INTEGRATED=HERE
sys.path.insert(0,str(INTEGRATED))
spec=importlib.util.spec_from_file_location('direct_tests',INTEGRATED/'test_compile_land.py');direct=importlib.util.module_from_spec(spec);spec.loader.exec_module(direct)
sys.path.insert(0,str(HERE))
import run_single_generation as single

class OneGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):direct.DirectLand.setUpClass()
    @classmethod
    def tearDownClass(cls):direct.DirectLand.tearDownClass()
    def setUp(self):
        self.f=direct.DirectLand('runTest');self.f.setUp();self.d=self.f.d;self.out=self.f.base/'onegen'
    def tearDown(self):self.f.tearDown()
    def request(self):
        cfg=self.f.cfg
        report_path=self.d/'physical-report.json';report_path.write_text(json.dumps({'status':'candidate-only','grid':cfg['grid'],'output_sha256':{'rows.u32le':cfg['physical_rows']['sha256'],'runs.u32le':cfg['physical_runs']['sha256']}}))
        physical_report={'path':str(report_path),'sha256':single.compiler.assign_land.sha(report_path)}
        request={'schema':'single-generation-direct-land-v1','snapshot':cfg['snapshot'],'grid':cfg['grid'],'physical_rows':cfg['physical_rows'],'physical_runs':cfg['physical_runs'],'physical_report':physical_report,'source_files':cfg['source_files'],'strip_rows':cfg['strip_rows'],
                 'component_source_sha256':single.compiler.assign_land.sha(HERE.parent/'build_components.cpp')}
        path=self.d/'request.json';path.write_text(json.dumps(request));return path
    def test_one_generation_exact_original_output(self):
        result=single.run(self.request(),self.out,True);self.assertEqual(result['component_generations'],1)
        self.assertEqual(self.out.stat().st_mode & 0o077,0)
        self.f.run_build()
        for name in ('rows.u32le','runs.u32le'):
            self.assertEqual((self.out/'assignment/land'/name).read_bytes(),(self.f.out/'land'/name).read_bytes())
        self.assertFalse((self.out/'assignment/verified-component-runs.u32le').exists())
        manifest=json.loads((self.out/'manifests/components.json').read_text());self.assertEqual(manifest['pins']['physical_rows']['sha256'],self.f.cfg['physical_rows']['sha256'])
    def test_prefill_binds_same_run_lineage(self):
        single.run(self.request(),self.out,True)
        replay=HERE.parents[1]/'v7-replay';sys.path.insert(0,str(replay))
        import build_prefill_plan as planner
        report_path=self.out/'report.json';report=json.loads(report_path.read_text())
        phys={'rows_sha256':self.f.cfg['physical_rows']['sha256'],'runs_sha256':self.f.cfg['physical_runs']['sha256']}
        rows=self.out/'assignment/land/rows.u32le';runs=self.out/'assignment/land/runs.u32le'
        land={'resolved_rows':rows.resolve(),'resolved_runs':runs.resolve(),'rows_sha256':single.compiler.assign_land.sha(rows),'runs_sha256':single.compiler.assign_land.sha(runs)}
        revision=self.f.snap['decision_revision'];snapshot_sha=self.f.cfg['snapshot']['sha256']
        from unittest.mock import patch
        with patch.object(planner,'canonical_physical_grid',return_value=self.f.cfg['grid']):
            planner.validate_land_report(report,report_path,phys,land,snapshot_sha,revision,self.f.base)
        bad_report={**report,'code_sha256':{**report['code_sha256'],'runner':'invalid'}}
        with patch.object(planner,'canonical_physical_grid',return_value=self.f.cfg['grid']):
            with self.assertRaisesRegex(ValueError,'orchestration report mismatch'):
                planner.validate_land_report(bad_report,report_path,phys,land,snapshot_sha,revision,self.f.base)
        shifted={**self.f.cfg['grid'],'west':self.f.cfg['grid']['west']+1}
        with patch.object(planner,'canonical_physical_grid',return_value=shifted):
            with self.assertRaisesRegex(ValueError,'manifest does not bind'):
                planner.validate_land_report(report,report_path,phys,land,snapshot_sha,revision,self.f.base)
        manifest=self.out/'manifests/components.json';doc=json.loads(manifest.read_text());doc['physical_report_kind']='raw-pipeline-report';manifest.write_text(json.dumps(doc))
        with patch.object(planner,'canonical_physical_grid',return_value=self.f.cfg['grid']):
            with self.assertRaisesRegex(ValueError,'orchestration report mismatch'):
                planner.validate_land_report(report,report_path,phys,land,snapshot_sha,revision,self.f.base)

    def test_prefill_rejects_tampered_stream_lineage(self):
        single.run(self.request(),self.out,True)
        replay=HERE.parents[1]/'v7-replay';sys.path.insert(0,str(replay))
        import build_prefill_plan as planner
        report_path=self.out/'report.json';report=json.loads(report_path.read_text())
        phys={'rows_sha256':self.f.cfg['physical_rows']['sha256'],'runs_sha256':self.f.cfg['physical_runs']['sha256']}
        rows=self.out/'assignment/land/rows.u32le';runs=self.out/'assignment/land/runs.u32le'
        land={'resolved_rows':rows.resolve(),'resolved_runs':runs.resolve(),'rows_sha256':single.compiler.assign_land.sha(rows),'runs_sha256':single.compiler.assign_land.sha(runs)}
        revision=self.f.snap['decision_revision'];snapshot_sha=self.f.cfg['snapshot']['sha256']
        component=self.out/'components/runs.u32le';original=component.read_bytes();component.write_bytes(original+b'x')
        from unittest.mock import patch
        with patch.object(planner,'canonical_physical_grid',return_value=self.f.cfg['grid']):
            with self.assertRaisesRegex(ValueError,'component artifact'):
                planner.validate_land_report(report,report_path,phys,land,snapshot_sha,revision,self.f.base)
        component.write_bytes(original)
        nested=self.out/'assignment/report.json';doc=json.loads(nested.read_text());doc['compiler_report']['input_sha256']['physical_runs']='0'*64
        nested.write_text(json.dumps(doc));report['land_report_sha256']=single.compiler.assign_land.sha(nested)
        from unittest.mock import patch
        with patch.object(planner,'canonical_physical_grid',return_value=self.f.cfg['grid']):
            with self.assertRaisesRegex(ValueError,'does not bind'):
                planner.validate_land_report(report,report_path,phys,land,snapshot_sha,revision,self.f.base)

    def test_incomplete_fails_without_completion_report(self):
        self.f.snap['affiliations'].pop();self.f.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'unassigned component'):single.run(self.request(),self.out,True)
        self.assertFalse((self.out/'report.json').exists())
    def test_manifest_tamper_rejected(self):
        single.run(self.request(),self.out,True)
        manifest=self.out/'manifests/components.json';record=json.loads(manifest.read_bytes());record['pins']['physical_runs']['sha256']='0'*64;manifest.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'component manifest pin mismatch'):single.compiler.prepare(self.out/'configs/land.json',self.out/'assignment2',True,manifest)
        self.assertFalse((self.out/'assignment2/report.json').exists())
    def test_manifest_cannot_upgrade_compose_to_raw_lineage(self):
        single.run(self.request(),self.out,True)
        manifest=self.out/'manifests/components.json';record=json.loads(manifest.read_bytes());record['physical_report_kind']='raw-pipeline-report';manifest.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'physical report kind mismatch'):single.compiler.prepare(self.out/'configs/land.json',self.out/'assignment2',True,manifest)
        self.assertFalse((self.out/'assignment2/report.json').exists())
    def test_explicit_unverified_mode_required(self):
        with self.assertRaisesRegex(ValueError,'explicit unverified'):single.run(self.request(),self.out,False)
        self.assertFalse(self.out.exists())
    def test_unselected_fails_before_generation(self):
        self.f.snap['affiliations'][0]['evidence']['execution_status']='research_only_not_selected';self.f.refresh_snapshot()
        with self.assertRaisesRegex(ValueError,'unselected or unknown land affiliation'):single.run(self.request(),self.out,True)
        self.assertFalse(self.out.exists())
    def test_physical_report_mismatch_fails_before_generation(self):
        p=self.request();r=json.loads(p.read_bytes());report=Path(r['physical_report']['path']);doc=json.loads(report.read_bytes());doc['output_sha256']['runs.u32le']='0'*64;report.write_text(json.dumps(doc));r['physical_report']['sha256']=single.compiler.assign_land.sha(report);p.write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'physical report does not bind'):single.run(p,self.out,True)
        self.assertFalse(self.out.exists())
    def test_code_change_fails_without_completion_report(self):
        from unittest.mock import patch
        first={'runner':'a'*64,'compiler':'b'*64,'stream_backend':'c'*64,'shared_backend':'d'*64}
        changed={**first,'runner':'e'*64}
        with patch.object(single,'code_hashes',side_effect=[first,changed]):
            with self.assertRaisesRegex(ValueError,'code changed during run'):single.run(self.request(),self.out,True)
        self.assertFalse((self.out/'report.json').exists())

    def test_unselected_stops_before_large_input_hashes(self):
        from unittest.mock import patch
        self.f.snap['affiliations'][0]['evidence']['execution_status']='research_only_not_selected';self.f.refresh_snapshot()
        request=self.request();snapshot_pin=self.f.cfg['snapshot']
        real_pin=single.compiler.pin
        with patch.object(single.compiler,'pin',side_effect=real_pin) as called:
            with self.assertRaisesRegex(ValueError,'unselected or unknown land affiliation'):single.run(request,self.out,True)
        self.assertEqual(called.call_count,1);self.assertEqual(called.call_args.args[0],snapshot_pin)
        self.assertFalse(self.out.exists())

    def test_component_source_mismatch_fails(self):
        p=self.request();r=json.loads(p.read_bytes());r['component_source_sha256']='0'*64;p.write_text(json.dumps(r))
        with self.assertRaisesRegex(ValueError,'source hash mismatch'):single.run(p,self.out,True)
        self.assertFalse(self.out.exists())
if __name__=='__main__':unittest.main()
