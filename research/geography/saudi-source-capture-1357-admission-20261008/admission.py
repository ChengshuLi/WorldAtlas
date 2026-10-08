"""Admission and exclusive publication helpers for the bounded Saudi successor.

The predecessor packet remains immutable. This module reads its small frozen
manifest, accounts for the complete raw/decoded body closure, and refuses the
known oversized replay before opening any body or invoking its producer.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

PER_FILE_BYTES = 32 * 1024 * 1024
PHASE_BYTES = 256 * 1024 * 1024
RECEIPT_BYTES = 4096
LOCK_SHA256 = "ba3ae27b291f850ded10652cc4dc13f90d7df79353833c54999d9dd0a0d12b9d"
MINIMUM_SOURCE_BYTES = 682_797_443


class AdmissionError(ValueError):
    pass


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AdmissionError(f"{label} must be a nonnegative integer")
    return value


def _hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise AdmissionError(f"{label} must be a lowercase SHA-256")
    return value


def safe_relative(value: Any) -> str:
    if (not isinstance(value, str) or not value or value.startswith("/") or
            "\\" in value or "\0" in value or
            any(part in ("", ".", "..") for part in value.split("/"))):
        raise AdmissionError("Destination/input path is not a safe relative path")
    return value


def read_regular(path: Path, limit: int = PER_FILE_BYTES) -> bytes:
    """Read one ordinary file without following a leaf symlink or exceeding its cap."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        raise AdmissionError(f"Required file is missing: {path}") from None
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise AdmissionError(f"Expected a bounded ordinary file: {path}")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit or len(raw) != info.st_size:
        raise AdmissionError(f"File changed or exceeds its byte cap: {path}")
    return raw


def _add_identity(identities: dict[str, int], digest: Any, size: Any, label: str,
                  per_file_bytes: int) -> None:
    digest = _hash(digest, f"{label} hash")
    size = _integer(size, f"{label} size")
    if size > per_file_bytes:
        raise AdmissionError(f"{label} exceeds the per-file byte cap")
    previous = identities.get(digest)
    if previous is not None and previous != size:
        raise AdmissionError(f"One content identity declares conflicting sizes: {label}")
    identities[digest] = size


