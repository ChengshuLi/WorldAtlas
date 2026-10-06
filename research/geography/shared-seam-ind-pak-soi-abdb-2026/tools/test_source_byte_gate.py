#!/usr/bin/env python3
"""Exercise the same length/hash acceptance gate used before metadata inspection."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from inspect_metadata import validate_source_bytes


def main() -> None:
    fixture = b"WorldAtlas source-byte gate fixture v1\x00\x01"
    expected_sha256 = hashlib.sha256(fixture).hexdigest()
    validate_source_bytes(fixture, len(fixture), expected_sha256)

    def rejected(candidate: bytes) -> bool:
        try:
            validate_source_bytes(candidate, len(fixture), expected_sha256)
        except ValueError:
            return True
        return False

    mutated = bytearray(fixture)
    mutated[-1] ^= 1
    mutation_rejected = rejected(bytes(mutated))
    truncation_rejected = rejected(fixture[:-1])
    if not mutation_rejected or not truncation_rejected:
        raise SystemExit("source-byte gate accepted a mutated or truncated fixture")

    repo = Path(__file__).resolve().parents[4]
    execution = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    gate_path = Path(__file__).with_name("inspect_metadata.py")
    print(json.dumps({
        "version": 1,
        "method_id": "soi-metadata-audit",
        "kind": "negative-control",
        "outcome": "passed",
        "control_scope": "The shared length/SHA-256 gate rejects changed or incomplete inputs.",
        "fixture_is_metadata_archive": False,
        "fixture_bytes": len(fixture),
        "fixture_sha256": expected_sha256,
        "execution_commit": execution,
        "gate_code_sha256": hashlib.sha256(gate_path.read_bytes()).hexdigest(),
        "mutation_last_byte_rejected_by_gate": mutation_rejected,
        "one_byte_truncation_rejected_by_gate": truncation_rejected,
        "metadata_archive_claim": "No mutation-control claim about the locally inspected ZIP; it is excluded from this packet.",
    }, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
