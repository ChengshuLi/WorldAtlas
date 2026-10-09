"""Positive/negative controls for geometry regression, not territorial approval."""
import importlib.util
import pathlib
import sys
import unittest
import json
import hashlib
import tempfile
import subprocess
import copy
from unittest.mock import patch

from shapely.geometry import Polygon, MultiPolygon, box, mapping, shape

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('geographic_regression', ROOT / 'scripts/check-geographic-regression.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
from evidence import geometry as shared_geometry


def features(**geometries):
    return {identity: {'type': 'Feature', 'id': identity,
        'properties': {'id': identity, 'name': identity}, 'geometry': mapping(geometry)}
        for identity, geometry in geometries.items()}


class EffectivePrimitiveControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('effective_wrapper', ROOT / 'scripts/run-geographic-check.py')
        cls.wrapper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.wrapper)

    def addition(self, geometry, component='addition', target='land', base=None):
        base = base or features(land=box(0, 0, 1, 1))
        return {'component_id': component, 'target_id': target,
                'base_geometry_sha256': gate.geometry_hash(base[target]), 'geometry': mapping(geometry)}

    def test_shared_edge_literal_set_preserves_original_base(self):
        base = features(land=box(0, 0, 1, 1), neighbor=box(3, 0, 4, 1))
        self.assertFalse(MultiPolygon([box(0, 0, 1, 1), box(1, 0, 2, 1)]).is_valid)
        before = copy.deepcopy(base)
        result = self.wrapper.compare_effective_primitives(gate, base, base,
                  {'baseline': [], 'candidate': [self.addition(box(1, 0, 2, 1), base=base)]})
        self.assertEqual(result['status'], 'no-new-regression')
        self.assertEqual(result['effective_set_domain'], 'literal-base-or-complete-additions:v2')
        self.assertEqual(base, before)

    def test_zero_cell_primitive_loss_is_not_hidden_by_native_conservation(self):
        base = features(land=box(0, 0, 1, 1))
        addition = self.addition(box(1, 0, 2, 1), base=base)
        result = self.wrapper.compare_effective_primitives(gate, base, base,
                  {'baseline': [addition], 'candidate': []})
        self.assertEqual(result['status'], 'regressions-found')
        self.assertTrue(any(f['properties']['kind'] == 'lost-previous-coverage'
                            for f in result['findings']['features']))

    def test_other_owner_overlap_is_rejected_but_internal_same_owner_is_not(self):
        base = features(land=box(0, 0, 1, 1), neighbor=box(2, 0, 3, 1))
        conflicting = self.wrapper.compare_effective_primitives(gate, base, base,
                  {'baseline': [], 'candidate': [self.addition(box(1, 0, 2.5, 1), base=base)]})
        self.assertEqual(conflicting['status'], 'regressions-found')
        self.assertTrue(any(f['properties']['kind'] == 'new-pair-overlap'
                            for f in conflicting['findings']['features']))
        internal = self.wrapper.compare_effective_primitives(gate, base, base,
                  {'baseline': [], 'candidate': [self.addition(box(.5, 0, 1.5, 1), base=base)]})
        self.assertEqual(internal['status'], 'no-new-regression')

    def test_duplicate_stale_and_invalid_complete_primitive_rejected(self):
        base = features(land=box(0, 0, 1, 1)); addition = self.addition(box(1, 0, 2, 1), base=base)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.wrapper.compare_effective_primitives(gate, base, base,
                  {'baseline': [], 'candidate': [addition, addition]})
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.wrapper.compare_effective_primitives(gate, base, base,
                  {'baseline': [], 'candidate': [{**addition, 'base_geometry_sha256': '0' * 64}]})
        invalid = Polygon([(1, 0), (2, 1), (1, 1), (2, 0), (1, 0)])
        result = self.wrapper.compare_effective_primitives(gate, base, base,
                  {'baseline': [], 'candidate': [self.addition(invalid, base=base)]})
        self.assertEqual(result['status'], 'blocked-invalid-or-unsupported-geometry')


