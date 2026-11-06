"""Bounded Caucasus source + direct v2 producer test on a synthetic grid.

Requires the pinned direct seed directory and actual raw Caucasus files via
environment variables. The snapshot, catalog, closure, mask, components and
resolution are synthetic. The frozen executable allowlist is used unchanged.
No production data is changed and no map is built.
"""
import hashlib
import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import caucasus_seed_gate as gate
import caucasus_stage2_binding as binding
import contracts
from caucasus_effective_snapshot import derive_verified, geomhash
from shapely.geometry import Point, Polygon, LineString, box
from geodesic_fixture import fixture_boundary_filter

REQUIRED = ('CAUCASUS_SELECTED', 'CAUCASUS_RECIPE', 'CAUCASUS_HYDRO',
            'CAUCASUS_AUTHOR', 'DIRECT_SEED_DIR')
PRODUCER_SHA = '48d5719ca263ac28f9433c729d413207f069caa23fb72513d647ed26edd42b35'
CHECKER_SHA = '5b01e11908293df6f941adbc391d4c9e7709f49c1b8ad60d46be0558d66ca6b3'
FIXTURE_SHA = '8d4158b13e9100c4de2ff7f7697c97d71d17ed4a2f7edfd3d09c0df126e78a5d'
CONTRACTS_SHA = 'ed2f78031508d8202358c9b9698f1446128855986d1c2ffcdb35a2f30a6d53d9'


