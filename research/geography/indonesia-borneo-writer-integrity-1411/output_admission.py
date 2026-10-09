"""Exclusive, no-follow output admission for the #1557 corrective writers."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath


MAX_FILE_BYTES = 32 * 1024 * 1024
RUN_PATTERN = re.compile(r"^run-[a-z0-9][a-z0-9-]{0,47}$")
NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
DIRECTORY = getattr(os, "O_DIRECTORY", 0)
CLOEXEC = getattr(os, "O_CLOEXEC", 0)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _open_dir_chain(directory: Path) -> int:
    """Open an absolute directory component-by-component, refusing symlinks."""
    absolute = Path(os.path.abspath(directory))
    if not absolute.is_absolute():
        raise ValueError("Directory path must be absolute")
    fd = os.open("/", os.O_RDONLY | DIRECTORY | CLOEXEC)
    try:
        for part in absolute.parts[1:]:
            if part in ("", ".", ".."):
                raise ValueError("Unsafe directory path component")
            next_fd = os.open(part, os.O_RDONLY | DIRECTORY | NOFOLLOW | CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except Exception:
        os.close(fd)
        raise


def _relative_parts(relative: str) -> tuple[str, ...]:
    if not isinstance(relative, str) or not relative or "\x00" in relative:
        raise ValueError("Expected a non-empty repository-relative path")
    path = PurePosixPath(relative)
    parts = path.parts
    if path.is_absolute() or any(part in ("", ".", "..") for part in parts):
        raise ValueError("Unsafe repository-relative path")
    return parts


def read_regular(root: Path, relative: str, limit: int = MAX_FILE_BYTES) -> bytes:
    """Read one regular file through no-follow directory descriptors."""
    parts = _relative_parts(relative)
    fd = _open_dir_chain(Path(root))
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | DIRECTORY | NOFOLLOW | CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = child
        file_fd = os.open(parts[-1], os.O_RDONLY | NOFOLLOW | CLOEXEC, dir_fd=fd)
        try:
            info = os.fstat(file_fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise ValueError(f"Input is not a bounded regular file: {relative}")
            chunks = []
            total = 0
            while True:
                chunk = os.read(file_fd, min(1024 * 1024, limit + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise ValueError(f"Input exceeds byte limit: {relative}")
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            os.close(file_fd)
    finally:
        os.close(fd)


def read_external_regular(filename: str, limit: int = MAX_FILE_BYTES) -> bytes:
    """Read caller-supplied local input without following any symlink component."""
    path = Path(os.path.abspath(filename))
    if not path.is_absolute() or any(part in ("", ".", "..") for part in path.parts[1:]):
        raise ValueError("Unsafe local input path")
    parent_fd = _open_dir_chain(path.parent)
    try:
        file_fd = os.open(path.name, os.O_RDONLY | NOFOLLOW | CLOEXEC, dir_fd=parent_fd)
        try:
            info = os.fstat(file_fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
                raise ValueError("Local input must be a bounded regular file")
            chunks = []
            total = 0
            while True:
                chunk = os.read(file_fd, min(1024 * 1024, limit + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise ValueError("Local input exceeds byte limit")
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            os.close(file_fd)
    finally:
        os.close(parent_fd)


class Reservation:
    def __init__(self, packet_root: Path, run_id: str, product_names: tuple[str, ...],
                 packet_fd: int, runs_fd: int, run_fd: int):
        self.packet_root = Path(packet_root)
        self.run_id = run_id
        self.product_names = product_names
        self.packet_fd = packet_fd
        self.runs_fd = runs_fd
        self.run_fd = run_fd
        self.closed = False

    @property
    def relative_dir(self) -> str:
        return f"{self.packet_root.name}/runs/{self.run_id}"

    def publish(self, products: dict[str, bytes], completion: dict) -> dict:
        expected_products = set(self.product_names) - {"completion.json"}
        if set(products) != expected_products:
            raise ValueError("Publication does not match the complete admitted output set")
        if any(not isinstance(name, str) or not isinstance(raw, bytes) for name, raw in products.items()):
            raise ValueError("Products must map names to complete byte strings")
        inventory = []
        for name in self.product_names:
            if name == "completion.json":
                continue
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | NOFOLLOW | CLOEXEC,
                         0o644, dir_fd=self.run_fd)
            try:
                raw = products[name]
                view = memoryview(raw)
                while view:
                    written = os.write(fd, view)
                    if written <= 0:
                        raise OSError("Short write while publishing an exclusive product")
                    view = view[written:]
                os.fsync(fd)
                inventory.append({"path": name, "bytes": len(raw), "sha256": sha256(raw),
                                  "hash_kind": "file-bytes"})
            finally:
                os.close(fd)
        receipt = dict(completion)
        receipt["outputs"] = inventory
        receipt_raw = (json.dumps(receipt, sort_keys=True, ensure_ascii=False,
                                  separators=(",", ":")) + "\n").encode("utf-8")
        fd = os.open("completion.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | NOFOLLOW | CLOEXEC,
                     0o644, dir_fd=self.run_fd)
        try:
            view = memoryview(receipt_raw)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise OSError("Short write while publishing completion receipt")
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self.run_fd)
        return {"completion_bytes": len(receipt_raw), "completion_sha256": sha256(receipt_raw),
                "output_count": len(inventory)}

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        for fd in (self.run_fd, self.runs_fd, self.packet_fd):
            try:
                os.close(fd)
            except OSError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def reserve_output_set(packet_root: Path, run_id: str, product_names: tuple[str, ...]) -> Reservation:
    """Admit an owned, unique run directory before any inputs or computations are read."""
    if not isinstance(run_id, str) or not RUN_PATTERN.fullmatch(run_id):
        raise ValueError("run id must match run-<lowercase letters, digits, hyphens>")
    if (not product_names or len(set(product_names)) != len(product_names) or
            "completion.json" not in product_names or
            any(name in ("", ".", "..", "completion.json") or "/" in name or "\\" in name
                for name in product_names if name != "completion.json")):
        raise ValueError("Invalid fixed output inventory")
    root = Path(os.path.abspath(packet_root))
    packet_fd = _open_dir_chain(root)
    runs_fd = None
    run_fd = None
    try:
        try:
            runs_fd = os.open("runs", os.O_RDONLY | DIRECTORY | NOFOLLOW | CLOEXEC, dir_fd=packet_fd)
        except FileNotFoundError:
            os.mkdir("runs", 0o755, dir_fd=packet_fd)
            runs_fd = os.open("runs", os.O_RDONLY | DIRECTORY | NOFOLLOW | CLOEXEC, dir_fd=packet_fd)
        try:
            os.stat(run_id, dir_fd=runs_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError(f"Refusing occupied run path, including symlinks: runs/{run_id}")
        os.mkdir(run_id, 0o755, dir_fd=runs_fd)
        run_fd = os.open(run_id, os.O_RDONLY | DIRECTORY | NOFOLLOW | CLOEXEC, dir_fd=runs_fd)
        for name in product_names:
            if name == "completion.json":
                continue
            try:
                os.stat(name, dir_fd=run_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise FileExistsError(f"Refusing occupied output leaf, including symlinks: {name}")
        return Reservation(root, run_id, product_names, packet_fd, runs_fd, run_fd)
    except Exception:
        for fd in (run_fd, runs_fd, packet_fd):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        raise


def verify_receipt(run_directory: Path) -> dict:
    """Verify a completed candidate output against its last-written receipt."""
    receipt_path = Path(run_directory) / "completion.json"
    raw = read_external_regular(str(receipt_path), limit=1024 * 1024)
    receipt = json.loads(raw)
    if receipt.get("status") != "complete" or not isinstance(receipt.get("outputs"), list):
        raise ValueError("Missing or unsuccessful completion receipt")
    seen = set()
    for descriptor in receipt["outputs"]:
        name = descriptor.get("path")
        if not isinstance(name, str) or "/" in name or name in seen or name == "completion.json":
            raise ValueError("Invalid receipt output path")
        seen.add(name)
        body = read_external_regular(str(Path(run_directory) / name), limit=MAX_FILE_BYTES)
        if len(body) != descriptor.get("bytes") or sha256(body) != descriptor.get("sha256"):
            raise ValueError(f"Changed comparison product: {name}")
    return receipt
