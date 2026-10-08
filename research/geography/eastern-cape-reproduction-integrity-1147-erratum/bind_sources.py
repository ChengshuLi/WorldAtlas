#!/usr/bin/env python3
"""Verify the exact #1371 issue pins and bind them to the current-main baseline."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/eastern-cape-reproduction-integrity-1147-erratum/"
ISSUE_BODY = ROOT / OWNED / "source-records/issue-contract-20261007.md"
ISSUE_BODY_SHA256 = "b1e95090949c9d058284bc58290e0fd9650ed94afc2aaa16eb607369c78cc916"
BASELINE_COMMIT = "de506f51100568e150e51f2926a5259b71e55272"
CURRENT_CODE = {
    "scripts/evidence/immutable.py": "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46",
    "scripts/evidence/geometry.py": "4b016a4efccf8a1080b048f350c0db94ac14343b40e0ed890c2ce4d2300436a9",
    "scripts/ellipsoidal_area.py": "4ead1c5de909b257a7b300984e4d3dc56124e9a6c0d27240662024e44fd8ed12",
}
PIN_RE = re.compile(
    r"^- `(baseline_\d+|original_1147_\d+)`: `([^`]+)` at `([a-f0-9]{40})`; "
    r"(\d+) bytes; SHA-256 `([a-f0-9]{64})`\.$", re.M
)


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE)


def blob_digest(commit: str, path: str) -> tuple[int, str]:
    row = git("ls-tree", "-z", commit, "--", path).decode().rstrip("\0")
    if not row.startswith(("100644 ", "100755 ")) or row.split("\t", 1)[-1] != path:
        raise ValueError(f"Expected ordinary committed source file: {path}")
    blob = row.split()[2]
    size = int(git("cat-file", "-s", blob))
    proc = subprocess.Popen(["git", "-C", str(ROOT), "cat-file", "blob", blob], stdout=subprocess.PIPE)
    digest = hashlib.sha256()
    count = 0
    assert proc.stdout is not None
    for block in iter(lambda: proc.stdout.read(1024 * 1024), b""):
        digest.update(block)
        count += len(block)
    if proc.wait() != 0 or count != size:
        raise ValueError(f"Could not hash complete Git blob: {path}")
    return count, digest.hexdigest()


def main() -> None:
    head = git("rev-parse", "HEAD").decode().strip()
    if subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", BASELINE_COMMIT, head]).returncode != 0:
        raise ValueError("Declared fresh-main source baseline must be an ancestor of this work branch")
    raw_body = ISSUE_BODY.read_bytes()
    if hashlib.sha256(raw_body).hexdigest() != ISSUE_BODY_SHA256:
        raise ValueError("Captured exact issue body does not match the reviewed body digest")
    body = raw_body.decode("utf-8")
    matches = list(PIN_RE.finditer(body))
    if len(matches) != 27:
        raise ValueError(f"Expected all 27 issue-declared pins; found {len(matches)}")
    contract = []
    for m in matches:
        name, path, contract_commit, raw_size, digest = m.groups()
        contract.append({"id": name, "path": path, "contract_commit": contract_commit,
                         "bytes": int(raw_size), "sha256": digest})
    expected_ids = [f"baseline_{i}" for i in range(1, 8)] + [f"original_1147_{i}" for i in range(1, 21)]
    if [x["id"] for x in contract] != expected_ids or len({x["path"] for x in contract}) != 27:
        raise ValueError("Issue pin roster is incomplete, duplicated or reordered")

    files = []
    total = 0
    for row in contract:
        size, digest = blob_digest(BASELINE_COMMIT, row["path"])
        if size != row["bytes"] or digest != row["sha256"]:
            raise ValueError(f"Current-main source bytes differ from issue pin: {row['path']}")
        files.append({"path": row["path"], "bytes": size, "sha256": digest, "hash_kind": "file-bytes"})
        total += size
    helper_pins = []
    for path, expected in CURRENT_CODE.items():
        size, digest = blob_digest(BASELINE_COMMIT, path)
        if digest != expected:
            raise ValueError(f"Current-main helper differs from reviewed pin: {path}")
        helper_pins.append({"path": path, "bytes": size, "sha256": digest, "hash_kind": "file-bytes"})
        total += size
    if total > 256 * 1024 * 1024:
        raise ValueError(f"Complete pinned input/code phase exceeds 256 MiB: {total}")

    lock = {
        "version": 1,
        "issue_number": 1371,
        "issue_body_sha256": ISSUE_BODY_SHA256,
        "baseline_commit": BASELINE_COMMIT,
        "contract_pins": contract,
        "files": sorted(files + helper_pins, key=lambda x: x["path"]),
        "complete_pinned_input_and_code_bytes": total,
        "phase_limit_bytes": 268435456,
        "current_project_code": helper_pins,
    }
    target = ROOT / OWNED / "source-lock.json"
    encoded = (json.dumps(lock, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()
    if target.exists():
        if target.is_symlink() or target.read_bytes() != encoded:
            raise ValueError("Existing source lock differs; preserve it and choose a fresh lock vintage")
    else:
        with target.open("xb") as stream:
            stream.write(encoded)
    print(json.dumps({"issue": 1371, "pin_count": len(files), "project_code_pins": len(helper_pins),
                      "baseline_commit": BASELINE_COMMIT, "complete_phase_input_code_bytes": total,
                      "issue_body_sha256": ISSUE_BODY_SHA256, "source_lock_sha256": hashlib.sha256(encoded).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
