import json
from pathlib import Path
import tempfile
import unittest

from benchmark_land import compare_land


class LandComparisonTests(unittest.TestCase):
    def make_run(self, root):
        for stage in ('components', 'stage2-provisional-only', 'land'):
            directory = root / stage;directory.mkdir(parents=True)
            for name in ('rows.u32le', 'runs.u32le'):
                (directory / name).write_bytes(b'\x01\x00\x00\x00')
        report = {'ties': [], 'certified_components': 4, 'exact_search_components': 2,
                  'exact_queries': 7}
        (root / 'stage2-provisional-only/report.json').write_text(json.dumps(report))

    def test_all_streams_are_compared_and_changed_output_fails(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / 'a', Path(td) / 'b'
            self.make_run(a);self.make_run(b)
            result = compare_land(a, b)
            self.assertEqual(len(result['streams']), 3)
            self.assertEqual(result['exact_queries'], 7)
            (b / 'land/runs.u32le').write_bytes(b'different')
            with self.assertRaisesRegex(ValueError, 'land/runs.u32le differs'):
                compare_land(a, b)

    def test_ties_are_checked_independently(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / 'a', Path(td) / 'b'
            self.make_run(a);self.make_run(b)
            path = b / 'stage2-provisional-only/report.json'
            report = json.loads(path.read_text());report['ties'] = [{'position': 1}]
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, 'tie decisions differ'):
                compare_land(a, b)


if __name__ == '__main__':
    unittest.main()