def plan_from_lock(lock: dict[str, Any], *, lock_sha256: str,
                   lock_bytes: int, output_reserve_bytes: int,
                   runtime_reserve_bytes: int, receipt_reserve_bytes: int = RECEIPT_BYTES,
                   supplemental_files: list[dict[str, Any]] | None = None,
                   per_file_bytes: int = PER_FILE_BYTES,
                   phase_bytes: int = PHASE_BYTES,
                   required_source_bytes: int | None = MINIMUM_SOURCE_BYTES) -> dict[str, Any]:
    """Compute a non-vacuous complete phase plan from frozen descriptors only.

    Same-SHA encoded/decoded bodies are counted once. Different content hashes
    are counted even when their byte lengths match. No source bodies are read.
    """
    if not isinstance(lock, dict) or lock.get("version") != 1:
        raise AdmissionError("Unsupported frozen execution manifest")
    if lock.get("limits") != {
        "per_encoded_or_decoded_input_bytes": per_file_bytes,
        "maximum_total_declared_bytes": phase_bytes,
    }:
        raise AdmissionError("Frozen manifest changes the accepted byte caps")

    sources = lock.get("source_blobs")
    if not isinstance(sources, list) or not sources:
        raise AdmissionError("Complete source inventory is missing")
    if lock.get("source_blob_count") != len(sources):
        raise AdmissionError("Frozen source inventory count does not reconcile")
    raw_total = 0
    seen_paths: set[tuple[str, str]] = set()
    identities: dict[str, int] = {}
    for row in sources:
        if not isinstance(row, dict):
            raise AdmissionError("Malformed frozen source row")
        commit, path = row.get("commit"), safe_relative(row.get("path"))
        if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
            raise AdmissionError("Source commit is not immutable")
        if (commit, path) in seen_paths:
            raise AdmissionError("Duplicate source path binding")
        seen_paths.add((commit, path))
        if row.get("mode") not in ("100644", "100755"):
            raise AdmissionError("Source body is not an ordinary Git file")
        if not isinstance(row.get("oid"), str) or re.fullmatch(r"[0-9a-f]{40}", row["oid"]) is None:
            raise AdmissionError("Source Git blob identity is missing")
        size = _integer(row.get("bytes"), "encoded source size")
        raw_total += size
        _add_identity(identities, row.get("sha256"), size, f"encoded source {path}", per_file_bytes)
        decoded_fields = {"uncompressed_bytes", "uncompressed_sha256"} & row.keys()
        if decoded_fields:
            if decoded_fields != {"uncompressed_bytes", "uncompressed_sha256"}:
                raise AdmissionError("Decoded source identity is incomplete")
            _add_identity(identities, row["uncompressed_sha256"], row["uncompressed_bytes"],
                          f"decoded source {path}", per_file_bytes)
    if raw_total != lock.get("source_blob_encoded_bytes"):
        raise AdmissionError("Encoded source byte total does not reconcile")

    code = lock.get("code")
    local_inputs = lock.get("local_inputs")
    if not isinstance(code, list) or not isinstance(local_inputs, list):
        raise AdmissionError("Frozen code or local input inventory is missing")
    code_paths = {safe_relative(row.get("path")) for row in code if isinstance(row, dict)}
    if code_paths != {"source_extract.py", "run_final.py", "compat/inputs.py", "compat/immutable.py"}:
        raise AdmissionError("Frozen executable inventory is incomplete")
    input_paths = {safe_relative(row.get("path")) for row in local_inputs if isinstance(row, dict)}
    if input_paths != {"issue-1336-api.json", "inputs/legacy-input-config.json"}:
        raise AdmissionError("Frozen local input inventory is incomplete")
    for label, rows in (("code", code), ("local input", local_inputs)):
        if any(not isinstance(row, dict) for row in rows):
            raise AdmissionError(f"Malformed frozen {label} row")
        for row in rows:
            _add_identity(identities, row.get("sha256"), row.get("bytes"),
                          f"{label} {row['path']}", per_file_bytes)

    lock_sha256 = _hash(lock_sha256, "frozen manifest hash")
    lock_bytes = _integer(lock_bytes, "frozen manifest size")
    _add_identity(identities, lock_sha256, lock_bytes, "frozen manifest", per_file_bytes)
    for row in supplemental_files or []:
        if not isinstance(row, dict):
            raise AdmissionError("Malformed supplemental input descriptor")
        safe_relative(row.get("path"))
        _add_identity(identities, row.get("sha256"), row.get("bytes"),
                      f"supplemental input {row['path']}", per_file_bytes)
    body_identities = {
        _hash(row["sha256"], "encoded source hash") for row in sources
    } | {
        _hash(row["uncompressed_sha256"], "decoded source hash")
        for row in sources if "uncompressed_sha256" in row
    }
    source_bytes = sum(identities[digest] for digest in body_identities)
    if required_source_bytes is not None and source_bytes != required_source_bytes:
        raise AdmissionError("Frozen source body minimum differs from issue 1511's accepted finding")

    output_reserve_bytes = _integer(output_reserve_bytes, "output reserve")
    runtime_reserve_bytes = _integer(runtime_reserve_bytes, "runtime reserve")
    receipt_reserve_bytes = _integer(receipt_reserve_bytes, "receipt reserve")
    if receipt_reserve_bytes > RECEIPT_BYTES:
        raise AdmissionError("Completion receipt reserve exceeds the shared 4 KiB limit")
    if output_reserve_bytes > per_file_bytes * 14:
        raise AdmissionError("Output reserve exceeds fourteen bounded product files")
    total = sum(identities.values()) + output_reserve_bytes + runtime_reserve_bytes + receipt_reserve_bytes
    return {
        "source_body_minimum_bytes": source_bytes,
        "raw_source_descriptors": len(sources),
        "unique_source_body_identities": len(body_identities),
        "encoded_descriptor_sum_bytes": raw_total,
        "unique_phase_input_bytes": sum(identities.values()),
        "supplemental_input_count": len(supplemental_files or []),
        "runtime_reserve_bytes": runtime_reserve_bytes,
        "output_reserve_bytes": output_reserve_bytes,
        "receipt_reserve_bytes": receipt_reserve_bytes,
        "complete_phase_bytes": total,
        "phase_limit_bytes": phase_bytes,
        "admitted": total <= phase_bytes,
    }


