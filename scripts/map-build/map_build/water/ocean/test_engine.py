import json, struct, tempfile, unittest
from unittest.mock import patch
import sys, types
from pathlib import Path
from map_build.water.ocean import engine as r


class OceanRunnerTests(unittest.TestCase):
    def snapshot(self):
        end = []
        routes = []
        for i, lon in enumerate((-90, 0, 90)):
            end.extend(
                [
                    {'endpoint_id': f'top{i}', 'longitude': str(lon), 'latitude': '90'},
                    {'endpoint_id': f'bottom{i}', 'longitude': str(lon), 'latitude': '-90'},
                ]
            )
            routes.append(
                {
                    'route_id': f'r{i}',
                    'route_type': 'meridian',
                    'parameters': {},
                    'points': [
                        {'ordinal': 0, 'endpoint_id': f'top{i}'},
                        {'ordinal': 1, 'endpoint_id': f'bottom{i}'},
                    ],
                }
            )
        seeds = []
        bindings = []
        for i, lon in enumerate((-157.5, -67.5, 22.5, 112.5)):
            end.append({'endpoint_id': f'sp{i}', 'longitude': str(lon), 'latitude': '67.5'})
            seeds.append({'seed_id': f's{i}', 'endpoint_id': f'sp{i}', 'entity_id': 100 + i})
            bindings.append({'code': 7 + i, 'entity_id': 100 + i, 'physical_class': 'water'})
        return {
            'schema': 'worldatlas-geography-decision-export-v1',
            'source': 'neon-export',
            'decision_revision': {'id': 'd', 'status': 'accepted', 'entity_revision': 'e'},
            'entity_revision': {'id': 'e', 'status': 'accepted'},
            'endpoints': end,
            'routes': routes,
            'ocean_seeds': seeds,
            'category_bindings': bindings,
            'policies': [
                {
                    'kind': 'ocean_fill',
                    'definition': {
                        'connectivity': 4,
                        'wrap_longitude': False,
                        'barrier_tie_rule': 'left-of-oriented-route',
                        'unseeded_policy': 'report-only',
                        'route_ids': ['r0', 'r1', 'r2'],
                        'seed_ids': ['s0', 's1', 's2', 's3'],
                    },
                }
            ],
        }

    def grid(self, root, name, code):
        rows = root / (name + '-rows')
        runs = root / (name + '-runs')
        rows.write_bytes(struct.pack('<5I', 0, 1, 2, 3, 4))
        runs.write_bytes(struct.pack('<8I', *[x for _ in range(4) for x in (8, code)]))
        return rows, runs

    def test_full_synthetic_partition_and_pins(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pr, pu = self.grid(root, 'phys', 1)
            rr, ru = self.grid(root, 'prefill', 0)
            out = root / 'out'
            r.run(
                self.snapshot(),
                'a' * 64,
                pr,
                pu,
                rr,
                ru,
                out,
                8,
                4,
                {'physical_rows_sha256': r.sha(pr)},
                2,
            )
            summary = json.loads((out / 'run-summary.json').read_text())
            layer = json.loads((out / 'ocean-layer-manifest.json').read_text())
            self.assertEqual(summary['unseeded_cell_count'], 0)
            self.assertEqual(summary['assigned_cells_total'], 32)
            self.assertEqual(len(layer['tiles']), 2)
            self.assertGreaterEqual(summary['processing_elapsed_seconds'], 0)
            rows = [
                json.loads(x)
                for t in layer['tiles']
                for x in (out / t['span_file']['path']).read_text().splitlines()
            ]
            self.assertEqual(len(rows), 4)
            for row in rows:
                self.assertEqual(
                    [(s['start'], s['end'], s['code'], s['member_id']) for s in row['spans']],
                    [(0, 2, 7, 's0'), (2, 4, 8, 's1'), (4, 6, 9, 's2'), (6, 8, 10, 's3')],
                )
            with self.assertRaises(FileExistsError):
                r.run(self.snapshot(), 'a' * 64, pr, pu, rr, ru, out, 8, 4, {})

    def test_final_recheck_runs_after_export_before_summary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pr, pu = self.grid(root, 'phys', 1)
            rr, ru = self.grid(root, 'prefill', 0)
            out = root / 'out'

            def after_export():
                self.assertTrue((out / 'ocean-layer-manifest.json').is_file())
                raise ValueError('input changed during export')

            with self.assertRaisesRegex(ValueError, 'input changed during export'):
                r.run(
                    self.snapshot(),
                    'a' * 64,
                    pr,
                    pu,
                    rr,
                    ru,
                    out,
                    8,
                    4,
                    {},
                    2,
                    pre_summary=after_export,
                )
            self.assertFalse((out / 'run-summary.json').exists())

    def test_fail_closed_on_unsupported_and_missing_decisions(self):
        s = self.snapshot()
        s['routes'][0]['route_type'] = 'geodesic'
        with self.assertRaisesRegex(ValueError, 'unsupported boundary'):
            r.load_config(s, 8, 4)
        s = self.snapshot()
        s['category_bindings'][0]['code'] = 8
        with self.assertRaises(ValueError):
            r.load_config(s, 8, 4)
        s = self.snapshot()
        s['entity_revision']['id'] = 'different-registry'
        with self.assertRaises(ValueError):
            r.load_config(s, 8, 4)
        s = self.snapshot()
        s['policies'][0]['definition']['route_ids'].append('missing')
        with self.assertRaisesRegex(ValueError, 'unknown route'):
            r.load_config(s, 8, 4)

    def test_unseeded_component_reported_not_assigned(self):
        s = self.snapshot()
        s['endpoints'] = []
        s['routes'] = []
        for i, lon in enumerate((-108, -36, 36, 108)):
            s['endpoints'].extend(
                [
                    {'endpoint_id': f't{i}', 'longitude': str(lon), 'latitude': '90'},
                    {'endpoint_id': f'b{i}', 'longitude': str(lon), 'latitude': '-54'},
                ]
            )
            s['routes'].append(
                {
                    'route_id': f'r{i}',
                    'route_type': 'meridian',
                    'points': [
                        {'ordinal': 0, 'endpoint_id': f't{i}'},
                        {'ordinal': 1, 'endpoint_id': f'b{i}'},
                    ],
                }
            )
        for i, lon in enumerate((-162, -90, -18, 54)):
            s['endpoints'].append(
                {'endpoint_id': f'sp{i}', 'longitude': str(lon), 'latitude': '72'}
            )
        s['policies'][0]['definition']['route_ids'] = ['r0', 'r1', 'r2', 'r3']
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, code in [('p', 1), ('c', 0)]:
                (root / (name + 'r')).write_bytes(struct.pack('<5I', 0, 1, 2, 3, 4))
                (root / (name + 'u')).write_bytes(
                    struct.pack('<8I', *[v for _ in range(4) for v in (10, code)])
                )
            r.run(
                s,
                'a' * 64,
                root / 'pr',
                root / 'pu',
                root / 'cr',
                root / 'cu',
                root / 'out',
                10,
                4,
                {},
                2,
            )
            summary = json.loads((root / 'out/run-summary.json').read_text())
            self.assertEqual(summary['unseeded_cell_count'], 8)
            self.assertEqual(summary['assigned_cells_total'], 32)

    def test_spherical_rhumb_endpoints_and_constant_bearing(self):
        import math

        points = [(-29.4122, 68.2254), (-23.1371290446, 66.4303932484)]
        dense = r.spherical_rhumb_points(points, 1)
        self.assertEqual((dense[0], dense[-1]), tuple(points))

        def psi(lat):
            p = math.radians(lat)
            return math.asinh(math.tan(p))

        mid = dense[len(dense) // 2]
        t = (mid[0] - points[0][0]) / (points[1][0] - points[0][0])
        self.assertAlmostEqual(
            psi(mid[1]), psi(points[0][1]) + t * (psi(points[1][1]) - psi(points[0][1])), places=12
        )
        self.assertEqual(r.spherical_rhumb_points([(0, 30), (1, 30)], 1)[-1], (1, 30))
        for ends in [[(179, 30), (-179, 30)], [(0, 90), (1, 80)]]:
            with self.assertRaises(ValueError):
                r.spherical_rhumb_points(ends, 1)
        with self.assertRaises(ValueError):
            r.spherical_rhumb_points(points, 0)

    def test_s130_published_rhumb_vertices(self):
        # Source: IHO S-130 Ed.1.0.0 GML, M.1505 and M.1504.
        import math

        for first, middle, last in [
            (
                (66.4303932484076, -23.137129044586),
                (67.3328552063905, -26.2331485568407),
                (68.2254, -29.4122),
            ),
            (
                (70.8287305424254, -9.04279190236343),
                (67.9535692712127, -11.4074756025156),
                (65.078408, -13.495404),
            ),
        ]:
            psi = lambda lat: math.asinh(math.tan(math.radians(lat)))
            t = (middle[1] - first[1]) / (last[1] - first[1])
            self.assertAlmostEqual(
                psi(middle[0]), psi(first[0]) + t * (psi(last[0]) - psi(first[0])), places=12
            )

    def test_rhumb_route_loader(self):
        s = self.snapshot()
        s['routes'][0]['route_type'] = 'spherical_rhumb'
        s['routes'][0]['parameters'] = {'max_step_km': '1'}
        s['endpoints'][0]['latitude'] = '80'
        s['endpoints'][1]['latitude'] = '-80'
        self.assertEqual(len(r.load_config(s, 8, 4)[1]), 3)

    def test_geodesic_route_when_dependency_available(self):
        import importlib.util

        if importlib.util.find_spec('pyproj') is None:
            self.skipTest('pyproj is not installed')
        import pyproj

        s = self.snapshot()
        s['build'] = {
            'software_versions': {'pyproj': pyproj.__version__, 'proj': pyproj.proj_version_str}
        }
        s['routes'][0]['route_type'] = 'wgs84_geodesic'
        s['routes'][0]['parameters'] = {'max_step_km': '1'}
        _, paths, _, _ = r.load_config(s, 8, 4)
        self.assertGreater(len(paths[0]), 100)
        self.assertEqual(paths[0][0], (2.0, 0.0))
        self.assertEqual(paths[0][-1], (2.0, 4.0))

    def test_exact_rational_endpoint_matches_rounded_decimal(self):
        e = {
            'longitude': '-0.333333333333333333',
            'latitude': '1.166666666666666667',
            'derivation': {
                'method': 'source_dms_exact_rational',
                'longitude_fraction': [-1, 3],
                'latitude_fraction': [7, 6],
            },
        }
        self.assertEqual(r.endpoint_coordinate(e, 'longitude'), float(-1 / 3))
        e['longitude'] = '-0.333333333333'
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            r.endpoint_coordinate(e, 'longitude')
        e['longitude'] = '-0.333333333333333333'
        e['derivation']['longitude_fraction'] = [1, 0]
        with self.assertRaisesRegex(ValueError, 'invalid exact'):
            r.endpoint_coordinate(e, 'longitude')

    def test_source_decimal_fraction_is_used_and_checked(self):
        e = {
            'longitude': '-9.042791902363430',
            'derivation': {
                'method': 'source_decimal_exact_rational',
                'longitude_fraction': [-904279190236343, 100000000000000],
            },
        }
        self.assertEqual(
            r.endpoint_coordinate(e, 'longitude'), float(-904279190236343 / 100000000000000)
        )
        e['derivation']['longitude_fraction'] = [1, 2]
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            r.endpoint_coordinate(e, 'longitude')

    def test_south_grid_endpoint_uses_grid_dimensions(self):
        s = self.snapshot()
        for e in s['endpoints']:
            if e['endpoint_id'].startswith('bottom'):
                e['latitude'] = '-89'
                e['derivation'] = {
                    'method': 'grid_south_edge',
                    'latitude_fraction': [-89, 1],
                    'longitude_fraction': [int(e['longitude']), 1],
                }
        paths = r.load_config(s, 8, 4)[1]
        self.assertTrue(all(path[-1][1] == 4 for path in paths))
        s['endpoints'][1]['latitude'] = '0'
        s['endpoints'][1]['derivation']['latitude_fraction'] = [0, 1]
        with self.assertRaisesRegex(ValueError, 'final grid row'):
            r.load_config(s, 8, 4)


if __name__ == '__main__':
    unittest.main()
