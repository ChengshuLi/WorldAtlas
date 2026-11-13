"""Compare the reusable distance engine with complete independent cell searches."""
from collections import defaultdict
from pathlib import Path
import tempfile
import unittest

import numpy as np
from pyproj import Geod

from map_build.core.grid import Grid
from map_build.core.layers import patch_rows, write_layer
from map_build.core.rle import open_grid, row
from map_build.land.assignments import assign_components, read_assignments
from map_build.land.components import ComponentGrid
from map_build.land.connected import build_components
from map_build.land.regional import build_regional
from map_build.land.seed_index import build_seed_index


class AssignmentTests(unittest.TestCase):
    def fixture(self, extra):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        grid = Grid(36, 18, 10.)
        seed_cells = [(8, 2, 301, 81), (8, 17, 999, 42), (8, 32, 5555, 707)]
        physical = np.ones((18, 36), dtype=np.uint32)
        seeds = np.zeros_like(physical)
        for y, x, code, _ in seed_cells:
            physical[y,x], seeds[y,x] = 17, code
        for y, x in extra:
            physical[y,x] = 17
        for name, values in [('physical', physical), ('seeds', seeds)]:
            write_layer(root/name, grid, patch_rows(values, grid.bounds, grid))
        build_components(grid, root/'physical', root/'components')
        bindings = [dict(entity_id=entity, code=code, physical_class='land') for _, _, code, entity in seed_cells]
        return root, grid, seed_cells, bindings

    def test_complete_component_distances_match_brute_force_and_compose_with_seeds(self):
        root, grid, seed_cells, bindings = self.fixture([(10,1), (10,2), (7,16), (13,29), (13,30), (8,35)])
        build_seed_index(grid, root/'seeds', root/'index', tile_cells=8)
        with ComponentGrid(root/'physical', root/'components', grid) as components:
            mainland = {components.point(float(grid.longitude(x)),float(grid.latitude(y))) for y,x,_,_ in seed_cells}
            seed_report = dict(groups={str(r): dict(role='mainland', component_id=r) for r in mainland})
            report = assign_components(components, seed_report, root/'index', bindings,
                                       root/'assignments', tie_metres=1e-5)
            observed = read_assignments(report)
            cells = defaultdict(list)
            for y in range(grid.height):
                for a,b,ident in components.row(y):
                    cells[int(ident)] += [(y,x) for x in range(int(a),int(b))]
        geod = Geod(ellps='WGS84')
        expected = {}
        for ident, points in cells.items():
            if ident in mainland:
                continue
            distances = {code: min(geod.inv(float(grid.longitude(x)),float(grid.latitude(y)),
                                            float(grid.longitude(xx)),float(grid.latitude(yy)))[2]
                                   for y,x in points) for yy,xx,code,_ in seed_cells}
            best = min(distances.values())
            winner = min(code for code, distance in distances.items() if distance <= best+1e-5)
            expected[ident] = next(b['entity_id'] for b in bindings if b['code'] == winner)
        self.assertEqual(observed, expected)
        self.assertTrue(report['ties'])
        selection = dict(domains={'regional': dict(features=[], affiliations=[], category_bindings=bindings)})
        result = build_regional(selection, grid, root/'physical', root/'components', root/'seeds',
                                root/'regional', protected=mainland, component_defaults=observed)
        with open_grid(result['land'], grid) as data:
            for y in range(grid.height):
                ends,codes = row(data,y,grid.width)
                values = codes[np.searchsorted(ends,np.arange(grid.width),side='right')]
                for ident, points in cells.items():
                    for yy,x in points:
                        if yy == y:
                            code = next((code for sy,sx,code,_ in seed_cells if (yy,x)==(sy,sx)), None)
                            if code is None:
                                code = next(b['code'] for b in bindings if b['entity_id']==observed[ident])
                            self.assertEqual(values[x], code)
                self.assertTrue(np.all(np.isin(values,[0,301,999,5555])))
        path = Path(report['entities'])
        path.write_bytes(path.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'assignment file differs'):
            read_assignments(report)

    def test_all_land_already_seeded_needs_no_island_distance_search(self):
        root, grid, seed_cells, bindings = self.fixture([])
        build_seed_index(grid, root/'seeds', root/'index', tile_cells=8)
        with ComponentGrid(root/'physical',root/'components',grid) as components:
            mainland={components.point(float(grid.longitude(x)),float(grid.latitude(y))) for y,x,_,_ in seed_cells}
            result=assign_components(components,dict(groups={str(r):dict(role='mainland',component_id=r) for r in mainland}),
                                     root/'index',bindings,root/'assignments',tie_metres=1e-5)
        self.assertEqual(read_assignments(result),{})
        self.assertEqual(result['exact_queries'],0)


if __name__=='__main__':
    unittest.main()
