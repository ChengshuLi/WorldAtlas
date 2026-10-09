#!/usr/bin/env python3
"""Prove the legacy validator consumes the exact ledger bytes we validated."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import uuid
from unittest.mock import patch

import reproduce


def main() -> int:
    ledger = reproduce.ROOT / reproduce.LEDGER
    original_read_text = Path.read_text
    forbidden_reads = []

    def reject_reopen(path, *args, **kwargs):
        if Path(path).resolve() == ledger.resolve():
            forbidden_reads.append(str(path))
            raise AssertionError("legacy validator reopened the pointer ledger")
        return original_read_text(path, *args, **kwargs)

    run_id = "ledger-binding-" + uuid.uuid4().hex
    with patch.object(Path, "read_text", reject_reopen):
        receipt = reproduce.run(run_id)
    expected = hashlib.sha256(ledger.read_bytes()).hexdigest()
    if forbidden_reads or receipt["pointer_ledger_sha256"] != expected or receipt["pointer_record_count"] != 6:
        raise AssertionError("validated ledger bytes were not bound to the executed run")
    report = {
        "version": 1,
        "method_id": "batch3-provenance-crossfield-validator",
        "kind": "positive-control",
        "outcome": "passed",
        "run_id": run_id,
        "pointer_ledger_sha256": receipt["pointer_ledger_sha256"],
        "pointer_record_count": receipt["pointer_record_count"],
        "legacy_ledger_reopen_blocked": True,
        "note": "The actual entry point completed while any second filesystem read of the ledger would raise; its receipt binds the original six validated records.",
    }
    output = reproduce.ROOT / reproduce.OWNED / "ledger-binding-control.json"
    with output.open("xb") as stream:
        stream.write(reproduce.canonical(report))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
