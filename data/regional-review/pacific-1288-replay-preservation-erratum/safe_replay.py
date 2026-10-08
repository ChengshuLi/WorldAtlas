#!/usr/bin/env python3
"""Run the historical Pacific replay only in an admitted private vintage."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
OWNED = "data/regional-review/pacific-1288-replay-preservation-erratum/"
VINTAGE = "replay-20261008-08"
SOURCE = "7962b56b08e21c581b5d4034fe3616da5f87efd7"
MERGE = "249e396178cfc160fd547ec4487c5d94832fc9af"
BASE = "a57085b7a5cfdbe3c1e0e4b0cd2e07c6240899fc"
PYTHON = os.environ.get("WORLDATLAS_PYTHON", sys.executable)
OLD = "data/regional-review/south-central-pacific-405-scope-validation-1054-erratum"
PACK = "data/regional-review/regional-review-14a242c4cb0781a7"
REPORTS = ("geometry-comparison.json", "geometry-controls.json", "geocode-screen.json")
MARKERS = {
    "reproduction-results.json": b"owned-existing-replay-marker\n",
    "positive-validation.json": b"owned-existing-replay-marker\n",
    "runs/run-1/geometry-comparison.json": b"owned-existing-replay-marker\n",
}

sys.path.insert(0, str(REPO / "scripts"))
from evidence.immutable import Baseline, NewVintage, descriptor  # noqa: E402


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(REPO), *args], stderr=subprocess.PIPE)


def tree_paths(commit: str, prefix: str) -> list[str]:
    return git("ls-tree", "-r", "--name-only", commit, "--", prefix).decode().splitlines()


def blob(commit: str, path: str) -> bytes:
    return git("show", f"{commit}:{path}")


def pin_inventory() -> tuple[list[dict], dict[str, bytes], dict[str, int]]:
    commit_by_path = {path: SOURCE for path in tree_paths(SOURCE, OLD)}
    commit_by_path.update({path: MERGE for path in tree_paths(MERGE, PACK)})
    # The immutable baseline role inventory and the scientific modules consumed
    # by verify.py are read from their original commits, never from the checkout.
    baseline_doc = json.loads(blob(MERGE, f"{PACK}/baseline-inputs.json"))
    for row in baseline_doc["files"]:
        commit_by_path[row["path"]] = BASE
    for path in ("scripts/evidence/geometry.py", "scripts/ellipsoidal_area.py"):
        commit_by_path[path] = BASE
    raw_by_path = {}
    for path, commit in sorted(commit_by_path.items()):
        raw = blob(commit, path)
        raw_by_path[path] = raw
    descriptors = [{**descriptor(path, raw_by_path[path]), "commit": commit_by_path[path]} for path in raw_by_path]
    # Authenticate the multi-vintage pins at their declared commits before any
    # output admission. The output writer itself uses BASE's complete input set.
    verified = []
    for row in descriptors:
        verified.append({k: row[k] for k in ("path", "bytes", "sha256", "hash_kind", "commit")})
    modes = {}
    for commit in (SOURCE, MERGE, BASE):
        for line in git("ls-tree", "-r", commit).decode().splitlines():
            mode, path = line.split("\t", 1)[0].split()[0], line.split("\t", 1)[1]
            if commit_by_path.get(path) == commit:
                modes[path] = 0o755 if mode == "100755" else 0o644
    if set(modes) != set(raw_by_path):
        raise RuntimeError("Source mode inventory is incomplete")
    return verified, raw_by_path, modes


def write_file(root: Path, name: str, raw: bytes) -> None:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)


def mirror(root: Path, pinned: dict[str, bytes], modes: dict[str, int], *, markers: bool) -> Path:
    repo = root / "repo"
    for path, raw in pinned.items():
        # Materialize complete original packets and the precise baseline/code
        # inputs, preserving their repository-relative paths.
        write_file(repo, path, raw)
        (repo / path).chmod(modes[path])
    gitdir = git("rev-parse", "--absolute-git-dir").decode().strip()
    (repo / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
    packet = repo / OLD
    if markers:
        for name, raw in MARKERS.items():
            write_file(packet, name, raw)
    return repo


def run_legacy(repo: Path, capture_dir: Path, *, label: str, markers: bool) -> dict:
    capture_dir.mkdir(parents=True, exist_ok=True)
    # Patch only the parent process's subprocess.run observer. The original
    # reproduce.py and verify.py files remain byte-identical and execute as-is.
    instrument = capture_dir / "instrument"
    instrument.mkdir()
    (instrument / "sitecustomize.py").write_text(
        "import json, os, pathlib, subprocess\n"
        "_run = subprocess.run\n"
        "_cap = pathlib.Path(os.environ['WA_CAPTURE_DIR'])\n"
        "_n = 0\n"
        "def _record(args, *a, **kw):\n"
        " global _n\n"
        " result = _run(args, *a, **kw)\n"
        " argv = args if isinstance(args, (list, tuple)) else []\n"
        " if len(argv) > 1 and str(argv[1]).endswith('/verify.py'):\n"
        "  _n += 1; stem = f'verifier-{_n:02d}'\n"
        "  def raw(value):\n"
        "   if value is None: return b''\n"
        "   return value if isinstance(value, bytes) else value.encode()\n"
        "  (_cap / (stem + '.stdout')).write_bytes(raw(result.stdout))\n"
        "  (_cap / (stem + '.stderr')).write_bytes(raw(result.stderr))\n"
        "  (_cap / (stem + '.json')).write_text(json.dumps({'argv': list(map(str, argv)), 'returncode': result.returncode}, sort_keys=True) + '\\n')\n"
        " return result\n"
        "subprocess.run = _record\n",
        encoding="utf-8",
    )
    tempdir = capture_dir / "tmp"
    tempdir.mkdir()
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(capture_dir),
        "PYTHONUSERBASE": "/Users/chengshuli/.local",
        "TMPDIR": str(tempdir),
        "PYTHONPATH": str(instrument),
        "PYTHONDONTWRITEBYTECODE": "1",
        "WA_CAPTURE_DIR": str(capture_dir),
    }
    command = [PYTHON, str(repo / OLD / "reproduce.py")]
    result = subprocess.run(command, cwd=repo, env=env, capture_output=True)
    (capture_dir / f"{label}-stdout.bin").write_bytes(result.stdout)
    (capture_dir / f"{label}-stderr.bin").write_bytes(result.stderr)
    attempts = []
    for sidecar in sorted(capture_dir.glob("verifier-*.json")):
        record = json.loads(sidecar.read_text())
        stem = sidecar.stem
        stdout = (capture_dir / f"{stem}.stdout").read_bytes()
        stderr = (capture_dir / f"{stem}.stderr").read_bytes()
        attempts.append({
            "argv": record["argv"], "returncode": record["returncode"],
            "stdout_path": f"attempts/{label}/{stem}.stdout",
            "stderr_path": f"attempts/{label}/{stem}.stderr",
            "stdout_sha256": sha(stdout), "stdout_bytes": len(stdout),
            "stderr_sha256": sha(stderr), "stderr_bytes": len(stderr),
        })
    return {
        "label": label,
        "marker_case": markers,
        "command": command,
        "returncode": result.returncode,
        "stdout_path": f"attempts/{label}/runner.stdout",
        "stderr_path": f"attempts/{label}/runner.stderr",
        "stdout_sha256": sha(result.stdout), "stdout_bytes": len(result.stdout),
        "stderr_sha256": sha(result.stderr), "stderr_bytes": len(result.stderr),
        "verifier_attempts": attempts,
        "failure_stdout": result.stdout.decode("utf-8", "replace")[-4000:] if result.returncode else "",
        "failure_stderr": result.stderr.decode("utf-8", "replace")[-4000:] if result.returncode else "",
    }


def collect_case(repo: Path, label: str, expected: dict[str, bytes], expected_modes: dict[str, int]) -> tuple[dict, dict[str, bytes]]:
    changes, manifest = {}, []
    for relative in tree_paths(SOURCE, OLD):
        path = repo / relative
        original = expected[relative]
        current = path.read_bytes() if path.is_file() else None
        mode = path.stat().st_mode & 0o777 if path.exists() else None
        manifest.append({"path": relative, "source_bytes": len(original), "source_sha256": sha(original),
            "source_mode": expected_modes[relative], "post_bytes": len(current) if current is not None else None,
            "post_sha256": sha(current) if current is not None else None, "post_mode": mode,
            "bytes_preserved": current == original, "mode_preserved": mode == expected_modes[relative]})
        if current is not None and current != original:
            name = relative.removeprefix(OLD + "/")
            changes[f"cases/{label}/{name}"] = current
    return {"changed_files": len(changes), "changed_bytes": sum(map(len, changes.values())), "path_manifest": manifest}, changes


def collect_attempt_artifacts(repo: Path, label: str) -> tuple[dict, dict[str, bytes]]:
    """Preserve the original producer's generated receipts, fixtures and reports."""
    packet = repo / OLD
    targets = ["inputs/expected-subjects.json", "inputs/scope.json",
        "positive-validation.json", "negative-validation.json",
        "reproducibility-validation.json", "reproduction-results.json"]
    files = []
    for prefix in ("controls", "pinned-inputs", "runs/run-1", "runs/run-2"):
        files.extend(p.relative_to(packet).as_posix() for p in sorted((packet / prefix).rglob("*")) if p.is_file())
    files.extend(name for name in targets if (packet / name).is_file())
    payloads, records = {}, []
    for relative in sorted(set(files)):
        raw = (packet / relative).read_bytes()
        key = f"cases/{label}/producer-artifacts/{relative}"
        payloads[key] = raw
        records.append({"path": relative, "bytes": len(raw), "sha256": sha(raw), "output_path": key})
    return {"file_count": len(records), "raw_bytes": sum(row["bytes"] for row in records), "files": records}, payloads


