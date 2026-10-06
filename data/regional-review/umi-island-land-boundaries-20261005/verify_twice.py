#!/usr/bin/env python3
"""Run the bounded comparator twice and record byte-for-byte reproducibility."""
from hashlib import sha256
from pathlib import Path
import json
import subprocess
import sys

root = Path(__file__).resolve().parent
runner = root / "verify.py"
result = root / "results.json"
hashes = []
for _ in range(2):
    subprocess.run([sys.executable, str(runner)], check=True, cwd=root.parents[2])
    hashes.append(sha256(result.read_bytes()).hexdigest())
if hashes[0] != hashes[1]:
    raise SystemExit("non-reproducible result bytes")
out = {"method_id": "site-outline-comparison", "kind": "reproducibility",
       "outcome": "passed", "run_one_sha256": hashes[0],
       "run_two_sha256": hashes[1]}
(root / "validation/reproducibility.json").write_text(
    json.dumps(out, sort_keys=True, separators=(",", ":")) + "\n")
print(json.dumps(out, sort_keys=True))
