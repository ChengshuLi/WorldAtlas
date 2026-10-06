"""Before-water discovery controls, using independently specified geometries."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from shapely.geometry import box, GeometryCollection, LineString, Point, Polygon
from physical_gap_audit import DOMAIN, Detector, bad_record, split_result


def inputs(land, locations=(), water=(), invalid_water=(), invalid_land=()):
    return {'land': list(land), 'locations': list(locations), 'water': list(water),
            'land_metadata': [{'id': 'land-reference:' + str(i), 'input_path': 'original-land'}
                              for i in range(len(land))],
            'invalid_land': list(invalid_land), 'invalid_locations': [], 'invalid_water': list(invalid_water),
            'location_metadata': [{'id': str(i)} for i in range(len(locations))],
            'water_metadata': [{'id': str(i)} for i in range(len(water))]}


class BeforeWaterControls(unittest.TestCase):
    def test_lake_overlap_cannot_hide_gap(self):
        gap = box(4, 0, 6, 10)
        detector = Detector(inputs([box(0, 0, 10, 10)],
                                   [box(0, 0, 4, 10), box(6, 0, 10, 10)], [gap]))
        result = detector.tile((0, 0, 10, 10))
        self.assertEqual(result['status'], 'checked')
        self.assertEqual(len(result['candidates']), 1)
        self.assertTrue(result['candidates'][0].equals_exact(gap, 0, normalize=True))
        diagnostics = detector.water_diagnostics(result['candidates'][0])
        self.assertEqual(diagnostics[0]['planar_area'], 20)
        self.assertEqual(diagnostics[0]['status'], 'reference-overlap-unverified-water')
        self.assertEqual([x['kind'] for x in detector.contacts(gap)], ['positive-length-boundary'] * 2)

    def test_invalid_water_is_diagnostic_not_blocker(self):
        bad = {'id': 'invalid-lake', 'unchecked_bounds': [0, 0, 10, 10]}
        result = Detector(inputs([box(0, 0, 10, 10)], invalid_water=[bad])).tile((0, 0, 10, 10))
        self.assertEqual(result['status'], 'checked')
        self.assertEqual(result['candidates'][0].area, 100)
        self.assertEqual(result['invalid_water_diagnostics'], [bad])

    def test_invalid_land_retains_exact_unchecked_tile(self):
        bad = {'id': 'invalid-land', 'unchecked_bounds': [0, 0, 1, 1]}
        detector = Detector(inputs([], invalid_land=[bad]))
        self.assertEqual(detector.tile((0, 0, 5, 5))['blocked_sources'], [bad])
        self.assertEqual(detector.tile((5, 5, 10, 10))['status'], 'checked')

    def test_every_nonempty_atom_is_retained(self):
        tiny = box(0, 0, 1e-12, 1e-12)
        line, point = LineString([(2, 0), (2, 1)]), Point(3, 0)
        candidates, residues = split_result(GeometryCollection([tiny, line, point]))
        self.assertEqual(len(candidates), 1)
        self.assertGreater(candidates[0].area, 0)
        self.assertEqual([x.geom_type for x in residues], ['LineString', 'Point'])

    def test_physical_hole_and_location_hole_remain_distinct(self):
        physical = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)],
                           [[(4, 4), (6, 4), (6, 6), (4, 6)]])
        location = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)],
                           [[(2, 2), (8, 2), (8, 8), (2, 8)]])
        result = Detector(inputs([physical], [location])).tile((0, 0, 10, 10))
        self.assertEqual(sum(x.area for x in result['candidates']), 32)
        self.assertFalse(any(x.contains(Point(5, 5)) for x in result['candidates']))
        self.assertTrue(any(x.contains(Point(3, 3)) for x in result['candidates']))

    def test_touching_tile_clips_are_retained_residues(self):
        result = Detector(inputs([box(0, 0, 1, 1)])).tile((1, 0, 2, 1))
        self.assertEqual(result['candidates'], [])
        self.assertTrue(any(x['stage'] == 'physical-land-clipping' and
                            x['geometry']['type'] == 'LineString' for x in result['residues']))
        self.assertEqual(result['residues'][1]['source']['id'], 'land-reference:0')

    def test_no_contact_does_not_invent_neighbor(self):
        detector = Detector(inputs([box(0, 0, 10, 10)], [box(20, 20, 21, 21)]))
        self.assertEqual(detector.contacts(box(0, 0, 10, 10)), [])

    def test_tile_split_preserves_whole_candidate_and_point_contact(self):
        from shapely import union_all
        detector = Detector(inputs([box(0, 0, 10, 10)], [box(10, 10, 11, 11)]))
        pieces = detector.tile((0, 0, 5, 10))['candidates'] + detector.tile((5, 0, 10, 10))['candidates']
        self.assertTrue(union_all(pieces).equals(box(0, 0, 10, 10)))
        self.assertEqual(detector.contacts(box(0, 0, 10, 10))[0]['kind'], 'point-only-ambiguous')

    def test_dateline_islands_keep_original_coordinates(self):
        east, west = box(179, 0, 180, 1), box(-180, 0, -179, 1)
        detector = Detector(inputs([east, west]))
        a = detector.tile((175, 0, 180, 5))['candidates']
        b = detector.tile((-180, 0, -175, 5))['candidates']
        self.assertEqual(sum(g.area for g in a + b), 2)
        self.assertTrue(a[0].equals_exact(east, 0, normalize=True))
        self.assertTrue(b[0].equals_exact(west, 0, normalize=True))

    def test_original_shore_on_tile_edge_is_not_removed(self):
        detector = Detector(inputs([box(0, 0, 10, 10)]))
        whole = detector.tile((0, 0, 10, 10))
        self.assertTrue(whole['physical_shore'].equals(box(0, 0, 10, 10).boundary))
        interior = detector.tile((2, 2, 8, 8))
        self.assertTrue(interior['physical_shore'].is_empty)

    def test_nonfinite_vertex_blocks_domain_even_with_finite_bounds(self):
        g = Polygon([(0, 0), (1, 0), (1, 1), (float('nan'), 1), (0, 0)])
        self.assertTrue(all(__import__('math').isfinite(x) for x in g.bounds))
        for identity in ['land-reference:0', 'location:0']:
            bad = bad_record(identity, g, 'invalid-nonfinite-coordinate', 'original-source')
            self.assertEqual(bad['unchecked_bounds'], list(DOMAIN))
            detector = Detector(inputs([], invalid_land=[bad]))
            self.assertEqual(detector.tile((90, 30, 95, 35))['status'], 'unchecked')


if __name__ == '__main__':
    unittest.main()
