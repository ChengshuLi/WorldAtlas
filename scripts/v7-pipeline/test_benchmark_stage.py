import json
from pathlib import Path
import sys
import tempfile
import unittest

from benchmark_stage import run_stage, stage_command


class BenchmarkStage(unittest.TestCase):
    def test_complete_stage_preserves_inputs_and_interpreter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'scripts').mkdir()
            script = root / 'scripts' / 'tiny.py'
            script.write_text('import pathlib,sys\na=sys.argv\npathlib.Path(a[a.index("--out")+1]).mkdir()\nprint("finished")\n')
            admitted = {'invocation': {'command': [sys.executable, '/old/scripts/tiny.py', '--input', '/immutable/input', '--out', '/old/output']}}
            receipt = root / 'admitted.json'
            receipt.write_text(json.dumps(admitted))
            report = run_stage(receipt, root, root / 'benchmark')
            self.assertEqual(report['command'][0], sys.executable)
            self.assertEqual(report['command'][2:4], ['--input', '/immutable/input'])
            self.assertGreater(report['process_wall_seconds'], 0)
            self.assertEqual((root / 'benchmark/builder.log').read_text(), 'finished\n')
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


if __name__ == '__main__':
    unittest.main()
