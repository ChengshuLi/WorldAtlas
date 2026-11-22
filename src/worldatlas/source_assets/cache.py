"""Provide verified local copies of R2 objects and files derived from them."""

import hashlib
import os
import shutil
import time
import zipfile
from collections.abc import Callable, Mapping, Sequence
from contextlib import closing
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO

from worldatlas.shared import r2
from worldatlas.shared.files import JSONValue

type FileSpec = Mapping[str, JSONValue]


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


def _stream_object(
    client: r2.R2Client,
    bucket: str,
    key: str,
    size: int,
    output: IO[bytes],
    check_cancelled: Callable[[], None],
) -> None:
    """Copy an entire R2 object, checking its length and stopping on cancellation.

    Args:
        client: Open R2 client.
        bucket: Object's bucket name.
        key: Object's key within the bucket.
        size: Expected object byte count.
        output: Open local file receiving the bytes.
        check_cancelled: Callback that raises if work should stop.

    Raises:
        ValueError: The object's length differs from the expected byte count.
    """
    check_cancelled()
    with client.open(bucket, key) as remote:
        if remote.size_bytes is not None and remote.size_bytes != size:
            raise ValueError("R2 source file size or hash mismatch")
        remaining = size
        while remaining:
            check_cancelled()
            chunk = remote.body.read(min(4 << 20, remaining))
            if not chunk:
                break
            output.write(chunk)
            remaining -= len(chunk)
        if remaining or remote.body.read(1):
            raise ValueError("R2 source file size or hash mismatch")


