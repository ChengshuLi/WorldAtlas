"""Official and candidate comparison streams share one immutable manifest."""
import os
import unittest
from unittest.mock import patch

import psycopg
from psycopg.types.json import Jsonb

from map_build.inputs.releases import read_release_streams


@unittest.skipUnless(os.environ.get('WORLDATLAS_TEST_DATABASE_URL'), 'requires disposable PostgreSQL')
class ReleaseLookupTests(unittest.TestCase):
    def test_candidate_then_official_lookup_and_release_protection(self):
        url = os.environ['WORLDATLAS_TEST_DATABASE_URL']
        with psycopg.connect(url, autocommit=True) as db:
            objects = {stream + '.u32le.gz': dict(r2_key='test/' + stream, sha256='a' * 64,
                       size_bytes=12, content_type='application/gzip') for stream in ('rows', 'runs')}
            manifest = dict(objects=objects, decoded_sha256=dict(rows='b' * 64, runs='c' * 64))
            try:
                db.execute('INSERT INTO atlas.map_releases(release_id,r2_bucket,manifest) VALUES (%s,%s,%s)',
                           ('v97.0-rc1', 'test', Jsonb(manifest)))
                with patch.dict(os.environ, NEON_DATABASE_URL=url):
                    candidate = read_release_streams('v97.0-rc1')
                    self.assertEqual([row[0] for row in candidate], ['rows', 'runs'])
                    self.assertEqual(candidate[0][1:4], ('test', 'test/rows', 12))
                    with self.assertRaisesRegex(ValueError, 'missing row or run'):
                        read_release_streams('v97.0')
                    db.execute("UPDATE atlas.map_releases SET approved_by='Reviewer',approved_at=now() WHERE release_id='v97.0-rc1'")
                    db.execute("INSERT INTO atlas.map_publications VALUES ('v97.0','v97.0-rc1',NULL)")
                    self.assertEqual(read_release_streams('v97.0'), candidate)
                    with self.assertRaises(psycopg.errors.ForeignKeyViolation):
                        db.execute("DELETE FROM atlas.map_releases WHERE release_id='v97.0-rc1'")
            finally:
                db.execute("DELETE FROM atlas.map_publications WHERE map_version='v97.0'")
                db.execute("DELETE FROM atlas.map_releases WHERE release_id='v97.0-rc1'")
