from collections import Counter
from pathlib import Path
import random
import tempfile
import unittest

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import patch_rows, write_layer
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.land.connected import build_components
from worldatlas.map_build.land.seed_strips import SeedRules
from worldatlas.map_build.land.seeds import build_seeds
from worldatlas.map_build.land.test_regional import feature, polygon


class SeedStripTests(unittest.TestCase):
    def test_vectorized_runs_match_independent_cell_labels_with_twelve_regions(self):
        rng = random.Random(47)
        width, height = 40, 5
        rules = [
            dict(
                component_id=i * 17,
                region_id='r' + str(i),
                inside_code=300 + i * 29,
                outside_code=900 + i * 37,
            )
            for i in range(12)
        ]
        rules += [dict(component_id=9001, region_id=None, inside_code=77777, outside_code=77777)]
        masks = {
            r['region_id']: np.array(
                [[rng.randrange(2) for _ in range(width)] for _ in range(height)], dtype=bool
            )
            for r in rules
            if r['region_id'] is not None
        }
        offsets, records = [0], []
        expected = np.zeros((height, width), dtype=np.uint32)
        populations = {r['component_id']: [0, 0] for r in rules}
        for y in range(height):
            for x in range(0, width, 3):
                chosen = rules[(y * 14 + x // 3) % len(rules)]
                stop = min(x + 2, width)
                root = chosen['component_id']
                records.append((x, stop, root))
                for xx in range(x, stop):
                    inside = chosen['region_id'] is None or masks[chosen['region_id']][y, xx]
                    expected[y, xx] = chosen['inside_code' if inside else 'outside_code']
                    populations[root][0 if inside else 1] += 1
            offsets.append(len(records))
        index = SeedRules(rules)
        pairs, counts, inside, outside, categories = index.strip(
            masks, np.array(offsets), np.array(records), width, height
        )
        actual = np.zeros_like(expected)
        offset = 0
        for y, count in enumerate(counts):
            start = 0
            for end, code in pairs[offset : offset + count]:
                actual[y, start:end] = code
                start = end
            self.assertEqual(start, width)
            offset += count
        np.testing.assert_array_equal(actual, expected)
        self.assertEqual(
            list(zip(inside, outside)), [tuple(populations[r['component_id']]) for r in rules]
        )
        totals = Counter(map(int, expected.ravel()))
        self.assertEqual(
            dict(zip(map(int, index.codes), map(int, categories))),
            {int(code): totals[int(code)] for code in index.codes},
        )
        self.assertEqual(index.required_regions(np.array([[0, 1, 9001]])), set())

    def test_empty_strip_and_bad_component_or_rule_inputs(self):
        rule = dict(component_id=7, region_id=None, inside_code=301, outside_code=301)
        index = SeedRules([rule])
        pairs, counts, *_ = index.strip(
            {}, np.zeros(3, dtype=int), np.empty((0, 3), dtype=int), 8, 2
        )
        self.assertEqual(pairs.tolist(), [[8, 0], [8, 0]])
        self.assertEqual(counts.tolist(), [1, 1])
        for rules in [
            [rule, rule],
            [dict(rule, inside_code=0)],
            [dict(rule, inside_code=301.5)],
            [dict(rule, outside_code=999)],
        ]:
            with self.subTest(rules=rules), self.assertRaises(ValueError):
                SeedRules(rules)
        with self.assertRaisesRegex(ValueError, 'intervals'):
            index.strip({}, np.array([0, 2]), np.array([[1, 4, 7], [3, 5, 7]]), 8, 1)


class SeedBuildTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.grid = Grid(16, 8, 22.5)
        self.physical = np.ones((8, 16), dtype=np.uint32)
        self.physical[3, [3, 4, 10, 11]] = 17
        write_layer(
            self.root / 'physical',
            self.grid,
            patch_rows(self.physical, self.grid.bounds, self.grid),
        )
        build_components(self.grid, self.root / 'physical', self.root / 'components')
        self.features, witnesses = [], []
        for ident, lon, bounds in [
            ('west', -101.25, [-120, 0, -60, 30]),
            ('east', 56.25, [30, 0, 110, 30]),
        ]:
            point = feature(ident + '-point', dict(type='Point', coordinates=[lon, 11.25]))
            area = feature(ident + '-area', polygon(*bounds))
            self.features += [point, area]
            witnesses.append(
                dict(
                    witness_id=ident,
                    point_feature_id=point['feature_id'],
                    identity_feature_id=area['feature_id'],
                    radius_cells=0,
                    max_water_cells=0,
                )
            )
        divider = feature(
            'divider', dict(type='LineString', coordinates=[[-90.0, 45.0], [-90.0, -22.5]])
        )
        divider['boundary_id'] = 'divider'
        closure = feature(
            'closure',
            dict(
                type='LineString',
                coordinates=[[-90.0, -22.5], [-130.0, -22.5], [-130.0, 45.0], [-90.0, 45.0]],
            ),
        )
        closure.update(route_id='closure', closure_method='physical_water_closure_v1')
        self.domain = dict(
            features=self.features,
            mainland_witnesses=witnesses,
            mainland_witness_groups=[
                dict(
                    group_id='west',
                    role='mainland',
                    witness_ids=['west'],
                    target_entity_ids=[81, 42],
                ),
                dict(
                    group_id='east', role='mainland', witness_ids=['east'], target_entity_ids=[707]
                ),
            ],
            mainland_group_relations=[dict(group_ids=['west', 'east'], relation='different')],
            category_bindings=[
                dict(entity_id=entity, code=code, physical_class='land')
                for entity, code in [(81, 301), (42, 999), (707, 77)]
            ],
            mainland_boundaries=[divider],
            routes=[closure],
            seed_regions=[
                dict(
                    region_id='selected-region',
                    segments=[
                        dict(kind='boundary', id='divider', start=0, end=2, reverse=False),
                        dict(kind='route', id='closure', start=0, end=4, reverse=False),
                    ],
                    witnesses=[dict(lon=-101.25, lat=11.25, inside=True)],
                )
            ],
            mainland_component_rules=[
                dict(
                    rule_id='west-rule',
                    group_id='west',
                    region_id='selected-region',
                    inside_entity_id=81,
                    outside_entity_id=42,
                ),
                dict(
                    rule_id='east-rule',
                    group_id='east',
                    region_id=None,
                    inside_entity_id=707,
                    outside_entity_id=707,
                ),
            ],
            land_baseline_policy=dict(
                region_ids=['selected-region'], mainland_rule_ids=['west-rule', 'east-rule']
            ),
        )

    def components(self):
        return ComponentGrid(self.root / 'physical', self.root / 'components', self.grid)

    def test_imported_witnesses_and_ordered_regions_generate_seeds_once(self):
        with self.components() as components:
            result = build_seeds(
                self.domain, components, self.root / 'seeds', strip_rows=3, workers=2
            )
        self.assertEqual(result['category_cell_counts'], {'77': 2, '301': 1, '999': 1})
        self.assertEqual(result['groups']['west']['component_id'], 0)
        self.assertEqual(result['groups']['east']['component_id'], 1)
        with open_grid(self.root / 'seeds', self.grid) as data:
            ends, codes = row(data, 3, self.grid.width)
            self.assertEqual(ends.tolist(), [3, 4, 5, 10, 12, 16])
            self.assertEqual(codes.tolist(), [0, 301, 999, 0, 77, 0])

    def test_current_selection_uses_distinct_pairs_and_complete_lines(self):
        self.domain['distinct_groups'] = [item['group_ids'] for item in self.domain.pop('mainland_group_relations')]
        for region in self.domain['seed_regions']:
            for segment in region['segments']:
                segment.pop('start')
                segment.pop('end')
        with self.components() as components:
            result = build_seeds(self.domain, components, self.root / 'current-seeds', workers=1)
        self.assertEqual(result['category_cell_counts'], {'77': 2, '301': 1, '999': 1})

    def test_point_outside_identity_area_and_closure_crossing_land_fail_before_output(self):
        point = self.features[0]
        original = point['geometry']
        point['geometry'] = {'type': 'Point', 'coordinates': [170, -60]}
        with self.components() as components, self.assertRaisesRegex(ValueError, 'source identity'):
            build_seeds(self.domain, components, self.root / 'bad-identity')
        self.assertFalse((self.root / 'bad-identity').exists())
        point['geometry'] = original
        route = self.domain['routes'][0]
        route['geometry']['coordinates'] = [
            [-90.0, -22.5],
            [-101.25, 11.25],
            [-130.0, 45.0],
            [-90.0, 45.0],
        ]
        route['geometry_sha256'] = feature('route', route['geometry'])['geometry_sha256']
        with self.components() as components, self.assertRaisesRegex(
            ValueError, 'nonterminal land'
        ):
            build_seeds(self.domain, components, self.root / 'bad-route')
        self.assertFalse((self.root / 'bad-route').exists())


if __name__ == '__main__':
    unittest.main()
