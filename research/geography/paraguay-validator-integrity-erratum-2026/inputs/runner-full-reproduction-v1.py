#!/usr/bin/env python3
"""Reproduce the original Paraguay validator safely and test the erratum gates.

The legacy entry point is executed unchanged against immutable Git blobs. Its
three historical output writes are intercepted in memory and published only to
fresh exclusive vintages through the current shared NewVintage helper.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/paraguay-validator-integrity-erratum-2026/"
ISSUE_SNAPSHOT = ROOT / OWNED / "inputs/issue-1330-api-2026-10-09.json"
ISSUE_BODY_SHA = "eae266406120f9c4c09d4d83c7123bc99db39abb13a31fb4b58f386afa3b0b97"
ISSUE_FILE_SHA = "e16236853d527aeeaa6d9e3414d38ec10cc0529b9af8dde4697fe88b206eb6ae"
BASELINE = "27be77596f23304de6a720735538427e6d23e242"
CURRENT = "913486d0df285012e470cd670c097d5e4344de3a"
OLD = "data/regional-review/regional-review-afee7ce9a5601ab2/"
VALIDATION = "data/regional-review/southern-south-america-crosswalk-validation-20261006/"
ISSUE_1111_PATH = VALIDATION + "source/issue-1111-api-2026-10-06.json"
VALIDATOR = VALIDATION + "validate_crosswalk.py"
HELPER = "scripts/evidence/immutable.py"
VALIDATOR_SHA = "f48a8842db54fa963c573152d889b648a9a15928be4eb99c84463ae6199093cf"
OLD_HELPER_SHA = "b7ff607b7774595788396e94f08fc29d750e4032624eb93732a5735c1ddcf7fd"
CURRENT_HELPER_SHA = "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46"
ISSUE_1111_SHA = "ec35fa800c4887b7f023457fc8f22fcfae5d185d647fc961dd4900f634d76c9d"
OUTPUT_PATHS = [
    VALIDATION + "expected-crosswalk-map.json",
    VALIDATION + "verification-results.json",
    VALIDATION + "adversarial-controls.json",
]
PREVIOUS_OUTPUT_SHA = {
    OUTPUT_PATHS[0]: "ef020da017210735ee4d1b4cce450f58367af56beff5c2d6c989af7c4d3232ce",
    OUTPUT_PATHS[1]: "8eff680dfc1393a1b831e2f3110b16cc3a308c1303f1a8b1ef92a255194938cc",
    OUTPUT_PATHS[2]: "ffb12802823dc5f247181a0fb20b3143eab9f0a3d56769b538477a26546180ba",
}


class EvidenceError(ValueError):
    pass


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{commit}:{path}"], stderr=subprocess.PIPE
    )


def json_bytes(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def file_descriptor(path: str, raw: bytes, commit: str | None = None) -> dict:
    item = {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}
    if commit:
        item["commit"] = commit
    return item


def require(condition: bool, message: str):
    if not condition:
        raise EvidenceError(message)


def verify_contract():
    raw = ISSUE_SNAPSHOT.read_bytes()
    require(sha(raw) == ISSUE_FILE_SHA, "Saved issue API snapshot changed")
    snapshot = json.loads(raw)
    issue = snapshot.get("issue", snapshot)
    require(issue.get("number") == 1330, "Issue snapshot number differs")
    body = issue.get("body", "")
    require(sha(body.encode()) == ISSUE_BODY_SHA, "Issue #1330 acceptance body changed")
    match = re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", body, re.S)
    require(match is not None, "Issue machine contract is absent")
    contract = json.loads(match.group(1))
    require(contract.get("mode") == "geography", "Wrong work lane")
    require(contract.get("owned_paths") == [OWNED], "Owned-path declaration changed")
    require(contract.get("depends_on") == [1111], "Issue dependency changed")
    require(contract.get("max_prs") == 1, "PR allowance changed")
    return issue, contract


def load_exact_helper(raw: bytes, expected_sha: str, commit: str):
    require(sha(raw) == expected_sha, f"Immutable helper hash mismatch at {commit}")
    module = types.ModuleType("evidence.immutable")
    module.__file__ = str(ROOT / HELPER)
    module.__package__ = "evidence"
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    package = types.ModuleType("evidence")
    package.__path__ = [str(ROOT / "scripts/evidence")]
    package.__package__ = "evidence"
    sys.modules["evidence"] = package
    sys.modules["evidence.immutable"] = module
    return module


def strict_parent_rosters(unit_raw: bytes, parent_raw: bytes, scope_raw: bytes, features: dict):
    scope = json.loads(scope_raw)
    subject_ids = scope.get("member_location_ids")
    parent_scope = scope.get("province_scopes")
    require(isinstance(subject_ids, list) and len(subject_ids) == 215 and len(set(subject_ids)) == 215,
            "Independent reference scope must contain 215 unique units")
    require(isinstance(parent_scope, list) and len(parent_scope) == 32, "Independent parent scope must have 32 rows")
    expected_parents = [row.get("id") for row in parent_scope]
    require(all(isinstance(x, str) and x for x in expected_parents) and len(set(expected_parents)) == 32,
            "Independent parent scope contains blank or repeated IDs")
    ureader = csv.DictReader(io.StringIO(unit_raw.decode("utf-8-sig"), newline=""))
    preader = csv.DictReader(io.StringIO(parent_raw.decode("utf-8-sig"), newline=""))
    unit_headers, parent_headers = ureader.fieldnames, preader.fieldnames
    require(unit_headers == ["id", "name", "parent_id", "reference_owner", "source_id", "source_name", "source_url", "source_vintage", "source_role", "license", "geometry_type", "native_source_id", "scope_area", "parent_name", "review_status", "evidence_note", "baseline_file", "original_geometry_sha256", "acceptance_disposition", "disposition_basis"],
            "Unit ledger has missing, duplicated or reordered columns")
    require(parent_headers == ["parent_id", "parent_name", "scope_area", "scoped_child_count", "acceptance_disposition", "evidence_basis", "source_limit", "scoped_child_ids"],
            "Parent ledger has missing, duplicated or reordered columns")
    units, parents = list(ureader), list(preader)
    unit_ids = [row.get("id") for row in units]
    require(len(units) == 215 and all(isinstance(x, str) and x for x in unit_ids) and len(set(unit_ids)) == 215,
            "Unit rows contain blank/duplicate IDs or wrong count")
    require(set(unit_ids) == set(subject_ids), "Unit rows differ from the independent exact 215 scope")
    expected_parent_set = set(expected_parents)
    expected_parent_names = {row["id"]: row.get("original_name") or row.get("name") for row in parent_scope}
    grouped: dict[str, set[str]] = {}
    for row in units:
        fid, parent_id = row.get("id"), row.get("parent_id")
        require(parent_id in expected_parent_set, f"Foreign unit parent: {fid}")
        feature = features.get(fid)
        require(feature is not None, f"Unit is absent from immutable features: {fid}")
        props = feature.get("properties") or {}
        require(row.get("name") == props.get("name") and parent_id == props.get("parent_id"),
                f"Unit identity/name/parent mismatch: {fid}")
        grouped.setdefault(parent_id, set()).add(fid)
    require(set(grouped) == expected_parent_set, "Unit rows do not cover exact independent parent set")
    parent_ids = [row.get("parent_id") for row in parents]
    require(len(parents) == 32 and all(isinstance(x, str) and x for x in parent_ids)
            and len(set(parent_ids)) == 32 and set(parent_ids) == expected_parent_set,
            "Parent rows contain blank/duplicate IDs or wrong exact scope")
    for row in parents:
        parent_id = row["parent_id"]
        raw_children = row.get("scoped_child_ids")
        require(isinstance(raw_children, str) and raw_children != "", f"Blank roster: {parent_id}")
        tokens = raw_children.split("|")
        require(all(token != "" and token.strip() == token for token in tokens), f"Blank/malformed child token: {parent_id}")
        require(len(tokens) == len(set(tokens)), f"Repeated raw child token: {parent_id}")
        expected = grouped[parent_id]
        require(set(tokens) == expected, f"Missing/substituted/foreign child: {parent_id}")
        count = row.get("scoped_child_count", "")
        require(re.fullmatch(r"0|[1-9][0-9]*", count) is not None and int(count) == len(expected),
                f"Declared child count mismatch: {parent_id}")
        require(row.get("parent_name") == expected_parent_names[parent_id],
                f"Parent name mismatch: {parent_id}")
    return {"units": len(units), "parents": len(parents), "raw_children_unique": True}


def run_legacy_entrypoint(validator_raw: bytes, helper_raw: bytes):
    require(sha(validator_raw) == VALIDATOR_SHA, "Validator code differs from issue pin")
    require(sha(helper_raw) == OLD_HELPER_SHA, "Captured original helper differs from historical pin")
    namespace = {"__name__": "__main__", "__file__": str(ROOT / VALIDATOR), "__package__": None}
    before = Path.write_text
    captured: dict[str, bytes] = {}

    def capture_write(path, data, *args, **kwargs):
        try:
            rel = path.resolve().relative_to(ROOT).as_posix()
        except Exception as exc:
            raise EvidenceError(f"Unplanned legacy output path: {path}") from exc
        if rel not in OUTPUT_PATHS or rel in captured or not isinstance(data, str):
            raise EvidenceError(f"Unexpected or repeated legacy output write: {rel}")
        encoding = kwargs.get("encoding") or "utf-8"
        captured[rel] = data.encode(encoding)
        return len(data)

    Path.write_text = capture_write
    try:
        load_exact_helper(helper_raw, OLD_HELPER_SHA, BASELINE)
        sys.path.insert(0, str(ROOT / "scripts"))
        exec(compile(validator_raw, str(ROOT / VALIDATOR), "exec"), namespace)
    finally:
        Path.write_text = before
    require(set(captured) == set(OUTPUT_PATHS), "Legacy entry point did not produce all three outputs")
    return captured, namespace


def run_claimed_full_reproduction(run_name: str, helper_current, issue, contract, input_facts):
    validator_raw = git_bytes(CURRENT, VALIDATOR)
    old_helper = git_bytes(BASELINE, HELPER)
    current_helper_raw = git_bytes(CURRENT, HELPER)
    issue_1111 = git_bytes(CURRENT, ISSUE_1111_PATH)
    require(sha(validator_raw) == VALIDATOR_SHA, "Current validator bytes differ from bound issue pin")
    require(sha(old_helper) == OLD_HELPER_SHA, "Original helper vintage differs from bound issue pin")
    require(sha(current_helper_raw) == CURRENT_HELPER_SHA, "Current shared helper differs from current-main pin")
    require(sha(issue_1111) == ISSUE_1111_SHA, "Consumed #1111 snapshot differs from preserved pin")
    outputs, namespace = run_legacy_entrypoint(validator_raw, old_helper)
    # The committed v1 packet remains untouched; compare every original product
    # against its prior whole-file digest before writing only to a new vintage.
    for path in OUTPUT_PATHS:
        original = git_bytes(CURRENT, path)
        require(sha(original) == PREVIOUS_OUTPUT_SHA[path], f"Preserved original product changed: {path}")
        require(sha(outputs[path]) == PREVIOUS_OUTPUT_SHA[path], f"Full original run differs bytewise: {path}")
    map_doc = json.loads(outputs[OUTPUT_PATHS[0]])
    result_doc = json.loads(outputs[OUTPUT_PATHS[1]])
    controls_doc = json.loads(outputs[OUTPUT_PATHS[2]])
    mapping_rows = map_doc.get("rows", [])
    source_ids = [row.get("source_shape_id") for row in mapping_rows]
    native_rows = [row for row in mapping_rows if row.get("mapping_type") == "individual native location"]
    aggregate_rows = [row for row in mapping_rows if row.get("mapping_type") == "member of atlas aggregate"]
    require(len(mapping_rows) == 247 and len(set(source_ids)) == 247 and all(source_ids),
            "Reproduced source map does not contain exactly 247 unique source IDs")
    require(len(native_rows) == 241 and len(aggregate_rows) == 6,
            "Reproduced native/aggregate source joins differ from the original evidence")
    require(len({row.get("atlas_location_id") for row in mapping_rows}) == 243,
            "Reproduced source map does not contain exactly 243 target identities")
    require(result_doc.get("exact_issue_subject_count") == 263 and result_doc.get("scope_unit_count") == 215
            and result_doc.get("scope_parent_count") == 32 and result_doc.get("source_record_count") == 247
            and result_doc.get("issue_scope_union_matches") is True,
            "Reproduced crosswalk report disagrees with the exact issue scope counts/union")
    require(len(controls_doc.get("controls", [])) == 12 and controls_doc.get("all_passed") is True,
            "Original reproduction did not retain all twelve successful controls")
    # The actual scope validator is called independently after the original
    # module-level entry point, using the unaltered source records it consumed.
    scope_raw = git_bytes(BASELINE, OLD + "scope.json")
    unit_raw = git_bytes(BASELINE, OLD + "unit-review.csv")
    parent_raw = git_bytes(BASELINE, OLD + "parent-review.csv")
    issue_snap = json.loads(issue_1111)
    contract_match = re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", issue_snap.get("body", ""), re.S)
    require(contract_match is not None, "Preserved #1111 snapshot has no evidence contract")
    subject_ids = json.loads(contract_match.group(1))["evidence_quality"]["subject_ids"]
    features = namespace["feature_lookup"](subject_ids)[1]
    roster = strict_parent_rosters(unit_raw, parent_raw, scope_raw, features)
    closure = list(input_facts)
    by_sha = {}
    for entry in closure:
        by_sha.setdefault(entry["sha256"], entry["bytes"])
    # Count unique byte-identical Git blobs once across historical commits.
    input_unique = sum(by_sha.values())
    receipt = {
        "version": 1,
        "run": run_name,
        "entrypoint": VALIDATOR,
        "entrypoint_sha256": sha(validator_raw),
        "runtime": {"python": sys.version, "platform": sys.platform},
        "issue_snapshot": file_descriptor(str(ISSUE_SNAPSHOT.relative_to(ROOT)), ISSUE_SNAPSHOT.read_bytes()),
        "issue_body_sha256": ISSUE_BODY_SHA,
        "issue_1111_snapshot": file_descriptor(OLD + "source/issue-1111-api-2026-10-06.json", issue_1111, CURRENT),
        "consumed_helper": {"path": HELPER, "commit": BASELINE, "bytes": len(old_helper), "sha256": sha(old_helper), "execution": "captured immutable bytes supplied to actual legacy import"},
        "current_output_helper": {"path": HELPER, "commit": CURRENT, "bytes": len(current_helper_raw), "sha256": sha(current_helper_raw)},
        "input_files": sorted(closure, key=lambda x: (x.get("commit", ""), x["path"])),
        "unique_raw_content_bytes": input_unique,
        "raw_file_cap_bytes": 33554432,
        "phase_cap_bytes": 268435456,
        "retained_products": {path: {"bytes": len(raw), "sha256": sha(raw), "byte_identical_to_original": True} for path, raw in sorted(outputs.items())},
        "reconciled_counts": {"subjects": 263, "units": 215, "parents": 32, "source_mappings": 247, "native_mappings": 241, "aggregate_members": 6, "distinct_targets": 243, "original_controls": 12},
        "parent_roster_reconciliation": roster,
        "geographic_status": "Integrity reproduction only; legal boundaries, current legal identity, source authority and geographic approval are not established.",
    }
    filenames = [Path(path).name for path in OUTPUT_PATHS] + ["run-receipt.json"]
    baseline = helper_current["evidence.immutable"].Baseline(ROOT, CURRENT, [file_descriptor(HELPER, current_helper_raw)])
    for digest, size in sorted(by_sha.items()):
        baseline.admit("captured-input-" + digest, size)
    baseline.admit("issue-snapshot-1330", len(ISSUE_SNAPSHOT.read_bytes()))
    receipt_raw = json_bytes(receipt)
    payloads = {Path(path).name: outputs[path] for path in OUTPUT_PATHS}
    payloads["run-receipt.json"] = receipt_raw
    publisher = helper_current["evidence.immutable"].NewVintage(baseline, OWNED, run_name, filenames)
    records = publisher.publish_bytes(payloads)
    return receipt, records, namespace, outputs


def encode_csv(headers, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def strict_control(namespace, unit_raw, parent_raw, scope_raw, subject_ids):
    original_index = json.loads(git_bytes(BASELINE, OLD + "packet-index.json"))
    original_sha = {x["path"]: x for x in original_index["files"]}
    ph, parents = namespace["csv_rows"](parent_raw)
    uh, units = namespace["csv_rows"](unit_raw)
    features = namespace["feature_lookup"](subject_ids)[1]
    tests = []

    def reject(label, altered):
        try:
            strict_parent_rosters(unit_raw, altered, scope_raw, features)
        except EvidenceError as exc:
            tests.append({"id": label, "outcome": "rejected", "reason": str(exc)})
            return
        raise EvidenceError("Strict raw-roster control was accepted: " + label)

    # Demonstrate the original defect through both original gates: coherent
    # candidate packet hashes pass, then the legacy raw-token-to-set validator
    # accepts the altered parent roster. The strict erratum rejects it.
    first = dict(parents[0])
    tokens = first["scoped_child_ids"].split("|")
    require(tokens, "Fixture parent has no children")
    dup_rows = [dict(x) for x in parents]
    dup_rows[0]["scoped_child_ids"] = "|".join(tokens + [tokens[0]])
    dup_raw = encode_csv(ph, dup_rows)
    dup_index = json.loads(json.dumps(original_index))
    target = next(x for x in dup_index["files"] if x["path"] == OLD + "parent-review.csv")
    target.update(bytes=len(dup_raw), sha256=sha(dup_raw))
    namespace["audit_candidate_packet"](json.dumps(dup_index).encode(), {OLD + "parent-review.csv": dup_raw}, original_index)
    namespace["validate_unit_parent_ledgers"](unit_raw, dup_raw, scope_raw, features)
    tests.append({"id": "legacy-rehashed-duplicate-raw-child-accepted", "outcome": "observed", "raw_token_count": len(tokens) + 1, "unique_child_count": len(set(tokens)), "legacy_gate": "accepted after coherent candidate packet rehash"})
    reject("duplicate-raw-child-token", dup_raw)

    blank_rows = [dict(x) for x in parents]
    blank_rows[0]["scoped_child_ids"] += "|"
    blank_raw = encode_csv(ph, blank_rows)
    blank_index = json.loads(json.dumps(original_index))
    target = next(x for x in blank_index["files"] if x["path"] == OLD + "parent-review.csv")
    target.update(bytes=len(blank_raw), sha256=sha(blank_raw))
    namespace["audit_candidate_packet"](json.dumps(blank_index).encode(), {OLD + "parent-review.csv": blank_raw}, original_index)
    namespace["validate_unit_parent_ledgers"](unit_raw, blank_raw, scope_raw, features)
    tests.append({"id": "legacy-rehashed-blank-child-accepted", "outcome": "observed", "legacy_gate": "accepted after coherent candidate packet rehash"})
    reject("blank-raw-child-token", blank_raw)

    duplicate_parent = encode_csv(ph, [*parents, dict(parents[0])])
    reject("duplicate-parent-row", duplicate_parent)
    missing_rows = [dict(x) for x in parents]
    missing_rows[0]["scoped_child_ids"] = "|".join(tokens[1:])
    reject("missing-child", encode_csv(ph, missing_rows))
    substitute_rows = [dict(x) for x in parents]
    foreign = next(x["id"] for x in units if x["parent_id"] != parents[0]["parent_id"])
    substitute_rows[0]["scoped_child_ids"] = "|".join([foreign] + tokens[1:])
    reject("substituted-foreign-child", encode_csv(ph, substitute_rows))
    count_rows = [dict(x) for x in parents]
    count_rows[0]["scoped_child_count"] = str(int(count_rows[0]["scoped_child_count"]) + 1)
    reject("incoherent-child-count", encode_csv(ph, count_rows))
    altered_header = parent_raw.replace(ph[0].encode(), b"wrong_parent_id", 1)
    reject("malformed-parent-column", altered_header)
    return tests


def test_vintage_controls(helper_module, current_helper_raw, all_input_facts):
    baseline = helper_module.Baseline(ROOT, CURRENT, [file_descriptor(HELPER, current_helper_raw)])
    by_sha = {}
    for item in all_input_facts:
        by_sha.setdefault(item["sha256"], item["bytes"])
    for digest, size in by_sha.items():
        baseline.admit("control-input-" + digest, size)
    baseline.admit("issue-snapshot-1330", len(ISSUE_SNAPSHOT.read_bytes()))
    controls = []

    def expect_error(label, callback, expected):
        try:
            callback()
        except Exception as exc:
            require(expected in str(exc), f"{label} rejected for unexpected reason: {exc}")
            controls.append({"id": label, "outcome": "rejected", "error": type(exc).__name__, "detail": str(exc)})
            return
        raise EvidenceError("Output-admission control was accepted: " + label)

    prefix = ROOT / OWNED / "vintages"
    prefix.mkdir(parents=True, exist_ok=True)
    ordinary = prefix / "ordinary-collision"
    ordinary.mkdir(exist_ok=False)
    sent = ordinary / "sentinel.bin"
    sent.write_bytes(b"preserve-existing-sentinel\n")
    original = sent.read_bytes()
    expect_error("existing-ordinary-run", lambda: helper_module.NewVintage(baseline, OWNED, ordinary.name, ["out.json"]), "already exists")
    require(sent.read_bytes() == original, "Existing sentinel changed on admission failure")
    controls[-1]["sentinel_sha256"] = sha(original)

    dangling = prefix / "broken-link"
    dangling.symlink_to(ROOT / OWNED / "outside-target-must-not-exist")
    expect_error("broken-symlink-run", lambda: helper_module.NewVintage(baseline, OWNED, dangling.name, ["out.json"]), "Symlink")
    dangling.unlink()
    controls[-1]["target_exists_after"] = (ROOT / OWNED / "outside-target-must-not-exist").exists()
    require(not controls[-1]["target_exists_after"], "Broken-link target was created")

    traversal_path = Path(OWNED) / "vintages"
    expect_error("traversal-vintage", lambda: helper_module.NewVintage(baseline, OWNED, "../escaped", ["out.json"]), "safe named fresh vintage")
    controls[-1]["escaped_target_created"] = (ROOT / "escaped" / "vintages" / "escaped").exists()
    require(not controls[-1]["escaped_target_created"], "Traversal wrote outside owned prefix")

    escape_target = ROOT.parent / "worldatlas-1330-escape-target-absent"
    symlink_parent = prefix / "symlink-parent"
    symlink_parent.symlink_to(escape_target)
    expect_error("symlink-escaped-destination", lambda: helper_module.NewVintage(baseline, OWNED, symlink_parent.name, ["out.json"]), "Symlink")
    symlink_parent.unlink()
    controls[-1]["external_target_created"] = escape_target.exists()
    require(not escape_target.exists(), "Symlink destination created an external target")

    expect_error("single-file-over-limit", lambda: baseline.admit("oversized-fixture", 33554433), "file byte budget")
    expect_error("complete-phase-over-limit", lambda: baseline.admit("phase-overflow-fixture", 33554432), "phase exceeds byte budget")

    # Inject a genuine post-calculation write failure into NewVintage itself.
    fail_files = ["first.json", "second.json"]
    failed_vintage = "failure-after-calculation"
    failed = helper_module.NewVintage(baseline, OWNED, failed_vintage, fail_files)
    values = {"first.json": b'{"calculated":true}\n', "second.json": b'{"complete":true}\n'}
    original_open = Path.open
    failed_target = failed.root / "second.json"

    def fail_second(path, *args, **kwargs):
        if path == failed_target and args and args[0] == "xb":
            raise OSError("injected failure after calculation and first output")
        if path == failed_target and kwargs.get("mode") == "xb":
            raise OSError("injected failure after calculation and first output")
        return original_open(path, *args, **kwargs)

    Path.open = fail_second
    try:
        try:
            failed.publish_bytes(values)
        except OSError as exc:
            require("injected failure" in str(exc), "Unexpected injected write failure")
        else:
            raise EvidenceError("Post-calculation failure fixture unexpectedly succeeded")
    finally:
        Path.open = original_open
    require((failed.root / "first.json").read_bytes() == values["first.json"], "Partial failure fixture did not leave its first output")
    require(not (failed.root / "publication.json").exists(), "Partial failed attempt has a completion receipt")
    controls.append({"id": "failure-after-calculation-no-receipt", "outcome": "partial-without-success-receipt", "partial_outputs": ["first.json"], "publication_receipt": False})
    failure_record = {
        "attempt": failed_vintage,
        "status": "failed",
        "failure": "injected failure after calculation and first output",
        "partial_files": ["first.json"],
        "publication_receipt": False,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    recdir = ROOT / OWNED / "failed-attempts"
    recdir.mkdir(exist_ok=True)
    record_path = recdir / "post-calculation-failure.json"
    with record_path.open("xb") as stream:
        stream.write(json_bytes(failure_record))
    return controls


def main():
    issue, contract = verify_contract()
    current_helper_raw = git_bytes(CURRENT, HELPER)
    require(sha(current_helper_raw) == CURRENT_HELPER_SHA, "Current main helper pin changed")
    current_module = load_exact_helper(current_helper_raw, CURRENT_HELPER_SHA, CURRENT)
    facts = []
    # A preflight closes every actual path the historical producer reads.
    # The full runtime read trace is separately recorded by the outer runner.
    world_raw = git_bytes(BASELINE, "data/world-index.json")
    world = json.loads(world_raw)
    require(len(world.get("parts", [])) == 36 and len(set(world["parts"])) == 36,
            "Pinned historical world index is not the expected complete 36-part inventory")
    preflight_paths = ["data/world-index.json", "data/hierarchy.json"] + ["data/" + p for p in world["parts"]]
    packet_index = json.loads(git_bytes(BASELINE, OLD + "packet-index.json"))
    require(len(packet_index.get("files", [])) == 19, "Pinned original #446 packet inventory changed")
    preflight_paths += [row["path"] for row in packet_index["files"]] + [OLD + "packet-index.json", OLD + "baseline-files.json"]
    for path in sorted(set(preflight_paths)):
        raw = git_bytes(BASELINE, path)
        require(len(raw) <= 33554432, "A file exceeds the single-file admission cap: " + path)
        facts.append(file_descriptor(path, raw, BASELINE))
    historical_manifest = json.loads(git_bytes(BASELINE, OLD + "baseline-files.json"))
    require(len(historical_manifest.get("files", [])) == 9, "Historical source manifest is not the exact nine-file pin set")
    for item in historical_manifest["files"]:
        raw = git_bytes(item["commit"], item["path"])
        require(len(raw) == item["bytes"] and sha(raw) == item["sha256"], "Historical source pin mismatch: " + item["path"])
        require(len(raw) <= 33554432, "Historical source exceeds single-file cap: " + item["path"])
        facts.append(file_descriptor(item["path"], raw, item["commit"]))
    validator_raw = git_bytes(CURRENT, VALIDATOR)
    helper_current_raw = git_bytes(CURRENT, HELPER)
    helper_original_raw = git_bytes(BASELINE, HELPER)
    issue_1111_raw = git_bytes(CURRENT, ISSUE_1111_PATH)
    facts += [file_descriptor(VALIDATOR, validator_raw, CURRENT), file_descriptor(HELPER, helper_current_raw, CURRENT), file_descriptor(ISSUE_1111_PATH, issue_1111_raw, CURRENT)]
    facts.append(file_descriptor(HELPER, helper_original_raw, BASELINE))
    snapshot_raw = ISSUE_SNAPSHOT.read_bytes()
    facts.append(file_descriptor(str(ISSUE_SNAPSHOT.relative_to(ROOT)), snapshot_raw))
    runner_raw = Path(__file__).read_bytes()
    facts.append(file_descriptor(str(Path(__file__).relative_to(ROOT)), runner_raw))
    # Historical original outputs and issue pins participate in each run's
    # total phase even though the legacy calculation only reads them by Git.
    for path in OUTPUT_PATHS:
        raw = git_bytes(CURRENT, path)
        require(sha(raw) == PREVIOUS_OUTPUT_SHA[path], "Preserved original output pin changed: " + path)
        facts.append(file_descriptor(path, raw, CURRENT))
    # Deduplicate identical Git blob objects, not path strings. File-byte hashes
    # provide a safe fallback for the issue API snapshot, which is not a Git blob.
    unique = {}
    for row in facts:
        if row.get("commit"):
            oid = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", f"{row['commit']}:{row['path']}"], stderr=subprocess.PIPE).decode().strip()
        else:
            oid = "sha256:" + row["sha256"]
        row["git_blob_oid"] = oid
        unique.setdefault(oid, row["bytes"])
    require(sum(unique.values()) <= 268435456,
            "Complete unique-content input phase exceeds 256 MiB")

    receipts, product_records, all_namespaces, all_outputs = [], [], [], []
    for run_name in ("original-run-one", "original-run-two"):
        receipt, records, namespace, outputs = run_claimed_full_reproduction(run_name, {"evidence.immutable": current_module}, issue, contract, facts)
        receipts.append(receipt)
        product_records.append(records)
        all_namespaces.append(namespace)
        all_outputs.append(outputs)
    for path in OUTPUT_PATHS:
        require(all_outputs[0][path] == all_outputs[1][path], "Two full original-vintage runs differ: " + path)

    issue_snap_1111 = json.loads(git_bytes(CURRENT, ISSUE_1111_PATH))
    match = re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->", issue_snap_1111["body"], re.S)
    subject_ids = json.loads(match.group(1))["evidence_quality"]["subject_ids"]
    unit_raw = git_bytes(BASELINE, OLD + "unit-review.csv")
    parent_raw = git_bytes(BASELINE, OLD + "parent-review.csv")
    scope_raw = git_bytes(BASELINE, OLD + "scope.json")
    row_controls = strict_control(all_namespaces[0], unit_raw, parent_raw, scope_raw, subject_ids)
    vintage_controls = test_vintage_controls(current_module, current_helper_raw, facts)
    summary = {
        "version": 1,
        "issue": 1330,
        "issue_body_sha256": ISSUE_BODY_SHA,
        "baseline_commit": BASELINE,
        "current_main_commit": CURRENT,
        "full_runs": receipts,
        "publication_records": product_records,
        "original_source_paths": facts,
        "unique_input_content_bytes": sum({x["sha256"]: x["bytes"] for x in facts}.values()),
        "per_file_limit_bytes": 33554432,
        "per_phase_limit_bytes": 268435456,
        "strict_parent_controls": row_controls,
        "safe_output_controls": vintage_controls,
        "original_products_unchanged": True,
        "geographic_acceptance": "No current legal boundary, sovereign status, source authority, source license, completeness, or regional approval is established by these validator-integrity reproductions.",
    }
    summary_path = ROOT / OWNED / "reproduction-results.json"
    with summary_path.open("xb") as stream:
        stream.write(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    print(json.dumps({"issue": 1330, "runs": len(receipts), "strict_controls": len(row_controls), "safe_output_controls": len(vintage_controls), "unique_input_content_bytes": summary["unique_input_content_bytes"], "result": str(summary_path.relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
