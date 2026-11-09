import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
MIXED = HERE.parent/'stage3-mixed-leeward-full-20261105'
sys.path.insert(0, str(MIXED))
import polygon_intersection as pi
import bering_intersection as bi
import bering_profiler as bp
import full_coverage_policy as cp
import polygon_resolution as resolution
import polygon_runtime as runtime

MODULES = {'polygon_intersection': pi, 'full_coverage_policy': cp,
           'polygon_resolution': resolution, 'bering_intersection': bi, 'bering_profiler': bp}


def result(function, *args, **kwargs):
    try:
        return 'return', function(*args, **kwargs)
    except ValueError as error:
        return 'error', str(error)


def pin(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


class BoundaryTests(unittest.TestCase):
    def test_random_exact_edges_and_visit_limits(self):
        rng = random.Random(315830)
        for width in (10, 32, 64, 512):
            grid = {'width': width, 'height': min(width//2, 64), 'west': -180, 'north': 90, 'step': 360/width}
            for _ in range(180):
                # Grid boundaries, exact centers, arbitrary binary64, off-grid,
                # horizontal, vertical, reversed and degenerate edges.
                points = []
                for i in range(2):
                    if rng.randrange(2):
                        points.append([-180 + (rng.randrange(-width, 2*width)+rng.choice((0, .5)))*grid['step'],
                                       90 - (rng.randrange(-width, 2*width)+rng.choice((0, .5)))*grid['step']])
                    else:
                        points.append([rng.uniform(-540, 540), rng.uniform(-270, 270)])
                if rng.randrange(4) == 0:
                    points[1][rng.randrange(2)] = points[0][rng.randrange(2)]
                geometry = {'type': 'Polygon', 'coordinates': [points + points[:1]]}
                limit = rng.choice((0, 1, 10, 5000000))
                expected = result(bi.reject_boundary_centers, geometry, grid, max_visits=limit)
                self.assertEqual(result(runtime.reject_boundary_centers, geometry, grid, max_visits=limit), expected)
                self.assertEqual(result(pi.reject_boundary_centers, geometry, grid, max_visits=limit), expected)

    def test_production_grid_one_ulp_center_contacts(self):
        grid = {'width':131072,'height':16,'west':-180,'north':90,'step':360/131072}
        x = -180 + 17.5*grid['step']
        y = 90 - 6.5*grid['step']
        for lon in (math.nextafter(x,-math.inf),x,math.nextafter(x,math.inf)):
            for lat in (math.nextafter(y,-math.inf),y,math.nextafter(y,math.inf)):
                for other in ((lon,90.),(-180.,lat),(lon+grid['step'],lat+grid['step'])):
                    geometry = {'type':'Polygon','coordinates':[[[lon,lat],list(other),[lon,lat]]]}
                    self.assertEqual(result(runtime.reject_boundary_centers,geometry,grid),
                                     result(bi.reject_boundary_centers,geometry,grid))

    def test_non_dyadic_and_multipolygon(self):
        geometry = {'type': 'MultiPolygon', 'coordinates': [[[[0., 1.], [2., 3.], [0., 1.]]], []]}
        for width in (7, 10, 64):
            grid = {'width': width, 'height': width//2, 'west': -180, 'north': 90, 'step': 360/width}
            self.assertEqual(result(runtime.reject_boundary_centers, geometry, grid), result(bi.reject_boundary_centers, geometry, grid))


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.grid = {'width': 10, 'height': 2, 'west': -180, 'north': 90, 'step': 36}
        self.geometry = {'type': 'Polygon', 'coordinates': [[[-105, 55], [-40, 55], [-40, 89], [-105, 89], [-105, 55]]]}
        self.write('physical_rows', '<I', [0, 3, 4])
        self.write('physical_runs', '<II', [(2, 1), (8, 17), (10, 1), (10, 1)])
        self.write('component_rows', '<I', [0, 2, 2])
        self.write('component_runs', '<III', [(2, 5, 10), (5, 8, 11)])

    def write(self, name, fmt, rows):
        (self.root/name).write_bytes(b''.join(struct.pack(fmt, *(row if isinstance(row, tuple) else (row,))) for row in rows))

    def prepare(self):
        self.inputs = {name: pin(self.root/name) for name in ('physical_rows','physical_runs','component_rows','component_runs')}
        self.paths = [spec['path'] for spec in self.inputs.values()]
        return runtime.prepare(MODULES, self.inputs, self.grid)

    def test_full_intersection_profile_and_witness_parity(self):
        prepared = self.prepare()
        for include, exclude in (([], []), ([{'lon': '54', 'lat': '72'}], [{'lon': '-90', 'lat': '72'}]),
                                 ([], [{'lon': '54', 'lat': '72'}]), ([{'lon': '0', 'lat': '72'}], [])):
            args = ([self.geometry], self.grid, *self.paths, include, exclude)
            self.assertEqual(result(prepared['intersect'], *args), result(pi.intersect, *args))
        args = (self.geometry, self.grid, *self.paths)
        self.assertEqual(result(prepared['profile'], *args), result(bp.profile, *args))
        self.assertEqual(result(prepared['reader'].intersect, [self.geometry], self.grid, *self.paths, [], []),
                         result(bi.intersect, [self.geometry], self.grid, *self.paths, [], []))
        prepared['verify']()
        self.assertIs(resolution.polygon_intersection, pi)
        self.assertIs(bp.readrow, bi.readrow)
        self.assertIsNot(prepared['intersect'], pi.intersect)

    def test_coverage_totals_and_row_reuse(self):
        prepared = self.prepare()
        coverage = prepared['resolve'].__globals__['full_coverage_policy']
        index = coverage.build_coverage_index(self.grid, *self.paths)
        self.assertEqual(dict(index._totals), {10: 3, 11: 3})
        self.assertEqual(cp.select_all_centers({'10': 3, '11': 2}, self.grid, *self.paths, coverage_index=index),
                         cp.select_all_centers({'10': 3, '11': 2}, self.grid, *self.paths))
        reader = prepared['reader']
        with open(self.paths[0], 'rb') as pr, open(self.paths[1], 'rb') as pv, open(self.paths[2], 'rb') as cr, open(self.paths[3], 'rb') as cv:
            p, c = reader.readrow(pr,pv,0,10,'physical'), reader.readrow(cr,cv,0,10,'component')
            self.assertEqual(list(p), pi.readrow(pr,pv,0,10,'physical'))
            self.assertEqual(list(c), pi.readrow(cr,cv,0,10,'component'))
            self.assertFalse(p.data.flags.writeable)
            reader.equal_coverage(p,c,10)
            self.assertTrue(p.index.validated.all())
            reader.equal_coverage(p,c,10)

    def test_changed_generation_rejected(self):
        prepared = self.prepare()
        self.write('component_runs', '<III', [(2, 5, 11), (5, 8, 10)])
        with self.assertRaisesRegex(ValueError, 'streams changed'):
            prepared['verify']()
        with self.assertRaisesRegex(ValueError, 'streams changed'):
            prepared['profile'](self.geometry, self.grid, *self.paths)

    def test_invalid_row_parity(self):
        for physical, component in (([(2,1),(8,17),(10,1),(10,1)], [(2,4,10),(5,8,11)]),
                                    ([(2,1),(8,99),(10,1),(10,1)], [(2,5,10),(5,8,11)]),
                                    ([(2,1),(8,17),(9,1),(10,1)], [(2,5,10),(5,8,11)]),
                                    ([(2,1),(8,17),(10,1),(10,1)], [(2,6,10),(5,8,11)])):
            self.write('physical_runs', '<II', physical)
            self.write('component_runs', '<III', component)
            prepared = self.prepare()
            args = ([self.geometry], self.grid, *self.paths, [], [])
            self.assertEqual(result(prepared['intersect'], *args), result(pi.intersect, *args))

    def test_random_coverage_union_validation(self):
        rng = random.Random(1381)
        for _ in range(250):
            labels = [rng.choice((1, 17)) for _ in range(10)]
            physical = [(i+1, code) for i, code in enumerate(labels)]
            components = [(i,i+1,rng.randrange(6)) for i,code in enumerate(labels) if code == 17]
            if components and rng.randrange(2):
                components.pop(rng.randrange(len(components)))
            self.write('physical_rows','<I',[0,10,20])
            self.write('physical_runs','<II',physical+physical)
            self.write('component_rows','<I',[0,len(components),len(components)*2])
            self.write('component_runs','<III',components+components)
            prepared = self.prepare()
            reader = prepared['reader']
            with open(self.paths[0],'rb') as pr, open(self.paths[1],'rb') as pv, open(self.paths[2],'rb') as cr, open(self.paths[3],'rb') as cv:
                p,c = reader.readrow(pr,pv,0,10,'physical'),reader.readrow(cr,cv,0,10,'component')
                self.assertEqual(result(reader.equal_coverage,p,c,10),result(pi.equal_coverage,list(p),list(c),10))


class DriverRoutingTests(unittest.TestCase):
    def test_real_pinned_runtime_to_writer(self):
        import apply_selected_mixed as driver
        from test_mixed_driver import DriverTests, js
        fixture = DriverTests('runTest')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        geometry = {'type': 'Polygon', 'coordinates': [[[0,55],[100,55],[100,89],[0,89],[0,55]]]}
        source = fixture.src/'selector.geojson'
        source.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'id':'f'},'geometry':geometry}]}))
        request_path = Path(fixture.cfg['point_request']['path'])
        request = json.loads(request_path.read_bytes())
        snapshot_path = Path(request['snapshot']['path'])
        snapshot = json.loads(snapshot_path.read_bytes())
        for name in ('sources','source_lineage_assets'):
            next(row for row in snapshot[name] if row['source_id']=='raw').update(sha256=pin(source)['sha256'],size_bytes=source.stat().st_size)
        snapshot['features'][0]['geometry_sha256'] = hashlib.sha256(json.dumps(geometry,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        request['snapshot'] = js(snapshot_path,snapshot)
        fixture.point['snapshot_sha256'] = request['snapshot']['sha256']
        fixture.cfg['point_request'] = js(request_path,request)
        fixture.cfg['polygon_source_files'] = [{'source_id':'raw','version':'v',**pin(source),'size_bytes':source.stat().st_size}]
        fixture.cfg['polygon_runtime'] = pin(Path(runtime.__file__))
        js(fixture.cfgpath,fixture.cfg)
        class Validator:
            @staticmethod
            def validate(*args): return {'status':'diagnostic-candidate-bound'}
        class Resolver:
            def resolve(self,request): return fixture.point
            def lineage_specs(self,manifest): return []
        class PointValidator:
            @staticmethod
            def claims_for(*args): return {}
        load = driver.loadmodule
        def module(name,path):
            return {'stage2_candidate_validator':Validator,'stage3_point_resolver':Resolver(),'reviewed_point_claim_validator':PointValidator}.get(name) or load(name,path)
        with patch.object(driver,'loadmodule',side_effect=module):
            driver.run(fixture.cfgpath)
        report = json.loads((fixture.b/'out/report.json').read_bytes())
        self.assertEqual(report['polygon_resolution']['claims'][0]['component_ids'],[11])
        self.assertEqual(report['writer']['changed_cells'],6)
        self.assertEqual(report['polygon_equivalent_runtime']['code'],fixture.cfg['polygon_runtime'])
        self.assertFalse(report['polygon_equivalent_runtime']['geographic_policy_changed'])


if __name__ == '__main__':
    unittest.main()
