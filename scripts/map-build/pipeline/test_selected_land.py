"""Exercise the main command's direct land stages and useful phase checkpoints."""
import json
from unittest.mock import patch
import unittest

from map_build.execution.runtime import Checkpoints, Timing
from map_build.land.test_seeds import SeedBuildTests
import run_pipeline


class SelectedLandTests(unittest.TestCase):
    def setUp(self):
        SeedBuildTests.setUp(self)
        self.domain['land_baseline_policy']['tie_tolerance_metres'] = '0.00001'
        self.runner = run_pipeline.Pipeline.__new__(run_pipeline.Pipeline)
        self.runner.selection = dict(domains={'mainland': self.domain, 'regional': dict(
            features=[], affiliations=[], category_bindings=self.domain['category_bindings'])})
        self.runner.out = self.root/'run'
        self.runner.out.mkdir()
        (self.runner.out/'input-selection.json').write_text(json.dumps(self.runner.selection))
        self.runner.cfg = dict(seed_controls=dict(strip_rows=3,workers=2),
                               land_controls=dict(numerical_guard_metres=1000,chunk_columns=1024))
        self.runner.timing = Timing(self.runner.out/'timing-events.jsonl')
        self.addCleanup(self.runner.timing.close)
        self.runner.checkpoints = Checkpoints(self.runner.out/'checkpoints','fixture')

    def test_direct_land_chain_and_resume_reuse_sealed_phases(self):
        output = self.runner.build_selected_land(self.root/'physical')
        counts = json.loads((output/'report.json').read_text())['counts']
        self.assertEqual(counts,{'77':2,'301':1,'999':1})
        def must_reuse(*args,**kwargs):
            self.fail('completed component construction was repeated')
        with patch('map_build.land.connected.build_components',must_reuse):
            self.assertEqual(self.runner.build_selected_land(self.root/'physical'),output)
        self.runner.checkpoints.verify_all()
        self.assertEqual(len(list((self.runner.out/'checkpoints').glob('*/complete.json'))),5)
        (self.runner.out/'input-selection.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'identity changed'):
            self.runner.build_selected_land(self.root/'physical')
