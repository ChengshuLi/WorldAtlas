import copy
import hashlib
import json
import unittest

from map_build.inputs.features import selected_basins


def feature(ident, provider_id, parents=()):
    geometry = {'type': 'Polygon', 'coordinates': [[[0, 0], [2, 0], [2, 2], [0, 0]]]}
    return dict(feature_id=ident, source_id='provider', source_version='edition',
                source_feature_id=provider_id, geometry=geometry, coordinate_reference='OGC:CRS84',
                geometry_sha256=hashlib.sha256(json.dumps(geometry, sort_keys=True,
                    separators=(',', ':')).encode()).hexdigest(),
                evidence={'source_parent_feature_ids': list(parents)})


def selection(*features):
    return {'features': list(features), 'basins': [
        dict(id='basin-'+f['feature_id'], feature_id=f['feature_id'],
             geometry_sha256=f['geometry_sha256']) for f in features]}


class SelectedFeatureTests(unittest.TestCase):
    def test_parent_and_child_are_rejected_even_when_their_assignments_agree(self):
        domain = selection(feature('whole', 'parent'), feature('part', 'child', ['parent']))
        with self.assertRaisesRegex(ValueError, 'provider parent'):
            selected_basins(domain)

    def test_provider_parent_names_do_not_collide_across_sources(self):
        domain = selection(feature('one', 'parent'), feature('two', 'child', ['parent']))
        domain['features'][1]['source_id'] = 'another-provider'
        self.assertEqual(len(selected_basins(domain)), 2)

    def test_geometry_edits_and_wrong_coordinate_reference_are_rejected(self):
        domain = selection(feature('one', 'parent'))
        changed = copy.deepcopy(domain)
        changed['features'][0]['geometry']['coordinates'][0][0][0] = 1
        with self.assertRaisesRegex(ValueError, 'checksum'):
            selected_basins(changed)
        domain['features'][0]['coordinate_reference'] = 'EPSG:3857'
        with self.assertRaisesRegex(ValueError, 'OGC:CRS84'):
            selected_basins(domain)

    def test_duplicate_provider_area_and_missing_feature_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'more than once'):
            selected_basins(selection(feature('one', 'parent'), feature('two', 'parent')))
        domain = selection(feature('one', 'parent'))
        domain['basins'][0]['feature_id'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'missing'):
            selected_basins(domain)
