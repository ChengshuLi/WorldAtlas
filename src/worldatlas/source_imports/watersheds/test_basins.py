"""Test how the basin map gives drainage groups to streams and outlets."""

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from osgeo import gdal
from shapely.geometry import LineString, box

from worldatlas.source_imports.watersheds.terrain import Grid
from worldatlas.source_imports.watersheds.basins import Basins
from worldatlas.source_imports.watersheds.waterways import Waterways, rasterize_waterway_destinations


def write_basin_shapefile(path, attribute, polygons, *, crs='EPSG:4326'):
    """Write test basin polygons and their provider IDs with GDAL.

    Args:
        path: Destination Shapefile path in the fixture directory.
        attribute: Provider field that identifies a basin.
        polygons: Pairs of basin IDs and Shapely polygons in longitude and latitude.
        crs: Coordinate reference for the written Shapefile.
    """
    geojson = path.with_suffix('.geojson')
    geojson.write_text(json.dumps({'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': {attribute: ident}, 'geometry': polygon.__geo_interface__}
        for ident, polygon in polygons
    ]}))
    gdal.VectorTranslate(str(path), str(geojson), format='ESRI Shapefile', dstSRS=crs,
                         accessMode='overwrite').Close()


class BasinTests(unittest.TestCase):
    """Use small basin maps to check what the source can tell us about each outlet."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'basins.shp'
        write_basin_shapefile(self.path, 'DEST', [(100, box(0, 0, 1, 2)), (200, box(1, 0, 2, 2))])

    def basins(self, groups=None):
        """Index the two fixture basins.

        Args:
            groups: Optional recipe mapping that replaces the usual two groups.

        Returns:
            A basin index for both fixture polygons.
        """
        return Basins([self.path], 'DEST', groups or {3: [100], 7: [200]}, [0, 0, 2, 2])

    def test_source_values_map_to_actual_construction_groups(self):
        basins = self.basins()
        self.assertEqual(basins.group_at_point((.5, 1)), 3)
        self.assertEqual(basins.group_at_point((1.5, 1)), 7)

    def test_each_known_group_requires_a_nonnegative_id_and_source_values(self):
        for groups in ({}, {-1: [100]}, {3: []}):
            with self.subTest(groups=groups), self.assertRaisesRegex(ValueError, 'known group IDs'):
                Basins([self.path], 'DEST', groups, [0, 0, 2, 2])

    def test_distinct_drainage_groups_cannot_use_aliases_for_one_id(self):
        with self.assertRaisesRegex(ValueError, 'equivalent numeric drainage group IDs'):
            self.basins({'3': [100], '03': [200]})

    def test_basin_source_requires_one_georeferenced_layer(self):
        path = self.root / 'basins.gpkg'
        with gdal.GetDriverByName('GPKG').Create(str(path), 0, 0, 0, gdal.GDT_Unknown) as dataset:
            dataset.CreateLayer('first')
            dataset.CreateLayer('second')
        with self.assertRaisesRegex(ValueError, 'requires one vector layer'):
            Basins([path], 'DEST', {3: [100]}, [0, 0, 2, 2])
        # Shapefile stores its coordinate reference in a separate file.
        self.path.with_suffix('.prj').unlink()
        with self.assertRaisesRegex(ValueError, 'requires its coordinate reference'):
            self.basins()

    def test_projected_basin_source_uses_wgs84_bounds_and_lookup_points(self):
        path = self.root / 'projected.shp'
        write_basin_shapefile(path, 'DEST', [(100, box(0, 0, 1, 2)), (200, box(3, 0, 4, 2))],
                             crs='EPSG:3857')
        basins = Basins([path], 'DEST', {3: [100], 7: [200]}, [0, 0, 2, 2])
        self.assertEqual(basins.group_at_point((.5, 1)), 3)
        self.assertEqual(basins.values, [100])

    def test_polygon_boundary_and_missing_coverage_remain_unknown(self):
        basins = self.basins()
        self.assertEqual(basins.group_at_point((1, 1)), -1)
        self.assertEqual(basins.group_at_point((3, 1)), -1)

    def test_unmapped_source_basin_does_not_become_a_guessed_group(self):
        basins = self.basins({0: [100]})
        self.assertEqual(basins.group_at_point((.5, 1)), 0)
        self.assertEqual(basins.group_at_point((1.5, 1)), -1)

    def test_fork_outside_coverage_does_not_inherit_a_group_from_an_unselected_basin(self):
        path = self.root / 'river.osm'
        path.write_text('<osm version="0.6"><node id="1" lon="1.5" lat="1"/>'
                        '<node id="2" lon="3" lat="1"/><node id="3" lon="4" lat="1.5"/>'
                        '<node id="4" lon="4" lat="0.5"/>'
                        '<way id="10"><nd ref="1"/><nd ref="2"/><tag k="waterway" v="stream"/></way>'
                        '<way id="20"><nd ref="2"/><nd ref="3"/><tag k="waterway" v="stream"/></way>'
                        '<way id="30"><nd ref="2"/><nd ref="4"/><tag k="waterway" v="stream"/></way></osm>')
        assigned, report = Waterways([path]).trace_destinations_from_basins(self.basins({3: [100]}))
        self.assertEqual(assigned, {})
        self.assertEqual(report['basin_exit_before_way_endpoint'], [])
        self.assertEqual(set(report['unassigned']), {'10', '20', '30'})

    def test_stream_ending_inside_an_unselected_basin_has_no_group(self):
        path = self.root / 'river.osm'
        path.write_text('<osm version="0.6"><node id="1" lon="0.5" lat="1"/>'
                        '<node id="2" lon="1.5" lat="1"/>'
                        '<way id="10"><nd ref="1"/><nd ref="2"/><tag k="waterway" v="stream"/></way></osm>')
        assigned, report = Waterways([path]).trace_destinations_from_basins(self.basins({3: [100]}))
        self.assertEqual(assigned, {})
        self.assertEqual(report['unassigned'], ['10'])

    def test_source_values_cannot_be_assigned_to_two_groups(self):
        with self.assertRaisesRegex(ValueError, 'multiple drainage groups'):
            self.basins({3: [100], 7: [100, 200]})

    def test_terminal_way_beyond_shore_uses_its_last_actual_basin_intersection(self):
        line = LineString([(.5, 1.), (1.5, 1.), (3., 1.)])
        group, point = self.basins().river_exit_group_and_point(line)
        self.assertEqual(group, 7)
        self.assertEqual(point, (2., 1.))

    def test_unselected_downstream_basin_cannot_fall_back_to_an_upstream_group(self):
        basins = self.basins({3: [100]})
        for endpoint in (1.5, 3.):
            self.assertEqual(basins.river_exit_group_and_point(LineString([(.5, 1.), (endpoint, 1.)]))[0], -1)

    def test_uncovered_way_and_shared_basin_edge_stay_unknown(self):
        basins = self.basins()
        self.assertEqual(basins.river_exit_group_and_point(LineString([(3., 1.), (4., 1.)])), (-1, None))
        self.assertEqual(basins.river_exit_group_and_point(LineString([(1., 1.), (1., 3.)]))[0], -1)

    def test_only_domain_exits_receive_basin_fallback(self):
        grid = Grid(np.zeros((3, 3)), (0., .5, 0., 1.5, 0., -.5), 'EPSG:4326')
        terminals = self.basins().classify_crop_exits(grid, np.full((3, 3), -1))
        self.assertEqual(terminals[0, 0], 3)
        self.assertEqual(terminals[1, 1], -1)

    def test_batched_outlet_lookup_keeps_a_shared_edge_with_an_unselected_basin_unknown(self):
        grid = Grid(np.zeros((1, 3)), (.25, .5, 0., 1.5, 0., -1.), 'EPSG:4326')
        labels = self.basins({3: [100]}).classify_crop_exits(grid, np.full((1, 3), -1))
        np.testing.assert_array_equal(labels, [[3, -1, -1]])

    def test_observed_ocean_creates_land_outlets_without_classifying_the_sea(self):
        grid = Grid(np.zeros((4, 4)), (0., .5, 0., 2., 0., -.5), 'EPSG:4326')
        ocean = np.zeros((4, 4), dtype=bool)
        ocean[0] = True
        outlets, labels = self.basins().classify_coastal_outlets(grid, ocean)
        np.testing.assert_array_equal(outlets[:2], np.ones((2, 4), dtype=bool))
        self.assertFalse(outlets[2:].any())
        np.testing.assert_array_equal(labels[0], [-1, -1, -1, -1])
        np.testing.assert_array_equal(labels[1], [3, 3, 7, 7])
        # Interior zero heights do not become ocean or drainage outlets.
        np.testing.assert_array_equal(labels[2:], np.full((2, 4), -1))

    def test_corner_ocean_reaches_diagonal_shore_without_wrapping(self):
        grid = Grid(np.zeros((4, 4)), (0., .5, 0., 2., 0., -.5), 'EPSG:4326')
        ocean = np.zeros((4, 4), dtype=bool)
        ocean[0, 0] = True
        outlets, labels = self.basins().classify_coastal_outlets(grid, ocean)
        expected = np.zeros_like(ocean)
        expected[:2, :2] = True
        np.testing.assert_array_equal(outlets, expected)
        self.assertEqual(labels[1, 1], 3)
        self.assertEqual(labels[0, 0], -1)

    def test_coastal_outlet_without_source_basin_coverage_stays_unknown(self):
        grid = Grid(np.zeros((3, 3)), (3., .5, 0., 2., 0., -.5), 'EPSG:4326')
        ocean = np.zeros((3, 3), dtype=bool)
        ocean[0] = True
        _, labels = self.basins().classify_coastal_outlets(grid, ocean)
        np.testing.assert_array_equal(labels, np.full((3, 3), -1))

    def test_coastal_outlet_inputs_must_match_the_terrain_and_flow(self):
        basins = self.basins()
        grid = Grid(np.zeros((1, 2)), (0., .5, 0., 2., 0., -.5), 'EPSG:4326')
        with self.assertRaisesRegex(ValueError, 'ocean mask and terrain grid must match'):
            basins.classify_coastal_outlets(grid, [[True]])
        flow, labels = np.array([[1, -1]]), np.array([[-1, -1]])
        with self.assertRaisesRegex(ValueError, 'must share one grid'):
            basins.classify_uncovered_outlets(grid, flow, [[True]], labels, {})
        with self.assertRaisesRegex(ValueError, 'must be flow terminals'):
            basins.classify_uncovered_outlets(grid, flow, [[True, False]], labels, {})

    def test_uncovered_outlet_uses_the_first_basin_reached_along_its_upstream_flow(self):
        grid = Grid(np.zeros((1, 5)), (0., 1., 0., 1.5, 0., -1.), 'EPSG:4326')
        flow = np.array([[1, 2, 3, 4, -1]])
        exits = np.array([[False, False, False, False, True]])
        labels = np.full(flow.shape, -1)
        result, report = self.basins().classify_uncovered_outlets(grid, flow, exits, labels, {})
        self.assertEqual(result[0, 4], 7)
        self.assertEqual(report['resolved'][0]['basin_values'], [200])
        self.assertEqual(report['resolved'][0]['upstream_reference'], (1.5, 1.))
        np.testing.assert_array_equal(labels, np.full(flow.shape, -1))

    def test_conflicting_upstream_source_destinations_leave_the_outlet_unknown(self):
        grid = Grid(np.zeros((2, 3)), (0., 1., 0., 2., 0., -1.), 'EPSG:4326')
        # Water reaches this outlet from basins 100 and 200, which belong
        # to different groups. The outlet should stay unknown.
        flow = np.array([[2, -1, -1], [-1, 5, 2]])
        exits = np.zeros(flow.shape, dtype=bool)
        exits[0, 2] = True
        labels = np.full(flow.shape, -1)
        result, report = self.basins().classify_uncovered_outlets(grid, flow, exits, labels, {})
        self.assertEqual(result[0, 2], -1)
        self.assertEqual(report['conflicting'][0]['groups'], [3, 7])

    def test_an_unselected_basin_at_the_coverage_frontier_is_not_skipped(self):
        grid = Grid(np.zeros((1, 4)), (0., 1., 0., 1.5, 0., -1.), 'EPSG:4326')
        flow = np.array([[1, 2, 3, -1]])
        exits = np.array([[False, False, False, True]])
        labels = np.full(flow.shape, -1)
        result, report = self.basins({3: [100]}).classify_uncovered_outlets(grid, flow, exits, labels, {})
        self.assertEqual(result[0, 3], -1)
        self.assertEqual(report['conflicting'][0]['basin_values'], [200])

    def test_an_unconnected_nearby_basin_does_not_classify_an_outlet(self):
        grid = Grid(np.zeros((1, 4)), (0., 1., 0., 1.5, 0., -1.), 'EPSG:4326')
        flow = np.full((1, 4), -1)
        exits = np.array([[False, False, False, True]])
        labels = np.full(flow.shape, -1)
        result, report = self.basins().classify_uncovered_outlets(grid, flow, exits, labels, {})
        self.assertEqual(result[0, 3], -1)
        self.assertEqual(report['unreferenced'], 1)

    def test_a_connected_mapped_river_identifies_an_uncovered_exit(self):
        grid = Grid(np.zeros((1, 3)), (3., 1., 0., 1.5, 0., -1.), 'EPSG:4326')
        flow = np.array([[1, 2, -1]])
        labels = np.full(flow.shape, -1)
        seeds = {12345: np.array([[True, False, False]])}
        exits = np.array([[False, False, True]])
        result, report = self.basins().classify_uncovered_outlets(grid, flow, exits, labels, seeds)
        self.assertEqual(result[0, 2], 12345)
        self.assertEqual(report['resolved'][0]['basin_values'], [])

    def test_a_shared_river_reference_does_not_become_a_single_outlet_group(self):
        grid = Grid(np.zeros((1, 3)), (3., 1., 0., 1.5, 0., -1.), 'EPSG:4326')
        flow = np.array([[1, 2, -1]])
        labels = np.full(flow.shape, -1)
        seeds = {g: np.array([[True, False, False]]) for g in (3, 7)}
        exits = np.array([[False, False, True]])
        result, report = self.basins().classify_uncovered_outlets(grid, flow, exits, labels, seeds)
        self.assertEqual(result[0, 2], -1)
        self.assertEqual(report['conflicting'][0]['groups'], [3, 7])

    def test_disconnected_river_networks_use_their_actual_exit_basins(self):
        path = self.root / 'rivers.osm'
        path.write_text('<osm version="0.6"><node id="1" lon="0.2" lat="1.5"/>'
                        '<node id="2" lon="0.3" lat="0.5"/>'
                        '<node id="3" lon="1.2" lat="1.5"/>'
                        '<node id="4" lon="1.3" lat="0.5"/>'
                        '<way id="10"><nd ref="1"/><nd ref="2"/>'
                        '<tag k="waterway" v="stream"/></way>'
                        '<way id="20"><nd ref="3"/><nd ref="4"/>'
                        '<tag k="waterway" v="stream"/></way></osm>')
        assigned, report = Waterways([path]).trace_destinations_from_basins(self.basins())
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
            path.write_text('<osm version="0.6">' + nodes + ''.join(parts) + '</osm>')
            network = Waterways([path])
            assigned, report = network.trace_destinations_from_basins(self.basins())
            self.assertEqual(assigned, {('1', '2'): (3, 7), ('2', '3'): (3,), ('2', '4'): (7,)})
            self.assertIn('10', report['ambiguous'])
            seeds.append(rasterize_waterway_destinations(network, assigned, grid)[0])
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
            path.write_text('<osm version="0.6">' + nodes + body + '</osm>')
            network = Waterways([path])
            assigned, _ = network.trace_destinations_from_basins(self.basins())
            results.append(rasterize_waterway_destinations(network, assigned, grid)[0])
        for group in results[0]:
            np.testing.assert_array_equal(results[0][group], results[1][group])

    def test_downstream_trace_can_cross_several_uncovered_estuary_ways(self):
        path = self.root / 'estuary.osm'
        path.write_text('<osm version="0.6"><node id="1" lon="0.5" lat="1"/>'
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
        assigned, report = network.trace_destinations_from_basins(self.basins())
        self.assertEqual(assigned[('1', '2')], (7,))
        self.assertEqual(assigned[('2', '3')], (7,))
        self.assertIn({'way': '20', 'group': 7, 'point': [2., 1.]},
                      report['basin_exit_before_way_endpoint'])
        self.assertEqual(network.trace_destinations_from_basins(self.basins({3: [100]}))[0], {})

    def test_closed_waterway_cycle_does_not_gain_an_invented_destination(self):
        path = self.root / 'cycle.osm'
        path.write_text('<osm version="0.6"><node id="1" lon="0.2" lat="1"/>'
                        '<node id="2" lon="0.3" lat="1"/>'
                        '<way id="10"><nd ref="1"/><nd ref="2"/><nd ref="1"/>'
                        '<tag k="waterway" v="stream"/></way></osm>')
        assigned, report = Waterways([path]).trace_destinations_from_basins(self.basins())
        self.assertEqual(assigned, {})
        self.assertEqual(report['unassigned'], ['10'])


if __name__ == '__main__':
    unittest.main()