def run_scope_cli(repo: Path, capture: Path, *, include_negatives: bool = True, positive_name: str = "valid") -> list[dict]:
    """Exercise the documented validator CLI on one valid and nine bad inputs."""
    packet = repo / OLD
    script = packet / "scope-validator.py"
    inputs = packet / "inputs"
    references = packet / "pinned-inputs"
    cases = [(positive_name, inputs / "scope.json", references, 0)]
    for name in ((
        "24-entry-duplicate", "equal-length-duplicate-replacement-rehashed",
        "missing-subject", "foreign-subject", "wrong-declared-count",
    ) if include_negatives else ()):
        cases.append((name, packet / "controls" / f"{name}.json", references, 1))
    for name in ((
        "missing-location-row", "wrong-parent-crosswalk",
        "area-member-count-mismatch", "area-member-substitution",
    ) if include_negatives else ()):
        cases.append((name, inputs / "scope.json", packet / "controls" / name, 1))
    results = []
    capture.mkdir(parents=True, exist_ok=True)
    for name, scope, rows, expected in cases:
        result = subprocess.run([PYTHON, str(script), str(scope), str(rows)], cwd=repo, capture_output=True)
        for stream, raw in (("stdout", result.stdout), ("stderr", result.stderr)):
            (capture / f"{name}.{stream}").write_bytes(raw)
        if result.returncode != expected:
            raise RuntimeError(f"scope-validator CLI {name} returned {result.returncode}, expected {expected}: {result.stdout[-1000:]!r} {result.stderr[-1000:]!r}")
        results.append({"case": name, "expected_returncode": expected, "actual_returncode": result.returncode,
            "stdout_path": f"attempts/scope-cli/{name}.stdout", "stderr_path": f"attempts/scope-cli/{name}.stderr",
            "stdout_bytes": len(result.stdout), "stdout_sha256": sha(result.stdout),
            "stderr_bytes": len(result.stderr), "stderr_sha256": sha(result.stderr)})
    return results