class RegressionControls(unittest.TestCase):
    def test_prepared_invalid_actual_translation(self):
        from unittest.mock import patch
        from shapely.geometry import Polygon, MultiPolygon, box, mapping
        from evidence.geometry import canonical_prepared_land
        original = MultiPolygon([box(179,0,180,1),box(-180,0,-179,1)])
        invalid = Polygon([(-181,0),(-180,1),(-181,1),(-180,0),(-181,0)])
        with patch('evidence.geometry.translate', return_value=invalid):
            with self.assertRaisesRegex(ValueError, 'actually translated') as caught:
                canonical_prepared_land(original)
        self.assertEqual(caught.exception.invalid_translated_members[0], mapping(invalid))
        self.assertTrue(original.is_valid)

    def test_identical_periodic_fixture_has_explicit_prepared_representation(self):
        candidate = MultiPolygon([box(179, 0, 180, 1), box(-180, 0, -179, 1)])
        raw = gate.canonical_json(mapping(candidate))
        contacts = []
        result = shared_geometry.canonical_prepared_land(candidate, seam_contacts=contacts)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.area, 2)
        self.assertEqual(len(contacts), 2)
        self.assertEqual(raw, gate.canonical_json(mapping(candidate)))
        self.assertEqual(gate.compare(features(land=candidate), features(land=candidate))['status'],
                         'no-footprint-change')
        with self.assertRaisesRegex(ValueError, 'Invalid original periodic multipart topology'):
            shared_geometry.canonical_land(candidate)

    def test_prepared_domain_retains_nonseam_and_tiny_overlap_rejections(self):
        across = Polygon([(179, 0), (-179, 0), (-179, 1), (179, 1), (179, 0)])
        periodic_overlap = Polygon([(-179, 0), (179.999999999, 0),
                                    (179.999999999, 1), (-179, 1), (-179, 0)])
        candidates = [self.tiny_invalid_multipart(),
                      MultiPolygon([box(0, 0, 1, 1), box(1, 0, 2, 1)]),
                      MultiPolygon([across, box(-179, 0, -178, 1)]),
                      MultiPolygon([box(179, 0, 180, 1), periodic_overlap]),
                      MultiPolygon([box(179, 0, 179.999999, 1),
                                    box(179.999999, 0, 180, 1)])]
        for candidate in candidates:
            with self.subTest(geometry=mapping(candidate)):
                with patch.object(shared_geometry, 'union_all', side_effect=AssertionError('union must not execute')):
                    with self.assertRaisesRegex(ValueError, 'Invalid original'):
                        shared_geometry.canonical_prepared_land(candidate)

    def test_prepared_domain_rejects_mixed_seam_and_interior_defect(self):
        candidate = MultiPolygon([box(179, 0, 180, 1), box(-180, 0, -179, 1),
                                  box(0, 0, 1, 1), box(1, 0, 2, 1)])
        with patch.object(shared_geometry, 'union_all', side_effect=AssertionError('union must not execute')):
            with self.assertRaisesRegex(ValueError, 'Invalid original multipart topology'):
                shared_geometry.canonical_prepared_land(candidate)

    def test_prepared_disjoint_point_hole_and_single_crossing_positives(self):
        hole = Polygon([(0, 0), (3, 0), (3, 3), (0, 3), (0, 0)],
                       [[(1, 1), (2, 1), (2, 2), (1, 2), (1, 1)]])
        candidates = [MultiPolygon([box(0, 0, 1, 1), box(2, 0, 3, 1)]),
                      MultiPolygon([box(0, 0, 1, 1), box(1, 1, 2, 2)]),
                      MultiPolygon([hole, box(4, 0, 5, 1)]),
                      Polygon([(179, 0), (-179, 0), (-179, 1), (179, 1), (179, 0)])]
        for candidate in candidates:
            raw = gate.canonical_json(mapping(candidate))
            self.assertTrue(shared_geometry.canonical_prepared_land(candidate).is_valid)
            self.assertEqual(raw, gate.canonical_json(mapping(candidate)))

    def test_prepared_domain_rejects_invalid_member_and_operation_failure(self):
        bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
        with self.assertRaisesRegex(ValueError, 'Invalid unwrapped'):
            shared_geometry.canonical_prepared_land(bowtie)
        candidate = MultiPolygon([box(179, 0, 180, 1), box(-180, 0, -179, 1)])
        with patch.object(shared_geometry, '_prepared_seam_contact', side_effect=ValueError('synthetic operation failure')):
            with self.assertRaisesRegex(ValueError, 'synthetic operation failure'):
                shared_geometry.canonical_prepared_land(candidate)

    def test_complete_three_current_features_preserve_all_seam_contacts(self):
        path = ROOT / 'coordination/engineering/prepared-geography-dateline-domain-20261007/diagnosis/complete-three-counterexamples.json'
        rows = json.loads(path.read_bytes())['rows']
        self.assertEqual(len(rows), 3)
        for row in rows:
            candidate = shape(row['whole_feature']['geometry'])
            original = gate.canonical_json(mapping(candidate))
            contacts = []
            self.assertTrue(shared_geometry.canonical_prepared_land(candidate, seam_contacts=contacts).is_valid)
            actual = {(c['member'], c['other_member'], c['longitude_shift']): c['contact_geometry'] for c in contacts}
            expected = {(c['i'], c['j'], c['shift']): c['intersection']['geometry']
                        for c in row['all_intersecting_directed_pairs'] if not c['combined_valid']}
            self.assertEqual(set(actual), set(expected))
            for key in actual:
                self.assertEqual(gate.canonical_json(actual[key]), gate.canonical_json(expected[key]))
            self.assertEqual(original, gate.canonical_json(mapping(candidate)))
            with self.assertRaisesRegex(ValueError, 'Invalid original periodic'):
                shared_geometry.canonical_land(candidate)

    def test_whole_original_sources_retain_distinct_domain_failures(self):
        path = ROOT / 'coordination/engineering/prepared-geography-dateline-domain-20261007/diagnosis/complete-source-predecessor-lineage.json'
        rows = json.loads(path.read_bytes())['matches']
        for row in rows:
            original = shape(row['whole_original_feature']['geometry'])
            if row['original_source_key'] == 'gb:FJI:ADM2':
                with self.assertRaisesRegex(ValueError, 'Expected finite longitude'):
                    shared_geometry.canonical_prepared_land(original)
            else:
                self.assertTrue(shared_geometry.canonical_prepared_land(original).is_valid)
                with self.assertRaisesRegex(ValueError, 'Invalid original periodic'):
                    shared_geometry.canonical_land(original)
            self.assertFalse(row['exact_canonical_geometry_equal'])
            self.assertFalse(row['source_equals_current_pointset'])

    def test_metadata_cannot_choose_domain_or_approve_invalid_member(self):
        invalid = features(land=self.tiny_invalid_multipart())
        invalid['land']['properties']['metadata'] = {'geometry_domain': shared_geometry.PREPARED_DOMAIN,
                                                    'source_approval': True, 'skip_geometry_validation': True}
        report = gate.compare(invalid, invalid)
        self.assertEqual(report['status'], 'blocked-invalid-or-unsupported-geometry')
        self.assertEqual(report['geometry_domain'], shared_geometry.PREPARED_DOMAIN)
        self.assertEqual(report['geometry_errors'][0]['original_geometry'], invalid['land']['geometry'])
        with self.assertRaises(TypeError):
            shared_geometry.canonical_land(shape(invalid['land']['geometry']), domain='untrusted-approval')

    def test_complete_binding_rejects_unknown_domain_or_forged_roster_and_release(self):
        fixture = self.trusted_fixture()
        try:
            snap = gate.snapshot(fixture.repo, fixture.baseline)
            binding = gate.prepared_inventory_binding(snap)
            gate.validate_prepared_inventory_binding(snap, binding)
            for key, value in [('domain', 'unknown'), ('commit', '0'*40), ('feature_count', 1),
                               ('feature_geometry_bindings_sha256', '0'*64),
                               ('release_and_hierarchy_pins', {}), ('files', [])]:
                wrong = copy.deepcopy(binding)
                wrong[key] = value
                with self.subTest(field=key):
                    with self.assertRaisesRegex(ValueError, 'complete immutable inventory binding mismatch'):
                        gate.validate_prepared_inventory_binding(snap, wrong)
            wrong = copy.deepcopy(snap)
            wrong['features'].pop('left')
            with self.assertRaisesRegex(ValueError, 'binding mismatch'):
                gate.validate_prepared_inventory_binding(wrong, binding)
        finally:
            fixture.close()

    def test_trusted_pr_and_combined_candidate_use_prepared_domain_bindings(self):
        fixture = self.trusted_fixture()
        try:
            seam = MultiPolygon([box(179, 0, 180, 1), box(-180, 0, -179, 1)])
            fixture.write('data/geography/part.json', {'type': 'FeatureCollection',
                          'features': list(features(seam=seam, far=box(10, 0, 11, 1)).values())})
            baseline = fixture.commit('prepared-seam-baseline')
            fixture.baseline = baseline
            fixture.git('checkout', '-qb', 'prepared-proposal', baseline)
            fixture.write('data/geography/part.json', {'type': 'FeatureCollection',
                          'features': list(features(seam=seam, far=box(10, 0, 11.1, 1)).values())})
            helper = fixture.repo / 'scripts/evidence/geometry.py'
            helper.write_text(helper.read_text() + "\nPREPARED_DOMAIN = 'forged-candidate-domain'\n")
            proposed = fixture.commit('valid-prepared-growth')
            result, report = fixture.run(proposed)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report['differential_report']['geometry_domain'], shared_geometry.PREPARED_DOMAIN)
            for vintage, commit in [('baseline', baseline), ('candidate', proposed)]:
                binding = report['differential_report']['prepared_geometry_bindings'][vintage]
                gate.validate_prepared_inventory_binding(gate.snapshot(fixture.repo, commit), binding)
            (fixture.repo / 'geography-check.json').unlink()
            fixture.git('checkout', '-qb', 'prepared-advanced-main', baseline)
            fixture.write('data/geographic-releases/index.json', {'synthetic_context': 'advanced'})
            advanced = fixture.commit('independent-prepared-context')
            fixture.git('merge', '--no-ff', '--no-edit', proposed)
            combined = fixture.git('rev-parse', 'HEAD')
            fixture.baseline = advanced
            result, report = fixture.run(combined)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report['baseline_commit'], advanced)
            self.assertEqual(report['candidate_commit'], combined)
            for vintage, commit in [('baseline', advanced), ('candidate', combined)]:
                binding = report['differential_report']['prepared_geometry_bindings'][vintage]
                gate.validate_prepared_inventory_binding(gate.snapshot(fixture.repo, commit), binding)
        finally:
            fixture.close()

    @staticmethod
    def tiny_invalid_multipart():
        return MultiPolygon([box(0, 0, 1e-6, 1e-6),
                             box(1e-6 - 1e-12, 0, 2e-6, 1e-6)])

    def test_tiny_overlap_rejected_before_union_without_area_waiver(self):
        candidate = self.tiny_invalid_multipart()
        self.assertFalse(candidate.is_valid)
        self.assertGreater(candidate.geoms[0].intersection(candidate.geoms[1]).area, 0)
        with patch.object(shared_geometry, 'union_all', side_effect=AssertionError('union must not execute')):
            with self.assertRaisesRegex(ValueError, 'Invalid original multipart topology'):
                shared_geometry.canonical_land(candidate)
        result = gate.compare(features(land=box(0, 0, 2e-6, 1e-6)), features(land=candidate))
        self.assertEqual(result['status'], 'blocked-invalid-or-unsupported-geometry')
        self.assertEqual(result['geometry_errors'][0]['original_geometry'], mapping(candidate))

    def test_shared_edge_invalidity_rejected_before_union(self):
        candidate = MultiPolygon([box(0, 0, 1, 1), box(1, 0, 2, 1)])
        self.assertEqual(candidate.geoms[0].intersection(candidate.geoms[1]).area, 0)
        with patch.object(shared_geometry, 'union_all', side_effect=AssertionError('union must not execute')):
            with self.assertRaisesRegex(ValueError, 'Invalid original multipart topology'):
                shared_geometry.canonical_land(candidate)

    def test_periodic_shared_edge_between_original_members_rejected(self):
        candidate = MultiPolygon([box(179, 0, 180, 1), box(-180, 0, -179, 1)])
        self.assertTrue(candidate.is_valid)  # Flat longitude misses the periodic shared edge.
        with patch.object(shared_geometry, 'union_all', side_effect=AssertionError('union must not execute')):
            with self.assertRaisesRegex(ValueError, 'Invalid original periodic multipart topology'):
                shared_geometry.canonical_land(candidate)

    def test_valid_disjoint_and_point_touching_multipart_preserved(self):
        for candidate in [MultiPolygon([box(0, 0, 1, 1), box(2, 0, 3, 1)]),
                          MultiPolygon([box(0, 0, 1, 1), box(1, 1, 2, 2)]),
                          MultiPolygon([box(179, 0, 180, 1), box(-180, 1, -179, 2)])]:
            self.assertTrue(shared_geometry.canonical_land(candidate).is_valid)
            self.assertEqual(gate.compare(features(land=candidate), features(land=candidate))['regressions'], 0)

    def test_shortest_edge_domain_positive_is_not_naive_raw_validity(self):
        across = Polygon([(179, 0), (-179, 0), (-179, 1), (179, 1), (179, 0)])
        candidate = MultiPolygon([across, box(0, 0, 1, 1)])
        self.assertFalse(candidate.is_valid)  # Raw flat longitude falsely overlaps the separate island.
        result = shared_geometry.canonical_land(candidate)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.area, 3)
        self.assertEqual(gate.compare(features(land=candidate), features(land=candidate))['status'], 'no-footprint-change')

    def test_baseline_multipart_defect_retained_even_after_valid_correction(self):
        invalid = features(land=self.tiny_invalid_multipart())
        for candidate in [invalid, features(land=box(0, 0, 2e-6, 1e-6))]:
            result = gate.compare(invalid, candidate)
            self.assertEqual(result['status'], 'blocked-invalid-or-unsupported-geometry')
            baseline = next(e for e in result['geometry_errors'] if e['vintage'] == 'baseline')
            self.assertEqual(baseline['original_geometry'], invalid['land']['geometry'])
            self.assertIsNone(result['regressions'])  # Invalid baseline is not silently certified/normalized.

    def test_island_inside_hole_is_valid_multipart(self):
        outer = box(0, 0, 4, 4).difference(box(1, 1, 3, 3))
        candidate = MultiPolygon([outer, box(1.5, 1.5, 2.5, 2.5)])
        self.assertTrue(candidate.is_valid)
        self.assertEqual(shared_geometry.canonical_land(candidate).area, 13)

    @staticmethod
    def trusted_fixture():
        spec = importlib.util.spec_from_file_location('multipart_trusted_fixture', ROOT / 'test/trusted-geography-check.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.Fixture()

    def test_trusted_pr_and_actual_combined_candidate_block_multipart_defect(self):
        fixture = self.trusted_fixture()
        try:
            def write_part(name, geometries):
                fixture.write(name, {'type': 'FeatureCollection', 'features': list(features(**geometries).values())})
            write_part('data/geography/part.json', {'land': box(0, 0, 2e-6, 1e-6)})
            write_part('data/geography/neighbor.json', {'neighbor': box(10, 0, 11, 1)})
            fixture.write('data/world-index.json', {'parts': ['geography/part.json', 'geography/neighbor.json']})
            baseline = fixture.commit('complete-valid-multipart-baseline')
            fixture.baseline = baseline
            fixture.git('checkout', '-qb', 'proposed', baseline)
            candidate = self.tiny_invalid_multipart()
            write_part('data/geography/part.json', {'land': candidate})
            proposed = fixture.commit('invalid-proposed-multipart')
            result, report = fixture.run(proposed)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(report['gate_status'], 'blocked')
            self.assertFalse(report['candidate_code_executed'])
            self.assertEqual(report['differential_report']['geometry_errors'][0]['vintage'], 'candidate')
            self.assertEqual(gate.canonical_json(report['differential_report']['geometry_errors'][0]['original_geometry']),
                             gate.canonical_json(mapping(candidate)))
            (fixture.repo / 'geography-check.json').unlink()
            fixture.git('checkout', '-qb', 'advanced-main', baseline)
            write_part('data/geography/neighbor.json', {'neighbor': box(10, 0, 10.9, 1)})
            advanced = fixture.commit('independent-main-footprint-change')
            fixture.git('merge', '--no-ff', '--no-edit', proposed)
            combined = fixture.git('rev-parse', 'HEAD')
            self.assertEqual(fixture.git('show', '-s', '--format=%P', combined).split(), [advanced, proposed])
            fixture.baseline = advanced
            result, report = fixture.run(combined)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(report['gate_status'], 'blocked')
            self.assertEqual(report['baseline_commit'], advanced)
            self.assertEqual(report['candidate_commit'], combined)
            self.assertFalse(report['candidate_code_executed'])
        finally:
            fixture.close()

    def test_trusted_source_only_research_remains_not_applicable(self):
        fixture = self.trusted_fixture()
        try:
            fixture.write('research/geography/synthetic-source-only/proposal.json',
                          {'proposed_geometry': mapping(self.tiny_invalid_multipart()), 'source_approval': False})
            candidate = fixture.commit('source-only-proposal-no-live-footprint-import')
            result, report = fixture.run(candidate)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report['status'], 'not-applicable')
            self.assertIsNone(report['regressions'])
            self.assertFalse(report['candidate_code_executed'])
            self.assertFalse(report['source_approval'])
            self.assertEqual(report['baseline_input_inventory'], report['candidate_input_inventory'])
        finally:
            fixture.close()

    def test_one_sided_shrink_with_unchanged_neighbor(self):
        before = features(left=box(0, 0, 1, 1), right=box(1, 0, 2, 1))
        after = features(left=box(0, 0, .9, 1), right=box(1, 0, 2, 1))
        report = gate.compare(before, after)
        self.assertEqual(report['status'], 'regressions-found')
        self.assertEqual(report['changed_location_ids'], ['left'])
        self.assertEqual(report['affected_neighbor_ids'], ['right'])
        finding = report['findings']['features'][0]
        self.assertAlmostEqual(shape(finding['geometry']).area, .1)
        self.assertEqual(finding['properties']['location_ids'], ['left', 'right'])
        self.assertEqual(len(finding['properties']['before']), 2)
        self.assertEqual(len(finding['properties']['after']), 2)
        x, y = finding['properties']['coordinate']
        self.assertTrue(.9 < x < 1 and 0 < y < 1)
        self.assertEqual(finding['properties']['physical_classification'], 'unverified')

    def test_combined_neighbor_changes_expose_gap_even_when_isolated_tests_pass(self):
        before = features(left=box(0, 0, 1.1, 1), right=box(.9, 0, 2, 1))
        left = features(left=box(0, 0, .95, 1), right=box(.9, 0, 2, 1))
        right = features(left=box(0, 0, 1.1, 1), right=box(1.05, 0, 2, 1))
        combined = features(left=box(0, 0, .95, 1), right=box(1.05, 0, 2, 1))
        self.assertEqual(gate.compare(before, left)['regressions'], 0)
        self.assertEqual(gate.compare(before, right)['regressions'], 0)
        self.assertEqual(gate.compare(before, combined)['regressions'], 1)

    def test_valid_joint_boundary_move(self):
        before = features(left=box(0, 0, 1, 1), right=box(1, 0, 2, 1))
        after = features(left=box(0, 0, .9, 1), right=box(.9, 0, 2, 1))
        result = gate.compare(before, after)
        self.assertEqual(result['status'], 'no-new-regression')
        self.assertEqual(result['regressions'], 0)

    def test_existing_gap_and_overlap_are_not_new_regressions(self):
        gap = features(left=box(0, 0, .9, 1), right=box(1, 0, 2, 1))
        overlap = features(left=box(0, 0, 1.1, 1), right=box(1, 0, 2, 1))
        self.assertEqual(gate.compare(gap, gap)['status'], 'no-footprint-change')
        after = features(left=box(0, 0, 1.1, 1), right=box(1, 0, 2.1, 1))
        self.assertEqual(gate.compare(overlap, after)['regressions'], 0)

    def test_new_overlap_is_exact_shape_not_whole_prior_overlap(self):
        before = features(left=box(0, 0, 1.1, 1), right=box(1, 0, 2, 1))
        after = features(left=box(0, 0, 1.2, 1), right=box(1, 0, 2, 1))
        result = gate.compare(before, after)
        self.assertEqual(result['regressions'], 1)
        feature = result['findings']['features'][0]
        self.assertEqual(feature['properties']['kind'], 'new-pair-overlap')
        self.assertAlmostEqual(shape(feature['geometry']).area, .1)

    def test_islands_holes_and_intentional_water_change_still_require_review(self):
        lake = box(.2, .2, .4, .4)
        mainland = box(0, 0, 1, 1).difference(lake)
        before = features(land=MultiPolygon([mainland, box(2, 0, 2.1, .1)]))
        after = features(land=MultiPolygon([mainland, box(2, 0, 2.2, .1)]))
        self.assertEqual(gate.compare(before, after)['regressions'], 0)
        enlarged_lake = box(.2, .2, .5, .5)
        corrected = features(land=MultiPolygon([box(0, 0, 1, 1).difference(enlarged_lake), box(2, 0, 2.1, .1)]))
        result = gate.compare(before, corrected)
        self.assertEqual(result['regressions'], 1)
        # A source might justify this water change, but geometry alone must not
        # silently waive the review required for intentional lost coverage.
        self.assertEqual(result['findings']['features'][0]['properties']['physical_classification'], 'unverified')

    def test_date_line_shared_boundary(self):
        across = Polygon([(179, 0), (-179, 0), (-179, 1), (179, 1), (179, 0)])
        before = features(across=across)
        smaller = Polygon([(179.1, 0), (-179.1, 0), (-179.1, 1), (179.1, 1), (179.1, 0)])
        result = gate.compare(before, features(across=smaller))
        self.assertEqual(result['regressions'], 2)
        self.assertAlmostEqual(sum(shape(f['geometry']).area for f in result['findings']['features']), .2)
        self.assertTrue(all(abs(f['properties']['coordinate'][0]) > 179 for f in result['findings']['features']))

    def test_tile_edges_do_not_change_result(self):
        before = features(left=box(4, 4, 5, 6), right=box(5, 4, 6, 6))
        after = features(left=box(4, 4, 4.9, 6), right=box(5, 4, 6, 6))
        result = gate.compare(before, after)
        self.assertEqual(result['regressions'], 1)
        self.assertAlmostEqual(shape(result['findings']['features'][0]['geometry']).area, .2)

    def test_date_line_neighbor_identity_on_opposite_side(self):
        before = features(east=box(179, 0, 180, 1), west=box(-180, 0, -179, 1))
        after = features(east=box(179, 0, 179.9, 1), west=box(-180, 0, -179, 1))
        result = gate.compare(before, after)
        self.assertEqual(result['regressions'], 1)
        self.assertEqual(result['affected_neighbor_ids'], ['west'])
        self.assertEqual(result['findings']['features'][0]['properties']['location_ids'], ['east', 'west'])

    def test_invalid_candidate_fails_closed(self):
        before = features(land=box(0, 0, 1, 1))
        after = features(land=Polygon([(0, 0), (1, 1), (0, 1), (1, 0), (0, 0)]))
        result = gate.compare(before, after)
        self.assertEqual(result['status'], 'blocked-invalid-or-unsupported-geometry')
        self.assertEqual(result['geometry_errors'][0]['location_id'], 'land')
        self.assertIsNone(result['regressions'])

    def test_malformed_candidate_retains_actionable_raw_geometry(self):
        before = features(land=box(0, 0, 1, 1))
        after = features(land=box(0, 0, 1, 1))
        del after['land']['geometry']['coordinates']
        result = gate.compare(before, after)
        self.assertEqual(result['status'], 'blocked-invalid-or-unsupported-geometry')
        error = result['geometry_errors'][0]
        self.assertEqual(error['location_id'], 'land')
        self.assertEqual(error['vintage'], 'candidate')
        self.assertEqual(error['original_geometry'], {'type': 'Polygon'})

    def test_unchanged_invalid_geometry_is_not_a_successful_fast_path(self):
        invalid = features(land=Polygon([(0, 0), (1, 1), (0, 1), (1, 0), (0, 0)]))
        result = gate.compare(invalid, invalid)
        self.assertEqual(result['changed_location_ids'], [])
        self.assertEqual(result['status'], 'blocked-invalid-or-unsupported-geometry')
        self.assertIsNone(result['regressions'])
        self.assertEqual({error['vintage'] for error in result['geometry_errors']}, {'baseline', 'candidate'})

    def test_same_invalid_commit_cli_fails_and_reports_original_location(self):
        with tempfile.TemporaryDirectory(prefix='geography-gate-control-') as directory:
            root = pathlib.Path(directory).resolve()
            invalid = features(land=Polygon([(0, 0), (1, 1), (0, 1), (1, 0), (0, 0)]))
            commit = self.fixture(root, invalid)
            out = root / 'result.json'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/check-geographic-regression.py'),
                '--repo', str(root), '--baseline', commit, '--candidate', commit, '--out', str(out)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(out.read_bytes())
            self.assertEqual(report['status'], 'blocked-invalid-or-unsupported-geometry')
            for vintage in ['baseline', 'candidate']:
                self.assertEqual(report[vintage]['locations'][0]['location_id'], 'land')
                self.assertEqual(gate.canonical_json(report[vintage]['locations'][0]['original_geometry']),
                                 gate.canonical_json(invalid['land']['geometry']))

    def test_unpinned_commit_is_rejected_before_git_read(self):
        for commit in ['HEAD', '--output=bad', '0' * 39]:
            with self.assertRaisesRegex(ValueError, 'immutable 40-character'):
                gate.snapshot(ROOT, commit)

    def test_deletion_and_replacement_preserve_union(self):
        before = features(old=box(0, 0, 1, 1), other=box(1, 0, 2, 1))
        after = features(new=box(0, 0, 1, 1), other=box(1, 0, 2, 1))
        self.assertEqual(gate.compare(before, after)['regressions'], 0)
        deleted = features(other=box(1, 0, 2, 1))
        self.assertEqual(gate.compare(before, deleted)['regressions'], 1)

    def test_no_threshold_filters_thin_positive_area_gap(self):
        before = features(land=box(0, 0, 1, 1))
        after = features(land=box(0, 0, 1 - 1e-12, 1))
        self.assertEqual(gate.compare(before, after)['regressions'], 1)

    def test_output_is_independent_of_location_input_order(self):
        before = features(left=box(0, 0, 1, 1), right=box(1, 0, 2, 1))
        after = features(left=box(0, 0, .9, 1), right=box(1.1, 0, 2, 1))
        first = gate.canonical_json(gate.compare(before, after))
        second = gate.canonical_json(gate.compare(dict(reversed(list(before.items()))), dict(reversed(list(after.items())))))
        self.assertEqual(first, second)

    def test_snapshot_rejects_duplicate_id_and_release_pointer_mismatch(self):
        with tempfile.TemporaryDirectory(prefix='geography-gate-control-') as directory:
            root = pathlib.Path(directory).resolve()
            original = self.fixture(root, features(land=box(0, 0, 1, 1)))
            part = root / 'data/geography/control.json'
            collection = json.loads(part.read_text())
            collection['features'].append(collection['features'][0])
            part.write_text(json.dumps(collection))
            duplicate = self.commit(root)
            with self.assertRaisesRegex(ValueError, 'duplicate stable'):
                gate.snapshot(root, duplicate)
            part.write_text(json.dumps({'type': 'FeatureCollection', 'features': list(features(land=box(0, 0, 1, 1)).values())}))
            (root / 'data/geographic-releases/current-manifest.json').write_text(json.dumps({'path': 'release.json', 'sha256': '0' * 64}))
            stale = self.commit(root)
            with self.assertRaisesRegex(ValueError, 'pointer hash'):
                gate.snapshot(root, stale)
            self.assertEqual(gate.snapshot(root, original)['features']['land']['id'], 'land')

    @staticmethod
    def commit(root):
        subprocess.run(['git', '-C', str(root), 'add', 'data'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(root), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                        'commit', '-m', 'Immutable test fixture'], check=True, capture_output=True)
        return subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD']).decode().strip()

    def fixture(self, root, locations):
        subprocess.run(['git', '-C', str(root), 'init'], check=True, capture_output=True)
        (root / 'data/geography').mkdir(parents=True)
        (root / 'data/geographic-releases').mkdir()
        (root / 'data/canonical-grid').mkdir()
        files = {'world-index.json': {'parts': ['geography/control.json']}, 'hierarchy.json': [],
                 'canonical-grid/manifest.json': {'version': 1}, 'geographic-releases/index.json': {},
                 'geographic-releases/release.json': {'id': 'control-release'},
                 'geography/control.json': {'type': 'FeatureCollection', 'features': list(locations.values())}}
        for name, value in files.items():
            (root / 'data' / name).write_bytes(gate.canonical_json(value))
        release = root / 'data/geographic-releases/release.json'
        (root / 'data/geographic-releases/current-manifest.json').write_bytes(gate.canonical_json(
            {'path': 'release.json', 'sha256': hashlib.sha256(release.read_bytes()).hexdigest()}))
        return self.commit(root)

    def test_immutable_commits_ignore_mutable_checkout_and_preserve_full_source_pins(self):
        with tempfile.TemporaryDirectory(prefix='geography-gate-control-') as directory:
            root = pathlib.Path(directory).resolve()
            base = self.fixture(root, features(left=box(0, 0, 1, 1), right=box(1, 0, 2, 1)))
            part = root / 'data/geography/control.json'
            part.write_bytes(gate.canonical_json({'type': 'FeatureCollection', 'features': list(
                features(left=box(0, 0, .9, 1), right=box(1, 0, 2, 1)).values())}))
            candidate = self.commit(root)
            part.write_text('This mutable checkout is deliberately corrupt.')
            report = gate.inspect(root, base, candidate)
            self.assertEqual(report['regressions'], 1)
            self.assertEqual(report['baseline']['commit'], base)
            self.assertEqual(report['candidate']['commit'], candidate)
            self.assertEqual(len(report['baseline']['files']), 7)
            self.assertEqual(report['candidate']['locations'][0]['containing_file'], 'data/geography/control.json')
            repeated = gate.inspect(root, base, candidate)
            self.assertEqual(gate.canonical_json(report), gate.canonical_json(repeated))

    def test_cli_nonzero_for_regression_and_exclusive_output(self):
        with tempfile.TemporaryDirectory(prefix='geography-gate-control-') as directory:
            root = pathlib.Path(directory).resolve()
            base = self.fixture(root, features(land=box(0, 0, 1, 1)))
            part = root / 'data/geography/control.json'
            part.write_bytes(gate.canonical_json({'type': 'FeatureCollection', 'features': list(features(land=box(0, 0, .9, 1)).values())}))
            candidate = self.commit(root)
            out = root / 'result.json'
            command = [sys.executable, str(ROOT / 'scripts/check-geographic-regression.py'), '--repo', str(root),
                       '--baseline', base, '--candidate', candidate, '--out', str(out)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(out.read_bytes())['regressions'], 1)
            original = out.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(out.read_bytes(), original)


