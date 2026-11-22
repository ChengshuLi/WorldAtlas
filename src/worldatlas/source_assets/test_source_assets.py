"""Test verified R2 downloads and cache reuse."""

import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from worldatlas.shared.r2 import R2Client
from worldatlas.source_assets import cache
from worldatlas.source_assets.cache import SourceCache


class DownloadTest(unittest.TestCase):
    """Exercise the file cache with temporary files and an in-memory R2 client."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve()
        self.raw = b'archived source bytes'
        self.source = {
            'r2_bucket': 'test',
            'r2_key': 'source.zip',
            'sha256': hashlib.sha256(self.raw).hexdigest(),
            'size_bytes': len(self.raw),
        }
        self.storage = Mock()
        self.enterContext(
            patch.object(cache.r2, 'make_r2_client', return_value=R2Client(self.storage))
        )
        self.cache = SourceCache(self.directory)
        self.addCleanup(self.cache.close)
        self.storage.get_object.return_value = {'Body': io.BytesIO(self.raw)}

    def test_download_and_reuse(self):
        path = self.cache.acquire(self.source)
        self.assertEqual(path.read_bytes(), self.raw)
        self.storage.get_object.assert_called_once_with(Bucket='test', Key='source.zip')
        self.assertEqual(self.cache.acquire(self.source), path)
        self.assertEqual(self.storage.get_object.call_count, 1)

    def test_cache_cancellation_stops_a_zip_archive_download(self):
        body = io.BytesIO(self.raw)
        self.storage.get_object.return_value = {'Body': body}
        check = Mock(side_effect=[None, InterruptedError('cancelled during transfer')])
        source_cache = SourceCache(self.directory, check_cancelled=check)
        self.addCleanup(source_cache.close)
        member = {
            'archive': self.source,
            'member': 'coast.shp',
            'sha256': 'a' * 64,
            'size_bytes': 10,
        }
        with self.assertRaisesRegex(InterruptedError, 'cancelled during transfer'):
            source_cache.acquire(member)
        self.assertTrue(body.closed)
        self.assertFalse(source_cache.path(self.source).exists())
        self.assertFalse(source_cache.path(member).exists())
        self.assertFalse(list(self.directory.rglob('download-*')))

    def test_download_time_excludes_verification_and_cached_reuse(self):
        clock = [0.0]
        original = cache._check_file

        def retrieve(**kwargs):
            clock[0] += 3.0
            return {'Body': io.BytesIO(self.raw)}

        def verify(path, digest, size):
            clock[0] += 7.0
            original(path, digest, size)

        self.storage.get_object.side_effect = retrieve
        with patch.object(cache.time, 'monotonic', side_effect=lambda: clock[0]), patch.object(
            cache, '_check_file', side_effect=verify
        ):
            self.cache.acquire(self.source)
            self.cache.acquire(self.source)
        self.assertEqual(self.cache.download_intervals, [(0.0, 3.0)])
        self.assertEqual(clock[0], 10.0)

    def test_reject_corrupt_download_and_remove_partial(self):
        self.storage.get_object.return_value = {'Body': io.BytesIO(b'x' * len(self.raw))}
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            self.cache.acquire(self.source)
        self.assertFalse(list(self.directory.rglob('download-*')))
        self.assertFalse((self.directory / self.source['sha256'] / 'source.zip').exists())

    def test_reject_wrong_catalog_size(self):
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            self.cache.acquire(dict(self.source, size_bytes=1))

    def test_rejects_transfer_shorter_than_announced_without_caching_it(self):
        body = io.BytesIO(self.raw[:4])
        self.storage.get_object.return_value = {'Body': body, 'ContentLength': len(self.raw)}
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            self.cache.acquire(self.source)
        self.assertTrue(body.closed)
        self.assertFalse((self.directory / self.source['sha256'] / 'source.zip').exists())
        self.assertFalse(list(self.directory.rglob('download-*')))

    def test_reject_corrupt_cache(self):
        path = self.cache.acquire(self.source)
        path.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            SourceCache(self.directory).acquire(self.source)
        self.assertEqual(self.storage.get_object.call_count, 1)

    def test_zip_member_requires_a_file_pin_for_its_archive(self):
        with self.assertRaisesRegex(ValueError, 'archive must be a pinned file'):
            self.cache.acquire(dict(self.source, archive='coast.zip', member='coast.shp'))
        self.storage.get_object.assert_not_called()

    def test_verifies_cache_file_published_by_a_competing_download(self):
        self.storage.get_object.side_effect = lambda **_: {'Body': io.BytesIO(self.raw)}
        destination = self.directory / self.source['sha256'] / 'source.zip'
        link = cache.os.link
        for valid, competing_bytes in ((True, self.raw), (False, b'x' * len(self.raw))):
            source_cache = SourceCache(self.directory)
            self.addCleanup(source_cache.close)

            def competing_publish(partial, final):
                if final == destination:
                    final.write_bytes(competing_bytes)
                link(partial, final)

            with self.subTest(valid=valid), patch.object(cache.os, 'link', side_effect=competing_publish):
                if valid:
                    self.assertEqual(source_cache.acquire(self.source), destination)
                else:
                    with self.assertRaisesRegex(ValueError, 'size or hash'):
                        source_cache.acquire(self.source)

            self.assertEqual(destination.read_bytes(), competing_bytes)
            self.assertFalse(list(destination.parent.glob('download-*')))
            destination.unlink()

    def test_download_error_removes_partial(self):
        self.storage.get_object.side_effect = OSError('connection interrupted')
        with self.assertRaisesRegex(OSError, 'interrupted'):
            self.cache.acquire(self.source)
        self.assertFalse(list(self.directory.rglob('download-*')))
        self.assertFalse((self.directory / self.source['sha256'] / 'source.zip').exists())

    def test_ordinary_raster_keeps_its_extension(self):
        source = dict(self.source, r2_key='provider/elevation.tif')
        path = self.cache.acquire(source)
        self.assertEqual(path.name, 'elevation.tif')
        self.assertEqual(path.read_bytes(), self.raw)


if __name__ == '__main__':
    unittest.main()
