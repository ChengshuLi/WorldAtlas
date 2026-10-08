#!/usr/bin/env python3
"""Reproduce the #1332 integrity erratum from captured immutable Git bytes.

This is cooperative provenance, not a security sandbox. It uses no network or
credentials, preserves every retained packet, and publishes only a new exclusive
vintage after the entire output set has been admitted.
"""
import argparse
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import os
import platform
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SOURCE_OWNED = "research/geography/south-america-batch4-validator-integrity-erratum-2026/"
OWNED = "research/geography/south-america-batch4-manifest-1349-erratum-20261008/"
ISSUE_SNAPSHOT = SOURCE_OWNED + "issue-1332-contract.json"
BASELINE = "e9190786dbf758524a3bde513fc4bb4d1ed6a3e7"
OLD_BASELINE = "7245eca6d56ee71fd1f40631c72116167ac5037d"
MERGE_1116 = "e7cd364e08a713825daa80a3d085d23bd58d5730"
ISSUE_DECLARED_OLD_REGISTER_SHA256 = "24d34c91f5e3517d1a05e29f1733cc4c0a656422f54ea71a855f63de95f9f57a"
AFFECTED = "data/regional-review/southern-south-america-batch4-validation-20261006"
ORIGINAL = "data/regional-review/regional-review-9b6d6a9ecf8f6c3b"
SCOPE = ORIGINAL + "/scope/embedded-workload-scope.json"
CROSSWALK = ORIGINAL + "/findings/crosswalk.csv"
PARENTS = ORIGINAL + "/findings/province-review.csv"
AREAS = ORIGINAL + "/findings/area-review.csv"
SOURCE_REGISTER = ORIGINAL + "/source/source-register.json"
REPRODUCER = ORIGINAL + "/findings/reproduce.py"
VERIFIER = AFFECTED + "/verify-packet.py"
BUILDER = AFFECTED + "/build-manifest.py"
IMMUTABLE = "scripts/evidence/immutable.py"
METHOD = "south-america-batch4-manifest-1349-erratum"
SUBJECT_SNAPSHOT_SHA256 = "70e61fad77bb6b93376821cbe8b7c8c73439eac95ede07a45784758400ae23f6"
ISSUE_PINS = {
    "world-index": ("data/world-index.json", "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03"),
    "hierarchy": ("data/hierarchy.json", "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b"),
    "original-scope": (SCOPE, "29a5984b06b96dff899a2c4d16659e63b66f75ab25dd2a744191e0267bc21af8"),
    "original-crosswalk": (CROSSWALK, "7a48c634a5e9d817cd3da977e1a023c7ffe0cc88340811817e68333ea2683ece"),
    "original-reproducer": (REPRODUCER, "f077ca8ab415b812e9832eb0340037313314be76947575b2ea6bfbafa56f2d0b"),
    "original-manifest": (ORIGINAL + "/evidence-quality.json", "85d43d138de43b4cde705217276e47716e835f5625263f75f9fc729be19d3aa0"),
    "original-summary": (ORIGINAL + "/findings/reproduction-summary.json", "6a417f7419cbdf940aa6c84fe7e62504f2030e2c3399907a6d4ee39efdf3766b"),
    "original-source-register": (SOURCE_REGISTER, "1e124f1c15ce6b9396ffd97e2d791b2d7cc995eb7d134f2d6dcfed1f18f235ca"),
    "affected-verifier": (VERIFIER, "12d3154a530f7ece109cc9b1c7b75db86f953bbcf763130ef5b76b01c6369acb"),
    "affected-manifest": (AFFECTED + "/evidence-quality.json", "4ef8fb06e41cc7461b2e4c928256bf87b2ea9e6487b72ca324c5e20fccb2d86d"),
    "original-parent-roster": (PARENTS, "26fa50de3fa6515fface069755f89b13dc6cb674b41fb95d9abcb9fbd0f91c2f"),
    "affected-issue-snapshot": (AFFECTED + "/issue-1116-contract.json", "04419a2a5916c65f46933cbccd5a1dd43147ece8b96b6f402259c9a55b0be961"),
}
BASELINE_EXTRA = {
    "original-area-roster": (AREAS, "7971335af98f6c8be11ab8699caca7f698384b2dd871983f5059b66da3fad17a"),
    "chile-source-metadata": (ORIGINAL + "/source/geoBoundaries-CHL-ADM3-metaData.json", "658356bb413f8b284b260360d1309527781e1b0c46027e1ae0a4c58da1c99409"),
    "paraguay-source-metadata": (ORIGINAL + "/source/geoBoundaries-PRY-ADM2-metaData.json", "d78f4e8a966cf3b077e62a33e8544e8c4bc08aab269da52f3b8d3602875851aa"),
    "original-source-review": (ORIGINAL + "/findings/source-review.md", None),
    "audit-prevention-helper": (IMMUTABLE, "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46"),
    "adjacent-manifest-writer": (BUILDER, "3ec08036828f262dd88b23b654e861b4d35fb1e4942f1340eced0d61adf8b843"),
}
OUTPUT_FILES = [
    "audit.json", "positive-control.json", "negative-control.json",
    "child-roster-controls.json", "execution-bindings.json",
    "legacy-writer-control.json", "run-metadata.json",
]
OUT_ROOT = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_bytes(commit, path):
    return subprocess.check_output(["git", "-C", str(REPO), "show", commit + ":" + path], stderr=subprocess.PIPE)


