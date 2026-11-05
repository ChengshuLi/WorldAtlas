"""Combined source, producer, WIP direct-binding and strict-core fixture.

Requires the pinned direct seed directory and actual Panama/Caucasus sources via
environment variables. The snapshot, catalog, closure, mask, components and
resolution are synthetic. The frozen executable allowlist is used unchanged.
No production data is changed and no map is built.
"""
import copy
import functools
import hashlib
import importlib.util
import json
import os
import sys
import unittest
from unittest import mock
from pathlib import Path

import contracts
import build_stage2 as wip_core
import direct_seed
import caucasus_seed_gate as gate
import caucasus_stage2_binding as binding
from caucasus_effective_snapshot import derive_verified, geomhash
from shapely.geometry import Point, Polygon

REQUIRED = ('CAUCASUS_SELECTED', 'CAUCASUS_RECIPE', 'CAUCASUS_HYDRO',
            'CAUCASUS_AUTHOR', 'DIRECT_SEED_DIR', 'PANAMA_REAL_OSM_ARCHIVE')
PRODUCER_SHA = '48d5719ca263ac28f9433c729d413207f069caa23fb72513d647ed26edd42b35'
CHECKER_SHA = '5b01e11908293df6f941adbc391d4c9e7709f49c1b8ad60d46be0558d66ca6b3'
FIXTURE_SHA = '8d4158b13e9100c4de2ff7f7697c97d71d17ed4a2f7edfd3d09c0df126e78a5d'


