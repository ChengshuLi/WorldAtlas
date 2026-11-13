from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from features.geometry import geometry_hash
from features.points import read_points


class PointTableTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'points.tsv'
        self.path.write_text('id\tname\tlon\tlat\n2\tSecond\t-20.25\t11.5\n1\tFirst\t5.5\t-2.25\n')
        self.settings = {'delimiter': '\t', 'id_field': 'id', 'longitude_field': 'lon',
                         'latitude_field': 'lat', 'coordinate_reference': 'OGC:CRS84',
                         'selections': [dict(feature_id='point-one', source_feature_id='1',
                                             expected_properties={'name': 'First'}),
                                        dict(feature_id='point-two', source_feature_id='2')]}

    def test_header_table_is_selected_by_identity_in_requested_order(self):
        features = read_points(self.path, self.settings)
        self.assertEqual([f['feature_id'] for f in features], ['point-one', 'point-two'])
        self.assertEqual(features[0]['geometry'], {'type': 'Point', 'coordinates': [5.5, -2.25]})
        self.assertEqual(features[1]['evidence']['provider_properties']['name'], 'Second')
        self.settings['selections'][0]['expected_geometry_sha256'] = geometry_hash(features[0]['geometry'])
        self.assertEqual(read_points(self.path, self.settings), features)

    def test_expected_hash_matches_stored_zero_but_still_detects_changed_coordinates(self):
        self.path.write_text('id\tname\tlon\tlat\n1\tFirst\t-0.0\t1e-24\n')
        self.settings['selections'] = self.settings['selections'][:1]
        canonical = b'{"coordinates":[0.0,1e-24],"type":"Point"}'
        self.settings['selections'][0]['expected_geometry_sha256'] = hashlib.sha256(canonical).hexdigest()
        self.assertEqual(read_points(self.path, self.settings)[0]['geometry']['coordinates'], [-0.0, 1e-24])
        self.path.write_text(self.path.read_text().replace('1e-24', '2e-24'))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            read_points(self.path, self.settings)

    def test_filtered_selection_keeps_explicit_points_outside_its_bounds(self):
        self.path.write_text('id\tname\tlon\tlat\tkind\n'
                             '2\tOutside\t-20.25\t11.5\tisland\n'
                             '3\tNew\t6\t-2\tisland\n'
                             '4\tWrong kind\t7\t-3\tcity\n'
                             '1\tFirst\t5.5\t-2.25\tisland\n')
        settings = dict(self.settings, where={'kind': 'island'}, feature_id_prefix='island-',
                        bounds_lon_lat=[0, -10, 10, 0])
        self.assertEqual([f['feature_id'] for f in read_points(self.path, settings)],
                         ['point-one', 'point-two', 'island-3'])
        settings['selections'] = []
        self.assertEqual([f['feature_id'] for f in read_points(self.path, settings)], ['island-1', 'island-3'])
        settings['where'] = {'missing': 'island'}
        with self.assertRaisesRegex(ValueError, 'filter columns'):
            read_points(self.path, settings)

    def test_headerless_archive_uses_explicit_column_names_and_member(self):
        archive = self.path.with_suffix('.zip')
        with ZipFile(archive, 'w') as output:
            output.writestr('records.txt', '1\tFirst\t5.5\t-2.25\n2\tSecond\t-20.25\t11.5\n')
            output.writestr('readme.txt', 'Provider documentation')
        self.settings.update(columns=['id', 'name', 'lon', 'lat'], member='records.txt')
        features = read_points(archive, self.settings)
        self.assertEqual(features[1]['geometry']['coordinates'], [-20.25, 11.5])
        self.settings['member'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'archive member'):
            read_points(archive, self.settings)

    def test_missing_duplicate_and_changed_identity_are_rejected(self):
        cases = [('id\tname\tlon\tlat\n1\tFirst\t5.5\t2\n', 'missing'),
                 ('id\tname\tlon\tlat\n1\tFirst\t5.5\t2\n1\tFirst\t5.5\t2\n', 'duplicated'),
                 ('id\tname\tlon\tlat\n1\tWrong\t5.5\t2\n', 'identity'),
                 ('id\tname\tlon\tlat\n1\tFirst\t5.5\t2\textra\n', 'number of columns')]
        for contents, reason in cases:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                self.path.write_text(contents)
                read_points(self.path, self.settings)

    def test_coordinate_and_schema_errors_are_rejected(self):
        self.settings['selections'] = self.settings['selections'][:1]
        for lon, lat in [('nan', '0'), ('0', 'inf'), ('181', '0'), ('0', '-91'), ('unknown', '0')]:
            with self.subTest(lon=lon, lat=lat), self.assertRaises(ValueError):
                self.path.write_text(f'id\tname\tlon\tlat\n1\tFirst\t{lon}\t{lat}\n')
                read_points(self.path, self.settings)
        for update in ({'columns': ['id', 'id', 'lon', 'lat']},
                       {'longitude_field': 'missing'}, {'coordinate_reference': 'unknown'}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                read_points(self.path, dict(self.settings, **update))

    def test_checksum_and_duplicate_selection_are_rejected(self):
        self.settings['selections'][0]['expected_geometry_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'checksum'):
            read_points(self.path, self.settings)
        settings = deepcopy(self.settings)
        settings['selections'] *= 2
        with self.assertRaisesRegex(ValueError, 'unique'):
            read_points(self.path, settings)


if __name__ == '__main__':
    unittest.main()