def descriptor(path, raw, role=None):
    row = {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}
    if role:
        row["role"] = role
    return row


def rows_csv(raw):
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline="")))


def write_csv(rows, columns):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


def read_issue_snapshot():
    path = REPO / ISSUE_SNAPSHOT
    raw = path.read_bytes()
    if sha(raw) != SUBJECT_SNAPSHOT_SHA256:
        raise ValueError("Captured #1332 issue snapshot changed")
    snapshot = json.loads(raw)
    issue = snapshot.get("issue", {})
    if issue.get("issue_number") != 1332 or issue.get("state") != "open":
        raise ValueError("Wrong or closed #1332 issue snapshot")
    match = re.search(r"<!-- worldatlas-work:v1\s*([\s\S]*?)\s*-->", issue.get("body", ""))
    if not match:
        raise ValueError("Captured issue body lacks its work contract")
    contract = json.loads(match.group(1))
    if contract.get("mode") != "geography" or contract.get("max_prs") != 1:
        raise ValueError("Issue lane or PR budget differs")
    if contract.get("owned_paths") != [SOURCE_OWNED]:
        raise ValueError("Issue-owned path differs")
    ids = contract.get("evidence_quality", {}).get("subject_ids", [])
    if len(ids) != 215 or len(set(ids)) != 215:
        raise ValueError("Issue contract must contain exact 215 unique subjects")
    return snapshot, contract, ids, raw


def load_immutable():
    path, expected = IMMUTABLE, BASELINE_EXTRA["audit-prevention-helper"][1]
    captured = git_bytes(BASELINE, path)
    if sha(captured) != expected:
        raise ValueError("Trusted immutable helper no longer matches its reviewed pin")
    if (REPO / path).read_bytes() != captured:
        raise ValueError("Materialized immutable helper differs from captured bytes")
    module = types.ModuleType("worldatlas_immutable_captured")
    module.__file__ = str(REPO / path)
    exec(compile(captured, module.__file__, "exec"), module.__dict__)
    return module, captured


def prepare_baseline(immutable):
    named = list(ISSUE_PINS.items()) + list(BASELINE_EXTRA.items())
    pins = []
    raw_by_name = {}
    for key, (path, expected) in named:
        raw = git_bytes(BASELINE, path)
        if expected and sha(raw) != expected:
            raise ValueError("Immutable issue pin differs: " + key)
        if (REPO / path).read_bytes() != raw:
            raise ValueError("Materialized evidence differs from baseline: " + key)
        pins.append({"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"})
        raw_by_name[path] = raw
    baseline = immutable.Baseline(str(REPO), BASELINE, pins)
    for path in baseline.pins:
        baseline.materialized_bytes(path)
    return baseline, raw_by_name


def validate_parent_rosters(parent_rows, features, hierarchy, ids, scope):
    if len(parent_rows) != 39:
        raise ValueError("Expected 39 complete parent rows")
    hmap = {r.get("id"): r for r in hierarchy if isinstance(r, dict) and r.get("id")}
    by_parent = {}
    for identity in ids:
        props = features[identity].get("properties", {})
        parent = props.get("parent_id")
        if not isinstance(parent, str) or not parent:
            raise ValueError("Scoped feature has no parent: " + identity)
        by_parent.setdefault(parent, set()).add(identity)
    if len(by_parent) != 39:
        raise ValueError("Expected 39 distinct actual province parents")
    scope_parents = {row.get("id"): row for row in scope.get("province_scopes", [])}
    seen_parents, seen_children = set(), set()
    audited = []
    for row in parent_rows:
        pid = row.get("province_id", "")
        if not pid or pid in seen_parents or pid not in by_parent:
            raise ValueError("Missing, duplicate or fabricated parent identity")
        seen_parents.add(pid)
        parent = hmap.get(pid)
        scoped = scope_parents.get(pid)
        if not parent or parent.get("level") != "province" or parent.get("name") != row.get("province_name"):
            raise ValueError("Parent ID, name or administrative tier mismatch: " + pid)
        if not scoped or scoped.get("name") != parent.get("name"):
            raise ValueError("Parent review differs from independent pinned scope: " + pid)
        tokens = row.get("scoped_location_ids", "").split(";")
        if not tokens or any(not token.strip() for token in tokens):
            raise ValueError("Blank scoped child ID: " + pid)
        if len(tokens) != len(set(tokens)):
            raise ValueError("Duplicate child ID in parent roster: " + pid)
        actual = by_parent[pid]
        if set(tokens) != actual:
            raise ValueError("Parent scoped child identities differ from indexed subject set: " + pid)
        if any(token in seen_children for token in tokens):
            raise ValueError("Child identity appears under multiple parents")
        seen_children.update(tokens)
        if int(row.get("full_scope_location_count", "-1")) != len(actual):
            raise ValueError("Parent child count differs from exact identities: " + pid)
        partial = row.get("partial_province")
        if partial not in ("True", "False") or (partial == "True") != bool(scoped.get("partial")):
            raise ValueError("Parent partial/full status differs from independent scope: " + pid)
        audited.append({
            "parent_id": pid, "parent_name": parent.get("name"), "level": parent.get("level"),
            "region_parent_id": parent.get("parent_id"), "child_count": len(tokens),
            "child_ids": sorted(tokens), "partial": partial == "True",
            "authoritative_current_parentage": "unverified",
            "independent_boundary_completeness": "unverified",
        })
    if seen_parents != set(by_parent) or seen_children != set(ids):
        raise ValueError("Parent roster does not cover the exact 215 scoped identities")
    return audited


