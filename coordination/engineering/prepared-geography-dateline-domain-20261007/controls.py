"""Small directed production guard controls, with actual immutable CLI execution."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

CASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('owned_producer', CASE / 'producer.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
COMMIT = None

class Controls(unittest.TestCase):
    def test_selectors_rejected_before_git(self):
        for value in ['main', 'a'*39, 'A'*40, '--output=x', None]:
            with self.subTest(value=value), patch.object(p, 'read_git', side_effect=AssertionError('Git called')):
                with self.assertRaisesRegex(ValueError, 'immutable lowercase'):
                    p.authenticate(value)

    def test_actual_executed_byte_mutation(self):
        original=p.read_git
        def changed(commit,path):
            raw=original(commit,path)
            return raw+b'\n# changed actual binding' if path=='scripts/evidence/geometry.py' else raw
        with patch.object(p,'read_git',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'Actual execution bytes differ'):
                p.authenticate(COMMIT)

    def test_runtime_mutation(self):
        with patch.object(p,'PINNED',dict(p.PINNED,geos='unknown')):
            with self.assertRaisesRegex(ValueError,'runtime mismatch'):
                p.authenticate(COMMIT)

    def test_output_guard_before_inputs(self):
        values=['relative',str(p.ROOT/'.cache/1293'),str(p.ROOT/'.cache/1293/../outside'),str(p.ROOT/'outside')]
        with patch.object(p,'authenticate',return_value=({},[],{},None)),patch.object(p,'Baseline',side_effect=AssertionError('inputs called')):
            for value in values:
                with self.subTest(value=value),self.assertRaises(ValueError):p.run(COMMIT,value)

    def test_retained_symlink_and_missing(self):
        scratch=CASE/'.cache';scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            target=Path(folder)/'alias';target.symlink_to(CASE/'config.json')
            pin={'path':str(target.relative_to(p.ROOT)),'bytes':0,'sha256':'0'*64}
            with self.assertRaisesRegex(ValueError,'symlink'):p.checked_retained(pin)
            target.unlink()
            with self.assertRaises(FileNotFoundError):p.checked_retained(pin)

    def test_actual_cli_no_write(self):
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch) / 'not-created'
            for value in ['main', 'A'*40, 'a'*39]:
                result = subprocess.run([sys.executable, '-B', str(CASE/'producer.py'), '--code-commit', value, '--out', str(target)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('immutable lowercase', result.stderr)
                self.assertFalse(target.exists())

    def test_actual_frozen_authentication(self):
        command = "import importlib.util,sys; s=importlib.util.spec_from_file_location('actual_producer',sys.argv[1]); m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m); c,p,r,d=m.authenticate(sys.argv[2]);print(len(p))"
        result = subprocess.run([sys.executable, '-B', '-c', command, str(CASE/'producer.py'), COMMIT], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '6')

    def test_whole_failed_middle_retention(self):
        from shapely.geometry import box, mapping
        features = [{'type':'Feature','id':x,'properties':{},'geometry':g} for x,g in [('first',mapping(box(1,1,2,2))),('missing',None),('last',mapping(box(3,3,4,4)))]]
        rows = [p.validate_feature(f,'whole-source.geojson',i) for i,f in enumerate(features)]
        self.assertEqual([r['id'] for r in rows], ['first','missing','last'])
        self.assertEqual([r['prepared']['status'] for r in rows], ['valid','unsupported-or-invalid','valid'])
        self.assertIsNone(rows[1]['prepared']['original_geometry'])
        self.assertNotIn('canonical_geometry_sha256', rows[1]['prepared'])

    def test_retained_byte_and_path_guards(self):
        config = json.loads((CASE/'config.json').read_bytes())
        pin = config['retained_fji']
        self.assertEqual(len(p.checked_retained(pin)), pin['uncompressed_bytes'])
        for mutation in [dict(pin, sha256='0'*64),dict(pin, uncompressed_sha256='0'*64),dict(pin, path='../outside'),dict(pin,path='docs/AGENTS.md')]:
            with self.subTest(mutation=mutation), self.assertRaises((ValueError,FileNotFoundError)):
                p.checked_retained(mutation)

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--code-commit',required=True)
    args=parser.parse_args();COMMIT=args.code_commit
    unittest.main(argv=[sys.argv[0]])
