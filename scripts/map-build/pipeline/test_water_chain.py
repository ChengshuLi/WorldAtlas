"""Exercise actual ocean -> closed water -> final plan -> complete final grid."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import run_pipeline as pipeline

sys.path[:0] = [str(pipeline.SCRIPTS / 'water'),
                str(pipeline.SCRIPTS / 'stages/ocean'), str(pipeline.SCRIPTS)]
from map_build.water.ocean import engine as ocean
from map_build.water import streaming_closed_water as closed
import compose_direct
import compose_full_water_grid as common
import prepare_final_plan
from test_closed_water_core import policy_snapshot
from test_helpers import rle


class FinalGridChain(unittest.TestCase):
    def test_real_processing_chained_through_final_output(self):
        width, height = 12, 5
        physical = np.full((height, width), 17, dtype=np.uint32)
        prefill = physical.copy()
        land = physical.copy()
        for x in (0, 3, 6, 9):
            physical[0, x], prefill[0, x], land[0, x] = 1, 0, 1
        physical[2, 1], prefill[2, 1], land[2, 1] = 1, 0, 1
        pr, pu = rle(physical)
        qr, qu = rle(prefill)
        lr, lu = rle(land)
        snapshot = policy_snapshot()
        snapshot.update({'schema': 'worldatlas-geography-decision-draft-evidence-v1',
                         'source': 'neon-export', 'entity_revision': {'id': 'entities', 'status': 'draft'}})
        snapshot['endpoints'] = [{'endpoint_id': 'top', 'longitude': '-30', 'latitude': '90'},
                                 {'endpoint_id': 'bottom', 'longitude': '-30', 'latitude': '-60'}]
        snapshot['routes'] = [{'route_id': 'r0', 'route_type': 'meridian', 'parameters': {},
                               'points': [{'ordinal': 0, 'endpoint_id': 'top'},
                                          {'ordinal': 1, 'endpoint_id': 'bottom'}]}]
        snapshot['ocean_seeds'] = []
        for i, x in enumerate((0, 3, 6, 9)):
            eid, sid = 100 + i, f's{i}'
            snapshot['endpoints'].append({'endpoint_id': sid,
                'longitude': str(-180 + (x + .5) * 30), 'latitude': '75'})
            snapshot['ocean_seeds'].append({'seed_id': sid, 'endpoint_id': sid, 'entity_id': eid})
            snapshot['category_bindings'].append({'code': 7 + i, 'entity_id': eid, 'physical_class': 'water'})
        snapshot['policies'].append({'id': 'ocean', 'kind': 'ocean_fill',
            'evidence': {'execution_status': 'selected_for_research'}, 'definition': {
                'connectivity': 4, 'wrap_longitude': True, 'barrier_tie_rule': 'left-of-oriented-route',
                'unseeded_policy': 'report-only', 'route_ids': ['r0'], 'seed_ids': ['s0', 's1', 's2', 's3']}})
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            inputs = root / 'inputs'
            inputs.mkdir()
            timer = pipeline.Timing(root / 'events.jsonl')
            def binary(name, data):
                path = inputs / name
                path.write_bytes(data)
                return path
            prp, pup = binary('physical-rows', pr.tobytes()), binary('physical-runs', pu.tobytes())
            qrp, qup = binary('prefill-rows', qr.tobytes()), binary('prefill-runs', qu.tobytes())
            snapshot_path = pipeline.write(inputs / 'snapshot.json', snapshot)
            snapshot_hash = pipeline.sha(snapshot_path)
            plan = pipeline.write(inputs / 'prefill-plan.json', {
                'schema': 'worldatlas-full-grid-composition-plan-v1',
                'grid': {'width': width, 'height': height}, 'land_input_kind': 'direct-research',
                'decision_revision_status': 'draft', 'decision_snapshot_sha256': snapshot_hash,
                'decision_revision': 'draft', 'entity_revision': 'entities', 'research_shore_method': None})
            audit = pipeline.write(inputs / 'prefill-audit.json', {
                'schema': 'worldatlas-prefill-class-rle-audit-v1', 'status': 'staged-not-published',
                'land_input_kind': 'direct-research', 'source_plan_sha256': pipeline.sha(plan),
                'decision_snapshot_sha256': snapshot_hash, 'decision_revision': 'draft',
                'entity_revision': 'entities', 'research_shore_method': None,
                'residual_eligible_water_cells': 5,
                'output': {'rows_sha256': pipeline.sha(qrp), 'runs_sha256': pipeline.sha(qup)}})
            pins = {'physical_rows_sha256': pipeline.sha(prp), 'physical_runs_sha256': pipeline.sha(pup),
                    'prefill_rows_sha256': pipeline.sha(qrp), 'prefill_runs_sha256': pipeline.sha(qup),
                    'prefill_audit_sha256': pipeline.sha(audit), 'prefill_plan_sha256': pipeline.sha(plan)}
            ocean_out = root / 'ocean'
            with timer.measure('water', 'ocean'):
                ocean.run(snapshot, snapshot_hash, prp, pup, qrp, qup, ocean_out,
                          width, height, pins, tile_height=2)
            partition = ocean_out / 'partition/manifest.json'
            cuts = ocean_out / 'barrier_edges.u32le'
            pins['source_cut_edges_sha256'] = pipeline.sha(cuts)
            pins['partition_manifest_sha256'] = pipeline.sha(partition)
            with timer.measure('water', 'closed'):
                result = closed.run(snapshot, snapshot_hash, (pr, pu), (qr, qu), (lr, lu),
                    partition, ocean_out / 'partition/unseeded_rows.u64le',
                    ocean_out / 'partition/unseeded_component_spans.u32le', cuts,
                    root / 'closed', width, height, 180, pins)
            self.assertEqual(result['assigned_cells'], 1)
            self.assertEqual(result['pending_cells'], 0)
            spec = {key: pipeline.pin(path) for key, path in {
                'plan': plan, 'audit': audit, 'rows': qrp, 'runs': qup,
                'ocean': ocean_out / 'ocean-layer-manifest.json', 'summary': ocean_out / 'run-summary.json',
                'closed': root / 'closed/manifest.json', 'partition': partition}.items()}
            final_plan = root / 'final-plan.json'
            with timer.measure('water', 'prepare-final'):
                prepare_final_plan.make(spec, final_plan)
            argv = ['compose', '--plan', str(final_plan), '--input-root', str(root),
                    '--out', str(root / 'final'), '--allow-unverified-snapshot', '--allow-draft-snapshot']
            # Production APIs use the canonical global grid. Reduce only test
            # dimensions, without replacing any producer, pin or coverage check.
            with timer.measure('water', 'compose'), patch.object(common, 'W', width), \
                    patch.object(common, 'H', height), patch.object(common, 'GRID', {'width': width, 'height': height}), \
                    patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
                compose_direct.main()
            report = pipeline.read(root / 'final/report.json')
            self.assertEqual(sum(report['counts'][str(i)] for i in range(7, 11)), 4)
            self.assertEqual(report['counts']['1'], 1)
            self.assertEqual(report['counts']['17'], width * height - 5)
            rows = np.fromfile(root / 'final/rows.u32le', dtype='<u4')
            runs = np.fromfile(root / 'final/runs.u32le', dtype='<u4').reshape(-1, 2)
            expected = physical.copy()
            for i, x in enumerate((0, 3, 6, 9)):
                expected[0, x] = 7 + i
            expected[2, 1] = 1
            for y in range(height):
                start = 0
                for end, code in runs[int(rows[y]):int(rows[y + 1])]:
                    self.assertTrue(np.all(expected[y, start:int(end)] == code))
                    start = int(end)
                self.assertEqual(start, width)
            self.assertFalse(report['publishable'])
            timer.completed_groups.add('water')
            self.assertTrue(timer.summary(None)['water']['complete'])
            self.assertEqual(pipeline.sha(root / 'final/runs.u32le'), report['output']['runs_sha256'])


if __name__ == '__main__':
    unittest.main()
