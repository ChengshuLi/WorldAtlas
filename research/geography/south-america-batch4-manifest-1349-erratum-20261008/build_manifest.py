#!/usr/bin/env python3
"""Build a scope-bound correction manifest and publish its success marker last."""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/south-america-batch4-manifest-1349-erratum-20261008/"
SOURCE_OWNED = "research/geography/south-america-batch4-validator-integrity-erratum-2026/"
BASELINE = "e9190786dbf758524a3bde513fc4bb4d1ed6a3e7"
PACKET_COMMIT = "5fa15de475f17ff93e205b767857d1e41a30949e"
ISSUE_1506 = 1506
WORKER_ID = "01a10947-b3d7-7812-8b2f-c5a47e88ccb2"
ISSUE_SNAPSHOT = OWNED + "issue-1506-contract.json"
ACCEPTED_SNAPSHOT = SOURCE_OWNED + "issue-1332-contract.json"
OLD_MANIFEST = SOURCE_OWNED + "evidence-quality.json"
HELPER = "scripts/evidence/immutable.py"
HELPER_SHA256 = "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46"
ACCEPTED_SNAPSHOT_SHA256 = "70e61fad77bb6b93376821cbe8b7c8c73439eac95ede07a45784758400ae23f6"
OUTPUTS = [OWNED + "reproducibility.json", OWNED + "preservation.json", OWNED + "evidence-quality.json"]
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_PHASE_BYTES = 256 * 1024 * 1024
OUTPUT_RESERVE = 1024 * 1024
RUNTIME_RESERVE = 64 * 1024
RUN_FILES = ["audit.json", "positive-control.json", "negative-control.json",
             "child-roster-controls.json", "execution-bindings.json",
             "legacy-writer-control.json", "run-metadata.json", "publication.json"]
COMPARE_FILES = [name for name in RUN_FILES if name not in ("run-metadata.json", "publication.json")]
RUN_NAMES = ("run-eleven", "run-twelve")
PRESERVED_RUN_NAMES = ("run-seven", "run-eight", "run-nine", "run-ten")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def safe_rel(value):
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        raise ValueError("Unsafe repository path")
    p = PurePosixPath(value)
    if p.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError("Unsafe repository path")
    return value


def no_symlink_path(relative, *, allow_missing_leaf=False):
    relative = safe_rel(relative)
    target = ROOT / relative
    current = ROOT
    if current.is_symlink():
        raise ValueError("Repository root may not be a symlink")
    parts = PurePosixPath(relative).parts
    for index, part in enumerate(parts):
        current = current / part
        if current.is_symlink():
            raise ValueError("Symlink in evidence path: " + relative)
        if index < len(parts) - 1 and current.exists() and not current.is_dir():
            raise ValueError("Non-directory evidence ancestor: " + relative)
    if not allow_missing_leaf and (not current.exists() or not current.is_file()):
        raise ValueError("Expected ordinary file: " + relative)
    return current


def pre_admit_outputs(manifest_path, repro_path):
    if manifest_path != OWNED + "evidence-quality.json" or repro_path != OWNED + "reproducibility.json":
        raise ValueError("Output paths must remain inside the exact issue-owned directory")
    root = no_symlink_path(OWNED.rstrip("/"), allow_missing_leaf=True)
    if not root.exists() or not root.is_dir():
        raise ValueError("Owned output root is not an ordinary directory")
    for relative in OUTPUTS:
        target = no_symlink_path(relative, allow_missing_leaf=True)
        if target.exists() or target.is_symlink():
            raise FileExistsError("Complete output set is not fresh; refusing all writes: " + relative)


def git_bytes(commit, path):
    safe_rel(path)
    return subprocess.check_output(["git", "-C", str(ROOT), "show", commit + ":" + path], stderr=subprocess.PIPE)


def git_tree(commit, prefix):
    raw = subprocess.check_output(["git", "-C", str(ROOT), "ls-tree", "-r", "-z", commit, "--", prefix.rstrip("/")], stderr=subprocess.PIPE)
    rows = []
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        meta, path_raw = entry.split(b"\t", 1)
        mode, kind, blob = meta.decode().split()
        path = path_raw.decode()
        safe_rel(path)
        if mode not in ("100644", "100755") or kind != "blob":
            raise ValueError("Historical packet contains a symlink or non-file: " + path)
        rows.append({"path": path, "mode": mode, "blob": blob, "commit": commit})
    return rows


def load_helper(helper_bytes):
    if sha(helper_bytes) != HELPER_SHA256:
        raise ValueError("Pinned immutable helper changed")
    module = types.ModuleType("worldatlas_immutable_captured")
    module.__file__ = str(ROOT / HELPER)
    exec(compile(helper_bytes, module.__file__, "exec"), module.__dict__)
    return module


