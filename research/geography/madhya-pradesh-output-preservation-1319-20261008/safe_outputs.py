"""Fail-closed output admission for the bounded #1485 erratum."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import types

ISSUE = 1485
WORKER_ID = "01a10947-b3d7-7812-8b2f-c5a47e88ccb2"
ISSUE_SNAPSHOT = "research/geography/madhya-pradesh-output-preservation-1319-20261008/issue-1485-current.json"
OWNED_PATH = "research/geography/madhya-pradesh-output-preservation-1319-20261008/"
EVIDENCE_PATH = "data/regional-review/regional-review-0968ad79c26518d2/"
EVALUATION_COMMIT = "cbb829672d18801e4310c30896a7ddb13a79b451"
ORIGINAL_MERGE = "913db0624b8aa79b188ff17a7f5c4ae0c0f63965"
IMMUTABLE_PATH = "scripts/evidence/immutable.py"
IMMUTABLE_SHA256 = "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46"
SOURCE_PINS = {
    "data/global-sources/IND-ADM3.geojson.gz": "211a72c2c80bb60d10214944fa8cc4764e9ba888116e802ce6d87084872f5301",
    "data/global-sources/IND-ADM3-metadata.json": "f7bb99ddfcadaa1091c4b634b48c8843ee9d8b636af4f6da1cefccb0d424fc33",
    EVIDENCE_PATH + "sources/source-inventory.json": "65e5a086e59c2db619bb3eac3a6248fc439225e2448c222bba6516ae0927904b",
}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


def current_commit(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD").decode().strip()


def load_contract(repo: Path) -> tuple[dict, dict]:
    issue = json.loads((repo / ISSUE_SNAPSHOT).read_bytes())
    match = re.search(r"<!-- worldatlas-work:v1\s*(\{[\s\S]*?\})\s*-->", issue["body"])
    if issue.get("number") != ISSUE or not match:
        raise ValueError("Pinned live issue snapshot lacks its exact work contract")
    contract = json.loads(match.group(1))
    if contract.get("owned_paths") != [OWNED_PATH] or contract.get("mode") != "geography":
        raise ValueError("Issue-owned path or lane differs from the confirmed reservation")
    if contract.get("evidence_quality", {}).get("manifest_path") != OWNED_PATH + "evidence-quality.json":
        raise ValueError("Issue evidence manifest path changed")
    return issue, contract


def load_immutable_api(repo: Path):
    commit = current_commit(repo)
    source = git(repo, "show", f"{commit}:{IMMUTABLE_PATH}")
    if sha256(source) != IMMUTABLE_SHA256:
        raise ValueError("Shared immutable helper differs from its admitted whole-file pin")
    module = types.ModuleType("worldatlas_pinned_immutable")
    module.__file__ = f"{commit}:{IMMUTABLE_PATH}"
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module, commit, source


def _descriptor(path: str, commit: str, raw: bytes) -> dict:
    return {"path": path, "commit": commit, "bytes": len(raw), "sha256": sha256(raw), "hash_kind": "file-bytes"}


def admitted_baseline(repo: Path):
    """Authenticate the issue pins, native containing parts and executed helper."""
    issue, contract = load_contract(repo)
    module, commit, helper_bytes = load_immutable_api(repo)
    pins = dict(contract["evidence_quality"]["pins"])
    pins[IMMUTABLE_PATH] = IMMUTABLE_SHA256
    pins.update(SOURCE_PINS)
    paths = list(pins)
    paths.extend([
        "data/geography/part-30.json", "data/geography/part-31.json",
        "data/geography/part-32.json", "data/geography/part-33.json",
    ])
    files = []
    unique = set()
    for path in paths:
        if path in unique:
            continue
        unique.add(path)
        raw = helper_bytes if path == IMMUTABLE_PATH else git(repo, "show", f"{commit}:{path}")
        expected = pins.get(path)
        if expected is not None and sha256(raw) != expected:
            raise ValueError(f"Whole-file source pin differs at {commit}:{path}")
        files.append({"path": path, "bytes": len(raw), "sha256": sha256(raw), "hash_kind": "file-bytes"})
    baseline = module.Baseline(repo, commit, files)
    return issue, contract, baseline, module, commit, files, pins


def safe_output_root(repo: Path, vintage: str, filenames: list[str]) -> Path:
    """Check the full owned path/output set without creating anything."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", vintage):
        raise ValueError("Run ID must be a fresh safe identifier")
    if not filenames or len(filenames) != len(set(filenames)):
        raise ValueError("Output inventory must be complete and unique")
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", n) for n in filenames):
        raise ValueError("Output names must be simple files inside the admitted vintage")
    repo = repo.resolve()
    root = repo / OWNED_PATH / "vintages" / vintage
    try:
        root.relative_to(repo / OWNED_PATH)
    except ValueError as exc:
        raise ValueError("Output escaped the declared owned path") from exc

    # Inspect every ancestor with lstat so dangling symlinks and ordinary files
    # cannot masquerade as absent paths. Existing parents must be real dirs.
    ancestors = list(reversed(root.parents)) + [root]
    for candidate in ancestors:
        if not candidate.is_relative_to(repo):
            continue
        try:
            mode = candidate.lstat().st_mode
        except FileNotFoundError:
            continue
        if candidate.is_symlink():
            raise ValueError(f"Symlink output ancestor refused: {candidate.relative_to(repo)}")
        if candidate != root and not candidate.is_dir():
            raise FileExistsError(f"Non-directory output ancestor refused: {candidate.relative_to(repo)}")
        if candidate == root:
            raise FileExistsError(f"Fresh output vintage already exists: {candidate.relative_to(repo)}")

    for name in filenames:
        target = root / name
        if os.path.lexists(target):
            raise FileExistsError(f"Output path already exists: {target.relative_to(repo)}")
    return root


