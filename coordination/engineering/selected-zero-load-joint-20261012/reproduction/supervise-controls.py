"""Actual tiny owned children, including an injected monitor read failure."""
import json, pathlib, runpy, subprocess, sys, tempfile, unittest
from unittest.mock import patch
SCRIPT = pathlib.Path(__file__).with_name('supervise.py')

class Lifetime(unittest.TestCase):
    def test_actual_success_has_observed_empty_terminal_group(self):
        with tempfile.TemporaryDirectory() as directory:
            out = pathlib.Path(directory)/'proof'
            command = [sys.executable, '-c', 'print("ordinary child")']
            with patch.object(sys, 'argv', [str(SCRIPT), str(out), *command]):
                runpy.run_path(str(SCRIPT), run_name='__main__')
            result = json.loads((out/'operating.json').read_text())
            self.assertTrue(result['complete'])
            self.assertEqual(result['terminal_group_scan']['members'], [])
            self.assertEqual(result['cleanup_group_scan']['members'], [])

    def test_failed_monitor_unconditionally_terminates_actual_sleeping_group(self):
        with tempfile.TemporaryDirectory() as directory:
            out = pathlib.Path(directory)/'proof'
            command = [sys.executable, '-c', 'import time; time.sleep(60)']
            original = subprocess.check_output
            calls = 0
            def fail_first_scan(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise OSError('forced monitor read failure')
                return original(*args, **kwargs)
            with patch.object(sys, 'argv', [str(SCRIPT), str(out), *command]), patch.object(subprocess, 'check_output', side_effect=fail_first_scan):
                with self.assertRaises(AssertionError):
                    runpy.run_path(str(SCRIPT), run_name='__main__')
            result = json.loads((out/'operating.json').read_text())
            self.assertFalse(result['complete'])
            self.assertEqual(result['failure'], 'supervisor-exception')
            self.assertEqual(result['returncode'], -9)
            self.assertTrue(result['terminal_group_scan']['members'])
            self.assertEqual(result['cleanup_group_scan']['members'], [])
            self.assertEqual(result['errors'][0]['message'], 'forced monitor read failure')
            self.assertLess(result['elapsed_seconds'], 5)

if __name__ == '__main__':
    unittest.main()
