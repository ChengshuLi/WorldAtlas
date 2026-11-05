"""Bounded real-GDAL region handoff; not a land compiler or map build.

Requires CAUCASUS_DERIVED_GEOJSON and the mainland-seed-l2 directory on
PYTHONPATH. The closure and proof are synthetic and are not geographic evidence.
"""
import json
import os
import unittest
from pathlib import Path

from caucasus_seed_gate import BOUNDARY, SOURCE_PINS, SOURCE_LOCATIONS, assembled_region_hash


@unittest.skipUnless(os.environ.get('CAUCASUS_DERIVED_GEOJSON'), 'derived geometry path not supplied')
class RealGdalHandoff(unittest.TestCase):
    def test_source_line_is_consumed_by_real_region_builder(self):
        from regions import assemble, geometry_hash
        line = json.loads(Path(os.environ['CAUCASUS_DERIVED_GEOJSON']).read_bytes())
        self.assertEqual(geometry_hash(line), '2f2f6c6777fe080fcbf13a526caad22b7b883fc982d3ff0492b91e082d6f06b6')
        coordinates = line['coordinates']
        start, end = coordinates[0], coordinates[-1]
        route = {'type': 'LineString', 'coordinates': [end, [end[0], 30.0], [start[0], 30.0], start]}
        refs = [{'source_id': s, 'version': v, 'relationship': 'research_comparison_evidence_not_independent_verification_or_proof_of_construction',
                 'role': 'supporting_research_evidence'} for s, v in SOURCE_PINS]
        records = {
            ('boundary', BOUNDARY): {'id': BOUNDARY, 'kind': 'boundary', 'revision_id': 'fixture',
                'execution_status': 'selected_for_research', 'geometry': line, 'geometry_sha256': geometry_hash(line),
                'geometry_hash_method': 'binary64-sorted-compact-geojson-v1', 'qualified_source_refs': refs,
                'lineage_status': 'incomplete'},
            ('route', 'fixture-route'): {'id': 'fixture-route', 'kind': 'route', 'role': 'water_closure',
                'revision_id': 'fixture', 'execution_status': 'selected_for_research', 'geometry': route,
                'geometry_sha256': geometry_hash(route), 'geometry_hash_method': 'binary64-sorted-compact-geojson-v1',
                'closure_method': 'physical_water_closure_v1', 'provenance': {'lineage_status': 'incomplete',
                'source_refs': [{'source_id': 'synthetic', 'version': '1'}]}, 'lineage_status': 'incomplete'},
        }
        catalog = {k: {'kind': 'raw', 'sha256': sha, 'bucket': SOURCE_LOCATIONS[k][0], 'key': SOURCE_LOCATIONS[k][1],
                       'origin': 'fixture citation'} for k, sha in SOURCE_PINS.items()}
        catalog[('synthetic', '1')] = {'kind': 'raw', 'sha256': 'a' * 64, 'bucket': 'fixture', 'key': 'fixture', 'origin': 'fixture'}
        region = {'region_id': 'fixture', 'revision_id': 'fixture', 'execution_status': 'selected_for_research',
                  'geometry_hash_method': 'binary64-sorted-compact-geojson-v1', 'witnesses': [], 'segments': [
                      {'kind': 'boundary', 'id': BOUNDARY, 'start': 0, 'end': len(coordinates), 'reverse': False},
                      {'kind': 'route', 'id': 'fixture-route', 'start': 0, 'end': 4, 'reverse': False}]}
        region['geometry_sha256'] = assembled_region_hash(region, records)
        def closure_check(record, pts):
            return {'schema': 'physical-water-closure-proof-v1', 'status': 'valid',
                    'geometry_sha256': geometry_hash({'type': 'LineString', 'coordinates': [[float(x), float(y)] for x, y in pts]}),
                    'physical_rows_sha256': 'b' * 64, 'physical_runs_sha256': 'c' * 64,
                    'physical_report_sha256': 'd' * 64, 'checker_sha256': 'e' * 64, 'contract_sha256': 'f' * 64}
        geom, report = assemble('fixture', records, region, catalog, closure_check,
                                physical_rows_sha256='b' * 64, physical_runs_sha256='c' * 64,
                                physical_report_sha256='d' * 64, checker_sha256='e' * 64,
                                closure_contract_sha256='f' * 64, guard=lambda: None)
        self.assertEqual(geometry_hash(geom), region['geometry_sha256'])
        self.assertEqual(report['input_trace'][0]['geometry_sha256'], geometry_hash(line))
        print('bounded GDAL region geometry:', region['geometry_sha256'])


if __name__ == '__main__':
    unittest.main()