def destination_controls(baseline: Baseline) -> list[dict]:
    """Exercise destination rejection against private sentinels before replay."""
    root = ROOT / "vintages"
    root.mkdir(exist_ok=True)
    controls = []
    for label in ("existing-file", "existing-directory", "partial-conflict", "live-symlink", "broken-symlink"):
        name = "control-" + label
        dest = root / name
        sentinel = dest / "attempts.json"
        if label in ("existing-file", "partial-conflict"):
            dest.mkdir()
            sentinel.write_bytes(b"preserve-existing-sentinel\n")
        elif label == "existing-directory":
            dest.mkdir()
        elif label == "live-symlink":
            target = root / "control-live-target"
            target.mkdir(exist_ok=True)
            dest.symlink_to(target, target_is_directory=True)
        else:
            dest.symlink_to(root / "missing-target", target_is_directory=True)
        before = sentinel.read_bytes() if sentinel.exists() else None
        try:
            NewVintage(baseline, OWNED, name, ["attempts.json", "case-changes.json"])
        except (ValueError, FileExistsError) as exc:
            rejected, reason = True, str(exc)
        else:
            rejected, reason = False, "unexpectedly admitted"
        after = sentinel.read_bytes() if sentinel.exists() else None
        if not rejected or before != after:
            raise RuntimeError(f"Unsafe destination control failed: {label}")
        controls.append({"case": label, "rejected": rejected, "reason": reason, "sentinel_unchanged": before == after})
        if dest.is_symlink():
            dest.unlink()
        elif dest.exists():
            shutil.rmtree(dest)
    target = root / "control-live-target"
    if target.exists():
        shutil.rmtree(target)
    try:
        NewVintage(baseline, OWNED, "control-traversal", ["../escape.json"])
    except ValueError as exc:
        controls.append({"case": "traversal", "rejected": True, "reason": str(exc), "sentinel_unchanged": True})
    else:
        raise RuntimeError("Traversal destination control was accepted")
    return controls


