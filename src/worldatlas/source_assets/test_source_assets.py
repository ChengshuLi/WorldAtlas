"""Test verified R2 downloads and cache reuse."""

import hashlib
import io
import os
from contextlib import contextmanager
from pathlib import Path
from stat import S_IFLNK
import tempfile
import unittest
from unittest.mock import Mock, patch
from zipfile import ZipFile, ZipInfo

from worldatlas.shared.r2 import R2Client
from worldatlas.source_assets import cache
from worldatlas.source_assets.archives import archive_member
from worldatlas.source_assets.cache import SourceCache


class ArchiveMemberTest(unittest.TestCase):
    def test_selection_rejects_repeated_names_directories_and_links(self):
        data = io.BytesIO()
        with ZipFile(data, 'w') as archive:
            archive.writestr('duplicate', b'first')
            with self.assertWarns(UserWarning):
                archive.writestr('duplicate', b'second')
            archive.writestr('directory/', b'')
            link = ZipInfo('link')
            link.external_attr = S_IFLNK << 16
            archive.writestr(link, b'target')
            archive.writestr('nested/target', b'content')
        with ZipFile(data) as archive:
            for name in ('duplicate', 'directory/', 'link'):
                with (
                    self.subTest(name=name),
                    self.assertRaisesRegex(ValueError, 'must be one regular file'),
                ):
                    archive_member(archive, name)
            self.assertEqual(
                archive.read(archive_member(archive, 'nested/target')), b'content'
            )


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

    def cloud(self, payload, key="sources/input.json"):
        return {
            "r2_bucket": "worldatlas",
            "r2_key": key,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }

    @contextmanager
    def fake_r2(self, payloads, calls):
        def retrieve(*, Bucket, Key):
            calls.append(Key)
            data = payloads[Key]
            return {"Body": io.BytesIO(data), "ContentLength": len(data)}

        with patch.object(self.storage, "get_object", side_effect=retrieve) as get:
            yield get

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
        self.assertFalse(source_cache.downloads[-1].completed)
        self.storage.get_object.return_value = {'Body': io.BytesIO(self.raw)}
        check.side_effect = None
        self.assertEqual(source_cache.acquire(self.source).read_bytes(), self.raw)
        self.assertEqual([transfer.completed for transfer in source_cache.downloads], [False, True])

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
        with (
            patch.object(cache.time, 'monotonic', side_effect=lambda: clock[0]),
            patch.object(cache, '_check_file', side_effect=verify),
        ):
            self.cache.acquire(self.source)
            self.cache.acquire(self.source)
        self.assertEqual(self.cache.downloads, [(0.0, 3.0, True)])
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

    def test_zip_members_can_use_the_archive_name(self):
        for name in ("archive.zip", "archive.zip/nested/data.shp"):
            with self.subTest(name=name):
                buffer = io.BytesIO()
                payload = b"geometry"
                with ZipFile(buffer, "w") as packed:
                    packed.writestr(name, payload)
                archive = self.cloud(buffer.getvalue(), "sources/archive.zip")
                pin = dict(
                    archive=archive,
                    member=name,
                    size_bytes=len(payload),
                    sha256=hashlib.sha256(payload).hexdigest(),
                )
                calls = []
                with self.fake_r2({"sources/archive.zip": buffer.getvalue()}, calls):
                    cache = self.cache
                    path = cache.acquire(archive)
                    member = cache.acquire(pin)
                    self.assertNotEqual(member, path)
                    self.assertEqual(member.read_bytes(), payload)
                    self.assertEqual(path.read_bytes(), buffer.getvalue())
                    self.assertEqual(cache.acquire(pin), member)
                self.assertEqual(calls, ["sources/archive.zip"])

    def test_invalid_zip_members_are_never_published_to_cache(self):
        source_cache = self.cache
        packed = io.BytesIO()
        payload = b"geometry"
        with ZipFile(packed, "w") as archive:
            archive.writestr("data.shp", payload)
        archive = self.cloud(packed.getvalue(), "sources/archive.zip")
        pin = dict(
            archive=archive,
            member="data.shp",
            size_bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
        )
        output = source_cache.path(pin)
        with self.fake_r2({"sources/archive.zip": packed.getvalue()}, []) as download:
            for changes, reason in (
                ({"member": 1}, "unsafe ZIP member"),
                ({"member": "missing.shp"}, "must be one regular file"),
                ({"sha256": "0" * 64}, "size or hash mismatch"),
            ):
                with self.subTest(changes=changes):
                    with self.assertRaisesRegex(ValueError, reason):
                        source_cache.acquire(dict(pin, **changes))
                    self.assertFalse(output.exists())
                    self.assertEqual(list(output.parent.glob("*.partial")), [])
            self.assertEqual(source_cache.acquire(pin).read_bytes(), payload)
            self.assertEqual(download.call_count, 1)

    def test_zip_cache_publication_checks_a_concurrent_writers_bytes(self):
        source_cache = self.cache
        packed = io.BytesIO()
        payload = b"geometry"
        with ZipFile(packed, "w") as archive:
            archive.writestr("one.shp", payload)
            archive.writestr("two.shp", payload)
        archive = self.cloud(packed.getvalue(), "sources/archive.zip")

        link = os.link
        for member, content in (("one.shp", payload), ("two.shp", b"corrupt!")):
            with self.subTest(member=member):
                pin = dict(
                    archive=archive,
                    member=member,
                    size_bytes=len(payload),
                    sha256=hashlib.sha256(payload).hexdigest(),
                )
                output = source_cache.path(pin)

                def race(source, destination):
                    if destination == output:
                        output.write_bytes(content)
                    return link(source, destination)

                with (
                    self.fake_r2({"sources/archive.zip": packed.getvalue()}, []),
                    patch.object(os, "link", side_effect=race),
                ):
                    if content == payload:
                        self.assertEqual(
                            source_cache.acquire(pin).read_bytes(), payload
                        )
                    else:
                        with self.assertRaisesRegex(
                            ValueError, "size or hash mismatch"
                        ):
                            source_cache.acquire(pin)
                self.assertEqual(output.read_bytes(), content)
                self.assertEqual(list(output.parent.glob("*.partial")), [])

    def test_wrong_download_is_never_published(self):
        source_cache = self.cache
        spec = self.cloud(b"{}")
        with self.fake_r2({"sources/input.json": b"wrong"}, []):
            with self.assertRaisesRegex(
                ValueError, "size or hash mismatch"
            ):
                source_cache.acquire(spec)
        self.assertFalse(source_cache.path(spec).exists())
        self.assertEqual(len(list((self.directory).rglob("download-*"))), 0)

    def test_invalid_cloud_pin_is_rejected(self):
        source_cache = self.cache
        spec = self.cloud(b"source", "raw/list.json")
        for changes, message in (
            ({"size_bytes": None}, "explicit SHA-256 and byte size"),
            ({"r2_key": "raw/../list.json"}, "invalid pinned R2 location"),
        ):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError, message):
                    source_cache.acquire(dict(spec, **changes))

    def test_cache_reuses_same_bytes_from_different_r2_keys(self):
        source_cache = self.cache
        payload = b"archive byte sequence"
        first = self.cloud(payload, "folder1/shared.bin")
        second = self.cloud(payload, "folder2/shared.bin")
        with self.fake_r2({first["r2_key"]: payload}, []) as download:
            self.assertEqual(source_cache.acquire(first), source_cache.acquire(second))
            download.assert_called_once()

    def test_import_cache_is_reused_without_network_or_download_time(self):
        payload = b"{}"
        source = self.cloud(payload)
        cached = self.directory / source["sha256"] / "input.json"
        cached.parent.mkdir()
        cached.write_bytes(payload)
        source_cache = self.cache
        with self.fake_r2({}, []) as download:
            self.assertEqual(source_cache.acquire(source), cached)
        download.assert_not_called()
        self.assertEqual(source_cache.downloads, [])

    def test_cached_cloud_corruption_and_zip_path_escapes_fail_closed(self):
        payload = b"{}"
        spec = self.cloud(payload)
        cached = self.directory / spec["sha256"] / "input.json"
        cached.parent.mkdir(parents=True)
        source_cache = self.cache
        with self.fake_r2({}, []) as download:
            cached.mkdir()
            with self.assertRaisesRegex(
                ValueError, "size or hash mismatch"
            ):
                source_cache.acquire(spec)
            cached.rmdir()
            cached.write_bytes(b"xx")
            with self.assertRaisesRegex(
                ValueError, "size or hash mismatch"
            ):
                source_cache.acquire(spec)
        download.assert_not_called()
        cached.write_bytes(payload)
        with self.assertRaisesRegex(ValueError, "unsafe ZIP member"):
            source_cache.acquire(
                dict(archive=spec, member="../outside", sha256="a" * 64, size_bytes=1)
            )


if __name__ == '__main__':
    unittest.main()
