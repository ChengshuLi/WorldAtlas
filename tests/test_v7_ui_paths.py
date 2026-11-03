import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path

BUILDER = Path(__file__).parents[1] / 'scripts' / 'build_full_v7_ui_bundle.py'

class BuilderPathsTest(unittest.TestCase):
    def test_explicit_roots_resolve_all_paths_without_building(self):
        code = '''import importlib.util, json
s = importlib.util.spec_from_file_location("builder", __import__("sys").argv[1]); b = importlib.util.module_from_spec(s); s.loader.exec_module(b)
print(json.dumps({k: str(getattr(b, k)) for k in ("ROOT", "TMP_ROOT", "OUTPUT_ROOT", "OLD", "V6ROWS", "V6RUNS", "V2Y", "INDEX_DIR")}))'''
        env = dict(os.environ, WORLDATLAS_WORK_ROOT='/example/work', WORLDATLAS_TMP_ROOT='/example/inputs', WORLDATLAS_OUTPUT_ROOT='/example/output', PYTHONDONTWRITEBYTECODE='1')
        import json
        paths = json.loads(subprocess.check_output([sys.executable, '-c', code, str(BUILDER)], env=env, text=True))
        self.assertEqual(paths['ROOT'], '/example/work')
        self.assertEqual(paths['TMP_ROOT'], '/example/inputs')
        self.assertEqual(paths['OUTPUT_ROOT'], '/example/output')
        self.assertEqual(paths['OLD'], '/example/inputs/v7-bay-ocean-stage-20261103/index-v7-stage')
        for name in ('V6ROWS', 'V6RUNS'):
            self.assertTrue(paths[name].startswith('/example/inputs/v6-aegean-final-publication-20261103/'))
        for name in ('V2Y', 'INDEX_DIR'):
            self.assertTrue(paths[name].startswith('/example/work/'))

if __name__ == '__main__':
    unittest.main()