@unittest.skipUnless(all(os.getenv(x) for x in REQUIRED), 'real source and direct fixture paths required')
class RealSourceDirectFixture(unittest.TestCase):
    def test_real_sources_direct_producer_and_checker(self):
        self.assertEqual(gate.digest(contracts.__file__), CONTRACTS_SHA)
        direct = Path(os.environ['DIRECT_SEED_DIR']).resolve(strict=True)
        self.assertEqual(gate.digest(direct / 'seed_producer.py'), PRODUCER_SHA)
        self.assertEqual(gate.digest(direct / 'test_seed_producer.py'), FIXTURE_SHA)
        self.assertEqual(gate.digest(direct / 'closure-checkers' / 'validate_water_closure_v2.py'), CHECKER_SHA)
        self.assertNotIn('seed_producer', sys.modules)
        sys.path.insert(0, str(direct))
        try:
            spec = importlib.util.spec_from_file_location('panama_seed_fixture_for_caucasus', direct / 'test_seed_producer.py')
            peer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(peer)
            fixture = peer.Producer('test_runs_from_selected_structured_inputs')
            fixture.setUp()
            self.addCleanup(fixture.doCleanups)
            grid = {'width': 80, 'height': 40, 'west': -180, 'north': 90, 'step': 4.5}
            guide = json.loads(Path(os.environ['CAUCASUS_SELECTED']).read_bytes())
            guide['coordinates'] = [[float(x), float(y)] for x, y in guide['coordinates']]
            self.assertEqual(geomhash(guide), '9f4ae3bc778ebbcd0258a19868acf0fa655763f5e849361196160fb4289c0d52')
            recipe_path = Path(os.environ['CAUCASUS_RECIPE'])
            recipe_sha = gate.digest(recipe_path)
            self.assertEqual(recipe_sha, '59cae33e287b029465b27110057cc8f06d2dcdf982186b13815cca8f8bbb961c')
            first, last = guide['coordinates'][0], guide['coordinates'][-1]
            route = {'type': 'LineString', 'coordinates': [last, [last[0], 34.0], [first[0], 34.0], first]}
            polygon = Polygon(guide['coordinates'] + route['coordinates'][1:])
            near_boundary = fixture_boundary_filter(polygon.boundary)
            self.assertTrue(polygon.is_valid)
            inside, outside = [], []
            for y in range(40):
                for x in range(80):
                    point = Point(grid['west'] + (x + .5) * grid['step'], grid['north'] - (y + .5) * grid['step'])
                    cell = box(grid['west'] + x * grid['step'], grid['north'] - (y + 1) * grid['step'],
                               grid['west'] + (x + 1) * grid['step'], grid['north'] - y * grid['step'])
                    if near_boundary(point) or cell.intersects(LineString(route['coordinates'])):
                        continue
                    (inside if polygon.contains(point) else outside).append((x, y))
            self.assertTrue(inside and len(outside) >= 5)
            land = {inside[len(inside)//2]: 10, outside[len(outside)//2]: 10}
            for root, point in zip((20, 30, 40, 50), outside[:4]):
                land[point] = root
            self.assertEqual(len(land), 6)
            cr = [[(x, x+1, root) for (x, y0), root in sorted(land.items()) if y0 == y] for y in range(40)]
            pr = []
            for y in range(40):
                vals = [17 if (x, y) in land else 1 for x in range(80)]
                pr.append([(x, vals[x-1]) for x in range(1, 81) if x == 80 or vals[x] != vals[x-1]])
            fixture.crows, fixture.cruns = peer.pair(fixture.src, 'component', cr, 'component')
            prows, pruns = peer.pair(fixture.mask, 'physical', pr, 'pair')
            (fixture.mask / 'rows.u32le').write_bytes(Path(prows['path']).read_bytes())
            (fixture.mask / 'runs.u32le').write_bytes(Path(pruns['path']).read_bytes())
            prows, pruns = peer.pin(fixture.mask / 'rows.u32le'), peer.pin(fixture.mask / 'runs.u32le')
            report = fixture.mask / 'report.json'
            report.write_text(json.dumps({'status': 'candidate-only', 'grid': grid, 'output_sha256':
                {'rows.u32le': prows['sha256'], 'runs.u32le': pruns['sha256']}}))
            inputs = fixture.req['inputs']
            inputs.update({'physical_rows': prows, 'physical_runs': pruns, 'physical_report': peer.pin(report),
                           'component_rows': fixture.crows, 'component_runs': fixture.cruns})
            sp = Path(inputs['snapshot']['path'])
            snap = json.loads(sp.read_text())
            b = snap['mainland_boundaries'][0]
            b.update({'boundary_id': gate.BOUNDARY, 'geometry': guide, 'geometry_sha256': geomhash(guide)})
            b['provenance']['source_assembly_v1'] = {'schema': 'caucasus-source-assembly-v1',
                'recipe': json.loads(recipe_path.read_bytes()), 'recipe_sha256': recipe_sha}
            for key, sha in gate.SOURCE_PINS.items():
                bucket, r2key, size = gate.SOURCE_LOCATIONS[key]
                source = {'source_id': key[0], 'version': key[1], 'sha256': sha, 'r2_bucket': bucket,
                          'r2_key': r2key, 'size_bytes': size}
                snap['sources'].append(source)
                snap['source_lineage_assets'].append({**source, 'kind': 'raw', 'provider': 'fixture',
                    'source_uri': 'https://example.org', 'provenance': {'origin': 'test fixture'}})
                b['provenance']['source_refs'].append({'source_id': key[0], 'version': key[1]})
                b['provenance']['source_relationships'].append({'source_id': key[0], 'version': key[1],
                    'relationship': 'research_comparison_evidence_not_independent_verification_or_proof_of_construction'})
            snap['routes'][0].update({'geometry': route, 'geometry_sha256': geomhash(route)})
            region = snap['seed_regions'][0]
            region['segments'][0].update({'id': gate.BOUNDARY, 'end': len(guide['coordinates'])})
            region['segments'][1]['end'] = 4
            region['geometry_sha256'] = gate.assembled_region_hash(region, {
                ('boundary', gate.BOUNDARY): b, ('route', snap['routes'][0]['route_id']): snap['routes'][0]})
            x, y = inside[len(inside)//2]
            region['witnesses'] = [{'lon': str(grid['west']+(x+.5)*grid['step']),
                                     'lat': str(grid['north']-(y+.5)*grid['step']), 'inside': True}]
            snap['land_baseline_policy']['boundary_ids'] = [gate.BOUNDARY]
            sp.write_text(json.dumps(snap))
            inputs['snapshot'] = peer.pin(sp)
            rp = Path(inputs['resolution']['path'])
            resolution = json.loads(rp.read_text())
            resolution.update({'snapshot_sha256': inputs['snapshot']['sha256'], 'grid': grid,
                'input_sha256': {k: inputs[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')}})
            rp.write_text(json.dumps(resolution)); inputs['resolution'] = peer.pin(rp)
            cp = Path(inputs['closure_contract']['path'])
            contract = json.loads(cp.read_text())
            evidence = cp.parent / 'producer.py'; evidence.write_text('synthetic physical encoding evidence\n')
            contract['grid'] = {'crs': 'EPSG:4326', 'width': 80, 'height': 40, 'west': -180, 'north': 90,
                                'step_numerator': 9, 'step_denominator': 2}
            contract['physical'].update({'rows_sha256': prows['sha256'], 'runs_sha256': pruns['sha256'],
                'report_sha256': gate.digest(report), 'encoding_evidence_sha256': gate.digest(evidence), 'producer_code_path': 'producer.py'})
            contract['resources'] = {'max_cell_visits': 1000}
            cp.write_text(json.dumps(contract)); inputs['closure_contract'] = peer.pin(cp)
            checker = direct / 'closure-checkers' / 'validate_water_closure_v2.py'
            inputs['closure_checker'] = peer.pin(checker)
            terminal_checker = direct / 'closure-checkers' / 'validate_terminal_closure.py'
            inputs['terminal_checker'] = peer.pin(terminal_checker)
            metric = {'policy_id': 'wgs', 'version': '1'}
            snap['land_baseline_policy'].update({
                'policy_id': 'fixture', 'version': '1', 'distance_policy_id': 'wgs',
                'distance_policy_version': '1', 'connectivity': 'four_neighbor_longitude_wrapped',
                'aggregation': 'minimum_over_component_and_mainland_cells',
                'endpoints': 'physical_land_cell_centers', 'tie': 'lowest_category_code',
                'tie_tolerance_metres': '0.00001', 'grid': grid,
                'physical_rows_sha256': prows['sha256'], 'physical_runs_sha256': pruns['sha256'],
                'physical_report_sha256': inputs['physical_report']['sha256']})
            prov = snap['routes'][0]['provenance']
            prov.update({'physical_rows_sha256': prows['sha256'],
                         'physical_runs_sha256': pruns['sha256'],
                         'physical_report_sha256': inputs['physical_report']['sha256'],
                         'contract_sha256': inputs['closure_contract']['sha256'],
                         'checker_sha256': inputs['closure_checker']['sha256']})
            sp.write_text(json.dumps(snap)); inputs['snapshot'] = peer.pin(sp)
            resolution['snapshot_sha256'] = inputs['snapshot']['sha256']
            rp.write_text(json.dumps(resolution)); inputs['resolution'] = peer.pin(rp)
            fixture.req['grid'] = grid
            fixture.path.write_text(json.dumps(fixture.req))
            request_sha = gate.digest(fixture.path)
            report_path = fixture.src / 'caucasus-gate-report.json'
            cfg = {'recipe': {'path': str(recipe_path), 'sha256': recipe_sha},
                   'hydro': {'path': os.environ['CAUCASUS_HYDRO'], 'sha256': list(gate.SOURCE_PINS.values())[0]},
                   'author': {'path': os.environ['CAUCASUS_AUTHOR'], 'sha256': list(gate.SOURCE_PINS.values())[1]},
                   'code_sha256': {name: gate.digest(binding.HERE / name) for name in binding.CODE}}
            binding.run_seed(cfg, fixture.path, request_sha, direct, PRODUCER_SHA,
                             fixture.work, fixture.output, report_path)
            gate_report = json.loads(report_path.read_text())
            self.assertTrue(gate_report['seed_producer_executed'])
            self.assertEqual(gate_report['seed_producer_sha256'], PRODUCER_SHA)
            self.assertIsNone(gate_report['seed_worker_sha256'])
            actual = json.loads((fixture.output / 'report.json').read_text())
            effective, replay = derive_verified(fixture.path, request_sha, recipe_path, recipe_sha,
                                                 os.environ['CAUCASUS_HYDRO'], os.environ['CAUCASUS_AUTHOR'])
            proof = next(t['closure_proof'] for t in actual['region_traces'][0]['input_trace'] if t['kind'] == 'route')
            boundary_trace = next(t for t in actual['region_traces'][0]['input_trace'] if t['kind'] == 'boundary')
            self.assertEqual(actual['decision_snapshot_sha256'], inputs['snapshot']['sha256'])
            self.assertEqual(gate.digest(sp), inputs['snapshot']['sha256'])
            self.assertEqual(replay['source_gate'], {k: v for k, v in gate_report.items()
                             if k not in ('request_sha256', 'effective_snapshot', 'seed_producer_executed', 'seed_producer_sha256', 'seed_worker_sha256')})
            self.assertEqual(replay['effective_snapshot'], gate_report['effective_snapshot'])
            self.assertEqual(boundary_trace['geometry_sha256'], gate_report['effective_snapshot']['derived_geometry_sha256'])
            self.assertEqual(actual['region_traces'][0]['geometry_sha256'], effective['seed_regions'][0]['geometry_sha256'])
            self.assertEqual(proof['checker_sha256'], CHECKER_SHA)
            self.assertEqual(proof['contract_sha256'], inputs['closure_contract']['sha256'])
            self.assertEqual(proof['status'], 'valid')
            self.assertEqual(actual['execution']['mode'], 'direct')
            groups = {g['group_id']: g for g in resolution['groups']}
            entity_codes = {i: i + 16 for i in range(1, 7)}
            result, binding_trace = binding.validate_seed(
                cfg, fixture.path, request_sha, gate_report, PRODUCER_SHA,
                contracts.validate_selected_seed_decisions, actual, groups, entity_codes, metric)
            self.assertEqual(result, snap['land_baseline_policy'])
            self.assertEqual(binding_trace['schema'], 'caucasus-stage2-binding-v1')
            forged_report = dict(gate_report, seed_producer_sha256='0' * 64)
            with self.assertRaisesRegex(ValueError, 'seed gate and independently derived view differ'):
                binding.validate_seed(cfg, fixture.path, request_sha, forged_report, PRODUCER_SHA,
                                      contracts.validate_selected_seed_decisions, actual, groups,
                                      entity_codes, metric)
            print('FIXTURE_RESULT', json.dumps({'snapshot_sha256': inputs['snapshot']['sha256'],
                'request_sha256': request_sha, 'derived_geometry_sha256': boundary_trace['geometry_sha256'],
                'checker_sha256': CHECKER_SHA, 'contract_sha256': inputs['closure_contract']['sha256'],
                'rows_sha256': actual['seed_rows_sha256'], 'runs_sha256': actual['seed_runs_sha256'],
                'producer_code_sha256': actual['code_sha256']}, sort_keys=True))
        finally:
            sys.path.remove(str(direct))
            sys.modules.pop('seed_producer', None)


if __name__ == '__main__':
    unittest.main()
