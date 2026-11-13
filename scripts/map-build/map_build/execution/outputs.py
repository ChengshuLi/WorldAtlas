"""Small O_EXCL-only output primitives for immutable scientific-workflow artifacts.

Callers must provide a fresh run directory and a new filename for every attempt.
This module intentionally offers no append, truncate, replace, rename, delete,
cleanup, or in-place manifest-update API. A failed write leaves its created path
in place; a retry uses a new run directory and new names.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import gzip
import io
import json
import os
from pathlib import Path
import re
import uuid
from typing import Any, Iterator, TextIO, BinaryIO


def _flags() -> int:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    return flags


def _new_fd(path: os.PathLike[str] | str, mode: int = 0o666) -> int:
    """Create one new regular output path; collisions and symlinks fail closed."""
    p = os.fspath(path)
    return os.open(p, _flags(), mode)


@contextmanager
def create_binary_exclusive(
    path: os.PathLike[str] | str, *, mode: int = 0o666
) -> Iterator[BinaryIO]:
    """Create a binary output exactly once with O_CREAT|O_EXCL; never truncate."""
    fd = _new_fd(path, mode)
    with os.fdopen(fd, "wb") as stream:
        yield stream
        stream.flush()


@contextmanager
def create_text_exclusive(
    path: os.PathLike[str] | str,
    *,
    encoding: str = "utf-8",
    newline: str | None = None,
    mode: int = 0o666,
) -> Iterator[TextIO]:
    """Create a text output exactly once with O_CREAT|O_EXCL; never truncate."""
    fd = _new_fd(path, mode)
    with os.fdopen(fd, "w", encoding=encoding, newline=newline) as stream:
        yield stream
        stream.flush()


@contextmanager
def create_gzip_exclusive(
    path: os.PathLike[str] | str,
    *,
    compresslevel: int = 6,
    mtime: int = 0,
    mode: int = 0o666,
) -> Iterator[gzip.GzipFile]:
    """Stream gzip bytes to a single O_EXCL-created file descriptor."""
    with create_binary_exclusive(path, mode=mode) as raw:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, compresslevel=compresslevel, mtime=mtime
        ) as gz:
            yield gz


@contextmanager
def create_gzip_text_exclusive(
    path: os.PathLike[str] | str,
    *,
    encoding: str = "utf-8",
    newline: str | None = "\n",
    compresslevel: int = 6,
    mtime: int = 0,
    mode: int = 0o666,
) -> Iterator[TextIO]:
    """Stream UTF-8 text through gzip, with the underlying path O_EXCL-created."""
    with create_gzip_exclusive(path, compresslevel=compresslevel, mtime=mtime, mode=mode) as gz:
        text = io.TextIOWrapper(gz, encoding=encoding, newline=newline)
        try:
            yield text
        finally:
            # Detach so the outer gzip context closes the compressor exactly once.
            try:
                text.flush()
            finally:
                text.detach()


def validate_fresh_output(
    input_root: os.PathLike[str] | str,
    output: os.PathLike[str] | str,
    inputs: tuple[os.PathLike[str] | str, ...] = (),
) -> Path:
    """Allow a fresh sibling or in-root output, never an existing input or symlink path.

    Callers must validate all input files before exclusively creating this path.
    No concurrent adversarial filesystem mutation is assumed by this path check.
    """
    root = Path(input_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('input root must be a directory')
    lexical = Path(os.path.abspath(os.fspath(output)))
    canonical = lexical.resolve(strict=False)
    if lexical != canonical:
        raise ValueError('output path traverses a symlink')
    if not canonical.parent.is_dir():
        raise ValueError('output parent must exist')
    if os.path.lexists(canonical):
        raise FileExistsError('output path must be new')
    if root == canonical or root.is_relative_to(canonical):
        raise ValueError('output cannot be the input root or its ancestor')
    for item in inputs:
        source = Path(item).resolve(strict=True)
        if source == canonical or source.is_relative_to(canonical):
            raise ValueError('output contains an input')
    return canonical


def create_directory_exclusive(path: os.PathLike[str] | str, *, mode: int = 0o777) -> Path:
    """Create exactly one directory; existing files/directories are errors."""
    p = Path(path)
    p.mkdir(mode=mode, parents=False, exist_ok=False)
    return p


def create_run_directory(parent: os.PathLike[str] | str, prefix: str = "run") -> Path:
    """Create a unique immutable run directory below an existing parent.

    A name collision raises FileExistsError. Callers start a fresh attempt rather
    than reusing, clearing, or replacing any previous run directory.
    """
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", prefix):
        raise ValueError("run prefix must be a simple filename component")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    path = Path(parent) / f"{prefix}-{stamp}-{uuid.uuid4().hex[:12]}"
    return create_directory_exclusive(path)


def write_json_exclusive(
    path: os.PathLike[str] | str,
    value: Any,
    *,
    indent: int | None = 2,
    ensure_ascii: bool = False,
) -> None:
    """Write one immutable JSON snapshot; later checkpoints need new filenames."""
    with create_text_exclusive(path, encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=indent, ensure_ascii=ensure_ascii)
        stream.write("\n")