def exercise_preflight_controls(repo: Path, tag: str) -> dict:
    """Exercise actual admission logic against private, disposable owned sentinels."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,35}", tag):
        raise ValueError("Unsafe control tag")
    vintages = repo / OWNED_PATH / "vintages"
    fixtures = repo / OWNED_PATH / "negative-fixtures" / tag
    fixtures.mkdir(parents=True, exist_ok=False)
    outcomes = {}
    names = ["assessments.json.gz"]

    def rejected(name, run_id, expected):
        try:
            safe_output_root(repo, run_id, names)
        except expected:
            outcomes[name] = "passed"
            return
        raise AssertionError(f"Unsafe output inventory was accepted: {name}")

    try:
        vintages.mkdir(parents=True, exist_ok=True)

        file_id = tag + "-file"
        file_target = vintages / file_id
        file_target.write_bytes(b"preexisting-file-sentinel\n")
        before = file_target.read_bytes()
        rejected("ordinary-file", file_id, FileExistsError)
        if file_target.read_bytes() != before:
            raise AssertionError("Ordinary file sentinel changed")
        file_target.unlink()

        dir_id = tag + "-directory"
        dir_target = vintages / dir_id
        dir_target.mkdir()
        sentinel = dir_target / "sentinel.bin"
        sentinel.write_bytes(b"preexisting-directory-sentinel\n")
        before = sentinel.read_bytes()
        rejected("ordinary-directory", dir_id, FileExistsError)
        if sentinel.read_bytes() != before:
            raise AssertionError("Directory sentinel changed")
        shutil.rmtree(dir_target)

        live_id = tag + "-live-link"
        live_target = fixtures / "live-target"
        live_target.mkdir()
        live_sentinel = live_target / "sentinel.bin"
        live_sentinel.write_bytes(b"live-target-sentinel\n")
        before = live_sentinel.read_bytes()
        live_link = vintages / live_id
        live_link.symlink_to(live_target, target_is_directory=True)
        rejected("live-symlink", live_id, ValueError)
        if live_sentinel.read_bytes() != before:
            raise AssertionError("Live symlink target sentinel changed")
        live_link.unlink()

        dangling_id = tag + "-dangling-link"
        dangling_target = fixtures / "absent-target"
        dangling_link = vintages / dangling_id
        dangling_link.symlink_to(dangling_target)
        rejected("dangling-symlink", dangling_id, ValueError)
        if os.path.lexists(dangling_target):
            raise AssertionError("Dangling target was unexpectedly created")
        dangling_link.unlink()

        traversal = tag + "/../../escaped"
        try:
            safe_output_root(repo, traversal, names)
        except ValueError:
            outcomes["traversal"] = "passed"
        else:
            raise AssertionError("Traversal destination was accepted")

        # Exercise a symlinked ancestor with a tiny synthetic repository-shaped
        # tree that remains entirely beneath this issue's owned directory.
        fake_repo = fixtures / "fake-repo"
        fake_owned = fake_repo / OWNED_PATH
        fake_vintages = fake_owned / "vintages"
        fake_owned.mkdir(parents=True)
        fake_vintages.symlink_to(live_target, target_is_directory=True)
        try:
            safe_output_root(fake_repo, tag + "-ancestor-link", names)
        except ValueError:
            outcomes["symlinked-ancestor"] = "passed"
        else:
            raise AssertionError("Symlinked ancestor was accepted")
        fake_vintages.unlink()
    finally:
        # This directory is created by this exact invocation and contains only
        # its own disposable controls. Sentinels have already been verified.
        shutil.rmtree(fixtures)
    return {"version": 1, "method_id": "safe-output-admission", "outcome": "passed",
            "cases": outcomes, "cases_passed": len(outcomes),
            "targets_preserved": ["ordinary-file", "ordinary-directory", "live-symlink"],
            "scope": "Private output-path controls only; no source or geography claim"}


def new_vintage_with_api(repo: Path, baseline, module, vintage: str, filenames: list[str]):
    safe_output_root(repo, vintage, filenames)
    return module.NewVintage(baseline, OWNED_PATH, vintage, filenames)


def verify_historical_manifest(repo: Path, baseline) -> dict:
    """Authenticate the old producer's declared complete inputs without replaying science."""
    manifest_path = EVIDENCE_PATH + "vintages/generator-integrity-erratum/evaluation-inputs.json"
    spec = json.loads(baseline.pinned_bytes(manifest_path))
    if spec.get("evaluation_commit") != EVALUATION_COMMIT:
        raise ValueError("Original evaluation vintage changed")
    checked = []
    for descriptor in spec.get("inputs", []):
        path = descriptor["path"]
        if (not isinstance(path, str) or not path or chr(92) in path or "\0" in path or
                any(part in {"", ".", ".."} for part in path.split("/"))):
            raise ValueError("Unsafe historical input path")
        # Resolve an ordinary historical Git blob and account its declared
        # whole-file size before materializing the bytes. These files belong to
        # the same complete execution phase as the current retained report.
        row = git(repo, "ls-tree", "-z", EVALUATION_COMMIT, "--", path)
        entries = [item for item in row.decode().split("\0") if item]
        if len(entries) != 1:
            raise ValueError(f"Historical input is absent or ambiguous: {path}")
        metadata, resolved_path = entries[0].split("\t", 1)
        mode, kind, blob = metadata.split()
        if resolved_path != path or mode not in {"100644", "100755"} or kind != "blob":
            raise ValueError(f"Historical input is not a committed ordinary file: {path}")
        size = int(git(repo, "cat-file", "-s", blob))
        baseline.admit(f"historical:{EVALUATION_COMMIT}:{path}", size)
        raw = git(repo, "cat-file", "blob", blob)
        if len(raw) != descriptor["bytes"] or sha256(raw) != descriptor["sha256"]:
            raise ValueError(f"Historical evaluation input mismatch: {descriptor['path']}")
        checked.append({"path": descriptor["path"], "commit": EVALUATION_COMMIT,
                        "bytes": len(raw), "sha256": sha256(raw), "hash_kind": "file-bytes"})
    phase_bytes = sum(size for name, size in baseline.consumed.items() if name.startswith("historical:" + EVALUATION_COMMIT + ":"))
    return {"commit": EVALUATION_COMMIT, "input_files": checked, "count": len(checked),
            "complete_phase_historical_bytes": phase_bytes,
            "complete_phase_input_bytes": sum(baseline.consumed.values())}


def exact_report_inputs(baseline):
    base = EVIDENCE_PATH
    vintage = base + "vintages/generator-integrity-erratum/"
    original = baseline.pinned_bytes(base + "assessments.json")
    run_one = baseline.pinned_bytes(vintage + "runs/2026-10-07/run-1/assessments.json.gz")
    run_two = baseline.pinned_bytes(vintage + "runs/2026-10-07/run-2/assessments.json.gz")
    if run_one != run_two:
        raise ValueError("The retained full producer vintages are not byte-identical")
    return original, run_one, run_two
