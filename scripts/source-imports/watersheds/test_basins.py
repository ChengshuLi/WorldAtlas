from pathlib import Path
import tempfile
import unittest

import numpy as np
from pyproj import CRS
import shapefile
from shapely.geometry import LineString

from watersheds.terrain import Grid
from watersheds.drainage import destination_memberships
from watersheds.waterways import Basins, Waterways, seed_grid


class BasinTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'basins.shp'
        with shapefile.Writer(self.path, shapeType=shapefile.POLYGON) as layer:
            layer.field('DEST', 'N', decimal=0)
            for first, last, ident in [(0., 1., 100), (1., 2., 200)]:
                layer.poly([[(first, 0), (first, 2), (last, 2), (last, 0), (first, 0)]])
                layer.record(ident)
        self.path.with_suffix('.prj').write_text(CRS.from_epsg(4326).to_wkt())

    def basins(self, groups=None):
        return Basins([self.path], 'DEST', groups or {3: [100], 7: [200]}, [0, 0, 2, 2])

    def test_source_values_map_to_actual_construction_groups(self):
        basins = self.basins()
        self.assertEqual(basins.at((.5, 1)), 3)
        self.assertEqual(basins.at((1.5, 1)), 7)

    def test_polygon_boundary_and_missing_coverage_remain_unknown(self):
        basins = self.basins()
        self.assertEqual(basins.at((1, 1)), -1)
        self.assertEqual(basins.at((3, 1)), -1)

    def test_unmapped_source_basin_does_not_become_a_guessed_group(self):
        basins = self.basins({0: [100]})
        self.assertEqual(basins.at((.5, 1)), 0)
        self.assertEqual(basins.at((1.5, 1)), -1)
        self.assertEqual(basins.unmapped, [200])

    def test_source_values_cannot_be_assigned_to_two_groups(self):
        with self.assertRaisesRegex(ValueError, 'multiple drainage groups'):
            self.basins({3: [100], 7: [100, 200]})

    def test_terminal_way_beyond_shore_uses_its_last_actual_basin_intersection(self):
        line = LineString([(.5, 1.), (1.5, 1.), (3., 1.)])
        group, point = self.basins().exit_group(line)
        self.assertEqual(group, 7)
        self.assertEqual(point, (2., 1.))

    def test_unselected_downstream_basin_cannot_fall_back_to_an_upstream_group(self):
        basins = self.basins({3: [100]})
        for endpoint in (1.5, 3.):
            self.assertEqual(basins.exit_group(LineString([(.5, 1.), (endpoint, 1.)]))[0], -1)

    def test_uncovered_way_and_shared_basin_edge_stay_unknown(self):
        basins = self.basins()
        self.assertEqual(basins.exit_group(LineString([(3., 1.), (4., 1.)])), (-1, None))
        self.assertEqual(basins.exit_group(LineString([(1., 1.), (1., 3.)]))[0], -1)

    def test_only_domain_exits_receive_basin_fallback(self):
        grid = Grid(np.zeros((3, 3)), (0., .5, 0., 1.5, 0., -.5), 'EPSG:4326')
        terminals = self.basins().terminals(grid, np.full((3, 3), -1))
        self.assertEqual(terminals[0, 0], 3)
        self.assertEqual(terminals[1, 1], -1)

    def test_observed_ocean_creates_land_outlets_without_classifying_the_sea(self):
        grid = Grid(np.zeros((4, 4)), (0., .5, 0., 2., 0., -.5), 'EPSG:4326')
        ocean = np.zeros((4, 4), dtype=bool)
        ocean[0] = True
        outlets, labels = self.basins().coastal_outlets(grid, ocean)
        np.testing.assert_array_equal(outlets[:2], np.ones((2, 4), dtype=bool))
        self.assertFalse(outlets[2:].any())
        np.testing.assert_array_equal(labels[0], [-1, -1, -1, -1])
        np.testing.assert_array_equal(labels[1], [3, 3, 7, 7])
        # Interior zero heights do not become ocean or drainage outlets.
        np.testing.assert_array_equal(labels[2:], np.full((2, 4), -1))

    def test_coastal_outlet_without_source_basin_coverage_stays_unknown(self):
        grid = Grid(np.zeros((3, 3)), (3., .5, 0., 2., 0., -.5), 'EPSG:4326')
        ocean = np.zeros((3, 3), dtype=bool)
        ocean[0] = True
        _, labels = self.basins().coastal_outlets(grid, ocean)
        np.testing.assert_array_equal(labels, np.full((3, 3), -1))

    def test_uncovered_outlet_uses_the_first_basin_reached_along_its_upstream_flow(self):
        grid = Grid(np.zeros((1, 5)), (0., 1., 0., 1.5, 0., -1.), 'EPSG:4326')
        flow = np.array([[1, 2, 3, 4, -1]])
        exits = np.array([[False, False, False, False, True]])
        labels = np.full(flow.shape, -1)
        result, report = self.basins().uncovered_exits(grid, flow, exits, labels, destination_memberships(labels))
        self.assertEqual(result[0, 4], 7)
        self.assertEqual(report['resolved'][0]['basin_values'], [200])
        self.assertEqual(report['resolved'][0]['upstream_reference'], (1.5, 1.))
        np.testing.assert_array_equal(labels, np.full(flow.shape, -1))

    def test_conflicting_upstream_source_destinations_leave_the_outlet_unknown(self):
        grid = Grid(np.zeros((2, 3)), (0., 1., 0., 2., 0., -1.), 'EPSG:4326')
        # One incoming branch first reaches basin 100, the other basin 200.
        flow = np.array([[2, -1, -1], [-1, 5, 2]])
        exits = np.zeros(flow.shape, dtype=bool)
        exits[0, 2] = True
        labels = np.full(flow.shape, -1)
        result, report = self.basins().uncovered_exits(grid, flow, exits, labels, destination_memberships(labels))
        self.assertEqual(result[0, 2], -1)
        self.assertEqual(report['conflicting'][0]['groups'], [3, 7])

    def test_an_unselected_basin_at_the_coverage_frontier_is_not_skipped(self):
        grid = Grid(np.zeros((1, 4)), (0., 1., 0., 1.5, 0., -1.), 'EPSG:4326')
        flow = np.array([[1, 2, 3, -1]])
        exits = np.array([[False, False, False, True]])
        labels = np.full(flow.shape, -1)
        result, report = self.basins({3: [100]}).uncovered_exits(grid, flow, exits, labels, destination_memberships(labels))
        self.assertEqual(result[0, 3], -1)
        self.assertEqual(report['conflicting'][0]['basin_values'], [200])

    def test_an_unconnected_nearby_basin_does_not_classify_an_outlet(self):
        grid = Grid(np.zeros((1, 4)), (0., 1., 0., 1.5, 0., -1.), 'EPSG:4326')
        flow = np.full((1, 4), -1)
        exits = np.array([[False, False, False, True]])
        labels = np.full(flow.shape, -1)
        result, report = self.basins().uncovered_exits(grid, flow, exits, labels, destination_memberships(labels))
        self.assertEqual(result[0, 3], -1)
        self.assertEqual(report['unreferenced'], 1)

    def test_a_connected_mapped_river_identifies_an_uncovered_exit(self):
        grid = Grid(np.zeros((1, 3)), (3., 1., 0., 1.5, 0., -1.), 'EPSG:4326')
        flow = np.array([[1, 2, -1]])
        labels = np.full(flow.shape, -1)
        seeds = np.array([[12345, -1, -1]])
        exits = np.array([[False, False, True]])
        result, report = self.basins().uncovered_exits(grid, flow, exits, labels, destination_memberships(seeds))
        self.assertEqual(result[0, 2], 12345)
        self.assertEqual(report['resolved'][0]['basin_values'], [])

    def test_a_shared_river_reference_does_not_become_a_single_outlet_group(self):
        grid = Grid(np.zeros((1, 3)), (3., 1., 0., 1.5, 0., -1.), 'EPSG:4326')
        flow = np.array([[1, 2, -1]])
        labels = np.full(flow.shape, -1)
        seeds = {g: np.array([[True, False, False]]) for g in (3, 7)}
        exits = np.array([[False, False, True]])
        result, report = self.basins().uncovered_exits(grid, flow, exits, labels, seeds)
        self.assertEqual(result[0, 2], -1)
        self.assertEqual(report['conflicting'][0]['groups'], [3, 7])

    def test_disconnected_natural_networks_use_their_actual_exit_basins(self):
        path = self.root / 'rivers.osm'
        path.write_text('<osm><node id="1" lon="0.2" lat="1.5"/>'
                        '<node id="2" lon="0.3" lat="0.5"/>'
                        '<node id="3" lon="1.2" lat="1.5"/>'
                        '<node id="4" lon="1.3" lat="0.5"/>'
                        '<way id="10"><nd ref="1"/><nd ref="2"/>'
                        '<tag k="waterway" v="stream"/></way>'
                        '<way id="20"><nd ref="3"/><nd ref="4"/>'
                        '<tag k="waterway" v="stream"/></way></osm>')
        assigned, report = Waterways([path]).basin_groups(self.basins())
        self.assertEqual(assigned, {('1', '2'): (3,), ('3', '4'): (7,)})
        self.assertEqual(report['unassigned'], [])

    def test_fork_seeds_do_not_depend_on_osm_way_segmentation(self):
        nodes = ('<node id="1" lon="1" lat="1.75"/>'
                 '<node id="2" lon="1" lat="1"/>'
                 '<node id="3" lon="0.25" lat="0.25"/>'
                 '<node id="4" lon="1.75" lat="0.25"/>')

        def way(ident, members):
            return (f'<way id="{ident}">' + ''.join(f'<nd ref="{n}"/>' for n in members) +
                    '<tag k="waterway" v="stream"/></way>')

        grid = Grid(np.zeros((4, 4)), (0., .5, 0., 2., 0., -.5), 'EPSG:4326')
        seeds = []
        for name, parts in [('unsplit', [way(10, [1, 2, 3]), way(20, [2, 4])]),
                            ('split', [way(10, [1, 2]), way(11, [2, 3]), way(20, [2, 4])])]:
            path = self.root / (name + '.osm')
            path.write_text('<osm>' + nodes + ''.join(parts) + '</osm>')
            network = Waterways([path])
            assigned, report = network.basin_groups(self.basins())
            self.assertEqual(assigned, {('1', '2'): (3, 7), ('2', '3'): (3,), ('2', '4'): (7,)})
            self.assertIn('10', report['ambiguous'])
            seeds.append(seed_grid(network, assigned, grid)[0])
        for group in seeds[0]:
            np.testing.assert_array_equal(seeds[0][group], seeds[1][group])
        self.assertTrue(seeds[0][3][0, 2])
        self.assertTrue(seeds[0][7][0, 2])
        self.assertTrue(seeds[0][3][3, 0])
        self.assertTrue(seeds[0][7][3, 3])

    def test_splitting_at_an_ordinary_shape_node_keeps_the_same_seeds(self):
        nodes = ('<node id="1" lon="0.25" lat="1.75"/>'
                 '<node id="2" lon="0.25" lat="1"/>'
                 '<node id="3" lon="0.25" lat="0.25"/>')
        grid = Grid(np.zeros((4, 4)), (0., .5, 0., 2., 0., -.5), 'EPSG:4326')
        results = []
        for name, members in [('unsplit', [(1, 2, 3)]), ('split', [(1, 2), (2, 3)])]:
            body = ''.join('<way id="' + str(i) + '">' +
                           ''.join(f'<nd ref="{n}"/>' for n in part) +
                           '<tag k="waterway" v="stream"/></way>' for i, part in enumerate(members))
            path = self.root / (name + '.osm')
            path.write_text('<osm>' + nodes + body + '</osm>')
            network = Waterways([path])
            assigned, _ = network.basin_groups(self.basins())
            results.append(seed_grid(network, assigned, grid)[0])
        for group in results[0]:
            np.testing.assert_array_equal(results[0][group], results[1][group])

    def test_downstream_trace_can_cross_several_uncovered_estuary_ways(self):
        path = self.root / 'estuary.osm'
        path.write_text('<osm><node id="1" lon="0.5" lat="1"/>'
                        '<node id="2" lon="1.5" lat="1"/>'
                        '<node id="3" lon="3" lat="1"/>'
                        '<node id="4" lon="4" lat="1"/>'
                        '<way id="10"><nd ref="1"/><nd ref="2"/>'
                        '<tag k="waterway" v="river"/></way>'
                        '<way id="20"><nd ref="2"/><nd ref="3"/>'
                        '<tag k="waterway" v="river"/></way>'
                        '<way id="30"><nd ref="3"/><nd ref="4"/>'
                        '<tag k="waterway" v="river"/></way></osm>')
        network = Waterways([path])
        assigned, report = network.basin_groups(self.basins())
        self.assertEqual(assigned[('1', '2')], (7,))
        self.assertEqual(assigned[('2', '3')], (7,))
        self.assertIn({'way': '20', 'group': 7, 'point': [2., 1.]},
                      report['basin_exit_before_way_endpoint'])
        self.assertEqual(network.basin_groups(self.basins({3: [100]}))[0], {})

    def test_closed_waterway_cycle_does_not_gain_an_invented_destination(self):
        path = self.root / 'cycle.osm'
        path.write_text('<osm><node id="1" lon="0.2" lat="1"/>'
                        '<node id="2" lon="0.3" lat="1"/>'
                        '<way id="10"><nd ref="1"/><nd ref="2"/><nd ref="1"/>'
                        '<tag k="waterway" v="stream"/></way></osm>')
        assigned, report = Waterways([path]).basin_groups(self.basins())
        self.assertEqual(assigned, {})
        self.assertEqual(report['unassigned'], ['10'])


if __name__ == '__main__':
    unittest.main()
