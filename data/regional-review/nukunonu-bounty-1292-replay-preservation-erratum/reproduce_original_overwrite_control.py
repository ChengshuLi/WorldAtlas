#!/usr/bin/env python3
"""Reproduce #1469's legacy overwrite in a private byte-identical packet mirror."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

OWNED = Path(__file__).resolve().parent
ROOT = OWNED.parents[2]
FIXTURE = OWNED / "original-overwrite-control"
PRIVATE = FIXTURE / "private-repo"
SOURCE_COMMIT = "c3ac95a5d72258d46c85e94590c8168edf32a3e3"
PYTHON = sys.executable
PACKETS = [
    "data/regional-review/regional-supplement-e5d72b7004238f80/nukunonu",
    "data/regional-review/regional-supplement-b5299df90ec984cc/bounty-islands",
]
OUTPUTS = {
    "nukunonu": PACKETS[0] + "/current-coverage.json",
    "bounty-islands": PACKETS[1] + "/current-coverage.json",
}
MARKER = b"owned-existing-1292-coverage-marker\n"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args, cwd=ROOT):
    return subprocess.check_output(["git", "-C", str(cwd), *args], stderr=subprocess.PIPE)


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def write_exclusive(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    require(not FIXTURE.exists() and not FIXTURE.is_symlink(),
            "refuse existing private overwrite fixture; choose a new preserved fixture name")
    pins = json.loads((OWNED / "source-pins.json").read_text())
    pin_by_key = {row["commit"] + ":" + row["path"]: row["sha256"] for row in pins["pins"]}
    FIXTURE.mkdir()
    PRIVATE.mkdir()
    listing = git("ls-tree", "-r", "-z", SOURCE_COMMIT, "--", *PACKETS).decode()
    copied = []
    for record in listing.split("\0"):
        if not record:
            continue
        mode_kind_path = record.split("\t", 1)
        mode, kind, _blob = mode_kind_path[0].split()
        path = mode_kind_path[1]
        require(kind == "blob" and mode in ("100644", "100755"),
                "packet mirror contains a non-ordinary source file: " + path)
        raw = git("show", SOURCE_COMMIT + ":" + path)
        key = SOURCE_COMMIT + ":" + path
        if key in pin_by_key:
            require(sha(raw) == pin_by_key[key], "packet copy differs from issue pin: " + path)
        write_exclusive(PRIVATE / path, raw)
        copied.append({"path": path, "bytes": len(raw), "sha256": sha(raw), "commit": SOURCE_COMMIT})

    helper_path = "scripts/ellipsoidal_area.py"
    helper = git("show", SOURCE_COMMIT + ":" + helper_path)
    require(sha(helper) == pin_by_key[SOURCE_COMMIT + ":" + helper_path],
            "actual area helper differs from issue pin")
    write_exclusive(PRIVATE / helper_path, helper)

    git_dir = git("rev-parse", "--absolute-git-dir").decode().strip()
    write_exclusive(PRIVATE / ".git", ("gitdir: " + git_dir + "\n").encode())
    require(git("rev-parse", "--show-toplevel", cwd=PRIVATE).decode().strip() == str(PRIVATE),
            "private mirror did not resolve through the read-only Git directory locator")

    original_before = {}
    for name, relative in OUTPUTS.items():
        original = (ROOT / relative).read_bytes()
        expected = git("show", SOURCE_COMMIT + ":" + relative)
        require(original == expected, "working original differs from pinned #1292 output: " + relative)
        original_before[name] = {"path": relative, "bytes": len(original), "sha256": sha(original)}
        marker_copy = FIXTURE / "before-markers" / (name + ".current-coverage.json")
        write_exclusive(marker_copy, MARKER)
        target = PRIVATE / relative
        require(not target.is_symlink() and target.is_file(), "private packet output is not an ordinary file")
        target.write_bytes(MARKER)

    command = [PYTHON, str(PRIVATE / PACKETS[0] / "reproduce_current_coverage.py")]
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    completed = subprocess.run(command, cwd=PRIVATE, env=env, capture_output=True)
    (FIXTURE / "legacy.stdout.bin").write_bytes(completed.stdout)
    (FIXTURE / "legacy.stderr.bin").write_bytes(completed.stderr)
    require(completed.returncode == 0, "actual original default command failed; inspect retained stderr")
    outputs_after = {}
    for name, relative in OUTPUTS.items():
        raw = (PRIVATE / relative).read_bytes()
        expected = git("show", SOURCE_COMMIT + ":" + relative)
        require(raw != MARKER, "legacy writer did not replace the existing marker: " + name)
        require(raw == expected, "legacy writer output differs from exact retained report: " + name)
        outputs_after[name] = {
            "path": relative,
            "bytes": len(raw),
            "sha256": sha(raw),
            "replaced_marker": True,
            "matches_exact_retained_report": True,
        }
    original_after = {}
    for name, relative in OUTPUTS.items():
        raw = (ROOT / relative).read_bytes()
        original_after[name] = {"path": relative, "bytes": len(raw), "sha256": sha(raw)}
        require(raw == (ROOT / relative).read_bytes(), "original workspace packet changed")
        require(original_after[name] == original_before[name],
                "original packet bytes changed outside the private mirror: " + relative)
    evidence = {
        "status": "reproduced",
        "issue": 1469,
        "reproduction": "The intact documented legacy default command exited zero and replaced both pre-existing marker files in a complete private packet mirror.",
        "source_commit": SOURCE_COMMIT,
        "private_repo": str(PRIVATE.relative_to(ROOT)),
        "git_directory_locator": git_dir,
        "command": command,
        "actual_exit_code": completed.returncode,
        "stdout": {"path": str((FIXTURE / "legacy.stdout.bin").relative_to(ROOT)),
                   "bytes": len(completed.stdout), "sha256": sha(completed.stdout)},
        "stderr": {"path": str((FIXTURE / "legacy.stderr.bin").relative_to(ROOT)),
                   "bytes": len(completed.stderr), "sha256": sha(completed.stderr)},
        "marker": {"bytes": len(MARKER), "sha256": sha(MARKER),
                   "copies": [str((FIXTURE / "before-markers" / (name + ".current-coverage.json")).relative_to(ROOT))
                              for name in OUTPUTS]},
        "original_outputs_before": original_before,
        "private_outputs_after": outputs_after,
        "original_outputs_after": original_after,
        "copied_packet_files": copied,
        "area_helper": {"path": helper_path, "commit": SOURCE_COMMIT,
                        "bytes": len(helper), "sha256": sha(helper)},
        "scope": "Private copied packets and outputs only; no source, producer or original output outside the declared issue-owned prefix was written.",
    }
    (FIXTURE / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({name: row["sha256"] for name, row in outputs_after.items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        raise
