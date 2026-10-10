"""Real Git/CLI controls: proposed scripts cannot waive trusted geometry checks."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / 'scripts/run-geographic-check.py'
PYTHON = os.environ.get('PYTHON', sys.executable)


def polygon(left, right):
    return {'type': 'Polygon', 'coordinates': [[[left, 0], [right, 0], [right, 1], [left, 1], [left, 0]]]}


def collection(left=1, right=1):
    return {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'id': 'left', 'properties': {'id': 'left'}, 'geometry': polygon(0, left)},
        {'type': 'Feature', 'id': 'right', 'properties': {'id': 'right'}, 'geometry': polygon(right, 2)}]}


class Fixture:
    def __init__(self):
        scratch = ROOT / '.cache/trusted-geography-fixtures'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.repo = Path(self.temporary.name).resolve()
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'synthetic-control')
        for name in ['scripts/check-geographic-regression.py', 'scripts/evidence/immutable.py',
                     'scripts/evidence/geometry.py', 'scripts/ellipsoidal_area.py', 'requirements.txt',
                     'package.json', '.github/evidence-policy.json', 'src/regional-import-gate.js',
                     'coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs',
                     'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs']:
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        shutil.copyfile(DRAFT, self.repo / 'scripts/run-geographic-check.py')
        self.write('data/world-index.json', {'parts': ['geography/part.json']})
        self.write('data/geography/part.json', collection())
        for name in ['data/hierarchy.json', 'data/canonical-grid/manifest.json', 'data/geographic-releases/index.json']:
            self.write(name, {})
        self.write('data/geographic-releases/release.json', {})
        raw = (self.repo / 'data/geographic-releases/release.json').read_bytes()
        self.write('data/geographic-releases/current-manifest.json', {'path': 'data/geographic-releases/release.json', 'sha256': hashlib.sha256(raw).hexdigest()})
        self.baseline = self.commit('trusted-baseline')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.PIPE).decode().strip()

    def write(self, name, value):
        target = self.repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, sort_keys=True) + '\n')

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-qm', message)
        return self.git('rev-parse', 'HEAD')

    def run(self, candidate, rewind=True):
        if rewind:
            self.git('checkout', '-q', '--detach', self.baseline)
        output = self.repo / 'geography-check.json'
        result = subprocess.run([PYTHON, '-I', '-B', str(self.repo / 'scripts/run-geographic-check.py'),
                                 '--repo', str(self.repo), '--baseline', self.baseline,
                                 '--candidate', candidate, '--out', str(output)],
                                capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != 'GH_TOKEN'})
        return result, json.loads(output.read_bytes()) if output.exists() else None

    def close(self):
        self.temporary.cleanup()


class TrustedCheckControls(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()

    def tearDown(self):
        self.f.close()

    def test_external_src_code_tampering_is_rejected(self):
        (self.f.repo / 'src/regional-import-gate.js').write_text("throw Error('tampered trusted dependency')\n")
        result, report = self.f.run(self.f.baseline, rewind=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(report)
        self.assertIn('differs from immutable trusted baseline', result.stderr)

    def test_external_package_and_policy_tampering_is_rejected(self):
        for name in ['package.json', '.github/evidence-policy.json']:
            target = self.f.repo / name
            raw = target.read_bytes()
            target.write_bytes(b'{}\n')
            result, report = self.f.run(self.f.baseline, rewind=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIsNone(report)
            self.assertIn('metadata or evidence policy differs', result.stderr)
            target.write_bytes(raw)

    def test_missing_or_symlinked_external_input_is_rejected(self):
        target = self.f.repo / '.github/evidence-policy.json'
        raw = target.read_bytes()
        target.unlink()
        result, report = self.f.run(self.f.baseline, rewind=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(report)
        replacement = self.f.repo / 'policy-copy.json'
        replacement.write_bytes(raw)
        target.symlink_to(replacement)
        result, report = self.f.run(self.f.baseline, rewind=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(report)

    def test_untracked_src_import_shadow_is_rejected(self):
        (self.f.repo / 'src/regional-import-gate').mkdir()
        (self.f.repo / 'src/regional-import-gate/index.js').write_text("throw Error('shadow')\n")
        result, report = self.f.run(self.f.baseline, rewind=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(report)
        self.assertIn('Untracked or missing file', result.stderr)

    def test_shallow_partial_fetch_reads_lazy_blobs_without_candidate_code(self):
        self.f.write('data/geography/part.json', collection(left=.9))
        (self.f.repo / 'scripts/check-geographic-regression.py').write_text("raise RuntimeError('candidate code executed')\n")
        candidate = self.f.commit('remote-gap-plus-disabled-checker')
        self.f.git('branch', 'trusted', self.f.baseline)
        self.f.git('config', 'uploadpack.allowFilter', 'true')
        checkout = self.f.repo / 'isolated-fetch-control'
        subprocess.run(['git', 'clone', '--quiet', '--depth=1', '--filter=blob:none', '--no-checkout',
                        '--branch', 'trusted', self.f.repo.as_uri(), str(checkout)], check=True, capture_output=True)
        def git(*args, env=None):
            return subprocess.run(['git', '-C', str(checkout), *args], capture_output=True, text=True, env=env)
        self.assertEqual(git('sparse-checkout', 'init', '--cone').returncode, 0)
        self.assertEqual(git('sparse-checkout', 'set', 'scripts', 'src', '.github',
                             'coordination/engineering/selected-geography-effective-prevention-20261009').returncode, 0)
        self.assertEqual(git('checkout', '--quiet', 'trusted').returncode, 0)
        self.assertEqual(git('rev-parse', '--is-shallow-repository').stdout.strip(), 'true')
        self.assertFalse((checkout / 'data').exists())
        blob = self.f.git('rev-parse', candidate + ':data/geography/part.json')
        # Prove the candidate part starts absent, rather than accidentally testing
        # an already materialized clone. Batch lookup disables lazy fetching.
        lookup = subprocess.run(['git', '-C', str(checkout), 'cat-file', '--batch-check'],
                                input=blob + '\n', capture_output=True, text=True,
                                env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'})
        self.assertIn('missing', lookup.stdout)
        token = 'synthetic-read-only-secret'
        output = checkout / 'fetch-report.json'
        result = subprocess.run([PYTHON, '-I', '-B', str(checkout / 'scripts/run-geographic-check.py'),
                                 '--repo', str(checkout), '--baseline', self.f.baseline,
                                 '--candidate', candidate, '--fetch', '--out', str(output)],
                                capture_output=True, text=True, env={**os.environ, 'GH_TOKEN': token})
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(output.is_file(), result.stderr)
        report = json.loads(output.read_bytes())
        self.assertEqual(report['status'], 'regressions-found')
        self.assertEqual(report['regressions'], 1)
        self.assertFalse(report['candidate_code_executed'])
        self.assertEqual(git('rev-parse', 'HEAD').stdout.strip(), self.f.baseline)
        self.assertFalse((checkout / 'data').exists())
        self.assertNotIn(token, result.stdout + result.stderr)
        self.assertNotIn(token, (checkout / '.git/config').read_text())
        self.assertNotIn('extraheader', (checkout / '.git/config').read_text())
        self.assertNotIn('missing', subprocess.run(['git', '-C', str(checkout), 'cat-file', '--batch-check'],
                         input=blob+'\n', capture_output=True, text=True,
                         env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'}).stdout)

    def test_unfixed_commit_and_existing_report_fail_closed(self):
        result, report = self.f.run('main')
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(report)
        self.assertIn('exact immutable', result.stderr)
        result, report = self.f.run(self.f.baseline)
        self.assertEqual(result.returncode, 0, result.stderr)
        raw = (self.f.repo / 'geography-check.json').read_bytes()
        result, report = self.f.run(self.f.baseline)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.f.repo / 'geography-check.json').read_bytes(), raw)

    def test_source_only_candidate_cannot_execute_its_script(self):
        self.f.write('research/geography/example/proposal.json', {'source_only': True})
        (self.f.repo / 'scripts/check-geographic-regression.py').write_text("raise RuntimeError('candidate code executed')\n")
        candidate = self.f.commit('source-only-and-disabled-checker')
        result, report = self.f.run(candidate)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report['status'], 'not-applicable')
        self.assertIsNone(report['regressions'])
        self.assertFalse(report['candidate_code_executed'])
        self.assertIn('not fresh polygon validation', report['limits'][0])

    def test_candidate_cannot_disable_gap_detection(self):
        self.f.write('data/geography/part.json', collection(left=.9))
        (self.f.repo / 'scripts/check-geographic-regression.py').write_text("raise RuntimeError('candidate code executed')\n")
        candidate = self.f.commit('gap-plus-disabled-checker')
        result, report = self.f.run(candidate)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(report['status'], 'regressions-found')
        self.assertEqual(report['regressions'], 1)
        self.assertEqual(report['trusted_code_commit'], self.f.baseline)
        self.assertEqual(report['candidate_commit'], candidate)
        finding = report['differential_report']['findings']['features'][0]
        self.assertEqual(finding['properties']['kind'], 'lost-previous-coverage')
        self.assertTrue(.9 < finding['properties']['coordinate'][0] < 1)

    def test_valid_joint_move_is_allowed(self):
        self.f.write('data/geography/part.json', collection(left=.9, right=.9))
        result, report = self.f.run(self.f.commit('joint-move'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report['status'], 'no-new-regression')
        self.assertEqual(report['regressions'], 0)

    def test_untrusted_checkout_cannot_run(self):
        self.f.write('data/geography/part.json', collection(left=.9))
        result, report = self.f.run(self.f.commit('untrusted-head'), rewind=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(report)
        self.assertIn('exact trusted baseline', result.stderr)

    def test_untracked_import_shadow_files_are_rejected(self):
        for name in ['scripts/evidence.py', 'scripts/evidence/__init__.py', 'scripts/evidence/geometry.so', 'scripts/evidence/__pycache__/geometry.pyc']:
            target = self.f.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("raise RuntimeError('untrusted shadow executed')\n")
            result, report = self.f.run(self.f.baseline, rewind=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIsNone(report)
            self.assertIn('Untracked or missing file', result.stderr)
            self.assertNotIn('untrusted shadow executed', result.stderr)
            target.unlink()

    def test_working_tree_checker_change_cannot_run(self):
        (self.f.repo / 'scripts/check-geographic-regression.py').write_text('pass\n')
        result, report = self.f.run(self.f.baseline, rewind=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(report)
        self.assertIn('differs from immutable trusted baseline', result.stderr)

    def test_candidate_part_symlink_is_rejected(self):
        p = self.f.repo / 'data/geography/part.json'
        p.unlink()
        p.symlink_to('../../scripts/check-geographic-regression.py')
        result, report = self.f.run(self.f.commit('symlinked-input'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(report)
        self.assertIn('ordinary Git file', result.stderr)

    def test_metadata_only_part_change_still_validates(self):
        value = collection()
        value['features'][0]['properties']['name'] = 'renamed'
        self.f.write('data/geography/part.json', value)
        result, report = self.f.run(self.f.commit('name-only'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report['status'], 'no-footprint-change')
        self.assertIn('differential_report', report)

    def test_two_individually_valid_proposals_fail_when_combined(self):
        # Old overlap covers both independent proposals; together they expose land.
        self.f.write('data/geography/part.json', collection(left=1.1, right=.9))
        self.f.baseline = self.f.commit('overlapping-baseline')
        self.f.write('data/geography/part.json', collection(left=.95, right=.9))
        left = self.f.commit('left-proposal')
        result, report = self.f.run(left)
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.f.repo / 'geography-check.json').unlink()
        self.f.write('data/geography/part.json', collection(left=1.1, right=1.05))
        right = self.f.commit('right-proposal')
        result, report = self.f.run(right)
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.f.repo / 'geography-check.json').unlink()
        self.f.write('data/geography/part.json', collection(left=.95, right=1.05))
        combined = self.f.commit('combined-proposals')
        result, report = self.f.run(combined)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(report['regressions'], 1)

    def test_existing_invalid_geometry_is_checked_on_metadata_part_change(self):
        value = collection()
        value['features'][0]['geometry'] = {'type': 'Polygon', 'coordinates': [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]}
        self.f.write('data/geography/part.json', value)
        self.f.baseline = self.f.commit('invalid-baseline')
        value['features'][0]['properties']['name'] = 'metadata-edit'
        self.f.write('data/geography/part.json', value)
        result, report = self.f.run(self.f.commit('invalid-metadata'))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(report['status'], 'blocked-invalid-or-unsupported-geometry')
        self.assertEqual(len(report['differential_report']['geometry_errors']), 2)

    def test_release_pointer_mismatch_is_not_inapplicable(self):
        self.f.write('data/geographic-releases/current-manifest.json', {'path': 'data/geographic-releases/release.json', 'sha256': '0' * 64})
        result, report = self.f.run(self.f.commit('bad-pointer'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(report)
        self.assertIn('pointer hash mismatch', result.stderr)


def receipt_run(directory):
    class Result(unittest.TextTestResult):
        def addSuccess(self, test):
            super().addSuccess(test)
            self.successes = getattr(self, 'successes', []) + [test._testMethodName]
    result = unittest.TextTestRunner(resultclass=Result, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(TrustedCheckControls))
    if not result.wasSuccessful() or result.skipped:
        return 1
    directory = Path(directory)
    if any(p.is_symlink() for p in [directory, *directory.absolute().parents]):
        raise ValueError('Symlink receipt destination')
    directory.mkdir()
    files = []
    for name in ['scripts/run-geographic-check.py', 'scripts/check-geographic-regression.py',
                 'scripts/evidence/immutable.py', 'scripts/evidence/geometry.py',
                 'scripts/ellipsoidal_area.py', 'test/trusted-geography-check.py']:
        raw = (ROOT / name).read_bytes()
        files.append({'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'hash_kind': 'file-bytes'})
    summary = {'method_id': 'trusted-geography-check', 'outcome': 'passed', 'tests': result.testsRun,
               'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
               'controls': sorted(result.successes), 'executed_files': files,
               'limits': ['Synthetic Git repositories only. File-protocol partial fetch exercises lazy blobs and environment-only credentials; actual GitHub authentication requires hosted readback.',
                          'No deployment, factual source approval, administrative repair or real-water exception.']}
    encode = lambda value: (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()
    (directory / 'results.json').write_bytes(encode(summary))
    positive = {'test_valid_joint_move_is_allowed', 'test_source_only_candidate_cannot_execute_its_script', 'test_metadata_only_part_change_still_validates'}
    for kind in ['positive-control', 'negative-control']:
        selected = [name for name in summary['controls'] if (name in positive) == (kind == 'positive-control')]
        (directory / (kind + '.json')).write_bytes(encode({**summary, 'kind': kind, 'controls': selected}))
    return 0



class LinuxTransitionControls(unittest.TestCase):
    """Real Git/tree/body controls; mocked baseline proof is labelled orchestration-only."""
    def setUp(self):
        import importlib.util
        from unittest import mock
        self.mock = mock
        spec = importlib.util.spec_from_file_location('trusted_linux_transition_control', DRAFT)
        self.gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.gate)
        scratch = ROOT / '.cache/trusted-linux-transition-fixtures'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'synthetic-control')
        self.git('config', 'user.email', 'control@example.invalid')
        self.paths = [f'support/boundary-{i:02}.py' for i in range(30)]
        self.vector_paths = self.paths[:3] + [f'methods/method-{i:02}.js' for i in range(25)]
        for i, name in enumerate(self.vector_paths):
            self.write(name, f'original-method-{i}\n'.encode())
        for i, name in enumerate(self.paths[3:7]):
            self.write(name, f'original-support-{i}\n'.encode())
        self.write(self.gate.LINUX_SUPPORT_MANIFEST, b'current author identity\n')
        self.write('data/ownership-selection.json', b'{}\n')
        self.write('data/scientific-input.json', b'unchanged scientific bytes\n')
        self.baseline = self.commit('synthetic trusted baseline')
        vector = [{'path': name, 'bytes': (self.repo/name).stat().st_size,
                   'sha256': hashlib.sha256((self.repo/name).read_bytes()).hexdigest()} for name in self.vector_paths]
        before = {name: self.pin(self.baseline, name) for name in self.paths}
        for i, name in enumerate(self.paths):
            self.write(name, f"raise RuntimeError('candidate must never execute {i}')\n".encode())
        self.candidate = self.commit('synthetic exact support transition')
        reference = [{'path': name, 'before': before[name], 'after': self.pin(self.candidate, name)} for name in self.paths]
        current = self.pin(self.baseline, self.gate.LINUX_SUPPORT_MANIFEST)
        reference.append({'path': self.gate.LINUX_SUPPORT_MANIFEST, 'before': {**current, 'sha256': '0'*64}, 'after': current})
        reference.sort(key=lambda row: row['path'])
        # Explicit synthetic contract; separately test the production literal map.
        self.gate.LINUX_SUPPORT_REFERENCE = reference
        self.gate.LINUX_SUPPORT_OLD_VECTOR = vector
        self.rehash()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.PIPE)

    def write(self, name, body):
        p = self.repo/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)

    def commit(self, message):
        self.git('add', '--all')
        self.git('commit', '-qm', message)
        return self.git('rev-parse', 'HEAD').decode().strip()

    def pin(self, version, name):
        row = self.git('ls-tree', '-z', version, '--', name)
        if not row:
            return None
        mode, kind, oid = row.split(b'\t')[0].decode().split()
        self.assertEqual(kind, 'blob')
        body = self.git('cat-file', 'blob', oid)
        return {'mode': mode, 'git_blob_oid': oid, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}

    def rehash(self):
        g = self.gate
        g.LINUX_SUPPORT_REFERENCE_SHA256 = g.transition_digest(g.LINUX_SUPPORT_REFERENCE)
        g.LINUX_SUPPORT_DELTA_SHA256 = g.transition_digest([r for r in g.LINUX_SUPPORT_REFERENCE if r['path'] != g.LINUX_SUPPORT_MANIFEST])
        g.LINUX_SUPPORT_VECTOR_SHA256 = g.transition_digest(g.LINUX_SUPPORT_OLD_VECTOR, newline=True)

    def check(self, candidate=None):
        return self.gate.linux_support_transition(self.repo, self.baseline, candidate or self.candidate)

    def test_exact_real_git_transition_and_no_candidate_execution(self):
        proof = self.check()
        self.assertEqual(proof['changed_paths'], 30)
        self.assertEqual(proof['baseline_commit'], self.baseline)
        self.assertEqual(proof['candidate_commit'], self.candidate)
        self.assertFalse(proof['candidate_code_executed'])
        self.assertFalse(proof['candidate_scientific_qualification'])
        self.assertIsNone(self.gate.linux_support_transition(self.repo, self.baseline, self.baseline))

    def test_production_literal_contract_is_complete_and_authentic(self):
        namespace = {'__name__': 'non_cli_control'}
        exec(compile(DRAFT.read_bytes(), str(DRAFT), 'exec'), namespace)
        self.assertEqual(namespace['transition_digest'](namespace['LINUX_SUPPORT_OLD_VECTOR'], newline=True),
                         '4ba0e3b564611248d428613c33bd60cf68a99233f2db572f3893a7d46dda429a')
        self.assertEqual(namespace['transition_digest'](namespace['LINUX_SUPPORT_REFERENCE']),
                         'ae94c33f7923a04648bb7da080c61fffef67cbe7f966127fc9869e3863d468ca')
        self.assertEqual(len(namespace['LINUX_SUPPORT_REFERENCE']), 31)

    def test_changed_body_missing_addition_and_wrong_mode_refuse(self):
        for alteration in ['body', 'missing', 'mode']:
            with self.subTest(alteration=alteration):
                self.git('checkout', '-q', '--detach', self.candidate)
                p = self.repo/self.paths[-1]
                if alteration == 'body': p.write_bytes(b'changed same audience\n')
                elif alteration == 'missing': p.unlink()
                else: p.chmod(0o755)
                self.assertIsNone(self.check(self.commit(alteration)))

    def test_excluded_path_directory_and_symlink_cannot_hide_descendants(self):
        for alteration in ['directory', 'symlink']:
            with self.subTest(alteration=alteration):
                self.git('checkout', '-q', '--detach', self.candidate)
                p = self.repo/self.paths[-1]
                p.unlink()
                if alteration == 'directory':
                    p.mkdir();(p/'hidden-child.py').write_bytes(b'not admitted\n')
                else: p.symlink_to('../data/scientific-input.json')
                self.assertIsNone(self.check(self.commit(alteration)))

    def test_extra_data_method_rename_and_file_refuse(self):
        for alteration in ['data', 'method', 'rename', 'extra']:
            with self.subTest(alteration=alteration):
                self.git('checkout', '-q', '--detach', self.candidate)
                if alteration == 'data': self.write('data/scientific-input.json', b'changed\n')
                elif alteration == 'method': self.write(self.vector_paths[-1], b'changed method\n')
                elif alteration == 'rename': (self.repo/self.paths[-1]).rename(self.repo/'renamed.py')
                else: self.write('outside.py', b'not admitted\n')
                self.assertIsNone(self.check(self.commit(alteration)))

    def test_preinstalled_manifest_identity_cannot_change(self):
        self.write(self.gate.LINUX_SUPPORT_MANIFEST, b'wrong worker\n')
        self.assertIsNone(self.check(self.commit('manifest drift')))

    def test_literal_vector_reordering_truncation_and_descriptor_bounds_refuse(self):
        g = self.gate
        original = list(g.LINUX_SUPPORT_OLD_VECTOR)
        for malformed in [original[::-1], original[:-1]]:
            g.LINUX_SUPPORT_OLD_VECTOR = malformed
            with self.assertRaisesRegex(ValueError, 'Incomplete or reordered'):
                self.check()
        g.LINUX_SUPPORT_OLD_VECTOR = original
        g.LINUX_SUPPORT_REFERENCE[-1]['after']['bytes'] = g.MAX_BYTES + 1
        self.rehash()
        with self.mock.patch.object(g, 'git', side_effect=AssertionError('body opened before admission')):
            with self.assertRaisesRegex(ValueError, 'bounds'):
                self.check()

    def test_whole_tree_git_failure_and_timeout_do_not_pass(self):
        from types import SimpleNamespace
        original = self.gate.subprocess.run
        def refusal(command, **kwargs):
            return SimpleNamespace(returncode=128) if 'diff-tree' in command else original(command, **kwargs)
        with self.mock.patch.object(self.gate.subprocess, 'run', side_effect=refusal):
            with self.assertRaisesRegex(ValueError, 'equivalence unavailable'):
                self.check()
        def timeout(command, **kwargs):
            if 'diff-tree' in command:
                raise subprocess.TimeoutExpired('git', 30)
            return original(command, **kwargs)
        with self.mock.patch.object(self.gate.subprocess, 'run', side_effect=timeout):
            with self.assertRaises(subprocess.TimeoutExpired):
                self.check()

    def orchestrate(self, proof):
        g = self.gate
        inspect = g.inspect
        with self.mock.patch.object(g, 'verify_trusted_checkout', return_value='synthetic-checkout'), \
             self.mock.patch.object(g, 'inventory', return_value=['synthetic-equal-input']), \
             self.mock.patch.object(g, 'inspect', side_effect=proof) as called:
            result = inspect(self.repo, self.baseline, self.candidate)
            called.assert_called_once_with(self.repo, self.baseline, self.baseline)
            return result

    def test_orchestration_retains_actual_baseline_proof_identities(self):
        proof = {'status': 'not-applicable', 'regressions': None,
                 'baseline_commit': self.baseline, 'candidate_commit': self.baseline,
                 'selected_native_report': {'synthetic_proof': True},
                 'selected_continuous_report': {'synthetic_proof': True}}
        result = self.orchestrate(lambda *args: proof)
        self.assertIs(result['reused_baseline_proof'], proof)
        self.assertEqual(result['candidate_commit'], self.candidate)
        self.assertEqual(result['reused_baseline_proof']['candidate_commit'], self.baseline)
        self.assertFalse(result['candidate_code_executed'])

    def test_original_baseline_failure_and_blocked_report_propagate(self):
        with self.assertRaisesRegex(RuntimeError, 'original baseline failure'):
            self.orchestrate(lambda *args: (_ for _ in ()).throw(RuntimeError('original baseline failure')))
        with self.assertRaisesRegex(ValueError, 'baseline proof did not pass'):
            self.orchestrate(lambda *args: {'status': 'native-regressions-found', 'regressions': 1})

    def test_candidate_input_inventory_mismatch_refuses_before_proof(self):
        g = self.gate
        with self.mock.patch.object(g, 'verify_trusted_checkout', return_value='synthetic-checkout'), \
             self.mock.patch.object(g, 'inventory', side_effect=[['before'], ['after']]):
            with self.assertRaisesRegex(ValueError, 'changed geographic inputs'):
                g.inspect(self.repo, self.baseline, self.candidate)


if __name__ == '__main__':
    if '--receipts' in sys.argv:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--receipts', required=True)
        raise SystemExit(receipt_run(parser.parse_args().receipts))
    unittest.main(verbosity=2)
