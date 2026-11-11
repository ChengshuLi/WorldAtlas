import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from iho.s130 import extract_routes


GML = '''<root xmlns:s="http://www.iho.int/S130/2.0"
 xmlns:g="http://www.opengis.net/gml/3.2" xmlns:x="http://www.w3.org/1999/xlink">
 <s:ConstructionLine g:id="line-a"><s:lineType>Rhumb Line</s:lineType>
  <s:lineContributingLocation x:href="#point-a"/>
  <s:lineContributingLocation x:href="#point-b"/>
  <g:posList srsName="http://www.opengis.net/def/crs/EPSG/0/4326">10 20 20 30 30 40</g:posList>
 </s:ConstructionLine>
 <s:ContributingPoint g:id="point-a"><g:pos srsName="http://www.opengis.net/def/crs/EPSG/0/4326">10 20</g:pos></s:ContributingPoint>
 <s:ContributingPoint g:id="point-b"><g:pos srsName="http://www.opengis.net/def/crs/EPSG/0/4326">30 40.00000000000001</g:pos></s:ContributingPoint>
 <s:ConstructionLine g:id="line-b"><s:lineType>Rhumb Line</s:lineType>
  <s:lineContributingLocation x:href="#point-c"/>
  <g:posList srsName="http://www.opengis.net/def/crs/EPSG/0/4326">5 60 -60 60</g:posList>
 </s:ConstructionLine>
 <s:ContributingPoint g:id="point-c"><g:pos srsName="http://www.opengis.net/def/crs/EPSG/0/4326">5 60</g:pos></s:ContributingPoint>
</root>'''


def fixture(directory, gml=GML):
    raw = gml.encode()
    archive = Path(directory) / 'source.zip'
    with ZipFile(archive, 'w') as packed:
        packed.writestr('dataset.gml', raw)
    recipe = dict(method='s130_rhumb_routes', source_id='iho-test', source_version='1',
                  gml_member='dataset.gml', gml_sha256=hashlib.sha256(raw).hexdigest(),
                  max_step_km=0.05, basis='Extract the selected source lines in their chosen direction.',
                  routes=[dict(route_id='route-a', construction_line_id='line-a', reverse=True,
                               endpoint_names=['First', 'Second']),
                          dict(route_id='route-b', construction_line_id='line-b', reverse=False,
                               endpoint_names=['Third', 'Fourth'])])
    return archive, hashlib.sha256(archive.read_bytes()).hexdigest(), recipe


class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path, self.digest, self.recipe = fixture(self.temp.name)

    def extract(self, recipe=None):
        return extract_routes(self.path, self.digest, recipe or self.recipe)

    def test_reverse_preserves_line_coordinate_and_fraction(self):
        result = self.extract()
        endpoint = result['endpoints'][0]
        self.assertEqual((endpoint['name'], endpoint['latitude'], endpoint['longitude']),
                         ('First', '30', '40'))
        self.assertEqual(endpoint['evidence']['point_id'], 'point-b')
        self.assertEqual(endpoint['derivation']['longitude_fraction'], [40, 1])
        self.assertEqual(result['routes'][0]['points'][0]['endpoint_id'], 'route-a-endpoint-0')
        self.assertEqual(result['routes'][0]['parameters'], {'max_step_km': 0.05})

    def test_forward_line_can_have_only_one_contributing_point(self):
        result = self.extract()
        first, last = result['endpoints'][2:]
        self.assertEqual(first['evidence']['point_id'], 'point-c')
        self.assertEqual((last['latitude'], last['longitude']), ('-60', '60'))
        self.assertNotIn('point_id', last['evidence'])

    def test_existing_endpoint_ids_are_preserved(self):
        self.recipe['routes'][0]['endpoint_ids'] = ['existing-start', 'existing-end']
        result = self.extract()
        self.assertEqual([p['endpoint_id'] for p in result['routes'][0]['points']],
                         ['existing-start', 'existing-end'])
        self.assertEqual(result['endpoints'][0]['endpoint_id'], 'existing-start')

    def test_endpoint_ids_must_be_unique_and_nonempty(self):
        for ids in (['same', 'same'], ['', 'end'], ['start'], ['route-b-endpoint-0', 'end']):
            self.recipe['routes'][0]['endpoint_ids'] = ids
            with self.subTest(ids=ids), self.assertRaisesRegex(ValueError, 'endpoint IDs'):
                self.extract()

    def test_south_grid_rule_preserves_the_raw_coordinate(self):
        self.recipe['routes'][1]['extend_to_south_grid_edge'] = True
        endpoint = self.extract()['endpoints'][-1]
        self.assertEqual(endpoint['latitude'], '-60')
        self.assertEqual(endpoint['derivation']['latitude_fraction'], [-60, 1])
        self.assertEqual(endpoint['derivation']['method'], 'grid_south_edge')

    def test_south_grid_extension_requires_a_meridian(self):
        self.recipe['routes'][0]['extend_to_south_grid_edge'] = True
        with self.assertRaisesRegex(ValueError, 'requires a meridian'):
            self.extract()

    def test_wrong_archive_checksum(self):
        with self.assertRaisesRegex(ValueError, 'archive SHA-256'):
            extract_routes(self.path, '0' * 64, self.recipe)

    def test_wrong_gml_checksum(self):
        with self.assertRaisesRegex(ValueError, 'GML SHA-256'):
            self.extract(dict(self.recipe, gml_sha256='0' * 64))

    def test_missing_member(self):
        with self.assertRaisesRegex(ValueError, 'one GML archive member'):
            self.extract(dict(self.recipe, gml_member='missing.gml'))

    def test_missing_source_line(self):
        self.recipe['routes'][0]['construction_line_id'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'not an S-130 rhumb'):
            self.extract()

    def test_duplicate_route_selection(self):
        self.recipe['routes'].append(copy.deepcopy(self.recipe['routes'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate route'):
            self.extract()

    def test_invalid_sampling_step(self):
        for value in (0, 2, True, float('nan')):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'max_step_km'):
                self.extract(dict(self.recipe, max_step_km=value))

    def test_unknown_settings_are_rejected(self):
        self.recipe['routes'][0]['route_type'] = 'wgs84_geodesic'
        with self.assertRaisesRegex(ValueError, 'invalid S-130 route selection'):
            self.extract()

    def test_wrong_coordinate_system(self):
        self.path, self.digest, self.recipe = fixture(self.temp.name, GML.replace('EPSG/0/4326', 'EPSG/0/9999'))
        with self.assertRaisesRegex(ValueError, 'EPSG:4326'):
            self.extract()

    def test_invalid_coordinate(self):
        self.path, self.digest, self.recipe = fixture(self.temp.name, GML.replace('10 20 20 30', 'NaN 20 20 30'))
        with self.assertRaisesRegex(ValueError, 'invalid S-130 coordinate'):
            self.extract()

    def test_unsupported_line_type(self):
        self.path, self.digest, self.recipe = fixture(self.temp.name, GML.replace('Rhumb Line', 'Unknown'))
        with self.assertRaisesRegex(ValueError, 'not an S-130 rhumb'):
            self.extract()

    def test_duplicate_feature_id(self):
        self.path, self.digest, self.recipe = fixture(self.temp.name, GML.replace('g:id="point-b"', 'g:id="point-a"'))
        with self.assertRaisesRegex(ValueError, 'duplicate GML'):
            self.extract()


if __name__ == '__main__':
    unittest.main()
