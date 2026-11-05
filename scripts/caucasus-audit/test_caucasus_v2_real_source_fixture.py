"""Bounded Caucasus source + direct v2 producer test on a synthetic grid.

Requires the pinned direct seed directory and actual raw Caucasus files via
environment variables. The snapshot, catalog, closure, mask, components and
resolution are synthetic. Executable allowlists are patched only in test memory.
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
from caucasus_effective_snapshot import derive_verified, geomhash
from shapely.geometry import Point, Polygon

REQUIRED = ('CAUCASUS_SELECTED', 'CAUCASUS_RECIPE', 'CAUCASUS_HYDRO',
            'CAUCASUS_AUTHOR', 'DIRECT_SEED_DIR')
PRODUCER_SHA = '48d5719ca263ac28f9433c729d413207f069caa23fb72513d647ed26edd42b35'
CHECKER_SHA = '5b01e11908293df6f941adbc391d4c9e7709f49c1b8ad60d46be0558d66ca6b3'
FIXTURE_SHA = '8d4158b13e9100c4de2ff7f7697c97d71d17ed4a2f7edfd3d09c0df126e78a5d'


@unittest.skipUnless(all(os.getenv(x) for x in REQUIRED), 'real source and direct fixture paths required')
class RealSourceDirectFixture(unittest.TestCase):
    def test_real_sources_direct_producer_and_checker(self):
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
            grid = {'width': 40, 'height': 40, 'west': 35, 'north': 50, 'step': .5}
            guide = json.loads(Path(os.environ['CAUCASUS_SELECTED']).read_bytes())
            guide['coordinates'] = [[float(x), float(y)] for x, y in guide['coordinates']]
            self.assertEqual(geomhash(guide), '9f4ae3bc778ebbcd0258a19868acf0fa655763f5e849361196160fb4289c0d52')
            recipe_path = Path(os.environ['CAUCASUS_RECIPE'])
            recipe_sha = gate.digest(recipe_path)
            self.assertEqual(recipe_sha, '59cae33e287b029465b27110057cc8f06d2dcdf982186b13815cca8f8bbb961c')
            first, last = guide['coordinates'][0], guide['coordinates'][-1]
            route = {'type': 'LineString', 'coordinates': [last, [last[0], 34.0], [first[0], 34.0], first]}
            polygon = Polygon(guide['coordinates'] + route['coordinates'][1:])
            self.assertTrue(polygon.is_valid)
            inside, outside = [], []
            for y in range(2, 30):
                for x in range(2, 30):
                    point = Point(grid['west'] + (x + .5) * grid['step'], grid['north'] - (y + .5) * grid['step'])
                    if point.distance(polygon.boundary) < 1:
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
                vals = [17 if (x, y) in land else 1 for x in range(40)]
                pr.append([(x, vals[x-1]) for x in range(1, 41) if x == 40 or vals[x] != vals[x-1]])
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
            contract['grid'] = {'crs': 'EPSG:4326', 'width': 40, 'height': 40, 'west': 35, 'north': 50,
                                'step_numerator': 1, 'step_denominator': 2}
            contract['physical'].update({'rows_sha256': prows['sha256'], 'runs_sha256': pruns['sha256'],
                'report_sha256': gate.digest(report), 'encoding_evidence_sha256': gate.digest(evidence), 'producer_code_path': 'producer.py'})
            contract['resources'] = {'max_cell_visits': 1000}
            cp.write_text(json.dumps(contract)); inputs['closure_contract'] = peer.pin(cp)
            checker = direct / 'closure-checkers' / 'validate_water_closure_v2.py'
            inputs['closure_checker'] = peer.pin(checker)
            fixture.req['grid'] = grid
            fixture.path.write_text(json.dumps(fixture.req))
            request_sha = gate.digest(fixture.path)
            gate_report, geometry = gate.check(fixture.path, recipe_path, recipe_sha,
                os.environ['CAUCASUS_HYDRO'], os.environ['CAUCASUS_AUTHOR'])
            gate_report['request_sha256'] = request_sha
            # The candidate fail-closed allowlist is patched only in this test.
            allowed = {k: inputs[k]['sha256'] for k in ('closure_checker','seed_builder','seed_kernel')}
            original_spec = gate.importlib.util.spec_from_file_location
            def instrumented_spec(name, path, *a, **kw):
                spec = original_spec(name, path, *a, **kw)
                if name == 'caucasus_gated_seed_producer':
                    original_exec = spec.loader.exec_module
                    def execute(module):
                        original_exec(module)
                        module.TRUSTED_CODE.update(allowed)
                    spec.loader.exec_module = execute
                return spec
            sys.modules.pop('seed_producer', None)
            with patch.object(gate.importlib.util, 'spec_from_file_location', side_effect=instrumented_spec):
                gate.run_producer(direct, PRODUCER_SHA, fixture.path, fixture.work, fixture.output, geometry, gate_report)
            actual = json.loads((fixture.output / 'report.json').read_text())
            effective, replay = derive_verified(fixture.path, request_sha, recipe_path, recipe_sha,
                                                 os.environ['CAUCASUS_HYDRO'], os.environ['CAUCASUS_AUTHOR'])
            proof = next(t['closure_proof'] for t in actual['region_traces'][0]['input_trace'] if t['kind'] == 'route')
            boundary_trace = next(t for t in actual['region_traces'][0]['input_trace'] if t['kind'] == 'boundary')
            self.assertEqual(actual['decision_snapshot_sha256'], inputs['snapshot']['sha256'])
            self.assertEqual(gate.digest(sp), inputs['snapshot']['sha256'])
            self.assertEqual(replay['source_gate'], {k: v for k, v in gate_report.items()
                             if k not in ('request_sha256', 'effective_snapshot')})
            self.assertEqual(replay['effective_snapshot'], gate_report['effective_snapshot'])
            self.assertEqual(boundary_trace['geometry_sha256'], gate_report['effective_snapshot']['derived_geometry_sha256'])
            self.assertEqual(actual['region_traces'][0]['geometry_sha256'], effective['seed_regions'][0]['geometry_sha256'])
            self.assertEqual(proof['checker_sha256'], CHECKER_SHA)
            self.assertEqual(proof['contract_sha256'], inputs['closure_contract']['sha256'])
            self.assertEqual(proof['status'], 'valid')
            self.assertEqual(actual['execution']['mode'], 'direct')
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
