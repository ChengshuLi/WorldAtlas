"""Persist and verify the append-only files used to resume a map build."""

import hashlib
import json
import os
from collections.abc import Iterable, Mapping
from pathlib import Path

from worldatlas.shared.files import JSONValue, sync_directory, write_bytes_atomic


def prefix_digest(path: Path, size: int, shortened_message: str) -> str:
    """Hash exactly the first size bytes, even if the journal has grown.

    Args:
        path: Journal to read.
        size: Length of the recorded prefix in bytes.
        shortened_message: Error to raise if those bytes are missing.

    Returns:
        Lowercase hexadecimal SHA-256 of the prefix.
    """
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while size:
            block = stream.read(min(1 << 20, size))
            if not block:
                raise ValueError(shortened_message)
            digest.update(block)
            size -= len(block)
    return digest.hexdigest()


def create_journal(path: Path) -> None:
    """Create an empty journal and flush its entry to disk.

    Args:
        path: New journal path in an existing directory.
    """
    with path.open("xb") as stream:
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def append_records(path: Path, records: Iterable[Mapping[str, JSONValue]]) -> None:
    """Append complete JSON lines and flush them before reporting success.

    Args:
        path: Existing journal.
        records: JSON objects in the order to append.
    """
    with path.open("a", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def preserve_torn_tail(path: Path, valid_bytes: int, backup: Path, data: bytes) -> None:
    """Save interrupted journal bytes before discarding the incomplete tail.

    Args:
        path: Journal to shorten.
        valid_bytes: Ending byte offset of the complete records.
        backup: New local file for debugging.
        data: Bytes the caller needs to preserve in the backup.
    """
    write_bytes_atomic(backup, data)
    with path.open("r+b") as stream:
        stream.truncate(valid_bytes)
        stream.flush()
        os.fsync(stream.fileno())
