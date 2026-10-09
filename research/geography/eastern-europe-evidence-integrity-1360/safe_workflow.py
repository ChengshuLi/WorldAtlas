#!/usr/bin/env python3
"""Safely stage and verify the exact #1344 producer without changing its history.

All writes are restricted to this issue's additive evidence directory. The
geographic producer is copied by exact digest from the accepted source packet
and run with complete, immutable inputs in fresh private namespaces. Receipts
are admitted as a complete set before execution and written exclusively.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]
ORIGINAL = REPO / "research/geography/eastern-europe-border-source-fitness-20261007"
EXEC = PACKET / "execution"
BASELINE = "432c5b8e0ac9b9597738a31f5386569312c75966"
ORIGINAL_MERGE = "0c30d0bf9cee9a8c300c7e3c8f45720b471a74ff"
CUSTODY_SHA = "db511bb8db98154ea189e6c0f8e3a6551277e68873084e0148e875a46e8cb01f"
RUN_ONE_SUMMARY_SHA = "5588dd339fe0a485e54bae8db4c283f8c6614b97e44f4fc55505c0aa1d4e6e9e"
RUN_TWO_SUMMARY_SHA = "5588dd339fe0a485e54bae8db4c283f8c6614b97e44f4fc55505c0aa1d4e6e9e"
CODE_PINS = {
    "produce.py": "1345d36a60d90d0c49340860125c436826d32e9bed0c17d9459b757c7f1dcaa1",
    "control-checks.py": "8c3e882b3ddaf4c082d9f42d3f072e1809119ff110b6eaaedde05f1473db4480",
    "execute.py": "fdc66851011afe0b20705ba65e0995f69d01601f5fdc11fc97de433081e179bb",
    "stage_inputs.py": "4b40f49f4bd258aa8bd71415a5bca424a3f7bc3f8795ef9e78adb2efb47da909",
    "build_manifest.py": "5822aa51684f12aaf4369074caa4671e372329742b575cce8e087fe222f6162e",
}
PRODUCTS = {
    "source-fitness.json",
    "scope-reconciliation.json",
    "feature-inventory.json",
    "whole-source-neighbor-overlays.csv",
    "run-summary.json",
}
SUBJECTS = sorted([
    "gb:BLR:ADM2:67162791B30498032594927",
    "gb:POL:ADM2:97123803B24100086136213",
    "gb:POL:ADM2:97123803B33088815311851",
    "gb:POL:ADM2:97123803B66371363243422",
    "gb:UKR:ADM2:74538382B51634820959847",
    "gb:UKR:ADM2:74538382B5714887404176",
    "gb:UKR:ADM2:74538382B72123275564902",
    "gb:UKR:ADM2:74538382B9478118461291",
    "gb:UKR:ADM2:74538382B97249439308301",
])
PARTS = {
    2: "93eeb8f5dab7d8ca6c86593f7ab7b1310312757abcef33d4e7200a270624a1bf",
    19: "baeade0e3ad11cdd65beb101e7b79284ae2b6ee8794f9b08e86631c7f20e6269",
    25: "dada55df1b7f0f2a2b307f4aea071d0e48791e3105875755fe74a292a6763394",
}
SUBJECT_PART = {"BLR": 2, "POL": 19, "UKR": 25}
PRODUCTS_BY_COUNTRY = {"BLR": ("gb:BLR:ADM2", 118), "POL": ("gb:POL:ADM2", 380), "UKR": ("gb:UKR:ADM2", 495)}
MAX_FILE = 32 * 1024 * 1024
MAX_PHASE = 256 * 1024 * 1024


class EvidenceError(RuntimeError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise EvidenceError(message)


def safe_relative(path: Path, root: Path) -> Path:
    """Return a lexical descendant path; reject traversal before filesystem access."""
    rel = Path(os.path.normpath(str(path)))
    if rel.is_absolute() or rel == Path(".") or any(part in ("..", "") for part in rel.parts):
        fail(f"unsafe relative path: {path}")
    root_abs = root.absolute()
    target = root_abs / rel
    try:
        target.relative_to(root_abs)
    except ValueError:
        fail(f"destination escapes owned root: {path}")
    return rel


def check_no_links(path: Path, *, allow_missing: bool = True) -> None:
    """Reject every existing symlink component, including dangling links."""
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current = current / component
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            if not allow_missing:
                fail(f"required path is missing: {current}")
            continue
        if stat.S_ISLNK(mode):
            fail(f"symlink path is not admitted: {current}")


def require_regular(path: Path) -> bytes:
    check_no_links(path, allow_missing=False)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        fail(f"not an ordinary file: {path}")
    if info.st_size > MAX_FILE:
        fail(f"file exceeds 32 MiB cap: {path} ({info.st_size})")
    raw = path.read_bytes()
    if len(raw) != info.st_size:
        fail(f"file changed while read: {path}")
    return raw


def preadmit_fresh(root: Path, relative_files: list[Path]) -> list[Path]:
    """Validate a complete destination set without creating or modifying it."""
    root = root.absolute()
    check_no_links(root)
    if os.path.lexists(root):
        fail(f"fresh namespace already exists: {root}")
    relatives = [safe_relative(p, root) for p in relative_files]
    if len(relatives) != len(set(relatives)):
        fail("duplicate path in complete destination set")
    total = sum(p.stat().st_size for p in relative_files if p.exists())
    if total > MAX_PHASE:
        fail(f"destination phase exceeds 256 MiB cap: {total}")
    for rel in relatives:
        target = root / rel
        check_no_links(target)
        if os.path.lexists(target):
            fail(f"destination already exists: {target}")
    return relatives


def admit_targets(targets: list[Path]) -> None:
    """Pre-admit an exclusive file set inside an existing or not-yet-made root."""
    if len(targets) != len(set(targets)):
        fail("duplicate path in destination set")
    for target in targets:
        check_no_links(target.parent)
        check_no_links(target)
        if os.path.lexists(target):
            fail(f"destination already exists: {target}")


def write_set_exclusive(payloads: dict[Path, bytes]) -> list[dict]:
    """Admit a complete receipt set before writing its first member."""
    admit_targets(list(payloads))
    return [write_exclusive(path, payloads[path]) for path in payloads]


def write_invocation_receipts(payloads: dict[Path, bytes]) -> list[dict]:
    """Admit and exclusively write an invocation receipt set."""
    return write_set_exclusive(payloads)


def write_control_receipts(payloads: dict[Path, bytes]) -> list[dict]:
    """Admit and exclusively write a control receipt set."""
    return write_set_exclusive(payloads)


def write_manifest_receipt(path: Path, raw: bytes) -> dict:
    """Admit the manifest destination before installing its immutable bytes."""
    admit_targets([path])
    return write_exclusive(path, raw)


def preflight_producer_output(output: Path, names: set[str]) -> None:
    if not names or any(Path(name).name != name for name in names):
        fail("producer output inventory must contain plain filenames")
    check_no_links(output)
    targets = [output / name for name in sorted(names)]
    admit_targets(targets)


def mkdir_fresh(path: Path) -> None:
    """Create a directory chain, one non-existing component at a time."""
    path = path.absolute()
    check_no_links(path)
    missing: list[Path] = []
    cursor = path
    while not os.path.lexists(cursor):
        missing.append(cursor)
        cursor = cursor.parent
    if not cursor.is_dir():
        fail(f"existing parent is not a directory: {cursor}")
    for item in reversed(missing):
        item.mkdir()
        if item.is_symlink() or not item.is_dir():
            fail(f"directory creation did not produce an ordinary directory: {item}")


def write_exclusive(path: Path, raw: bytes) -> dict:
    """Write one admitted file with O_EXCL/O_NOFOLLOW and never replace a target."""
    check_no_links(path.parent, allow_missing=False)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o644)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)
    return {"path": path.relative_to(REPO).as_posix(), "bytes": len(raw), "sha256": sha(raw)}


def copy_verified(source: Path, target: Path, expected_size: int | None = None,
                  expected_sha: str | None = None) -> dict:
    raw = require_regular(source)
    if expected_size is not None and len(raw) != expected_size:
        fail(f"whole-file byte count mismatch: {source}")
    if expected_sha is not None and sha(raw) != expected_sha:
        fail(f"whole-file SHA-256 mismatch: {source}")
    return write_exclusive(target, raw)


def copy_input_tree(source_root: Path, target_root: Path,
                    tamper: tuple[Path, int] | None = None) -> tuple[list[dict], dict]:
    _, files = custody_inventory(source_root)
    rels = [rel for rel, _, _ in files] + [Path("source-custody.json")]
    source_bytes = 0
    for rel, expected_size, _ in files:
        source = source_root / rel
        check_no_links(source, allow_missing=False)
        info = source.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size != expected_size or info.st_size > MAX_FILE:
            fail(f"source staging inventory is not admitted: {rel}")
        source_bytes += info.st_size
    custody_path = source_root / "source-custody.json"
    check_no_links(custody_path, allow_missing=False)
    custody_size = custody_path.lstat().st_size
    if custody_size > MAX_FILE:
        fail("source-custody index exceeds 32 MiB")
    source_bytes += custody_size
    stage_code_bytes = len(require_regular(PACKET / "safe_workflow.py"))
    copy_phase = source_bytes * 2 + stage_code_bytes
    if copy_phase > MAX_PHASE:
        fail(f"complete source-staging read/copy phase exceeds 256 MiB: {copy_phase}")
    admission = {"source_input_bytes": source_bytes, "exclusive_staged_copy_bytes": source_bytes,
                 "safe_stage_code_bytes": stage_code_bytes, "complete_phase_bytes": copy_phase,
                 "phase_limit_bytes": MAX_PHASE, "whole_input_file_count": len(rels)}
    preadmit_fresh(target_root, rels)
    mkdir_fresh(target_root)
    copied = [copy_verified(source_root / "source-custody.json", target_root / "source-custody.json",
                            expected_sha=CUSTODY_SHA)]
    for rel, size, expected in files:
        raw = require_regular(source_root / rel)
        if len(raw) != size or sha(raw) != expected:
            fail(f"whole-file custody mismatch before staging: {rel}")
        if tamper and rel == tamper[0]:
            if not raw:
                fail(f"cannot prepare a changed-byte fixture from empty file: {rel}")
            changed = bytearray(raw)
            changed[tamper[1] % len(changed)] ^= 1
            raw = bytes(changed)
        mkdir_fresh((target_root / rel).parent)
        copied.append(write_exclusive(target_root / rel, raw))
    return copied, admission


def custody_inventory(input_root: Path) -> tuple[dict, list[tuple[Path, int, str]]]:
    custody_path = input_root / "source-custody.json"
    custody_raw = require_regular(custody_path)
    if sha(custody_raw) != CUSTODY_SHA:
        fail("pinned source-custody manifest SHA-256 mismatch")
    custody = json.loads(custody_raw)
    if custody.get("baseline_commit") != BASELINE:
        fail("source-custody baseline commit mismatch")
    files: list[tuple[Path, int, str]] = []
    for row in custody.get("files", []):
        rel = Path(row["path"]).relative_to("inputs")
        files.append((rel, int(row["bytes"]), row["sha256"]))
        if row.get("transport_path"):
            tr = Path(row["transport_path"]).relative_to("inputs")
            files.append((tr, int(row["transport_bytes"]), row["transport_sha256"]))
    if len(files) != 33 or len({x[0] for x in files}) != len(files):
        fail(f"unexpected exact source custody inventory: {len(files)} files")
    return custody, files


def verify_inputs(input_root: Path) -> tuple[dict, list[dict]]:
    custody, expected = custody_inventory(input_root)
    expected_paths = {rel.as_posix() for rel, _, _ in expected} | {"source-custody.json"}
    actual_paths = set()
    for path in input_root.rglob("*"):
        check_no_links(path, allow_missing=False)
        if path.is_dir():
            continue
        if not path.is_file():
            fail(f"unexpected non-file input: {path}")
        actual_paths.add(path.relative_to(input_root).as_posix())
    if actual_paths != expected_paths:
        fail(f"input inventory mismatch: missing={sorted(expected_paths-actual_paths)} extra={sorted(actual_paths-expected_paths)}")
    checked = []
    total = 0
    for rel, size, digest in expected:
        raw = require_regular(input_root / rel)
        if len(raw) != size or sha(raw) != digest:
            fail(f"whole-file custody mismatch: {rel}")
        total += len(raw)
        checked.append({"path": rel.as_posix(), "bytes": len(raw), "sha256": digest})
    if total > MAX_PHASE:
        fail(f"complete staged input exceeds 256 MiB cap: {total}")
    return custody, checked


def pinned_git_bytes(commit: str, path: str) -> bytes:
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=REPO,
                            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if len(result.stdout) > MAX_FILE:
        fail(f"pinned file exceeds 32 MiB cap: {path}")
    return result.stdout


def expected_output_descriptors() -> tuple[dict, dict]:
    rel = "research/geography/eastern-europe-border-source-fitness-20261007/runs"
    raw_one = pinned_git_bytes(ORIGINAL_MERGE, f"{rel}/run-one/run-summary.json")
    raw_two = pinned_git_bytes(ORIGINAL_MERGE, f"{rel}/run-two/run-summary.json")
    if sha(raw_one) != RUN_ONE_SUMMARY_SHA or sha(raw_two) != RUN_TWO_SUMMARY_SHA:
        fail("pinned historical run-summary file hash mismatch")
    one, two = json.loads(raw_one), json.loads(raw_two)
    if one != two or one.get("status") != "complete":
        fail("historical complete run summaries differ or are not complete")
    expected = one.get("outputs")
    names = set(expected or {}) | {"run-summary.json"}
    if names != PRODUCTS:
        fail(f"pinned complete output inventory differs from the declared product set: {sorted(names)}")
    return expected, {"run-one": sha(raw_one), "run-two": sha(raw_two)}


def admit_reproduction_phase(inputs: Path, code_dir: Path) -> dict:
    """Bound both runs, decoded inputs, outputs and receipts before computation."""
    _, checked = verify_inputs(inputs)
    raw_bytes = sum(x["bytes"] for x in checked)
    raw_bytes += require_regular(inputs / "source-custody.json").__len__()
    import gzip
    decoded_bytes = 0
    decode_paths = [
        "baseline/candidate-source.gz", "baseline/lakes-source.gz",
        "baseline/physical-component-input.gz", "baseline/numeric-run-one.gz",
        "baseline/numeric-run-two.gz",
    ]
    for rel in decode_paths:
        encoded = require_regular(inputs / rel)
        decoded = gzip.decompress(encoded)
        if len(decoded) > MAX_FILE:
            fail(f"decoded file exceeds 32 MiB cap: {rel}")
        decoded_bytes += len(decoded)
    expected, _ = expected_output_descriptors()
    result_outputs = sum(int(x["bytes"]) for x in expected.values())
    result_outputs += len(pinned_git_bytes(ORIGINAL_MERGE,
        "research/geography/eastern-europe-border-source-fitness-20261007/runs/run-one/run-summary.json"))
    code_bytes = sum(len(require_regular(code_dir / name)) for name in CODE_PINS)
    code_bytes += len(require_regular(PACKET / "safe_workflow.py"))
    # Two complete output inventories and bounded invocation/operation receipts.
    receipts_reserved = 64 * 1024
    phase = raw_bytes + decoded_bytes + code_bytes + 2 * result_outputs + receipts_reserved
    if phase > MAX_PHASE:
        fail(f"complete two-run input/decoded/output phase exceeds 256 MiB: {phase}")
    return {"raw_input_bytes": raw_bytes, "decoded_input_bytes": decoded_bytes,
            "copied_code_bytes": code_bytes, "one_complete_output_bytes": result_outputs,
            "two_run_output_bytes": 2 * result_outputs, "receipt_reserve_bytes": receipts_reserved,
            "complete_phase_bytes": phase, "phase_limit_bytes": MAX_PHASE,
            "input_file_count": len(checked) + 1, "decoded_file_count": len(decode_paths)}


def stage_inputs() -> tuple[Path, list[dict], dict]:
    source_root = ORIGINAL / "inputs"
    target_root = EXEC / "staged-inputs"
    copied, admission = copy_input_tree(source_root, target_root)
    verify_inputs(target_root)
    return target_root, copied, admission


def copy_pinned_code() -> tuple[Path, dict]:
    code_dir = EXEC / "code"
    rels = [Path(name) for name in CODE_PINS]
    preadmit_fresh(code_dir, rels)
    mkdir_fresh(code_dir)
    copied = {}
    for name, expected in CODE_PINS.items():
        raw = require_regular(ORIGINAL / name)
        if sha(raw) != expected:
            fail(f"historically pinned helper changed: {name}")
        copied[name] = write_exclusive(code_dir / name, raw)
    return code_dir, copied


def run_one(name: str, inputs: Path, code_dir: Path, admission: dict) -> dict:
    run_root = EXEC / "runs" / name
    output = run_root / "products"
    receipt = EXEC / "history" / f"{name}-invocation.json"
    summary = EXEC / "history" / "two-run-summary.json"
    # Admit every known output and receipt for this phase before the producer runs.
    destinations = [output / filename for filename in sorted(PRODUCTS)] + [receipt, summary]
    check_no_links(run_root)
    if os.path.lexists(run_root):
        fail(f"run namespace already exists: {run_root}")
    check_no_links(EXEC / "history")
    if not os.path.lexists(EXEC / "history"):
        mkdir_fresh(EXEC / "history")
    mkdir_fresh(run_root)
    preflight_producer_output(output, PRODUCTS)
    for path in [receipt, summary]:
        check_no_links(path)
        if os.path.lexists(path):
            fail(f"run receipt destination already exists: {path}")
    producer = code_dir / "produce.py"
    before = sha(require_regular(producer))
    argv = [sys.executable, "-B", str(producer), "--inputs", str(inputs), "--output", str(output)]
    start = time.time_ns()
    env = {k: v for k, v in os.environ.items() if k not in {"GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN"}}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(argv, cwd=REPO, text=True, capture_output=True, env=env)
    end = time.time_ns()
    after = sha(require_regular(producer))
    outcome = "passed" if proc.returncode == 0 and before == after else "failed"
    row = {
        "version": 1, "run_id": name, "command": ["python", "-B", "produce.py", "--inputs", "execution/staged-inputs", "--output", f"execution/runs/{name}/products"],
        "cwd": "repository root", "started_unix_ns": start, "ended_unix_ns": end,
        "exit_code": proc.returncode, "producer_sha256_before": before,
        "producer_sha256_after": after, "stdout": proc.stdout, "stderr": proc.stderr,
        "outcome": outcome,
    }
    if outcome == "passed":
        inventory = inspect_run(output)
        row["output_inventory"] = inventory
        row["run_summary_sha256"] = sha(require_regular(output / "run-summary.json"))
        row["admission"] = admission
    write_invocation_receipts({receipt: canonical(row)})
    if outcome != "passed":
        fail(f"frozen producer failed in {name}: exit={proc.returncode}; see invocation receipt")
    return row


def inspect_run(output: Path) -> dict:
    check_no_links(output, allow_missing=False)
    actual = {p.name for p in output.iterdir()}
    if actual != PRODUCTS:
        fail(f"complete producer output inventory mismatch at {output}: {sorted(actual)}")
    descriptors = {}
    for name in sorted(PRODUCTS):
        raw = require_regular(output / name)
        descriptors[name] = {"bytes": len(raw), "sha256": sha(raw)}
    summary = json.loads(require_regular(output / "run-summary.json"))
    if summary.get("status") != "complete":
        fail(f"producer summary is not complete: {output}")
    declared = summary.get("outputs")
    expected_declared = PRODUCTS - {"run-summary.json"}
    if not isinstance(declared, dict) or set(declared) != expected_declared:
        fail(f"producer summary inventory mismatch: {output}")
    for name in expected_declared:
        actual_file = descriptors[name]
        row = declared[name]
        if row.get("bytes") != actual_file["bytes"] or row.get("sha256") != actual_file["sha256"]:
            fail(f"producer summary does not bind actual output bytes: {output}/{name}")
    if (summary.get("complete_current_contacts") != 9 or
            summary.get("family_id") != "gap-source-batch:70c8e23708e01b28b207d2e8" or
            summary.get("component_id") != "physical-component:e30c80444254d81f52df404c8a084164b44849c5a93d2abb7fc1212e31b030a8" or
            summary.get("candidate_id") != "physical-gap:1624:42:d40fef6eb0e28f8ab7556c90e2a934b6d2114f155c633c17d324cbf319058184" or
            summary.get("source_products_scanned") != {"BLR": 118, "POL": 380, "UKR": 495} or
            summary.get("source_files_verified") != 33 or
            summary.get("source_custody_sha256") != CUSTODY_SHA):
        fail("actual producer summary lost a pinned family/component/candidate/contact/source inventory binding")
    expected, summary_hashes = expected_output_descriptors()
    for name, expected_row in expected.items():
        if descriptors[name] != {"bytes": expected_row["bytes"], "sha256": expected_row["sha256"]}:
            fail(f"actual output differs from the independently pinned retained product: {output}/{name}")
    run_id = output.parent.name
    if run_id not in summary_hashes or descriptors["run-summary.json"]["sha256"] != summary_hashes[run_id]:
        fail(f"actual run-summary bytes differ from the pinned retained version: {output}")
    return descriptors


def compare_runs() -> dict:
    one = EXEC / "runs/run-one/products"
    two = EXEC / "runs/run-two/products"
    d1, d2 = inspect_run(one), inspect_run(two)
    differing = [name for name in sorted(PRODUCTS) if d1[name] != d2[name]]
    if differing:
        fail(f"actual complete run products differ: {differing}")
    invocations = []
    for name in ("run-one", "run-two"):
        record = json.loads(require_regular(EXEC / "history" / f"{name}-invocation.json"))
        if record.get("outcome") != "passed" or record.get("exit_code") != 0:
            fail(f"invocation is not truthfully successful: {name}")
        if record.get("output_inventory") != (d1 if name == "run-one" else d2):
            fail(f"invocation inventory disagrees with actual files: {name}")
        invocations.append(record)
    return {"status": "passed", "identical": True, "run_one": d1, "run_two": d2,
            "invocation_exit_codes": [x["exit_code"] for x in invocations]}


def build_subject_crosswalk(inputs: Path) -> dict:
    """Rejoin each contract subject to current Atlas and complete source records."""
    part_features: dict[str, list[dict]] = {"BLR": [], "POL": [], "UKR": []}
    for country, (product_key, expected_count) in PRODUCTS_BY_COUNTRY.items():
        part = SUBJECT_PART[country]
        raw = require_regular(inputs / f"baseline/atlas-part-{part}.json")
        if sha(raw) != PARTS[part]:
            fail(f"current subject part pin mismatch: part-{part}")
        collection = json.loads(raw)
        for feature in collection.get("features", []):
            fid = feature.get("id") or feature.get("properties", {}).get("id")
            if fid in SUBJECTS:
                part_features[country].append(feature)

    index = [feature.get("id") for values in part_features.values() for feature in values]
    if len(index) != len(SUBJECTS) or set(index) != set(SUBJECTS) or len(set(index)) != len(index):
        fail("current Atlas subject join is missing, foreign or duplicate")

    registry = json.loads(require_regular(inputs / "baseline/administrative-registry.json"))
    original = json.loads(require_regular(inputs / "baseline/source-corpus-catalogue.json"))
    fitness = json.loads(require_regular(EXEC / "runs/run-one/products/source-fitness.json"))
    contact_comparisons = fitness.get("current_atlas_contact_source_comparisons", [])
    comparisons = {row.get("contact_id"): row for row in contact_comparisons}
    if set(comparisons) != set(SUBJECTS) or len(comparisons) != len(SUBJECTS):
        fail("pinned source fitness result lacks the exact nine-contact comparison set")

    rows = []
    for country, (product_key, expected_count) in PRODUCTS_BY_COUNTRY.items():
        path = inputs / f"source-products/geoBoundaries-{country}-ADM2_simplified.geojson"
        raw = require_regular(path)
        collection = json.loads(raw)
        features = collection.get("features", [])
        shape_ids = [row.get("properties", {}).get("shapeID") for row in features]
        if (collection.get("type") != "FeatureCollection" or len(features) != expected_count or
                any(not isinstance(shape_id, str) or not shape_id for shape_id in shape_ids) or
                len(set(shape_ids)) != len(shape_ids)):
            fail(f"complete source product inventory is invalid: {country}")
        registry_row = registry.get(product_key)
        if registry_row is None or registry_row.get("sha256") != sha(raw) or registry_row.get("admUnitCount") != str(expected_count):
            fail(f"source registry does not bind the exact whole product: {country}")
        corpus_row = next((row for row in original.get("products", []) if row.get("key") == product_key), None)
        if (corpus_row is None or corpus_row.get("original_sha256") != sha(raw) or
                corpus_row.get("original_bytes") != len(raw) or corpus_row.get("feature_count") != expected_count):
            fail(f"source-corpus catalogue does not bind the exact whole product: {country}")
        by_shape = {feature["properties"]["shapeID"]: feature for feature in features}
        for current in part_features[country]:
            props = current.get("properties", {})
            metadata = props.get("metadata", {})
            sid = current["id"]
            shape_id = sid.rsplit(":", 1)[-1]
            matches = [by_shape[shape_id]] if shape_id in by_shape else []
            comparison = comparisons[sid]
            if len(matches) != 1:
                fail(f"native source shapeID join missing or ambiguous: {sid}")
            source = matches[0]
            source_props = source.get("properties", {})
            if (source_props.get("shapeID") != shape_id or
                    sha(canonical(source)) != comparison.get("source_product_feature_sha256") or
                    sha(canonical(current)) != comparison.get("current_atlas_feature_sha256") or
                    comparison.get("current_geometry_equals_simplified_source_topologically") is not False):
                fail(f"complete source/current subject hash or geometry record mismatch: {sid}")
            rows.append({
                "subject_id": sid,
                "current_atlas": {
                    "name": props.get("name"), "parent_id": props.get("parent_id"),
                    "reference_owner": props.get("reference_owner"),
                    "source_id": metadata.get("source_id"), "source_url": metadata.get("source_url"),
                    "reference_year_claim": metadata.get("reference_year"),
                    "administrative_level_claim": metadata.get("administrative_level"),
                    "parent_source_level_claim": metadata.get("parent_source_level"),
                    "parent_match_claim": metadata.get("parent_match"),
                    "full_feature_sha256": sha(canonical(current)),
                },
                "retained_geoBoundaries_product": {
                    "product_key": product_key, "shape_id": shape_id,
                    "shape_name": source_props.get("shapeName"),
                    "shape_type": source_props.get("shapeType"),
                    "shape_group": source_props.get("shapeGroup"),
                    "feature_sha256": sha(canonical(source)),
                    "complete_product_sha256": sha(raw), "complete_product_bytes": len(raw),
                    "complete_feature_count": expected_count,
                    "recorded_represented_year_claim": registry_row.get("boundaryYearRepresented"),
                    "recorded_license_claim": registry_row.get("boundaryLicense"),
                    "recorded_boundary_source_claim": registry_row.get("boundarySource"),
                    "simplified_product_url": registry_row.get("simplifiedGeometryGeoJSON"),
                    "source_parent_unit_id": None,
                    "source_parent_limit": "The complete retained simplified feature stores country shapeGroup and ADM2 shapeType; it does not contain a source ADM1 parent ID.",
                },
                "comparison": {
                    "current_geometry_equals_simplified_source_topologically": False,
                    "current_geometry_type": comparison.get("current_atlas_geometry_type"),
                    "source_geometry_type": comparison.get("source_geometry_type"),
                    "current_source_url_points_to_unsimplified_product": metadata.get("source_url") != registry_row.get("simplifiedGeometryGeoJSON"),
                    "cause_or_correct_geometry": "unresolved",
                },
            })
    rows.sort(key=lambda x: x["subject_id"])
    if len(rows) != len(SUBJECTS):
        fail("complete nine-subject crosswalk was not produced")
    return {"version": 1, "issue": 1515, "scope": {
                "family_id": "gap-source-batch:70c8e23708e01b28b207d2e8",
                "component_id": "physical-component:e30c80444254d81f52df404c8a084164b44849c5a93d2abb7fc1212e31b030a8",
                "candidate_id": "physical-gap:1624:42:d40fef6eb0e28f8ab7556c90e2a934b6d2114f155c633c17d324cbf319058184"},
            "subject_count": len(rows), "source_products": {country: {"key": key, "feature_count": count}
                for country, (key, count) in PRODUCTS_BY_COUNTRY.items()},
            "findings": {"unique_current_id_and_native_shapeID_joins": True,
                         "all_nine_current_geometries_topologically_equal_to_simplified_source": False,
                         "source_vintage_and_parent_roles_are_metadata_claims": True,
                         "legal_boundary_physical_class_and_correct_geometries": "unresolved"},
            "subjects": rows}


def write_final_receipts(comparison: dict) -> list[dict]:
    controls = EXEC / "controls"
    if not os.path.lexists(controls):
        mkdir_fresh(controls)
    positive_path = controls / "positive-control.json"
    reproducibility_path = controls / "reproducibility.json"
    summary_path = EXEC / "history/two-run-summary.json"
    aggregate = sha(canonical(comparison["run_one"]))
    full = {"version": 1, **comparison, "producer_sha256": CODE_PINS["produce.py"],
            "python": platform.python_version(), "platform": platform.platform()}
    positive = {"version": 1, "method_id": "frozen-producer", "kind": "positive-control", "outcome": "passed",
                "scope": {"family_id": "gap-source-batch:70c8e23708e01b28b207d2e8",
                          "component_id": "physical-component:e30c80444254d81f52df404c8a084164b44849c5a93d2abb7fc1212e31b030a8",
                          "candidate_id": "physical-gap:1624:42:d40fef6eb0e28f8ab7556c90e2a934b6d2114f155c633c17d324cbf319058184",
                          "contact_count": 9}, "actual_comparison": comparison}
    reproducibility = {"version": 1, "method_id": "frozen-producer", "kind": "reproducibility",
                       "outcome": "passed", "actual_products_equal": True,
                       "run_one_sha256": aggregate, "run_two_sha256": sha(canonical(comparison["run_two"])),
                       "actual_product_inventory": comparison["run_one"]}
    receipts = write_set_exclusive({summary_path: canonical(full), positive_path: canonical(positive),
                                    reproducibility_path: canonical(reproducibility)})
    return receipts


def comparison_probe(name: str, mutate: str) -> dict:
    probe_root = EXEC / "comparison-probes" / name
    d1 = probe_root / "run-one" / "products"
    d2 = probe_root / "run-two" / "products"
    rel_files = [Path("run-one/products") / x for x in PRODUCTS] + [Path("run-two/products") / x for x in PRODUCTS]
    preadmit_fresh(probe_root, rel_files)
    mkdir_fresh(probe_root)
    for source, dest in ((EXEC / "runs/run-one/products", d1), (EXEC / "runs/run-two/products", d2)):
        mkdir_fresh(dest)
        for name_file in PRODUCTS:
            copy_verified(source / name_file, dest / name_file)
    touched = d2 / "source-fitness.json"
    if mutate == "change-real-row":
        value = json.loads(require_regular(touched))
        row = value["country_overlays"]["BLR"]
        row["positive_area_intersection_features"] = 987654
        payload = canonical(value)
        touched.unlink()
        write_exclusive(touched, payload)
    elif mutate == "remove-product":
        touched.unlink()
    elif mutate == "false-summary-status":
        p = d2 / "run-summary.json"
        value = json.loads(require_regular(p)); value["status"] = "failed"
        p.unlink(); write_exclusive(p, canonical(value))
    try:
        left, right = inspect_run(d1), inspect_run(d2)
        if left != right:
            fail(f"probe actual product inventories differ: {name}")
        observed = "accepted"
    except EvidenceError as exc:
        observed = "rejected"
        reason = str(exc)
    expected = "rejected"
    if observed != expected:
        fail(f"comparison probe was falsely accepted: {name}")
    return {"case": name, "mutation": mutate, "observed": observed, "expected": expected,
            "reason": reason, "original_summary_hash_preserved": mutate == "change-real-row"}


def writer_self_tests() -> list[dict]:
    import tempfile
    results = []
    with tempfile.TemporaryDirectory(prefix="writer-probes-", dir=EXEC) as temp:
        root = Path(temp)
        for writer in ("stage", "producer", "invocation", "control", "manifest"):
            case = root / writer
            case.mkdir()
            nested = case / "nested"
            nested.mkdir()
            sentinel = nested / "sentinel.json"
            original = b"preserve-this-sentinel\n"
            write_exclusive(sentinel, original)
            existing = nested / "existing.json"
            write_exclusive(existing, b"occupied\n")
            dangling = nested / "dangling.json"
            dangling.symlink_to(nested / "absent-target.json")
            redirected = case / "redirected"
            redirected.mkdir()
            outside_sentinel = redirected / "sentinel.json"
            write_exclusive(outside_sentinel, b"preserve-outside-sentinel\n")
            link_ancestor = case / "linked-ancestor"
            link_ancestor.symlink_to(redirected, target_is_directory=True)
            through_link = link_ancestor / "new.json"
            probes = []
            for kind, hazard in (("existing-file", existing), ("dangling-target", dangling),
                                 ("linked-ancestor", through_link)):
                fresh = nested / "new.json"
                try:
                    if writer == "stage":
                        target = {"existing-file": case / "occupied-stage",
                                  "dangling-target": case / "dangling-stage",
                                  "linked-ancestor": link_ancestor / "stage"}[kind]
                        if kind == "existing-file":
                            target.mkdir(); write_exclusive(target / "sentinel.json", original)
                        elif kind == "dangling-target":
                            target.symlink_to(case / "absent-stage", target_is_directory=True)
                        copy_input_tree(ORIGINAL / "inputs", target)
                    elif writer == "producer":
                        output = case / f"producer-output-{kind}"
                        if kind == "existing-file":
                            output.mkdir(); write_exclusive(output / "source-fitness.json", b"occupied\n")
                        elif kind == "dangling-target":
                            output.mkdir(); (output / "source-fitness.json").symlink_to(case / "absent-product")
                        else:
                            output = link_ancestor / "products"
                        preflight_producer_output(output, PRODUCTS)
                    elif writer == "invocation":
                        write_invocation_receipts({fresh: b"new-value\n", hazard: b"must-not-write\n"})
                    elif writer == "control":
                        write_control_receipts({fresh: b"new-value\n", hazard: b"must-not-write\n"})
                    else:
                        target = {"existing-file": existing, "dangling-target": dangling,
                                  "linked-ancestor": through_link}[kind]
                        write_manifest_receipt(target, b"must-not-write\n")
                    outcome, reason = "accepted", ""
                except EvidenceError as exc:
                    outcome, reason = "rejected", str(exc)
                if fresh.exists():
                    fail(f"writer {writer} wrote a new member before rejecting its unsafe destination")
                probes.append({"case": kind, "outcome": outcome, "reason": reason})
            if any(x["outcome"] != "rejected" for x in probes):
                fail(f"writer {writer} admitted an occupied destination")
            if (sentinel.read_bytes() != original or existing.read_bytes() != b"occupied\n" or
                outside_sentinel.read_bytes() != b"preserve-outside-sentinel\n"):
                fail(f"writer {writer} changed a preservation sentinel")
            results.append({"writer": writer, "probes": probes, "sentinels_unchanged": True})
    return results


def actual_producer_control(name: str, inputs: Path, code_dir: Path,
                            arguments: list[str], expected_reason: str,
                            admission: dict) -> dict:
    attempt = EXEC / "controls/producer-negatives" / name
    output = attempt / "products"
    check_no_links(attempt)
    if os.path.lexists(attempt):
        fail(f"negative-control namespace already exists: {attempt}")
    check_no_links(output)
    if os.path.lexists(output):
        fail(f"negative-control output destination already exists: {output}")
    mkdir_fresh(attempt)
    preflight_producer_output(output, PRODUCTS)
    argv = [sys.executable, "-B", str(code_dir / "produce.py"), "--inputs", str(inputs),
            "--output", str(output), *arguments]
    env = {k: v for k, v in os.environ.items() if k not in {"GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN"}}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(argv, cwd=REPO, text=True, capture_output=True, env=env)
    try:
        observed = json.loads(proc.stderr.splitlines()[0])
    except (IndexError, json.JSONDecodeError):
        observed = {"status": "unparseable", "reason": proc.stderr[:1200]}
    passed = proc.returncode != 0 and observed.get("status") == "rejected" and expected_reason in observed.get("reason", "")
    if os.path.lexists(output):
        files = sorted(p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file())
    else:
        files = []
    return {"case": name, "exit_code": proc.returncode, "observed": observed,
            "expected_reason_contains": expected_reason, "created_product_paths": files,
            "admission": admission, "outcome": "passed" if passed else "failed"}


def run_negative_controls(input_root: Path, code_dir: Path) -> dict:
    fixture_root = EXEC / "controls/fixtures"
    if not os.path.lexists(fixture_root):
        mkdir_fresh(fixture_root)
    candidate_gz = require_regular(input_root / "baseline/candidate-source.gz")
    import gzip
    candidates = json.loads(gzip.decompress(candidate_gz))["features"]
    candidate_id = "physical-gap:1624:42:d40fef6eb0e28f8ab7556c90e2a934b6d2114f155c633c17d324cbf319058184"
    matches = [x for x in candidates if x.get("id") == candidate_id]
    if len(matches) != 1:
        fail("pinned candidate feature is not unique in the complete candidate source")
    candidate = matches[0]
    admission = admit_reproduction_phase(input_root, code_dir)
    geometry_path = fixture_root / "candidate-geometry.json"
    metadata_path = fixture_root / "candidate-contact-metadata.json"
    geometry = json.loads(json.dumps(candidate))
    geometry["geometry"]["coordinates"][0][0][0] += 0.000001
    metadata = json.loads(json.dumps(candidate))
    point = metadata["properties"]["exact_location_contacts"][0]["geometry"]["coordinates"][0][0]
    point[0] += 0.000001
    for path, value in ((geometry_path, geometry), (metadata_path, metadata)):
        admit_targets([path])
        write_exclusive(path, canonical(value))
    cases = [
        actual_producer_control("missing-contact", input_root, code_dir,
                                ["--control", "omit-contact"], "candidate contact roster missing", admission),
        actual_producer_control("duplicate-contact", input_root, code_dir,
                                ["--control", "duplicate-contact"], "duplicate candidate contact ID", admission),
        actual_producer_control("foreign-subject", input_root, code_dir,
                                ["--control", "foreign-subject"], "candidate contact roster missing or foreign", admission),
        actual_producer_control("candidate-geometry-change", input_root, code_dir,
                                ["--candidate-override", str(geometry_path)], "candidate full feature binding mismatch", admission),
        actual_producer_control("candidate-contact-metadata-change", input_root, code_dir,
                                ["--candidate-override", str(metadata_path)], "candidate full feature binding mismatch", admission),
    ]
    tampered_inputs = EXEC / "controls/tampered-inputs"
    _, tamper_stage_admission = copy_input_tree(input_root, tampered_inputs,
                    (Path("source-products/geoBoundaries-BLR-ADM2_simplified.geojson"), 566102))
    changed_input = tampered_inputs / "source-products/geoBoundaries-BLR-ADM2_simplified.geojson"
    original_input = input_root / "source-products/geoBoundaries-BLR-ADM2_simplified.geojson"
    raw_before, raw_after = require_regular(original_input), require_regular(changed_input)
    if len(raw_before) != len(raw_after) or raw_before == raw_after:
        fail("changed-source fixture did not alter exactly one byte while preserving its length")
    cases.append(actual_producer_control("changed-source-byte", tampered_inputs, code_dir, [],
                                         "whole-file custody mismatch", admission))
    if any(c["outcome"] != "passed" for c in cases):
        fail("one or more actual producer negative controls did not reject the expected input")
    return {"version": 1, "kind": "negative-control", "outcome": "passed", "controls": cases,
            "tampered_input_staging_admission": tamper_stage_admission,
            "tampered_source": {"path": "source-products/geoBoundaries-BLR-ADM2_simplified.geojson",
                                "bytes": len(raw_after), "original_sha256": sha(raw_before),
                                "changed_sha256": sha(raw_after), "changed_byte_offset": 566102}}


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fresh", action="store_true", help="stage exact inputs, copy pinned code and execute two runs")
    mode.add_argument("--controls", action="store_true", help="run actual producer negatives and positive-output tamper probes")
    parser.add_argument("--workspace", default="execution", help="fresh directory under this owned packet")
    args = parser.parse_args()
    global EXEC
    EXEC = PACKET / safe_relative(Path(args.workspace), PACKET)
    if args.fresh:
        check_no_links(EXEC)
        if os.path.lexists(EXEC):
            fail(f"execution namespace already exists; choose a fresh --workspace: {EXEC}")
        input_root, staged, stage_admission = stage_inputs()
        code_dir, code = copy_pinned_code()
        admission = admit_reproduction_phase(input_root, code_dir)
        a = run_one("run-one", input_root, code_dir, admission)
        b = run_one("run-two", input_root, code_dir, admission)
        compared = compare_runs()
        crosswalk = build_subject_crosswalk(input_root)
        crosswalk_path = EXEC / "subject-bindings.json"
        write_exclusive(crosswalk_path, canonical(crosswalk))
        receipts = write_final_receipts(compared)
        result = {"status": "passed", "staged_input_count": len(staged), "staged_input_bytes": sum(x["bytes"] for x in staged),
                  "stage_admission": stage_admission,
                  "code": code, "runs": [a, b], "comparison": compared, "subject_crosswalk": {"path": crosswalk_path.relative_to(PACKET).as_posix(), "subject_count": crosswalk["subject_count"], "sha256": sha(require_regular(crosswalk_path))}, "receipts": receipts}
        path = EXEC / "fresh-execution.json"
        if os.path.lexists(path): fail("fresh-execution receipt already exists")
        write_exclusive(path, canonical(result))
        print(json.dumps({"status": "passed", "staged_input_count": len(staged), "runs": 2,
                          "output_files_per_run": len(PRODUCTS), "identical": compared["identical"],
                          "complete_phase_bytes": admission["complete_phase_bytes"]}, sort_keys=True))
    elif args.controls:
        check_no_links(EXEC, allow_missing=False)
        if not EXEC.is_dir():
            fail(f"execution workspace is not a directory: {EXEC}")
        input_root = EXEC / "staged-inputs"
        code_dir = EXEC / "code"
        _, checked = verify_inputs(input_root)
        actual = run_negative_controls(input_root, code_dir)
        actual["method_id"] = "frozen-producer"
        out_actual = EXEC / "controls/producer-negative-control.json"
        write_control_receipts({out_actual: canonical(actual)})
        results = writer_self_tests()
        results += [comparison_probe("altered-actual-row", "change-real-row"),
                    comparison_probe("missing-actual-product", "remove-product"),
                    comparison_probe("false-actual-run-summary", "false-summary-status")]
        out = EXEC / "controls/writer-and-comparison-controls.json"
        write_control_receipts({out: canonical({"version": 1, "method_id": "safe-writers", "kind": "negative-control", "outcome": "passed", "staged_input_files": len(checked), "cases": results})})
        print(json.dumps({"status": "passed", "producer_negative_cases": len(actual["controls"]), "writer_and_comparison_cases": len(results)}, sort_keys=True))
    else:
        parser.error("choose --fresh or --controls")


if __name__ == "__main__":
    try:
        main()
    except EvidenceError as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
