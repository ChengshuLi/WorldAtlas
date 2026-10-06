#!/usr/bin/env python3
"""Safely reproduce the immutable #421 roster and geometry phases."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PACKET = ROOT / "data/regional-review/regional-review-3f920fc5cb99166e"
PIN_FILE = HERE / "original-input-pins.json"
EXPECTED_SUBJECTS = 230
MAX_OBJECT = 32 * 1024 * 1024
MAX_PHASE = 256 * 1024 * 1024
RUN_ID = "verify-20261006-02"

OUTPUTS = {
    "roster": ["assessment.csv", "province-scope.csv", "area-scope.csv", "reproduction-summary.json"],
    "geometry": ["geometry-screen.csv", "parent-scale-screen.csv", "geometry-method-and-neighbor-summary.json", "geometry-run-summary.json"],
}
SCRIPTS = {
    "roster": "reproduce.py",
    "geometry": "geometry_screen.py",
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def guarded_path_open(path: Path, mode: str, *, old_open, root: Path, packet: Path,
                      outdir: Path, allowed: set[str], pinned: set[str], writes: list[str],
                      args=(), kwargs=None):
    """Guard packet paths lexically, before symlinks can redirect resolution."""
    lexical = Path(os.path.abspath(path))
    root = Path(os.path.abspath(root))
    packet = Path(os.path.abspath(packet))
    if lexical == packet or packet in lexical.parents:
        # Reject symlinked packet components, including the target file. This
        # applies to both reads and writes, and does not follow the final link.
        current = lexical
        while current != packet:
            if current.is_symlink():
                raise PermissionError(f"Symlinked historical packet path: {current}")
            current = current.parent
        if packet.is_symlink():
            raise PermissionError(f"Symlinked historical packet directory: {packet}")
        rel = str(lexical.relative_to(root))
        if any(flag in mode for flag in "wax+"):
            if lexical.parent != packet or lexical.name not in allowed or "r" in mode or "+" in mode:
                raise PermissionError(f"Unexpected historical output target: {rel}")
            destination = outdir / lexical.name
            if destination.exists():
                raise FileExistsError(f"Fresh output already exists: {destination}")
            writes.append(lexical.name)
            return old_open(destination, "x" + ("b" if "b" in mode else ""), *args, **(kwargs or {}))
        if rel not in pinned:
            raise PermissionError(f"Unpinned historical packet read: {rel}")
    return old_open(path, mode, *args, **(kwargs or {}))


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"], stderr=subprocess.PIPE)


def read_pins() -> list[dict]:
    doc = json.loads(PIN_FILE.read_text(encoding="utf-8"))
    if doc.get("version") != 1 or doc.get("issue") != 1169 or len(doc.get("inputs", [])) != 47:
        raise ValueError("The 47-entry original-input contract is missing or malformed")
    return doc["inputs"]


def verify_scope() -> dict:
    item = next(x for x in read_pins() if x["path"].endswith("/scope.json"))
    scope = json.loads(git_bytes(item["commit"], item["path"]))
    subjects = scope.get("member_location_ids", [])
    if len(subjects) != EXPECTED_SUBJECTS or len(set(subjects)) != EXPECTED_SUBJECTS:
        raise ValueError("Exact 230-subject scope is incomplete or duplicated")
    if scope.get("location_count") != EXPECTED_SUBJECTS or len(scope.get("province_scopes", [])) != 17 or len(scope.get("area_scopes", [])) != 3:
        raise ValueError("Historical parent/area reference-context counts changed")
    if scope.get("owned_evidence_path") != "data/regional-review/regional-review-3f920fc5cb99166e/":
        raise ValueError("Unexpected source packet ownership path")
    return {"subject_count": len(subjects), "subject_ids": subjects,
            "scope_sha256": item["sha256"], "parent_reference_count": len(scope["province_scopes"]),
            "area_reference_count": len(scope["area_scopes"]), "area_scopes": scope["area_scopes"],
            "source_packet_owned_path": scope["owned_evidence_path"]}


def validate_inputs(overrides: dict[str, bytes] | None = None) -> dict:
    """Verify immutable Git blobs and materialized files before execution."""
    overrides = overrides or {}
    pins = read_pins()
    total = 0
    for item in pins:
        raw = overrides.get(f"{item['commit']}:{item['path']}")
        if raw is None:
            raw = git_bytes(item["commit"], item["path"])
        if len(raw) > MAX_OBJECT:
            raise ValueError(f"Input exceeds 32 MiB: {item['path']}")
        if len(raw) != item["bytes"] or sha(raw) != item["sha256"]:
            raise ValueError(f"Historical input mismatch: {item['path']}")
        total += len(raw)
        local = ROOT / item["path"]
        # Older baseline files need not be materialized in the sparse checkout;
        # when present, they must match the same immutable bytes as the Git blob.
        current = local
        while current != ROOT:
            if current.is_symlink():
                raise ValueError(f"Symlinked working-tree input is not allowed: {item['path']}")
            current = current.parent
        if local.exists() and (not local.is_file() or local.stat().st_size != item["bytes"] or sha(local.read_bytes()) != item["sha256"]):
            raise ValueError(f"Working-tree input differs from its immutable pin: {item['path']}")
    if total > MAX_PHASE:
        raise ValueError("Complete input admission exceeds 256 MiB")
    return {"file_count": len(pins), "input_bytes": total, "max_file_bytes": max(x["bytes"] for x in pins)}


def verify_negative_controls() -> dict:
    pins = read_pins()
    controls = []
    cases = [
        ("wrong-baseline", next(x for x in pins if x["path"] == "data/hierarchy.json")),
        ("demonstrated-whole-source-drift", next(x for x in pins if x["path"].endswith("geoBoundaries-XKX-ADM1.geojson"))),
        ("wrong-original-code", next(x for x in pins if x["path"].endswith("/reproduce.py"))),
    ]
    for name, item in cases:
        original = git_bytes(item["commit"], item["path"])
        mutated = bytearray(original)
        mutated[len(mutated) // 2] ^= 1
        key = f"{item['commit']}:{item['path']}"
        try:
            validate_inputs({key: bytes(mutated)})
        except ValueError:
            controls.append({"id": name, "outcome": "passed", "rejected_path": item["path"], "before_output_creation": True})
        else:
            raise AssertionError(f"Wrong bytes were admitted: {name}")

    # Reproduce the exact name-drift probe on a complete source object in memory.
    xkx = next(x for x in pins if x["path"].endswith("geoBoundaries-XKX-ADM1.geojson"))
    raw = git_bytes(xkx["commit"], xkx["path"])
    fc = json.loads(raw)
    subject = "2360587B11570115914955"
    matches = [f for f in fc["features"] if f.get("properties", {}).get("shapeID") == subject]
    if len(matches) != 1:
        raise AssertionError("Demonstrated native source feature is not unique")
    matches[0]["properties"]["shapeName"] = "AUDITOR_SYNTHETIC_SOURCE_NAME"
    synthetic = json.dumps(fc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    key = f"{xkx['commit']}:{xkx['path']}"
    try:
        validate_inputs({key: synthetic})
    except ValueError:
        controls.append({"id": "demonstrated-complete-source-name-drift", "outcome": "passed", "native_id": subject,
                         "synthetic_name": "AUDITOR_SYNTHETIC_SOURCE_NAME", "source_bytes_modified": False,
                         "rejected_path": xkx["path"], "before_output_creation": True})
    else:
        raise AssertionError("The synthetic complete-source drift was admitted")

    # Exclusive output admission must preserve an existing sentinel byte-for-byte.
    sentinel_dir = HERE / "runs" / RUN_ID / "controls"
    sentinel_dir.mkdir(parents=True, exist_ok=False)
    sentinel = sentinel_dir / "assessment.csv"
    sentinel.write_bytes(b"DO NOT OVERWRITE\n")
    before = sentinel.read_bytes()
    try:
        with sentinel.open("x", encoding="utf-8"):
            pass
    except FileExistsError:
        pass
    else:
        raise AssertionError("Existing output was not rejected")
    if sentinel.read_bytes() != before:
        raise AssertionError("Existing output sentinel changed")
    controls.append({"id": "existing-output", "outcome": "passed", "sentinel_sha256": sha(before), "preserved": True})

    # A retained historical output path that is a symlink must never redirect
    # writes to an external file. Exercise the same guard used by reproduction.
    with tempfile.TemporaryDirectory(prefix="symlink-guard-", dir=HERE / "runs" / RUN_ID) as temp:
        sandbox = Path(temp)
        root = sandbox / "repo"
        packet = root / "data/regional-review/legacy"
        packet.mkdir(parents=True)
        fresh = sandbox / "fresh"
        fresh.mkdir()
        external = sandbox / "external-sentinel.csv"
        external.write_bytes(b"EXTERNAL EVIDENCE MUST SURVIVE\n")
        historical = packet / "assessment.csv"
        historical.symlink_to(external)
        before = external.read_bytes()
        writes: list[str] = []
        try:
            guarded_path_open(historical, "w", old_open=Path.open, root=root, packet=packet,
                              outdir=fresh, allowed={"assessment.csv"}, pinned={"data/regional-review/legacy/assessment.csv"},
                              writes=writes)
        except PermissionError:
            pass
        else:
            raise AssertionError("Symlinked historical output path was admitted")
        if external.read_bytes() != before:
            raise AssertionError("External symlink target changed")
        controls.append({"id": "symlink-output-target", "outcome": "passed",
                         "target_sha256": sha(before), "preserved": True, "rejected_before_write": True})
    result = {"version": 1, "method_id": "immutable-input-and-exclusive-output-guard", "controls": controls}
    target = HERE / "runs" / RUN_ID / "negative-controls.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    return result


def execute_phase(phase: str, run_name: str) -> dict:
    capacity = validate_inputs()
    original_script = PACKET / SCRIPTS[phase]
    input_pin = next(x for x in read_pins() if x["path"] == str(original_script.relative_to(ROOT)))
    source = git_bytes(input_pin["commit"], input_pin["path"])
    outdir = HERE / "runs" / RUN_ID / run_name
    outdir.parent.mkdir(parents=True, exist_ok=True)
    outdir.mkdir(exist_ok=False)
    allowed = set(OUTPUTS[phase])
    reads: set[str] = set()
    writes: list[str] = []
    old_open = Path.open
    pinned_paths = {x["path"] for x in read_pins()}

    def guarded_open(path: Path, mode="r", *args, **kwargs):
        result = guarded_path_open(path, mode, old_open=old_open, root=ROOT, packet=PACKET,
                                   outdir=outdir, allowed=allowed,
                                   pinned=pinned_paths, writes=writes,
                                   args=args, kwargs=kwargs)
        if str(path).startswith(str(PACKET)) and not any(flag in mode for flag in "wax+"):
            reads.add(str(Path(os.path.abspath(path)).relative_to(ROOT)))
        return result

    # Import the exact historical helper only after all its bytes have passed
    # the same 47-input verification.  Python's bytecode cache is disabled.
    old_sys_path = list(sys.path)
    old_argv = list(sys.argv)
    old_file = globals().get("__file__")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.argv = [str(original_script)]
    Path.open = guarded_open
    started = time.time()
    try:
        with redirect_stdout(io.StringIO()):
            exec(compile(source, str(original_script), "exec"), {"__name__": "__main__", "__file__": str(original_script)})
    finally:
        Path.open = old_open
        sys.path[:] = old_sys_path
        sys.argv[:] = old_argv
        if old_file is not None:
            globals()["__file__"] = old_file
    elapsed = round(time.time() - started, 3)
    if set(writes) != allowed:
        raise AssertionError(f"Unexpected output set for {phase}: {writes}")
    generated = []
    for filename in OUTPUTS[phase]:
        raw = (outdir / filename).read_bytes()
        if len(raw) > MAX_OBJECT:
            raise ValueError(f"Generated output exceeds 32 MiB: {filename}")
        old = next(x for x in read_pins() if x["path"] == f"data/regional-review/regional-review-3f920fc5cb99166e/{filename}")
        expected = git_bytes(old["commit"], old["path"])
        generated.append({"path": str((outdir / filename).relative_to(ROOT)), "bytes": len(raw), "sha256": sha(raw),
                          "matches_historical": raw == expected, "historical_sha256": old["sha256"]})
        if raw != expected:
            raise AssertionError(f"Generated result differs from historical output: {filename}")
    output_bytes = sum(x["bytes"] for x in generated)
    if capacity["input_bytes"] + output_bytes > MAX_PHASE:
        raise ValueError("Complete reproduction phase exceeds 256 MiB")
    post = validate_inputs()
    if post != capacity:
        raise AssertionError("Input admission changed during reproduction")
    return {"phase": phase, "run": run_name, "elapsed_seconds": elapsed, "input_admission": capacity,
            "packet_files_read": sorted(reads), "outputs": generated}


def write_json(name: str, value: dict) -> str:
    target = HERE / "runs" / RUN_ID / "receipts" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    return str(target.relative_to(ROOT))


def aggregate_run_sha(run: dict) -> str:
    payload = [{"name": Path(row["path"]).name, "sha256": row["sha256"]} for row in run["outputs"]]
    return sha(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def create_validation_receipts(runs: list[dict], control: dict) -> list[dict]:
    receipt_rows = []
    negative_ids = [x["id"] for x in control["controls"] if x["id"] != "existing-output"]
    for phase, method in (("roster", "exact-roster-generator"), ("geometry", "geometry-screen-generator")):
        pair = [r for r in runs if r["phase"] == phase]
        first = aggregate_run_sha(pair[0])
        second = aggregate_run_sha(pair[1])
        if first != second:
            raise AssertionError(f"Run-level reproducibility failed for {phase}")
        positive = {"version": 1, "method_id": method, "kind": "positive-control", "outcome": "passed",
                    "run": pair[0]["run"], "output_count": len(pair[0]["outputs"]),
                    "historical_output_matches": sum(x["matches_historical"] for x in pair[0]["outputs"]),
                    "historical_output_hashes": [x["historical_sha256"] for x in pair[0]["outputs"]],
                    "scope_subjects": EXPECTED_SUBJECTS}
        negative = {"version": 1, "method_id": method, "kind": "negative-control", "outcome": "passed",
                    "rejected_input_mutations": negative_ids, "outputs_created_before_rejection": False,
                    "control_manifest": f"runs/{RUN_ID}/negative-controls.json"}
        repeat = {"version": 1, "method_id": method, "kind": "reproducibility", "outcome": "passed",
                  "run_one": pair[0]["run"], "run_two": pair[1]["run"],
                  "run_one_sha256": first, "run_two_sha256": second}
        rows = [("positive-control", positive), ("negative-control", negative), ("reproducibility", repeat)]
        for kind, value in rows:
            path = write_json(f"{phase}-{kind}.json", value)
            receipt_rows.append({"method_id": method, "kind": kind, "outcome": "passed", "evidence_path": path})
    geometry_run = next(r for r in runs if r["phase"] == "geometry")
    diagnostic = json.loads((ROOT / geometry_run["outputs"][2]["path"]).read_text(encoding="utf-8"))
    method = "epsg6933-source-comparison"
    for kind in ("positive-control", "negative-control"):
        detail = diagnostic["controls"][kind.replace("-", "_")]
        value = {"version": 1, "method_id": method, "kind": kind, "outcome": detail["outcome"],
                 "expectation": detail["expectation"], "observed_iou": detail["observed_iou"],
                 "source_artifact": geometry_run["outputs"][2]["path"]}
        path = write_json(f"geometry-diagnostic-{kind}.json", value)
        receipt_rows.append({"method_id": method, "kind": kind, "outcome": "passed", "evidence_path": path})
    return receipt_rows


def main() -> None:
    global RUN_ID
    if len(sys.argv) not in (1, 3) or (len(sys.argv) == 3 and sys.argv[1] != "--run-id"):
        raise SystemExit("Usage: reproduce_guarded.py [--run-id UNIQUE-VINTAGE]; input pins and paths are fixed.")
    if len(sys.argv) == 3:
        RUN_ID = sys.argv[2]
    if not __import__("re").fullmatch(r"[a-z0-9][a-z0-9-]{0,47}", RUN_ID):
        raise SystemExit("Run id must be a lowercase slug of at most 48 characters")
    if (HERE / "runs" / RUN_ID).exists():
        raise SystemExit("Run output directory already exists; choose a new run id to preserve prior evidence")
    admission = validate_inputs()
    scope = verify_scope()
    control = verify_negative_controls()
    runs = [execute_phase(phase, f"{phase}-run-{index}") for phase in OUTPUTS for index in (1, 2)]
    for phase in OUTPUTS:
        pair = [r for r in runs if r["phase"] == phase]
        if [o["sha256"] for o in pair[0]["outputs"]] != [o["sha256"] for o in pair[1]["outputs"]]:
            raise AssertionError(f"Repeated phase differs: {phase}")
    validations = create_validation_receipts(runs, control)
    roster_summary_entry = next(x for r in runs if r["phase"] == "roster" for x in r["outputs"] if x["path"].endswith("/reproduction-summary.json"))
    roster_summary = json.loads((ROOT / roster_summary_entry["path"]).read_text(encoding="utf-8"))
    reproduced_scope_summary = {"row_count": roster_summary["scoped_locations"],
                                "province_parent_count": roster_summary["province_parents"],
                                "outcomes": roster_summary["outcomes"],
                                "source_counts": roster_summary["source_counts"],
                                "native_source_feature_counts": {"Greece_2010": roster_summary["GRC_source_features"],
                                                                  "Kosovo_2021_package": roster_summary["XKX_asset_features"]},
                                "area_counts": {name: {"owned": counts[0], "full": counts[1]}
                                                for name, counts in roster_summary["area_counts"].items()},
                                "assessment_sha256": roster_summary["assessment_sha256"]}
    result = {"version": 1, "issue": 1169, "source_packet_issue": 421, "scope_accounting": scope,
              "input_admission": admission, "runs": runs, "negative_controls": control["controls"],
              "reproduced_scope_summary": reproduced_scope_summary,
              "validation": validations,
              "historical_outputs_matched": sum(o["matches_historical"] for r in runs for o in r["outputs"]),
              "historical_output_comparisons": sum(len(r["outputs"]) for r in runs),
              "limits": ["Reproduction safeguards and historical numerical identity do not establish legal boundaries, license compatibility, present-day completeness, or regional approval."]}
    target = HERE / "runs" / RUN_ID / "reproduction-results.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"issue": 1169, "inputs": admission["file_count"], "input_bytes": admission["input_bytes"],
                      "runs": len(runs), "historical_outputs_matched": result["historical_outputs_matched"],
                      "negative_controls": len(control["controls"]), "result": str(target.relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    main()
