"""Bounded checks of literal v2 seed pins, without test-time pin overrides."""
import contextlib
import hashlib
import pathlib
import unittest
from unittest import mock

import seed_producer
import test_seed_producer

HERE = pathlib.Path(__file__).resolve().parent


class LiteralFreeze(unittest.TestCase):
    def test_literal_pins_and_real_osm_synthetic_grid(self):
        paths = {
            'seed_builder': HERE / 'rasterizer/build_seed.py',
            'seed_kernel': HERE / 'rasterizer/seed_kernel.cpp',
            'closure_checker': HERE / 'closure-checkers/validate_water_closure_v2.py',
        }
        for name, path in paths.items():
            self.assertEqual(seed_producer.TRUSTED_CODE[name], hashlib.sha256(path.read_bytes()).hexdigest())
        terminal = HERE / 'closure-checkers/validate_terminal_closure.py'
        self.assertEqual(seed_producer.TRUSTED_TERMINAL_CHECKER, hashlib.sha256(terminal.read_bytes()).hexdigest())
        case = test_seed_producer.Producer('test_real_panama_archive_and_water_checker_on_synthetic_grid')
        case.setUp()
        try:
            # The inherited fixture normally patches the allowed hashes. Do not
            # patch them here: the literal checked-in constants must succeed.
            with mock.patch.object(test_seed_producer.patch, 'dict', lambda *a, **k: contextlib.nullcontext()):
                case.test_real_panama_archive_and_water_checker_on_synthetic_grid()
        finally:
            case.doCleanups()

    def test_unreviewed_checker_fails_before_output(self):
        case = test_seed_producer.Producer('test_runs_from_selected_structured_inputs')
        case.setUp()
        try:
            with self.assertRaisesRegex(ValueError, 'unreviewed executable code'):
                seed_producer.run(case.path, case.work, case.output)
            self.assertFalse(case.work.exists())
            self.assertFalse(case.output.exists())
        finally:
            case.doCleanups()


if __name__ == '__main__':
    unittest.main()
