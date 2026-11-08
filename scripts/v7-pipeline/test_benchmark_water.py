import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import benchmark_water
from execution_state import Timing
from run_pipeline import pin


class WaterBenchmarkTests(unittest.TestCase):
    def reference(self, root):
        for relative in ('physical/physical', 'land', 'final'):
            directory = root / relative
            directory.mkdir(parents=True)
            (directory / 'rows.u32le').write_bytes(struct.pack('<II', 0, 1))
            (directory / 'runs.u32le').write_bytes(struct.pack('<II', 2, 7))
            (directory / 'report.json').write_text(json.dumps({'grid': {'width': 2, 'height': 1}}))
        report = {'stages': {stage: {'outputs_complete': True}
                             for stage in ('physical', 'mainland', 'water')},
                  'final': {key: pin(root / 'final' / name) for key, name in
                            (('rows', 'rows.u32le'), ('runs', 'runs.u32le'), ('report', 'report.json'))}}
        (root / 'report.json').write_text(json.dumps(report))
        (root / 'request.json').write_text('{}')

    def run_benchmark(self, reference, out, *, different=False, change_input=False):
        calls = []

        class FakePipeline:
            def __init__(self, config, candidate, *, allow_provisional):
                self.out = candidate
                candidate.mkdir()
                self.timing = Timing(candidate / 'timing-events.jsonl', attempt='fresh')
                calls.append(('new', config, allow_provisional))

            def water(self, physical, land):
                calls.append(('water', physical, land))
                final = self.out / 'final'
                final.mkdir()
                for name in ('rows.u32le', 'runs.u32le'):
                    (final / name).write_bytes((reference / 'final' / name).read_bytes())
                if different:
                    (final / 'runs.u32le').write_bytes(struct.pack('<II', 2, 8))
                if change_input:
                    (land / 'report.json').write_text('{}')
                return final

            def close(self):
                calls.append(('close',))
                self.timing.close()

        with patch.object(benchmark_water, 'Pipeline', FakePipeline), \
                patch.object(benchmark_water, 'validate_runtime'), \
                patch.object(benchmark_water, 'environment', return_value={'test': True}):
            result = benchmark_water.benchmark(reference, reference / 'request.json', out)
        return result, calls

    def test_whole_water_stage_is_fresh_and_all_final_cells_are_compared(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reference, out = root / 'reference', root / 'benchmark'
            self.reference(reference)
            result, calls = self.run_benchmark(reference, out)
            self.assertEqual(calls[1], ('water', reference / 'physical/physical', reference / 'land'))
            self.assertEqual(calls[-1], ('close',))
            self.assertTrue(result['water']['outputs_complete'])
            self.assertTrue(result['water']['timing_complete'])
            self.assertEqual(result['comparison']['cells_compared'], 2)
            self.assertEqual(result['comparison']['changed_cells'], 0)
            self.assertTrue(result['comparison']['byte_identical'])
            self.assertTrue((out / 'stage-timing.json').is_file())
            self.assertTrue((out / 'comparison.json').is_file())

    def test_changed_final_cells_fail_with_saved_comparison(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reference, out = root / 'reference', root / 'benchmark'
            self.reference(reference)
            with self.assertRaisesRegex(ValueError, 'water output differs'):
                self.run_benchmark(reference, out, different=True)
            comparison = json.loads((out / 'comparison.json').read_text())
            self.assertEqual(comparison['changed_cells'], 2)

    def test_input_mutation_and_incomplete_reference_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            reference = root / 'reference'
            self.reference(reference)
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                self.run_benchmark(reference, root / 'mutation', change_input=True)
            report = json.loads((reference / 'report.json').read_text())
            report['stages']['water']['outputs_complete'] = False
            (reference / 'report.json').write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'completed physical'):
                self.run_benchmark(reference, root / 'incomplete')

    def test_output_must_not_overlap_reference(self):
        with tempfile.TemporaryDirectory() as td:
            reference = Path(td) / 'reference'
            self.reference(reference)
            with self.assertRaisesRegex(ValueError, 'must be disjoint'):
                self.run_benchmark(reference, reference / 'benchmark')


if __name__ == '__main__':
    unittest.main()