class SourceCache:
    """Reuse verified files across runs and skip repeat verification within one run.

    The cache path is based on the checksum. Extracted ZIP members also keep
    their original relative paths so readers can find companion files.
    """

    def __init__(
        self,
        directory: Path,
        *,
        endpoint: str = r2.DEFAULT_R2_ENDPOINT,
        client: r2.R2Client | None = None,
    ) -> None:
        """Configure a local cache and the R2 connection to use for misses.

        Args:
            directory: Root directory for cached files.
            endpoint: R2 account URL used when opening a client.
            client: Existing R2 client, kept open by its caller.
        """
        self.directory = directory.resolve()
        self.endpoint = endpoint
        self.client = client
        self.pins: list[dict[str, str]] = []
        self.download_intervals: list[tuple[float, float]] = []
        self._verified: set[tuple[Path, str, int]] = set()

    def path(self, spec: FileSpec) -> Path:
        """Find where a pinned R2 object or ZIP member belongs locally.

        Args:
            spec: File pin with a direct location or an archive and member name.

        Returns:
            The absolute cache path, whether or not the file exists yet.

        Raises:
            ValueError: A pin or member path is invalid.
        """
        digest, _ = _fingerprint(spec)
        if "archive" not in spec:
            _, key = _location(spec)
            return self.directory / digest / Path(key).name

        archive, member = spec["archive"], spec.get("member")
        if not isinstance(archive, dict):
            raise ValueError("ZIP archive must be a pinned file")
        if (
            not isinstance(member, str)
            or "\\" in member
            or any(part in ("", ".", "..") for part in member.split("/"))
        ):
            raise ValueError("unsafe ZIP member")
        self.path(archive)
        archive_digest, _ = _fingerprint(archive)
        return self.directory / archive_digest / member

    def _verified_file(
        self,
        path: Path,
        digest: str,
        size: int,
        write: Callable[[IO[bytes]], None],
        *,
        previous: Path | None = None,
    ) -> Path:
        """Return a verified file, publishing new bytes only after they pass checks.

        Args:
            path: Final cache path.
            digest: Expected SHA-256.
            size: Expected byte count.
            write: Callback that writes the complete file to a temporary destination.
            previous: Alternate filename used by earlier imports, if applicable.

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
            if previous is not None and previous != path and previous.is_file():
                _check_file(previous, digest, size)
                self._publish(previous, path, digest, size)
            else:
                output = NamedTemporaryFile(
                    dir=path.parent, prefix="download-", delete=False
                )
                pending = Path(output.name)
                try:
                    with output:
                        write(output.file)
                    _check_file(pending, digest, size)
                    self._publish(pending, path, digest, size)
                finally:
                    pending.unlink(missing_ok=True)
        self._verified.add(identity)
        self.pins.append({"path": str(path), "sha256": digest})
        return path

    @staticmethod
    def _publish(source: Path, path: Path, digest: str, size: int) -> None:
        """Link verified bytes to the final name or check a competing writer's bytes.

        Args:
            source: Verified local bytes.
            path: Final cache path.
            digest: Expected SHA-256.
            size: Expected byte count.
        """
        try:
            os.link(source, path)
        except FileExistsError:
            _check_file(path, digest, size)

    def acquire(
        self,
        spec: FileSpec,
        *,
        endpoint: str | None = None,
        check_cancelled: Callable[[], None] = lambda: None,
    ) -> Path:
        """Reuse or fetch one complete R2 object or requested ZIP member.

        Args:
            spec: Expected file bytes and their R2 or ZIP location.
            endpoint: Account URL override for these bytes.
            check_cancelled: Optional callback that raises during cancelled work.

        Returns:
            The verified local file path.
        """
        path = self.path(spec)
        digest, size = _fingerprint(spec)
        if "archive" in spec:
            return self._verified_file(
                path,
                digest,
                size,
                lambda output: self._extract(spec, output, endpoint, check_cancelled),
            )

        bucket, key = _location(spec)
        # Older imports used source.ext even when the provider supplied a name.
        previous = path.with_name("source" + (Path(key).suffix or ".bin"))
        return self._verified_file(
            path,
            digest,
            size,
            lambda output: self._download(
                bucket, key, size, output, endpoint or self.endpoint, check_cancelled
            ),
            previous=previous,
        )

    def _download(
        self,
        bucket: str,
        key: str,
        size: int,
        output: IO[bytes],
        endpoint: str,
        check_cancelled: Callable[[], None],
    ) -> None:
        """Transfer one object and record the time spent on the transfer itself.

        Args:
            bucket: R2 bucket.
            key: R2 object key.
            size: Expected object byte count.
            output: Open temporary output file.
            endpoint: Account URL if the caller did not supply a client.
            check_cancelled: Callback that raises if work should stop.
        """
        started = time.monotonic()
        try:
            if self.client is not None:
                _stream_object(self.client, bucket, key, size, output, check_cancelled)
            else:
                with closing(r2.make_r2_client(endpoint)) as client:
                    _stream_object(client, bucket, key, size, output, check_cancelled)
        finally:
            self.download_intervals.append((started, time.monotonic()))

    def _extract(
        self,
        spec: FileSpec,
        output: IO[bytes],
        endpoint: str | None,
        check_cancelled: Callable[[], None],
    ) -> None:
        """Read a single regular ZIP member from its verified archive.

        Args:
            spec: Validated archive and member pin.
            output: Open temporary output file.
            endpoint: Account URL override for the archive.
            check_cancelled: Callback that raises if work should stop.

        Raises:
            ValueError: The member is missing, ambiguous, or not a regular file.
        """
        archive, member = spec["archive"], spec["member"]
        assert isinstance(archive, dict) and isinstance(member, str)
        local = self.acquire(
            archive, endpoint=endpoint, check_cancelled=check_cancelled
        )
        with zipfile.ZipFile(local) as packed:
            matches = [item for item in packed.infolist() if item.filename == member]
            if (
                len(matches) != 1
                or matches[0].is_dir()
                or ((matches[0].external_attr >> 16) & 0o170000) == 0o120000
            ):
                raise ValueError("ZIP member must be one regular file")
            with packed.open(matches[0]) as source:
                shutil.copyfileobj(source, output, 1 << 20)

    def assemble(
        self, parts: Sequence[FileSpec], digest: str, size: int, filename: str
    ) -> Path:
        """Reuse or assemble a provider file stored as several R2 objects.

        Args:
            parts: File pins in byte order.
            digest: SHA-256 of the complete file.
            size: Byte count of the complete file.
            filename: Plain filename for the assembled file.

        Returns:
            The verified local path to the complete file.

        Raises:
            ValueError: The parts, filename, or resulting bytes are invalid.
        """
        if (
            not parts
            or not filename
            or Path(filename).name != filename
            or filename in (".", "..")
        ):
            raise ValueError("ordered source parts and a plain filename are required")
        digest, size = _fingerprint({"sha256": digest, "size_bytes": size})
        if sum(_fingerprint(part)[1] for part in parts) != size:
            raise ValueError("source part sizes do not match the complete file")

        def join(output: IO[bytes]) -> None:
            """Copy the verified local parts to the assembly in byte order.

            Args:
                output: Open temporary output file.
            """
            for part in parts:
                with self.acquire(part).open("rb") as source:
                    shutil.copyfileobj(source, output, 1 << 20)

        path = self.directory / digest / filename
        return self._verified_file(path, digest, size, join)
