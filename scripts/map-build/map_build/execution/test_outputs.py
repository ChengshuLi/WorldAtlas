import tempfile
import unittest
from pathlib import Path

from map_build.execution.outputs import create_binary_exclusive, create_directory_exclusive


class OutputSafety(unittest.TestCase):
    def test_directory_collision_keeps_existing_contents(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'output'
            create_directory_exclusive(target)
            (target / 'existing').write_text('original')
            with self.assertRaises(FileExistsError):
                create_directory_exclusive(target)
            self.assertEqual((target / 'existing').read_text(), 'original')

    def test_file_collision_keeps_existing_contents(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'output'
            with create_binary_exclusive(target) as stream:
                stream.write(b'original')
            with self.assertRaises(FileExistsError):
                with create_binary_exclusive(target):
                    pass
            self.assertEqual(target.read_bytes(), b'original')

    def test_file_writer_refuses_existing_and_dangling_symlinks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            source.write_text('original')
            for name, destination in [('link', source), ('dangling', root / 'missing')]:
                link = root / name
                link.symlink_to(destination)
                with self.assertRaises(FileExistsError):
                    with create_binary_exclusive(link):
                        pass
                self.assertTrue(link.is_symlink())
            self.assertEqual(source.read_text(), 'original')
            self.assertFalse((root / 'missing').exists())


if __name__ == '__main__':
    unittest.main()
