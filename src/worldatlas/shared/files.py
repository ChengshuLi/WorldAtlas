"""Read, verify, and publish local files."""

import hashlib
import json
import os
import uuid
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

# JSON arrays are accepted as lists or tuples when writing.
type JSONValue = (
    Mapping[str, Any] | list[Any] | tuple[Any, ...] | str | int | float | bool | None
)


def read_json(path: Path | str) -> Any:
    """Read a JSON value from a local file.

    Args:
        path: File to read.

    Returns:
        The decoded value. Objects become dicts, arrays become lists, and
        scalar values become str, int, float, bool or None.

    Raises:
        OSError: The file cannot be read.
        ValueError: The file does not contain valid JSON.
    """
    return json.loads(Path(path).read_bytes())


def sha256_file(path: Path | str) -> str:
    """Hash a file without loading it all into memory.

    Args:
        path: File to hash.

    Returns:
        A 64-character lowercase hexadecimal SHA-256 digest.

    Raises:
        OSError: The file cannot be read.
    """
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pin_file(path: Path | str) -> dict[str, str]:
    """Record a file's current location and contents.

    Args:
        path: File to resolve and hash.

    Returns:
        A dictionary with the absolute "path" and its "sha256" digest.

    Raises:
        OSError: The path cannot be resolved or read.
        ValueError: The resolved path is not a regular file.
    """
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    return {"path": str(path), "sha256": sha256_file(path)}


def verify_pins(pins: Iterable[Mapping[str, str]]) -> None:
    """Check that every file still matches its recorded digest.

    Args:
        pins: Records with "path" and expected "sha256" values.

    Raises:
        OSError: A pinned file cannot be read.
        ValueError: A file is not regular or its digest differs.
    """
    for expected in pins:
        if pin_file(expected["path"])["sha256"] != expected["sha256"]:
            raise ValueError("checkpoint/input hash mismatch: " + expected["path"])


def json_bytes(value: JSONValue, *, sort_keys: bool = True) -> bytes:
    """Encode JSON with two-space indentation and a final newline.

    Args:
        value: JSON-compatible value to encode.
        sort_keys: Whether to sort object keys or preserve their insertion
            order.

    Returns:
        The UTF-8 encoded JSON.

    Raises:
        TypeError: A value cannot be represented as JSON.
        ValueError: A number is nonfinite or a container refers to itself.
    """
    text = json.dumps(value, sort_keys=sort_keys, indent=2, allow_nan=False)
    return (text + "\n").encode("utf-8")


def compact_json_bytes(value: JSONValue) -> bytes:
    """Encode a JSON value as compact, sorted UTF-8 for hashing.

    Args:
        value: JSON-compatible value to encode.

    Returns:
        Compact JSON with sorted keys, literal Unicode, and a trailing newline.

    Raises:
        TypeError: A value cannot be represented as JSON.
        ValueError: A number is nonfinite or a container refers to itself.
    """
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return (text + "\n").encode("utf-8")


def sync_directory(path: Path | str) -> None:
    """Flush directory entry changes to disk.

    Args:
        path: Directory containing the changed entries.

    Raises:
        OSError: The directory cannot be opened or flushed.
    """
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_bytes_atomic(path: Path | str, data: bytes) -> Path:
    """Write bytes to a new file and publish it after the write completes.

    Args:
        path: Destination file path. Its directory must already exist.
        data: Contents to write.

    Returns:
        The destination path.

    Raises:
        OSError: The write fails or the destination already exists.
    """
    path = Path(path)
    pending = path.with_name(f".{path.name}.{uuid.uuid4().hex}.pending")
    with pending.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(pending, path)
    except FileExistsError:
        # The result already exists. Keep it and discard this competing copy.
        pending.unlink()
        raise
    sync_directory(path.parent)
    pending.unlink()
    sync_directory(path.parent)
    return path


def write_json(path: Path | str, value: JSONValue, *, sort_keys: bool = True) -> Path:
    """Encode JSON and write it to a new file atomically.

    Args:
        path: Destination file path.
        value: JSON-compatible value to write.
        sort_keys: Whether to sort object keys or preserve their insertion
            order.

    Returns:
        The destination path.

    Raises:
        OSError: The write fails or the destination already exists.
        TypeError: A value cannot be represented as JSON.
        ValueError: A number is nonfinite or a container refers to itself.
    """
    return write_bytes_atomic(path, json_bytes(value, sort_keys=sort_keys))
