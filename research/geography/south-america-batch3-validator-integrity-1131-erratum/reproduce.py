#!/usr/bin/env python3
"""Safely execute the retained batch3 validator into a fresh evidence vintage.

The source validator is intentionally left byte-for-byte unchanged. Its seven
historical output paths are intercepted in memory; products are committed only
under this erratum's fresh run namespace.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import sys
import uuid
from datetime import datetime, timezone
import platform
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
OWNED = Path("research/geography/south-america-batch3-validator-integrity-1131-erratum")
SOURCE = Path("data/regional-review/southern-south-america-batch3-validation-20261006")
SCRIPT = SOURCE / "validate_batch3.py"
LEDGER = SOURCE / "source/upstream-lfs-pointer-records.json"
OUTPUTS = (
    "baseline-feature-bindings.json",
    "source-provenance-findings.json",
    "adversarial-controls.json",
    "verification-results.json",
    "positive-control.json",
    "negative-control.json",
    "reproducibility.json",
)
EXPECTED = {
    "arg-adm2-geojson": ("releaseData/gbOpen/ARG/ADM2/geoBoundaries-ARG-ADM2.geojson", "f35dae5a257302dea5bd1549ae135baf82e7ee7491918854c3db9bbdec890177", 69702323),
    "chl-adm3-geojson": ("releaseData/gbOpen/CHL/ADM3/geoBoundaries-CHL-ADM3.geojson", "f3833ce1965394ae705e3793b50bdd007775b43da604251871deffed04f3bffd", 171783952),
    "arg-adm2-metaData-json": ("releaseData/gbOpen/ARG/ADM2/geoBoundaries-ARG-ADM2-metaData.json", "17452b82df4498c1b29a4489bd78709cef922b453579b1a47010dfd2524a7ce2", 958),
    "chl-adm3-metaData-json": ("releaseData/gbOpen/CHL/ADM3/geoBoundaries-CHL-ADM3-metaData.json", "658356bb413f8b284b260360d1309527781e1b0c46027e1ae0a4c58da1c99409", 983),
    "arg-adm2-metaData-txt": ("releaseData/gbOpen/ARG/ADM2/geoBoundaries-ARG-ADM2-metaData.txt", "bb817b543f9e2b56a597b3114f9a20d35f01dd5090dcc483b8acbad38d4a23a6", 1116),
    "chl-adm3-metaData-txt": ("releaseData/gbOpen/CHL/ADM3/geoBoundaries-CHL-ADM3-metaData.txt", "6cfbdf4f0d46be517dfef3454e94b3eaf870b77911bb73b93825205464712b34", 1142),
}


class Invalid(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def read_ledger(path: Path) -> tuple[bytes, dict]:
    raw = path.read_bytes()
    try:
        doc = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Invalid("pointer ledger is not valid UTF-8 JSON") from exc
    if not isinstance(doc, dict) or doc.get("version") != 1 or doc.get("commit") != "9469f09592ced973a3448cf66b6100b741b64c0d":
        raise Invalid("pointer ledger format or upstream vintage differs")
    rows = doc.get("objects")
    if not isinstance(rows, list) or len(rows) != len(EXPECTED):
        raise Invalid(f"pointer ledger must contain exactly {len(EXPECTED)} records before identity mapping")
    if any(not isinstance(row, dict) or not isinstance(row.get("id"), str) for row in rows):
        raise Invalid("pointer ledger contains a malformed record")
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise Invalid("duplicate pointer record identity")
    if set(ids) != set(EXPECTED):
        raise Invalid("pointer ledger contains missing or foreign identities")
    for row in rows:
        path_expected, oid, size = EXPECTED[row["id"]]
        if row.get("upstream_commit") != doc["commit"] or row.get("upstream_path") != path_expected:
            raise Invalid("pointer record path or vintage mismatch: " + row["id"])
        if row.get("lfs_object_sha256") != oid or row.get("lfs_object_bytes") != size:
            raise Invalid("pointer record LFS hash or size mismatch: " + row["id"])
    return raw, doc


def safe_root(run_id: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run_id):
        raise Invalid("run ID must be a safe lowercase slug")
    base = (ROOT / OWNED / "runs").resolve()
    target = ROOT / OWNED / "runs" / run_id
    if target.resolve(strict=False).parent != base or target.is_symlink():
        raise Invalid("run destination escapes the owned namespace or is a symlink")
    # Check every existing ancestor without following a dangling link silently.
    for part in (target, *target.parents):
        if part == ROOT:
            break
        if part.is_symlink():
            raise Invalid("symlink in run destination path")
    if os.path.lexists(target):
        raise FileExistsError("run destination already exists; choose a new run ID")
    return target


def write_complete(root: Path, files: dict[str, bytes], metadata: dict) -> dict:
    if set(files) != set(OUTPUTS) or any(not isinstance(v, bytes) for v in files.values()):
        raise Invalid("actual entry point did not produce the complete seven-product set")
    if not root.is_dir() or any((root / name).exists() or (root / name).is_symlink() for name in (*OUTPUTS, "publication.json")):
        raise FileExistsError("reserved run destination changed before output publication")
    descriptors = []
    try:
        for name in OUTPUTS:
            path = root / name
            with path.open("xb") as stream:
                stream.write(files[name])
                stream.flush()
                os.fsync(stream.fileno())
            descriptors.append({"path": name, "bytes": len(files[name]), "sha256": sha(files[name])})
        receipt = {"version": 1, "status": "complete", **metadata, "outputs": descriptors}
        temp = root / ".publication-incomplete"
        with temp.open("xb") as stream:
            stream.write(canonical(receipt))
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, root / "publication.json")
        temp.unlink()
        return receipt
    except Exception:
        # A failed run is intentionally preserved without a success receipt.
        raise


def run(run_id: str, fixture: Path | None = None) -> dict:
    root = safe_root(run_id)
    ledger_path = ROOT / LEDGER
    source_raw, source_doc = read_ledger(fixture if fixture else ledger_path)
    # Reserve an empty, exclusive directory before executing the generator. The
    # fixed seven filenames and final receipt are now admitted as one set.
    root.parent.mkdir(parents=True, exist_ok=True)
    root = safe_root(run_id)
    root.mkdir(exist_ok=False)
    output_paths = { (ROOT / SOURCE / name).resolve(): name for name in OUTPUTS }
    generated: dict[str, bytes] = {}
    original_read_bytes = Path.read_bytes
    original_write_bytes = Path.write_bytes
    original_read_text = Path.read_text

    def redirected_write(self, data):
        path = Path(self).resolve()
        name = output_paths.get(path)
        if name is None:
            return original_write_bytes(self, data)
        if name in generated:
            raise Invalid("original entry point attempted to write an output twice")
        if not isinstance(data, bytes):
            raise Invalid("original output writer supplied non-bytes")
        generated[name] = data
        return len(data)

    def redirected_read_bytes(self, *args, **kwargs):
        name = output_paths.get(Path(self).resolve())
        if name is not None and name in generated:
            return generated[name]
        return original_read_bytes(self, *args, **kwargs)

    def redirected_read_text(self, *args, **kwargs):
        if fixture is not None and Path(self).resolve() == ledger_path.resolve():
            return source_raw.decode("utf-8")
        return original_read_text(self, *args, **kwargs)

    old_argv = sys.argv
    try:
        sys.argv = [str(ROOT / SCRIPT)]
        with patch.object(Path, "write_bytes", redirected_write), patch.object(Path, "read_bytes", redirected_read_bytes), patch.object(Path, "read_text", redirected_read_text):
            runpy.run_path(str(ROOT / SCRIPT), run_name="__main__")
    finally:
        sys.argv = old_argv
    metadata = {
        "run_id": run_id,
        "execution_id": str(uuid.uuid4()),
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "entry_point": str(SCRIPT),
        "entry_point_sha256": sha((ROOT / SCRIPT).read_bytes()),
        "wrapper": str(OWNED / "reproduce.py"),
        "wrapper_sha256": sha(Path(__file__).read_bytes()),
        "shared_helper": "scripts/evidence/immutable.py",
        "shared_helper_sha256": sha((ROOT / "scripts/evidence/immutable.py").read_bytes()),
        "python_version": platform.python_version(),
        "shapely_version": __import__("shapely").__version__,
        "pointer_ledger_path": str(LEDGER),
        "pointer_ledger_sha256": sha(source_raw),
        "pointer_record_count": len(source_doc["objects"]),
        "pointer_record_ids": sorted(row["id"] for row in source_doc["objects"]),
        "fixture_input": str(fixture.relative_to(ROOT)) if fixture else None,
    }
    receipt = write_complete(root, generated, metadata)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--pointer-fixture", type=Path)
    args = parser.parse_args()
    fixture = args.pointer_fixture.resolve() if args.pointer_fixture else None
    receipt = run(args.run_id, fixture)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Invalid, FileExistsError) as exc:
        print(f"reproduction rejected: {exc}", file=sys.stderr)
        raise SystemExit(2)
