#!/usr/bin/env python3
"""Reproduce the merged runner and its missing executable-pin rejection."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PACKET = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
BASELINE_COMMIT = "643e4123ce9881a9d07f564166edae34aec7aa08"
ISSUE_BODY_SHA256 = "043bc67f66df53f60f2ac8b5d52b0a62fa71fb13556dd3bdf4f9e5d62cc91f71"
CAPSULE_SHA256 = "5b3787d9f07373751d2bbd5a94acec41eab79de43732cd4f6c45e2fd72c3d873"
HELPER_SHA256 = "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46"
PREFIX = "data/regional-review/uruguay-artigas-contested-guard-erratum/"
sys.path.insert(0, str(REPO))
from scripts.evidence.immutable import Baseline, sha256


def issue_spec():
    raw = (PACKET / "inputs/issue-1413-api.json").read_bytes()
    issue = json.loads(raw)
    body = issue["body"].encode("utf-8")
    if sha256(body) != ISSUE_BODY_SHA256:
        raise ValueError("captured live issue body differs from the audited contract")
    marker = "<!-- worldatlas-work:v1\n"
    start = body.decode().index(marker) + len(marker)
    end = body.decode().index("\n-->", start)
    return json.loads(body.decode()[start:end])


def make_baseline():
    spec = issue_spec()
    pins = dict(spec["evidence_quality"]["pins"])
    capsule_path = PREFIX + "inputs/code/capsule-reproduce.py"
    if pins.get(capsule_path) != CAPSULE_SHA256:
        raise ValueError("issue does not anchor the retained capsule bytes")
    manifest_path = PREFIX + "evidence-quality.json"
    raw_manifest = subprocess.check_output(["git", "-C", str(REPO), "show", f"{BASELINE_COMMIT}:{manifest_path}"])
    if sha256(raw_manifest) != pins.get(manifest_path):
        raise ValueError("the parent capsule manifest differs from the issue pin")
    capsule_entries = json.loads(raw_manifest)["capsule"]
    for rel, expected in capsule_entries.items():
        path = PREFIX + rel
        if path in pins and pins[path] != expected:
            raise ValueError("issue pin and parent capsule manifest disagree: " + rel)
        pins[path] = expected
    pins["scripts/evidence/immutable.py"] = HELPER_SHA256
    files = []
    for path, expected in pins.items():
        raw = subprocess.check_output(["git", "-C", str(REPO), "show", f"{BASELINE_COMMIT}:{path}"])
        if sha256(raw) != expected:
            raise ValueError("immutable pin differs from issue contract: " + path)
        files.append({"path": path, "bytes": len(raw), "sha256": expected, "hash_kind": "file-bytes"})
    baseline = Baseline(REPO, BASELINE_COMMIT, files)
    for path in pins:
        if baseline.materialized_bytes(path) != baseline.pinned_bytes(path):
            raise ValueError("materialized original differs from immutable pin: " + path)
    return spec, baseline, pins


SPEC, BASELINE, PIN_MAP = make_baseline()
SOURCE_PREFIX = PREFIX + ""
REL_PINNED_FILES = [path[len(PREFIX):] for path in PIN_MAP if path.startswith(PREFIX)]
LEGACY_PATHS = REL_PINNED_FILES
RESULTS = PACKET / "controls/original-runner-audit-v2.json"
LOGS = PACKET / "controls/original-runner-logs-v2"
FIXTURES = PACKET / "controls/original-runner-fixtures-v2"
PROBE = b'\n(Path(OUT) / "audit-unreviewed-code.txt").write_text("executed\\n", encoding="utf-8")\n'


def exclusive_bytes(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def new_fixture(name):
    root = FIXTURES / name
    if root.exists() or root.is_symlink():
        raise FileExistsError("preserve existing fixture and choose a new audit name")
    root.mkdir(parents=True)
    for rel in LEGACY_PATHS:
        source = PREFIX + rel
        raw = BASELINE.pinned_bytes(source)
        exclusive_bytes(root / rel, raw)
    manifest = json.loads((root / "evidence-quality.json").read_bytes())
    if not set(manifest["capsule"]).issubset(set(LEGACY_PATHS)):
        raise ValueError("fixture is missing a retained capsule file")
    (root / "outputs").mkdir()
    return root


def log_process(name, result):
    exclusive_bytes(LOGS / (name + ".stdout.txt"), result.stdout)
    exclusive_bytes(LOGS / (name + ".stderr.txt"), result.stderr)


def attempt(name, root, target):
    runner = root / "reproduce.py"
    result = subprocess.run([sys.executable, str(runner), "--output", str(target)], cwd=REPO,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    log_process(name, result)
    return result


def digest(path):
    return sha256(path.read_bytes()) if path.is_file() and not path.is_symlink() else None


def run_success(root, run_id, name):
    target = root / "outputs" / run_id
    result = attempt(name, root, target)
    report = target / "reproduction-results.json"
    expected = BASELINE.pinned_bytes(PREFIX + "inputs/original-reproduction-results.json")
    observed = report.read_bytes() if report.is_file() and not report.is_symlink() else None
    return {"case": name, "exit_code": result.returncode,
            "report_sha256": sha256(observed) if observed is not None else None,
            "matches_original_report": observed == expected,
            "output_files": sorted(p.name for p in target.iterdir()) if target.is_dir() else [],
            "probe_sha256": digest(target / "audit-unreviewed-code.txt") if target.is_dir() else None}


def expect_rejection(name, root, target, sentinel=None):
    before = sorted(p.name for p in target.parent.iterdir())
    sentinel_hash = digest(sentinel) if sentinel else None
    result = attempt(name, root, target)
    after = sorted(p.name for p in target.parent.iterdir())
    unchanged = before == after and (digest(sentinel) == sentinel_hash if sentinel else True)
    return {"case": name, "exit_code": result.returncode, "rejected": result.returncode != 0,
            "output_namespace_unchanged": unchanged, "sentinel_sha256": sentinel_hash}


def mutate_capsule(root):
    path = root / "inputs/code/capsule-reproduce.py"
    with path.open("ab") as stream:
        stream.write(PROBE)
        stream.flush()
        os.fsync(stream.fileno())


def mutate_manifest(root, mode):
    path = root / "evidence-quality.json"
    value = json.loads(path.read_bytes())
    key = "inputs/code/capsule-reproduce.py"
    if mode == "remove":
        value["capsule"].pop(key)
    elif mode == "refresh":
        value["capsule"][key] = digest(root / key)
    else:
        raise ValueError(mode)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main():
    if RESULTS.exists() or LOGS.exists() or FIXTURES.exists():
        raise FileExistsError("audit outputs already exist; preserve them and use a new runner version")
    LOGS.mkdir()
    observations = []

    valid = new_fixture("baseline-two-runs")
    observations.append(run_success(valid, "fresh-one", "baseline-fresh-run-one"))
    observations.append(run_success(valid, "fresh-two", "baseline-fresh-run-two"))

    missing = new_fixture("missing-code-pin")
    mutate_manifest(missing, "remove")
    observations.append(run_success(missing, "missing-pin-output", "missing-executable-pin"))

    removed = new_fixture("removed-pin-probe")
    mutate_capsule(removed)
    mutate_manifest(removed, "remove")
    observations.append(run_success(removed, "removed-pin-output", "removed-pin-altered-code"))

    refreshed = new_fixture("refreshed-pin-probe")
    mutate_capsule(refreshed)
    mutate_manifest(refreshed, "refresh")
    observations.append(run_success(refreshed, "refreshed-pin-output", "coherently-refreshed-pin-altered-code"))

    drift = new_fixture("ordinary-code-drift")
    mutate_capsule(drift)
    observations.append(expect_rejection("ordinary-code-drift", drift, drift / "outputs" / "drift"))

    wrong_input = new_fixture("wrong-complete-input")
    with (wrong_input / "inputs/sources/ury-gb-2017.geojson").open("ab") as stream:
        stream.write(b" ")
    observations.append(expect_rejection("wrong-complete-input", wrong_input, wrong_input / "outputs" / "wrong-input"))

    safety = new_fixture("output-safety")
    existing = safety / "outputs" / "existing"
    existing.mkdir()
    sentinel = existing / "keep.txt"
    exclusive_bytes(sentinel, b"preserve-me\n")
    observations.append(expect_rejection("existing-output-sentinel", safety, existing, sentinel))

    broken = safety / "outputs" / "broken-link"
    broken.symlink_to(safety / "missing-target", target_is_directory=True)
    observations.append(expect_rejection("broken-symlink", safety, broken))
    if not broken.is_symlink() or broken.exists():
        raise AssertionError("broken symlink fixture changed")

    escape = safety / "outputs" / "symlink-parent-escape"
    outside = safety / "outside"
    outside.mkdir()
    held = safety / "outputs-held"
    (safety / "outputs").rename(held)
    (safety / "outputs").symlink_to(outside, target_is_directory=True)
    observations.append(expect_rejection("symlink-parent-escape", safety, escape))
    outside_items = sorted(p.name for p in outside.iterdir())
    (safety / "outputs").unlink()
    held.rename(safety / "outputs")
    if outside_items:
        raise AssertionError("symlink parent wrote outside its owned fixture")

    traversal = safety / "outputs" / ".." / "traversal-escape"
    observations.append(expect_rejection("traversal", safety, traversal))

    for path, expected in PIN_MAP.items():
        if BASELINE.materialized_bytes(path) != BASELINE.pinned_bytes(path):
            raise AssertionError("retained original changed during audit: " + path)
    passed_baseline = all(x["exit_code"] == 0 and x["matches_original_report"] for x in observations[:4])
    result = {
        "version": 1, "issue": 1413, "date": "2026-10-07", "baseline_commit": BASELINE_COMMIT,
        "issue_body_sha256": ISSUE_BODY_SHA256, "capsule_sha256": CAPSULE_SHA256,
        "helper_version": "worldatlas-evidence-preparation-v1", "helper_sha256": HELPER_SHA256,
        "runtime": {"python": sys.version, "executable": sys.executable},
        "pinned_files_checked": len(PIN_MAP), "source_phase_bytes": sum(x["bytes"] for x in BASELINE.pins.values()),
        "observations": observations, "all_original_pins_unchanged": True,
        "finding": "The merged runner accepts an omitted required capsule pin and accepts altered executed capsule code when the mutable manifest pin is removed or coherently refreshed; actual probe bytes are recorded in the two output directories.",
        "baseline_runs_reproduced": passed_baseline,
        "limits": ["These runs reproduce the retained offline representation only; no territorial, legal, current-boundary, source-reuse, or sovereignty conclusion is made."]
    }
    exclusive_bytes(RESULTS, (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    print(json.dumps({"audit": str(RESULTS.relative_to(REPO)), "observations": len(observations),
                      "baseline_runs_reproduced": passed_baseline,
                      "adversarial_probes": sum(bool(x.get("probe_sha256")) for x in observations)}))


if __name__ == "__main__":
    main()
