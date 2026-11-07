"""Batch extraction keeps the single-feature bytes, bindings and failure gates."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import extract_seavox_feature as single
import extract_seavox_features as batch


class BatchExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / 'source.zip'
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for ext in ('.shp', '.shx', '.dbf', '.prj'):
                archive.writestr('sea' + ext, b'fixture')
        self.features = {ident: {'type': 'Feature', 'id': n, 'properties': {'MRGID_SR': ident},
            'geometry': {'type': 'Polygon', 'coordinates': [[[n, 0], [n + .5, 0], [n, .5], [n, 0]]]}}
            for n, ident in enumerate(('24063', '24064'))}
        self.snapshot = {'schema': 'worldatlas-geography-decision-export-v1', 'source': 'neon-export',
            'decision_revision': {'id': 'r1', 'entity_revision': 'e1', 'status': 'accepted'},
            'entity_revision': {'id': 'e1', 'status': 'accepted'},
            'sources': [{'source_id': 'sea', 'version': 'v19', 'sha256': single.digest(self.archive)}],
            'basins': [{'id': 'sea-' + ident, 'source_id': 'sea', 'source_version': 'v19',
                'source_feature_id': ident, 'geometry_sha256': single.canonical_hash(feature['geometry'])}
                for ident, feature in self.features.items()]}
        self.policy = self.root / 'policy.json'
        self.out = self.root / 'batch'

    def save_policy(self):
        self.policy.write_text(json.dumps(self.snapshot))
        return single.digest(self.policy)

    def run_batch(self, **kwargs):
        policy_sha = self.save_policy()
        with patch.object(batch, 'extract_features', return_value=self.features) as extract, \
                patch.object(batch.subprocess, 'run') as run:
            run.return_value.stdout = 'GDAL test'
            result = batch.run(self.archive, self.root, self.policy, policy_sha, self.out,
                               allow_unverified=True, **kwargs)
        extract.assert_called_once()
        return result

    def test_exact_files_and_original_manifest_contract(self):
        index = self.run_batch()
        self.assertEqual(index['decision_count'], 2)
        self.assertEqual(index['feature_count'], 2)
        self.assertEqual(index['archive_sha256'], single.digest(self.archive))
        for entry in index['features']:
            basin = next(b for b in self.snapshot['basins'] if b['id'] == entry['decision_id'])
            feature = self.features[entry['source_feature_id']]
            expected_dir = self.root / ('single-' + entry['decision_id'])
            expected = single.write_extraction(expected_dir, feature, self.snapshot,
                single.digest(self.policy), basin, self.snapshot['sources'][0], 'GDAL test')
            actual = json.loads((self.out / entry['manifest_file']).read_text())
            self.assertGreaterEqual(actual.pop('processing_elapsed_seconds'), 0)
            self.assertEqual(actual, expected)
            self.assertEqual((self.out / entry['feature_file']).read_bytes(),
                             (expected_dir / 'source.geojson').read_bytes())
            self.assertEqual(entry['manifest_file_sha256'], single.digest(self.out / entry['manifest_file']))
            self.assertEqual(entry['feature_file_sha256'], single.digest(self.out / entry['feature_file']))
        self.assertEqual(json.loads((self.out / 'batch-manifest.json').read_text()), index)
        with self.assertRaises(FileExistsError):
            self.run_batch()

    def test_different_decisions_can_bind_one_identical_feature(self):
        second = copy.deepcopy(self.snapshot['basins'][0])
        second['id'] = 'another-sea'
        self.snapshot['basins'][1] = second
        self.features.pop('24064')
        result = self.run_batch()
        self.assertEqual((result['decision_count'], result['feature_count']), (2, 1))
        self.assertEqual(result['features'][0]['feature_file_sha256'], result['features'][1]['feature_file_sha256'])

    def test_selection_order_is_deterministic(self):
        self.snapshot['basins'].reverse()
        result = self.run_batch()
        self.assertEqual([item['decision_id'] for item in result['features']], ['sea-24063', 'sea-24064'])

    def test_bad_bindings_fail_before_output(self):
        for key, value, message in [('id', '../unsafe', 'unique and safe'),
                                    ('source_feature_id', "1' OR 1=1", 'digits only'),
                                    ('geometry_sha256', '0' * 64, 'does not match')]:
            original = copy.deepcopy(self.snapshot)
            with self.subTest(key=key):
                self.snapshot['basins'][0][key] = value
                with self.assertRaisesRegex(ValueError, message):
                    self.run_batch()
                self.assertFalse(self.out.exists())
            self.snapshot = original

    def test_duplicate_decisions_and_multiple_archives_are_rejected(self):
        self.snapshot['basins'][1]['id'] = self.snapshot['basins'][0]['id']
        with self.assertRaisesRegex(ValueError, 'unique and safe'):
            self.run_batch()
        self.snapshot['basins'][1]['id'] = 'other'
        self.snapshot['sources'].append({'source_id': 'other', 'version': 'v19', 'sha256': '0' * 64})
        self.snapshot['basins'][1]['source_id'] = 'other'
        with self.assertRaisesRegex(ValueError, 'one nonempty pinned archive'):
            self.run_batch()
        self.assertFalse(self.out.exists())

    def test_archive_or_policy_mutation_prevents_completion(self):
        policy_sha = self.save_policy()
        def mutate(*args, **kwargs):
            self.archive.write_bytes(self.archive.read_bytes() + b'changed')
            return self.features
        with patch.object(batch, 'extract_features', side_effect=mutate), \
                patch.object(batch.subprocess, 'run') as run:
            run.return_value.stdout = 'GDAL test'
            with self.assertRaisesRegex(ValueError, 'changed during extraction'):
                batch.run(self.archive, self.root, self.policy, policy_sha, self.out, allow_unverified=True)
        self.assertFalse(self.out.exists())

    def test_explicit_snapshot_optin_is_required(self):
        policy_sha = self.save_policy()
        with self.assertRaisesRegex(ValueError, 'explicit test-only'):
            batch.run(self.archive, self.root, self.policy, policy_sha, self.out)

    def test_materialization_is_workspace_local_and_transient(self):
        work = self.root / 'work'
        work.mkdir()
        policy_sha = self.save_policy()
        def extract(archive, ids, *, dataset):
            self.assertTrue(dataset.is_relative_to(work))
            self.assertEqual(dataset.read_bytes(), b'fixture')
            self.assertTrue(dataset.with_suffix('.prj').is_file())
            return self.features
        with patch.object(batch, 'extract_features', side_effect=extract), \
                patch.object(batch.subprocess, 'run') as run:
            run.return_value.stdout = 'GDAL test'
            result = batch.run(self.archive, self.root, self.policy, policy_sha, self.out,
                               allow_unverified=True, work_root=work)
        self.assertEqual(list(work.iterdir()), [])
        self.assertIn('archive_materialization', result['processing_stages_seconds'])


class OgrBatchTests(unittest.TestCase):
    def test_filter_and_exact_inventory(self):
        features = [{'type': 'Feature', 'properties': {'mrgid_sr': ident},
            'geometry': {'type': 'Polygon', 'coordinates': []}} for ident in ('2', '10')]
        with patch.object(single.subprocess, 'run') as run:
            run.return_value.stdout = json.dumps({'type': 'FeatureCollection', 'features': features})
            result = single.extract_features(Path('source.zip'), ['10', '2'])
            self.assertEqual(set(result), {'2', '10'})
            self.assertIn("mrgid_sr IN ('2','10')", run.call_args.args[0])
            for invalid in (features[:1], [*features, features[0]], [*features, {
                    **features[0], 'properties': {'mrgid_sr': '999'}}]):
                run.return_value.stdout = json.dumps({'type': 'FeatureCollection', 'features': invalid})
                with self.assertRaisesRegex(ValueError, 'exactly one matching'):
                    single.extract_features(Path('source.zip'), ['2', '10'])

    @unittest.skipUnless(shutil.which('ogr2ogr'), 'GDAL ogr2ogr is required')
    def test_real_archive_batch_is_byte_identical_to_individual_extractions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'source.geojson'
            source.write_text(json.dumps({'type': 'FeatureCollection', 'features': [
                {'type': 'Feature', 'properties': {'MRGID_SR': ident, 'name': 'Sea ' + ident},
                 'geometry': {'type': 'Polygon', 'coordinates': [[[n, 0], [n + .123456789012345, 0],
                                                               [n, 1], [n, 0]]]}}
                for n, ident in enumerate(('24063', '24064', '24065'))]}))
            shape = root / 'shape'
            subprocess.run(['ogr2ogr', '-f', 'ESRI Shapefile', str(shape), str(source)],
                           check=True, capture_output=True)
            archive = root / 'sea.zip'
            with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
                for component in shape.iterdir():
                    zipped.write(component, component.name)
            selected = single.extract_features(archive, ['24063', '24065'])
            for ident in selected:
                individual = single.extract_feature(archive, ident)
                self.assertEqual(single.canonical_hash(selected[ident]), single.canonical_hash(individual))
                self.assertEqual(json.dumps(selected[ident], sort_keys=True), json.dumps(individual, sort_keys=True))


if __name__ == '__main__':
    unittest.main()