def contract_ids(raw):
    if sha(raw) != ACCEPTED_SNAPSHOT_SHA256:
        raise ValueError("Accepted immutable #1332 snapshot hash differs")
    snapshot = json.loads(raw)
    issue = snapshot.get("issue", {})
    if issue.get("issue_number") != 1332 or issue.get("state") != "open":
        raise ValueError("Captured accepted #1332 issue state differs")
    m = re.search(r"<!-- worldatlas-work:v1\s*([\s\S]*?)\s*-->", issue.get("body", ""))
    if not m:
        raise ValueError("Accepted #1332 issue contract is absent")
    spec = json.loads(m.group(1))
    if spec.get("mode") != "geography" or spec.get("max_prs") != 1 or spec.get("owned_paths") != [SOURCE_OWNED]:
        raise ValueError("Accepted #1332 lane, PR budget or ownership differs")
    ids = spec.get("evidence_quality", {}).get("subject_ids", [])
    if len(ids) != 215 or len(set(ids)) != 215:
        raise ValueError("Accepted #1332 scope is not exactly 215 unique subjects")
    return ids


def candidate_bytes(path, size_admit):
    target = no_symlink_path(path)
    size = target.stat().st_size
    if size > MAX_FILE_BYTES:
        raise ValueError("Candidate file exceeds 32 MiB: " + path)
    size_admit(path, size)
    raw = target.read_bytes()
    if len(raw) != size:
        raise ValueError("Candidate changed during read: " + path)
    return raw


def run_summary(name, root, ids, inputs):
    docs = {}
    for filename in RUN_FILES:
        path = root + filename
        docs[filename] = inputs[path]
    receipt = json.loads(docs["publication.json"])
    expected = set(RUN_FILES[:-1])
    rows = receipt.get("outputs", [])
    if receipt.get("version") != 1 or receipt.get("status") != "complete" or len(rows) != len(expected):
        raise ValueError("Run has no complete exact output receipt: " + name)
    actual_rows = {}
    for row in rows:
        path = safe_rel(row.get("path"))
        if not path.startswith(root) or Path(path).name not in expected or Path(path).name in actual_rows:
            raise ValueError("Run receipt inventory/path mismatch: " + name)
        actual = docs[Path(path).name]
        if row.get("bytes") != len(actual) or row.get("sha256") != sha(actual):
            raise ValueError("Run receipt does not bind whole output bytes: " + path)
        actual_rows[Path(path).name] = path
    if set(actual_rows) != expected:
        raise ValueError("Run receipt omits or adds a result: " + name)
    audit = json.loads(docs["audit.json"])
    for filename, kind in (("positive-control.json", "positive-control"),
                            ("negative-control.json", "negative-control"),
                            ("child-roster-controls.json", "negative-control"),
                            ("legacy-writer-control.json", "negative-control")):
        control = json.loads(docs[filename])
        if control.get("method_id") != "south-america-batch4-manifest-1349-erratum" or control.get("kind") != kind or control.get("outcome") != "passed":
            raise ValueError("Fresh producer control does not bind the #1506 method: " + root + filename)
    subject_rows = audit.get("subject_rows", [])
    found = [row.get("subject_id") for row in subject_rows]
    digest = sha(json.dumps(sorted(ids), separators=(",", ":")).encode())
    if len(found) != 215 or len(set(found)) != 215 or set(found) != set(ids):
        raise ValueError("Generated run identities do not exactly match accepted contract: " + name)
    if audit.get("subject_count") != 215 or audit.get("subject_ids_sha256") != digest:
        raise ValueError("Generated run subject digest/count mismatch: " + name)
    if audit.get("parent_count") != 39 or len(audit.get("parent_rosters", [])) != 39:
        raise ValueError("Generated run does not contain all 39 exact parent joins: " + name)
    if audit.get("area_count") != 5 or len(audit.get("areas", [])) != 5:
        raise ValueError("Generated run does not contain all five inherited areas: " + name)
    metadata = json.loads(docs["run-metadata.json"])
    if metadata.get("producer_sha256") != sha(INPUTS[OWNED + "reproduce.py"]):
        raise ValueError("Fresh run does not bind the exact consumed producer bytes: " + name)
    if metadata.get("immutable_helper_sha256") != HELPER_SHA256:
        raise ValueError("Fresh run does not bind the exact pinned helper bytes: " + name)
    if metadata.get("issue_snapshot_sha256") != ACCEPTED_SNAPSHOT_SHA256 or metadata.get("baseline_commit") != BASELINE:
        raise ValueError("Fresh run metadata does not bind the immutable scope/baseline: " + name)
    hashes = {filename: sha(docs[filename]) for filename in COMPARE_FILES}
    return {"name": name, "root": root, "audit": audit, "receipt": receipt, "metadata": metadata,
            "metadata_sha256": sha(docs["run-metadata.json"]), "publication_sha256": sha(docs["publication.json"]),
            "hashes": hashes, "paths": actual_rows}


