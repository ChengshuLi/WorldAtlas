import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import benchmark_seavox_coordinates as b


class BatchParityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='seavox-parity-test-', dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.reference, self.candidate = self.root / 'reference', self.root / 'candidate'
        self.geometry_sha = 'a' * 64
        self.archive_sha = 'b' * 64
        self.policy = self.write(self.root / 'policy.json', {'basins': [
            {'id': 'sea', 'source_feature_id': '123', 'geometry_sha256': self.geometry_sha}]})
        self.policy_sha = b.digest(self.policy)
        feature = self.write(self.reference / 'sea/source.geojson', {'type': 'FeatureCollection', 'features': []})
        manifest = self.write(self.reference / 'sea/manifest.json', {
            'schema': 'worldatlas-seavox-archive-extraction-v1', 'decision_id': 'sea',
            'source_feature_id': '123', 'gdal_version': 'synthetic-gdal',
            'geometry_sha256': self.geometry_sha, 'archive_sha256': self.archive_sha,
            'decision_snapshot_sha256': self.policy_sha, 'feature_file_sha256': b.digest(feature),
            'processing_elapsed_seconds': 1})
        self.index = {'schema': 'worldatlas-seavox-batch-extraction-v1',
            'status': 'completed_unverified_candidate_not_published',
            'archive_sha256': self.archive_sha, 'decision_snapshot_sha256': self.policy_sha,
            'gdal_version': 'synthetic-gdal',
            'decision_count': 1, 'feature_count': 1, 'features': [{'decision_id': 'sea',
                'source_feature_id': '123', 'geometry_sha256': self.geometry_sha,
                'feature_file': 'sea/source.geojson', 'feature_file_sha256': b.digest(feature),
                'manifest_file': 'sea/manifest.json', 'manifest_file_sha256': b.digest(manifest)}]}
        self.write(self.reference / 'batch-manifest.json', self.index)
        shutil.copytree(self.reference, self.candidate)

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) + '\n')
        return path

    def compare(self):
        return b.compare_batches(self.reference, self.candidate, self.policy, self.policy_sha, self.archive_sha)

    def test_exact_batches_ignore_only_elapsed_time(self):
        receipt = self.candidate / 'sea/manifest.json'
        manifest = b.read(receipt)
        manifest['processing_elapsed_seconds'] = .01
        self.write(receipt, manifest)
        index = copy.deepcopy(self.index)
        index['features'][0]['manifest_file_sha256'] = b.digest(receipt)
        self.write(self.candidate / 'batch-manifest.json', index)
        self.assertEqual(self.compare()['decision_count'], 1)

    def test_modified_feature_with_rebound_index_still_fails(self):
        feature = self.write(self.candidate / 'sea/source.geojson', {'modified': True})
        manifest = b.read(self.candidate / 'sea/manifest.json')
        manifest['feature_file_sha256'] = b.digest(feature)
        receipt = self.write(self.candidate / 'sea/manifest.json', manifest)
        index = copy.deepcopy(self.index)
        index['features'][0].update(feature_file_sha256=b.digest(feature), manifest_file_sha256=b.digest(receipt))
        self.write(self.candidate / 'batch-manifest.json', index)
        with self.assertRaisesRegex(ValueError, 'reference/candidate'):
            self.compare()

    def test_index_path_and_geometry_drift_fail(self):
        for key, value in [('feature_file', '../private'), ('geometry_sha256', 'c' * 64)]:
            index = copy.deepcopy(self.index)
            index['features'][0][key] = value
            self.write(self.candidate / 'batch-manifest.json', index)
            with self.assertRaisesRegex(ValueError, 'identity/path'):
                self.compare()

    def test_missing_decision_and_changed_policy_fail(self):
        index = copy.deepcopy(self.index)
        index['features'] = []
        self.write(self.candidate / 'batch-manifest.json', index)
        with self.assertRaisesRegex(ValueError, 'complete selected batch'):
            self.compare()
        self.write(self.policy, {'basins': []})
        with self.assertRaisesRegex(ValueError, 'policy pin'):
            self.compare()

    def test_complete_harness_calls_both_modes_in_process_with_local_scratch(self):
        archive = self.root / 'archive.zip'
        archive.write_bytes(b'pinned archive fixture')
        repo = Path(__file__).resolve().parents[2]
        names = ('extract_seavox_features', 'extract_seavox_feature', 'decision_snapshot', 'seavox_properties',
                 'seavox_coordinates')
        modules = {name: SimpleNamespace(__file__=str(repo / 'scripts/v7-replay' / (name + '.py')))
                   for name in names}
        out = self.root / 'paired'
        def produce(*args, **kwargs):
            self.assertEqual(os.environ['TMPDIR'], str(out / 'scratch'))
            self.assertEqual(kwargs['work_root'], out / 'scratch')
            return {'synthetic': 'producer'}
        modules['extract_seavox_features'].run = Mock(side_effect=produce)
        with patch.object(b.importlib, 'import_module', return_value=modules['extract_seavox_features']), \
             patch.dict(b.sys.modules, modules), patch.object(b, 'compare_batches', return_value={'status': 'exact'}):
            result = b.benchmark(archive, b.digest(archive), self.root, self.policy,
                                 self.policy_sha, out, repo)
        calls = modules['extract_seavox_features'].run.call_args_list
        self.assertEqual([call.kwargs['scalar_coordinates'] for call in calls], [True, False])
        self.assertEqual(set(result['timings']), {'scalar-reference', 'arrow-candidate'})
        for timing in result['timings'].values():
            self.assertTrue(timing['started_at_utc'].endswith('+00:00'))
            self.assertGreaterEqual(timing['ended_at_utc'], timing['started_at_utc'])

    def test_cached_converter_outside_selected_checkout_prevents_report(self):
        archive = self.root / 'archive.zip'
        archive.write_bytes(b'pinned archive fixture')
        repo = Path(__file__).resolve().parents[2]
        names = ('extract_seavox_features', 'extract_seavox_feature', 'decision_snapshot', 'seavox_properties',
                 'seavox_coordinates')
        modules = {name: SimpleNamespace(__file__=str(repo / 'scripts/v7-replay' / (name + '.py')))
                   for name in names}
        modules['seavox_coordinates'].__file__ = str(self.root / 'other-checkout/seavox_coordinates.py')
        modules['extract_seavox_features'].run = Mock(return_value={'synthetic': 'producer'})
        out = self.root / 'wrong-cached-module'
        with patch.object(b.importlib, 'import_module', return_value=modules['extract_seavox_features']), \
             patch.dict(b.sys.modules, modules), patch.object(b, 'compare_batches', return_value={'status': 'exact'}):
            with self.assertRaisesRegex(ValueError, 'outside.*seavox_coordinates'):
                b.benchmark(archive, b.digest(archive), self.root, self.policy, self.policy_sha, out, repo)
        self.assertFalse((out / 'report.json').exists())


if __name__ == '__main__':
    unittest.main()