def validate_areas(area_rows, scope, hierarchy):
    hmap = {r.get("id"): r for r in hierarchy if isinstance(r, dict) and r.get("id")}
    areas = {r.get("id"): r for r in scope.get("area_scopes", [])}
    if len(area_rows) != 5 or len(areas) != 5 or {r.get("area_id") for r in area_rows} != set(areas):
        raise ValueError("Expected exact five-area scope roster")
    checked = []
    for row in area_rows:
        aid = row["area_id"]
        base, declared = hmap.get(aid), areas[aid]
        if not base or base.get("level") != "area" or row.get("area_name") != base.get("name") or declared.get("name") != base.get("name"):
            raise ValueError("Area identity/name differs from pinned hierarchy: " + aid)
        if int(row["owned_member_count"]) != int(declared["owned_member_location_count"]):
            raise ValueError("Area owned count differs from pinned scope")
        if int(row["full_area_member_count"]) != int(declared["full_area_location_count"]):
            raise ValueError("Area full count differs from pinned scope")
        if row.get("partial_area") != str(bool(declared.get("partial"))):
            raise ValueError("Area partial/full flag differs from pinned scope")
        checked.append({"area_id": aid, "area_name": base["name"],
                        "owned_members": int(row["owned_member_count"]),
                        "full_area_members": int(row["full_area_member_count"]),
                        "partial": row["partial_area"] == "True",
                        "administrative_equivalence": "not established"})
    return checked


def roster_controls(parent_rows, features, hierarchy, ids, scope):
    cases = []
    scenarios = [
        ("fabricated-child", lambda rows: rows[0].update(scoped_location_ids="gb:CHL:ADM3:AUDITOR-FABRICATED-CHILD;" + rows[0]["scoped_location_ids"].split(";", 1)[1])),
        ("missing-child", lambda rows: rows[0].update(scoped_location_ids=";".join(rows[0]["scoped_location_ids"].split(";")[1:]))),
        ("duplicate-child", lambda rows: rows[0].update(scoped_location_ids=rows[0]["scoped_location_ids"] + ";" + rows[0]["scoped_location_ids"].split(";")[0])),
        ("blank-child", lambda rows: rows[0].update(scoped_location_ids=rows[0]["scoped_location_ids"] + ";")),
        ("substituted-child", lambda rows: rows[0].update(scoped_location_ids="gb:CHL:ADM3:INVENTED")),
        ("wrong-parent-name", lambda rows: rows[0].update(province_name="Invented parent")),
        ("wrong-child-count", lambda rows: rows[0].update(full_scope_location_count="999")),
    ]
    for name, mutate in scenarios:
        candidate = [dict(row) for row in parent_rows]
        mutate(candidate)
        candidate_sha = sha(write_csv(candidate, list(parent_rows[0].keys())))
        try:
            validate_parent_rosters(candidate, features, hierarchy, ids, scope)
        except (ValueError, KeyError, TypeError) as error:
            cases.append({"name": name, "candidate_sha256": candidate_sha,
                          "outcome": "rejected", "reason": str(error)})
        else:
            raise ValueError("Child-roster negative control accepted: " + name)
    return {"method_id": METHOD, "kind": "negative-control", "outcome": "passed",
            "controls_executed": len(cases), "controls": cases}


def audit_legacy_validator(verify, raw_by_name, ids, features, scope):
    raw = dict(raw_by_name)
    actual = verify.audit(raw, ids, {})
    parent_rows = rows_csv(raw[PARENTS])
    changed = [dict(row) for row in parent_rows]
    parts = changed[0]["scoped_location_ids"].split(";")
    changed[0]["scoped_location_ids"] = "gb:CHL:ADM3:AUDITOR-FABRICATED-CHILD;" + ";".join(parts[1:])
    raw[PARENTS] = write_csv(changed, list(parent_rows[0].keys()))
    accepted = verify.audit(raw, ids, {})
    if accepted.get("parent_review_rows_checked") != 39:
        raise ValueError("Legacy actual audit did not reach its known blind spot")
    try:
        validate_parent_rosters(changed, features,
            json.loads(raw["data/hierarchy.json"]), ids, scope)
    except ValueError as error:
        rejected = str(error)
    else:
        raise ValueError("Corrected validator accepted the exact legacy fixture")
    return {
        "legacy_function": "captured verify-packet.py::audit(raw, ids, issue)",
        "legacy_code_sha256": sha(verify.code_bytes),
        "legacy_mutation_sha256": sha(raw[PARENTS]),
        "legacy_outcome": "accepted fabricated child while reporting 39 parent rows checked",
        "legacy_reported_parent_rows": accepted["parent_review_rows_checked"],
        "corrected_outcome": "rejected against independent complete world-index children",
        "corrected_reason": rejected,
        "source_limit": "The indexed rows establish retained Atlas IDs and parent links only; they do not certify legal identity, source currency, boundaries or completeness.",
    }


