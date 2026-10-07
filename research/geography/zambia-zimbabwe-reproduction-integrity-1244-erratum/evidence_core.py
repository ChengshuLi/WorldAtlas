"""Bounded, immutable and exclusive evidence primitives for issue #1385."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import subprocess
import types
import sys

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/zambia-zimbabwe-reproduction-integrity-1244-erratum/"
BASE = "79ffb2ed04702e16f009e4675a8d74ef9bd09d4f"
HELPER_COMMIT = "d51c43e878c797d215ba5bd8285571fa14add443"
HELPER_PATH = "scripts/evidence/immutable.py"
HELPER_SHA = "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46"
CONTRACT = ROOT / OWNED / "integrity-contract.json"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
MAX_FILE = 32 * 1024 * 1024
MAX_PHASE = 256 * 1024 * 1024


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()


def deterministic_gzip(raw: bytes) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0, compresslevel=9) as stream:
        stream.write(raw)
    return output.getvalue()


def verify_code() -> dict:
    """Check all actually consumed project entrypoints against the reviewed lock."""
    lock = json.loads(CONTRACT.read_bytes())
    if lock.get("version") != 1 or lock.get("baseline_commit") != BASE:
        raise ValueError("Unknown immutable integrity contract")
    expected = lock.get("code")
    if not isinstance(expected, dict) or set(expected) != {"evidence_core.py", "reproduce.py", "record_controls.py", "safe_vintage.py"}:
        raise ValueError("Incomplete executed-code inventory")
    observed = {}
    for name, digest in expected.items():
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("Invalid executed-code pin")
        raw = (HERE / name).read_bytes()
        if sha(raw) != digest:
            raise ValueError("Actually executed candidate code differs from reviewed lock: " + name)
        observed[name] = {"path": OWNED + name, "bytes": len(raw), "sha256": digest}
    helper_expected = lock.get("project_helper")
    helper_raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{HELPER_COMMIT}:{HELPER_PATH}"])
    if (helper_expected != {"commit": HELPER_COMMIT, "path": HELPER_PATH, "bytes": len(helper_raw), "sha256": HELPER_SHA}
            or sha(helper_raw) != HELPER_SHA):
        raise ValueError("Pinned project preparation helper differs from its reviewed whole-file lock")
    return {"lock_path": OWNED + "integrity-contract.json", "lock_sha256": sha(CONTRACT.read_bytes()), "executed": observed,
            "project_helper": helper_expected}


def source_lock() -> dict:
    path = HERE / "source-lock.json"
    body = (HERE / "issue-contract-source.txt").read_bytes()
    lock = json.loads(path.read_bytes())
    if sha(body) != lock.get("issue_contract_sha256"):
        raise ValueError("Captured issue contract bytes changed")
    if lock.get("version") != 1 or lock.get("issue") != 1385 or lock.get("baseline_commit") != BASE:
        raise ValueError("Wrong issue/source contract")
    if len(lock.get("pins", [])) != 53 or len({x["id"] for x in lock["pins"]}) != 53:
        raise ValueError("Incomplete whole-source issue pin inventory")
    if len(lock.get("subject_ids", [])) != 4 or len(set(lock["subject_ids"])) != 4:
        raise ValueError("Wrong exact native subject scope")
    if len(lock.get("component_ids", [])) != 10 or len(set(lock["component_ids"])) != 10:
        raise ValueError("Wrong exact physical component scope")
    source_text = body.decode("utf-8")
    pin_pattern = re.compile(r'- `((?:baseline|original_1244)_\d+)`: `([^`]+)` at `([0-9a-f]{40})`; (\d+) bytes; SHA-256 `([0-9a-f]{64})`\.')
    declared = [{"id": match[1], "path": match[2], "commit": match[3], "bytes": int(match[4]),
                 "sha256": match[5], "hash_kind": "file-bytes"} for match in pin_pattern.finditer(source_text)]
    if declared != lock["pins"]:
        raise ValueError("Whole-file pin lock disagrees with captured original issue body")
    match = re.search(r"<!-- worldatlas-work:v1\n(.*?)\n-->", source_text, re.S)
    if not match:
        raise ValueError("Captured issue contract block is missing")
    contract = json.loads(match.group(1))
    if (contract.get("owned_paths") != [OWNED] or contract.get("mode") != "geography"
            or contract.get("depends_on") != [] or contract.get("evidence_quality", {}).get("subject_ids") != lock["subject_ids"]):
        raise ValueError("Captured issue scope, ownership, mode, dependencies or subjects changed")
    component_section = source_text.split("Exact complete component roster:", 1)[-1].split("\n<!-- worldatlas-work:v1", 1)[0]
    components = re.findall(r"`(physical-component:[a-f0-9]{64})`", component_section)
    if components != lock["component_ids"]:
        raise ValueError("Captured ten-component issue roster changed")
    if {p["id"].split("_")[0] for p in lock["pins"]} != {"baseline", "original"}:
        raise ValueError("Issue pins must include both baseline and original-PR evidence")
    for pin in lock["pins"]:
        expected_commit = BASE if pin["id"].startswith("baseline_") else lock["original_merge_commit"]
        if pin["commit"] != expected_commit:
            raise ValueError("Issue pin commit vintage changed")
    return lock


def verify_source_contract(phase: Phase) -> dict:
    """Hash all 53 declared original files without decompressing any dataset."""
    lock = source_lock()
    observed = []
    budget = 0
    for pin in lock["pins"]:
        raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f'{pin["commit"]}:{pin["path"]}'])
        if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
            raise ValueError("Declared whole-file issue pin mismatch: " + pin["id"])
        budget += len(raw)
        phase.admit("issue-pin:" + pin["id"], raw)
        observed.append({"id": pin["id"], "path": pin["path"], "commit": pin["commit"], "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"})
    if sum(phase.baseline.consumed.values()) > MAX_PHASE:
        raise ValueError("Source contract verification exceeded the semantic byte limit")
    return {"issue_contract_sha256": lock["issue_contract_sha256"], "pins_verified": observed, "raw_bytes_verified": budget,
            "decoded_data_opened": False, "limit": "Verification pass authenticates complete issue pins by raw bytes only; semantic work is independently partitioned below."}


def pin_at(repo: Path, commit: str, path: str, expected_sha: str | None = None, expected_bytes: int | None = None) -> dict:
    if commit != BASE:
        raise ValueError("Unexpected source baseline")
    safe_repo_path(path)
    row = __import__("subprocess").check_output(["git", "-C", str(repo), "ls-tree", "-z", commit, "--", path])
    line = row.decode().rstrip("\0")
    if not line.endswith("\t" + path) or not line.startswith(("100644 ", "100755 ")):
        raise ValueError("Expected one ordinary committed input: " + path)
    blob = line.split()[2]
    size = int(__import__("subprocess").check_output(["git", "-C", str(repo), "cat-file", "-s", blob]))
    if size > MAX_FILE:
        raise ValueError("Input exceeds individual byte bound: " + path)
    raw = __import__("subprocess").check_output(["git", "-C", str(repo), "cat-file", "blob", blob])
    if len(raw) != size or (expected_bytes is not None and size != expected_bytes) or (expected_sha and sha(raw) != expected_sha):
        raise ValueError("Immutable input hash/size mismatch: " + path)
    return {"path": path, "bytes": size, "sha256": sha(raw), "hash_kind": "file-bytes"}


def safe_repo_path(path: str):
    if not isinstance(path, str) or not path or "\\" in path or "\0" in path or any(p in ("", ".", "..") for p in path.split("/")):
        raise ValueError("Unsafe repository path")


class Phase:
    """One semantic pass, with each raw, decoded, code and output byte admitted."""
    def __init__(self, name: str, paths: list[str], *, extra: list[tuple[str, bytes]] = (), pin_map: dict[str, dict] | None = None, overrides: dict[str, bytes] | None = None):
        self.name = name
        self.overrides = overrides or {}
        self.code = verify_code()
        code_paths = ["scripts/evidence/geometry.py", "scripts/ellipsoidal_area.py"]
        all_paths = sorted(set(paths + code_paths))
        pin_map = pin_map or {}
        pins = [pin_at(ROOT, BASE, path, (pin_map.get(path) or {}).get("sha256"), (pin_map.get(path) or {}).get("bytes")) for path in all_paths]
        helper_bytes = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{HELPER_COMMIT}:{HELPER_PATH}"])
        if sha(helper_bytes) != HELPER_SHA:
            raise ValueError("Pinned preparation helper changed during bootstrap")
        self.helper_pin = {"path": HELPER_PATH, "commit": HELPER_COMMIT, "bytes": len(helper_bytes), "sha256": sha(helper_bytes), "hash_kind": "file-bytes"}
        self.helper = types.ModuleType("worldatlas_pinned_immutable")
        self.helper.__file__ = str(ROOT / HELPER_PATH)
        exec(compile(helper_bytes, self.helper.__file__, "exec"), self.helper.__dict__)
        self.baseline = self.helper.Baseline(ROOT, BASE, pins)
        self.baseline.admit("project-code:" + HELPER_PATH, len(helper_bytes))
        self.modules = self.baseline.load_modules({"evidence.geometry": "scripts/evidence/geometry.py", "ellipsoidal_area": "scripts/ellipsoidal_area.py"})
        self.inputs: dict[str, dict] = {}
        for path, raw in extra:
            self.admit(path, raw)

    @property
    def records(self):
        return [self.baseline.pins[path] for path in sorted(self.baseline.pins)] + [self.helper_pin] + [self.inputs[k] for k in sorted(self.inputs)]

    def verify_helper(self):
        raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{HELPER_COMMIT}:{HELPER_PATH}"])
        if len(raw) != self.helper_pin["bytes"] or sha(raw) != self.helper_pin["sha256"]:
            raise ValueError("Actually executed pinned preparation helper changed")

    def raw(self, path: str) -> bytes:
        raw = self.baseline.pinned_bytes(path)
        if path in self.overrides:
            altered = self.overrides[path]
            if len(altered) > MAX_FILE:
                raise ValueError("Altered consumed input exceeds per-file bound")
            if altered != raw:
                raise ValueError("Actually consumed immutable input drift detected before semantic use: " + path)
            raw = altered
        self.inputs[path] = {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}
        return raw

    def admit(self, name: str, raw: bytes):
        if len(raw) > MAX_FILE:
            raise ValueError("Intermediate exceeds per-file byte bound: " + name)
        self.baseline.admit("derived:" + name, len(raw))
        self.inputs["derived:" + name] = {"path": name, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes", "role": "derived-phase-input"}

    def decoded(self, path: str, raw: bytes) -> bytes:
        data = gzip.decompress(raw)
        if len(data) > MAX_FILE:
            raise ValueError("Decoded source exceeds per-file byte bound: " + path)
        self.baseline.admit(path + ":decoded", len(data))
        self.inputs[path + ":decoded"] = {"path": path, "bytes": len(data), "sha256": sha(data), "hash_kind": "file-bytes", "encoding": "gzip-decoded"}
        return data

    def account_output(self, name: str, raw: bytes):
        if len(raw) > MAX_FILE:
            raise ValueError("Output exceeds per-file byte bound: " + name)
        decoded = gzip.decompress(raw) if name.endswith(".gz") else b""
        if len(decoded) > MAX_FILE:
            raise ValueError("Decoded output exceeds per-file byte bound: " + name)
        size = len(raw) + len(decoded)
        self.baseline.admit("output:" + name, size)
        if sum(self.baseline.consumed.values()) > MAX_PHASE:
            raise ValueError("Complete semantic phase exceeds 256 MiB")
        return {"path": name, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}


def finalize_phase_output(phase: Phase, value: dict, name: str):
    """Bind a phase's complete input + actual compressed/decoded result bytes."""
    base = sum(phase.baseline.consumed.values())
    value["phase_accounting"] = {"input_bytes": base, "maximum_file_bytes": MAX_FILE, "maximum_phase_bytes": MAX_PHASE,
                                  "input_limit_respected": base <= MAX_PHASE}
    if base > MAX_PHASE:
        raise ValueError("Semantic phase inputs exceed the 256 MiB limit")
    decoded = canonical(value)
    encoded = deterministic_gzip(decoded) if name.endswith(".gz") else decoded
    phase.account_output(name, encoded)
    if sum(phase.baseline.consumed.values()) > MAX_PHASE:
        raise ValueError("Complete semantic phase including output exceeds the 256 MiB limit")
    return encoded, value


