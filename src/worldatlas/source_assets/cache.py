"""Provide verified local copies of R2 objects and files derived from them."""

import hashlib
import os
import shutil
import time
import zipfile
from collections.abc import Callable, Mapping
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO, NamedTuple

from worldatlas.shared import r2
from worldatlas.shared.files import JSONValue
from worldatlas.source_assets.archives import archive_member

type FileSpec = Mapping[str, JSONValue]


class Download(NamedTuple):
    """An R2 transfer's clock readings and whether it received all bytes."""

    started: float
    ended: float
    completed: bool


def _fingerprint(spec: FileSpec) -> tuple[str, int]:
    """Read a file's expected byte count and SHA-256.

    Args:
        spec: Pinned file metadata.

    Returns:
        The lowercase SHA-256 and the expected byte count.

    Raises:
        ValueError: The sha256 or size_bytes field is invalid.
    """
    digest, size = spec.get("sha256"), spec.get("size_bytes")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(c not in "0123456789abcdef" for c in digest)
        or type(size) is not int
        or size < 0
    ):
        raise ValueError("cloud inputs require explicit SHA-256 and byte size")
    return digest, size


def _location(spec: FileSpec) -> tuple[str, str]:
    """Read the bucket and key of a pinned R2 object.

    Args:
        spec: R2 file metadata.

    Returns:
        The R2 bucket and object key.

    Raises:
        ValueError: The location is missing or has an invalid key.
    """
    bucket, key = spec.get("r2_bucket"), spec.get("r2_key")
    if (
        not isinstance(bucket, str)
        or not bucket
        or not isinstance(key, str)
        or not key
        or "\\" in key
        or any(part in ("", ".", "..") for part in key.split("/"))
    ):
        raise ValueError("invalid pinned R2 location")
    return bucket, key


def validate_object_pin(spec: FileSpec) -> None:
    """Validate a complete, direct R2 object reference.

    Args:
        spec: Bucket, key, byte size and checksum of the object.
    """
    _location(spec)
    _fingerprint(spec)


def _check_file(path: Path, digest: str, size: int) -> None:
    """Verify a local file's byte count and SHA-256.

    Args:
        path: File to verify.
        digest: Expected lowercase SHA-256.
        size: Expected number of bytes.

    Raises:
        ValueError: The path is not a file or the bytes differ.
    """
    if path.is_file():
        with path.open("rb") as stream:
            if (
                os.fstat(stream.fileno()).st_size == size
                and hashlib.file_digest(stream, "sha256").hexdigest() == digest
            ):
                return
    raise ValueError(f"source file size or hash mismatch: {path}")


