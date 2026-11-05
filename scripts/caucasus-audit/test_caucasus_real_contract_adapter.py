"""Bounded test of adapter against real contracts with a synthetic fixture.

Put the reviewed stage2-geodesic-20261104 directory on PYTHONPATH. No seed,
real closure, Neon update or map is produced.
"""
import unittest
import copy
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import contracts
import test_contracts_qualified
import caucasus_stage2_validation as adapter
import caucasus_seed_gate as gate
import caucasus_stage2_binding as binding
from caucasus_effective_snapshot import derive_verified, geomhash


class RealContractAdapterTest(unittest.TestCase):
    def setUp(self):
        self.fixture = test_contracts_qualified.CrosswalkTests('test_full_crosswalk_and_tampers')
        self.fixture.setUp()
        self.fixture.seed['decision_snapshot_sha256'] = 'a' * 64
        self.derivation = {'effective_snapshot': {'original_snapshot_sha256': 'a' * 64}}
        self.digests = {'request': 'c' * 64, 'recipe': 'd' * 64,
                        'hydro': list(adapter.SOURCE_PINS.values())[0],
                        'author': list(adapter.SOURCE_PINS.values())[1]}

    def invoke(self):
        x = self.fixture
        with patch.object(adapter, 'verify_code'), patch.object(adapter, 'derive_verified', return_value=(x.snapshot, self.derivation)), patch.object(adapter, 'digest', side_effect=lambda p: self.digests[p]):
            return adapter.validate(contracts.validate_selected_seed_decisions, x.seed, x.groups, x.codes, x.metric,
                                    request_path='request', request_sha256='c' * 64, recipe='recipe',
                                    recipe_sha256='d' * 64, hydro='hydro', author='author', code_sha256={})

    def test_real_validator_accepts_fixture(self):
        result, trace = self.invoke()
        self.assertEqual(result, self.fixture.snapshot['land_baseline_policy'])
        self.assertEqual(trace['schema'], 'caucasus-source-validation-v1')

    def test_real_validator_rejects_stale_boundary_trace(self):
        self.fixture.seed['region_traces'][0]['input_trace'][0]['geometry_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'geometry hash mismatch'):
            self.invoke()

    @unittest.skipUnless(all(os.getenv(k) for k in ('CAUCASUS_SELECTED', 'CAUCASUS_RECIPE', 'CAUCASUS_HYDRO', 'CAUCASUS_AUTHOR')), 'raw source fixture paths not supplied')
    def test_real_source_derivation_and_real_validator(self):
        x = self.fixture
        line = json.loads(Path(os.environ['CAUCASUS_SELECTED']).read_bytes())
        line['coordinates'] = [[float(v) for v in p] for p in line['coordinates']]
        b = x.snapshot['mainland_boundaries'][0]
        b.update(boundary_id=gate.BOUNDARY, geometry=line, geometry_sha256=geomhash(line))
        recipe = json.loads(Path(os.environ['CAUCASUS_RECIPE']).read_bytes())
        recipe_sha = gate.digest(os.environ['CAUCASUS_RECIPE'])
        b['provenance']['source_assembly_v1'] = {'schema': 'caucasus-source-assembly-v1', 'recipe': recipe, 'recipe_sha256': recipe_sha}
        for key, sha in gate.SOURCE_PINS.items():
            source_id, version = key
            bucket, r2key, size = gate.SOURCE_LOCATIONS[key]
            source = {'source_id': source_id, 'version': version, 'sha256': sha, 'r2_bucket': bucket, 'r2_key': r2key, 'size_bytes': size}
            x.snapshot['sources'].append(source)
            x.snapshot['source_lineage_assets'].append({**source, 'kind': 'raw', 'provider': 'fixture provider', 'source_uri': 'https://example.org', 'provenance': {}})
            b['provenance']['source_refs'].append({'source_id': source_id, 'version': version})
            rel = 'research_comparison_evidence_not_independent_verification_or_proof_of_construction'
            b['provenance']['source_relationships'].append({'source_id': source_id, 'version': version, 'relationship': rel})
            x.seed['region_traces'][0]['input_trace'][0]['source_citations'].append({'source_id': source_id, 'version': version, 'relationship': rel, 'role': 'supporting_research_evidence', 'sha256': sha, 'bucket': bucket, 'key': r2key})
        coords = line['coordinates']
        a, z = coords[0], coords[-1]
        route = {'type': 'LineString', 'coordinates': [z, [z[0], 30.0], [a[0], 30.0], a]}
        x.snapshot['routes'][0].update(geometry=route, geometry_sha256=geomhash(route))
        region = x.snapshot['seed_regions'][0]
        region['segments'][0].update(id=gate.BOUNDARY, end=len(coords))
        region['segments'][1]['end'] = 4
        x.snapshot['land_baseline_policy']['boundary_ids'] = [gate.BOUNDARY]
        records = {('boundary', gate.BOUNDARY): b, ('route', 'q'): x.snapshot['routes'][0]}
        region['geometry_sha256'] = gate.assembled_region_hash(region, records)
        traces = x.seed['region_traces'][0]['input_trace']
        traces[0].update(id=gate.BOUNDARY, end=len(coords))
        traces[1].update(end=4, geometry_sha256=geomhash(route))
        traces[1]['closure_proof']['geometry_sha256'] = geomhash(route)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / 'snapshot.json'
            snapshot.write_text(json.dumps(x.snapshot, sort_keys=True, separators=(',', ':')))
            request = root / 'request.json'
            request.write_text(json.dumps({'inputs': {'snapshot': {'path': str(snapshot), 'sha256': gate.digest(snapshot)}}}, sort_keys=True, separators=(',', ':')))
            request_sha = gate.digest(request)
            kwargs = dict(request_path=request, request_sha256=request_sha, recipe=os.environ['CAUCASUS_RECIPE'], recipe_sha256=recipe_sha, hydro=os.environ['CAUCASUS_HYDRO'], author=os.environ['CAUCASUS_AUTHOR'])
            effective, source_trace = derive_verified(**kwargs)
            derived = effective['mainland_boundaries'][0]
            traces[0]['geometry_sha256'] = derived['geometry_sha256']
            x.seed['region_traces'][0]['geometry_sha256'] = effective['seed_regions'][0]['geometry_sha256']
            x.seed['decision_snapshot_sha256'] = gate.digest(snapshot)
            # The current frozen validator must not accept derived seed traces
            # against the unchanged selected view.
            with self.assertRaisesRegex(ValueError, 'region decision/trace mismatch'):
                contracts.validate_selected_seed_decisions(x.snapshot, x.seed, x.groups, x.codes, x.metric)
            pins = {n: adapter.digest(adapter.HERE / n) for n in adapter.CODE}
            result, _ = adapter.validate(contracts.validate_selected_seed_decisions, x.seed, x.groups, x.codes, x.metric, code_sha256=pins, **kwargs)
            self.assertEqual(result, x.snapshot['land_baseline_policy'])
            producer_sha = 'e' * 64
            report = dict(source_trace['source_gate'], request_sha256=request_sha,
                          seed_producer_executed=True, seed_producer_sha256=producer_sha,
                          seed_worker_sha256=None, effective_snapshot=source_trace['effective_snapshot'])
            cfg = {'recipe': {'path': str(kwargs['recipe']), 'sha256': recipe_sha},
                   'hydro': {'path': str(kwargs['hydro']), 'sha256': gate.SOURCE_PINS[next(iter(gate.SOURCE_PINS))]},
                   'author': {'path': str(kwargs['author']), 'sha256': list(gate.SOURCE_PINS.values())[1]},
                   'code_sha256': {n: gate.digest(binding.HERE / n) for n in binding.CODE}}
            result, _ = binding.validate_seed(cfg, request, request_sha, report, producer_sha,
                                              contracts.validate_selected_seed_decisions, x.seed,
                                              x.groups, x.codes, x.metric)
            self.assertEqual(result, x.snapshot['land_baseline_policy'])


if __name__ == '__main__':
    unittest.main()
