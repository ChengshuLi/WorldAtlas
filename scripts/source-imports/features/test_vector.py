import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from osgeo import ogr, osr

from features.geometry import geometry_hash, validate_geometry
from features.vector import dataset_path, read_features


class VectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'features.geojson'
        self.recipe = {'id_field': 'provider_id', 'selections': [
            {'feature_id': 'selected', 'source_feature_id': 'a',
             'expected_properties': {'name': 'First'}}]}
        self.write()

    def write(self, ids=('a', 'b')):
        self.path.write_text(json.dumps({'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'properties': {'provider_id': ident, 'name': 'First'},
             'geometry': {'type': 'Point', 'coordinates': [20 + i, 10]}}
            for i, ident in enumerate(ids)]}))

    def test_selected_point_and_identity(self):
        rows = read_features(self.path, self.recipe)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['geometry'], {'type': 'Point', 'coordinates': [20, 10]})
        self.assertEqual(rows[0]['source_feature_id'], 'a')
        self.recipe['selections'][0]['expected_geometry_sha256'] = geometry_hash(rows[0]['geometry'])
        self.assertEqual(read_features(self.path, self.recipe), rows)
        self.recipe['selections'][0]['expected_geometry_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'checksum'):
            read_features(self.path, self.recipe)

    def test_missing_duplicate_and_wrong_identity(self):
        self.write(('b',))
        with self.assertRaisesRegex(ValueError, 'missing'):
            read_features(self.path, self.recipe)
        self.write(('a', 'a'))
        with self.assertRaisesRegex(ValueError, 'duplicated'):
            read_features(self.path, self.recipe)
        self.write()
        self.recipe['selections'][0]['expected_properties']['name'] = 'Other'
        with self.assertRaisesRegex(ValueError, 'identity'):
            read_features(self.path, self.recipe)

    def test_projected_source_is_converted_with_xy_axis_order(self):
        path = self.path.with_suffix('.gpkg')
        source = ogr.GetDriverByName('GPKG').CreateDataSource(str(path))
        crs = osr.SpatialReference()
        crs.ImportFromEPSG(3857)
        layer = source.CreateLayer('points', crs, ogr.wkbPoint)
        layer.CreateField(ogr.FieldDefn('provider_id', ogr.OFTString))
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField('provider_id', 'a')
        geometry = ogr.Geometry(ogr.wkbPoint)
        geometry.AddPoint_2D(1113194.9079327357, 0)
        feature.SetGeometry(geometry)
        layer.CreateFeature(feature)
        source = None
        self.recipe['selections'][0].pop('expected_properties')
        result = read_features(path, self.recipe)[0]
        self.assertAlmostEqual(result['geometry']['coordinates'][0], 10)
        self.assertAlmostEqual(result['geometry']['coordinates'][1], 0)

    def test_archive_member_selection(self):
        path = self.path.with_suffix('.zip')
        with ZipFile(path, 'w') as archive:
            archive.write(self.path, 'nested/source.geojson')
        self.recipe['member'] = 'nested/source.geojson'
        self.assertEqual(read_features(path, self.recipe)[0]['geometry']['coordinates'], [20, 10])
        with self.assertRaisesRegex(ValueError, 'missing'):
            dataset_path(path, 'missing')
        with self.assertRaisesRegex(ValueError, 'non-archive'):
            dataset_path(self.path, 'member')

    def test_invalid_geometry_is_rejected(self):
        for geometry in ({'type': 'Point', 'coordinates': [float('nan'), 1]},
                         {'type': 'Point', 'coordinates': [1, 2, 3]},
                         {'type': 'Point', 'coordinates': [True, 2]},
                         {'type': 'Point', 'coordinates': ['1', 2]},
                         {'type': 'Point', 'coordinates': [181, 2]},
                         {'type': 'Point', 'coordinates': [1, -91]},
                         {'type': 'Polygon', 'coordinates': [[[0, 0], [1, 1], [0, 1], [1, 0], [0, 0]]]}):
            with self.subTest(geometry=geometry), self.assertRaises(ValueError):
                validate_geometry(geometry)
