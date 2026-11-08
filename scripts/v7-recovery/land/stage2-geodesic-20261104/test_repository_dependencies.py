"""Ensure stage-two code dependencies are present and match their frozen pins."""
import ast
import hashlib
from pathlib import Path
import unittest

import build_stage2
import orchestrate_stage2

HERE = Path(__file__).resolve().parent
LAND = HERE.parent


def literal_assignment(path, name):
    tree = ast.parse(path.read_text())
    values = [n.value for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    if len(values) != 1:
        raise AssertionError(f'expected one {name} assignment in {path}')
    return ast.literal_eval(values[0])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RepositoryDependenciesTest(unittest.TestCase):
    def test_orchestrator_and_core_files_are_present(self):
        code = orchestrate_stage2.code_hashes(lambda: None)
        self.assertTrue(set(build_stage2.CODE_NAMES).issubset(code))
        expected = orchestrate_stage2.REVIEWED_SEED_FREEZE
        self.assertIsNotNone(expected)
        self.assertFalse(orchestrate_stage2.SEED_FREEZE_CURRENT)
        self.assertNotEqual({n: code['seed-producer/' + n] for n in orchestrate_stage2.SEED_NAMES}, expected)
        self.assertIn('seed_worker.py', orchestrate_stage2.SEED_NAMES)
        self.assertEqual(code['seed-producer/seed_worker.py'], sha(HERE / 'seed-producer' / 'seed_worker.py'))
        self.assertNotIn('guarded_exec.py', orchestrate_stage2.SEED_NAMES)
        self.assertNotIn('guarded_raster_exec.py', orchestrate_stage2.SEED_NAMES)

    def test_current_sources_and_distinct_reviewed_checker_pins(self):
        producer = HERE / 'seed-producer' / 'seed_producer.py'
        pins = literal_assignment(producer, 'TRUSTED_CODE')
        pins['terminal_checker'] = literal_assignment(producer, 'TRUSTED_TERMINAL_CHECKER')
        files = {
            'seed_builder': LAND / 'neon-mainland-regions-20261104/rasterizer/build_seed.py',
            'seed_kernel': LAND / 'neon-mainland-regions-20261104/rasterizer/seed_kernel.cpp',
            'closure_checker': LAND / 'mainland-source-verification-20261104/validate_water_closure_v2.py',
            'terminal_checker': LAND / 'mainland-source-verification-20261104/validate_terminal_closure.py',
        }
        self.assertEqual(set(files), set(pins))
        current = dict(pins)
        # Current direct-path checkers remain provisional-only. Do not replace
        # the separately reviewed historical freeze to make a test pass.
        current['closure_checker'] = literal_assignment(producer, 'PROVISIONAL_CLOSURE_CHECKER')
        current['terminal_checker'] = literal_assignment(producer, 'PROVISIONAL_TERMINAL_CHECKER')
        self.assertNotEqual(current['closure_checker'], pins['closure_checker'])
        self.assertNotEqual(current['terminal_checker'], pins['terminal_checker'])
        for name, path in files.items():
            with self.subTest(name=name):
                self.assertEqual(sha(path), current[name])
        component = LAND / 'fresh-components-20261104/build_components.py'
        source = LAND / 'fresh-components-20261104/components.py'
        self.assertEqual(sha(source), literal_assignment(component, 'COMPONENT_SOURCE_SHA256'))


if __name__ == '__main__':
    unittest.main()
