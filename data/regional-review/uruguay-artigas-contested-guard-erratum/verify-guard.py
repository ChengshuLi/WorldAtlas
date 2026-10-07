#!/usr/bin/env python3
"""Exercise preservation and drift rejection without touching historical evidence."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

PACKET = Path(__file__).resolve().parent
RUNNER = PACKET / "reproduce.py"
OUTPUTS = PACKET / "outputs"


def attempt(path):
    return subprocess.run([sys.executable, str(RUNNER), "--output", str(path)], capture_output=True)


def must_fail(label, path):
    before = set(p.name for p in OUTPUTS.iterdir())
    result = attempt(path)
    after = set(p.name for p in OUTPUTS.iterdir())
    if result.returncode == 0 or after != before:
        raise AssertionError(label + " was not safely rejected")


existing = Path(tempfile.mkdtemp(prefix="existing-sentinel-", dir=str(OUTPUTS)))
sentinel = existing / "keep.txt"
sentinel.write_text("preserve-me\n")
try:
    must_fail("existing destination", existing)
    assert sentinel.read_text() == "preserve-me\n"
finally:
    sentinel.unlink()
    existing.rmdir()
must_fail("traversal", OUTPUTS / ".." / "escape")

with tempfile.TemporaryDirectory(prefix="artigas-guard-") as outside:
    link = OUTPUTS / "symlink-escape"
    link.symlink_to(outside, target_is_directory=True)
    try:
        must_fail("symlink destination", link)
        assert list(Path(outside).iterdir()) == []
    finally:
        link.unlink()

for relative, marker in [
    ("inputs/code/capsule-reproduce.py", b"# drift probe\n"),
    ("inputs/sources/ury-gb-2017.geojson", b" "),
]:
    target = PACKET / relative
    original = target.read_bytes()
    try:
        target.write_bytes(original + marker)
        must_fail("drift in " + relative, OUTPUTS / ("drift-" + Path(relative).stem))
    finally:
        target.write_bytes(original)

print("passed: existing-output sentinel, traversal, symlink destination, code drift, source drift")
