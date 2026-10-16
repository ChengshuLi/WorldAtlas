"""Admission-only controls: no constructor, science, or external reads."""
import importlib.util
import os
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('bounded_native348', ROOT / 'run-bounded-native348.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vietnam348-admission-')
        self.old = pathlib.Path.cwd()
        os.chdir(self.temp.name)
        pathlib.Path('.cache/delivery-handoff').mkdir(parents=True)
        pathlib.Path('sentinel').write_text('unchanged\n')

    def tearDown(self):
        self.assertEqual(pathlib.Path('sentinel').read_text(), 'unchanged\n')
        os.chdir(self.old)
        self.temp.cleanup()

    def refuse(self, destination):
        before = sorted(str(p) for p in pathlib.Path('.').rglob('*'))
        with self.assertRaises(AssertionError):
            launcher.admit_destination(destination)
        self.assertEqual(sorted(str(p) for p in pathlib.Path('.').rglob('*')), before)

    def test_fresh_namespace_is_read_only(self):
        dest = launcher.admit_destination('.cache/delivery-handoff/new')
        self.assertFalse(os.path.lexists(dest))

    def test_existing_file(self):
        pathlib.Path('.cache/delivery-handoff/existing').write_text('retained')
        self.refuse('.cache/delivery-handoff/existing')
        self.assertEqual(pathlib.Path('.cache/delivery-handoff/existing').read_text(), 'retained')

    def test_dangling_destination(self):
        p = pathlib.Path('.cache/delivery-handoff/link')
        p.symlink_to('missing')
        self.refuse(str(p))
        self.assertTrue(p.is_symlink())

    def test_live_directory_ancestor(self):
        pathlib.Path('ordinary').mkdir()
        p = pathlib.Path('.cache/delivery-handoff/link')
        p.symlink_to(pathlib.Path('ordinary').absolute(), target_is_directory=True)
        self.refuse(str(p / 'new'))
        self.assertFalse((pathlib.Path('ordinary') / 'new').exists())

    def test_dangling_ancestor(self):
        p = pathlib.Path('.cache/delivery-handoff/link')
        p.symlink_to('missing', target_is_directory=True)
        self.refuse(str(p / 'new'))
        self.assertTrue(p.is_symlink())

    def test_namespace_and_traversal(self):
        self.refuse('.cache/unapproved/new')
        self.refuse('.cache/delivery-handoff/../new')

    def test_changed_post_run_head_is_non_success_before_receipt(self):
        self.assertIsNone(launcher.completion_reason(None, 'a' * 40, 'a' * 40))
        self.assertEqual(launcher.completion_reason(None, 'a' * 40, 'b' * 40), 'executing_tree_head_changed')
        self.assertEqual(launcher.completion_reason('wall_deadline', 'a' * 40, 'b' * 40), 'wall_deadline')

    def test_current_adoption_tree_must_match_captured_code(self):
        calls = []
        def git(*args):
            calls.append(args)
            return (('a' * 40) + '\n').encode()
        launcher.require_current_head(git, 'a' * 40)
        with self.assertRaisesRegex(AssertionError, 'Executing adoption tree'):
            launcher.require_current_head(git, 'b' * 40)
        self.assertEqual(calls, [('rev-parse', 'HEAD')] * 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
