"""Acquire pinned R2 input files into the shared build cache."""

import os
import shutil
import uuid
import zipfile
from contextlib import closing
from pathlib import Path
from typing import Any

from worldatlas.shared import r2
from worldatlas.source_assets.catalog import check_source, download_source


def _cloud_file_matches(path: Path, spec: dict[str, Any]) -> bool:
    """Check that a regular file has the expected bytes.

    Args:
        path: File to verify.
        spec: Expected byte size and SHA-256.

    Returns:
        True if the file matches both values.
    """
    if not path.is_file():
        return False
    try:
        check_source(path, spec)
    except ValueError:
        return False
    return True


def _extract_cloud_member(
    archive: Path, member: str, path: Path, spec: dict[str, Any]
) -> None:
    """Extract and verify one ZIP member before publishing it to the shared cache.

    Args:
        archive: Local path to the verified ZIP.
        member: Validated relative member name inside the ZIP.
        path: Local cache destination.
        spec: Expected byte size and SHA-256.

    Raises:
        ValueError: The member is missing, ambiguous, or fails verification.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + "." + uuid.uuid4().hex + ".partial")
    try:
        with zipfile.ZipFile(archive) as packed:
            members = [item for item in packed.infolist() if item.filename == member]
            if (
                len(members) != 1
                or members[0].is_dir()
                or ((members[0].external_attr >> 16) & 0o170000) == 0o120000
            ):
                raise ValueError("ZIP member must be one regular file")
            with packed.open(members[0]) as src, partial.open("xb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
        if not _cloud_file_matches(partial, spec):
            raise ValueError("cloud input size/SHA-256 mismatch: " + str(path))
        try:
            os.link(partial, path)
        except FileExistsError:
            if not _cloud_file_matches(path, spec):
                raise ValueError("concurrent cloud input changed") from None
    finally:
        partial.unlink(missing_ok=True)


class R2InputCache:
    """Share verified local R2 files between the steps of one build attempt."""

    def __init__(
        self,
        directory: Path,
        output: Path,
        endpoint: str | None,
    ) -> None:
        """Set the cache location, run boundary, and R2 account.

        Args:
            directory: Shared input cache directory.
            output: Output directory that must stay separate from cached inputs.
            endpoint: Default R2 account URL for source files.
        """
        self.directory = directory.resolve()
        self.out = output
        self.endpoint = endpoint
        self.pins: list[dict[str, str]] = []
        self.download_intervals: list[tuple[float, float]] = []
        # Repeated references to the same verified bytes skip another file read.
        self.verified_paths: dict[tuple[Path, str, int], Path] = {}

    def path(self, spec: dict[str, Any]) -> Path:
        """Find the cache path for a pinned object or ZIP member.

        Args:
            spec: R2 object or ZIP member with its size and SHA-256.

        Returns:
            Absolute cache path. The file may still need to be acquired.

        Raises:
            ValueError: The reference is invalid or the path escapes the cache.
        """
        expected = spec.get("sha256")
        size = spec.get("size_bytes")
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or any(c not in "0123456789abcdef" for c in expected)
            or type(size) is not int
            or size < 0
        ):
            raise ValueError("cloud inputs require explicit SHA-256 and byte size")
        if "archive" in spec:
            self.path(spec["archive"])
            member = spec["member"]
            if not isinstance(member, str):
                raise ValueError("unsafe ZIP member")
            rel = Path(member)
            if (
                not member
                or rel.is_absolute()
                or "\\" in member
                or any(part in ("", ".", "..") for part in member.split("/"))
            ):
                raise ValueError("unsafe ZIP member")
            path = self.directory / spec["archive"]["sha256"] / rel
        else:
            bucket, key = spec.get("r2_bucket"), spec.get("r2_key")
            if (
                not isinstance(bucket, str)
                or not bucket
                or not isinstance(key, str)
                or not key
                or "\\" in key
                or any(p in ("", ".", "..") for p in key.split("/"))
            ):
                raise ValueError("invalid pinned R2 location")
            path = self.directory / expected / Path(key).name
        path = path.resolve()
        if not path.is_relative_to(self.directory) or path.is_relative_to(self.out):
            raise ValueError("cloud input overlaps output or escapes work directory")
        return path

    def acquire_r2_input(
        self, spec: dict[str, Any], *, endpoint: str | None = None
    ) -> Path:
        """Get a verified local copy of an R2 object or ZIP member.

        Args:
            spec: Object location or archive and member, plus byte size and SHA-256.
            endpoint: R2 account URL. Defaults to the physical-source endpoint.

        Returns:
            Local path to the verified bytes in the work directory.

        Raises:
            ValueError: The reference is invalid or the bytes fail verification.
        """
        path = self.path(spec)
        expected = spec["sha256"]
        identity = (path, expected, spec["size_bytes"])
        if identity in self.verified_paths:
            return self.verified_paths[identity]
        if path.exists():
            if not _cloud_file_matches(path, spec):
                raise ValueError(
                    "cached cloud input size/SHA-256 mismatch: " + str(path)
                )
        elif "archive" in spec:
            archive = self.acquire_r2_input(spec["archive"], endpoint=endpoint)
            _extract_cloud_member(archive, spec["member"], path, spec)
        else:
            self._download_r2_object(spec, path, endpoint)
            path = path.resolve(strict=True)

        self.pins.append({"path": str(path), "sha256": expected})
        self.verified_paths[identity] = path
        return path

    def _download_r2_object(
        self, spec: dict[str, Any], path: Path, endpoint: str | None
    ) -> None:
        """Download a verified R2 object and record its transfer time.

        Args:
            spec: Object location, SHA-256, and byte size.
            path: Local cache destination.
            endpoint: R2 account URL, or None to use the physical-source setting.

        Raises:
            ValueError: The download failed verification.
        """
        if endpoint is None:
            endpoint = self.endpoint
        transfer = {}
        try:
            with closing(r2.make_r2_client(endpoint)) as client:
                download_source(
                    client,
                    spec,
                    self.directory,
                    filename=path.name,
                    timing=transfer,
                )
        except ValueError as exc:
            raise ValueError("cloud input size/SHA-256 mismatch: " + str(path)) from exc
        finally:
            self.download_intervals.extend(transfer.get("download_intervals", []))
