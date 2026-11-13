import tempfile, unittest
from pathlib import Path
from map_build.execution.outputs import (
    validate_fresh_output,
    create_directory_exclusive,
    create_binary_exclusive,
)


class OutputSafety(unittest.TestCase):
    def test_fresh_sibling_inside_root_and_exclusive_collision(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            source = root / 'input'
            source.write_text('original')
            target = validate_fresh_output(root, root / 'new', (source,))
            create_directory_exclusive(target)
            with self.assertRaisesRegex(FileExistsError, 'must be new'):
                validate_fresh_output(root, target, (source,))
            with self.assertRaises(FileExistsError):
                create_directory_exclusive(target)
            self.assertEqual(source.read_text(), 'original')

    def test_existing_root_ancestor_or_input_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve() / 'root'
            root.mkdir()
            source = root / 'input'
            source.write_text('original')
            for out in (root, root.parent, source):
                with self.subTest(out=out), self.assertRaises((ValueError, FileExistsError)):
                    validate_fresh_output(root, out, (source,))
            self.assertEqual(source.read_text(), 'original')

    def test_symlink_parent_and_dangling_target_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve() / 'root'
            root.mkdir()
            outside = Path(t).resolve() / 'outside'
            outside.mkdir()
            (root / 'link').symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                validate_fresh_output(root, root / 'link' / 'output')
            (root / 'dangling').symlink_to(root / 'missing')
            with self.assertRaises(ValueError):
                validate_fresh_output(root, root / 'dangling')

    def test_exclusive_file_refuses_symlink_or_race(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            target = validate_fresh_output(root, root / 'newfile')
            target.write_text('other')
            with self.assertRaises(FileExistsError):
                with create_binary_exclusive(target):
                    pass
            self.assertEqual(target.read_text(), 'other')

    def test_missing_parent_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError, 'parent'):
                validate_fresh_output(Path(t).resolve(), Path(t).resolve() / 'missing' / 'output')


if __name__ == '__main__':
    unittest.main()
