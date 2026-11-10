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

from shared.build_osm_boundary import build_boundary, download_archive, save_boundary


def source_fixture():
    elements = [{'type': 'node', 'id': 1, 'lon': 0, 'lat': 0},
                {'type': 'node', 'id': 2, 'lon': 1, 'lat': 1},
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


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.raw, self.source = source_fixture()
        self.storage = Mock()
        self.storage.get_object.return_value = {'Body': io.BytesIO(self.raw)}

    def test_download_and_reuse(self):
        path = download_archive(self.storage, self.source, self.directory)
        self.assertEqual(path.read_bytes(), self.raw)
        self.storage.get_object.assert_called_once_with(Bucket='test', Key='source.zip')
        self.assertEqual(download_archive(self.storage, self.source, self.directory), path)
        self.assertEqual(self.storage.get_object.call_count, 1)

    def test_reject_corrupt_download_and_remove_partial(self):
        self.storage.get_object.return_value = {'Body': io.BytesIO(b'corrupt')}
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            download_archive(self.storage, self.source, self.directory)
        self.assertEqual(list(self.directory.rglob('*.*')), [])

    def test_reject_wrong_catalog_size(self):
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            download_archive(self.storage, dict(self.source, size_bytes=1), self.directory)

    def test_reject_corrupt_cache(self):
        path = download_archive(self.storage, self.source, self.directory)
        path.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            download_archive(self.storage, self.source, self.directory)
        self.assertEqual(self.storage.get_object.call_count, 1)

    def test_download_error_removes_partial(self):
        self.storage.get_object.side_effect = OSError('connection interrupted')
        with self.assertRaisesRegex(OSError, 'interrupted'):
            download_archive(self.storage, self.source, self.directory)
        self.assertEqual(list(self.directory.rglob('*.*')), [])


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
        self.storage = Mock()
        self.storage.get_object.side_effect = lambda **kwargs: {'Body': io.BytesIO(self.raw)}
        self.database.execute("INSERT INTO atlas.entity_registry_revisions VALUES ('__osm_entities')")
        for revision in ('__osm_a', '__osm_b'):
            self.database.execute('INSERT INTO atlas.decision_revisions VALUES (%s,%s,%s)',
                                  (revision, '__osm_entities', Jsonb({})))
        for version in ('1', '2', 'evidence'):
            self.database.execute(
                "INSERT INTO atlas.source_assets "
                "(source_id,version,title,kind,provider,source_uri,license_name,license_uri,"
                "attribution,r2_bucket,r2_key,sha256,size_bytes,provenance) "
                "VALUES ('osm-test',%s,'Test','raw','Test','test:source','Test','test:license',"
                "'Test','test',%s,%s,%s,'{}')",
                (version, version + '.zip', self.source['sha256'], self.source['size_bytes']),
            )

    def build(self, revision='__osm_a', version='1', expected=None):
        return build_boundary(self.database, self.storage, 'osm-test', version, revision,
                              'border', 'Test rationale', self.directory, expected)

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
        self.assertEqual(provenance['construction']['archive_sha256'], self.source['sha256'])
        self.assertEqual(self.links(), [('1', 'geometry_source')])
        self.assertEqual(self.build(), result)
        self.assertEqual(self.links(), [('1', 'geometry_source')])
        self.assertEqual(self.storage.get_object.call_count, 1)

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
        self.assertEqual(self.links(), [('2', 'geometry_source'), ('evidence', 'supporting_evidence')])
        self.assertEqual(self.boundary()[2]['review_note'], 'keep me')
        self.assertEqual(self.boundary('__osm_b'), before)

    def test_geometry_can_change_without_release_pin(self):
        self.build()
        changed = {'type': 'LineString', 'coordinates': [[0.0, 0.0], [2.0, 2.0]]}
        digest = save_boundary(self.database, '__osm_a', 'border', changed,
                               self.source, 'Changed source interpretation')
        self.assertEqual(self.boundary()[:2], (changed, digest))

    def test_unknown_revision_stops_before_download(self):
        with self.assertRaisesRegex(ValueError, 'revision does not exist'):
            self.build(revision='missing')
        self.storage.get_object.assert_not_called()

    def test_missing_source_stops_before_download(self):
        with self.assertRaisesRegex(ValueError, 'raw source version is missing'):
            self.build(version='missing')
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
        self.assertEqual(self.links(), [('1', 'geometry_source')])

    def test_failed_source_link_rolls_back_geometry_and_links(self):
        import psycopg

        self.build()
        before = self.boundary()
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            save_boundary(self.database, '__osm_a', 'border',
                          {'type': 'LineString', 'coordinates': [[0, 0], [2, 2]]},
                          dict(self.source, version='missing'), 'Must roll back')
        self.assertEqual(self.boundary(), before)
        self.assertEqual(self.links(), [('1', 'geometry_source')])


if __name__ == '__main__':
    unittest.main()
