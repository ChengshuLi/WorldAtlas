"""Complete SeaVoX replay comparison rejects source, index and feature drift."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import benchmark_seavox as mod


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.reference, self.candidate = self.root / 'reference', self.root / 'candidate'
        self.reference.mkdir()
        self.candidate.mkdir()
        archive = self.write(self.root / 'archive', {'archive': 'fixture'})
        self.geometry_sha = 'a' * 64
        policy = self.write(self.root / 'policy.json', {'basins': [
            {'id': 'sea', 'source_feature_id': '123', 'geometry_sha256': self.geometry_sha}]})
        self.policy_sha, self.archive_sha = mod.digest(policy), mod.digest(archive)
        self.write(self.reference / 'request.json', {'sources': {
            'seavox_archive': {'path': str(archive), 'sha256': self.archive_sha},
            'water_snapshot': {'path': str(policy), 'sha256': self.policy_sha}}})
        self.write(self.reference / 'timing-events.jsonl', {'event': 'complete', 'id': 'water/extract-sea',
            'start_monotonic_seconds': 10, 'monotonic_seconds': 40})
        manifest = {'schema': 'worldatlas-seavox-archive-extraction-v1', 'decision_id': 'sea',
            'source_feature_id': '123', 'geometry_sha256': self.geometry_sha,
            'decision_snapshot_sha256': self.policy_sha, 'archive_sha256': self.archive_sha,
            'feature_file': 'source.geojson', 'gdal_version': 'GDAL fixture', 'processing_elapsed_seconds': 42}
        outputs = []
        for folder in (self.reference / 'extractions/sea', self.candidate / 'sea'):
            feature = self.write(folder / 'source.geojson', {'type': 'FeatureCollection', 'features': []})
            manifest['feature_file_sha256'] = mod.digest(feature)
            path = self.write(folder / 'manifest.json', manifest)
            if folder.is_relative_to(self.reference):
                outputs = [{'path': str(file), 'sha256': mod.digest(file)} for file in (feature, path)]
            else:
                self.entry = {'decision_id': 'sea', 'source_feature_id': '123', 'geometry_sha256': self.geometry_sha,
                    'feature_file': 'sea/source.geojson', 'feature_file_sha256': mod.digest(feature),
                    'manifest_file': 'sea/manifest.json', 'manifest_file_sha256': mod.digest(path)}
        self.write(self.reference / 'checkpoints/extract-sea/complete.json', {
            'schema': 'worldatlas-command-checkpoint-v1', 'outputs': outputs})
        self.index = {'schema': 'worldatlas-seavox-batch-extraction-v1',
            'status': 'completed_unverified_candidate_not_published', 'archive_sha256': self.archive_sha,
            'decision_snapshot_sha256': self.policy_sha, 'decision_count': 1, 'feature_count': 1,
            'gdal_version': 'GDAL fixture', 'features': [self.entry]}
        self.save_index()

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) + '\n')
        return path

    def save_index(self):
        self.write(self.candidate / 'batch-manifest.json', self.index)

    def test_exact_comparison_ignores_only_elapsed_time(self):
        path = self.candidate / 'sea/manifest.json'
        manifest = mod.read(path)
        manifest['processing_elapsed_seconds'] = .01
        self.write(path, manifest)
        self.entry['manifest_file_sha256'] = mod.digest(path)
        self.save_index()
        result = mod.compare_extractions(self.reference, self.candidate)
        self.assertEqual(result['decision_count'], 1)
        self.assertEqual(result['reference_summed_command_seconds'], 30)
        self.assertEqual(result['status'], 'all-selected-feature-bytes-and-provenance-identical')

    def test_index_paths_and_identity_are_bound(self):
        for key, value in [('feature_file', '../source.geojson'), ('geometry_sha256', 'b' * 64),
                           ('source_feature_id', '999')]:
            before = copy.deepcopy(self.index)
            with self.subTest(key=key):
                self.index['features'][0][key] = value
                self.save_index()
                with self.assertRaisesRegex(ValueError, 'index path|index identity'):
                    mod.compare_extractions(self.reference, self.candidate)
            self.index = before

    def test_modified_feature_fails_even_with_a_new_index_pin(self):
        feature = self.candidate / 'sea/source.geojson'
        self.write(feature, {'modified': 'feature'})
        self.entry['feature_file_sha256'] = mod.digest(feature)
        self.save_index()
        with self.assertRaisesRegex(ValueError, 'feature bytes differ'):
            mod.compare_extractions(self.reference, self.candidate)

    def test_reference_checkpoint_and_source_pins_are_required(self):
        feature = self.reference / 'extractions/sea/source.geojson'
        original = feature.read_bytes()
        feature.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'differs from checkpoint'):
            mod.compare_extractions(self.reference, self.candidate)
        feature.write_bytes(original)
        (self.root / 'archive').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'input pin mismatch'):
            mod.compare_extractions(self.reference, self.candidate)

    def test_missing_reference_duration_fails(self):
        (self.reference / 'timing-events.jsonl').write_text('')
        with self.assertRaisesRegex(ValueError, 'timing inventory is incomplete'):
            mod.compare_extractions(self.reference, self.candidate)

    def test_relative_sources_resolve_at_original_configuration(self):
        request_path = self.reference / 'request.json'
        request = mod.read(request_path)
        for spec in request['sources'].values():
            spec['path'] = Path(spec['path']).name
        self.write(request_path, request)
        self.write(self.reference / 'run-identity.json', {'request': {'path': str(self.root / 'original-config.json')}})
        self.assertEqual(mod.compare_extractions(self.reference, self.candidate)['decision_count'], 1)


if __name__ == '__main__':
    unittest.main()
