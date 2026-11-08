import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from benchmark_stage import run_stage, stage_command


class BenchmarkStage(unittest.TestCase):
    def test_complete_stage_preserves_inputs_and_interpreter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'scripts').mkdir()
            script = root / 'scripts' / 'tiny.py'
            script.write_text('import pathlib,os\ndef main(a, *, emit):\n pathlib.Path(a[a.index("--out")+1]).mkdir()\n emit("finished")\n print("same PID",os.getpid())\n')
            admitted = {'invocation': {'command': [sys.executable, '/old/scripts/tiny.py', '--input', '/immutable/input', '--out', '/old/output']}}
            receipt = root / 'admitted.json'
            receipt.write_text(json.dumps(admitted))
            report = run_stage(receipt, root, root / 'benchmark')
            self.assertEqual(report['command'][0], sys.executable)
            self.assertEqual(report['command'][2:4], ['--input', '/immutable/input'])
            self.assertGreater(report['process_wall_seconds'], 0)
            self.assertEqual(report['execution_mode'], 'in-process-python-api')
            import os
            self.assertEqual((root / 'benchmark/builder.log').read_text(), f'finished\nsame PID {os.getpid()}\n')
            self.assertTrue((root / 'benchmark/candidate').is_dir())
            with self.assertRaises(ValueError):
                run_stage(receipt, root, root / 'benchmark')
            with self.assertRaises(ValueError):
                stage_command(admitted, root, root / 'new', ['--out', '/overwrite'])
            with self.assertRaises(ValueError):
                stage_command(admitted, root, root / 'new', ['--out=/overwrite'])
            admitted['invocation']['command'].append('--research-interval')
            command=stage_command(admitted,root,root/'new',['--pointwise-nearest'],drop_boolean_options=('--research-interval',))
            self.assertNotIn('--research-interval',command)
            self.assertIn('--pointwise-nearest',command)

    def test_wrong_sibling_origin_rejected_without_running_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'scripts').mkdir()
            (root/'scripts/helper.py').write_text('VALUE=1\n')
            (root/'scripts/tiny.py').write_text('def main(a, *, emit):\n raise AssertionError("must not run")\n')
            receipt=root/'admission.json'
            receipt.write_text(json.dumps({'invocation':{'command':[sys.executable,'/old/scripts/tiny.py','--out','/old/out']}}))
            with patch.dict(sys.modules,{'helper':SimpleNamespace(__file__=str(root/'wrong.py'))}):
                with self.assertRaisesRegex(ImportError,'outside the selected checkout'):
                    run_stage(receipt,root,root/'output')
            self.assertFalse((root/'output/stage-timing.json').exists())
            self.assertFalse((root/'output/candidate').exists())

    def test_api_failure_restores_interpreter_state_and_emits_no_success(self):
        for body, error in [('raise RuntimeError("bad input")',RuntimeError),('raise SystemExit(3)',RuntimeError)]:
            with self.subTest(body=body),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'scripts').mkdir()
                (root/'scripts/tiny.py').write_text(f'def main(a, *, emit):\n {body}\n')
                receipt=root/'admission.json'
                receipt.write_text(json.dumps({'invocation':{'command':[sys.executable,'/old/scripts/tiny.py','--out','/old/out']}}))
                before=(sys.path[:],sys.argv[:],sys.stdout,sys.stderr)
                with self.assertRaises(error):run_stage(receipt,root,root/'output')
                self.assertEqual((sys.path,sys.argv,sys.stdout,sys.stderr),before)
                self.assertFalse((root/'output/stage-timing.json').exists())

    def test_no_api_or_no_argument_api_is_not_run_as_a_cli(self):
        for text in ('VALUE=1\n','def main():\n raise AssertionError("not called")\n'):
            with self.subTest(text=text),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'scripts').mkdir();(root/'scripts/tiny.py').write_text(text)
                receipt=root/'admission.json'
                receipt.write_text(json.dumps({'invocation':{'command':[sys.executable,'/old/scripts/tiny.py','--out','/old/out']}}))
                with self.assertRaises(TypeError):run_stage(receipt,root,root/'output')
                self.assertFalse((root/'output/stage-timing.json').exists())

    def test_changed_entrypoint_has_no_success_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'scripts').mkdir()
            (root/'scripts/tiny.py').write_text('from pathlib import Path\ndef main(a, *, emit):\n Path(__file__).write_text("changed")\n')
            receipt=root/'admission.json'
            receipt.write_text(json.dumps({'invocation':{'command':[sys.executable,'/old/scripts/tiny.py','--out','/old/out']}}))
            with self.assertRaisesRegex(ValueError,'entrypoint changed'):run_stage(receipt,root,root/'output')
            self.assertFalse((root/'output/stage-timing.json').exists())

    def test_command_cannot_escape_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'scripts').mkdir();(root/'outside.py').write_text('')
            admission={'invocation':{'command':[sys.executable,'/old/scripts/../outside.py','--out','old']}}
            with self.assertRaisesRegex(ValueError,'missing stage script'):
                stage_command(admission,root,root/'new')


if __name__ == '__main__':
    unittest.main()
