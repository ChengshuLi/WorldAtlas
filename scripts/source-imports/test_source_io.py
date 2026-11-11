import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from source_io import download_archive


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.raw = b'archived source bytes'
        self.source = {'r2_bucket': 'test', 'r2_key': 'source.zip',
                       'sha256': hashlib.sha256(self.raw).hexdigest(),
                       'size_bytes': len(self.raw)}
        self.storage = Mock()
        self.storage.get_object.return_value = {'Body': io.BytesIO(self.raw)}

    def test_download_and_reuse(self):
        path = download_archive(self.storage, self.source, self.directory)
        self.assertEqual(path.read_bytes(), self.raw)
        self.storage.get_object.assert_called_once_with(Bucket='test', Key='source.zip')
        self.assertEqual(download_archive(self.storage, self.source, self.directory), path)
        self.assertEqual(self.storage.get_object.call_count, 1)

    def test_reject_corrupt_download_and_remove_partial(self):
        self.storage.get_object.return_value = {'Body': io.BytesIO(b'corrupt')}
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            download_archive(self.storage, self.source, self.directory)
        self.assertEqual(list(self.directory.rglob('*.*')), [])

    def test_reject_wrong_catalog_size(self):
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            download_archive(self.storage, dict(self.source, size_bytes=1), self.directory)

    def test_reject_corrupt_cache(self):
        path = download_archive(self.storage, self.source, self.directory)
        path.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            download_archive(self.storage, self.source, self.directory)
        self.assertEqual(self.storage.get_object.call_count, 1)

    def test_download_error_removes_partial(self):
        self.storage.get_object.side_effect = OSError('connection interrupted')
        with self.assertRaisesRegex(OSError, 'interrupted'):
            download_archive(self.storage, self.source, self.directory)
        self.assertEqual(list(self.directory.rglob('*.*')), [])


if __name__ == '__main__':
    unittest.main()