def main() -> None:
    # Destination conflicts are rejected before any source computation/replay.
    pins, contents, modes = pin_inventory()
    immutable_pins = [row for row in pins if row["commit"] == BASE]
    immutable = Baseline(REPO, BASE, immutable_pins)
    for row in pins:
        if row["commit"] != BASE:
            immutable.admit("external:" + row["commit"] + ":" + row["path"], row["bytes"])
    safe_destination_checks = destination_controls(immutable)
    files = ["attempts.json", "case-changes.json", "replay-summary.json", "scope.json"]
    # A bounded output inventory cannot be guessed after compute. Pre-admit
    # named products; raw attempt streams go in per-attempt JSONL envelopes.
    vintage = NewVintage(immutable, OWNED, VINTAGE, files)
    scratch_root = Path(tempfile.mkdtemp(prefix=".replay-scratch-", dir=ROOT))
    published = False
    try:
        expected_packet = {p: contents[p] for p in tree_paths(SOURCE, OLD)}
        cases, payloads, all_attempts = [], {}, []
        for label, has_markers in (("fresh-1", False), ("fresh-2", False), ("existing-markers", True)):
            area = scratch_root / label
            repo = mirror(area, contents, modes, markers=has_markers)
            capture = area / "captured"
            attempt = run_legacy(repo, capture, label=label, markers=has_markers)
            all_attempts.append(attempt)
            # Copy actual streams into memory before any branch can raise and
            # before scratch cleanup. A nonzero historical command is itself
            # useful replay evidence and must leave a durable, hash-bound run.
            for suffix, filename in (("stdout", f"{label}-stdout.bin"), ("stderr", f"{label}-stderr.bin")):
                payloads[attempt[f"{suffix}_path"]] = (capture / filename).read_bytes()
            for item in attempt["verifier_attempts"]:
                for suffix in ("stdout", "stderr"):
                    target = capture / Path(item[suffix + "_path"]).name
                    payloads[item[suffix + "_path"]] = target.read_bytes()
            if attempt["returncode"] != 0:
                from base64 import b64encode
                from evidence.immutable import canonical_json
                failure_summary = {
                    "issue": 1463, "worker_id": "01a10947-7d6e-7ba2-98a1-a9f91dedabfc",
                    "status": "replay_failed_after_capturing_actual_attempt",
                    "failed_label": label, "failed_returncode": attempt["returncode"],
                    "runner_code": {"path": str(Path(__file__).resolve().relative_to(REPO)), "bytes": len(Path(__file__).read_bytes()), "sha256": sha(Path(__file__).read_bytes())},
                    "source_commit": SOURCE, "affected_merge": MERGE, "baseline_commit": BASE,
                    "geographic_approval": "unapproved; replay is mechanical only",
                }
                attempt_bundle = {
                    "version": 1, "attempts": all_attempts, "scope_validator_cli": [],
                    "raw_streams": {name: b64encode(raw).decode("ascii") for name, raw in payloads.items()},
                }
                empty_cases = {"version": 1, "cases": [], "original_input_count": len(expected_packet),
                    "destination_controls": safe_destination_checks, "raw_changed_files": {}}
                failure_values = {
                    "attempts.json": canonical_json(attempt_bundle),
                    "case-changes.json": canonical_json(empty_cases),
                    "replay-summary.json": canonical_json(failure_summary),
                    "scope.json": canonical_json({"subject_ids": json.loads(contents[f"{OLD}/inputs/expected-subjects.json"]), "count": 23, "vintage": VINTAGE}),
                }
                vintage.publish_bytes(failure_values)
                published = True
                raise RuntimeError(f"Historical CLI returned {attempt['returncode']} in {label}; actual streams were preserved in {VINTAGE}")
            if len(attempt["verifier_attempts"]) != 3:
                raise RuntimeError(f"Expected exactly three actual original verifier processes in {label}")
            if has_markers:
                overwritten = {}
                for rel, sentinel in MARKERS.items():
                    after = (repo / OLD / rel).read_bytes()
                    overwritten[rel] = {"before_sha256": sha(sentinel), "after_sha256": sha(after), "marker_replaced": after != sentinel}
                    payloads[f"cases/{label}/{rel}"] = after
                if not all(row["marker_replaced"] for row in overwritten.values()):
                    raise RuntimeError("Expected original writer to replace all three private sentinels")
                marker_reports = {}
                for run_name in ("run-1", "run-2"):
                    for name in REPORTS:
                        output = (repo / OLD / "runs" / run_name / name).read_bytes()
                        expected = contents[f"{PACK}/{name}"]
                        if output != expected:
                            raise RuntimeError(f"Marker case output differs from original: {run_name}/{name}")
                        payloads[f"cases/{label}/{run_name}/{name}"] = output
                        marker_reports[f"{run_name}/{name}"] = {"bytes": len(output), "sha256": sha(output), "exact_original_bytes": True}
                cases.append({"label": label, "result": "confirmed-original-overwrite", "markers": overwritten, "reports": marker_reports})
            else:
                report_records = {}
                expected = {name: contents[f"{PACK}/{name}"] for name in REPORTS}
                for run_name in ("run-1", "run-2"):
                    for name in REPORTS:
                        raw = (repo / OLD / "runs" / run_name / name).read_bytes()
                        matches = raw == expected[name]
                        if not matches:
                            raise RuntimeError(f"Fresh replay differs from original report: {run_name}/{name}")
                        payloads[f"cases/{label}/{run_name}/{name}"] = raw
                        report_records[f"{run_name}/{name}"] = {"bytes": len(raw), "sha256": sha(raw), "exact_original_bytes": True}
                cases.append({"label": label, "result": "complete-report-match", "reports": report_records})
            change_summary, changed = collect_case(repo, label, expected_packet, modes)
            cases[-1]["packet_changes"] = change_summary
            cases[-1]["raw_changed_files"] = {path: sha(raw) for path, raw in changed.items()}
            for path, raw in changed.items():
                payloads[path] = raw
            attempt_summary, attempt_files = collect_attempt_artifacts(repo, label)
            cases[-1]["producer_artifacts"] = attempt_summary
            payloads.update(attempt_files)
        if cases[0]["reports"] != cases[1]["reports"]:
            raise RuntimeError("Independent fresh output vintages do not match")
        scope_cli_capture = scratch_root / "scope-cli"
        scope_cli_results = run_scope_cli(scratch_root / "fresh-1" / "repo", scope_cli_capture)
        scope_cli_results.extend(run_scope_cli(scratch_root / "fresh-2" / "repo", scope_cli_capture, include_negatives=False, positive_name="valid-run-2"))
        for result in scope_cli_results:
            for suffix in ("stdout", "stderr"):
                payloads[result[f"{suffix}_path"]] = (scope_cli_capture / f"{result['case']}.{suffix}").read_bytes()
        summary = {
            "issue": 1463, "worker_id": "01a10947-7d6e-7ba2-98a1-a9f91dedabfc",
            "source_commit": SOURCE, "affected_merge": MERGE, "baseline_commit": BASE,
            "inventory_file_count": len(pins), "inventory_raw_bytes": sum(x["bytes"] for x in pins),
            "actual_attempt_count": sum(len(a["verifier_attempts"]) for a in all_attempts) + len(scope_cli_results),
            "full_cli_executions": 3, "complete_report_sets": 6,
            "runner_code": {"path": str(Path(__file__).resolve().relative_to(REPO)), "bytes": len(Path(__file__).read_bytes()), "sha256": sha(Path(__file__).read_bytes())},
            "orchestrator_python": sys.version.split()[0],
            "legacy_python_runtime": json.loads(subprocess.check_output([PYTHON, "-c", "import json,sys,numpy,shapely,pyproj; print(json.dumps({'python':sys.version.split()[0],'numpy':numpy.__version__,'shapely':shapely.__version__,'pyproj':pyproj.__version__}))"], cwd=REPO)),
            "original_marker_overwrite_reproduced_in_private_copy": True,
            "historical_files_modified": False,
            "geographic_approval": "unapproved; replay is mechanical only",
            "unresolved": ["territorial meaning", "source completeness", "shoreline vintage", "physical island semantics", "parent completeness", "source policy"],
        }
        # NewVintage accepts only a fixed flat filename inventory. Store the
        # nested actual raw streams in one bounded deterministic JSON envelope;
        # Base64 preserves exact stdout/stderr and overwritten packet bytes.
        from base64 import b64encode
        attempt_bundle = {"version": 1, "attempts": all_attempts, "scope_validator_cli": scope_cli_results, "raw_streams": {name: b64encode(raw).decode("ascii") for name, raw in payloads.items() if name.startswith("attempts/")}}
        changes_bundle = {"version": 1, "cases": cases, "original_input_count": len(expected_packet), "destination_controls": safe_destination_checks, "raw_changed_files": {name: b64encode(raw).decode("ascii") for name, raw in payloads.items() if name.startswith("cases/")}}
        from evidence.immutable import canonical_json
        values = {
            "attempts.json": canonical_json(attempt_bundle),
            "case-changes.json": canonical_json(changes_bundle),
            "replay-summary.json": canonical_json(summary),
            "scope.json": canonical_json({"subject_ids": json.loads(contents[f"{OLD}/inputs/expected-subjects.json"]), "count": 23, "vintage": VINTAGE}),
        }
        records = vintage.publish_bytes(values)
        published = True
        print(json.dumps({"status": "complete", "vintage": VINTAGE, "outputs": records, "attempts": summary["actual_attempt_count"]}, sort_keys=True))
    finally:
        # If output publication itself failed, retain the raw scratch evidence
        # for recovery. Remove the large private mirror only after durable
        # publication (including the explicit failed-attempt bundle above).
        if published:
            shutil.rmtree(scratch_root)
        else:
            print(f"Unpublished replay evidence retained at {scratch_root}", file=sys.stderr)


if __name__ == "__main__":
    main()