def make_output_rows(input_paths, repro_raw, preservation_raw):
    rows = []
    for path, role in input_paths:
        raw = REPRO_BYTES if path == OWNED + "reproducibility.json" else preservation_raw if path == OWNED + "preservation.json" else None
        if raw is None:
            raw = INPUTS[path]
        row = {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}
        if role:
            row["role"] = role
        rows.append(row)
    # Reproducibility is calculated during this run, before either destination is written.
    repro = {"path": OWNED + "reproducibility.json", "bytes": len(repro_raw), "sha256": sha(repro_raw), "hash_kind": "file-bytes", "role": "two fresh run comparison"}
    preservation = {"path": OWNED + "preservation.json", "bytes": len(preservation_raw), "sha256": sha(preservation_raw), "hash_kind": "file-bytes", "role": "historical file/mode preservation receipt"}
    by_path = {row["path"]: row for row in rows}
    by_path[repro["path"]] = repro
    by_path[preservation["path"]] = preservation
    return [by_path[path] for path in sorted(by_path)]


# The dict is initialized by build() after all candidate files have been admitted.
INPUTS = {}
REPRO_BYTES = b""


def build(*, manifest_path=None, repro_path=None, fault_after_first=False):
    manifest_path = manifest_path or OWNED + "evidence-quality.json"
    repro_path = repro_path or OWNED + "reproducibility.json"
    # Every final path is admitted before reading a body or calculating a result.
    pre_admit_outputs(manifest_path, repro_path)

    # Read only Git metadata first. Prove the complete input/decoded/output reserve
    # fits before loading any indexed body or running a comparison.
    prior_raw = git_bytes(PACKET_COMMIT, OLD_MANIFEST)
    prior_hash = sha(prior_raw)
    if prior_hash != "cbab3413a6808f7dd3e06389b235f782ef2363a109b9397ebbc3d5ec8bc45aac":
        raise ValueError("Original #1332 manifest pin changed")
    prior = json.loads(prior_raw)
    packet_rows = git_tree(PACKET_COMMIT, SOURCE_OWNED)
    baseline_specs = prior.get("baseline", {}).get("files", [])
    if not baseline_specs:
        raise ValueError("Original manifest lacks its whole baseline inventory")
    commit_rows = []
    sizes = {}
    for row in baseline_specs:
        path = safe_rel(row["path"])
        metadata = subprocess.check_output(["git", "-C", str(ROOT), "ls-tree", "-z", BASELINE, "--", path], stderr=subprocess.PIPE)
        if not metadata:
            raise ValueError("Baseline path absent from immutable evaluation commit: " + path)
        blob_row = metadata.split(b"\0", 1)[0]
        mode_data, _ = blob_row.split(b"\t", 1)
        mode, kind, blob = mode_data.decode().split()
        if mode not in ("100644", "100755") or kind != "blob":
            raise ValueError("Baseline input is not a regular Git blob: " + path)
        size = int(subprocess.check_output(["git", "-C", str(ROOT), "cat-file", "-s", blob], text=True).strip())
        if size > MAX_FILE_BYTES:
            raise ValueError("Baseline input exceeds 32 MiB: " + path)
        sizes["baseline:" + path] = size
        commit_rows.append({**row, "commit": BASELINE})
    for row in packet_rows:
        path = row["path"]
        size = int(subprocess.check_output(["git", "-C", str(ROOT), "cat-file", "-s", row["blob"]], text=True).strip())
        if size > MAX_FILE_BYTES:
            raise ValueError("Historical packet file exceeds 32 MiB: " + path)
        sizes["historical:" + path] = size
        sizes["candidate:" + path] = size
    output_static = [OWNED + name for name in ("README.md", "issue-1506-contract.json", "claim-receipt.json",
                     "initial-run-routing-control.json", "reproduce.py", "build_manifest.py",
                     "verify_controls.py", "cli-controls.json")]
    output_static.extend(OWNED + "controls/failed-first-builder/" + name for name in
                         ("evidence-quality.json", "preservation.json", "reproducibility.json"))
    output_static.extend(OWNED + "controls/failed-second-builder/" + name for name in
                         ("evidence-quality.json", "preservation.json", "reproducibility.json"))
    output_static.extend(OWNED + "controls/failed-third-builder/" + name for name in
                         ("evidence-quality.json", "preservation.json", "reproducibility.json"))
    output_static.extend(OWNED + "controls/failed-fourth-builder/" + name for name in
                         ("evidence-quality.json", "preservation.json", "reproducibility.json"))
    output_static.extend([OWNED + "controls/first-builder-rejection.json",
                          OWNED + "controls/second-builder-rejection.json",
                          OWNED + "controls/third-builder-rejection.json",
                          OWNED + "controls/fourth-builder-rejection.json",
                          OWNED + "controls/first-control-receipt.json",
                          OWNED + "controls/second-control-receipt.json",
                          OWNED + "controls/third-control-receipt.json",
                          OWNED + "controls/fourth-control-receipt.json"])
    output_candidate = list(output_static)
    for run in (*PRESERVED_RUN_NAMES, *RUN_NAMES):
        root = OWNED + "vintages/" + run + "/"
        output_candidate.extend(root + filename for filename in RUN_FILES)
    for path in output_candidate:
        target = no_symlink_path(path)
        size = target.stat().st_size
        if size > MAX_FILE_BYTES:
            raise ValueError("Candidate output/input exceeds 32 MiB: " + path)
        sizes["candidate:" + path] = size
    output_targets = [OWNED + "reproducibility.json", OWNED + "preservation.json", OWNED + "evidence-quality.json"]
    complete = sum(sizes.values()) + OUTPUT_RESERVE + RUNTIME_RESERVE
    if complete > MAX_PHASE_BYTES:
        raise ValueError("Complete raw input, output and runtime reserve exceeds 256 MiB")

    # Authenticate the exact helper after byte admission; consume captured pinned bytes.
    helper_raw = git_bytes(BASELINE, HELPER)
    if sha(helper_raw) != HELPER_SHA256:
        raise ValueError("Immutable helper hash differs from pinned issue value")
    helper_path = no_symlink_path(HELPER)
    if helper_path.read_bytes() != helper_raw:
        raise ValueError("Actually imported helper differs from authenticated bytes")
    immutable = load_helper(helper_raw)
    baseline = immutable.Baseline(str(ROOT), BASELINE, baseline_specs)
    accepted_raw = git_bytes(PACKET_COMMIT, ACCEPTED_SNAPSHOT)
    if sha(accepted_raw) != ACCEPTED_SNAPSHOT_SHA256:
        raise ValueError("Accepted contract snapshot no longer matches its whole pin")
    ids = contract_ids(accepted_raw)
    issue_raw = candidate_bytes(ISSUE_SNAPSHOT.rstrip("/"), lambda p, n: baseline.admit("candidate:" + p, n))
    issue_capture = json.loads(issue_raw)
    issue = issue_capture.get("issue", issue_capture)
    if issue.get("number", issue.get("issue_number")) != ISSUE_1506 or issue.get("state") != "open":
        raise ValueError("Current #1506 issue snapshot does not bind an open issue")
    marker = re.search(r"<!-- worldatlas-work:v1\s*([\s\S]*?)\s*-->", issue.get("body", ""))
    if not marker:
        raise ValueError("Current #1506 issue contract is absent")
    contract = json.loads(marker.group(1))
    if contract.get("mode") != "geography" or contract.get("max_prs") != 1 or contract.get("owned_paths") != [OWNED]:
        raise ValueError("Current #1506 issue lane, budget or owned scope changed")
    current_ids = contract.get("evidence_quality", {}).get("subject_ids", [])
    if len(current_ids) != 215 or len(set(current_ids)) != 215 or set(current_ids) != set(ids):
        raise ValueError("The accepted 215 IDs differ from current #1506 exact scope")

    # Capture all historical packet bytes/modes, verify the working tree preserves
    # the exact commit, and admit all consumed bodies before any result calculation.
    global INPUTS, REPRO_BYTES
    INPUTS = {}
    preservation = []
    for row in packet_rows:
        path, mode = row["path"], row["mode"]
        committed = git_bytes(PACKET_COMMIT, path)
        target = no_symlink_path(path)
        actual = target.read_bytes()
        if actual != committed or target.stat().st_size != len(committed):
            raise ValueError("Historical #1332 packet differs from its original bytes: " + path)
        file_mode = "100755" if (stat.S_IMODE(target.stat().st_mode) & 0o111) else "100644"
        if file_mode != mode:
            raise ValueError("Historical #1332 packet mode changed: " + path)
        baseline.admit("historical:" + path, len(committed))
        baseline.admit("candidate:" + path, len(actual))
        preservation.append({"path": path, "commit": PACKET_COMMIT, "mode": mode,
                             "bytes": len(committed), "sha256": sha(committed)})
    for path in output_candidate:
        raw = candidate_bytes(path, lambda p, n: baseline.admit("candidate:" + p, n))
        INPUTS[path] = raw
    preservation_raw = canonical({"version": 1, "packet_commit": PACKET_COMMIT,
                                   "original_file_count": len(preservation), "files": preservation,
                                   "result": "all original packet bytes and Git modes match the immutable #1332 merge tree"})
    # The complete index is authenticated and scanned before metrics or reports are calculated.
    features, containing = baseline.subjects(ids)
    if len(features) != 215 or len(containing) != 215:
        raise ValueError("Immutable complete index does not resolve every accepted subject")
    # One bounded actual-source inventory is admitted. These source files are
    # inherited evidence; this job performs no new geographic source verification.
    actual_inputs = sum(baseline.consumed.values())
    if actual_inputs + OUTPUT_RESERVE + RUNTIME_RESERVE > MAX_PHASE_BYTES:
        raise ValueError("Consumed inputs leave insufficient admitted output/runtime reserve")

    runs = {}
    for run in RUN_NAMES:
        root = OWNED + "vintages/" + run + "/"
        for filename in RUN_FILES:
            path = root + filename
            if path not in INPUTS:
                raise ValueError("Fresh run output was not admitted: " + path)
        runs[run] = run_summary(run, root, ids, INPUTS)
    one, two = (runs[name] for name in RUN_NAMES)
    if one["hashes"] != two["hashes"]:
        raise ValueError("Fresh run calculation products differ")
    for result in runs.values():
        if result["metadata"].get("vintage") != result["name"]:
            raise ValueError("Fresh run metadata does not name its actual vintage")
    if one["metadata_sha256"] == two["metadata_sha256"]:
        raise ValueError("Fresh run metadata must differ by actual run")
    one_digest = sha(json.dumps(one["hashes"], sort_keys=True, separators=(",", ":")).encode())
    two_digest = sha(json.dumps(two["hashes"], sort_keys=True, separators=(",", ":")).encode())
    repro = {"method_id": "south-america-batch4-manifest-1349-erratum", "kind": "reproducibility", "outcome": "passed",
             "comparison_policy": "Compare all six deterministic calculation/control outputs byte-for-byte; retain each fresh run's distinct metadata and publication receipt.",
             "run_one": {"vintage": one["name"], "outputs": one["hashes"], "metadata_sha256": one["metadata_sha256"], "publication_sha256": one["publication_sha256"]},
             "run_two": {"vintage": two["name"], "outputs": two["hashes"], "metadata_sha256": two["metadata_sha256"], "publication_sha256": two["publication_sha256"]},
             "run_one_sha256": one_digest, "run_two_sha256": two_digest,
             "equal_deterministic_product_digest": one_digest == two_digest, "run_metadata_differ": True,
             "producer_sha256": sha(INPUTS[OWNED + "reproduce.py"]),
             "immutable_helper_sha256": HELPER_SHA256,
             "builder_sha256": sha(INPUTS[OWNED + "build_manifest.py"]),
             "total_input_bytes": actual_inputs, "reserved_output_bytes": OUTPUT_RESERVE,
             "runtime": {"python": sys.version.split()[0], "implementation": sys.implementation.name, "platform": platform.platform()},
             "method_note": "Each fresh producer run admitted 214,557,427 whole input/fixture/output bytes, wrote seven outputs and published its complete receipt last."}
    REPRO_BYTES = canonical(repro)

    prior = json.loads(git_bytes(PACKET_COMMIT, OLD_MANIFEST))
    previous_baseline = prior["baseline"]
    baseline_rows = [{**row, "commit": BASELINE} for row in previous_baseline["files"]]
    baseline_rows.extend({"path": row["path"], "commit": PACKET_COMMIT, "bytes": row["bytes"],
                          "sha256": row["sha256"], "hash_kind": "file-bytes"} for row in preservation)
    if len({(row["path"], row["commit"]) for row in baseline_rows}) != len(baseline_rows):
        raise ValueError("Duplicate historical baseline path/commit descriptor")
    if len({row["path"] for row in baseline_rows}) != len(baseline_rows):
        raise ValueError("Repeated historical paths need explicit references; no ambiguity is permitted")
    pins = dict(previous_baseline["pins"])
    pin_files = {name: {"path": path, "commit": BASELINE} for name, path in previous_baseline["pin_files"].items()}
    issue_pins = contract.get("evidence_quality", {}).get("pins", {})
    for path, expected in sorted(issue_pins.items()):
        record = next((row for row in preservation if row["path"] == path), None)
        if record is None or record["sha256"] != expected:
            raise ValueError("Issue-declared historical pin changed: " + path)
        pins[path] = expected
        pin_files[path] = {"path": path, "commit": PACKET_COMMIT}
    subject_files = {identity: {"path": binding["path"], "commit": BASELINE} for identity, binding in containing.items()}

    new_paths = []
    static = [(OWNED + name, role) for name, role in [
        ("README.md", "scope, methods and limits"), ("issue-1506-contract.json", "retrieved GitHub work contract"),
        ("claim-receipt.json", "serialized reservation receipt"), ("initial-run-routing-control.json", "preserved and restored path-routing control"),
        ("reproduce.py", "actual fresh producer CLI"), ("build_manifest.py", "corrected manifest builder CLI"),
        ("verify_controls.py", "reproducible legacy and corrected builder CLI controls"),
        ("cli-controls.json", "whole-hash receipts for actual CLI positive/adverse controls")]]
    static.extend((OWNED + "controls/failed-first-builder/" + name, "preserved schema-rejected first builder draft")
                  for name in ("evidence-quality.json", "preservation.json", "reproducibility.json"))
    static.extend((OWNED + "controls/failed-second-builder/" + name, "preserved metric-binding-rejected second builder draft")
                  for name in ("evidence-quality.json", "preservation.json", "reproducibility.json"))
    static.extend((OWNED + "controls/failed-third-builder/" + name, "preserved issue-pin-binding-rejected third builder draft")
                  for name in ("evidence-quality.json", "preservation.json", "reproducibility.json"))
    static.extend((OWNED + "controls/failed-fourth-builder/" + name, "preserved control-receipt-rejected fourth builder draft")
                  for name in ("evidence-quality.json", "preservation.json", "reproducibility.json"))
    static.extend([(OWNED + "controls/first-builder-rejection.json", "validator failure receipt for retained first draft"),
                   (OWNED + "controls/second-builder-rejection.json", "validator failure receipt for retained second draft"),
                   (OWNED + "controls/third-builder-rejection.json", "trusted baseline pin-binding failure receipt for retained third draft"),
                   (OWNED + "controls/fourth-builder-rejection.json", "trusted control-envelope failure receipt for retained fourth draft"),
                   (OWNED + "controls/first-control-receipt.json", "superseded initial exact CLI control run"),
                   (OWNED + "controls/second-control-receipt.json", "superseded second exact CLI control run"),
                   (OWNED + "controls/third-control-receipt.json", "superseded third exact CLI control run"),
                   (OWNED + "controls/fourth-control-receipt.json", "superseded fourth exact CLI control run")])
    for run in PRESERVED_RUN_NAMES:
        root = OWNED + "vintages/" + run + "/"
        role = "retained run with inherited #1332 method labels; not used as accepted control evidence" if run in ("run-nine", "run-ten") else "preserved earlier fresh producer evidence"
        static.extend((root + name, role) for name in RUN_FILES)
    for run in RUN_NAMES:
        root = OWNED + "vintages/" + run + "/"
        static.extend((root + name, "fresh generated producer evidence with exact code bindings") for name in RUN_FILES)
    static.extend([(OWNED + "preservation.json", "preserved original file/mode inventory"),
                   (OWNED + "reproducibility.json", "two-run complete output comparison")])
    static.append((OWNED + "evidence-quality.json", "completion manifest"))
    static.sort()
    for path, role in static:
        safe_rel(path)
        new_paths.append((path, role))
    output_rows = []
    for path, role in new_paths:
        if path == OWNED + "evidence-quality.json":
            continue
        raw = REPRO_BYTES if path == OWNED + "reproducibility.json" else preservation_raw if path == OWNED + "preservation.json" else INPUTS[path]
        output_rows.append({"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes", "role": role})
    output_rows.sort(key=lambda row: row["path"])

    audit_path = OWNED + "vintages/run-eleven/audit.json"
    positive_path = OWNED + "vintages/run-eleven/positive-control.json"
    negative_path = OWNED + "vintages/run-eleven/negative-control.json"
    audit = runs["run-eleven"]["audit"]
    positive = json.loads(INPUTS[positive_path])
    negative = json.loads(INPUTS[negative_path])
    metrics = [
        ("exact_issue_subjects", audit["subject_count"], "subjects", audit_path, "/subject_count"),
        ("distinct_retained_province_parents", audit["parent_count"], "parents", audit_path, "/parent_count"),
        ("raw_child_ids_independently_checked", positive["child_id_tokens"], "child IDs", positive_path, "/child_id_tokens"),
        ("inherited_area_records_checked", audit["area_count"], "areas", audit_path, "/area_count"),
        ("adverse_controls_rejected", negative["controls_executed"], "controls", negative_path, "/controls_executed"),
    ]
    output_lookup = {row["path"]: row for row in output_rows}
    metric_rows, summaries, bindings = [], [], []
    for metric_id, value, unit, path, pointer in metrics:
        metric_rows.append({"id": metric_id, "value": value, "unit": unit, "vintage": "baseline",
                            "evaluation_commit": BASELINE, "input_sha256": output_lookup[path]["sha256"],
                            "input_file": {"path": path, "commit": "candidate"}})
        summaries.append({"metric_id": metric_id, "value": value, "unit": unit})
        bindings.append({"metric_id": metric_id, "path": path, "json_pointer": pointer})

    sources = list(prior.get("sources", []))
    sources.append({"id": "github-issue-1506", "url": "https://github.com/ChengshuLi/WorldAtlas/issues/1506",
        "role": "current additive work scope, exact subject roster and historical source pins", "vintage": issue.get("updated_at", "2026-10-08"),
        "retrieved_at": issue_capture.get("retrieved_at", "2026-10-08"),
        "license": {"status": "unknown", "terms": "GitHub issue text is retained as task evidence; content reuse is not evaluated by this packet."},
        "retention": "restoration-only", "restoration": "Read " + ISSUE_SNAPSHOT + " or retrieve the issue through the connected GitHub API.",
        "verification": "verified", "temporal_status": "unknown", "limit": "The issue defines code/evidence acceptance only; it is not an authoritative geography source."})
    sources = sorted({row["id"]: row for row in sources}.values(), key=lambda row: row["id"])
    inherited_limits = list(prior.get("limits", []))
    limits = sorted(set(inherited_limits + [
        "No geoBoundaries original geometry or upstream feature row was acquired, retained or reverified.",
        "The original 2022 Paraguay INE response bytes, response-level reuse terms and statistical-to-administrative relation remain unverified.",
        "Candidate source IDs, vintages, tier labels, names and license strings remain inherited observations, not fresh source certification.",
        "Chile ADM3, Paraguay ADM2 and the Asunción aggregate are neighboring candidate granularities; equivalence, adjacency and complete neighboring coverage are not established.",
        "The retained Atlas subject index proves only exact stored identity and parent links; it does not prove current administrative truth.",
        "Original #935/#948/#1120 evidence, source hashes, rows and history are referenced read-only at their committed historical vintages.",
        "The first local manifest draft used an unsupported run-name metric vintage and was rejected by the evidence validator; its exact three files are retained under controls/failed-first-builder/ and excluded from the accepted top-level outputs.",
        "The second local manifest draft lacked explicit candidate input paths for repeated whole-file metric hashes and was rejected by the evidence validator; its exact three files are retained under controls/failed-second-builder/ and excluded from the accepted top-level outputs.",
        "The third manifest draft used generated pin keys instead of the exact issue-declared paths and failed the trusted hosted evidence contract; its exact files and hosted failure are retained under controls/failed-third-builder/ and excluded from the accepted top-level outputs.",
        "The fourth manifest draft referenced inherited producer controls whose method_id still named #1332, so the trusted control receipt check rejected them; its exact files and hosted failure are retained under controls/failed-fourth-builder/ and excluded from accepted outputs.",
        "Runs nine and ten retain useful generated rows/receipts and exact producer/helper hashes, but their inherited control method labels are retained as an explicitly nonaccepted vintage; only fresh run-eleven/run-twelve controls bind this repair method.",
        "This packet establishes a bounded builder custody repair only; it does not complete original #1120 or certify geographic approval, source rights, imports or publication."
    ]))
    manifest = {
        "version": 1, "issue": ISSUE_1506, "lane": "geography", "worker_id": WORKER_ID,
        "subject_ids": ids, "subject_ids_sha256": sha(json.dumps(sorted(ids), separators=(",", ":")).encode()),
        "baseline": {"version": 2, "commit": BASELINE, "files": baseline_rows, "pins": pins,
                     "pin_files": pin_files, "subject_files": subject_files},
        "sources": sources, "outputs": output_rows,
        "methods": [{"id": "south-america-batch4-manifest-1349-erratum", "kind": "generator",
            "helper_version": "worldatlas-evidence-preparation-v1",
            "description": "Run the documented producer twice, authenticate the accepted immutable scope and exact consumed code/index/products, reconcile all 215 generated IDs and 39/5 joins, and atomically admit all builder output destinations before calculation.",
            "software": "Python 3.12.14 standard library; captured pinned scripts/evidence/immutable.py; Git object reads only; no network or credentials during reproduction",
            "units": "retained Atlas subject identities and parent/area records; no new geographic claims"}],
        "metrics": metric_rows, "summaries": summaries, "metric_bindings": bindings,
        "validation": [
            {"method_id": "south-america-batch4-manifest-1349-erratum", "kind": "positive-control", "outcome": "passed", "evidence_path": positive_path},
            {"method_id": "south-america-batch4-manifest-1349-erratum", "kind": "negative-control", "outcome": "passed", "evidence_path": negative_path},
            {"method_id": "south-america-batch4-manifest-1349-erratum", "kind": "reproducibility", "outcome": "passed", "evidence_path": OWNED + "reproducibility.json"}],
        "change_receipts": [{"path": path, "status": "added"} for path in sorted([row["path"] for row in output_rows] + [OWNED + "evidence-quality.json"])],
        "conclusions": [
            {"text": "The current #1506 exact 215-ID scope equals the whole accepted #1332 snapshot and every identity in both fresh run-eleven/run-twelve producer audits; the 36-part pinned index resolves all subjects.", "status": "supported", "source_ids": ["github-issue-1332", "github-issue-1506", "worldatlas-baseline-e919"]},
            {"text": "Both fresh producer runs retain 39 exact parent joins and five inherited area records, with all six deterministic calculation/control files identical and per-run metadata/receipts distinct.", "status": "supported", "source_ids": ["github-issue-1506", "worldatlas-baseline-e919"]},
            {"text": "The original #1349 manifest builder and prior 65-file packet remain byte/mode-preserved at their immutable merge commit; source authority, legal parentage, geometry, currency, completeness, neighboring granularity and reuse terms remain unresolved.", "status": "unresolved", "source_ids": ["github-issue-1332", "github-issue-1506", "worldatlas-baseline-e919"]}
        ],
        "stages": {"research": "complete", "implementation": "proposed", "geographic_approval": "unapproved"},
        "commands": [
            "PYTHONDONTWRITEBYTECODE=1 python3.12 -B " + OWNED + "reproduce.py --vintage run-eleven",
            "PYTHONDONTWRITEBYTECODE=1 python3.12 -B " + OWNED + "reproduce.py --vintage run-twelve",
            "PYTHONDONTWRITEBYTECODE=1 python3.12 -B " + OWNED + "verify_controls.py",
            "PYTHONDONTWRITEBYTECODE=1 python3.12 -B " + OWNED + "build_manifest.py",
            "node scripts/evidence-quality.mjs " + OWNED + "evidence-quality.json"],
        "limits": limits
    }
    manifest_raw = canonical(manifest)
    outputs_raw = {OWNED + "reproducibility.json": REPRO_BYTES,
                   OWNED + "preservation.json": preservation_raw,
                   OWNED + "evidence-quality.json": manifest_raw}
    actual_output_bytes = sum(len(raw) for raw in outputs_raw.values())
    if any(len(raw) > MAX_FILE_BYTES for raw in outputs_raw.values()):
        raise ValueError("Final output exceeds the 32 MiB per-file cap")
    if actual_inputs + actual_output_bytes + RUNTIME_RESERVE > MAX_PHASE_BYTES:
        raise ValueError("Complete consumed inputs, decoded outputs and runtime exceed 256 MiB")
    generated_output_paths = {OWNED + "reproducibility.json", OWNED + "preservation.json"}
    if sum(row["bytes"] for row in output_rows if row["path"] in generated_output_paths) != actual_output_bytes - len(manifest_raw):
        raise ValueError("Output inventory byte accounting differs")
    # Revalidate consumed inputs and the entire destination set immediately before
    # first write. The success manifest is the final hard-linked output.
    for name, spec in baseline.pins.items():
        baseline.pinned_bytes(name)
    for path, expected in INPUTS.items():
        if no_symlink_path(path).read_bytes() != expected:
            raise ValueError("Consumed input/code drifted during manifest construction: " + path)
    pre_admit_outputs(manifest_path, repro_path)
    atomic_exclusive_write(OWNED + "reproducibility.json", REPRO_BYTES)
    if fault_after_first:
        raise RuntimeError("Controlled publication failure after first output; no success manifest was published")
    atomic_exclusive_write(OWNED + "preservation.json", preservation_raw)
    atomic_exclusive_write(OWNED + "evidence-quality.json", manifest_raw)
    print(json.dumps({"status": "complete", "issue": ISSUE_1506, "subjects": len(ids),
        "baseline_files": len(baseline_rows), "preserved_original_files": len(preservation),
        "input_bytes": actual_inputs, "output_bytes": actual_output_bytes,
        "outputs": {path: sha(raw) for path, raw in outputs_raw.items()}}, indent=2, sort_keys=True))


def atomic_exclusive_write(path, raw):
    target = no_symlink_path(path, allow_missing_leaf=True)
    target.parent.mkdir(parents=False, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".manifest-repair-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        # Hard-link install is exclusive; a collision never overwrites a sentinel.
        os.link(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-path", default=OWNED + "evidence-quality.json")
    parser.add_argument("--repro-path", default=OWNED + "reproducibility.json")
    parser.add_argument("--test-fail-after-first-output", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.test_fail_after_first_output and os.environ.get("WORLDATLAS_ENABLE_TEST_FAULT") != "1":
        raise ValueError("Fault injection is limited to an explicit isolated control run")
    build(manifest_path=args.manifest_path, repro_path=args.repro_path,
          fault_after_first=args.test_fail_after_first_output)


if __name__ == "__main__":
    main()
