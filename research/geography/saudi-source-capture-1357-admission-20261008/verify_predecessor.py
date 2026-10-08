#!/usr/bin/env python3
"""Prove the complete 148-file predecessor packet is byte/mode preserved."""
from __future__ import annotations

import json
from pathlib import Path
import stat
import subprocess

import admission
import run_safe


PREFIX = run_safe.PREDECESSOR


def verify(repo: Path, commit: str) -> dict:
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise admission.AdmissionError("Expected exact immutable baseline commit")
    raw = subprocess.check_output(["git", "-C", str(repo), "ls-tree", "-r", "-l", commit, "--", PREFIX])
    rows = []
    total = 0
    for entry in raw.decode("utf-8").splitlines():
        metadata, path = entry.split("\t", 1)
        mode, kind, oid, size = metadata.split()
        if kind != "blob" or mode not in ("100644", "100755"):
            raise admission.AdmissionError(f"Predecessor contains a non-ordinary baseline member: {path}")
        size = int(size)
        if size > admission.PER_FILE_BYTES:
            raise admission.AdmissionError(f"Predecessor file exceeds per-file verification cap: {path}")
        baseline = subprocess.check_output(["git", "-C", str(repo), "cat-file", "blob", oid])
        current_path = repo / path
        try:
            info = current_path.lstat()
        except FileNotFoundError:
            raise admission.AdmissionError(f"Predecessor file is missing from worktree: {path}") from None
        if not stat.S_ISREG(info.st_mode):
            raise admission.AdmissionError(f"Predecessor file is not an ordinary worktree file: {path}")
        current = admission.read_regular(current_path)
        actual_mode = "100755" if info.st_mode & stat.S_IXUSR else "100644"
        digest = admission.sha256(baseline)
        if len(baseline) != size or current != baseline or actual_mode != mode:
            raise admission.AdmissionError(f"Predecessor file bytes or mode differ from baseline: {path}")
        rows.append({"path": path, "mode": mode, "git_blob_oid": oid,
                     "bytes": size, "sha256": digest})
        total += size
    rows.sort(key=lambda row: row["path"])
    if len(rows) != 148 or total != 82_587_757:
        raise admission.AdmissionError("Predecessor packet count/byte total differs from the accepted inventory")
    changed = subprocess.check_output(["git", "-C", str(repo), "diff", "--name-only", commit, "--", PREFIX]).decode().splitlines()
    if changed:
        raise admission.AdmissionError("Git reports changed predecessor paths")
    return {"version": 1, "status": "all-predecessor-files-and-modes-preserved",
            "baseline_commit": commit, "file_count": len(rows), "total_bytes": total,
            "files": rows, "changed_paths": [], "source_or_geographic_approval": False}


def main() -> int:
    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--repo", default=str(run_safe.REPO_ROOT))
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--output")
    args = parser.parse_args()
    repo = Path(args.repo).resolve(strict=True)
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "--verify", "--end-of-options", args.commit + "^{commit}"], text=True).strip()
    result = verify(repo, commit)
    if args.output:
        admission.write_exclusive_json(repo, args.output, result)
    print(json.dumps({key: value for key, value in result.items() if key != "files"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
