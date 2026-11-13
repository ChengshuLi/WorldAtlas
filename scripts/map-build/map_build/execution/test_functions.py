from pathlib import Path
import tempfile
import unittest

from map_build.execution.runtime import Checkpoints, Timing, pin


class FunctionCheckpointTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'source.txt'
        self.source.write_text('input')
        self.output = self.root / 'output'
        self.checkpoints = Checkpoints(self.root / 'checkpoints', 'attempt')
        self.timing = Timing(self.root / 'timing-events.jsonl')
        self.addCleanup(self.timing.close)

    def call(self, action):
        return self.checkpoints.run_function('calculate', 'water', action, (), timing=self.timing,
                                            inputs=[pin(self.source)], outputs=[self.output])

    def calculate(self):
        self.output.mkdir()
        (self.output / 'result').write_text(self.source.read_text())
        return {'result': str(self.output / 'result')}

    def test_resume_trusts_function_changes_and_preserves_the_output_record(self):
        first = self.call(self.calculate)

        def changed_function():
            self.fail('a completed calculation was repeated')

        self.assertEqual(self.call(changed_function), first)
        self.assertEqual(Path(first['result']).read_text(), 'input')

    def test_stage_accepts_explicit_keyword_inputs(self):
        def calculate(*, suffix):
            result = self.calculate()
            result['suffix'] = suffix
            return result
        result = self.checkpoints.run_function('calculate', 'water', calculate, (), kwargs={'suffix': 'selected'},
                                              timing=self.timing, inputs=[pin(self.source)], outputs=[self.output])
        self.assertEqual(result['suffix'], 'selected')

    def test_changed_data_or_output_is_rejected(self):
        self.call(self.calculate)
        (self.output / 'result').write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'output changed'):
            self.call(self.calculate)
        (self.output / 'result').write_text('input')
        self.source.write_text('new input')
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            self.call(self.calculate)

    def test_failed_calculation_retains_partial_files_and_can_restart(self):
        def interrupted():
            self.output.mkdir()
            (self.output / 'partial').write_text('partial')
            raise InterruptedError('interrupted')

        with self.assertRaises(InterruptedError):
            self.call(interrupted)
        self.call(self.calculate)
        preserved = list((self.root / 'preserved').glob('calculate-*/0-output/partial'))
        self.assertEqual(len(preserved), 1)
        self.assertEqual(preserved[0].read_text(), 'partial')
        self.assertEqual((self.output / 'result').read_text(), 'input')


if __name__ == '__main__':
    unittest.main()
