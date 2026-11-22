"""Test verified R2 downloads, cache reuse, and multipart assembly."""

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
        self.make_client = self.enterContext(
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

    def test_reject_download_filename_outside_cache_directory(self):
        with self.assertRaisesRegex(ValueError, 'plain filename'):
            self.cache.assemble([self.source], self.source['sha256'], len(self.raw), '../terrain.tif')
        self.storage.get_object.assert_not_called()

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

    def assert_competing_cache_write_is_verified(self, acquire, destination, expected):
        """Publish fixtures just before the caller tries to link the same path."""
        link = cache.os.link
        for valid, competing_bytes in ((True, expected), (False, b'x' * len(expected))):
            self.cache = SourceCache(self.directory)

            def competing_publish(partial, final):
                if final == destination:
                    final.write_bytes(competing_bytes)
                link(partial, final)

            with self.subTest(valid=valid), patch.object(cache.os, 'link', side_effect=competing_publish):
                if valid:
                    self.assertEqual(acquire(), destination)
                else:
                    with self.assertRaisesRegex(ValueError, 'size or hash'):
                        acquire()

            self.assertEqual(destination.read_bytes(), competing_bytes)
            self.assertFalse(list(destination.parent.glob('download-*')))
            destination.unlink()

    def test_verifies_cache_file_published_by_a_competing_download(self):
        self.storage.get_object.side_effect = lambda **_: {'Body': io.BytesIO(self.raw)}
        destination = self.directory / self.source['sha256'] / 'source.zip'
        self.assert_competing_cache_write_is_verified(
            lambda: self.cache.acquire(self.source), destination, self.raw
        )

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

    def parts(self):
        payloads = [b'first bytes', b'second bytes']
        sources = [
            dict(
                r2_bucket='test',
                r2_key=f'part-{i}.bin',
                sha256=hashlib.sha256(raw).hexdigest(),
                size_bytes=len(raw),
            )
            for i, raw in enumerate(payloads)
        ]
        self.storage.get_object.side_effect = [{'Body': io.BytesIO(raw)} for raw in payloads]
        whole = b''.join(payloads)
        return sources, whole, hashlib.sha256(whole).hexdigest()

    def test_reassemble_verified_parts_and_reuse_complete_file(self):
        parts, whole, digest = self.parts()
        path = self.cache.assemble(parts, digest, len(whole), 'provider.tif')
        self.assertEqual(path.read_bytes(), whole)
        self.assertEqual(self.storage.get_object.call_count, 2)
        self.assertEqual(
            self.cache.assemble(parts, digest, len(whole), 'provider.tif'),
            path,
        )
        self.assertEqual(self.storage.get_object.call_count, 2)
        self.make_client.assert_called_once_with()

    def test_verifies_complete_file_published_by_a_competing_assembly(self):
        parts, whole, digest = self.parts()
        destination = self.directory / digest / 'provider.tif'
        self.assert_competing_cache_write_is_verified(
            lambda: self.cache.assemble(parts, digest, len(whole), destination.name),
            destination, whole,
        )
        self.assertEqual(self.storage.get_object.call_count, 2)

    def test_rejects_multipart_requests_with_no_parts_or_invalid_filename(self):
        parts, whole, digest = self.parts()
        for requested, filename in (([], 'provider.tif'), (parts, '../provider.tif')):
            with (self.subTest(part_count=len(requested), filename=filename),
                  self.assertRaisesRegex(ValueError, 'ordered source parts and a plain filename')):
                self.cache.assemble(requested, digest, len(whole), filename)
        self.storage.get_object.assert_not_called()

    def test_multipart_download_times_accumulate_without_charging_reassembly(self):
        parts, whole, digest = self.parts()
        with patch.object(cache.time, 'monotonic', side_effect=[0.0, 2.0, 4.0, 7.0]):
            self.cache.assemble(parts, digest, len(whole), 'provider.tif')
        self.assertEqual(self.cache.download_intervals, [(0.0, 2.0), (4.0, 7.0)])
        self.assertEqual(self.storage.get_object.call_count, 2)

    def test_wrong_part_order_fails_complete_checksum(self):
        parts, whole, digest = self.parts()
        self.storage.get_object.side_effect = [
            {'Body': io.BytesIO(b'second bytes')},
            {'Body': io.BytesIO(b'first bytes')},
        ]
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            self.cache.assemble(parts[::-1], digest, len(whole), 'provider.tif')
        self.assertFalse(list(self.directory.rglob('download-*')))
        self.assertFalse((self.directory / digest / 'provider.tif').exists())

    def test_inconsistent_part_sizes_fail_before_downloading(self):
        parts, whole, digest = self.parts()
        with self.assertRaisesRegex(ValueError, 'part sizes'):
            self.cache.assemble(parts, digest, len(whole) + 1, 'provider.tif')
        self.storage.get_object.assert_not_called()


if __name__ == '__main__':
    unittest.main()
