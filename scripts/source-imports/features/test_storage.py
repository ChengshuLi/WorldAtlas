import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import psycopg

from features.build_features import build_features
from features.geometry import geometry_hash, save_features


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
            '(source_id,version,title,kind,provider,source_uri,license_name,license_uri,'
            'attribution,r2_bucket,r2_key,sha256,size_bytes,provenance) '
            "VALUES ('__feature_raw','1','Test','raw','Test','test:source','Test','test:license',"
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
        return self.database.execute('SELECT feature_id,geometry,coordinate_reference,geometry_sha256,evidence '
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
        self.assertEqual(after[4]['construction_ref']['version'], '2')
        self.assertEqual(self.snapshot('__features_b'), other)
        self.assertEqual(self.build(version='2')['geometry_sha256'], first['geometry_sha256'])
        self.assertEqual(self.storage.get_object.call_count, 1)
        self.assertEqual(self.database.execute('SELECT count(*) FROM atlas.decision_basins WHERE revision=%s', ('__features_a',)).fetchone()[0], 1)

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
                              '(source_id,version,title,kind,provider,source_uri,license_name,license_uri,'
                              'attribution,r2_bucket,r2_key,sha256,size_bytes,provenance) '
                              "SELECT source_id,'2',title,kind,provider,source_uri,license_name,license_uri,"
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

    def test_schema_upgrade_from_previous_layout_is_idempotent(self):
        with self.database.transaction(force_rollback=True):
            self.database.execute('ALTER TABLE atlas.decision_features DROP COLUMN geometry, DROP COLUMN coordinate_reference')
            sql = (Path(__file__).resolve().parents[3] / 'database/upgrades/feature_geometry.sql').read_text()
            self.database.execute(sql)
            self.database.execute(sql)
            self.build()
            self.assertEqual(self.snapshot()[0][2], 'OGC:CRS84')

    def test_database_rejects_half_populated_geometry(self):
        self.build()
        with self.assertRaises(psycopg.errors.CheckViolation), self.database.transaction():
            self.database.execute("UPDATE atlas.decision_features SET coordinate_reference=NULL WHERE revision='__features_a'")
