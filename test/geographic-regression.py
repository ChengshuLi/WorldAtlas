"""Positive/negative controls for geometry regression, not territorial approval."""
import importlib.util
import pathlib
import sys
import unittest
import json
import hashlib
import tempfile
import subprocess

from shapely.geometry import Polygon, MultiPolygon, box, mapping, shape

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('geographic_regression', ROOT / 'scripts/check-geographic-regression.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def features(**geometries):
    return {identity: {'type': 'Feature', 'id': identity,
        'properties': {'id': identity, 'name': identity}, 'geometry': mapping(geometry)}
        for identity, geometry in geometries.items()}


class RegressionControls(unittest.TestCase):
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


def receipt_run(directory):
    """Run real controls and retain deterministic results in a new directory."""
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
    files = [gate.descriptor(name, (ROOT / name).read_bytes()) for name in
             ['scripts/check-geographic-regression.py', 'test/geographic-regression.py']]
    summary = {'method_id': 'geographic-regression', 'tests': result.testsRun,
        'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
        'outcome': 'passed', 'controls': controls, 'executed_files': files,
        'software': {'shapely': gate.shapely.__version__, 'geos': gate.shapely.geos_version_string}}
    (directory / 'results.json').write_bytes(gate.canonical_json(summary))
    negative = {'test_valid_joint_boundary_move', 'test_existing_gap_and_overlap_are_not_new_regressions',
        'test_output_is_independent_of_location_input_order', 'test_deletion_and_replacement_preserve_union',
        'test_islands_holes_and_intentional_water_change_still_require_review'}
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
        sys.exit(receipt_run(parser.parse_args().receipts))
    unittest.main()