@unittest.skipUnless(all(os.getenv(x) for x in REQUIRED), 'real source and direct fixture paths required')
class CombinedWipDirectGateFixture(unittest.TestCase):
    def test_isolated_direct_gate_and_core_with_both_sources(self):
        self.assertEqual(gate.digest(contracts.__file__), 'f703e5edcb0f67cc908aa0812e5b194b480ea2916c017464e51d1bfa0066c7f1')
        self.assertEqual(gate.digest(wip_core.__file__), '79d2d723ecb0fc7ee36647843cca311d4b3098b71179799fc5ba4997530055b6')
        self.assertEqual(gate.digest(direct_seed.__file__), '79dff028d83d9fdba6170ccec80d7b9d54ac9ba13ae134683d9b35217cfd0654')
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
            from osm_source_handoff import verified_geometry
            from panama_core_validation import validate_panama_source
            fixture = peer.Producer('test_runs_from_selected_structured_inputs')
            fixture.setUp()
            self.addCleanup(fixture.doCleanups)
            grid = {'width': 720, 'height': 360, 'west': -180, 'north': 90, 'step': .5}
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
            for y in range(80, 110):
                for x in range(420, 475):
                    point = Point(grid['west'] + (x + .5) * grid['step'], grid['north'] - (y + .5) * grid['step'])
                    if point.distance(polygon.boundary) < 1:
                        continue
                    (inside if polygon.contains(point) else outside).append((x, y))
            self.assertTrue(inside and len(outside) >= 5)
            land = {inside[len(inside)//2]: 10, outside[len(outside)//2]: 10}
            for root, point in zip((20, 30, 40, 50), outside[:4]):
                land[point] = root
            self.assertEqual(len(land), 6)
            land[(206,164)] = 60; land[(202,163)] = 60
            cr = [[(x, x+1, root) for (x, y0), root in sorted(land.items()) if y0 == y] for y in range(grid['height'])]
            pr = []
            for y in range(grid['height']):
                vals = [17 if (x, y) in land else 1 for x in range(grid['width'])]
                pr.append([(x, vals[x-1]) for x in range(1, grid['width']+1) if x == grid['width'] or vals[x] != vals[x-1]])
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
            panama_archive = Path(os.environ['PANAMA_REAL_OSM_ARCHIVE']).resolve(strict=True)
            panama_sha = '04fe1adb295e93d78ee029b48351d2b0380d69ac631b47c909dffd538bbaf6c1'
            panama_hash = 'cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17'
            panama_line = verified_geometry(panama_archive, panama_sha, panama_hash)
            panama_first, panama_last = panama_line['coordinates'][0], panama_line['coordinates'][-1]
            panama_route = {'type':'LineString','coordinates':[panama_last, [-76.0, panama_last[1]], [-76.0, panama_first[1]], panama_first]}
            panama_polygon = Polygon(panama_line['coordinates'] + panama_route['coordinates'][1:])
            self.assertTrue(panama_polygon.is_valid and panama_polygon.contains(Point(-76.75, 7.75)))
            self.assertFalse(panama_polygon.contains(Point(-78.75, 8.25)))
            source = {'source_id':'osm-panama-current-way-full-bundle', 'version':'capture-20261105-04fe1adb295e',
                'sha256':panama_sha, 'r2_bucket':'worldatlas', 'r2_key':'sources/osm/panama-colombia/way-full-20261105-04fe1adb295e.zip', 'size_bytes':panama_archive.stat().st_size}
            snap['sources'].append(source)
            snap['source_lineage_assets'].append({**source, 'kind':'raw', 'provider':'OSM', 'source_uri':'https://www.openstreetmap.org/',
                'provenance':{'origin':'synthetic fixture catalog','representation':'provider_original_bundle'}})
            ref = {'source_id':source['source_id'], 'version':source['version']}
            panama_boundary = copy.deepcopy(b)
            panama_boundary.update({'boundary_id':'panama_colombia_osm_admin_boundary', 'geometry':panama_line, 'geometry_sha256':panama_hash,
                'provenance':{'lineage_status':'incomplete', 'source_refs':[ref], 'source_relationships':[{**ref,'relationship':'supporting_geographic_evidence_not_complete_construction_lineage'}]}})
            snap['mainland_boundaries'].append(panama_boundary)
            proute = copy.deepcopy(snap['routes'][0]); proute.update({'route_id':'panama-closure-fixture','geometry':panama_route,'geometry_sha256':geomhash(panama_route)})
            snap['routes'].append(proute)
            pregion = copy.deepcopy(region);pregion.update({'region_id':'north_america_mainland_region_v1',
                'segments':[{'kind':'boundary','id':'panama_colombia_osm_admin_boundary','start':0,'end':len(panama_line['coordinates']),'reverse':False},
                            {'kind':'route','id':'panama-closure-fixture','start':0,'end':4,'reverse':False}],
                'witnesses':[{'lon':'-76.75','lat':'7.75','inside':True}]})
            pregion['geometry_sha256'] = gate.assembled_region_hash(pregion, {('boundary','panama_colombia_osm_admin_boundary'):panama_boundary,('route','panama-closure-fixture'):proute})
            snap['seed_regions'].append(pregion)
            snap['land_baseline_policy']['boundary_ids'].append('panama_colombia_osm_admin_boundary')
            snap['land_baseline_policy']['route_ids'].append('panama-closure-fixture')
            snap['land_baseline_policy']['region_ids'].append('north_america_mainland_region_v1')
            snap['land_baseline_policy']['mainland_rule_ids'].append('rule5')
            snap['mainland_component_rules'].append({'rule_id':'rule5','decision_revision':'r','execution_status':'selected_for_research',
                'group_id':'g5','region_id':'north_america_mainland_region_v1','inside_entity_id':5,'outside_entity_id':6})
            inputs['panama_osm_archive'] = peer.pin(panama_archive)
            sp.write_text(json.dumps(snap))
            inputs['snapshot'] = peer.pin(sp)
            rp = Path(inputs['resolution']['path'])
            resolution = json.loads(rp.read_text())
            resolution['groups'].append({'group_id':'g5','role':'mainland','target_entity_ids':[5,6],'component_id_current_generation_only':60})
            resolution.update({'snapshot_sha256': inputs['snapshot']['sha256'], 'grid': grid,
                'input_sha256': {k: inputs[k]['sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')}})
            rp.write_text(json.dumps(resolution)); inputs['resolution'] = peer.pin(rp)
            cp = Path(inputs['closure_contract']['path'])
            contract = json.loads(cp.read_text())
            evidence = cp.parent / 'producer.py'; evidence.write_text('synthetic physical encoding evidence\n')
            contract['grid'] = {'crs': 'EPSG:4326', 'width': 720, 'height': 360, 'west': -180, 'north': 90,
                                'step_numerator': 1, 'step_denominator': 2}
            contract['physical'].update({'rows_sha256': prows['sha256'], 'runs_sha256': pruns['sha256'],
                'report_sha256': gate.digest(report), 'encoding_evidence_sha256': gate.digest(evidence), 'producer_code_path': 'producer.py'})
            contract['resources'] = {'max_cell_visits': 1000}
            cp.write_text(json.dumps(contract)); inputs['closure_contract'] = peer.pin(cp)
            checker = direct / 'closure-checkers' / 'validate_water_closure_v2.py'
            inputs['closure_checker'] = peer.pin(checker)
            # Synthetic complete selected-policy metadata for the strict core.
            inputs['terminal_checker'] = peer.pin(direct / 'closure-checkers' / 'validate_terminal_closure.py')
            metric = {'policy_id': 'wgs', 'version': '1'}
            policy = snap['land_baseline_policy']
            policy.update({'policy_id':'fixture', 'version':'1', 'grid':grid,
                'distance_policy_id':'wgs', 'distance_policy_version':'1',
                'connectivity':'four_neighbor_longitude_wrapped', 'aggregation':'minimum_over_component_and_mainland_cells',
                'endpoints':'physical_land_cell_centers', 'tie':'lowest_category_code', 'tie_tolerance_metres':'0.00001',
                'physical_rows_sha256':prows['sha256'], 'physical_runs_sha256':pruns['sha256'],
                'physical_report_sha256':gate.digest(report)})
            for selected_route in snap['routes']:
                selected_route['provenance'].update({'physical_rows_sha256':'1'*64, 'physical_runs_sha256':'2'*64,
                    'physical_report_sha256':'3'*64, 'contract_sha256':'4'*64, 'checker_sha256':'5'*64})
            sp.write_text(json.dumps(snap));inputs['snapshot'] = peer.pin(sp)
            resolution['snapshot_sha256'] = inputs['snapshot']['sha256'];rp.write_text(json.dumps(resolution));inputs['resolution'] = peer.pin(rp)
            fixture.req['grid'] = grid
            stage = fixture.d / 'synthetic-stage'
            (stage / 'requests').mkdir(parents=True); (stage / 'derived').mkdir()
            fixture.path = stage / 'requests' / 'seed.json'
            fixture.path.write_text(json.dumps(fixture.req))
            request_sha = gate.digest(fixture.path)
            report_path = fixture.src / 'caucasus-gate-report.json'
            cfg = {'recipe': {'path': str(recipe_path), 'sha256': recipe_sha},
                   'hydro': {'path': os.environ['CAUCASUS_HYDRO'], 'sha256': list(gate.SOURCE_PINS.values())[0]},
                   'author': {'path': os.environ['CAUCASUS_AUTHOR'], 'sha256': list(gate.SOURCE_PINS.values())[1]},
                   'code_sha256': {name: gate.digest(binding.HERE / name) for name in binding.CODE}}
            evil = fixture.d / 'ambient-startup'; evil.mkdir()
            sentinel = fixture.d / 'ambient-startup-ran'
            (evil / 'sitecustomize.py').write_text('from pathlib import Path\nPath(' + repr(str(sentinel)) + ').write_text("injected")\n')
            with mock.patch.dict(os.environ, {'PYTHONPATH':str(evil)}):
                invoked = direct_seed.invoke(fixture.path, fixture.work, fixture.output,
                    caucasus={'config':cfg, 'directory':str(binding.HERE), 'report':str(report_path)})
            self.assertFalse(sentinel.exists(), 'isolated gate ran ambient Python startup code')
            forged_config = copy.deepcopy(cfg);forged_config['code_sha256']['caucasus_seed_gate.py'] = '0'*64
            with self.assertRaisesRegex(ValueError, 'Caucasus gate code mismatch'):
                direct_seed.invoke(fixture.path, fixture.d/'forged-work', fixture.d/'forged-output',
                    caucasus={'config':forged_config, 'directory':str(binding.HERE), 'report':str(fixture.d/'forged-report.json')})
            self.assertFalse((fixture.d/'forged-work').exists())
            self.assertFalse((fixture.d/'forged-output').exists())
            gate_report = json.loads(report_path.read_text())
            self.assertTrue(gate_report['seed_producer_executed'])
            self.assertEqual(gate_report['seed_producer_sha256'], PRODUCER_SHA)
            self.assertIsNone(gate_report['seed_worker_sha256'])
            actual = json.loads((fixture.output / 'report.json').read_text())
            self.assertEqual(invoked, actual)
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
            # Exercise the WIP core's direct input/manifest binding with the
            # actual generated gate, seed and real Panama archive, not mocks.
            pin = peer.pin
            mapping = (('snapshot','decision_snapshot'), ('physical_rows','physical_rows'),
                ('physical_runs','physical_runs'), ('physical_report','physical_report'),
                ('component_rows','component_rows'), ('component_runs','component_runs'),
                ('component_manifest','component_manifest'), ('closure_checker','closure_checker'),
                ('terminal_checker','terminal_checker'), ('closure_contract','closure_contract'),
                ('seed_builder','seed_builder'), ('seed_kernel','seed_kernel'),
                ('panama_osm_archive','panama_osm_archive'))
            outer_inputs = {dst:fixture.req['inputs'][src] for src,dst in mapping}
            controls = {'minimum_memory_kib':0}
            outer = {'grid':grid,'policy_id':'p','policy_version':'1','controls':controls,
                     'seed_controls':fixture.req['controls'],'inputs':outer_inputs,'caucasus_source':cfg}
            outer_path = fixture.d / 'outer.json'; outer_path.write_text(json.dumps(outer)); outer_pin = pin(outer_path)
            manifest = stage / 'derived' / 'manifest.json'; manifest.write_text('{}')
            core_cfg = {'orchestration':{'outer_config_sha256':outer_pin['sha256'],'derived_manifest':pin(manifest)},
                'policy_id':'p','policy_version':'1','controls':controls,
                'inputs':{'resolution_report':fixture.req['inputs']['resolution']},
                'seed_code_files':{'rasterizer':inputs['seed_builder'],'rasterizer_kernel':inputs['seed_kernel']}}
            db = {'request':pin(fixture.path),'panama_osm_archive':inputs['panama_osm_archive'],'outer_config':outer_pin}
            derived = {'seed_request_sha256':db['request']['sha256'], 'direct_seed_binding':db}
            wip_core.validate_seed_mode(None, db, derived)
            with self.assertRaisesRegex(ValueError, 'seed mode or derived binding mismatch'):
                wip_core.validate_seed_mode({'historical':'pin'}, db, derived)
            core_paths = {'seed_report':fixture.output / 'report.json'}
            core_pins = {dst:fixture.req['inputs'][src]['sha256'] for src,dst in mapping
                         if dst in ('decision_snapshot','physical_rows','physical_runs','physical_report',
                                    'component_rows','component_runs','component_manifest')}
            core_pins['resolution_report'] = inputs['resolution']['sha256']
            self.assertEqual(wip_core.verify_direct_binding(db,derived,core_cfg,core_paths,core_pins,grid,actual,lambda:None), fixture.req)
            forged_binding = copy.deepcopy(db); forged_binding['panama_osm_archive']['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'input hash mismatch'):
                wip_core.verify_direct_binding(forged_binding,derived,core_cfg,core_paths,core_pins,grid,actual,lambda:None)
            forged_marker = {'seed_request_sha256':'0'*64}
            with self.assertRaisesRegex(ValueError, 'request/marker mismatch'):
                wip_core.verify_direct_binding(db,forged_marker,core_cfg,core_paths,core_pins,grid,actual,lambda:None)
            groups = {g['group_id']:g for g in resolution['groups']}
            entity_codes = {i:i+16 for i in range(1,7)}
            # Stored route provenance describes the old proof; the actual
            # generated proofs bind different current checker/contract bytes.
            with self.assertRaisesRegex(ValueError, 'route source/provenance mismatch'):
                binding.validate_seed(cfg, fixture.path, request_sha, gate_report, PRODUCER_SHA,
                    contracts.validate_selected_seed_decisions, actual, groups, entity_codes, metric)
            fresh_validator = functools.partial(contracts.validate_selected_seed_decisions, fresh_closure_proofs=True)
            result, binding_trace = binding.validate_seed(
                cfg, fixture.path, request_sha, gate_report, PRODUCER_SHA,
                fresh_validator, actual, groups, entity_codes, metric)
            self.assertEqual(result, policy)
            for region_trace in actual['region_traces']:
                provenance = next(t['route_provenance'] for t in region_trace['input_trace'] if t['kind'] == 'route')
                self.assertNotEqual(provenance['checker_sha256'], inputs['closure_checker']['sha256'])
                self.assertNotEqual(provenance['contract_sha256'], inputs['closure_contract']['sha256'])
            for key, message in (('checker_sha256', 'water closure checker mismatch'), ('contract_sha256', 'closure proof mismatch')):
                altered = copy.deepcopy(actual)
                altered_proof = next(t['closure_proof'] for t in altered['region_traces'][1]['input_trace'] if t['kind'] == 'route')
                altered_proof[key] = '0' * 64
                with self.assertRaisesRegex(ValueError, message):
                    fresh_validator(effective, altered, groups, entity_codes, metric)
            altered_history = copy.deepcopy(actual)
            altered_route = next(t for t in altered_history['region_traces'][0]['input_trace'] if t['kind'] == 'route')
            altered_route['route_provenance']['contract_sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'route provenance mismatch'):
                fresh_validator(effective, altered_history, groups, entity_codes, metric)
            forged_gate = dict(gate_report, seed_producer_sha256='0' * 64)
            with self.assertRaisesRegex(ValueError, 'seed gate and independently derived view differ'):
                binding.validate_seed(cfg, fixture.path, request_sha, forged_gate, PRODUCER_SHA,
                                      fresh_validator, actual, groups, entity_codes, metric)
            forged_core = copy.deepcopy(actual)
            panama_region = next(x for x in forged_core['region_traces'] if x['region_id'] == 'north_america_mainland_region_v1')
            panama_region['input_trace'][0]['geometry_sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'geometry hash mismatch'):
                fresh_validator(effective, forged_core, groups, entity_codes, metric)
            stale_view = copy.deepcopy(effective)
            stale_view['routes'][0]['provenance']['contract_sha256'] = 'f' * 64
            with self.assertRaisesRegex(ValueError, 'route provenance mismatch'):
                fresh_validator(stale_view, actual, groups, entity_codes, metric)
            panama_trace = validate_panama_source(snap, inputs['snapshot']['sha256'], actual, inputs['panama_osm_archive'])
            self.assertEqual(panama_trace['geometry_sha256'], panama_hash)
            self.assertEqual(panama_trace['vertices'], 5254)
            self.assertEqual(actual['seed_rows_sha256'], 'fa311f33642523204236c02d8f7d23309174347304e8412d76e126643480c9dc')
            self.assertEqual(actual['seed_runs_sha256'], 'e068228e97fa80bde0f7d937dc62e26c7ae36330604369c22459f1fea5079091')
            self.assertEqual(len(actual['region_traces']), 2)
            for region_trace in actual['region_traces']:
                route_proof = next(t['closure_proof'] for t in region_trace['input_trace'] if t['kind'] == 'route')
                self.assertEqual(route_proof['status'], 'valid')
                self.assertEqual(route_proof['checker_sha256'], CHECKER_SHA)
            forged = copy.deepcopy(actual);forged['panama_source_trace']['geometry_sha256'] = '0'*64
            with self.assertRaisesRegex(ValueError, 'source trace mismatch'):
                validate_panama_source(snap, inputs['snapshot']['sha256'], forged, inputs['panama_osm_archive'])
            self.assertEqual(binding_trace['schema'], 'caucasus-stage2-binding-v1')
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
