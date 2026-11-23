"""Check that atomic writes preserve completed files and handle failed publication."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from worldatlas.shared.files import write_bytes_atomic


class AtomicWriteTests(unittest.TestCase):
    def test_atomic_publish_preserves_pending_on_link_failure(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'report.json'
            with mock.patch.object(os, 'link', side_effect=OSError('link failure')):
                with self.assertRaisesRegex(OSError, 'link failure'):
                    write_bytes_atomic(path, b'payload')
            self.assertFalse(path.exists())
            self.assertEqual(
                [p.read_bytes() for p in Path(d).glob('.report.json.*.pending')], [b'payload']
            )

    def test_atomic_publish_does_not_overwrite_existing(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'report.json'
            path.write_bytes(b'existing')
            with self.assertRaises(FileExistsError):
                write_bytes_atomic(path, b'new')
            self.assertEqual(path.read_bytes(), b'existing')
            self.assertEqual(list(Path(d).glob('.report.json.*.pending')), [])
