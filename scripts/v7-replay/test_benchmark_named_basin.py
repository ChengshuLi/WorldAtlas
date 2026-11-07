import gzip
import json
from pathlib import Path
import tempfile
import unittest

from benchmark_named_basin import assignment_comparison


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


if __name__ == '__main__':
    unittest.main()
