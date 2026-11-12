from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import psycopg
from psycopg.types.json import Jsonb

from iho.build_routes import build_routes, save_routes
from iho.s130 import extract_routes
from iho.test_s130 import fixture, GML


@unittest.skipUnless(os.environ.get('WORLDATLAS_TEST_DATABASE_URL'),
                     'set WORLDATLAS_TEST_DATABASE_URL to a local database with the initial schema')
class BuildTests(unittest.TestCase):
    def setUp(self):
        self.database = psycopg.connect(os.environ['WORLDATLAS_TEST_DATABASE_URL'])
        self.addCleanup(self.database.close)
        self.addCleanup(self.database.rollback)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.path, self.digest, self.recipe = fixture(self.work)
        self.raw = self.path.read_bytes()
        self.source = dict(source_id='iho-test', version='1', sha256=self.digest)
        self.database.execute("INSERT INTO atlas.entity_registry_revisions VALUES ('__iho_entities')")
        for revision in ('__iho_a', '__iho_b'):
            self.database.execute("INSERT INTO atlas.decision_revisions VALUES (%s,'__iho_entities','{}')", (revision,))
        self.storage = Mock()
        self.responses = {}
        self.storage.get_object.side_effect = lambda **kwargs: {'Body': io.BytesIO(self.responses[kwargs['Key']])}
        self.register('1', self.recipe, self.raw)
        _, _, changed = fixture(self.work, GML.replace('10 20 20 30', '11 20 20 30'))
        changed['source_version'] = '2'
        self.register('2', changed, self.path.read_bytes())
        self.path.write_bytes(self.raw)

    def register(self, version, recipe, raw):
        self.responses[version + '.zip'] = raw
        self.database.execute(
            'INSERT INTO atlas.source_assets '
            '(source_id,version,title,kind,provider,source_uri,license_name,license_uri,'
            'attribution,r2_bucket,r2_key,sha256,size_bytes,provenance) '
            "VALUES ('iho-test',%s,'Test','raw','Test','test:source','Test','test:license',"
            "'Test','test',%s,%s,%s,'{}')",
            (version, version + '.zip', hashlib.sha256(raw).hexdigest(), len(raw)),
        )
        text = json.dumps(recipe, sort_keys=True, separators=(',', ':'))
        self.database.execute('INSERT INTO atlas.structured_documents VALUES (%s,%s,%s,%s,%s::json)',
                              ('__iho_recipe', version, hashlib.sha256(text.encode()).hexdigest(),
                               len(text.encode()), text))

    def build(self, version='1', revision='__iho_a'):
        return build_routes(self.database, self.storage, '__iho_recipe', version,
                            revision, self.work / 'downloads')

    def snapshot(self, revision='__iho_a'):
        return [self.database.execute(f'SELECT * FROM atlas.{table} WHERE revision=%s ORDER BY 2,3',
                                      (revision,)).fetchall()
                for table in ('decision_endpoints', 'decision_routes', 'decision_route_points')]

    def test_build_and_repeat(self):
        result = self.build()
        before = self.snapshot()
        self.assertEqual(result['endpoint_count'], 4)
        self.assertEqual([len(rows) for rows in before], [4, 2, 4])
        first = self.database.execute("SELECT longitude,latitude,derivation,evidence FROM atlas.decision_endpoints "
                                      "WHERE revision='__iho_a' AND endpoint_id='route-a-endpoint-0'").fetchone()
        self.assertEqual(first[:2], (Decimal(40), Decimal(30)))
        self.assertEqual(first[2]['method'], 'source_decimal_exact_rational')
        self.assertEqual(first[3]['construction']['recipe_id'], '__iho_recipe')
        self.assertEqual(first[3]['source_refs'][0]['sha256'], self.digest)
        self.assertEqual(self.build(), result)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.storage.get_object.call_count, 1)

    def test_changed_source_preserves_notes_and_other_revision(self):
        self.build()
        self.build(revision='__iho_b')
        other = self.snapshot('__iho_b')
        self.database.execute("UPDATE atlas.decision_routes SET evidence=evidence || '{\"review_note\":\"keep\"}' "
                              "WHERE revision='__iho_a'")
        self.build(version='2')
        self.assertEqual(self.database.execute("SELECT latitude FROM atlas.decision_endpoints "
                                               "WHERE revision='__iho_a' AND endpoint_id='route-a-endpoint-1'").fetchone()[0], 11)
        evidence = self.database.execute("SELECT evidence FROM atlas.decision_routes "
                                         "WHERE revision='__iho_a' AND route_id='route-a'").fetchone()[0]
        self.assertEqual(evidence['review_note'], 'keep')
        self.assertEqual(evidence['construction']['recipe_version'], '2')
        self.assertEqual(self.snapshot('__iho_b'), other)

    def test_replaced_endpoint_drops_old_selector_and_point_id(self):
        self.build()
        self.database.execute("UPDATE atlas.decision_endpoints SET evidence=evidence || "
                              "'{\"selector\":{},\"point_id\":\"old\",\"note\":\"keep\"}' "
                              "WHERE revision='__iho_a' AND endpoint_id='route-b-endpoint-1'")
        self.build()
        evidence = self.database.execute("SELECT evidence FROM atlas.decision_endpoints "
                                         "WHERE revision='__iho_a' AND endpoint_id='route-b-endpoint-1'").fetchone()[0]
        self.assertEqual(evidence['note'], 'keep')
        self.assertNotIn('selector', evidence)
        self.assertNotIn('point_id', evidence)

    def test_snapshot_exports_route_and_endpoint_sources(self):
        path = Path(__file__).resolve().parents[2] / 'map-build/map_build/inputs/geography.sql'
        self.build()
        # Exercise the real export query against the transaction's source records.
        raw = self.database.execute(path.read_text(),
                                    {'revision': '__iho_a'}).fetchone()[0]
        snapshot = json.loads(raw)
        self.assertEqual([(s['source_id'], s['version']) for s in snapshot['sources']],
                         [('iho-test', '1')])
        digest = self.database.execute("SELECT sha256 FROM atlas.source_assets "
                                       "WHERE source_id='iho-test' AND version='2'").fetchone()[0]
        self.database.execute("UPDATE atlas.decision_endpoints SET evidence=%s "
                              "WHERE revision='__iho_a' AND endpoint_id='route-b-endpoint-1'",
                              (Jsonb({'source_refs': [dict(source_id='iho-test', version='2', sha256=digest)]}),))
        raw = self.database.execute(path.read_text(),
                                    {'revision': '__iho_a'}).fetchone()[0]
        snapshot = json.loads(raw)
        self.assertEqual([s['version'] for s in snapshot['sources']], ['1', '2'])

    def test_failed_point_link_rolls_back_all_records(self):
        self.build()
        before = self.snapshot()
        result = extract_routes(self.path, self.digest, self.recipe)
        result['endpoints'][0]['name'] = 'Must roll back'
        result['routes'][1]['points'][1]['endpoint_id'] = 'missing'
        recipe = dict(self.recipe, recipe_id='__iho_recipe', recipe_version='1')
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            save_routes(self.database, '__iho_a', result, self.source, recipe)
        self.assertEqual(self.snapshot(), before)

    def test_bad_archive_does_not_write(self):
        self.responses['1.zip'] = b'corrupt'
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            self.build()
        self.assertEqual(self.snapshot(), [[], [], []])

    def test_missing_recipe_stops_before_download(self):
        with self.assertRaisesRegex(ValueError, 'construction record is missing'):
            self.build(version='missing')
        self.storage.get_object.assert_not_called()

    def test_missing_revision_stops_before_download(self):
        with self.assertRaisesRegex(ValueError, 'revision does not exist'):
            self.build(revision='missing')
        self.storage.get_object.assert_not_called()


if __name__ == '__main__':
    unittest.main()
