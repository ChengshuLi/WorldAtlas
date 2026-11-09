import copy
import math
import os
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'lydekker-regional-rule'))
import satellite_geodesic as reference
from satellite_index import apply_satellites, RunIndex


class SatelliteIndexTests(unittest.TestCase):
    def test_unchanged_workflow_with_runtime_dependencies(self):
        if not os.environ.get('MIXED_CLAIMS_PATH') or not os.environ.get('RUN_PAIR_PATH'):
            self.skipTest('reviewed replay and WGS84 module paths required')
        import component_index
        import regional_runtime
        import regional_workflow
        import satellite_index
        import test_regional_workflow
        workflow = SimpleNamespace(research=regional_workflow.research,
                                   require_boo_east=regional_workflow.require_boo_east)
        modules = {'component_index': component_index, 'satellite_index': satellite_index,
                   'regional_workflow': workflow}
        prepared = []
        def accelerated(rows, runs, grid, *args, **kwargs):
            runtime = regional_runtime.prepare(modules, {'component_rows': rows, 'component_runs': runs}, grid, {})
            prepared.append(runtime)
            result = runtime['dependencies']['research'](rows, runs, grid, *args, **kwargs)
            runtime['verify']()
            return result
        result = unittest.TestResult()
        with patch.object(regional_workflow, 'research', accelerated):
            test_regional_workflow.TestWorkflow('test_end_to_end_research_without_map_write').run(result)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failures, [])
        self.assertEqual(len(prepared), 3)
        self.assertIs(regional_workflow.research, workflow.research)

    def test_reviewed_satellite_behavior(self):
        import test_satellite_geodesic as reviewed_tests
        with patch.object(reviewed_tests, 'apply_satellites', apply_satellites), patch.object(reference, 'apply_satellites', apply_satellites):
            result = unittest.TestResult()
            unittest.defaultTestLoader.loadTestsFromModule(reviewed_tests).run(result)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failures, [])

    def test_random_differential_results_and_exact_solver_calls(self):
        from pyproj import Geod
        geod = Geod(ellps='WGS84')
        rng = random.Random(20261107)
        for width, north, height, radius in [(360, 90, 180, 400000), (36000, 90, 20, 5000),
                                             (36000, -89.8, 20, 5000), (36000, .1, 20, 50000)]:
            for _ in range(8):
                runs, components = {}, {}
                for root in range(1, 30):
                    y = rng.randrange(height)
                    a = rng.choice([rng.randrange(width - 5), rng.randrange(5), width - rng.randrange(1, 5)])
                    count = rng.randrange(1, min(5, width - a) + 1)
                    runs[root] = [(y, a, a + count)]
                    if y + 1 < height and rng.randrange(2):
                        runs[root].append((y + 1, a, a + count))
                    total = sum(b - a for _, a, b in runs[root])
                    components[root] = {'total': total, 'in_scope': total}
                proposals = {r: {'code': rng.choice([18, 22]), 'basis': rng.choice([
                    'whole_component_line_side', 'selected_affiliation', 'inferred_source_extent_group_convention'])}
                              for r in runs if rng.randrange(3)}
                result = {'proposals': proposals, 'review': {r: 'outside_line_latitude' for r in runs if r not in proposals},
                          'competitor_targets': {r: rng.choice([18, 22]) for r in runs if rng.randrange(2)}}
                anchors = {r: {'code': p['code'], 'source_id': 'fixture', 'source_feature_id': str(r),
                               'source_version': 'v1', 'source_sha256': 'a'*64, 'main_island_evidence': 'fixture'}
                           for r, p in proposals.items() if p['basis'] == 'selected_affiliation'}
                calls = []
                def exact(y, a, b, yy, c, d, width, *, north, incumbent, tol):
                    calls.append((y, a, b, yy, c, d, incumbent, tol))
                    step = 360/width
                    distance = min(geod.inv(-180 + (x + .5)*step, north - (y + .5)*step,
                                            -180 + (z + .5)*step, north - (yy + .5)*step)[2]
                                   for x in range(a, b) for z in range(c, d))
                    return (distance if distance <= incumbent + tol else None), None
                kwargs = dict(width=width, north=north, max_satellite_cells=4, max_gap_m=radius,
                              candidate_roots=set(runs), allow_unanchored_nearest=True)
                expected = reference.apply_satellites(copy.deepcopy(result), components, runs, anchors, exact, **kwargs)
                old_calls, calls = calls, []
                actual = apply_satellites(copy.deepcopy(result), components, runs, anchors, exact, **kwargs)
                self.assertEqual(actual, expected)
                self.assertEqual(sorted(calls), sorted(old_calls))

    def test_query_contains_every_run_passing_reviewed_lower_bound(self):
        rng = random.Random(7)
        for width, north, height, radius in [(360, 90, 180, 300000), (36000, 90, 100, 5000), (36000, .5, 100, 5000)]:
            runs = {r: [(rng.randrange(height), rng.randrange(width - 20), 0)] for r in range(100)}
            runs = {r: [(y, a, a + rng.randrange(1, 20))] for r, [(y, a, _)] in runs.items()}
            components = {r: {'total': b - a} for r, [(y, a, b)] in runs.items()}
            dy = math.ceil(radius/reference.MIN_MERIDIONAL_RADIUS*180/math.pi/(360/width)) + 1
            index = RunIndex(runs, components, set(runs), width, north, radius, dy)
            for root, [(y, a, b)] in runs.items():
                nearby = index.nearby(root, runs[root], components)
                for parent, [(yy, c, d)] in runs.items():
                    if components[parent]['total'] <= components[root]['total']:
                        continue
                    if reference.run_lower_bound(y, a, b, yy, c, d, width, north) <= radius:
                        self.assertIn((yy, c, d), nearby[parent][0])


if __name__ == '__main__':
    unittest.main()
