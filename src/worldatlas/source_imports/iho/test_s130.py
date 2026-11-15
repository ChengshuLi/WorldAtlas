import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from worldatlas.source_imports.iho.s130 import extract_routes


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
    recipe = dict(method='s130_rhumb_routes', source_id='iho-test',
                  gml_member='dataset.gml', gml_sha256=hashlib.sha256(raw).hexdigest(),
                  max_step_km=1.0, basis='Extract the selected source lines in their chosen direction.',
                  routes=[dict(feature_id='route-a', construction_line_id='line-a', reverse=True),
                          dict(feature_id='route-b', construction_line_id='line-b', reverse=False)])
    return archive, hashlib.sha256(archive.read_bytes()).hexdigest(), recipe


class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path, self.digest, self.recipe = fixture(self.temp.name)

    def extract(self, recipe=None):
        return extract_routes(self.path, self.digest, recipe or self.recipe)

    def test_reverse_preserves_all_provider_vertices(self):
        feature=self.extract()[0]
        coordinates=feature['geometry']['coordinates']
        self.assertEqual(feature['feature_id'],'route-a')
        self.assertEqual(feature['source_feature_id'],'line-a')
        self.assertEqual(coordinates[0],[40,30])
        self.assertEqual(coordinates[-1],[20,10])
        self.assertIn([30,20],coordinates)

    def test_meridian_preserves_both_provider_endpoints(self):
        coordinates=self.extract()[1]['geometry']['coordinates']
        self.assertEqual(coordinates[0],[60,5])
        self.assertEqual(coordinates[-1],[60,-60])
        self.assertTrue(all(point[0]==60 for point in coordinates))

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
        with self.assertRaisesRegex(ValueError, 'distinct'):
            self.extract()

    def test_invalid_sampling_step(self):
        for value in (0, 2, True, float('nan')):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'max_step_km'):
                self.extract(dict(self.recipe, max_step_km=value))

    def test_unknown_settings_are_rejected(self):
        self.recipe['routes'][0]['route_type'] = 'wgs84_geodesic'
        with self.assertRaisesRegex(ValueError, 'invalid construction field: routes'):
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
