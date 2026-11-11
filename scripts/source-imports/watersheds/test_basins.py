from pathlib import Path
import tempfile
import unittest

import numpy as np
from pyproj import CRS
import shapefile

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

    def test_only_domain_exits_receive_basin_fallback(self):
        grid = Grid(np.zeros((3, 3)), (0., .5, 0., 1.5, 0., -.5), 'EPSG:4326')
        terminals = self.basins().terminals(grid, np.full((3, 3), -1))
        self.assertEqual(terminals[0, 0], 3)
        self.assertEqual(terminals[1, 1], -1)

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


if __name__ == '__main__':
    unittest.main()
