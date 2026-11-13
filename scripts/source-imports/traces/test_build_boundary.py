from contextlib import nullcontext
import hashlib
import json
import os
import unittest

import psycopg
from traces.build_boundary import build_boundary


@unittest.skipUnless(os.environ.get('WORLDATLAS_TEST_DATABASE_URL'),
                     'set WORLDATLAS_TEST_DATABASE_URL to a disposable database with the initial schema')
class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.database = psycopg.connect(os.environ['WORLDATLAS_TEST_DATABASE_URL'])
        self.addCleanup(self.database.close)
        self.addCleanup(self.database.rollback)
        self.database.execute(
            'INSERT INTO atlas.source_assets '
            '(source_id,version,title,provider,source_uri,license_name,license_uri,'
            'attribution,r2_bucket,r2_key,sha256,size_bytes,provenance) '
            "VALUES ('__trace_source','1','Test','Test','test:source','Test','test:license',"
            "'Test','test','figure.pdf',%s,10,'{}')", ('a' * 64,))
        self.recipe = dict(method='smooth_latitude_trace', source_id='__trace_source', source_version='1',
                           line_id='__trace_final', basis='Reviewed points from the source figure.',
                           points=[[10., 1.], [9., 0.], [8., -1.]],
                           step_latitude_degrees=.01, smoothing_latitude_degrees=.08)
        self.register('1', self.recipe)

    def register(self, version, recipe):
        text = json.dumps(recipe, sort_keys=True, separators=(',', ':'))
        self.database.execute('INSERT INTO atlas.structured_documents VALUES (%s,%s,%s,%s,%s::json)',
                              ('__trace_construction', version, hashlib.sha256(text.encode()).hexdigest(),
                               len(text.encode()), text))

    def build(self, version='1', expected=None):
        return build_boundary(self.database, '__trace_construction', version, expected)

    def row(self):
        return self.database.execute("SELECT line_id,source_id,source_version,geometry,geometry_sha256,coordinate_reference,provenance,construction_id,construction_version FROM atlas.geographic_line_observations "
                                     "WHERE line_id='__trace_final'").fetchone()

    def test_build_and_repeat(self):
        result = self.build()
        before = self.row()
        self.assertEqual(result['line_id'], '__trace_final')
        self.assertEqual(result['vertices'], 201)
        self.assertEqual(result['sha256'], before[4])
        self.assertEqual(before[7], '__trace_construction')
        self.assertEqual(self.build(), result)
        self.assertEqual(self.row(), before)

    def test_signed_zero_trace_hash_matches_saved_geometry(self):
        self.register('zero', dict(self.recipe, points=[[10., -0.0], [9., -1.]]))
        result = self.build('zero')
        geometry = self.row()[3]
        raw = json.dumps(geometry, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), result['sha256'])
        self.assertEqual(geometry['coordinates'][0], [10., 0.])

    def test_shared_entry_point_selects_trace_from_the_stored_method(self):
        from run_import import run_import
        result = run_import(lambda: nullcontext(self.database), '__trace_construction', '1')
        self.assertEqual(result['line_id'], '__trace_final')
        self.assertEqual(self.row()[4], result['sha256'])

    def test_new_points_update_final_boundary_and_retain_notes(self):
        self.build()
        before = self.row()
        self.database.execute("UPDATE atlas.geographic_line_observations "
                              "SET provenance=provenance || '{\"note\":\"keep\"}' "
                              "WHERE line_id='__trace_final'")
        self.register('2', dict(self.recipe, points=[[12., 1.], [11., 0.], [10., -1.]]))
        self.build('2')
        after = self.row()
        self.assertNotEqual(after[4], before[4])
        self.assertEqual(after[3]['coordinates'][0], [12., 1.])
        self.assertEqual(after[6]['note'], 'keep')
        self.assertEqual(after[8], '2')

    def test_description_fields_do_not_control_execution(self):
        self.register('2', dict(self.recipe, source_location='An additional source description.'))
        self.assertEqual(self.build('1'), self.build('2'))

    def test_expected_geometry_mismatch_does_not_write(self):
        self.build()
        before = self.row()
        with self.assertRaisesRegex(ValueError, 'expected geometry'):
            self.build(expected='0' * 64)
        self.assertEqual(self.row(), before)

    def test_unknown_source_does_not_write(self):
        self.register('2', dict(self.recipe, source_version='missing'))
        with self.assertRaisesRegex(ValueError, 'raw source version is missing'):
            self.build('2')
        self.assertIsNone(self.row())

    def test_invalid_points_do_not_write(self):
        self.register('2', dict(self.recipe, points=[[0, 0], [0, 1]]))
        with self.assertRaisesRegex(ValueError, 'north to south'):
            self.build('2')
        self.assertIsNone(self.row())

    def test_smoothing_outside_wgs84_leaves_existing_record_unchanged(self):
        self.build()
        before = self.row()
        self.register('invalid-output', dict(self.recipe, points=[[180., 2.], [179., 1.], [180., 0.]],
                                             smoothing_latitude_degrees=1.))
        with self.assertRaisesRegex(ValueError, 'smoothed trace'):
            self.build('invalid-output')
        self.assertEqual(self.row(), before)

    def test_unknown_method_does_not_write(self):
        self.register('2', dict(self.recipe, method='some.python.function'))
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            self.build('2')
        self.assertIsNone(self.row())

    def test_missing_record_does_not_write(self):
        with self.assertRaisesRegex(ValueError, 'construction record is missing'):
            self.build('missing')
        self.assertIsNone(self.row())


if __name__ == '__main__':
    unittest.main()
