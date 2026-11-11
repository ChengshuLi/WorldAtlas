import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import zipfile

from psycopg.types.json import Jsonb

from osm.build_boundary import build_boundary, save_boundary


def source_fixture(endpoint=(1, 1)):
    elements = [{'type': 'node', 'id': 1, 'lon': 0, 'lat': 0},
                {'type': 'node', 'id': 2, 'lon': endpoint[0], 'lat': endpoint[1]},
                {'type': 'way', 'id': 3, 'nodes': [1, 2]}]
    response = json.dumps({'elements': elements}).encode()
    manifest = {'start_node': 1, 'ways': [{'id': 3, 'file': '3.json',
                 'sha256': hashlib.sha256(response).hexdigest()}]}
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        archive.writestr('manifest.json', json.dumps(manifest))
        archive.writestr('3.json', response)
    raw = output.getvalue()
    return raw, {'source_id': 'osm-test', 'version': '1', 'r2_bucket': 'test',
                 'r2_key': 'source.zip', 'sha256': hashlib.sha256(raw).hexdigest(),
                 'size_bytes': len(raw)}


@unittest.skipUnless(os.environ.get('WORLDATLAS_TEST_DATABASE_URL'),
                     'set WORLDATLAS_TEST_DATABASE_URL to a local database with the initial schema')
