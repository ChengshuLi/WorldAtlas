from pathlib import Path
import tempfile
import unittest

import numpy as np
from pyproj import CRS
import shapefile
from shapely.geometry import LineString

from watersheds.terrain import Grid
from watersheds.waterways import Basins, Waterways


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
        self.assertEqual(assigned, {'10': 3, '20': 7})
        self.assertEqual(report['unassigned'], [])

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
        self.assertEqual(assigned['10'], 7)
        self.assertEqual(assigned['20'], 7)
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
