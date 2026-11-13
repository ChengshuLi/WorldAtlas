import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import psycopg

from worldatlas.source_imports.features.build_features import build_features
from worldatlas.source_imports.features.geometry import geometry_hash, save_features


@unittest.skipUnless(os.environ.get('WORLDATLAS_TEST_DATABASE_URL'), 'requires disposable PostgreSQL')
class StorageTests(unittest.TestCase):
    def setUp(self):
        self.database = psycopg.connect(os.environ['WORLDATLAS_TEST_DATABASE_URL'])
        self.addCleanup(self.database.close)
        self.addCleanup(self.database.rollback)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.database.execute("INSERT INTO atlas.entity_registry_revisions VALUES ('__feature_entities')")
        for revision in ('__features_a', '__features_b'):
            self.database.execute("INSERT INTO atlas.decision_revisions VALUES (%s,'__feature_entities','{}')", (revision,))
        self.recipe = dict(method='selected_vector_features', recipe_id='__features', recipe_version='1',
                           source_id='__feature_raw', source_version='1', basis='Selected provider points.',
                           id_field='provider_id', selections=[dict(feature_id='point-a', source_feature_id='a')])
        raw = json.dumps({'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'properties': {'provider_id': 'a'},
             'geometry': {'type': 'Point', 'coordinates': [10, 20]}}]}).encode()
        self.database.execute(
            'INSERT INTO atlas.source_assets '
            '(source_id,version,title,provider,source_uri,license_name,license_uri,'
            'attribution,r2_bucket,r2_key,sha256,size_bytes,provenance) '
            "VALUES ('__feature_raw','1','Test','Test','test:source','Test','test:license',"
            "'Test','test','source.geojson',%s,%s,'{}')", (hashlib.sha256(raw).hexdigest(), len(raw)))
        self.register('1')
        self.storage = Mock()
        self.storage.get_object.side_effect = lambda **_: {'Body': io.BytesIO(raw)}

    def register(self, version):
        self.recipe['recipe_version'] = version
        text = json.dumps(self.recipe, sort_keys=True, separators=(',', ':'))
        self.database.execute('INSERT INTO atlas.structured_documents VALUES (%s,%s,%s,%s,%s::json)',
                              ('__features', version, hashlib.sha256(text.encode()).hexdigest(), len(text), text))

    def build(self, version='1', revision='__features_a'):
        return build_features(self.database, self.storage, '__features', version, revision, self.work)

    def snapshot(self, revision='__features_a'):
        return self.database.execute('SELECT feature_id,geometry,coordinate_reference,geometry_sha256,evidence,construction_id,construction_version '
                                     'FROM atlas.decision_features WHERE revision=%s ORDER BY feature_id', (revision,)).fetchall()

    def test_build_cached_repeat_and_changed_construction_preserve_notes_and_links(self):
        first = self.build()
        self.build(revision='__features_b')
        other = self.snapshot('__features_b')
        self.database.execute("UPDATE atlas.decision_features SET evidence=evidence || '{\"note\":\"keep\"}' "
                              "WHERE revision='__features_a'")
        self.database.execute("INSERT INTO atlas.decision_basins VALUES "
                              "('__features_a','basin','point-a','test','{}','{}')")
        self.recipe['basis'] = 'Updated explanation.'
        self.register('2')
        self.build(version='2')
        after = self.snapshot()[0]
        self.assertEqual(after[2], 'OGC:CRS84')
        self.assertEqual(after[3], geometry_hash(after[1]))
        self.assertEqual(after[4]['note'], 'keep')
        self.assertEqual(after[6], '2')
        self.assertEqual(self.snapshot('__features_b'), other)
        self.assertEqual(self.build(version='2')['geometry_sha256'], first['geometry_sha256'])
        self.assertEqual(self.storage.get_object.call_count, 1)
        self.assertEqual(self.database.execute('SELECT count(*) FROM atlas.decision_basins WHERE revision=%s', ('__features_a',)).fetchone()[0], 1)

    def test_revision_selection_deduplicates_features_and_tracks_construction_versions(self):
        from worldatlas.source_imports.run_import import selected_constructions

        self.build()
        self.build(revision='__features_b')
        self.assertEqual(selected_constructions(self.database, ['__features_a', '__features_b']),
                         [('__features', '1', '__features_a'), ('__features', '1', '__features_b')])
        self.register('2')
        self.build(version='2')
        self.assertEqual(selected_constructions(self.database, ['__features_a']),
                         [('__features', '2', '__features_a')])
        with self.assertRaisesRegex(ValueError, 'unknown decision revisions'):
            selected_constructions(self.database, ['missing'])

    def test_save_rolls_back_all_features_on_missing_source(self):
        self.build()
        before = self.snapshot()
        features = [dict(feature_id='point-a', source_id='__feature_raw', source_version='1',
                         source_feature_id='a', geometry={'type': 'Point', 'coordinates': [11, 21]}),
                    dict(feature_id='point-b', source_id='missing', source_version='1',
                         source_feature_id='b', geometry={'type': 'Point', 'coordinates': [12, 22]})]
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            save_features(self.database, '__features_a', features, self.recipe)
        self.assertEqual(self.snapshot(), before)

    def test_table_import_uses_the_same_atomic_storage_and_cache(self):
        raw = b'provider_id,name,longitude,latitude\na,First,-20.25,11.5\n'
        self.database.execute('INSERT INTO atlas.source_assets '
                              '(source_id,version,title,provider,source_uri,license_name,license_uri,'
                              'attribution,r2_bucket,r2_key,sha256,size_bytes,provenance) '
                              "SELECT source_id,'2',title,provider,source_uri,license_name,license_uri,"
                              'attribution,r2_bucket,%s,%s,%s,provenance FROM atlas.source_assets '
                              'WHERE source_id=%s AND version=%s',
                              ('source.csv', hashlib.sha256(raw).hexdigest(), len(raw), '__feature_raw', '1'))
        self.storage.get_object.side_effect = lambda **_: {'Body': io.BytesIO(raw)}
        self.recipe.update(method='selected_table_points', source_version='2', longitude_field='longitude',
                           latitude_field='latitude', coordinate_reference='OGC:CRS84')
        self.recipe['selections'][0]['expected_properties'] = {'name': 'First'}
        self.register('2')
        self.build(version='2')
        before = self.snapshot()
        self.assertEqual(before[0][1], {'type': 'Point', 'coordinates': [-20.25, 11.5]})
        self.assertEqual(before[0][4]['provider_properties']['name'], 'First')
        self.build(version='2')
        self.assertEqual(self.storage.get_object.call_count, 1)
        self.recipe['selections'][0]['expected_properties']['name'] = 'Changed'
        self.register('3')
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.build(version='3')
        self.assertEqual(self.snapshot(), before)

    def test_signed_zero_checksum_matches_the_geometry_read_back_from_jsonb(self):
        save_features(self.database, '__features_a', [dict(
            feature_id='zero', source_id='__feature_raw', source_version='1', source_feature_id='a',
            geometry={'type': 'Point', 'coordinates': [-0.0, 0.0]})], self.recipe)
        row = self.snapshot()[0]
        self.assertEqual(geometry_hash(row[1]), row[3])

    def test_expected_checksum_survives_vector_and_table_import_storage_and_repeat(self):
        expected = hashlib.sha256(b'{"coordinates":[0.0,1e-24],"type":"Point"}').hexdigest()
        for method, raw, suffix in (
            ('selected_vector_features', json.dumps({'type': 'FeatureCollection', 'features': [
                {'type': 'Feature', 'properties': {'provider_id': 'a'},
                 'geometry': {'type': 'Point', 'coordinates': [-0.0, 1e-24]}}]}).encode(), 'geojson'),
            ('selected_table_points', b'provider_id,lon,lat\na,-0.0,1e-24\n', 'csv'),
        ):
            with self.subTest(method=method):
                self.database.execute(
                    'INSERT INTO atlas.source_assets '
                    '(source_id,version,title,provider,source_uri,license_name,license_uri,'
                    'attribution,r2_bucket,r2_key,sha256,size_bytes,provenance) '
                    'SELECT source_id,%s,title,provider,source_uri,license_name,license_uri,'
                    'attribution,r2_bucket,%s,%s,%s,provenance FROM atlas.source_assets '
                    'WHERE source_id=%s AND version=%s',
                    (method, 'zero.' + suffix, hashlib.sha256(raw).hexdigest(), len(raw), '__feature_raw', '1'))
                self.recipe.update(method=method, source_version=method)
                if suffix == 'csv':
                    self.recipe.update(longitude_field='lon', latitude_field='lat', coordinate_reference='OGC:CRS84')
                self.recipe['selections'][0]['expected_geometry_sha256'] = expected
                self.register(method)
                self.storage.get_object.side_effect = lambda **_: {'Body': io.BytesIO(raw)}
                self.build(version=method)
                before = self.snapshot()
                self.assertEqual(json.dumps(before[0][1]['coordinates']), '[0.0, 1e-24]')
                self.assertEqual(before[0][3], expected)
                self.build(version=method)
                self.assertEqual(self.snapshot(), before)
                self.recipe['selections'][0]['expected_geometry_sha256'] = '0' * 64
                self.register(method + '-bad')
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    self.build(version=method + '-bad')
                self.assertEqual(self.snapshot(), before)

    def test_native_geometry_retains_its_declared_coordinate_reference(self):
        save_features(self.database, '__features_a', [dict(
            feature_id='native', source_id='__feature_raw', source_version='1', source_feature_id='a',
            coordinate_reference='EPSG:3857', geometry={'type': 'Point', 'coordinates': [1000, 2000]})], self.recipe)
        row = self.snapshot()[0]
        self.assertEqual(row[1], {'type': 'Point', 'coordinates': [1000, 2000]})
        self.assertEqual(row[2], 'EPSG:3857')
        self.assertEqual(row[3], geometry_hash(row[1]))
