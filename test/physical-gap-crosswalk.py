"""Meaningful original/new shape, identity and uncertainty controls."""
import pathlib
import sys
import unittest
from shapely.geometry import box, mapping
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from geographic_components import components
from physical_gap_crosswalk import crosswalk, membership


def feature(identity, g, area=1):
    return {'type': 'Feature', 'id': identity, 'geometry': mapping(g),
            'properties': {'area_m2': area}}


def run(old, new):
    a, _ = components(old)
    b, _ = components(new)
    for row in b:
        row['id'] = 'physical-component:' + row['id'].split(':', 1)[1]
    return crosswalk(old, new, a, b)


class CrosswalkControls(unittest.TestCase):
    def test_water_split_to_whole_keeps_both_original_identities(self):
        result = run([feature('old-left', box(0, 0, 1, 1)), feature('old-right', box(2, 0, 3, 1))],
                     [feature('new-whole', box(0, 0, 3, 1))])
        self.assertEqual(len(result['old_fragments']), 2)
        self.assertEqual(len(result['new_fragments']), 1)
        self.assertEqual(len(result['fragment_pairs']), 2)
        added = result['new_fragments'][0]['difference']
        self.assertEqual(added['remaining_planar_area'], 1)
        self.assertEqual(len(added['atoms']), 1)
        self.assertEqual(len(result['components']), 3)

    def test_no_contact_retains_unmatched_original_and_new_shapes(self):
        result = run([feature('old', box(0, 0, 1, 1))], [feature('new', box(10, 0, 11, 1))])
        self.assertEqual(result['fragment_pairs'], [])
        self.assertEqual(result['old_fragments'][0]['pair_numbers'], [])
        self.assertEqual(result['new_fragments'][0]['difference']['remaining_planar_area'], 1)

    def test_point_contact_is_not_positive_area_correspondence(self):
        result = run([feature('old', box(0, 0, 1, 1))], [feature('new', box(1, 1, 2, 2))])
        self.assertEqual(result['fragment_pairs'][0]['kind'], 'point-only-contact')
        self.assertEqual(result['old_fragments'][0]['difference']['remaining_planar_area'], 1)

    def test_tiny_positive_shape_and_measurement_unknown_are_preserved(self):
        g = box(0, 0, 1e-12, 1e-12)
        result = run([feature('original-id', g, None)], [feature('new-id', g, None)])
        self.assertEqual(result['fragment_pairs'][0]['kind'], 'identical-coordinates')
        for kind in ('old_fragments', 'new_fragments'):
            self.assertTrue(result[kind][0]['unmeasured_original'])
            self.assertIsNone(result[kind][0]['original_area_m2'])
        self.assertNotEqual(result['components'][0]['component'], result['components'][1]['component'])

    def test_dateline_contact_keeps_shift_and_original_identities_explicit(self):
        result = run([feature('east', box(179, 0, 180, 1))], [feature('west', box(-180, 0, -179, 1))])
        pair = result['fragment_pairs'][0]
        self.assertEqual(pair['kind'], 'positive-length-contact')
        self.assertEqual(pair['new_shift_degrees'], 360)
        self.assertTrue(pair['dateline'])
        self.assertEqual(result['old_fragments'][0]['difference']['remaining_planar_area'], 1)

    def test_omitted_or_rehashed_component_membership_fails(self):
        f = feature('original', box(0, 0, 1, 1))
        rows, _ = components([f])
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            membership([f], [])
        rows[0]['properties']['fragment_bindings'][0]['feature_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'binding changed'):
            membership([f], rows)


if __name__ == '__main__':
    unittest.main()
