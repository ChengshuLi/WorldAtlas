import gzip
import json
from pathlib import Path
import tempfile
import unittest

from benchmark_coastal import compare_batches, digest


class CoastalComparisonTest(unittest.TestCase):
    def fixture(self, root, record=b'{"row":0,"spans":[{"start":0,"end":2,"code":1}]}\n'):
        tile = root / 'tile-0000'
        tile.mkdir(parents=True)
        spans = tile / 'coastal-assignments.jsonl.gz'
        spans.write_bytes(gzip.compress(record))
        manifest = {'schema': 'worldatlas-coastal-tile-candidate-v1',
                    'status': 'partial-unverified-research-not-published',
                    'core_cols': [0, 2], 'core_rows': [0, 1], 'physical_water_cells': 2,
                    'assigned_cells': 2, 'span_count': 1, 'coastal_centers': 1,
                    'span_file': {'path': spans.name, 'sha256': digest(spans)}}
        (tile / 'manifest.json').write_text(json.dumps(manifest))
        complete = {'schema': 'worldatlas-sealed-coastal-batch-v1',
                    'status': 'complete-research-not-published', 'timing_complete': True,
                    'snapshot_sha256': 'a' * 64, 'plan_sha256': 'b' * 64,
                    'grid': {'width': 2, 'height': 1}, 'sealed_input_sha256': {}, 'metadata_sha256': {},
                    'tiles': [{'tile': 0, 'box': [0, 2, 0, 1],
                               'manifest_sha256': digest(tile / 'manifest.json')}]}
        (root / 'batch-complete.json').write_text(json.dumps(complete))

    def test_compare_all_bytes_and_fail_on_assignment_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root / 'reference')
            self.fixture(root / 'candidate')
            result = compare_batches(root / 'reference', root / 'candidate')
            self.assertEqual(result['tile_count'], 1)
            self.assertEqual(result['physical_water_cells'], 2)
            self.fixture(root / 'changed', b'{"row":0,"spans":[]}\n')
            with self.assertRaisesRegex(ValueError, 'assignment bytes differ'):
                compare_batches(root / 'reference', root / 'changed')
            complete = root / 'candidate/batch-complete.json'
            data = json.loads(complete.read_text())
            data['plan_sha256'] = 'c' * 64
            complete.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'input mismatch'):
                compare_batches(root / 'reference', root / 'candidate')

    def test_incomplete_or_mutated_artifacts_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root / 'reference')
            self.fixture(root / 'candidate')
            (root / 'candidate/tile-0000/manifest.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'manifest hash'):
                compare_batches(root / 'reference', root / 'candidate')


if __name__ == '__main__':
    unittest.main()