class DatabaseTest(unittest.TestCase):
    """Exercise actual SQL and rollback behavior; every test rolls back its fixtures."""
    def setUp(self):
        import psycopg

        self.database = psycopg.connect(os.environ['WORLDATLAS_TEST_DATABASE_URL'])
        self.addCleanup(self.database.close)
        self.addCleanup(self.database.rollback)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.raw, self.source = source_fixture()
        raw_updated, source_updated = source_fixture(endpoint=(2, 2))
        self.storage = Mock()
        responses = {'1.zip': self.raw, '2.zip': raw_updated}
        self.storage.get_object.side_effect = lambda **kwargs: {
            'Body': io.BytesIO(responses[kwargs['Key']])}
        self.database.execute("INSERT INTO atlas.entity_registry_revisions VALUES ('__osm_entities')")
        for revision in ('__osm_a', '__osm_b'):
            self.database.execute('INSERT INTO atlas.decision_revisions VALUES (%s,%s,%s)',
                                  (revision, '__osm_entities', Jsonb({})))
        for version in ('1', '2', 'evidence'):
            source = source_updated if version == '2' else self.source
            self.database.execute(
                "INSERT INTO atlas.source_assets "
                "(source_id,version,title,kind,provider,source_uri,license_name,license_uri,"
                "attribution,r2_bucket,r2_key,sha256,size_bytes,provenance) "
                "VALUES ('osm-test',%s,'Test','raw','Test','test:source','Test','test:license',"
                "'Test','test',%s,%s,%s,'{\"origin\":\"test:source\",\"representation\":\"provider_original_bundle\"}')",
                (version, version + '.zip', source['sha256'], source['size_bytes']),
            )
        self.recipe = self.add_recipe('1')
        self.add_recipe('2', source_version='2')

    def add_recipe(self, version, **changes):
        recipe = dict(method='osm_way_chain', source_id='osm-test', source_version='1',
                      boundary_id='border', basis='Test construction description')
        recipe.update(changes)
        text = json.dumps(recipe, sort_keys=True, separators=(',', ':'))
        raw = text.encode()
        self.database.execute(
            'INSERT INTO atlas.structured_documents VALUES (%s,%s,%s,%s,%s::json)',
            ('__osm_recipe', version, hashlib.sha256(raw).hexdigest(), len(raw), text),
        )
        return dict(recipe, recipe_id='__osm_recipe', recipe_version=version)

    def build(self, revision='__osm_a', version='1', expected=None):
        return build_boundary(self.database, self.storage, '__osm_recipe', version,
                              revision, self.directory, expected)

    def boundary(self, revision='__osm_a'):
        return self.database.execute(
            'SELECT geometry,geometry_sha256,provenance FROM atlas.decision_mainland_boundaries '
            'WHERE revision=%s AND boundary_id=%s', (revision, 'border'),
        ).fetchone()

    def links(self):
        return self.database.execute(
            'SELECT source_version,relationship FROM atlas.decision_mainland_boundary_sources '
            "WHERE revision='__osm_a' AND boundary_id='border' ORDER BY source_version"
        ).fetchall()

    def test_full_build_and_idempotent_repeat(self):
        result = self.build()
        geometry, digest, provenance = self.boundary()
        self.assertEqual(geometry['coordinates'], [[0.0, 0.0], [1.0, 1.0]])
        self.assertEqual(result['sha256'], digest)
        self.assertEqual(result['vertices'], 2)
        self.assertEqual(provenance['basis'], 'Test construction description')
        self.assertEqual(provenance['construction']['recipe_id'], '__osm_recipe')
        self.assertEqual(provenance['construction']['recipe_version'], '1')
        self.assertEqual(provenance['construction']['archive_sha256'], self.source['sha256'])
        self.assertEqual(self.links(), [('1', 'construction_input')])
        self.assertEqual(self.build(), result)
        self.assertEqual(self.links(), [('1', 'construction_input')])
        self.assertEqual(self.storage.get_object.call_count, 1)

    def test_source_consumed_by_the_constructor_is_marked_as_an_input(self):
        self.build()
        self.database.execute("UPDATE atlas.decision_mainland_boundary_sources "
                              "SET relationship='supporting_evidence' "
                              "WHERE revision='__osm_a' AND boundary_id='border'")
        self.build()
        self.assertEqual(self.links(), [('1', 'construction_input')])

    def test_source_update_preserves_evidence_notes_and_other_revision(self):
        self.build()
        self.build(revision='__osm_b')
        before = self.boundary('__osm_b')
        self.database.execute(
            "UPDATE atlas.decision_mainland_boundaries SET provenance=provenance || "
            "'{\"review_note\":\"keep me\"}' WHERE revision='__osm_a'")
        self.database.execute(
            "INSERT INTO atlas.decision_mainland_boundary_sources "
            "VALUES ('__osm_a','border','osm-test','evidence','supporting_evidence')")
        self.build(version='2')
        self.assertEqual(self.links(), [('2', 'construction_input'), ('evidence', 'supporting_evidence')])
        self.assertEqual(self.boundary()[2]['review_note'], 'keep me')
        self.assertEqual(self.boundary()[0]['coordinates'], [[0.0, 0.0], [2.0, 2.0]])
        self.assertNotEqual(self.boundary()[1], before[1])
        self.assertEqual(self.boundary()[2]['construction']['recipe_version'], '2')
        self.assertEqual(self.boundary('__osm_b'), before)

    def test_imported_boundary_is_consumable_by_map_builder(self):
        import importlib.util
        import sys
        from unittest.mock import patch

        self.build()
        scripts = Path(__file__).resolve().parents[2]
        query = scripts / 'map-build/land/mainland-l2-draft/query-stage2-selected.sql'
        raw = self.database.execute(query.read_text(), {'revision': '__osm_a'}).fetchone()[0]
        path = scripts / 'map-build/stages/land/stage2-geodesic-20261104/seed-producer/export_adapter.py'
        spec = importlib.util.spec_from_file_location('osm_test_export_adapter', path)
        adapter = importlib.util.module_from_spec(spec)
        with patch.object(sys, 'path', [str(path.parent), *sys.path]):
            spec.loader.exec_module(adapter)
        revision, registry, records, sources = adapter.boundary_records(json.loads(raw))
        self.assertEqual((revision, registry), ('__osm_a', '__osm_entities'))
        boundary = records['boundary', 'border']
        self.assertEqual(boundary['lineage_status'], 'complete')
        self.assertEqual(boundary['qualified_source_refs'][0]['role'], 'construction_input')
        self.assertEqual(sources['osm-test', '1']['sha256'], self.source['sha256'])

    def test_geometry_can_change_without_release_pin(self):
        self.build()
        changed = {'type': 'LineString', 'coordinates': [[0.0, 0.0], [2.0, 2.0]]}
        digest = save_boundary(self.database, '__osm_a', changed, self.source,
                               dict(self.recipe, basis='Changed source interpretation'))
        self.assertEqual(self.boundary()[:2], (changed, digest))

    def test_unknown_revision_stops_before_download(self):
        with self.assertRaisesRegex(ValueError, 'revision does not exist'):
            self.build(revision='missing')
        self.storage.get_object.assert_not_called()

    def test_missing_source_stops_before_download(self):
        self.add_recipe('missing-source', source_version='missing')
        with self.assertRaisesRegex(ValueError, 'raw source version is missing'):
            self.build(version='missing-source')
        self.storage.get_object.assert_not_called()

    def test_missing_recipe_stops_before_download(self):
        with self.assertRaisesRegex(ValueError, 'construction record is missing'):
            self.build(version='missing')
        self.storage.get_object.assert_not_called()

    def test_recipe_checksum_mismatch_stops_before_download(self):
        self.database.execute("INSERT INTO atlas.structured_documents VALUES "
                              "('__osm_recipe','bad-hash',repeat('0',64),2,'{}')")
        with self.assertRaisesRegex(ValueError, 'construction record size or hash mismatch'):
            self.build(version='bad-hash')
        self.storage.get_object.assert_not_called()

    def test_unknown_method_stops_before_download(self):
        self.add_recipe('unknown-method', method='some.python.function')
        with self.assertRaisesRegex(ValueError, 'unsupported construction method'):
            self.build(version='unknown-method')
        self.storage.get_object.assert_not_called()

    def test_empty_description_stops_before_download(self):
        self.add_recipe('empty-basis', basis='')
        with self.assertRaisesRegex(ValueError, 'invalid OSM construction record'):
            self.build(version='empty-basis')
        self.storage.get_object.assert_not_called()

    def test_corrupt_download_does_not_create_boundary(self):
        self.storage.get_object.side_effect = None
        self.storage.get_object.return_value = {'Body': io.BytesIO(b'corrupt')}
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            self.build()
        self.assertIsNone(self.boundary())
        self.assertEqual(self.links(), [])

    def test_expected_geometry_mismatch_leaves_boundary_unchanged(self):
        self.build()
        before = self.boundary()
        with self.assertRaisesRegex(ValueError, 'expected geometry'):
            self.build(expected='0' * 64)
        self.assertEqual(self.boundary(), before)
        self.assertEqual(self.links(), [('1', 'construction_input')])

    def test_failed_source_link_rolls_back_geometry_and_links(self):
        import psycopg

        self.build()
        before = self.boundary()
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            save_boundary(self.database, '__osm_a',
                          {'type': 'LineString', 'coordinates': [[0, 0], [2, 2]]},
                          dict(self.source, version='missing'), self.recipe)
        self.assertEqual(self.boundary(), before)
        self.assertEqual(self.links(), [('1', 'construction_input')])

    def region_fixture(self):
        self.build()
        save_boundary(self.database, '__osm_a',
                      {'type': 'LineString', 'coordinates': [[1., 1.], [1., 0.], [0., 0.]]},
                      self.source, dict(self.recipe, boundary_id='return'))
        self.database.execute(
            "INSERT INTO atlas.decision_mainland_seed_regions VALUES "
            "('__osm_a','region','selected_for_research',repeat('0',64),"
            "'binary64-sorted-compact-geojson-v1','[]')")
        self.database.execute(
            "INSERT INTO atlas.decision_mainland_region_segments VALUES "
            "('__osm_a','region',0,'boundary','border',NULL,0,2,false),"
            "('__osm_a','region',1,'boundary','return',NULL,0,3,false)")

    def test_changed_vertex_count_updates_region_references_and_hash_in_one_write(self):
        self.region_fixture()
        geometry = {'type': 'LineString', 'coordinates': [[0., 0.], [.4, .6], [1., 1.]]}
        save_boundary(self.database, '__osm_a', geometry, self.source, self.recipe)
        count = self.database.execute(
            "SELECT end_index FROM atlas.decision_mainland_region_segments "
            "WHERE revision='__osm_a' AND region_id='region' AND ordinal=0").fetchone()[0]
        self.assertEqual(count, 3)
        polygon = {'type': 'Polygon', 'coordinates': [[[0., 0.], [.4, .6], [1., 1.], [1., 0.], [0., 0.]]]}
        digest = hashlib.sha256(json.dumps(polygon, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(self.database.execute(
            "SELECT geometry_sha256 FROM atlas.decision_mainland_seed_regions "
            "WHERE revision='__osm_a' AND region_id='region'").fetchone()[0], digest)

    def test_broken_region_join_rolls_back_boundary_source_links_and_slice(self):
        self.region_fixture()
        before = self.boundary()
        with self.assertRaisesRegex(ValueError, 'does not join'):
            save_boundary(self.database, '__osm_a',
                          {'type': 'LineString', 'coordinates': [[0., 0.], [.4, .6], [2., 2.]]},
                          self.source, self.recipe)
        self.assertEqual(self.boundary(), before)
        self.assertEqual(self.database.execute(
            "SELECT end_index FROM atlas.decision_mainland_region_segments "
            "WHERE revision='__osm_a' AND region_id='region' AND ordinal=0").fetchone()[0], 2)


if __name__ == '__main__':
    unittest.main()
