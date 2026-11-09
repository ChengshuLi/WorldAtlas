"""Atomic publication, competing writers, crash boundaries and link rejection."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import atomic_move as publication


class Move(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'data').write_text('complete')
        (self.source / 'nested').mkdir()
        (self.source / 'nested' / 'second').write_text('also complete')
        self.destination = self.root / 'destination'

    def test_new_destination(self):
        with patch('ctypes.CDLL', side_effect=AssertionError('custom native binding')), \
                patch('subprocess.Popen', side_effect=AssertionError('process launch')):
            publication.move_noreplace(self.source, self.destination)
        self.assertEqual((self.destination / 'data').read_text(), 'complete')
        self.assertEqual((self.destination / 'nested' / 'second').read_text(), 'also complete')
        self.assertFalse(self.source.exists())
        target, receipt = publication.published_directory(self.destination)
        self.assertEqual(self.destination.resolve(), target)
        self.assertEqual(json.loads(receipt.read_bytes())['schema'], publication.SCHEMA)

    def test_parent_alias_is_canonicalized_without_following_destination_leaf(self):
        parent = self.root / 'real-parent'
        parent.mkdir()
        alias = self.root / 'parent-alias'
        alias.symlink_to(parent, target_is_directory=True)
        destination = alias / 'published'
        publication.move_noreplace(self.source, destination)
        target, receipt = publication.published_directory(destination)
        self.assertEqual(target, destination.resolve())
        self.assertEqual(json.loads(receipt.read_bytes())['destination'], str(parent / 'published'))

    def test_every_existing_destination_is_preserved(self):
        for kind in ('empty-directory', 'file', 'dangling-link'):
            destination = self.root / kind
            if kind == 'empty-directory':
                destination.mkdir()
            elif kind == 'file':
                destination.write_text('keep')
            else:
                destination.symlink_to(self.root / 'missing')
            with self.assertRaises(FileExistsError):
                publication.move_noreplace(self.source, destination)
            self.assertTrue(os.path.lexists(destination))
            self.assertTrue(self.source.is_dir())

    def test_destination_created_at_exact_publication_boundary_is_not_replaced(self):
        real_symlink = os.symlink

        def race(*args, **kwargs):
            self.destination.mkdir()
            return real_symlink(*args, **kwargs)

        with patch.object(publication.os, 'symlink', side_effect=race):
            with self.assertRaises(FileExistsError):
                publication.move_noreplace(self.source, self.destination)
        self.assertFalse(self.destination.is_symlink())
        self.assertEqual(list(self.destination.iterdir()), [])
        self.assertTrue(self.source.is_dir())

    def test_concurrent_publishers_have_exactly_one_winner(self):
        sources = [self.source]
        for index in range(1, 12):
            source = self.root / ('source-' + str(index))
            source.mkdir()
            (source / 'data').write_text(str(index))
            sources.append(source)

        def publish(source):
            try:
                publication.move_noreplace(source, self.destination)
                return source
            except FileExistsError:
                return None

        with ThreadPoolExecutor(max_workers=12) as pool:
            winners = [value for value in pool.map(publish, sources) if value is not None]
        self.assertEqual(len(winners), 1)
        winner = winners[0]
        self.assertFalse(winner.exists())
        for source in sources:
            if source != winner:
                self.assertTrue((source / 'data').is_file())
        self.assertEqual((self.destination / 'data').read_text(), 'complete' if winner == self.source else winner.name[7:])

    def test_destination_invisible_until_complete_tree_is_durable(self):
        real_copy = publication._copy_tree

        def copy(*args, **kwargs):
            self.assertFalse(os.path.lexists(self.destination))
            result = real_copy(*args, **kwargs)
            self.assertFalse(os.path.lexists(self.destination))
            return result

        with patch.object(publication, '_copy_tree', side_effect=copy):
            publication.move_noreplace(self.source, self.destination)
        self.assertEqual((self.destination / 'nested' / 'second').read_text(), 'also complete')

    def test_interruption_before_publication_keeps_complete_source(self):
        with patch.object(publication.os, 'symlink', side_effect=InterruptedError('crash before commit')):
            with self.assertRaises(InterruptedError):
                publication.move_noreplace(self.source, self.destination)
        self.assertFalse(os.path.lexists(self.destination))
        self.assertEqual((self.source / 'data').read_text(), 'complete')
        publication.move_noreplace(self.source, self.destination)
        self.assertEqual((self.destination / 'data').read_text(), 'complete')

    def test_interruption_after_publication_keeps_independent_complete_output(self):
        with patch.object(publication.shutil, 'rmtree', side_effect=OSError('crash after commit')):
            with self.assertRaisesRegex(RuntimeError, 'published output may exist'):
                publication.move_noreplace(self.source, self.destination)
        (self.source / 'data').write_text('later mutation')
        self.assertEqual((self.destination / 'data').read_text(), 'complete')
        with self.assertRaises(FileExistsError):
            publication.move_noreplace(self.source, self.destination)

    def test_directory_sync_failure_after_commit_is_reported_uncertain(self):
        real_sync = publication._sync_directory

        def sync(path):
            if Path(path) == self.destination.parent and self.destination.is_symlink():
                raise OSError('durability uncertain')
            return real_sync(path)

        with patch.object(publication, '_sync_directory', side_effect=sync):
            with self.assertRaisesRegex(RuntimeError, 'durability or source cleanup uncertain'):
                publication.move_noreplace(self.source, self.destination)
        self.assertEqual((self.destination / 'data').read_text(), 'complete')
        self.assertTrue(self.source.exists())

    def test_source_symlinks_and_special_files_are_rejected(self):
        for name in ('link', 'fifo'):
            candidate = self.source / name
            if name == 'link':
                candidate.symlink_to(self.root)
            else:
                os.mkfifo(candidate)
            with self.assertRaises(ValueError):
                publication.move_noreplace(self.source, self.destination)
            self.assertFalse(os.path.lexists(self.destination))
            candidate.unlink()

    def test_receipt_tampering_and_arbitrary_links_are_rejected(self):
        self.destination.symlink_to(self.source)
        with self.assertRaises(ValueError):
            publication.published_directory(self.destination)
        self.destination.unlink()
        publication.move_noreplace(self.source, self.destination)
        _, receipt = publication.published_directory(self.destination)
        receipt.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'receipt mismatch'):
            publication.published_directory(self.destination)


if __name__ == '__main__':
    unittest.main()