def temp_gitfile(root):
    gitfile = (REPO / ".git").read_text()
    (root / ".git").write_text(gitfile)


def copy_git_file(commit, path, root):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(git_bytes(commit, path))
    return target


def run_unsafe_cli_fixture(base, verify, historical_raw, altered_crosswalk, mutated_helper=False):
    """Execute the unchanged original CLI only against disposable scratch sentinels."""
    with tempfile.TemporaryDirectory(prefix="worldatlas-1332-writer-") as temp:
        root = Path(temp) / "repo"
        root.mkdir()
        temp_gitfile(root)
        # The CLI and each dynamic helper input are copied as captured immutable bytes.
        staged = []
        for path in (VERIFIER, AFFECTED + "/issue-1116-contract.json"):
            content = git_bytes(MERGE_1116, path)
            copy_git_file(MERGE_1116, path, root)
            staged.append({"commit": MERGE_1116, **descriptor(path, content)})
        for suffix in ["scope/embedded-workload-scope.json",
                       "findings/crosswalk.csv", "findings/province-review.csv",
                       "findings/area-review.csv", "source/source-register.json",
                       "source/geoBoundaries-CHL-ADM3-metaData.json",
                       "source/geoBoundaries-PRY-ADM2-metaData.json",
                       "findings/reproduce.py"]:
            path = ORIGINAL + "/" + suffix
            content = historical_raw[path]
            copy_git_file(OLD_BASELINE, path, root)
            staged.append({"commit": OLD_BASELINE, **descriptor(path, content)})
        # The patched crosswalk is supplied in memory by the CLI. Other helper
        # reads use their own baseline vintage, not a later working-tree file.
        for num in (2, 20, 28):
            name = f"data/geography/part-{num}.json"
            content = historical_raw[name]
            copy_git_file(OLD_BASELINE, name, root)
            staged.append({"commit": OLD_BASELINE, **descriptor(name, content)})
        crosswalk_target = root / CROSSWALK
        crosswalk_target.parent.mkdir(parents=True, exist_ok=True)
        crosswalk_target.write_bytes(altered_crosswalk)
        packet = root / AFFECTED
        run_dir = packet / "run-disposable"
        run_dir.mkdir(parents=True)
        targets = [packet / "legacy-false-positive-reproduction.json",
                   run_dir / "crosswalk-baseline-audit.json",
                   run_dir / "positive-control.json",
                   run_dir / "negative-controls.json"]
        before = {}
        for index, target in enumerate(targets):
            sentinel = f"disposable sentinel {index}\n".encode()
            target.write_bytes(sentinel)
            before[str(target.relative_to(root))] = sha(sentinel)
        helper_path = root / REPRODUCER
        if mutated_helper:
            old = helper_path.read_bytes()
            fixture = b"AUDITOR_CODE_FIXTURE_EXECUTED = True\n" + old.replace(
                b"'baseline_matches':len(found)", b"'baseline_matches':len(found)-1")
            if fixture == old or sha(fixture) != "1f36cfce1dd0cbec3bf96104598f4457ae3696c07f23959d8a709e357e2e8e31":
                raise ValueError("Exact reported helper-drift fixture no longer matches")
            helper_path.write_bytes(fixture)
        command = [sys.executable, str(packet / "verify-packet.py"), "--out-dir", "run-disposable"]
        completed = subprocess.run(command, cwd=root, env={"PATH": os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True, timeout=90)
        after = {str(path.relative_to(root)): sha(path.read_bytes()) for path in targets}
        if completed.returncode != 0 or all(before[k] == after[k] for k in before):
            raise ValueError("Disposable original CLI did not execute and overwrite its sentinels: " + completed.stderr[-1000:])
        result = {"method_id": METHOD, "kind": "negative-control", "outcome": "passed",
                  "fixture": "unchanged actual verify-packet.py entry point in temporary repository; no original paths used",
                  "sentinels": [{"path": key, "before_sha256": before[key], "after_sha256": after[key],
                                 "overwritten": before[key] != after[key]} for key in before],
                  "exit_code": completed.returncode,
                  "mode": "altered materialized original helper accepted" if mutated_helper else "retained-root and caller output overwrite reproduced",
                  "staged_git_inputs": staged,
                  "patched_crosswalk_input": {"commit": OLD_BASELINE, "bytes": len(altered_crosswalk),
                      "sha256": sha(altered_crosswalk)},
                  "temporary_output_bytes": [{"path": key, "bytes": (root / key).stat().st_size,
                      "sha256": after[key]} for key in after]}
        if mutated_helper:
            if not all(row["overwritten"] for row in result["sentinels"]):
                raise ValueError("Helper-drift fixture did not complete")
            output = json.loads((run_dir / "crosswalk-baseline-audit.json").read_text())
            legacy = output.get("legacy_false_positive_reproduction", {})
            # The issue reports this separate metric and the 215 baseline feature
            # count. Preserve observed values without promoting them to truth.
            result["executed_helper_sha256"] = sha(helper_path.read_bytes())
            result["helper_fixture_executed"] = True
            result["audit_baseline_feature_matches"] = output.get("baseline_feature_matches")
            result["legacy_output_keys"] = sorted(legacy.get("legacy_output", {}))
            result["exact_legacy_output"] = legacy.get("legacy_output", {})
        return result


def prepare_legacy_cli_inputs(verify, ids):
    raw, _ = verify.baseline_inputs()
    rows = verify.parse_csv(raw[CROSSWALK])
    if len(rows) != 215:
        raise ValueError("Historical CLI baseline crosswalk is not the exact 215-row fixture")
    rows[1]["source_shape_id"] = "FABRICATED-NOT-A-SOURCE-ID"
    return raw, verify.rows_to_csv(rows)


def adverse_code_drift(immutable, base, expected_pin):
    path = IMMUTABLE
    with tempfile.TemporaryDirectory(prefix="worldatlas-1332-code-drift-") as temp:
        root = Path(temp) / "repo"
        root.mkdir()
        temp_gitfile(root)
        copy_git_file(BASELINE, path, root)
        target = root / path
        changed = target.read_bytes() + b"\n# materialized drift fixture\n"
        target.write_bytes(changed)
        isolated = immutable.Baseline(str(root), BASELINE, [
            {"path": path, "bytes": len(git_bytes(BASELINE, path)),
             "sha256": expected_pin, "hash_kind": "file-bytes"}])
        try:
            isolated.materialized_bytes(path)
        except ValueError as error:
            return {"path": path, "pinned_sha256": expected_pin,
                    "changed_materialized_sha256": sha(changed), "outcome": "rejected-before-execution",
                    "reason": str(error)}
        raise ValueError("Materialized helper drift was not rejected")


def safety_controls(immutable, baseline, root):
    outcomes = []
    def rejected(name, operation):
        try:
            operation()
        except (ValueError, FileExistsError, OSError) as error:
            outcomes.append({"name": name, "outcome": "rejected", "reason": type(error).__name__})
        else:
            raise ValueError("Unsafe destination control unexpectedly admitted: " + name)
    temp = Path(root)
    rejected("owned-path-traversal", lambda: immutable.NewVintage(baseline, "research/geography/../../outside/", "safe", ["a.json"]))
    rejected("vintage-traversal", lambda: immutable.NewVintage(baseline, OWNED, "../outside", ["a.json"]))
    rejected("filename-traversal", lambda: immutable.NewVintage(baseline, OWNED, "safe", ["../outside.json"]))
    # Collision and broken-link checks occur in a disposable repo, never the packet.
    with tempfile.TemporaryDirectory(prefix="worldatlas-1332-output-safety-") as scratch:
        checkout = Path(scratch) / "repo"
        checkout.mkdir()
        temp_gitfile(checkout)
        minimal = immutable.Baseline(str(checkout), BASELINE, [
            {"path": IMMUTABLE, "bytes": len(git_bytes(BASELINE, IMMUTABLE)),
             "sha256": BASELINE_EXTRA["audit-prevention-helper"][1], "hash_kind": "file-bytes"}])
        owned = checkout / OWNED
        collision = owned / "vintages" / "collision"
        collision.mkdir(parents=True)
        (collision / "audit.json").write_bytes(b"preserve me")
        rejected("existing-ordinary-output", lambda: immutable.NewVintage(minimal, OWNED, "collision", ["audit.json"]))
        (owned / "vintages" / "broken-link").symlink_to(owned / "missing-target")
        rejected("broken-symlink-output", lambda: immutable.NewVintage(minimal, OWNED, "broken-link", ["audit.json"]))
        failed = immutable.NewVintage(minimal, OWNED, "failure-after-computation", ["audit.json"])
        original_link = immutable.os.link
        def fail_receipt(source, destination):
            if Path(destination).name == "publication.json":
                raise OSError("controlled final receipt failure")
            return original_link(source, destination)
        immutable.os.link = fail_receipt
        try:
            try:
                failed.publish({"audit.json": {"value": 1}})
            except OSError:
                pass
            else:
                raise ValueError("Post-calculation receipt fault did not fire")
        finally:
            immutable.os.link = original_link
        if (failed.root / "publication.json").exists() or not (failed.root / "audit.json").exists():
            raise ValueError("Partial failure did not preserve output without completion receipt")
        outcomes.append({"name": "failure-after-computation", "outcome": "partial-run-no-completion-receipt",
                         "output_preserved": True, "publication_receipt_present": False})
        if (collision / "audit.json").read_bytes() != b"preserve me":
            raise ValueError("Collision sentinel changed")
    return {"method_id": METHOD, "kind": "negative-control", "outcome": "passed",
            "controls_executed": len(outcomes), "controls": outcomes}


def run(vintage):
    snapshot, contract, ids, snapshot_raw = read_issue_snapshot()
    immutable, helper_raw = load_immutable()
    base, raw = prepare_baseline(immutable)
    # Authenticate the two historical versions separately. The 7245 source
    # register and the e7cd merge source register intentionally differ.
    historical_register = git_bytes(OLD_BASELINE, SOURCE_REGISTER)
    merge_register = git_bytes(MERGE_1116, SOURCE_REGISTER)
    old_helper = git_bytes(OLD_BASELINE, REPRODUCER)
    merge_helper = git_bytes(MERGE_1116, REPRODUCER)
    if sha(historical_register) != ISSUE_DECLARED_OLD_REGISTER_SHA256:
        raise ValueError("Original #935 source-register vintage changed")
    if sha(merge_register) != ISSUE_PINS["original-source-register"][1]:
        raise ValueError("Later #1120 source-register vintage changed")
    if sha(old_helper) != ISSUE_PINS["original-reproducer"][1] or sha(merge_helper) != sha(old_helper):
        raise ValueError("Historical helper bytes differ across declared vintages")
    if sha(git_bytes(MERGE_1116, VERIFIER)) != ISSUE_PINS["affected-verifier"][1]:
        raise ValueError("Affected verifier source pin differs at merge vintage")

    vintage_writer = immutable.NewVintage(base, OWNED, vintage, OUTPUT_FILES)
    _, _, issue_ids, _ = read_issue_snapshot()
    if ids != issue_ids or len(ids) != 215:
        raise ValueError("Current issue scope differs from pinned contract")

    # Complete unique world-index traversal: all indexed part bytes count toward
    # the phase, and all 215 subject-to-containing-file links are retained.
    features, containing = base.subjects(ids)
    scope = json.loads(base.pinned_bytes(SCOPE))
    if scope.get("member_location_ids") != ids or len(scope.get("province_scopes", [])) != 39:
        raise ValueError("New issue subject scope differs from original frozen scope")
    index = json.loads(base.pinned_bytes("data/world-index.json"))
    if len(index.get("parts", [])) != 36 or len(set(index["parts"])) != 36:
        raise ValueError("Expected complete unique 36-part index")
    if len(features) != 215:
        raise ValueError("Exact subjects missing from full index")
    # The legacy audit function expects its three subject-containing parts in
    # the explicit input map. These are the same immutable bytes traversed above.
    for part in ("data/geography/part-2.json", "data/geography/part-20.json", "data/geography/part-28.json"):
        raw[part] = base.read(part)
    hierarchy = json.loads(base.pinned_bytes("data/hierarchy.json"))
    source_rows = rows_csv(base.pinned_bytes(CROSSWALK))
    parent_rows = rows_csv(base.pinned_bytes(PARENTS))
    area_rows = rows_csv(base.pinned_bytes(AREAS))
    parent_audit = validate_parent_rosters(parent_rows, features, hierarchy, ids, scope)
    area_audit = validate_areas(area_rows, scope, hierarchy)

    # Load the actual affected audit function from authenticated captured bytes,
    # never through runpy from its mutable materialized path.
    loaded = base.load_modules({"verify_packet": VERIFIER})
    verify = loaded["verify_packet"]
    verify.code_bytes = base.pinned_bytes(VERIFIER)
    if sha(verify.code_bytes) != ISSUE_PINS["affected-verifier"][1]:
        raise ValueError("Executed affected verifier hash differs from issue pin")
    # Bind the exact legacy verifier baseline and the altered crosswalk bytes
    # supplied at its historical helper boundary before any output calculation.
    historical_raw, altered_crosswalk = prepare_legacy_cli_inputs(verify, ids)
    historical_input_descriptors = [
        {"commit": OLD_BASELINE, **descriptor(path, value)}
        for path, value in sorted(historical_raw.items())
    ]
    for path, value in historical_raw.items():
        current = base.read(path)
        if sha(current) != sha(value):
            base.admit(OLD_BASELINE + ":" + path, len(value))
    if sha(altered_crosswalk) != sha(historical_raw[CROSSWALK]):
        base.admit("fixture:legacy-cli-fabricated-crosswalk", len(altered_crosswalk))
    mutated_original_helper = b"AUDITOR_CODE_FIXTURE_EXECUTED = True\n" + historical_raw[REPRODUCER].replace(
        b"'baseline_matches':len(found)", b"'baseline_matches':len(found)-1")
    base.admit("fixture:legacy-cli-mutated-original-helper", len(mutated_original_helper))
    legacy_audit = verify.audit(dict(raw), ids, snapshot)
    legacy_blind_spot = audit_legacy_validator(verify, raw, ids, features, scope)

    # The old historical helper is executed from a captured exact byte pin in
    # the disposable actual-CLI fixture above. The mutation fixture exercises
    # its genuine runpy boundary without touching any retained packet.
    writer_control = run_unsafe_cli_fixture(base, verify, historical_raw, altered_crosswalk, mutated_helper=False)
    drift_fixture = run_unsafe_cli_fixture(base, verify, historical_raw, altered_crosswalk, mutated_helper=True)
    for run_name, test in (("unchanged", writer_control), ("mutated-helper", drift_fixture)):
        for output in test["temporary_output_bytes"]:
            base.admit("scratch:" + run_name + ":" + output["path"], output["bytes"])
    code_drift = adverse_code_drift(immutable, base, BASELINE_EXTRA["audit-prevention-helper"][1])

    # Keep all upstream identity/licensing/boundary questions inherited from
    # the original packet. Candidate source fields are observations only.
    source_profiles = {
        "gb:CHL:ADM3": {"rows": 167, "candidate_vintage": "2020", "granularity": "ADM3",
            "retained_original_geometry": False, "current_authority": "unverified",
            "license": "candidate metadata only; source terms not reverified"},
        "gb:PRY:ADM2": {"rows": 47, "candidate_vintage": "2012", "granularity": "ADM2",
            "retained_original_geometry": False, "current_authority": "unverified",
            "license": "candidate metadata only; source terms not reverified"},
        "atlas:city:PRY-4837": {"rows": 1, "candidate_vintage": "undated modern reference",
            "granularity": "aggregate city territory", "retained_original_geometry": False,
            "current_authority": "unverified", "license": "underlying source license not independently restored"},
    }
    row_lookup = {row["location_id"]: row for row in source_rows}
    if len(source_rows) != 215 or set(row_lookup) != set(ids):
        raise ValueError("Original crosswalk candidate differs from exact issue subject set")
    row_report = []
    for identity in ids:
        feature, row = features[identity], row_lookup[identity]
        props = feature.get("properties", {})
        parent_id = props.get("parent_id")
        parent = next(x for x in parent_audit if x["parent_id"] == parent_id)
        if row.get("name") != str(props.get("name", "")) or row.get("parent_id") != str(parent_id or ""):
            raise ValueError("Retained crosswalk name/parent differs from immutable Atlas baseline: " + identity)
        row_report.append({
            "subject_id": identity, "containing_part": containing[identity]["path"],
            "retained_baseline_name": props.get("name"), "retained_parent_id": parent_id,
            "retained_parent_name": parent["parent_name"],
            "candidate_source_id": row.get("source_id"), "candidate_source_year": row.get("source_year"),
            "candidate_license_claim": row.get("license"),
            "candidate_source_member_id": row.get("source_shape_id"),
            "candidate_source_member_name": row.get("source_name"),
            "candidate_source_name_flag": row.get("name_exact_match"),
            "boundary_completeness": "not established",
            "legal_parentage": "not established",
            "source_row_identity_and_license": "not independently reverified",
            "neighboring_granularity_note": "Chile candidate ADM3, Paraguay candidate ADM2, and one aggregate city record are not asserted equivalent",
        })
    if sum(x.get("source_id") == "gb:CHL:ADM3" for x in source_rows) != 167 or sum(x.get("source_id") == "gb:PRY:ADM2" for x in source_rows) != 47:
        raise ValueError("Retained candidate source profile counts differ")
    if sum(x.get("source_id") == "atlas:city:PRY-4837" for x in source_rows) != 1:
        raise ValueError("Expected one Asunción aggregate row")

    control_writer = safety_controls(immutable, base, OUT_ROOT)
    mapping_controls = verify.controls(raw, ids, features, source_rows)
    complete_controls = roster_controls(parent_rows, features, hierarchy, ids, scope)
    output_by_name = {
        "audit.json": {
            "issue": 1332, "work_scope_issue": 1116, "evaluation_commit": BASELINE,
            "subject_count": len(ids), "subject_ids_sha256": sha(json.dumps(sorted(ids), separators=(",", ":")).encode()),
            "index_part_count": len(index["parts"]), "indexed_subject_count": len(features),
            "crosswalk_candidate_row_count": len(source_rows),
            "source_profiles": source_profiles, "subject_rows": row_report,
            "parent_count": len(parent_audit), "parent_rosters": parent_audit,
            "area_count": len(area_audit), "areas": area_audit,
            "legacy_audit_function_result": {
                "parent_review_rows_checked": legacy_audit.get("parent_review_rows_checked"),
                "distinct_actual_parent_count": legacy_audit.get("distinct_actual_parent_count"),
                "scope_id_count": legacy_audit.get("scope_id_count"),
            },
            "legacy_child_roster_gap": legacy_blind_spot,
            "historical_source_registers": {
                "old_baseline_7245_sha256": sha(historical_register),
                "old_baseline_7245_bytes": len(historical_register),
                "issue_declared_old_baseline_sha256": ISSUE_DECLARED_OLD_REGISTER_SHA256,
                "issue_declared_old_baseline_pin_matches_git_bytes": sha(historical_register) == ISSUE_DECLARED_OLD_REGISTER_SHA256,
                "merge_1116_e7cd_sha256": sha(merge_register),
                "merge_1116_e7cd_bytes": len(merge_register),
                "same_vintage": historical_register == merge_register,
                "interpretation": "distinct legitimate source-register vintages; both hashes match their separately named Git commits; no equivalence asserted",
            },
            "geographic_outcome": "mechanical retained-identity and audit-integrity checks only; no upstream legal or boundary certification",
            "limits": [
                "Original Chile geoBoundaries 2020 ADM3 and Paraguay 2012 ADM2 geometries were not restored or reverified.",
                "INE 2022 response bytes, license terms and statistical-to-administrative relationship remain unverified.",
                "Current legal parentage, completeness, boundary validity, neighboring seams and positional accuracy remain unresolved.",
                "The 215 retained Atlas IDs establish only retained baseline identity and parent links.",
                "Asuncion aggregate source identity, legal tier, extent and license remain unresolved.",
            ],
        },
        "positive-control.json": {
            "method_id": METHOD, "kind": "positive-control", "outcome": "passed",
            "subjects": len(ids), "crosswalk_rows": len(source_rows), "parent_rows": len(parent_audit),
            "child_id_tokens": sum(x["child_count"] for x in parent_audit),
            "area_rows": len(area_audit), "complete_index_parts": len(index["parts"]),
            "upstream_source_rows_reverified": 0,
            "scope_hash": sha(json.dumps(sorted(ids), separators=(",", ":")).encode()),
        },
        "negative-control.json": {
            "method_id": METHOD, "kind": "negative-control", "outcome": "passed",
            "controls_executed": mapping_controls["controls_executed"] + complete_controls["controls_executed"] + control_writer["controls_executed"],
            "mapping_controls": mapping_controls, "child_roster_controls": complete_controls,
            "output_safety_controls": control_writer,
            "code_drift_control": code_drift,
            "unsafe_cli_sentinel_control": writer_control,
            "mutated_helper_cli_control": drift_fixture,
            "adjacent_manifest_writer": {
                "path": BUILDER, "sha256": BASELINE_EXTRA["adjacent-manifest-writer"][1],
                "disposition": "source inspected; not executed because it uses overwrite-capable write_text on retained manifest",
            },
        },
        "child-roster-controls.json": complete_controls,
        "execution-bindings.json": {
            "baseline_commit": BASELINE, "merge_commit_1116": MERGE_1116,
            "legacy_baseline_commit": OLD_BASELINE,
            "authenticated_helpers": [
                {"path": IMMUTABLE, "sha256": sha(helper_raw), "execution": "captured Git bytes compiled only after pin and materialized check"},
                {"path": VERIFIER, "sha256": sha(verify.code_bytes), "execution": "Baseline.load_modules pinned bytes; actual audit function called"},
                {"path": REPRODUCER, "sha256": sha(old_helper), "execution": "captured 7245 Git bytes copied to disposable actual CLI scratch and invoked by runpy"},
                {"path": BUILDER, "sha256": BASELINE_EXTRA["adjacent-manifest-writer"][1], "execution": "not executed; source inspection only"},
            ],
            "legacy_cli_baseline_inputs_7245": historical_input_descriptors,
            "unique_input_phase_bytes_before_publication": sum(base.consumed.values()),
            "legacy_helper_runtime_inputs_7245": [
                {"path": path, "bytes": len(historical_raw[path]), "sha256": sha(historical_raw[path])}
                for path in [SCOPE, CROSSWALK, PARENTS, AREAS, SOURCE_REGISTER,
                    ORIGINAL + "/source/geoBoundaries-CHL-ADM3-metaData.json",
                    ORIGINAL + "/source/geoBoundaries-PRY-ADM2-metaData.json",
                    "data/geography/part-2.json", "data/geography/part-20.json",
                    "data/geography/part-28.json", REPRODUCER]
            ],
            "in_memory_fabricated_crosswalk": {"bytes": len(altered_crosswalk), "sha256": sha(altered_crosswalk)},
            "mutated_original_helper_fixture": {"bytes": len(mutated_original_helper), "sha256": sha(mutated_original_helper)},
            "captured_issue_snapshot_sha256": sha(snapshot_raw),
            "original_1116_snapshot_sha256": sha(raw[AFFECTED + "/issue-1116-contract.json"]),
            "source_vintages": {
                "source_register_7245": sha(historical_register),
                "source_register_e7cd": sha(merge_register),
                "issue_declared_source_register_7245": ISSUE_DECLARED_OLD_REGISTER_SHA256,
                "issue_old_pin_discrepancy": sha(historical_register) != ISSUE_DECLARED_OLD_REGISTER_SHA256,
                "meaning": "separately identified, never substituted or silently refreshed",
            },
            "changed_materialized_code": code_drift,
            "runtime": {"python": platform.python_version(), "platform": platform.platform()},
            "project_imports": "No undeclared project imports; verifier and historical reproducer use Python standard library only.",
        },
        "legacy-writer-control.json": writer_control,
        "run-metadata.json": {
            "vintage": vintage, "created_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "baseline_commit": BASELINE, "issue_snapshot_sha256": sha(snapshot_raw),
            "producer_sha256": sha(Path(__file__).read_bytes()),
            "immutable_helper_sha256": sha(helper_raw),
            "project_imports": "Only captured pinned scripts/evidence/immutable.py; remaining imports are Python standard library.",
            "result_note": "Run identity and timestamp differ by vintage; deterministic calculation products are compared separately.",
        },
    }
    records = vintage_writer.publish(output_by_name)
    print(json.dumps({"status": "complete", "vintage": vintage, "outputs": records,
                      "consumed_input_bytes": sum(base.consumed.values()),
                      "unique_consumed_files": len(base.consumed)}, indent=2, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vintage", required=True, help="fresh safe vintage name; never reused")
    args = parser.parse_args()
    run(args.vintage)


if __name__ == "__main__":
    main()