class SourceCache:
    """Reuse verified files across runs and skip repeat verification within one run.

    The cache path is based on the checksum. Extracted ZIP members also keep
    their original relative paths so readers can find companion files.
    """

    def __init__(
        self,
        directory: Path,
        *,
        check_cancelled: Callable[[], None] = lambda: None,
    ) -> None:
        """Set up a local cache with one R2 client.

        Args:
            directory: Root directory for cached files.
            check_cancelled: Callback that raises if a download should stop.
        """
        self.directory = directory.resolve()
        self.client = r2.make_r2_client()
        self._check_cancelled = check_cancelled
        self.downloads: list[Download] = []
        self._verified: set[tuple[Path, str, int]] = set()

    def close(self) -> None:
        """Close the R2 client."""
        self.client.close()

    def path(self, spec: FileSpec) -> Path:
        """Find where a pinned R2 object or ZIP member belongs locally.

        A whole R2 object uses its own SHA-256 as the directory name and the
        filename from its R2 key. ZIP members go under ``zip-members``, using
        the ZIP's SHA-256 and their paths inside it. A member can have the
        same name as its archive. This keeps ``land_polygons.shp`` beside its
        ``.dbf`` and ``.shx`` files so GDAL can open the Shapefile.

        Args:
            spec: A whole object's R2 pin, or a member pin with an ``archive``
                pin and the exact ``member`` name inside that ZIP.

        Returns:
            The absolute cache path, whether or not the file exists yet.

        Raises:
            ValueError: A pin or member path is invalid.
        """
        path, _, _, _ = self._plan(spec)
        return path

    def _plan(
        self, spec: FileSpec
    ) -> tuple[Path, str, int, Callable[[IO[bytes]], None]]:
        """Resolve the local name, byte pin, and acquisition for one input.

        Args:
            spec: A direct R2 object or a ZIP member and its archive pin.

        Returns:
            (path, SHA-256, byte count, writer). The writer fetches the bytes
            into an open file when the cache does not already have them.
        """
        digest, size = _fingerprint(spec)
        if "archive" not in spec:
            bucket, key = _location(spec)
            path = self.directory / digest / Path(key).name
            return (
                path,
                digest,
                size,
                lambda output: self._download(bucket, key, size, output),
            )

        archive, member = spec["archive"], spec.get("member")
        if not isinstance(archive, dict):
            raise ValueError("ZIP archive must be a pinned file")
        if (
            not isinstance(member, str)
            or "\\" in member
            or any(part in ("", ".", "..") for part in member.split("/"))
        ):
            raise ValueError("unsafe ZIP member")
        archive_path, archive_digest, archive_size, fetch = self._plan(archive)
        path = self.directory / "zip-members" / archive_digest / member

        def extract(output: IO[bytes]) -> None:
            """Copy the selected member of the verified local ZIP.

            Args:
                output: Open temporary file for the extracted member.
            """
            local = self._verified_file(
                archive_path, archive_digest, archive_size, fetch
            )
            with zipfile.ZipFile(local) as packed:
                with packed.open(archive_member(packed, member)) as source:
                    shutil.copyfileobj(source, output, 1 << 20)

        return path, digest, size, extract

    def _verified_file(
        self,
        path: Path,
        digest: str,
        size: int,
        write: Callable[[IO[bytes]], None],
    ) -> Path:
        """Return a verified file, publishing new bytes only after they pass checks.

        Args:
            path: Final cache path.
            digest: Expected SHA-256.
            size: Expected byte count.
            write: Callback that writes the complete file to a temporary destination.

        Returns:
            The verified cache path.
        """
        identity = (path, digest, size)
        if identity in self._verified:
            return path
        if path.exists():
            _check_file(path, digest, size)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            output = NamedTemporaryFile(
                dir=path.parent, prefix="download-", delete=False
            )
            pending = Path(output.name)
            try:
                with output:
                    write(output.file)
                _check_file(pending, digest, size)
                try:
                    os.link(pending, path)
                except FileExistsError:
                    # Another process created the final file first. Check its
                    # size and checksum before returning that file.
                    _check_file(path, digest, size)
            finally:
                pending.unlink(missing_ok=True)
        self._verified.add(identity)
        return path

    def acquire(self, spec: FileSpec) -> Path:
        """Reuse or fetch one complete R2 object or requested ZIP member.

        Args:
            spec: Expected file bytes and their R2 or ZIP location.

        Returns:
            The verified local file path.
        """
        return self._verified_file(*self._plan(spec))

    def _download(self, bucket: str, key: str, size: int, output: IO[bytes]) -> None:
        """Stream one R2 object, check its byte count, and record the transfer time.

        Args:
            bucket: R2 bucket.
            key: R2 object key.
            size: Expected object byte count.
            output: Open temporary output file.

        Raises:
            ValueError: The object's length differs from the expected byte count.
            InterruptedError: The cancellation callback requested a stop.
        """
        self._check_cancelled()
        started = time.monotonic()
        completed = False
        try:
            with self.client.open(bucket, key) as remote:
                if remote.size_bytes is not None and remote.size_bytes != size:
                    raise ValueError("R2 source file size or hash mismatch")
                remaining = size
                while remaining:
                    self._check_cancelled()
                    chunk = remote.body.read(min(4 << 20, remaining))
                    if not chunk:
                        break
                    output.write(chunk)
                    remaining -= len(chunk)
                if remaining or remote.body.read(1):
                    raise ValueError("R2 source file size or hash mismatch")
            completed = True
        finally:
            self.downloads.append(Download(started, time.monotonic(), completed))
