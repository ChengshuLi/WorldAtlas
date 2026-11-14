import unittest

from worldatlas.map_build.inputs.features import selected_basins


def feature(ident, provider_id):
    return dict(
        feature_id=ident, source_id='provider', source_feature_id=provider_id,
        geometry={'type': 'Polygon', 'coordinates': [[[0, 0], [2, 0], [2, 2], [0, 0]]]},
        coordinate_reference='OGC:CRS84',
    )


def selection(*features):
    return {'features': list(features), 'basins': [
        dict(id='basin-' + f['feature_id'], feature_id=f['feature_id']) for f in features
    ]}


class SelectedFeatureTests(unittest.TestCase):
    def test_provider_names_do_not_collide_across_sources(self):
        domain = selection(feature('one', 'same'), feature('two', 'same'))
        domain['features'][1]['source_id'] = 'another-provider'
        self.assertEqual(len(selected_basins(domain)), 2)

    def test_wrong_geometry_type_and_coordinate_reference_are_rejected(self):
        domain = selection(feature('one', 'area'))
        domain['features'][0]['coordinate_reference'] = 'EPSG:3857'
        with self.assertRaisesRegex(ValueError, 'OGC:CRS84'):
            selected_basins(domain)
        domain['features'][0]['coordinate_reference'] = 'OGC:CRS84'
        domain['features'][0]['geometry'] = {'type': 'Point', 'coordinates': [0, 0]}
        with self.assertRaisesRegex(ValueError, 'geometry'):
            selected_basins(domain)

    def test_duplicate_provider_area_and_missing_feature_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'more than once'):
            selected_basins(selection(feature('one', 'same'), feature('two', 'same')))
        domain = selection(feature('one', 'area'))
        domain['basins'][0]['feature_id'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'missing'):
            selected_basins(domain)
