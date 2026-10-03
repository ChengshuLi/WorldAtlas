"""A later geographic release must not substitute new bytes for earlier evidence."""
import gzip
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'data/macro-improvements/macro-boundary-reconciliation/verify.py'
spec = importlib.util.spec_from_file_location('macro_boundary_replay', MODULE)
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


class ArchivedInputReplay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original_root = replay.ROOT
        replay.ROOT = Path(self.tmp.name)
        self.release = {'hierarchy_sha256': 'earlier-release'}
        self.original = b'{"version":3}'
        self.expected = hashlib.sha256(self.original).hexdigest()
        self.current = replay.ROOT / 'data/hierarchy.json'
        self.current.parent.mkdir(parents=True)
        self.current.write_bytes(b'{"version":4}')
        self.archive = (replay.ROOT / 'data/macro-foundation/predecessor-inspections' /
                        'earlier-release/hierarchy.json.gz')
        self.archive.parent.mkdir(parents=True)

    def tearDown(self):
        replay.ROOT = self.original_root
        self.tmp.cleanup()

    def test_new_release_replays_original_archive_bytes(self):
        self.archive.write_bytes(gzip.compress(self.original))
        self.assertEqual(replay.pinned_bytes('data/hierarchy.json', self.expected,
                                           self.release), self.original)
        self.assertEqual(self.current.read_bytes(), b'{"version":4}')

    def test_wrong_archive_is_rejected(self):
        self.archive.write_bytes(gzip.compress(b'{"version":999}'))
        with self.assertRaisesRegex(AssertionError, 'archived input hash'):
            replay.pinned_bytes('data/hierarchy.json', self.expected, self.release)

    def test_matching_current_bytes_need_no_archive(self):
        self.current.write_bytes(self.original)
        self.assertEqual(replay.pinned_bytes('data/hierarchy.json', self.expected,
                                           self.release), self.original)

    def test_unsupported_changed_input_is_not_silently_skipped(self):
        with self.assertRaisesRegex(AssertionError, 'without preserved archive'):
            replay.pinned_bytes('data/unpreserved.json', self.expected, self.release)


if __name__ == '__main__':
    unittest.main()
