"""The producer accepts large valid inputs without relaxing their checks."""
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'seed-producer'))
sys.path.insert(0, str(HERE / 'hint-producer'))
import build_stage2
import export_adapter
import region_client
import regions
import seed_producer
import seed_rules
import run_diagnostic


class UncappedProducerTest(unittest.TestCase):
    def test_large_pinned_json_and_snapshot_still_check_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'snapshot.json'
            raw = b'{"ok":true}' + b' ' * ((16 << 20) + 1)
            path.write_bytes(raw)
            pin = {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}
            ticks = []
            guard = lambda: ticks.append(1)
            self.assertEqual(seed_producer.bounded_json(pin, guard), {'ok': True})
            self.assertEqual(export_adapter.load_pinned_snapshot(path, pin['sha256'], guard), {'ok': True})
            self.assertEqual(build_stage2.read_json(path, guard), {'ok': True})
            self.assertEqual(json.loads(run_diagnostic.read_bytes(path)), {'ok': True})
            self.assertGreater(len(ticks), 16)
            path.write_bytes(raw + b' ')
            with self.assertRaisesRegex(ValueError, 'pin mismatch'):
                export_adapter.load_pinned_snapshot(path, pin['sha256'], guard)
            with self.assertRaisesRegex(ValueError, 'pin mismatch'):
                seed_producer.bounded_json(pin, guard)

    def test_representative_bound_is_geometry_derived_above_128_mib(self):
        tiles = 35000
        expected = tiles * 6 * 32 * 20
        self.assertGreater(expected, 128 << 20)
        self.assertEqual(build_stage2.representative_byte_limit(tiles), expected)
        self.assertEqual(run_diagnostic.representative_byte_limit(tiles), expected)

    def test_large_region_code_and_request_are_still_pinned(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            code = root / 'code'; code.mkdir()
            work = root / 'work'; work.mkdir()
            source = root / 'inputs'; source.mkdir()
            for name in region_client.CODE:
                (code / name).write_bytes(b'#' * ((1 << 20) + 1))
            request = {'closure': {'checker_path': str(source / 'checker'),
                                   'contract_path': str(source / 'contract'),
                                   'physical_dir': str(source)},
                       'padding': 'x' * ((16 << 20) + 1)}
            response = {'schema': 'stage2-region-worker-result-v1',
                        'status': 'selected-research-region'}
            with mock.patch.object(region_client, 'BASE', code), mock.patch('runpy.run_path', return_value={'execute': lambda req, guard: dict(response)}):
                result = region_client.execute(request, work, lambda: None)
                self.assertEqual(result['code_sha256']['region_worker.py'], hashlib.sha256((code / 'region_worker.py').read_bytes()).hexdigest())
                def mutate(req, guard):
                    (code / 'region_worker.py').write_text('changed')
                    return dict(response)
                with mock.patch('runpy.run_path', return_value={'execute': mutate}):
                    with self.assertRaisesRegex(ValueError, 'code changed'):
                        region_client.execute(request, work, lambda: None)

    def test_large_line_retains_coordinate_validation(self):
        coords = [[i / 1000000, 0] for i in range(200001)]
        self.assertEqual(len(regions.points({'type': 'LineString', 'coordinates': coords})), len(coords))
        coords[-1] = coords[-2]
        with self.assertRaisesRegex(ValueError, 'duplicate consecutive'):
            regions.points({'type': 'LineString', 'coordinates': coords})

    def test_large_decision_list_still_checks_unique_ids(self):
        values = [{'id': str(i)} for i in range(10001)]
        self.assertEqual(len(seed_rules.unique(values, 'id')), len(values))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            seed_rules.unique(values + [values[0]], 'id')


if __name__ == '__main__':
    unittest.main()
