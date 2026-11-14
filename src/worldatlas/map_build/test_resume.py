"""Resume validates selected data and outputs while trusting code changes."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from worldatlas.map_build import build as pipeline


class ExecutorResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        inputs = self.root / 'inputs'
        inputs.mkdir()
        sentinel = pipeline.write(inputs / 'sentinel.json', {})
        required = ('land_config', 'water_config', 'raw_manifest')
        cfg = {
            'schema': 'worldatlas-end-to-end-pipeline-v1',
            'input_root': str(self.root),
            'sources': {key: pipeline.pin(sentinel) for key in required},
        }
        cfg['sources']['raw_manifest'] = pipeline.pin(self.source_path(inputs))
        self.config = pipeline.write(inputs / 'request.json', cfg)
        self.saved_selection=pipeline.write(inputs/'selection.json',{'schema':'worldatlas-input-selection-v3','geography':{'features':[],'basins':[],'affiliations':[],'routes':[],'category_bindings':[]},'raw_sources':[]})
        self.out = self.root / 'run'
        self.source = inputs / 'source.bin'

    def runner(self, resume=False):
        runner = pipeline.Pipeline(self.config, self.out, resume=resume, selection=self.saved_selection)
        self.addCleanup(runner.close)
        return runner

    def test_changed_completed_output_fails_before_reuse(self):
        first = self.runner()
        self.execute(first)
        first.close()
        (self.out / 'result/result.bin').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'output changed'):
            self.runner(resume=True)

    def test_changed_input_pin_fails_before_reuse(self):
        first = self.runner()
        self.execute(first)
        first.close()
        self.source.write_bytes(b'changed input')
        with self.assertRaisesRegex(ValueError, 'source pin mismatch'):
            self.runner(resume=True)

    def test_lost_timing_prefix_is_rejected_before_checkpoint_reuse(self):
        first = self.runner()
        self.execute(first)
        first.close()
        (self.out / 'timing-events.jsonl').write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'timing journal lost'):
            self.runner(resume=True)

    def test_changed_code_is_recorded_and_resume_keeps_the_original_identity(self):
        first = self.runner()
        original = pipeline.pin(self.out / 'run-identity.json')
        first.close()
        with patch.object(pipeline, 'code_identity', return_value={'changed.py': '0' * 64}), \
                patch.object(pipeline, 'repository_identity', return_value={'commit': 'changed'}):
            resumed = self.runner(resume=True)
            self.assertEqual(pipeline.pin(self.out / 'run-identity.json'), original)
            self.assertEqual(
                pipeline.read(resumed.attempt_dir / 'producer.json')['code'],
                {'changed.py': '0' * 64},
            )

    def test_two_live_runners_cannot_resume_same_run(self):
        self.runner()
        with self.assertRaisesRegex(ValueError, 'another pipeline runner'):
            self.runner(resume=True)

    def test_generated_document_must_match_on_resume(self):
        first = self.runner()
        path = first.document('handoff', {'input': 'fixed'})
        first.close()
        second = self.runner(resume=True)
        self.assertEqual(second.document('handoff', {'input': 'fixed'}), path)
        with self.assertRaisesRegex(ValueError, 'generated request changed'):
            second.document('handoff', {'input': 'different'})

    def source_path(self, inputs):
        path = inputs / 'source.bin'
        path.write_bytes(b'final-output\x00\x01\x02')
        return path

    def execute(self, runner):
        output = self.out / 'result'

        def calculate():
            output.mkdir()
            (output / 'result.bin').write_bytes(self.source.read_bytes())
            return {'directory': str(output)}

        return runner.checkpoints.run_function(
            'fixture-stage',
            'water',
            calculate,
            (),
            timing=runner.timing,
            inputs=[pipeline.pin(self.source)],
            outputs=[output],
        )
