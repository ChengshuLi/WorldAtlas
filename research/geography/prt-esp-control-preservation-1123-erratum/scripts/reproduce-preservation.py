#!/usr/bin/env python3
"""Reproduce the retained control writer safely into one exclusive vintage.

The legacy entry point is executed unchanged in a disposable, credential-free
snapshot of its exact pinned code and reports. Its output is buffered there and
is published to this issue-owned namespace only after a complete successful run.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[4]
OWNED_PATH = "research/geography/prt-esp-control-preservation-1123-erratum/"
SOURCE_PACKET = "research/geography/shared-seam-prt-esp-20261006/"
BASELINE = "777b082b0a3447c39205255312ec69f453e85e7a"
PYTHON = Path(sys.executable).resolve()
PINNED = {
    "scripts/validate-measurement-controls.py": "9d617d3589109ee85db087fff3fc25ee6f36df8dace2b51949c5d06d20e9ad4f",
    "scripts/reproduce-comparison.py": "62fad3ced494623fa7b3b6c790d94e1b3d5103c6b8361c866725bd02e92ad215",
    "validation/positive-control.json": "0785be71c7af64b626e8098b6a49be96b3171107d34f54f9600b7893e80f284d",
    "validation/negative-control.json": "3df7bebbe0099e5af0b8a7a665143a5dce3983a78ebdc99d31dee6e57d846885",
    "validation/reproducibility.json": "9fcbd1ceb03ca82b73e66414dc40fbe11333204155aeb750820fb8f75d496499",
    "outputs/run-09/report.json": "4f52d5ef455ae24e4ec7d0067567e6498e7407a0244a08622c3e2793ed0ad5a0",
    "outputs/run-10/report.json": "4f52d5ef455ae24e4ec7d0067567e6498e7407a0244a08622c3e2793ed0ad5a0",
    "evidence-quality.json": "9fda6a96e159d46d14fa6fcb09433facb512ef5154daff1e8fffa8430cf47370",
}
PARTS = {
    "data/geography/part-19.json": None,
    "data/geography/part-28.json": None,
}
SUBJECTS = [
    "atlas:district:ESP-1003:a5622946",
    "atlas:district:ESP-1004:a5622946",
    "atlas:district:ESP-1010:a5622946",
    "gb:PRT:ADM2:2272694B24025236019409",
    "gb:PRT:ADM2:2272694B40601521893357",
    "gb:PRT:ADM2:2272694B64876814145037",
    "gb:PRT:ADM2:2272694B74999887486897",
]
OUTPUT_NAMES = [
    "run-01-positive-control.json",
    "run-01-negative-control.json",
    "run-01-reproducibility.json",
    "run-02-positive-control.json",
    "run-02-negative-control.json",
    "run-02-reproducibility.json",
    "two-run-comparison.json",
    "failure-mismatch.json",
    "admission-controls.json",
]
METHOD_ID = "utm29-direct-geos-overlay-measurement"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "cat-file", "blob", f"{commit}:{path}"])


def capture_inputs() -> tuple[dict[str, bytes], dict[str, dict], bytes]:
    files = {}
    descriptors = {}
    for relative, expected in PINNED.items():
        path = SOURCE_PACKET + relative
        raw = git_blob(BASELINE, path)
        if sha(raw) != expected:
            raise RuntimeError(f"Issue pin mismatch at {BASELINE}:{path}")
        files[path] = raw
        descriptors[path] = {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}
    for path in PARTS:
        raw = git_blob(BASELINE, path)
        files[path] = raw
        descriptors[path] = {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}
    helper_path = "scripts/evidence/immutable.py"
    helper_raw = git_blob(BASELINE, helper_path)
    files[helper_path] = helper_raw
    descriptors[helper_path] = {"path": helper_path, "bytes": len(helper_raw), "sha256": sha(helper_raw), "hash_kind": "file-bytes"}
    return files, descriptors, helper_raw


def sandbox(files: dict[str, bytes], *, mismatch: bool = False) -> tuple[tempfile.TemporaryDirectory, Path, Path]:
    """Create an exact minimal input snapshot with deterministic local Git HEAD."""
    temporary = tempfile.TemporaryDirectory(prefix="prt-esp-preservation-")
    root = Path(temporary.name) / "repo"
    for path, raw in files.items():
        # Retained control receipts are pinned read-only in the author checkout;
        # the validator does not consume them. Do not seed its sandbox with them:
        # each execution must begin with a truly fresh output namespace.
        if (path.startswith(SOURCE_PACKET + "validation/") or path == SOURCE_PACKET + "evidence-quality.json"
                or path == "scripts/evidence/immutable.py"):
            continue
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if mismatch and path == SOURCE_PACKET + "outputs/run-10/report.json":
            raw += b" "  # Valid JSON, deliberately different whole-file bytes.
        target.write_bytes(raw)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "--all"], check=True)
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "GIT_AUTHOR_NAME": "WorldAtlas bounded reproduction",
        "GIT_AUTHOR_EMAIL": "noreply@example.invalid",
        "GIT_COMMITTER_NAME": "WorldAtlas bounded reproduction",
        "GIT_COMMITTER_EMAIL": "noreply@example.invalid",
        "GIT_AUTHOR_DATE": "2020-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2020-01-01T00:00:00Z",
    }
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "captured immutable inputs"], env=env, check=True)
    script = root / SOURCE_PACKET / "scripts/validate-measurement-controls.py"
    return temporary, root, script


def execute(files: dict[str, bytes], *, mismatch: bool = False) -> dict[str, bytes | str]:
    temporary, root, script = sandbox(files, mismatch=mismatch)
    package_dirs = [Path(entry) for entry in sys.path if entry and
                    (Path(entry) / "pyproj/__init__.py").is_file() and
                    (Path(entry) / "shapely/__init__.py").is_file()]
    if not package_dirs:
        raise RuntimeError("Could not identify the installed pinned scientific runtime packages")
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": os.pathsep.join(str(path) for path in package_dirs),
    }
    completed = subprocess.run([str(PYTHON), "-B", str(script)], cwd=root, env=env,
                               capture_output=True, text=True)
    output = root / SOURCE_PACKET / "validation"
    observed = {name: (output / name).read_bytes() for name in ("positive-control.json", "negative-control.json") if (output / name).is_file()}
    if (output / "reproducibility.json").is_file():
        observed["reproducibility.json"] = (output / "reproducibility.json").read_bytes()
    if mismatch:
        if completed.returncode == 0 or "Final complete reports differ" not in completed.stderr:
            raise AssertionError("Mismatched retained reports did not fail through the actual validator path")
        if set(observed) != {"positive-control.json", "negative-control.json"}:
            raise AssertionError("Mismatch path unexpectedly published a completion receipt")
        observation = {
            "version": 1,
            "kind": "mismatched-report-adverse-control",
            "outcome": "rejected-without-completion-receipt",
            "entry_point_sha256": sha(files[SOURCE_PACKET + "scripts/validate-measurement-controls.py"]),
            "run_one_report_sha256": sha(files[SOURCE_PACKET + "outputs/run-09/report.json"]),
            "run_two_report_sha256": sha(files[SOURCE_PACKET + "outputs/run-10/report.json"] + b" "),
            "legacy_private_attempt_products": sorted(observed),
            "completion_receipt_present": False,
            "originals_touched": False,
        }
        result = {"failure-mismatch.json": json_bytes(observation)}
        temporary.cleanup()
        return result
    if completed.returncode != 0:
        raise RuntimeError(f"Actual validator failed: {completed.stderr[-2000:]}")
    if set(observed) != {"positive-control.json", "negative-control.json", "reproducibility.json"}:
        raise AssertionError("Actual validator did not produce the complete three-file set")
    temporary.cleanup()
    return observed


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_helper(helper_raw: bytes, module_name: str):
    module = types.ModuleType(module_name)
    module.__file__ = str(ROOT / "scripts/evidence/immutable.py")
    exec(compile(helper_raw, module.__file__, "exec"), module.__dict__)
    return module


def prepare_vintage(descriptors: dict[str, dict], helper_raw: bytes, vintage: str):
    """Pin inputs and admit every final path before running any experiment."""
    helper = load_helper(helper_raw, "worldatlas_immutable_preflight")
    baseline = helper.Baseline(ROOT, BASELINE, list(descriptors.values()))
    return helper.NewVintage(baseline, OWNED_PATH, vintage, OUTPUT_NAMES)


def whole_runner_collision_probe(vintage: str) -> dict:
    """Call the normal runner with an occupied final path and trap any execution."""
    from uuid import uuid4

    probe_vintage = f"admission-probe-{uuid4().hex[:12]}"
    candidate_root = ROOT / OWNED_PATH / "vintages" / probe_vintage
    target = candidate_root / OUTPUT_NAMES[0]
    marker_parent = tempfile.TemporaryDirectory(prefix="worldatlas-preflight-marker-")
    marker = Path(marker_parent.name) / "computation-was-reached"
    candidate_root.mkdir(parents=True, exist_ok=False)
    target.write_bytes(b"pre-existing-sentinel")
    before = target.read_bytes()
    namespace = runpy.run_path(str(Path(__file__).resolve()))

    def forbidden_execution(*_args, **_kwargs):
        marker.write_text("runner reached calculation")
        raise AssertionError("Existing target was not rejected before computation")

    namespace["execute"] = forbidden_execution
    original_argv = sys.argv
    rejected = False
    try:
        sys.argv = [str(Path(__file__).resolve()), probe_vintage]
        try:
            namespace["main"](preflight_probe=False)
        except FileExistsError:
            rejected = True
        if not rejected:
            raise AssertionError("Normal runner accepted an existing final output")
        if marker.exists() or target.read_bytes() != before:
            raise AssertionError("Existing-target admission ran computation or changed its sentinel")
    finally:
        sys.argv = original_argv
        if candidate_root.exists() and candidate_root.is_dir() and not candidate_root.is_symlink():
            shutil.rmtree(candidate_root)
        marker_parent.cleanup()
    return {"case": "normal-runner-existing-final-output", "rejected_before_computation": True,
            "sentinel_preserved": True, "computation_marker_created": False}


def fixture_record(helper_raw: bytes) -> dict:
    """Exercise shared fresh-run admission in a separate temporary Git repo."""
    module = load_helper(helper_raw, "worldatlas_immutable_admission")
    cases = []
    with tempfile.TemporaryDirectory(prefix="worldatlas-admission-") as temp:
        repo = Path(temp) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / "baseline.txt").write_text("pinned\n")
        subprocess.run(["git", "-C", str(repo), "add", "baseline.txt"], check=True)
        env = {"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
               "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
               "GIT_AUTHOR_DATE": "2020-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2020-01-01T00:00:00Z"}
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "pin"], env=env, check=True)
        commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        descriptor = {"path": "baseline.txt", "bytes": 7, "sha256": sha(b"pinned\n"), "hash_kind": "file-bytes"}
        baseline = module.Baseline(repo, commit, [descriptor])
        owned = "research/geography/admission-fixture/"
        parent = repo / owned / "vintages"
        cases_to_make = [
            ("existing-file", "existing-file", "positive-control.json", "file"),
            ("existing-directory", "existing-directory", "positive-control.json", "directory"),
            ("dangling-symlink", "dangling-symlink", "positive-control.json", "dangling"),
            ("symlinked-parent-escape", "parent-escape", "positive-control.json", "parent"),
        ]
        for kind, vintage, filename, state in cases_to_make:
            root = parent / vintage
            target = root / filename
            protected = None
            if state == "parent":
                parent.mkdir(parents=True, exist_ok=True)
                outside = Path(temp) / "outside"
                outside.mkdir()
                protected = outside / "sentinel"
                protected.write_bytes(b"sentinel")
                if parent.exists() and parent.is_dir():
                    parent.rmdir()
                parent.symlink_to(outside, target_is_directory=True)
            else:
                root.mkdir(parents=True, exist_ok=True)
                if state == "file":
                    target.write_bytes(b"sentinel")
                    protected = target
                elif state == "directory":
                    target.mkdir()
                    protected = target / "sentinel"
                    protected.write_bytes(b"sentinel")
                else:
                    target.symlink_to(Path(temp) / "missing-target")
            before = None
            if protected is not None:
                before = protected.read_bytes()
            if state == "dangling":
                before = os.readlink(target)
            try:
                module.NewVintage(baseline, owned, vintage, [filename])
                rejected = False
            except (FileExistsError, ValueError):
                rejected = True
            if not rejected:
                raise AssertionError(f"Fresh-output admission accepted {kind}")
            if state in {"file", "directory"} and protected.read_bytes() != before:
                raise AssertionError("Existing sentinel contents changed")
            if state == "dangling" and os.readlink(target) != before:
                raise AssertionError("Dangling symlink changed")
            if state == "parent" and protected.read_bytes() != before:
                raise AssertionError("Symlink-parent escape sentinel changed")
            cases.append({"case": kind, "rejected_before_write": True, "sentinel_preserved": True})
            # Remove this fixture's root; the next fixture gets a distinct path.
            if state != "parent":
                if root.exists():
                    import shutil
                    shutil.rmtree(root)
        import pyproj
        import shapely
        return {"version": 1, "kind": "fresh-output-admission-controls", "outcome": "passed", "cases": cases,
                "runtime": {"python": sys.version.split()[0], "shapely": shapely.__version__,
                            "geos": shapely.geos_version_string, "pyproj": pyproj.__version__},
                "scope": "Disposable repository fixtures plus a unique cleaned sentinel under this issue-owned path; no production or original evidence paths used."}


def main(*, preflight_probe: bool = True) -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: reproduce-preservation.py FRESH_VINTAGE_NAME")
    vintage = sys.argv[1]
    files, descriptors, helper_bytes = capture_inputs()
    # This complete-set admission precedes the first actual control run or fixture.
    vintage_writer = prepare_vintage(descriptors, helper_bytes, vintage)
    whole_run_admission = whole_runner_collision_probe(vintage) if preflight_probe else None
    positive_one = execute(files)
    positive_two = execute(files)
    for name in positive_one:
        if positive_one[name] != positive_two[name]:
            raise AssertionError(f"Fresh actual validator runs differ at {name}")
    positive = json.loads(positive_one["positive-control.json"])
    negative = json.loads(positive_one["negative-control.json"])
    reproducibility = json.loads(positive_one["reproducibility.json"])
    for row, expected in (
        (positive, {"covered_area_m2": 5000.0, "uncovered_residual_area_m2": 5000.0,
                    "covered_fraction": 0.5, "shared_boundary_contact_length_m": 150.0}),
        (negative, {"covered_area_m2": 0.0, "uncovered_residual_area_m2": 10000.0,
                    "covered_fraction": 0.0, "shared_boundary_contact_length_m": 0.0}),
    ):
        if row.get("outcome") != "passed" or any(abs(row["actual"][key] - value) > 1e-5 for key, value in expected.items()):
            raise AssertionError("Actual entry point failed a declared positive/negative control")
    if reproducibility.get("outcome") != "passed" or reproducibility.get("run_one_sha256") != reproducibility.get("run_two_sha256"):
        raise AssertionError("Actual entry point did not verify complete retained report equality")
    controls = {}
    for prefix, result in (("run-01", positive_one), ("run-02", positive_two)):
        for name, raw in result.items():
            controls[f"{prefix}-{name}"] = raw
    run_hashes = []
    for result in (positive_one, positive_two):
        digest = hashlib.sha256()
        for name, raw in sorted(result.items()):
            digest.update(name.encode("utf-8") + b"\0" + len(raw).to_bytes(8, "big") + raw)
        run_hashes.append(digest.hexdigest())
    controls["two-run-comparison.json"] = json_bytes({
        "version": 1,
        "method_id": METHOD_ID,
        "kind": "reproducibility",
        "outcome": "passed",
        "run_one_sha256": run_hashes[0],
        "run_two_sha256": run_hashes[1],
        "compared_products": sorted(positive_one),
        "run_one_products_sha256": {name: sha(raw) for name, raw in sorted(positive_one.items())},
        "run_two_products_sha256": {name: sha(raw) for name, raw in sorted(positive_two.items())},
    })
    failure = execute(files, mismatch=True)
    controls.update(failure)
    admission = fixture_record(helper_bytes)
    if whole_run_admission is not None:
        admission["cases"].insert(0, whole_run_admission)
    controls["admission-controls.json"] = json_bytes(admission)

    # Recheck every historical issue pin after execution. The sandboxed CLI has
    # no path to the originals, and these checks bind that preservation claim.
    for relative, expected in PINNED.items():
        actual = sha(git_blob(BASELINE, SOURCE_PACKET + relative))
        if actual != expected:
            raise AssertionError(f"Historical pinned input changed: {relative}")
    new_hash = {name: sha(raw) for name, raw in controls.items()}
    records = vintage_writer.publish_bytes(controls)
    print(json.dumps({"vintage": vintage, "output_count": len(records), "outputs": new_hash,
                      "runner_sha256": sha(Path(__file__).read_bytes()),
                      "helper_sha256": sha(helper_bytes), "original_issue_pins_preserved": True}, sort_keys=True))


if __name__ == "__main__":
    main()
