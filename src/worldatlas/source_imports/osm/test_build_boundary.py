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

from contextlib import nullcontext
from worldatlas.source_imports.run_import import run_import
from worldatlas.source_imports.osm.build_boundary import save_boundary


def source_fixture(endpoint=(1, 1), *, coordinates=None):
    points = coordinates if coordinates is not None else [(0, 0), endpoint]
    elements = [{'type': 'node', 'id': i, 'lon': x, 'lat': y}
                for i, (x, y) in enumerate(points, 1)]
    elements.append({'type': 'way', 'id': 3, 'nodes': list(range(1, len(points) + 1))})
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
    """Exercise actual SQL and rollback behavior; every test removes its fixtures."""
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
                "(source_id,version,title,provider,source_uri,license_name,license_uri,"
                "attribution,r2_bucket,r2_key,sha256,size_bytes) "
                "VALUES ('osm-test',%s,'Test','Test','test:source','Test','test:license',"
                "'Test','test',%s,%s,%s)",
                (version, version + '.zip', source['sha256'], source['size_bytes']),
            )
        self.recipe = self.add_recipe('1')
        self.add_recipe('2', source_version='2')

    def add_recipe(self, version, **changes):
        recipe = dict(method='osm_way_chain', source_id='osm-test', source_version='1',
                      boundary_id='border', basis='Test construction description')
        recipe.update(changes)
        text = json.dumps(recipe, sort_keys=True, separators=(',', ':'))
        self.database.execute(
            'INSERT INTO atlas.construction_records(source_id,version,document) VALUES (%s,%s,%s::jsonb)',
            ('__osm_recipe', version, text),
        )
        return dict(recipe, recipe_id='__osm_recipe', recipe_version=version)

    def build(self, revision='__osm_a', version='1', expected=None):
        return run_import(lambda: nullcontext(self.database), '__osm_recipe', version,
                          storage=self.storage, revision=revision, work_dir=self.directory,
                          expected_geometry_sha256=expected)

    def boundary(self, revision='__osm_a'):
        return self.database.execute(
            'SELECT geometry,geometry_sha256,provenance,construction_version FROM atlas.decision_mainland_boundaries '
            'WHERE revision=%s AND boundary_id=%s', (revision, 'border'),
        ).fetchone()

    def links(self):
        return self.database.execute(
            'SELECT source_version,relationship FROM atlas.decision_mainland_boundary_sources '
            "WHERE revision='__osm_a' AND boundary_id='border' ORDER BY source_version"
        ).fetchall()

    def test_full_build_and_idempotent_repeat(self):
        result = self.build()
        geometry, digest, provenance, construction_version = self.boundary()
        self.assertEqual(geometry['coordinates'], [[0.0, 0.0], [1.0, 1.0]])
        self.assertEqual(result['sha256'], digest)
        self.assertEqual(result['vertices'], 2)
        self.assertEqual(provenance['basis'], 'Test construction description')
        self.assertEqual(self.database.execute("SELECT construction_id FROM atlas.decision_mainland_boundaries WHERE revision='__osm_a' AND boundary_id='border'").fetchone()[0], '__osm_recipe')
        self.assertEqual(construction_version, '1')
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
        self.assertEqual(self.boundary()[3], '2')
        self.assertEqual(self.boundary('__osm_b'), before)

    def test_imported_boundary_is_consumable_by_map_builder(self):
        from worldatlas.map_build.inputs.features import feature_geometry

        self.build()
        from worldatlas.map_build.inputs.selection import QUERY
        query = QUERY
        raw = self.database.execute(query.read_text(), {'revision': '__osm_a'}).fetchone()[0]
        selected = json.loads(raw)
        self.assertEqual(selected['decision_revision']['id'], '__osm_a')
        record = next(b for b in selected['mainland_boundaries'] if b['boundary_id'] == 'border')
        geometry = feature_geometry(record, ('LineString',))
        self.assertEqual(geometry, self.boundary()[0])
        self.assertEqual(record['source_refs'][0]['relationship'], 'construction_input')
        source = next(s for s in selected['sources'] if s['source_id'] == 'osm-test')
        self.assertEqual(source, {'source_id': 'osm-test', 'version': '1'})

    def test_geometry_can_change_without_release_pin(self):
        self.build()
        changed = {'type': 'LineString', 'coordinates': [[0.0, 0.0], [2.0, 2.0]]}
        digest = save_boundary(self.database, '__osm_a', changed, self.source,
                               dict(self.recipe, basis='Changed source interpretation'))
        self.assertEqual(self.boundary()[:2], (changed, digest))

    def test_signed_zero_boundary_can_be_read_by_map_builder(self):
        from worldatlas.map_build.inputs.features import feature_geometry

        geometry = {'type': 'LineString', 'coordinates': [[-0.0, 0.0], [1.0, 1.0]]}
        digest = save_boundary(self.database, '__osm_a', geometry, self.source, self.recipe)
        saved, stored_digest, *_ = self.boundary()
        self.assertEqual(digest, stored_digest)
        self.assertEqual(feature_geometry(dict(geometry=saved, geometry_sha256=digest,
                                              coordinate_reference='OGC:CRS84'), ('LineString',)), saved)

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

    def test_malformed_recipes_are_rejected_when_inserted(self):
        import psycopg
        for changes in ({'method': 'some.python.function'}, {'basis': ''}, {'extra': 1}):
            with self.subTest(changes=changes), self.assertRaises(psycopg.errors.CheckViolation), self.database.transaction():
                self.add_recipe('invalid', **changes)
        with self.assertRaises(psycopg.errors.CheckViolation), self.database.transaction():
            self.database.execute("INSERT INTO atlas.construction_records VALUES ('__osm_recipe','incomplete','{}')")
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

    def test_crossing_source_leaves_existing_boundary_and_links_unchanged(self):
        self.build()
        before = self.boundary()
        raw, source = source_fixture(coordinates=[(0, 0), (2, 2), (0, 2), (2, 0)])
        self.database.execute(
            'INSERT INTO atlas.source_assets '
            '(source_id,version,title,provider,source_uri,license_name,license_uri,'
            'attribution,r2_bucket,r2_key,sha256,size_bytes) '
            "SELECT source_id,'crossing',title,provider,source_uri,license_name,license_uri,"
            "attribution,r2_bucket,'crossing.zip',%s,%s FROM atlas.source_assets "
            "WHERE source_id='osm-test' AND version='1'",
            (source['sha256'], source['size_bytes']))
        self.add_recipe('crossing', source_version='crossing')
        self.storage.get_object.side_effect = lambda **kwargs: {'Body': io.BytesIO(raw)}
        with self.assertRaisesRegex(ValueError, 'self-intersection'):
            self.build(version='crossing')
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
            "INSERT INTO atlas.decision_mainland_seed_regions VALUES ('__osm_a','region','[]')")
        self.database.execute(
            "INSERT INTO atlas.decision_mainland_region_segments VALUES "
            "('__osm_a','region',0,'boundary','border',NULL,false),"
            "('__osm_a','region',1,'boundary','return',NULL,false)")

    def region_sections(self):
        return self.database.execute(
            "SELECT * FROM atlas.decision_mainland_region_segments WHERE revision='__osm_a' ORDER BY ordinal").fetchall()

    def test_changed_vertex_count_needs_no_region_reference_updates(self):
        self.region_fixture()
        sections = self.region_sections()
        geometry = {'type': 'LineString', 'coordinates': [[0., 0.], [.4, .6], [1., 1.]]}
        save_boundary(self.database, '__osm_a', geometry, self.source, self.recipe)
        self.assertEqual(self.boundary()[0], geometry)
        self.assertEqual(self.region_sections(), sections)

    def test_broken_region_join_rolls_back_boundary_and_source_links(self):
        self.region_fixture()
        before, sections = self.boundary(), self.region_sections()
        with self.assertRaisesRegex(ValueError, 'does not join'):
            save_boundary(self.database, '__osm_a',
                          {'type': 'LineString', 'coordinates': [[0., 0.], [.4, .6], [2., 2.]]},
                          self.source, self.recipe)
        self.assertEqual(self.boundary(), before)
        self.assertEqual(self.links(), [('1', 'construction_input')])
        self.assertEqual(self.region_sections(), sections)

    def test_simple_boundary_crossing_another_region_section_rolls_back(self):
        from shapely.geometry import LineString, Polygon

        self.region_fixture()
        before, sections = self.boundary(), self.region_sections()
        coordinates = [[0., 0.], [2., .5], [1., 1.]]
        self.assertTrue(LineString(coordinates).is_simple)
        self.assertFalse(Polygon([*coordinates, [1., 0.], [0., 0.]]).is_valid)
        with self.assertRaisesRegex(ValueError, 'invalid region polygon'):
            save_boundary(self.database, '__osm_a',
                          {'type': 'LineString', 'coordinates': coordinates},
                          self.source, self.recipe)
        self.assertEqual(self.boundary(), before)
        self.assertEqual(self.links(), [('1', 'construction_input')])
        self.assertEqual(self.region_sections(), sections)

    def test_parallel_boundary_updates_validate_the_latest_committed_region(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        import time

        import psycopg

        self.region_fixture()
        self.database.commit()

        def cleanup():
            self.database.rollback()
            with self.database.transaction():
                for table in ('decision_mainland_region_segments', 'decision_mainland_seed_regions',
                              'decision_mainland_boundary_sources', 'decision_mainland_boundaries',
                              'decision_revisions'):
                    self.database.execute('DELETE FROM atlas.' + table + " WHERE revision IN ('__osm_a','__osm_b')")
                self.database.execute("DELETE FROM atlas.entity_registry_revisions WHERE revision='__osm_entities'")
                self.database.execute("DELETE FROM atlas.construction_records WHERE source_id='__osm_recipe'")
                self.database.execute("DELETE FROM atlas.source_assets WHERE source_id='osm-test'")

        self.addCleanup(cleanup)
        paused, release = Event(), Event()

        class PauseBeforeValidation:
            def __init__(self, database):
                self.database = database

            def transaction(self):
                return self.database.transaction()

            def execute(self, sql, parameters):
                if sql.startswith('SELECT s.reverse,coalesce'):
                    paused.set()
                    if not release.wait(5):
                        raise AssertionError('test did not release the first writer')
                return self.database.execute(sql, parameters)

        first = {'type': 'LineString', 'coordinates': [[0., 0.], [.4, .6], [1., 1.]]}
        second = {'type': 'LineString', 'coordinates': [[1., 1.], [1.2, -.2], [0., 0.]]}

        def write(database, geometry, boundary_id):
            return save_boundary(database, '__osm_a', geometry, self.source,
                                 dict(self.recipe, boundary_id=boundary_id))

        url = os.environ['WORLDATLAS_TEST_DATABASE_URL']
        with psycopg.connect(url) as a, psycopg.connect(url) as b, \
                psycopg.connect(url, autocommit=True) as observer, ThreadPoolExecutor(2) as workers:
            try:
                first_result = workers.submit(write, PauseBeforeValidation(a), first, 'border')
                self.assertTrue(paused.wait(5))
                second_result = workers.submit(write, b, second, 'return')
                deadline = time.monotonic() + 5
                while not second_result.done():
                    blockers = observer.execute('SELECT pg_blocking_pids(%s)', (b.info.backend_pid,)).fetchone()[0]
                    if a.info.backend_pid in blockers:
                        break
                    if time.monotonic() >= deadline:
                        self.fail('second writer neither completed nor waited for the first writer')
                    release.wait(.01)
            finally:
                release.set()
            first_result.result(timeout=5)
            second_result.result(timeout=5)

        from shapely.geometry import Polygon
        saved = dict(self.database.execute(
            "SELECT boundary_id,geometry FROM atlas.decision_mainland_boundaries WHERE revision='__osm_a'").fetchall())
        self.assertEqual(saved, {'border': first, 'return': second})
        self.assertTrue(Polygon([*saved['border']['coordinates'], *saved['return']['coordinates'][1:]]).is_valid)


if __name__ == '__main__':
    unittest.main()
