#!/usr/bin/env python3
"""Run the original and corrected manifest-builder controls in disposable copies."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/south-america-batch4-manifest-1349-erratum-20261008"
SOURCE = "research/geography/south-america-batch4-validator-integrity-erratum-2026"
PYTHON = os.environ.get("WORLDATLAS_TEST_PYTHON", "python3.12")
ACCEPTED_ID = "atlas:city:PRY-4837"
FOREIGN_ID = "gb:AFG:ADM2:17698898B67359070524975"
MAX_BYTES = 32 * 1024 * 1024


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def copy_repo(parent, name):
    repo = parent / name
    repo.mkdir()
    (repo / ".git").write_text((ROOT / ".git").read_text())
    (repo / "research/geography").mkdir(parents=True)
    shutil.copytree(ROOT / SOURCE, repo / SOURCE)
    shutil.copytree(ROOT / OWNED, repo / OWNED,
                    ignore=shutil.ignore_patterns(".controls-scratch", "__pycache__"))
    (repo / "scripts/evidence").mkdir(parents=True)
    shutil.copy2(ROOT / "scripts/evidence/immutable.py", repo / "scripts/evidence/immutable.py")
    probe = subprocess.run(["git", "-C", str(repo), "show", "e9190786dbf758524a3bde513fc4bb4d1ed6a3e7:data/world-index.json"], capture_output=True)
    if probe.returncode or len(probe.stdout) > MAX_BYTES:
        raise RuntimeError("Disposable repository cannot read its immutable Git baseline")
    return repo


def run(repo, script, *, args=(), env=None):
    command = [PYTHON, "-B", str(repo / script), *args]
    result = subprocess.run(command, cwd=repo, capture_output=True, text=True, env=env)
    return {"command": [PYTHON, "-B", script, *args], "exit_code": result.returncode,
            "stdout": result.stdout[-2000:], "stderr": result.stderr[-2000:]}


def output_hashes(repo, paths):
    result = {}
    for path in paths:
        target = repo / path
        if target.is_file() and not target.is_symlink():
            raw = target.read_bytes()
            if len(raw) > MAX_BYTES:
                raise ValueError("Control output exceeds ordinary-file limit")
            result[path] = {"bytes": len(raw), "sha256": digest(raw)}
    return result


def remove_old_outputs(repo):
    for name in ("evidence-quality.json", "reproducibility.json"):
        (repo / SOURCE / name).unlink(missing_ok=True)


def issue_contract(repo, packet):
    issue_number = "1332" if packet == SOURCE else "1506"
    path = repo / packet / ("issue-" + issue_number + "-contract.json")
    captured = json.loads(path.read_bytes())
    issue = captured.get("issue", captured)
    match = re.search(r"<!-- worldatlas-work:v1\s*([\s\S]*?)\s*-->", issue["body"])
    if not match:
        raise ValueError("Contract marker missing in control fixture")
    return path, captured, issue, match


def replace_scope_id(path, captured, issue, match):
    spec = json.loads(match.group(1))
    ids = spec["evidence_quality"]["subject_ids"]
    ids[ids.index(ACCEPTED_ID)] = FOREIGN_ID
    changed = "<!-- worldatlas-work:v1\n" + json.dumps(spec, ensure_ascii=False, sort_keys=True) + "\n-->"
    issue["body"] = issue["body"][:match.start()] + changed + issue["body"][match.end():]
    if "issue" in captured:
        captured["issue"] = issue
    path.write_text(json.dumps(captured, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def legacy_controls(parent):
    results = {}
    repo = copy_repo(parent, "legacy-positive")
    remove_old_outputs(repo)
    result = run(repo, SOURCE + "/build_manifest.py")
    paths = [SOURCE + "/evidence-quality.json", SOURCE + "/reproducibility.json"]
    outputs = output_hashes(repo, paths)
    if result["exit_code"] != 0 or outputs.get(paths[0], {}).get("sha256") != "cbab3413a6808f7dd3e06389b235f782ef2363a109b9397ebbc3d5ec8bc45aac":
        raise AssertionError("Original builder complete positive control changed")
    results["original_complete_positive"] = {**result, "outputs": outputs}

    repo = copy_repo(parent, "legacy-first-collision")
    result = run(repo, SOURCE + "/build_manifest.py")
    outputs = output_hashes(repo, [SOURCE + "/evidence-quality.json", SOURCE + "/reproducibility.json"])
    if result["exit_code"] == 0 or outputs.get(SOURCE + "/evidence-quality.json", {}).get("sha256") != "cbab3413a6808f7dd3e06389b235f782ef2363a109b9397ebbc3d5ec8bc45aac" or outputs.get(SOURCE + "/reproducibility.json", {}).get("sha256") != "bd845629235f72a1fbc01c9bfcae6ba6b28e9cfbb40d696233be0d90e98a61d5":
        raise AssertionError("Original first-output collision did not preserve the complete prior output set")
    results["original_first_output_collision"] = {**result, "outputs": outputs}

    repo = copy_repo(parent, "legacy-late-collision")
    target = repo / SOURCE
    (target / "reproducibility.json").unlink()
    sentinel = b"preserved final manifest sentinel\n"
    (target / "evidence-quality.json").write_bytes(sentinel)
    result = run(repo, SOURCE + "/build_manifest.py")
    outputs = output_hashes(repo, [SOURCE + "/evidence-quality.json", SOURCE + "/reproducibility.json"])
    if result["exit_code"] == 0 or outputs.get(SOURCE + "/reproducibility.json", {}).get("sha256") != "bd845629235f72a1fbc01c9bfcae6ba6b28e9cfbb40d696233be0d90e98a61d5" or outputs.get(SOURCE + "/evidence-quality.json", {}).get("sha256") != digest(sentinel):
        raise AssertionError("Original late-manifest defect did not reproduce exactly")
    results["original_late_manifest_collision"] = {**result, "outputs": outputs}

    repo = copy_repo(parent, "legacy-scope-substitution")
    remove_old_outputs(repo)
    path, captured, issue, match = issue_contract(repo, SOURCE)
    replace_scope_id(path, captured, issue, match)
    result = run(repo, SOURCE + "/build_manifest.py")
    manifest_path = repo / SOURCE / "evidence-quality.json"
    manifest = json.loads(manifest_path.read_bytes())
    audit = json.loads((repo / SOURCE / "vintages/run-five/audit.json").read_bytes())
    audit_ids = {row["subject_id"] for row in audit["subject_rows"]}
    outputs = output_hashes(repo, [SOURCE + "/evidence-quality.json", SOURCE + "/reproducibility.json"])
    bad_ids = FOREIGN_ID in manifest["subject_ids"] and ACCEPTED_ID not in manifest["subject_ids"] and FOREIGN_ID not in audit_ids and ACCEPTED_ID in audit_ids
    if result["exit_code"] != 0 or not bad_ids:
        raise AssertionError("Original valid-index foreign-ID substitution was not accepted")
    results["original_valid_index_scope_substitution"] = {**result, "outputs": outputs,
        "foreign_id_in_manifest": FOREIGN_ID in manifest["subject_ids"], "accepted_id_in_run_audit": ACCEPTED_ID in audit_ids,
        "foreign_id_in_run_audit": FOREIGN_ID in audit_ids}
    return results


def fixed_controls(parent):
    results = {}
    output_names = [OWNED + "/" + name for name in ("reproducibility.json", "preservation.json", "evidence-quality.json")]

    for key, collision in (("first_output_collision", "reproducibility.json"), ("late_manifest_collision", "evidence-quality.json")):
        repo = copy_repo(parent, "fixed-" + key)
        sentinel = b"preserve this destination byte-for-byte\n"
        (repo / OWNED / collision).write_bytes(sentinel)
        result = run(repo, OWNED + "/build_manifest.py")
        hashes = output_hashes(repo, output_names)
        if result["exit_code"] == 0 or hashes != {OWNED + "/" + collision: {"bytes": len(sentinel), "sha256": digest(sentinel)}}:
            raise AssertionError("Corrected builder collision pre-admission changed output state")
        results[key] = {**result, "outputs": hashes}

    repo = copy_repo(parent, "fixed-contract-substitution")
    path, captured, issue, match = issue_contract(repo, OWNED)
    replace_scope_id(path, captured, issue, match)
    result = run(repo, OWNED + "/build_manifest.py")
    if result["exit_code"] == 0 or output_hashes(repo, output_names):
        raise AssertionError("Corrected builder accepted a changed current scope")
    results["changed_current_contract"] = {**result, "outputs": {}}

    repo = copy_repo(parent, "fixed-producer-drift")
    producer = repo / OWNED / "reproduce.py"
    producer.write_bytes(producer.read_bytes() + b"\n# deliberate post-run drift\n")
    result = run(repo, OWNED + "/build_manifest.py")
    if result["exit_code"] == 0 or output_hashes(repo, output_names):
        raise AssertionError("Corrected builder accepted post-run producer drift")
    results["producer_code_drift"] = {**result, "outputs": {}}

    repo = copy_repo(parent, "fixed-run-audit-substitution")
    audit_path = repo / OWNED / "vintages/run-nine/audit.json"
    audit = json.loads(audit_path.read_bytes())
    for row in audit["subject_rows"]:
        if row["subject_id"] == ACCEPTED_ID:
            row["subject_id"] = FOREIGN_ID
            break
    audit["subject_ids_sha256"] = digest(json.dumps(sorted(row["subject_id"] for row in audit["subject_rows"]), separators=(",", ":")).encode())
    audit_raw = (json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    audit_path.write_bytes(audit_raw)
    receipt_path = repo / OWNED / "vintages/run-nine/publication.json"
    receipt = json.loads(receipt_path.read_bytes())
    for row in receipt["outputs"]:
        if row["path"].endswith("/audit.json"):
            row["bytes"], row["sha256"] = len(audit_raw), digest(audit_raw)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    result = run(repo, OWNED + "/build_manifest.py")
    if result["exit_code"] == 0 or output_hashes(repo, output_names):
        raise AssertionError("Corrected builder accepted run output identity substitution")
    results["run_audit_identity_substitution"] = {**result, "outputs": {}}

    repo = copy_repo(parent, "fixed-helper-drift")
    helper = repo / "scripts/evidence/immutable.py"
    helper.write_bytes(helper.read_bytes() + b"\n# deliberate drift\n")
    result = run(repo, OWNED + "/build_manifest.py")
    if result["exit_code"] == 0 or output_hashes(repo, output_names):
        raise AssertionError("Corrected builder accepted materialized helper drift")
    results["helper_code_drift"] = {**result, "outputs": {}}

    repo = copy_repo(parent, "fixed-output-symlink")
    link_target = repo / "sentinel-target"
    link_target.write_bytes(b"sentinel\n")
    (repo / OWNED / "evidence-quality.json").symlink_to(link_target)
    result = run(repo, OWNED + "/build_manifest.py")
    if result["exit_code"] == 0 or output_hashes(repo, output_names):
        raise AssertionError("Corrected builder accepted output symlink")
    results["symlink_destination"] = {**result, "outputs": {}}

    repo = copy_repo(parent, "fixed-traversal-arg")
    result = run(repo, OWNED + "/build_manifest.py", args=("--manifest-path", "../escape.json"))
    if result["exit_code"] == 0 or output_hashes(repo, output_names):
        raise AssertionError("Corrected builder accepted traversal output argument")
    results["traversal_argument"] = {**result, "outputs": {}}

    repo = copy_repo(parent, "fixed-controlled-partial")
    env = dict(os.environ, WORLDATLAS_ENABLE_TEST_FAULT="1")
    result = run(repo, OWNED + "/build_manifest.py", args=("--test-fail-after-first-output",), env=env)
    hashes = output_hashes(repo, output_names)
    if result["exit_code"] == 0 or set(hashes) != {OWNED + "/reproducibility.json"}:
        raise AssertionError("Controlled publication failure did not preserve only its first partial output: " + json.dumps({"result": result, "outputs": hashes}, sort_keys=True))
    results["controlled_partial_publication"] = {**result, "outputs": hashes}

    repo = copy_repo(parent, "fixed-rerun")
    result = run(repo, OWNED + "/build_manifest.py")
    first = output_hashes(repo, output_names)
    completed = json.loads((repo / output_names[2]).read_bytes())
    _, snapshot, issue, marker = issue_contract(repo, OWNED)
    spec = json.loads(marker.group(1))
    declared_pins = spec.get("evidence_quality", {}).get("pins", {})
    for path, expected in declared_pins.items():
        if completed["baseline"]["pins"].get(path) != expected or completed["baseline"]["pin_files"].get(path) != {"path": path, "commit": "5fa15de475f17ff93e205b767857d1e41a30949e"}:
            raise AssertionError("Corrected manifest does not bind the exact issue-declared pin key/path: " + path)
    again = run(repo, OWNED + "/build_manifest.py")
    second = output_hashes(repo, output_names)
    if result["exit_code"] != 0 or again["exit_code"] == 0 or first != second or set(first) != set(output_names):
        raise AssertionError("Corrected builder positive/rerun behavior changed")
    results["corrected_complete_positive_and_rerun"] = {"first_exit_code": result["exit_code"],
        "rerun_exit_code": again["exit_code"], "issue_pin_paths_verified": len(declared_pins),
        "outputs_after_rerun": second}
    return results


def main():
    directory = ROOT / OWNED
    scratch = directory / ".controls-scratch"
    scratch.mkdir(exist_ok=False)
    placeholder = {"version": 1, "status": "control execution in progress"}
    receipt_path = directory / "cli-controls.json"
    if receipt_path.exists():
        raise FileExistsError("Refusing to overwrite an earlier controls receipt")
    receipt_path.write_text(json.dumps(placeholder, indent=2, sort_keys=True) + "\n")
    try:
        legacy = legacy_controls(scratch)
        fixed = fixed_controls(scratch)
        receipt = {"version": 1, "status": "passed", "python": subprocess.check_output([PYTHON, "--version"], text=True).strip(),
                   "runner_sha256": digest(Path(__file__).read_bytes()),
                   "legacy_builder_sha256": digest((ROOT / SOURCE / "build_manifest.py").read_bytes()),
                   "corrected_builder_sha256": digest((ROOT / OWNED / "build_manifest.py").read_bytes()),
                   "controls": {**legacy, **fixed},
                   "scope": "Disposable complete packet copies only; no original, accepted historical run or source file was modified."}
        receipt["superseded_first_actual_builder_output"] = json.loads(
            (directory / "controls/first-builder-rejection.json").read_bytes())
        receipt["superseded_second_actual_builder_output"] = json.loads(
            (directory / "controls/second-builder-rejection.json").read_bytes())
        receipt["superseded_third_actual_builder_output"] = json.loads(
            (directory / "controls/third-builder-rejection.json").read_bytes())
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"status": "passed", "controls": len(receipt["controls"]), "receipt_sha256": digest(receipt_path.read_bytes())}, indent=2))
    except Exception:
        receipt_path.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(scratch)


if __name__ == "__main__":
    main()
