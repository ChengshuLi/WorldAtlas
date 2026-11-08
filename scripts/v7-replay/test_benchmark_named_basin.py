import gzip
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from benchmark_named_basin import assignment_comparison
import benchmark_named_basin as benchmark


class BenchmarkBasin(unittest.TestCase):
    def test_every_span_compared_and_counts_not_trusted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {'row': 2, 'spans': [{'start': 3, 'end': 8, 'code': 2, 'rule_id': 'nearest', 'member_id': 'sea'}]}
            paths = [root / 'old.gz', root / 'new.gz']
            for path in paths:
                with gzip.open(path, 'wt') as stream:
                    stream.write(json.dumps(row) + '\n')
            result = assignment_comparison(*paths, 10, 5)
            self.assertEqual(result['cells'], 5)
            self.assertTrue(result['decompressed_bytes_equal'])
            row['spans'][0]['code'] = 1
            with gzip.open(paths[1], 'wt') as stream:
                stream.write(json.dumps(row) + '\n')
            with self.assertRaisesRegex(ValueError, 'assignment mismatch'):
                assignment_comparison(*paths, 10, 5)

    def test_verifier_is_called_as_python_api_and_log_is_new(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            root = Path(tmp); (root / 'verify_basin_coverage.py').write_text('# selected verifier\n')
            module = SimpleNamespace(__file__=str(root / 'verify_basin_coverage.py'))
            module.main = Mock(side_effect=lambda args, *, emit: emit(json.dumps({'status': 'exact'})))
            arguments = ['--manifest', 'candidate.json', '--allow-draft-snapshot']
            with patch.dict(benchmark.sys.modules, {'verify_basin_coverage': module}):
                benchmark.verify_coverage(root / 'build_seavox_basin.py', arguments, root / 'coverage.log')
                self.assertEqual(module.main.call_args.args, (arguments,))
                self.assertEqual(json.loads((root / 'coverage.log').read_text()), {'status': 'exact'})
                with self.assertRaises(FileExistsError):
                    benchmark.verify_coverage(root / 'build_seavox_basin.py', arguments, root / 'coverage.log')

    def test_wrong_cached_verifier_fails_before_creating_log(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
            root = Path(tmp); (root / 'verify_basin_coverage.py').write_text('# selected verifier\n')
            module = SimpleNamespace(__file__=str(root / 'wrong.py'), main=Mock())
            with patch.dict(benchmark.sys.modules, {'verify_basin_coverage': module}):
                with self.assertRaisesRegex(ImportError, 'outside the selected checkout'):
                    benchmark.verify_coverage(root / 'build_seavox_basin.py', [], root / 'coverage.log')
            self.assertFalse((root / 'coverage.log').exists())
            module.main.assert_not_called()


if __name__ == '__main__':
    unittest.main()
