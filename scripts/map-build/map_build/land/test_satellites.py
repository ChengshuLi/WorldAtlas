"""Check satellite assignment against complete WGS84 cell-center distances."""
import math
import random
import unittest

from pyproj import Geod

from map_build.core.distances import run_pair
from map_build.land.satellites import RunIndex, apply_satellites
from map_build.land.source_groups import apply_groups


class SatelliteTests(unittest.TestCase):
    def test_run_minimum_matches_all_cell_pairs_including_wrap_and_poles(self):
        geod = Geod(ellps='WGS84')
        rng = random.Random(41)
        for width, north in [(360, 90), (36000, 90), (36000, .1), (36000, -89.8)]:
            step = 360 / width
            for _ in range(12):
                y, yy = rng.randrange(10), rng.randrange(10)
                a, c = rng.randrange(width - 4), rng.randrange(width - 4)
                b, d = a + rng.randrange(1, 5), c + rng.randrange(1, 5)
                expected = min(geod.inv(-180 + (x + .5)*step, north - (y + .5)*step,
                                        -180 + (z + .5)*step, north - (yy + .5)*step)[2]
                               for x in range(a, b) for z in range(c, d))
                self.assertAlmostEqual(run_pair(y, a, b, yy, c, d, width, north)[0], expected, places=6)
        self.assertAlmostEqual(run_pair(89, 0, 2, 89, 358, 360, 360)[0],
                               geod.inv(-179.5, .5, 179.5, .5)[2], places=6)

    def test_index_includes_every_larger_parent_in_range(self):
        rng = random.Random(7)
        for width, north in [(360, 90), (36000, .1), (36000, -89.8)]:
            radius = 300000 if width == 360 else 5000
            runs = {root: [(rng.randrange(10), rng.choice([0, width - 6, width//2]), 0)]
                    for root in range(24)}
            runs = {root: [(y, a, a + rng.randrange(1, 6))] for root, [(y, a, _)] in runs.items()}
            components = {root: dict(total=b-a) for root, [(y, a, b)] in runs.items()}
            dy = math.ceil(radius / 6335439 * 180 / math.pi / (360 / width)) + 1
            index = RunIndex(runs, components, set(runs), width, north, radius, dy)
            for root, [(y, a, b)] in runs.items():
                nearby = index.nearby(root, runs[root], components)
                for parent, [(yy, c, d)] in runs.items():
                    if components[parent]['total'] > components[root]['total']:
                        distance = run_pair(y, a, b, yy, c, d, width, north)[0]
                        if distance <= radius:
                            self.assertIn((yy, c, d), nearby[parent][0])

    def test_direct_anchors_do_not_chain_through_inferred_satellites(self):
        runs = {100: [(0, 100, 103)], 200: [(0, 104, 106)], 300: [(0, 107, 108)]}
        components = {root: dict(total=b-a, in_scope=b-a) for root, [(_, a, b)] in runs.items()}
        result = dict(proposals={100: dict(code=301, basis='selected_affiliation')},
                      review={200: 'outside_line_latitude', 300: 'outside_line_latitude'})
        anchor = dict(code=301, source_id='points', source_version='1', source_feature_id='main',
                      source_sha256='a'*64, main_island_evidence='Selected named point.')
        output = apply_satellites(result, components, runs, {100: anchor}, run_pair,
                                  width=36000, north=.1, max_satellite_cells=2, max_gap_m=3000,
                                  tie_m=0, candidate_roots=set(runs), allow_anchored_over_unknown_nearer=True)
        self.assertEqual(output['proposals'][200]['code'], 301)
        self.assertNotIn(300, output['proposals'])
        self.assertEqual(output['review'][300], 'outside_line_latitude')

    def test_groups_preserve_explicit_claims_and_expose_conflicting_targets(self):
        result = dict(proposals={1: dict(code=301, basis='selected_affiliation'),
                                 2: dict(code=301, basis='whole_component_line_side')},
                      review={3: 'crosses_or_touches_line', 4: 'outside_line_latitude'})
        counts = {root: dict(total=2, in_scope=2) for root in range(1, 5)}
        windows = [dict(group_id='first', code=999, components=counts, source={}),
                   dict(group_id='other', code=707, components={2: counts[2]}, source={})]
        output = apply_groups(result, windows)
        self.assertEqual(output['proposals'][1]['code'], 301)
        self.assertIn(1, output['selected_group_conflicts'])
        self.assertEqual(output['review'][2], 'conflicting_regional_group_conventions')
        self.assertEqual(output['review'][3], 'crosses_or_touches_line')
        self.assertEqual(output['proposals'][4]['code'], 999)


if __name__ == '__main__':
    unittest.main()