def secure_publish(run_path: str, filenames: list[str], payloads: dict[str, bytes], admission_phase: Phase, *, failure_hook=None):
    """Exclusive dirfd writer; helper admission + no-follow identity checks at every write."""
    if set(payloads) != set(filenames) or "publication.json" in filenames:
        raise ValueError("Require the complete reserved output set")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run_path):
        raise ValueError("Use a fresh safe vintage name")
    admission_phase.code = verify_code()
    admission_phase.verify_helper()
    admission_phase.helper.admit_destination(admission_phase.baseline, OWNED, run_path, filenames)
    for path in admission_phase.baseline.pins:
        admission_phase.baseline.pinned_bytes(path)
    for name, raw in payloads.items():
        if Path(name).name != name or not name or len(raw) > MAX_FILE:
            raise ValueError("Unsafe or oversized output name")
        if name.endswith(".gz") and len(gzip.decompress(raw)) > MAX_FILE:
            raise ValueError("Decoded output exceeds per-file byte bound")
    root_fd = os.open(ROOT, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    opened = [root_fd]
    named = []
    try:
        for part in ("research", "geography", OWNED.rstrip("/").split("/")[-1], "vintages"):
            parent = opened[-1]
            try:
                os.mkdir(part, mode=0o755, dir_fd=parent)
            except FileExistsError:
                pass
            fd = os.open(part, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent)
            opened.append(fd)
            named.append((parent, part, fd))
        parent_fd = opened[-1]
        try:
            os.mkdir(run_path, mode=0o755, dir_fd=parent_fd)
        except FileExistsError as error:
            raise FileExistsError("Fresh output vintage already exists") from error
        run_fd = os.open(run_path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
        opened.append(run_fd)
        named.append((parent_fd, run_path, run_fd))
        expected = os.fstat(run_fd)
        def assert_owned():
            for parent, name, child in named:
                now = os.stat(name, dir_fd=parent, follow_symlinks=False)
                held = os.fstat(child)
                if not stat.S_ISDIR(now.st_mode) or (now.st_dev, now.st_ino) != (held.st_dev, held.st_ino):
                    raise RuntimeError("Output ancestor or vintage was replaced; foreign directory left untouched")
        outputs = []
        for index, name in enumerate(filenames):
            assert_owned()
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644, dir_fd=run_fd)
            try:
                raw = payloads[name]
                view = memoryview(raw)
                while view:
                    written = os.write(fd, view)
                    view = view[written:]
                os.fsync(fd)
            finally:
                os.close(fd)
            outputs.append({"path": OWNED + "vintages/" + run_path + "/" + name, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"})
            if failure_hook:
                failure_hook("after-output", parent_fd, run_fd, run_path, index)
        assert_owned()
        receipt = canonical({"version": 1, "status": "complete", "outputs": outputs})
        fd = os.open(".publication-incomplete", os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=run_fd)
        try:
            os.write(fd, receipt)
            os.fsync(fd)
        finally:
            os.close(fd)
        assert_owned()
        os.rename(".publication-incomplete", "publication.json", src_dir_fd=run_fd, dst_dir_fd=run_fd)
        os.fsync(run_fd)
        if failure_hook:
            failure_hook("after-receipt", parent_fd, run_fd, run_path, len(filenames))
        assert_owned()
        return receipt
    finally:
        for fd in reversed(opened):
            try:
                os.close(fd)
            except OSError:
                pass
