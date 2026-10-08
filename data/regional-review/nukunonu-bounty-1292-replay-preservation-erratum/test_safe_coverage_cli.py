#!/usr/bin/env python3
"""Adverse controls for the documented safe replay command and shared writer."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[3]
OWNED = ROOT / "data/regional-review/nukunonu-bounty-1292-replay-preservation-erratum"
RUNNER = OWNED / "reproduce_safe_coverage.py"
PYTHON = sys.executable


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def cli(*args):
    return subprocess.run(
        [PYTHON, "-B", str(RUNNER), *args],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
    )


def test_real_cli_rejections():
    vintages = OWNED / "vintages"
    suffix = uuid.uuid4().hex[:12]
    collision = "fixture-collision-" + suffix
    target = vintages / collision
    target.mkdir()
    sentinel = b"preexisting evidence sentinel\n"
    (target / "attempt.json").write_bytes(sentinel)
    try:
        result = cli("run", "--vintage", collision)
        require(result.returncode != 0, "actual CLI rejected existing output vintage")
        require((target / "attempt.json").read_bytes() == sentinel, "collision sentinel unchanged")
        require(not (target / "publication.json").exists(), "collision produced no success receipt")
    finally:
        import shutil
        shutil.rmtree(target)

    broken = "fixture-broken-" + suffix
    broken_path = vintages / broken
    broken_path.symlink_to(OWNED / ("absent-" + suffix))
    try:
        result = cli("run", "--vintage", broken)
        require(result.returncode != 0, "actual CLI rejected broken symlink output root")
        require(not (OWNED / ("absent-" + suffix)).exists(), "broken-link target was not created")
    finally:
        broken_path.unlink(missing_ok=True)

    output_link = "fixture-output-link-" + suffix
    output_root = vintages / output_link
    output_root.mkdir()
    external_sentinel = OWNED / ("external-sentinel-" + suffix)
    external_sentinel.write_bytes(sentinel)
    (output_root / "attempt.json").symlink_to(external_sentinel)
    try:
        result = cli("run", "--vintage", output_link)
        require(result.returncode != 0, "actual CLI rejected symlink output file")
        require(external_sentinel.read_bytes() == sentinel, "symlink target sentinel unchanged")
        require(not (output_root / "publication.json").exists(), "symlink rejection produced no receipt")
    finally:
        (output_root / "attempt.json").unlink(missing_ok=True)
        output_root.rmdir()
        external_sentinel.unlink()

    escape = "escape-" + suffix
    result = cli("run", "--vintage", "../" + escape)
    require(result.returncode != 0, "actual CLI rejected traversal vintage")
    require(not (OWNED / escape).exists(), "traversal destination was not created")
    print("PASS actual CLI: existing file, broken symlink, output symlink and traversal rejected; sentinels unchanged")


def fixture_baseline(repo, module):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE).decode().strip()
    git("init", "-q")
    git("config", "user.name", "WorldAtlas evidence fixture")
    git("config", "user.email", "fixture@example.invalid")
    pin = repo / "pin.json"
    pin.write_bytes(b'{"id":"independent-baseline"}\n')
    git("add", "pin.json")
    git("commit", "-qm", "Immutable safe-write baseline")
    commit = git("rev-parse", "HEAD")
    raw = pin.read_bytes()
    desc = {"path": "pin.json", "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(), "hash_kind": "file-bytes"}
    return module.Baseline(repo, commit, [desc])


def test_parent_symlink_and_partial_write():
    spec = importlib.util.spec_from_file_location(
        "worldatlas_safe_vintage_fixture", ROOT / "scripts/evidence/immutable.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix=".safe-writer-fixture-", dir=OWNED) as folder:
        repo = Path(folder)
        baseline = fixture_baseline(repo, module)
        owned = "data/regional-review/writer-fixture/"
        vintages = repo / owned / "vintages"
        vintages.parent.mkdir(parents=True)

        link_target = repo / "redirect-target"
        vintages.symlink_to(link_target, target_is_directory=True)
        try:
            try:
                module.NewVintage(baseline, owned, "parent-link", ["one.json"])
                raise AssertionError("shared writer accepted symlink parent")
            except ValueError as exc:
                require("Symlink" in str(exc), "shared writer reports unsafe parent")
            require(not link_target.exists(), "unsafe parent target remains absent")
        finally:
            vintages.unlink(missing_ok=True)

        vintages.mkdir()
        for unsafe in ("../escape", "/absolute", "bad\\name"):
            try:
                module.NewVintage(baseline, owned, unsafe, ["one.json"])
                raise AssertionError("shared writer accepted traversal name")
            except ValueError:
                pass
        require(list(vintages.iterdir()) == [], "unsafe names created no output")

        run = module.NewVintage(baseline, owned, "partial-write", ["one.json", "two.json"])
        original_open = Path.open

        def fail_second(path, *args, **kwargs):
            if path == run.root / "two.json":
                raise OSError("fixture failure after first product write")
            return original_open(path, *args, **kwargs)

        try:
            from unittest.mock import patch
            with patch.object(Path, "open", fail_second):
                run.publish_bytes({"one.json": b'{"one":1}\n', "two.json": b'{"two":2}\n'})
            raise AssertionError("simulated partial writer failure did not occur")
        except OSError as exc:
            require("fixture failure" in str(exc), "expected write failure observed")
        require((run.root / "one.json").read_bytes() == b'{"one":1}\n',
                "first partial product retained for diagnosis")
        require(not (run.root / "publication.json").exists(),
                "partial run cannot be accepted as complete")
    print("PASS shared writer: parent symlink, traversal and post-first-write failure remain incomplete")

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--post-calculation-publication-failure":
        vintage = sys.argv[2]
        spec = importlib.util.spec_from_file_location("worldatlas_replay_failure_fixture", RUNNER)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        original_factory = runner.helper_module

        def failing_publication_factory(root, helper_bytes):
            helper = original_factory(root, helper_bytes)
            original_publish = helper.NewVintage.publish_bytes

            def fail_success_after_calculation(self, values):
                if self.vintage == vintage:
                    raise OSError("fixture publication failure after full calculation")
                return original_publish(self, values)

            helper.NewVintage.publish_bytes = fail_success_after_calculation
            return helper

        runner.helper_module = failing_publication_factory
        code = runner.run_vintage(ROOT, vintage)
        failed = OWNED / "vintages" / ("failed-" + vintage)
        success = OWNED / "vintages" / vintage
        require(code == 1 and not success.exists(), "injected publication failure has no success directory")
        receipt = json.loads((failed / "publication.json").read_bytes())
        attempt = json.loads((failed / "attempt.json").read_bytes())
        require(receipt.get("status") == "complete", "failure itself has a complete receipt")
        require(attempt.get("status") == "failed", "failed calculation attempt is labeled failed")
        require(attempt.get("publication_failure", {}).get("message") ==
                "fixture publication failure after full calculation",
                "failure receipt binds the injected post-calculation error")
        require(set(attempt.get("outputs", {})) == {"nukunonu", "bounty-islands"},
                "failed publication preserves both fully computed reports")
        require(all(row.get("matches_retained_output") for row in attempt["outputs"].values()),
                "failure receipt records exact retained report matches")
        print("PASS actual producer: complete post-calculation failure receipt retained; no success publication")
        raise SystemExit(0)
    elif len(sys.argv) == 1:
        test_real_cli_rejections()
        test_parent_symlink_and_partial_write()
    else:
        raise SystemExit("Usage: test_safe_coverage_cli.py [--post-calculation-publication-failure FRESH-NAME]")
