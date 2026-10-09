#!/usr/bin/env python3
"""Bind the two fresh native-footprint audit runs without rewriting them."""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

OWN = Path(__file__).resolve().parent
MAX_FILE = 32 * 1024 * 1024
MAX_PHASE = 256 * 1024 * 1024
OUTPUT_RESERVE = 6 * 1024 * 1024

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def admit(run_names):
    """Admit every input and all three destinations before reading inputs."""
    assert len(run_names) == 2 and run_names[0] != run_names[1]
    for name in run_names:
        assert name.replace("-", "").isalnum(), "run names must be simple IDs"
    inputs = [OWN / "runs" / name / "native-coverage-audit.json" for name in run_names]
    outputs = [OWN / "runs" / name / "run-manifest.json" for name in run_names]
    repro = OWN / f"reproducibility-{run_names[0]}-{run_names[1]}.json"
    outputs.append(repro)
    sizes = []
    for path in [*inputs, Path(__file__).resolve()]:
        assert path.resolve() == path and OWN in path.parents and not path.is_symlink() and path.is_file()
        size = path.stat().st_size
        assert size <= MAX_FILE, f"per-file admission failed: {path}"
        sizes.append(size)
    assert sum(sizes) + OUTPUT_RESERVE <= MAX_PHASE, "complete finalizer phase exceeds 256 MiB"
    for path in outputs:
        assert path.parent.resolve() == path.parent and (path.parent == OWN or OWN in path.parent.resolve().parents)
        assert not path.parent.is_symlink() and path.parent.is_dir()
        assert not os.path.lexists(path), f"refuse existing output, including dangling symlink: {path}"
    return inputs, outputs

def write_all(rows):
    encoded = [(path, data.encode("utf-8")) for path, data in rows]
    assert sum(len(data) for _, data in encoded) <= OUTPUT_RESERVE
    assert all(len(data) <= 2 * 1024 * 1024 for _, data in encoded)
    for path, _ in encoded:
        assert not os.path.lexists(path), f"refuse existing output, including dangling symlink: {path}"
    created = []
    try:
        for path, data in encoded:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644)
            st = os.fstat(fd)
            created.append((path, st.st_dev, st.st_ino))
            try:
                offset = 0
                while offset < len(data):
                    offset += os.write(fd, data[offset:])
                os.fsync(fd)
            finally:
                os.close(fd)
    except Exception:
        for path, device, inode in reversed(created):
            try:
                st = path.lstat()
                if (st.st_dev, st.st_ino) == (device, inode):
                    path.unlink()
            except FileNotFoundError:
                pass
        raise

def main():
    run_names = sys.argv[1:3] if len(sys.argv) >= 3 else ["run-1", "run-2"]
    inputs, destinations = admit(run_names)
    outs = []
    manifest_payloads = []
    for name, result, manifest in zip(run_names, inputs, destinations[:2]):
        data = json.loads(result.read_bytes())
        assert data["method_id"] == "native-geotiff-coverage-and-pixel-controls"
        assert data["outcome"] == "passed"
        result_hash = digest(result)
        result_size = result.stat().st_size
        outs.append({"run": name, "path": str(result.relative_to(OWN)), "sha256": result_hash, "bytes": result_size,
                     "audit_code_sha256": data["input_bindings"]["audit_code"]["sha256"],
                     "input_bindings": data["input_bindings"]})
        manifest_payloads.append(json.dumps({"schema": "worldatlas-source-run-v1", "run": name,
                                        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                                        "method_id": data["method_id"], "outcome": data["outcome"],
                                        "output": {"path": str(result.relative_to(OWN)), "bytes": result_size, "sha256": result_hash},
                                        "audit_code": data["input_bindings"]["audit_code"],
                                        "input_bindings": data["input_bindings"],
                                        "interpretation": "Only native headers, three exact one-pixel controls and geometric tile-footprint coverage; no monthly surface-water counts."}, indent=2, sort_keys=True) + "\n")
    assert outs[0]["sha256"] == outs[1]["sha256"]
    repro_payload = json.dumps({"schema": "worldatlas-source-reproducibility-v1", "method_id": "native-geotiff-coverage-and-pixel-controls",
                                 "status": "reproduced-byte-identically", "runs": outs,
                                 "run_one_sha256": outs[0]["sha256"], "run_two_sha256": outs[1]["sha256"],
                                 "limits": ["This repeated source-footprint phase does not rerun the refused 578,813,952-byte full monthly pixel phase.",
                                            "Equal bytes show deterministic output from the same pinned sources and method; they do not certify geographic truth or physical classification."]}, indent=2, sort_keys=True) + "\n"
    write_all(list(zip(destinations, [*manifest_payloads, repro_payload])))
    repro_hash = hashlib.sha256(repro_payload.encode()).hexdigest()
    print(f"matching audit outputs: {outs[0]['sha256']}; reproducibility receipt {repro_hash}")

if __name__ == "__main__":
    main()