def receipt_run(directory, code_commit=None):
    """Run real controls and retain deterministic results in a new directory."""
    files = ['scripts/check-geographic-regression.py', 'scripts/run-geographic-check.py',
             'scripts/evidence/geometry.py', 'scripts/evidence/immutable.py',
             'scripts/ellipsoidal_area.py', 'test/geographic-regression.py',
             'test/trusted-geography-check.py', 'src/regional-import-gate.js',
             'requirements.txt', 'package.json', '.github/evidence-policy.json']
    if code_commit is not None:
        import re
        if not re.fullmatch('[a-f0-9]{40}', code_commit):
            raise ValueError('Require exact immutable executed control commit')
        for name in files:
            tree = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', code_commit, '--', name])
            if not tree.startswith((b'100644 ', b'100755 ')):
                raise ValueError('Executed control input must be ordinary Git bytes: ' + name)
            if subprocess.check_output(['git', '-C', str(ROOT), 'show', code_commit + ':' + name]) != (ROOT / name).read_bytes():
                raise ValueError('Executed control input differs from frozen commit: ' + name)
    class Result(unittest.TextTestResult):
        def addSuccess(self, test):
            super().addSuccess(test)
            self.successes = getattr(self, 'successes', []) + [test._testMethodName]

    result = unittest.TextTestRunner(resultclass=Result).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(RegressionControls))
    if not result.wasSuccessful() or result.skipped:
        return 1
    directory = pathlib.Path(directory)
    if any(p.is_symlink() for p in [directory, *directory.absolute().parents]):
        raise ValueError('Symlink receipt destination')
    directory.mkdir()  # Exclusive: never refresh original control evidence.
    controls = sorted(result.successes)
    files = [gate.descriptor(name, (ROOT / name).read_bytes()) for name in files]
    summary = {'method_id': 'geographic-regression', 'tests': result.testsRun,
        'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
        'outcome': 'passed', 'controls': controls, 'executed_files': files,
        'executed_commit': code_commit,
        'software': {'shapely': gate.shapely.__version__, 'geos': gate.shapely.geos_version_string}}
    (directory / 'results.json').write_bytes(gate.canonical_json(summary))
    negative = {'test_valid_joint_boundary_move', 'test_existing_gap_and_overlap_are_not_new_regressions',
        'test_output_is_independent_of_location_input_order', 'test_deletion_and_replacement_preserve_union',
        'test_islands_holes_and_intentional_water_change_still_require_review',
        'test_valid_disjoint_and_point_touching_multipart_preserved',
        'test_shortest_edge_domain_positive_is_not_naive_raw_validity',
        'test_island_inside_hole_is_valid_multipart',
        'test_trusted_source_only_research_remains_not_applicable'}
    for kind in ['positive-control', 'negative-control']:
        selected = [name for name in controls if (name in negative) == (kind == 'negative-control')]
        value = {**summary, 'kind': kind, 'controls': selected,
            'limits': ['Synthetic diagnostic controls only; mixed lake/deletion cases also exercise positive failures. No geography approval.']}
        (directory / (kind + '.json')).write_bytes(gate.canonical_json(value))
    return 0


if __name__ == '__main__':
    if '--receipts' in sys.argv:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--receipts', required=True)
        parser.add_argument('--code-commit')
        args = parser.parse_args()
        sys.exit(receipt_run(args.receipts, args.code_commit))
    unittest.main()
