import json
import os
from pathlib import Path
import tempfile
import unittest
import hashlib

import psycopg
from psycopg.types.json import Jsonb

from map_build.inputs.selection import read_selection, read_saved


@unittest.skipUnless(os.environ.get('WORLDATLAS_TEST_DATABASE_URL'), 'requires disposable PostgreSQL')
class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.url = os.environ['WORLDATLAS_TEST_DATABASE_URL']
        self.writer = psycopg.connect(self.url, autocommit=True)
        self.addCleanup(self.writer.close)
        self.addCleanup(self.remove)
        self.writer.execute("INSERT INTO atlas.geographic_entity_ids(id,color_rgb) VALUES (970000001,'#123456')")
        self.writer.execute("INSERT INTO atlas.entity_registry_revisions VALUES ('__selection_entities')")
        self.writer.execute("INSERT INTO atlas.geographic_entities(revision,id,name,level) "
                            "VALUES ('__selection_entities',970000001,'Selected entity','continent')")
        self.writer.execute("INSERT INTO atlas.decision_revisions VALUES ('__selection_water','__selection_entities','{}')")

    def remove(self):
        self.writer.execute("DELETE FROM atlas.decision_revisions WHERE revision='__selection_water'")
        self.writer.execute("DELETE FROM atlas.geographic_entities WHERE revision='__selection_entities'")
        self.writer.execute("DELETE FROM atlas.entity_registry_revisions WHERE revision='__selection_entities'")
        self.writer.execute('DELETE FROM atlas.geographic_entity_ids WHERE id=970000001')

    def test_later_queries_keep_the_same_view_when_another_worker_commits(self):
        writer = self.writer
        class ConcurrentEditCursor(psycopg.Cursor):
            def execute(self, query, *args, **kwargs):
                self.domain = isinstance(query, str) and query.startswith('WITH RECURSIVE')
                return super().execute(query, *args, **kwargs)

            def fetchone(self):
                row = super().fetchone()
                if self.domain:
                    writer.execute("UPDATE atlas.geographic_entity_ids SET color_rgb='#ABCDEF' WHERE id=970000001")
                return row
        with psycopg.connect(self.url, cursor_factory=ConcurrentEditCursor) as reader:
            result = read_selection(reader, {'water': '__selection_water'})
            self.assertEqual(reader.info.transaction_status, psycopg.pq.TransactionStatus.IDLE)
        self.assertEqual(result['registry_colors']['__selection_entities'],
                         [{'entity_id': 970000001, 'color_rgb': '#123456'}])
        self.assertEqual(writer.execute('SELECT color_rgb FROM atlas.geographic_entity_ids WHERE id=970000001').fetchone()[0], '#ABCDEF')

    def test_saved_replay_keeps_old_values_after_an_edit(self):
        with psycopg.connect(self.url) as database:
            selected = read_selection(database, {'water': '__selection_water'})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'selection.json'
            path.write_text(json.dumps(selected))
            self.writer.execute("UPDATE atlas.geographic_entity_ids SET color_rgb='#ABCDEF' WHERE id=970000001")
            self.assertEqual(read_saved(path, selected['revisions']), selected)
            with self.assertRaisesRegex(ValueError, 'different geographic revisions'):
                read_saved(path, {'water': 'different'})

    def test_missing_revision_is_rejected(self):
        with psycopg.connect(self.url) as database:
            with self.assertRaisesRegex(ValueError, 'missing'):
                read_selection(database, {'water': 'missing'})

    def test_geometry_and_source_metadata_survive_separate_record_reads(self):
        geometry = {'type': 'Point', 'coordinates': [12.25, 45.5]}
        digest = hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.writer.execute(
            'INSERT INTO atlas.source_assets '
            '(source_id,version,title,kind,provider,source_uri,license_name,license_uri,'
            'attribution,r2_bucket,r2_key,sha256,size_bytes,provenance) '
            "VALUES ('__selection_raw','1','Test','raw','Test','test:source','Test','test:license',"
            "'Test','test','source.geojson',%s,1,'{}')", ('a'*64,))
        try:
            self.writer.execute(
                'INSERT INTO atlas.decision_features '
                '(revision,feature_id,source_id,source_version,source_feature_id,geometry_sha256,'
                'geometry,coordinate_reference,evidence) '
                "VALUES ('__selection_water','point','__selection_raw','1','provider-point',%s,%s,'OGC:CRS84','{}')",
                (digest, Jsonb(geometry)))
            with psycopg.connect(self.url) as database:
                result = read_selection(database, {'water': '__selection_water'})
            feature = result['domains']['water']['features'][0]
            self.assertEqual(feature['geometry'], geometry)
            self.assertEqual(feature['geometry_sha256'], digest)
            self.assertEqual(feature['source_feature_id'], 'provider-point')
            self.assertEqual(result['raw_sources'][0]['source_id'], '__selection_raw')
        finally:
            self.writer.execute("DELETE FROM atlas.decision_features WHERE revision='__selection_water'")
            self.writer.execute("DELETE FROM atlas.source_assets WHERE source_id='__selection_raw'")
