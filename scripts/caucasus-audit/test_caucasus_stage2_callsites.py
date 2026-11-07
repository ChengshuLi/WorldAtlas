"""Bounded checks for the staged stage-2 call sites; no map build."""
import hashlib
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy, pyproj, scipy  # Keep runtime dependencies loaded across module stubs.

HERE = Path(__file__).resolve().parent
STAGE2 = HERE if (HERE / 'build_stage2.py').is_file() else HERE.parent / 'v7-land' / 'research-mixed-runtime' / 'stage2-geodesic-20261104'


class CallsiteTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        names = ('atomic_move', 'baseline_runner', 'checkpoints', 'engine', 'preflight',
                 'verify_inputs', 'verify_physical_lineage', 'witness_compare',
                 'build_seed_tiles', 'representatives', 'certificate', 'exact_index',
                 'write_land_stream')
        self.modules = {n: types.ModuleType(n) for n in names}
        self.modules['certificate'].CertificateIndex = object
        self.modules['exact_index'].ExactIndex = object
        self.modules['write_land_stream'].write_land_stream = lambda *a, **k: None
        verify = self.modules['verify_inputs']
        verify.sha_file = lambda p, guard: hashlib.sha256(Path(p).read_bytes()).hexdigest()
        verify.bounded_bytes = lambda p, limit, *args: Path(p).read_bytes()
        self.patch = patch.dict(sys.modules, self.modules)
        self.patch.start()
        spec = importlib.util.spec_from_file_location('test_build_stage2_source', STAGE2 / 'build_stage2.py')
        self.build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.build)
        self.build.CAUCASUS_DIR = HERE
        sys.modules['build_stage2'] = self.build

    def tearDown(self):
        sys.modules.pop('build_stage2', None)
        self.patch.stop()
        self.temp.cleanup()

    def config(self):
        config = {'code_sha256': {n: hashlib.sha256((HERE / n).read_bytes()).hexdigest()
                                  for n in self.build.CAUCASUS_CODE}}
        for name in ('recipe', 'hydro', 'author'):
            p = self.root / name
            p.write_text(name)
            config[name] = {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        return config

    def test_core_binding_loads_pinned_helper_and_rejects_changed_input(self):
        cfg = self.config()
        binding = self.build.caucasus_binding(cfg, lambda: None)
        self.assertEqual(binding.CODE, self.build.CAUCASUS_CODE)
        Path(cfg['recipe']['path']).write_text('changed')
        with self.assertRaisesRegex(ValueError, 'input hash mismatch'):
            self.build.caucasus_binding(cfg, lambda: None)

    def test_outer_config_rejects_handoff_and_source_combination(self):
        spec = importlib.util.spec_from_file_location('test_orchestrate_source', STAGE2 / 'orchestrate_stage2.py')
        outer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(outer)
        cfg = {'schema': 'stage2-fresh-orchestration-v1', 'grid': {},
               'inputs': {k: {} for k in outer.BASE_INPUTS}, 'policy_id': 'p', 'policy_version': 'v',
               'controls': {}, 'seed_controls': {'timeout_seconds': 1, 'strip_rows': 1, 'max_group_rss_kib': 262144},
               'hint_max_rss_kib': 1, 'caucasus_source': self.config()}
        path = self.root / 'config.json'
        path.write_text(json.dumps(cfg))
        with patch.object(self.build, 'validate_controls'):
            _, selected = outer.load_config(path)
            self.assertEqual(selected['caucasus_source'], cfg['caucasus_source'])
            cfg['seed_handoff'] = {}
            path.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(ValueError, 'invalid fresh orchestration'):
                outer.load_config(path)


if __name__ == '__main__':
    unittest.main()