def bounded_gzip(raw: bytes, *, declared_bytes: int, declared_sha256: str,
                 per_file_bytes: int = PER_FILE_BYTES) -> bytes:
    if len(raw) > per_file_bytes:
        raise AdmissionError("Encoded gzip body exceeds the per-file cap")
    if declared_bytes > per_file_bytes:
        raise AdmissionError("Declared decoded gzip body exceeds the per-file cap")
    if len(raw) < 18 or raw[:2] != b"\x1f\x8b":
        raise AdmissionError("Invalid gzip body")
    decoder = gzip.GzipFile(fileobj=__import__("io").BytesIO(raw))
    decoded = decoder.read(per_file_bytes + 1)
    if len(decoded) > per_file_bytes or decoder.read(1):
        raise AdmissionError("Actual decoded gzip body exceeds the per-file cap")
    if len(decoded) != declared_bytes or sha256(decoded) != _hash(declared_sha256, "decoded gzip hash"):
        raise AdmissionError("Decoded gzip body differs from its frozen identity")
    return decoded


def admit_destinations(root: Path, relative_paths: list[str], *,
                       directory_paths: list[str] | None = None) -> list[str]:
    """Reject collisions, traversal, and any existing symlink ancestor/leaf."""
    root = root.resolve(strict=True)
    normalized = [safe_relative(path) for path in relative_paths]
    directories = [safe_relative(path) for path in (directory_paths or [])]
    if len(normalized) != len(set(normalized)):
        raise AdmissionError("Destination set contains duplicate paths")
    if len(directories) != len(set(directories)) or set(normalized) & set(directories):
        raise AdmissionError("Destination set contains duplicate file/directory paths")
    for i, left in enumerate(normalized):
        for right in normalized[i + 1:]:
            if left.startswith(right + "/") or right.startswith(left + "/"):
                raise AdmissionError("Destination set contains an ancestor collision")
    for directory in directories:
        if any(directory == file_path or directory.startswith(file_path + "/")
               for file_path in normalized):
            raise AdmissionError("A file destination contains a directory destination")
    for value in normalized + directories:
        current = root
        for segment in value.split("/"):
            current = current / segment
            try:
                info = current.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(info.st_mode):
                raise AdmissionError(f"Symlink in destination path: {value}")
            if current != root / value and not stat.S_ISDIR(info.st_mode):
                raise AdmissionError(f"Non-directory destination ancestor: {value}")
            if current == root / value:
                raise FileExistsError(f"Destination already exists: {value}")
    return normalized


def _open_dir(root: Path, segments: list[str], *, create: bool) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(root, flags)
    try:
        for segment in segments:
            try:
                next_fd = os.open(segment, flags, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(segment, 0o755, dir_fd=fd)
                next_fd = os.open(segment, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def write_exclusive(root: Path, relative_path: str, raw: bytes) -> None:
    """Create parents without following symlinks; create and fsync one new file."""
    relative_path = safe_relative(relative_path)
    if len(raw) > PER_FILE_BYTES:
        raise AdmissionError("Output exceeds the per-file byte cap")
    parts = relative_path.split("/")
    root = root.resolve(strict=True)
    parent_fd = _open_dir(root, parts[:-1], create=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(parts[-1], flags, 0o644, dir_fd=parent_fd)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(parent_fd)


def write_exclusive_json(root: Path, relative_path: str, value: dict[str, Any]) -> None:
    raw = (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    write_exclusive(root, relative_path, raw)
