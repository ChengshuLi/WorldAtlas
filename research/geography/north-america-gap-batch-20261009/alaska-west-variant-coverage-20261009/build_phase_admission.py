#!/usr/bin/env python3
"""Inventory the exact bounded source-coverage phase before any overlay call."""
from __future__ import annotations

import hashlib
import json
import pathlib
import stat

ROOT = pathlib.Path(__file__).resolve().parents[4]
PACKET = "research/geography/north-america-gap-batch-20261009/alaska-west-variant-coverage-20261009"
RUNTIME_TEMPLATE = "research/geography/alaska-thirteen-geometry-measurement-20261008/phase-admission.json"
INPUTS = [
    RUNTIME_TEMPLATE,
    "research/geography/north-america-gap-batch-20261009/alaska-west-four-source-physical-evidence.json",
    "research/geography/alaska-thirteen-geometry-measurement-20261008/sources/geoboundaries-USA-ADM2-full-9469f09.geojson",
    "research/geography/alaska-thirteen-geometry-measurement-20261008/sources/geoboundaries-USA-ADM2-full-9469f09-receipt.json",
    "research/geography/alaska-thirteen-geometry-measurement-20261008/sources/geoboundaries-USA-ADM2-full-9469f09-source-check.json",
    "data/regional-review/usa-adm2-lineage-428/sources/upstream-2018/geoBoundaries-USA-ADM2_simplified.geojson",
    "data/regional-review/usa-adm2-lineage-428/sources/upstream-2018/simplified-object-retrieval.json",
    "data/regional-review/usa-adm2-lineage-428/sources/upstream-2018/retrieval.json",
    "data/regional-review/usa-adm2-lineage-428/sources/upstream-2018/geoBoundaries-USA-ADM2-metaData.json",
]
CODE = [
    "scripts/evidence/immutable.py",
    "research/geography/alaska-thirteen-geometry-measurement-20261008/measure_alaska.py",
    f"{PACKET}/variant_coverage_driver.py",
    f"{PACKET}/variant_coverage_run_phase.py",
    f"{PACKET}/build_phase_admission.py",
    f"{PACKET}/build_evidence_manifest.py",
]
RUNTIME_ROOT = pathlib.Path("/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python")
MAX_FILE = 32 * 1024 * 1024
MAX_PHASE = 256 * 1024 * 1024
MAX_PROCESS = 512 * 1024 * 1024
SCRATCH = 8 * 1024 * 1024
OUTPUT_RESERVE = 1024 * 1024


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def descriptor(path: str) -> dict:
    p = ROOT / path
    if p.is_symlink() or not p.is_file():
        raise SystemExit("phase member must be an ordinary file: " + path)
    raw = p.read_bytes()
    if len(raw) > MAX_FILE:
        raise SystemExit("phase member exceeds 32 MiB: " + path)
    return {"path": path, "bytes": len(raw), "sha256": digest(raw), "hash_kind": "file-bytes"}


def main() -> None:
    template = json.loads((ROOT / RUNTIME_TEMPLATE).read_bytes())
    closure = []
    seen = set()
    for prior in template["runtime_file_closure"]:
        path = pathlib.Path(prior["path"])
        resolved = path.resolve(strict=True)
        raw = resolved.read_bytes()
        mode = stat.S_IMODE(resolved.stat().st_mode)
        row = {"path": str(path), "realpath": str(resolved), "bytes": len(raw), "sha256": digest(raw), "mode": mode}
        if str(resolved) in seen:
            raise SystemExit("duplicate runtime file: " + str(resolved))
        seen.add(str(resolved))
        closure.append(row)
    runtime_bytes = sum(row["bytes"] for row in closure)
    python_version = template["runtime"]

    inputs = [descriptor(path) for path in INPUTS]
    code = [descriptor(path) for path in CODE]
    for row in inputs + code:
        if row["bytes"] > MAX_FILE:
            raise SystemExit("member exceeds 32 MiB: " + row["path"])
    input_bytes = sum(row["bytes"] for row in inputs)
    code_bytes = sum(row["bytes"] for row in code)
    phase = {
        "schema_version": 1,
        "status": "PASS",
        "scientific_operations_invoked": False,
        "scope": "Exactly four PR #1653 component geometries against the Aleutians West feature in two already-retained geoBoundaries USA ADM2 variants from the 9469f09 release.",
        "inputs": inputs,
        "project_code": code,
        "runtime": python_version,
        "runtime_file_closure": closure,
        "caps": {"max_member_bytes": MAX_FILE, "max_phase_bytes": MAX_PHASE, "max_process_bytes": MAX_PROCESS, "wall_seconds": 900},
        "max_process_bytes": MAX_PROCESS,
        "cap_bytes": MAX_PHASE,
        "component_totals": {
            "encoded_inputs": input_bytes,
            "project_code_files": code_bytes,
            "imported_runtime_files_and_python_executable": runtime_bytes,
            "scratch_reservation": SCRATCH,
            "generated_output_reservation": OUTPUT_RESERVE,
            "phase_admission_file_bytes": 0,
        },
    }
    out = ROOT / PACKET / "phase-admission.json"
    # Fixed-point the self-counted admission file size. A cryptographic
    # self-hash is intentionally omitted; the execution receipt binds the file.
    for _ in range(16):
        phase["complete_phase_bytes"] = sum(phase["component_totals"].values())
        phase["headroom_bytes"] = MAX_PHASE - phase["complete_phase_bytes"]
        raw = (json.dumps(phase, indent=2, ensure_ascii=False) + "\n").encode()
        size = len(raw)
        if size == phase["component_totals"]["phase_admission_file_bytes"]:
            break
        phase["component_totals"]["phase_admission_file_bytes"] = size
    else:
        raise SystemExit("phase admission byte-size accounting did not stabilize")
    phase["complete_phase_bytes"] = sum(phase["component_totals"].values())
    phase["headroom_bytes"] = MAX_PHASE - phase["complete_phase_bytes"]
    raw = (json.dumps(phase, indent=2, ensure_ascii=False) + "\n").encode()
    if len(raw) != phase["component_totals"]["phase_admission_file_bytes"]:
        raise SystemExit("phase admission byte-size changed after final total")
    if phase["complete_phase_bytes"] > MAX_PHASE:
        raise SystemExit("complete phase exceeds 256 MiB")
    out.write_bytes((json.dumps(phase, indent=2, ensure_ascii=False) + "\n").encode())
    print(json.dumps({"status": phase["status"], "complete_phase_bytes": phase["complete_phase_bytes"],
                      "cap_bytes": MAX_PHASE, "headroom_bytes": phase["headroom_bytes"],
                      "inputs": len(inputs), "project_code": len(code), "runtime_files": len(closure),
                      "runtime_bytes": runtime_bytes, "max_member_bytes": MAX_FILE,
                      "max_process_bytes": MAX_PROCESS, "admission_path": str(out)}, sort_keys=True))


if __name__ == "__main__":
    main()
