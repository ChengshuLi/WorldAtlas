#!/usr/bin/env python3
"""Exercise the corrected producer/control boundaries without provider access."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = HERE.parents[3]
SOURCE = REPO / "research/geography/portugal-spain-official-boundaries-20261007"
OWNED = "research/geography/portugal-spain-official-boundaries-audit-followup-20261008/"
ANALYSIS = HERE / "run-analysis.py"
CONTROLS = HERE / "run-controls.py"
PYTHON = sys.executable


def run(script, args=(), **env_changes):
    env = dict(os.environ)
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHON": PYTHON, "WORLDATLAS_TEST_PYTHON": PYTHON})
    env.update({key: value for key, value in env_changes.items() if value is not None})
    for key, value in list(env_changes.items()):
        if value is None:
            env.pop(key, None)
    return subprocess.run([PYTHON, "-B", str(script), *args], cwd=REPO, env=env,
                          text=True, capture_output=True, check=False)


def require_rejected(label, result, expected_text):
    if result.returncode == 0 or expected_text not in (result.stdout + result.stderr):
        raise AssertionError(f"{label} did not reject as expected: rc={result.returncode}; {result.stdout[-500:]} {result.stderr[-500:]}")
    return {"id": label, "outcome": "rejected-as-expected", "exit_code": result.returncode,
            "reason_contains": expected_text}


def main():
    from runpy import run_path
    analysis = run_path(str(ANALYSIS), run_name="worldatlas_1482_probe_import")
    baseline, _ = analysis["packet_baseline"]()
    NewVintage = analysis["packet_baseline"].__globals__["NewVintage"]
    checks = []
    scope = json.loads((SOURCE / "inputs/scope.json").read_bytes())
    cases = {}

    changed = json.loads(json.dumps(scope)); changed["subject_ids"][-1] = changed["subject_ids"][0]
    cases["duplicate-missing-subject"] = (changed, "Duplicate, missing, or wrong exact subject roster")
    changed = json.loads(json.dumps(scope)); changed["families"][0]["component_ids"].pop()
    cases["missing-component"] = (changed, "Duplicate, missing, or wrong component identity")
    changed = json.loads(json.dumps(scope)); changed["families"][0]["id"] = "gap-source-batch:fabricated"
    cases["fabricated-family"] = (changed, "Unknown family identity")
    changed = json.loads(json.dumps(scope)); changed["families"][0]["contact_subjects"][0] = "gb:ESP:ADM3:wrong-parent"
    cases["wrong-family-subject-parent"] = (changed, "Duplicate, missing, or wrong family-subject incidence")
    changed = json.loads(json.dumps(scope)); changed["pinned_baseline_subject_files"][scope["subject_ids"][0]] = "data/geography/part-8.json"
    cases["wrong-subject-reference"] = (changed, "Wrong subject-to-reference part binding")

    with tempfile.TemporaryDirectory(prefix="worldatlas-1482-adverse-", dir=REPO / OWNED) as temporary:
        tmp = Path(temporary)
        for ordinal, (label, (value, expected)) in enumerate(cases.items(), 1):
            scope_file = tmp / f"scope-{ordinal}.json"
            scope_file.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            result = run(ANALYSIS, [f"run-{ordinal+2:02d}-r99"], WORLDATLAS_SCOPE_PATH=str(scope_file))
            checks.append(require_rejected(label + " at actual producer CLI", result, expected))
            result = run(CONTROLS, WORLDATLAS_SCOPE_PATH=str(scope_file),
                         WORLDATLAS_CONTROL_VINTAGE=f"control-probe-{ordinal}")
            checks.append(require_rejected(label + " at actual control CLI", result, expected))

        # Missing and altered original packet inputs fail at the actual producer's authenticated read boundary.
        missing_root = tmp / "missing-source"
        missing_root.mkdir()
        shutil.copyfile(SOURCE / "evidence-quality.json", missing_root / "evidence-quality.json")
        result = run(ANALYSIS, ["run-20-r99"], WORLDATLAS_SOURCE_ROOT=str(missing_root))
        checks.append(require_rejected("missing-original-source-input at actual producer CLI", result, "Original packet file missing or unsafe"))

        # Hard-link every immutable packet item and alter only a code input in the private fixture.
        tampered_root = tmp / "tampered-code"
        manifest = json.loads((SOURCE / "evidence-quality.json").read_bytes())
        prefix = "research/geography/portugal-spain-official-boundaries-20261007/"
        for row in manifest["outputs"]:
            relative = row["path"].split(prefix, 1)[1]
            source_file = SOURCE / relative
            target = tampered_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if relative == "scripts/run-analysis.py":
                target.write_bytes(source_file.read_bytes() + b"\n# altered input canary\n")
            else:
                os.link(source_file, target)
        shutil.copyfile(SOURCE / "evidence-quality.json", tampered_root / "evidence-quality.json")
        result = run(ANALYSIS, ["run-21-r99"], WORLDATLAS_SOURCE_ROOT=str(tampered_root))
        checks.append(require_rejected("altered-consumed-code at actual producer CLI", result, "Original packet evidence changed"))

        # A candidate that refreshes its own scope output hash still cannot replace the immutable packet manifest pin.
        refreshed_root = tmp / "refreshed-scope-hash"
        for row in manifest["outputs"]:
            relative = row["path"].split(prefix, 1)[1]
            source_file = SOURCE / relative
            target = refreshed_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if relative == "inputs/scope.json":
                changed = json.loads(source_file.read_bytes())
                changed["subject_ids"][-1] = changed["subject_ids"][0]
                body = json.dumps(changed, ensure_ascii=False).encode()
                target.write_bytes(body)
                row["bytes"], row["sha256"] = len(body), hashlib.sha256(body).hexdigest()
            else:
                os.link(source_file, target)
        refreshed_manifest = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        (refreshed_root / "evidence-quality.json").write_bytes(refreshed_manifest)
        result = run(ANALYSIS, ["run-22-r99"], WORLDATLAS_SOURCE_ROOT=str(refreshed_root))
        checks.append(require_rejected("coherently-refreshed-candidate-scope-hash at actual producer CLI", result, "Original source packet manifest hash mismatch"))

    # Filesystem collision canaries invoke the actual control entrypoint. The symlink points only to an owned sentinel.
    vintages = REPO / OWNED / "vintages"
    fixtures = REPO / OWNED / "fixtures"
    fixtures.mkdir(exist_ok=True)
    sentinel = fixtures / "collision-sentinel.txt"
    sentinel_bytes = b"preserve-existing-control-output\n"
    sentinel.write_bytes(sentinel_bytes)
    collision_root = vintages / "controls-ordinary-collision"
    collision_root.mkdir(exist_ok=True)
    collision_file = collision_root / "positive-control.json"
    collision_file.write_bytes(sentinel_bytes)
    result = run(CONTROLS, WORLDATLAS_CONTROL_VINTAGE="controls-ordinary-collision")
    checks.append(require_rejected("ordinary-control-output-collision at actual control CLI", result, "Evidence already exists"))
    if collision_file.read_bytes() != sentinel_bytes:
        raise AssertionError("Ordinary collision sentinel changed")

    live_link = vintages / "controls-live-symlink"
    live_link.symlink_to(sentinel.parent, target_is_directory=True)
    result = run(CONTROLS, WORLDATLAS_CONTROL_VINTAGE="controls-live-symlink")
    checks.append(require_rejected("live-symlink-output-collision at actual control CLI", result, "Symlink in output path"))
    if sentinel.read_bytes() != sentinel_bytes or not live_link.is_symlink():
        raise AssertionError("Live symlink collision modified its target")
    live_link.unlink()

    broken_link = vintages / "controls-broken-symlink"
    broken_link.symlink_to(fixtures / "no-such-target")
    result = run(CONTROLS, WORLDATLAS_CONTROL_VINTAGE="controls-broken-symlink")
    checks.append(require_rejected("broken-symlink-output-collision at actual control CLI", result, "Symlink in output path"))
    if not broken_link.is_symlink() or sentinel.read_bytes() != sentinel_bytes:
        raise AssertionError("Broken symlink collision modified the sentinel")
    broken_link.unlink()

    # Probe the actual retained science vintage; this must already exist or the
    # producer would accept a fresh run and make the collision check vacuous.
    result = run(ANALYSIS, ["run-01-r5"])
    checks.append(require_rejected("producer-rerun-collision", result, "Evidence already exists"))
    result = run(CONTROLS, WORLDATLAS_CONTROL_VINTAGE="../escaped")
    checks.append(require_rejected("output-path-traversal at actual control CLI", result, "Use a safe fresh control vintage"))

    # Inject failure only after actual geometry calculations; no run completion receipt may appear.
    failed_name = "run-03-r99"
    failure_vintage = vintages / (failed_name + "-failed-" + hashlib.sha256((HERE / "run-analysis.py").read_bytes()).hexdigest()[:12])
    if not (failure_vintage / "failure.json").is_file():
        result = run(ANALYSIS, [failed_name], WORLDATLAS_FAIL_AFTER_COMPUTE=failed_name)
        checks.append(require_rejected("post-computation-failure", result, "Injected post-computation failure control"))
    else:
        checks.append({"id": "post-computation-failure", "outcome": "retained-actual-failure-record"})
    failure_record = failure_vintage / "failure.json"
    failure_receipt = failure_vintage / "publication.json"
    if not failure_record.is_file() or not failure_receipt.is_file() or json.loads(failure_record.read_bytes()).get("outcome") != "failed":
        raise AssertionError("Post-computation failure did not retain an honest failure record")
    published_failure = json.loads(failure_receipt.read_bytes())
    failure_outputs = published_failure.get("outputs", [])
    if len(failure_outputs) != 14 or any(row["path"].endswith("execution-receipt.json") for row in failure_outputs):
        raise AssertionError("Post-computation failure did not preserve all science outputs without a success receipt")
    for row in failure_outputs:
        target = REPO / row["path"]
        raw = target.read_bytes()
        if target.is_symlink() or len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise AssertionError("Retained failed-attempt output differs from its completion inventory")

    report = {"version": 1, "issue": 1482, "kind": "actual-entrypoint-adverse-controls",
              "outcome": "passed", "checks": checks,
              "sentinel": {"path": str(collision_file.relative_to(REPO)), "bytes": len(sentinel_bytes),
                           "sha256": hashlib.sha256(sentinel_bytes).hexdigest(), "unchanged": True},
              "post_computation_failure": {"vintage": str(failure_vintage.relative_to(REPO)),
                  "failure_record_sha256": hashlib.sha256(failure_record.read_bytes()).hexdigest(),
                  "successful_run_receipt_present": False},
              "limits": ["All producer probes use retained local packet bytes and immutable Git reads; no provider request or GitHub credential is passed to scientific commands."]}
    # The complete adversarial report is written inside the declared research namespace.
    # Preserve the canary bytes and collision result in the report, then remove test fixtures.
    shutil.rmtree(collision_root)
    shutil.rmtree(fixtures)
    report_vintage = "adverse-controls-r4"
    while (vintages / report_vintage).exists() or (vintages / report_vintage).is_symlink():
        number = int(report_vintage.rsplit("r", 1)[1]) + 1
        report_vintage = f"adverse-controls-r{number}"
    report_path = REPO / OWNED / "vintages" / report_vintage / "adverse-controls.json"
    publisher = NewVintage(baseline, OWNED, report_vintage, ["adverse-controls.json"])
    publisher.publish({"adverse-controls.json": report})
    print(json.dumps({"outcome": report["outcome"], "check_count": len(checks), "report": str(report_path.relative_to(REPO))}, sort_keys=True))


if __name__ == "__main__":
    main()
