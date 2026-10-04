#!/usr/bin/env python3
"""Read-only output and immutable baseline descriptor verification."""
import hashlib, json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/equatorial-micronesia-baseline-followup/"
m = json.loads((ROOT / OWNED / "evidence-quality.json").read_text())
def verify(path, size, digest):
    raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{m['baseline']['commit']}:{path}"]) if path in {x['path'] for x in m['baseline']['files']} else (ROOT / path).read_bytes()
    assert len(raw) == size and hashlib.sha256(raw).hexdigest() == digest, path
for f in m["baseline"]["files"]: verify(f["path"], f["bytes"], f["sha256"])
for f in m["outputs"]: verify(f["path"], f["bytes"], f["sha256"])
for s in m["sources"]:
    for f in s.get("files", []): verify(f["path"], f["bytes"], f["sha256"])
assert len(m["baseline"]["subject_files"]) == len(m["subject_ids"]) == 3
print(json.dumps({"result":"PASS", "baseline_files":len(m["baseline"]["files"]), "outputs":len(m["outputs"]), "subjects":3}, indent=2))
