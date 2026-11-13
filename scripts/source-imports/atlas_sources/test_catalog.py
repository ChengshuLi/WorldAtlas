import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from atlas_sources.catalog import download_source, assemble_parts


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.raw = b'archived source bytes'
        self.source = {
            'r2_bucket': 'test',
            'r2_key': 'source.zip',
            'sha256': hashlib.sha256(self.raw).hexdigest(),
            'size_bytes': len(self.raw),
        }
        self.storage = Mock()
        self.storage.get_object.return_value = {'Body': io.BytesIO(self.raw)}

    def test_download_and_reuse(self):
        path = download_source(self.storage, self.source, self.directory)
        self.assertEqual(path.read_bytes(), self.raw)
        self.storage.get_object.assert_called_once_with(Bucket='test', Key='source.zip')
        self.assertEqual(download_source(self.storage, self.source, self.directory), path)
        self.assertEqual(self.storage.get_object.call_count, 1)

    def test_map_and_import_names_share_the_same_verified_bytes(self):
        imported = download_source(self.storage, self.source, self.directory)
        named = download_source(self.storage, self.source, self.directory, filename='provider.zip')
        self.assertEqual(imported.stat().st_ino, named.stat().st_ino)
        self.assertEqual(named.read_bytes(), self.raw)
        self.assertEqual(self.storage.get_object.call_count, 1)

    def test_import_reuses_a_source_previously_cached_by_the_map(self):
        source = dict(self.source, r2_key='provider/archived.zip')
        named = download_source(self.storage, source, self.directory, filename='archived.zip')
        imported = download_source(self.storage, source, self.directory)
        self.assertEqual(imported.stat().st_ino, named.stat().st_ino)
        self.assertEqual(self.storage.get_object.call_count, 1)

    def test_download_time_excludes_verification_and_cached_reuse(self):
        import atlas_sources.catalog as catalog

        clock, timing = [0.0], {}
        original = catalog.check_source

        def retrieve(**kwargs):
            clock[0] += 3.0
            return {'Body': io.BytesIO(self.raw)}

        def verify(path, source):
            clock[0] += 7.0
            original(path, source)

        self.storage.get_object.side_effect = retrieve
        with patch('atlas_sources.catalog.time.monotonic', side_effect=lambda: clock[0]), patch(
            'atlas_sources.catalog.check_source', side_effect=verify
        ):
            download_source(self.storage, self.source, self.directory, timing=timing)
            download_source(self.storage, self.source, self.directory, timing=timing)
        self.assertEqual(timing['download_seconds'], 3.0)
        self.assertEqual(clock[0], 17.0)

    def test_reject_corrupt_download_and_remove_partial(self):
        self.storage.get_object.return_value = {'Body': io.BytesIO(b'corrupt')}
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            download_source(self.storage, self.source, self.directory)
        self.assertEqual(list(self.directory.rglob('*.*')), [])

    def test_reject_wrong_catalog_size(self):
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            download_source(self.storage, dict(self.source, size_bytes=1), self.directory)

    def test_reject_corrupt_cache(self):
        path = download_source(self.storage, self.source, self.directory)
        path.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            download_source(self.storage, self.source, self.directory)
        self.assertEqual(self.storage.get_object.call_count, 1)

    def test_download_error_removes_partial(self):
        self.storage.get_object.side_effect = OSError('connection interrupted')
        with self.assertRaisesRegex(OSError, 'interrupted'):
            download_source(self.storage, self.source, self.directory)
        self.assertEqual(list(self.directory.rglob('*.*')), [])

    def test_ordinary_raster_keeps_its_extension(self):
        source = dict(self.source, r2_key='provider/elevation.tif')
        path = download_source(self.storage, source, self.directory)
        self.assertEqual(path.name, 'source.tif')
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
        path = assemble_parts(
            self.storage, parts, digest, len(whole), 'provider.tif', self.directory
        )
        self.assertEqual(path.read_bytes(), whole)
        self.assertEqual(self.storage.get_object.call_count, 2)
        self.assertEqual(
            assemble_parts(self.storage, parts, digest, len(whole), 'provider.tif', self.directory),
            path,
        )
        self.assertEqual(self.storage.get_object.call_count, 2)

    def test_multipart_download_times_accumulate_without_charging_reassembly(self):
        parts, whole, digest = self.parts()
        timing = {}
        with patch('atlas_sources.catalog.time.monotonic', side_effect=[0.0, 2.0, 4.0, 7.0]):
            assemble_parts(
                self.storage,
                parts,
                digest,
                len(whole),
                'provider.tif',
                self.directory,
                timing=timing,
            )
            assemble_parts(
                self.storage,
                parts,
                digest,
                len(whole),
                'provider.tif',
                self.directory,
                timing=timing,
            )
        self.assertEqual(timing['download_seconds'], 5.0)
        self.assertEqual(self.storage.get_object.call_count, 2)

    def test_wrong_part_order_fails_complete_checksum(self):
        parts, whole, digest = self.parts()
        self.storage.get_object.side_effect = [
            {'Body': io.BytesIO(b'second bytes')},
            {'Body': io.BytesIO(b'first bytes')},
        ]
        with self.assertRaisesRegex(ValueError, 'size or hash'):
            assemble_parts(
                self.storage, parts[::-1], digest, len(whole), 'provider.tif', self.directory
            )
        self.assertFalse(list(self.directory.rglob('assembly-*')))
        self.assertFalse((self.directory / digest / 'provider.tif').exists())

    def test_inconsistent_part_sizes_fail_before_downloading(self):
        parts, whole, digest = self.parts()
        with self.assertRaisesRegex(ValueError, 'part sizes'):
            assemble_parts(
                self.storage, parts, digest, len(whole) + 1, 'provider.tif', self.directory
            )
        self.storage.get_object.assert_not_called()


if __name__ == '__main__':
    unittest.main()
