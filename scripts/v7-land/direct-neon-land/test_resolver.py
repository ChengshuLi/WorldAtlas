import json,unittest
from pathlib import Path
import compile_land as c
import run_single_generation as single
import test_compile_land as direct_tests
import test_single_generation as single_tests

class Resolver(unittest.TestCase):
    @classmethod
    def setUpClass(cls):direct_tests.DirectLand.setUpClass();single_tests.OneGeneration.setUpClass()
    @classmethod
    def tearDownClass(cls):single_tests.OneGeneration.tearDownClass();direct_tests.DirectLand.tearDownClass()
    def setUp(self):self.f=direct_tests.DirectLand('runTest');self.f.setUp()
    def tearDown(self):self.f.tearDown()
    def test_partial_rules_are_explicit_and_no_land_output(self):
        self.f.snap['affiliations'].pop();self.f.refresh_snapshot();cfg=self.f.d/'config.json';cfg.write_text(json.dumps(self.f.cfg));out=self.f.base/'resolved'
        result=c.prepare(cfg,out,True,resolve_only=True)
        self.assertEqual(result['schema'],'direct-land-explicit-resolution-v1');self.assertEqual(result['status'],'research-partial-no-land-grid')
        rules=json.loads((out/'compiler-config.json').read_bytes())['rules'];self.assertEqual(len(rules),1);self.assertEqual(rules[0]['kind'],'polygon_partition')
        self.assertEqual(result['compiler_config_sha256'],c.assign_land.sha(out/'compiler-config.json'))
        self.assertEqual(result['snapshot_sha256'],self.f.cfg['snapshot']['sha256']);self.assertTrue(result['gdal_version']);self.assertTrue(result['numpy_version']);self.assertFalse((out/'report.json').exists());self.assertFalse((out/'land').exists())
        with self.assertRaisesRegex(ValueError,'unassigned component'):c.prepare(cfg,self.f.base/'full',True)
    def test_unselected_fails_before_partial_output(self):
        self.f.snap['affiliations'][0]['evidence']['execution_status']='research_only_not_selected';self.f.refresh_snapshot();cfg=self.f.d/'config.json';cfg.write_text(json.dumps(self.f.cfg));out=self.f.base/'resolved'
        with self.assertRaisesRegex(ValueError,'explicit research selection'):c.prepare(cfg,out,True,resolve_only=True)
        self.assertFalse(out.exists())
    def test_same_run_manifest_partial(self):
        fixture=single_tests.OneGeneration('runTest');fixture.setUp();
        try:
            single.run(fixture.request(),fixture.out,True)
            out=fixture.out/'resolved';r=c.prepare(fixture.out/'configs/land.json',out,True,fixture.out/'manifests/components.json',resolve_only=True)
            self.assertEqual(r['component_generation_method'],'single-generation-manifest');self.assertEqual(r['component_manifest_sha256'],c.assign_land.sha(fixture.out/'manifests/components.json'))
            self.assertFalse((out/'report.json').exists());self.assertFalse((out/'land').exists())
        finally:fixture.tearDown()
if __name__=='__main__':unittest.main()
