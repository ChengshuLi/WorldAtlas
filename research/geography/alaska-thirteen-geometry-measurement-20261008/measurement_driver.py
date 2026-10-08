#!/usr/bin/env python3
"""Authenticate one admitted run and publish it through the shared evidence writer."""
from __future__ import annotations
import gzip
import hashlib
import json
import pathlib
import hashlib
import stat
import subprocess
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[3]
CAMPAIGN = ROOT / "research/geography/alaska-thirteen-geometry-measurement-20261008"
OWNED_PATH = "research/geography/alaska-thirteen-geometry-measurement-20261008/"
OUTPUTS = ["measurement.json", "proposal-geometry.geojson",
           "proposal-gain-geometry.geojson", "output-manifest.json"]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: measurement_driver.py FRESH_RUN_NAME")
    run_name = sys.argv[1]
    commit = git("rev-parse", "HEAD").decode().strip()
    phase_path = "research/geography/alaska-thirteen-geometry-measurement-20261008/phase-admission.json"
    phase_raw = git("show", f"{commit}:{phase_path}")
    materialized_phase = (ROOT / phase_path).read_bytes()
    if materialized_phase != phase_raw:
        raise SystemExit("materialized phase admission differs from immutable HEAD")
    phase = json.loads(phase_raw)
    if phase.get("status") != "PASS" or phase.get("scientific_operations_invoked") is not False:
        raise SystemExit("a complete passing phase admission is required before source or geometry reads")

    pins_by_path = {}
    for row in phase.get("inputs", []) + phase.get("project_code", []):
        descriptor = {"path": row["path"], "bytes": row["bytes"], "sha256": row["sha256"], "hash_kind": "file-bytes"}
        if row["path"] in pins_by_path and pins_by_path[row["path"]] != descriptor:
            raise SystemExit(f"duplicate or conflicting phase pin: {row['path']}")
        pins_by_path[row["path"]] = descriptor
    phase_descriptor = {"path": phase_path, "bytes": len(phase_raw), "sha256": sha(phase_raw), "hash_kind": "file-bytes"}
    if phase_path in pins_by_path and pins_by_path[phase_path] != phase_descriptor:
        raise SystemExit("phase admission self-pin conflicts")
    pins_by_path[phase_path] = phase_descriptor

    helper_path = "scripts/evidence/immutable.py"
    helper_descriptor = pins_by_path.get(helper_path)
    if not helper_descriptor:
        raise SystemExit("shared immutable evidence helper is absent from phase code pins")
    helper_raw = git("show", f"{commit}:{helper_path}")
    if len(helper_raw) != helper_descriptor["bytes"] or sha(helper_raw) != helper_descriptor["sha256"]:
        raise SystemExit("shared evidence helper bytes differ from phase pin")
    helper_module = types.ModuleType("pinned_evidence_immutable")
    helper_module.__file__ = str(ROOT / helper_path)
    exec(compile(helper_raw, helper_module.__file__, "exec"), helper_module.__dict__)
    baseline = helper_module.Baseline(ROOT, commit, list(pins_by_path.values()))
    baseline.materialized_bytes(helper_path)
    for descriptor in pins_by_path.values():
        baseline.materialized_bytes(descriptor["path"])

    # Account for each decoded alias and the installed scientific runtime before
    # constructing the output reservation or invoking any geometry operation.
    for row in phase.get("decoded_aliases", []):
        encoded = baseline.materialized_bytes(row["path"])
        decoded = gzip.decompress(encoded)
        if len(decoded) != row["bytes"] or sha(decoded) != row["sha256"]:
            raise SystemExit(f"decoded native/source alias differs from immutable pin: {row['path']}")
        baseline.admit(row["path"] + ":decoded", len(decoded))
    totals = phase.get("component_totals", {})
    runtime_bytes = totals.get("imported_runtime_files_and_python_executable")
    scratch_bytes = totals.get("scratch_reservation")
    output_reserve = totals.get("generated_output_reservation")
    if not all(isinstance(value, int) and value >= 0 for value in (runtime_bytes, scratch_bytes, output_reserve)):
        raise SystemExit("runtime, scratch and output reserve are incomplete")
    if sum(baseline.consumed.values()) + runtime_bytes + scratch_bytes + output_reserve > baseline.max_phase_bytes:
        raise SystemExit("complete immutable inputs, runtime, scratch and generated-output reserve exceed 256 MiB")
    runtime_closure = phase.get("runtime_file_closure", [])
    if not runtime_closure:
        raise SystemExit("complete runtime file closure is absent from phase admission")
    verified_runtime = set()
    for row in runtime_closure:
        path = pathlib.Path(row["path"])
        realpath = path.resolve(strict=True)
        if str(realpath) != row.get("realpath") or not realpath.is_file():
            raise SystemExit(f"runtime path identity changed: {path}")
        raw = realpath.read_bytes()
        mode = stat.S_IMODE(realpath.stat().st_mode)
        if (len(raw) != row.get("bytes") or hashlib.sha256(raw).hexdigest() != row.get("sha256")
                or mode != row.get("mode")):
            raise SystemExit(f"runtime file bytes or mode changed: {realpath}")
        if str(realpath) in verified_runtime:
            raise SystemExit(f"duplicate runtime realpath: {realpath}")
        verified_runtime.add(str(realpath))
        baseline.admit("runtime:" + str(realpath), len(raw))
    if sum(row["bytes"] for row in runtime_closure) != runtime_bytes:
        raise SystemExit("runtime closure byte total differs from phase admission")
    baseline.admit("reserve:measurement-scratch", scratch_bytes)

    # This reserves the whole fresh output set before loading the pinned producer
    # or performing a single geometry predicate.
    vintage = helper_module.NewVintage(baseline, OWNED_PATH, run_name, OUTPUTS)
    modules = baseline.load_modules({"alaska_measurement": OWNED_PATH + "measure_alaska.py"})
    repo_root = pathlib.Path(ROOT).resolve()
    for module in tuple(sys.modules.values()):
        name = getattr(module, "__file__", None)
        if not name:
            continue
        path = pathlib.Path(name).resolve()
        try:
            path.relative_to(repo_root)
            continue
        except ValueError:
            pass
        if str(path) not in verified_runtime:
            raise SystemExit(f"loaded external module is outside admitted runtime closure: {path}")
        row = next(item for item in runtime_closure if item["realpath"] == str(path))
        raw = path.read_bytes()
        if (len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]
                or stat.S_IMODE(path.stat().st_mode) != row["mode"]):
            raise SystemExit(f"loaded runtime file changed after admission: {path}")
    producer = modules["alaska_measurement"]
    producer.BASELINE = baseline
    producer.VINTAGE = vintage
    producer.IMMUTABLE_BASELINE_COMMIT = commit
    sys.argv = [str(ROOT / (OWNED_PATH + "measure_alaska.py")), "--output-dir", run_name]
    producer.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
