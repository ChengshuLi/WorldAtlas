import unittest
from unittest.mock import patch

import caucasus_stage2_binding as binding


class BindingTest(unittest.TestCase):
    def config(self):
        return {'recipe': {'path': 'recipe', 'sha256': 'a' * 64},
                'hydro': {'path': 'hydro', 'sha256': 'b' * 64},
                'author': {'path': 'author', 'sha256': 'c' * 64},
                'code_sha256': {name: 'd' * 64 for name in binding.CODE}}

    def test_missing_binding_code_pin_rejected(self):
        cfg = self.config()
        cfg['code_sha256'].pop('caucasus_stage2_binding.py')
        with self.assertRaisesRegex(ValueError, 'complete Caucasus code'):
            binding.verify_config(cfg)

    def test_seed_command_executes_direct_producer(self):
        with patch.object(binding, 'verify_config'), patch.object(binding, 'validate_direct_request'), patch.object(binding, 'digest', return_value='e' * 64), patch.object(binding.subprocess, 'run') as run:
            binding.run_seed(self.config(), 'request', 'e' * 64, 'producer', 'f' * 64,
                             'work', 'output', 'gate')
        args = run.call_args[0][0]
        self.assertIn('--producer-dir', args)
        self.assertNotIn('--worker-sha256', args)
        self.assertTrue(run.call_args[1]['check'])

    def test_independent_gate_trace_is_required(self):
        cfg = self.config()
        source = {'schema': 'caucasus-source-seed-gate-v1', 'snapshot_sha256': 's'}
        effective = {'original_snapshot_sha256': 's'}
        trace = {'source_derivation': {'source_gate': source, 'effective_snapshot': effective}}
        gate = dict(source, request_sha256='r', seed_producer_executed=True,
                    seed_producer_sha256='p', seed_worker_sha256=None, effective_snapshot=effective)
        with patch.object(binding, 'verify_config'), patch.object(binding.validation, 'validate', return_value=('ok', trace)):
            result, report = binding.validate_seed(cfg, 'request', 'r', gate, 'p', lambda: None, {}, {}, {}, {})
            self.assertEqual(result, 'ok')
            self.assertEqual(report['schema'], 'caucasus-stage2-binding-v1')
            gate['seed_producer_sha256'] = 'wrong'
            with self.assertRaisesRegex(ValueError, 'independently derived'):
                binding.validate_seed(cfg, 'request', 'r', gate, 'p', lambda: None, {}, {}, {}, {})


if __name__ == '__main__':
    unittest.main()
