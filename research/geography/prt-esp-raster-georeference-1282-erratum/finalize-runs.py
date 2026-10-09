#!/usr/bin/env python3
"""Bind the two fresh native-footprint audit runs without rewriting them."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OWN = Path(__file__).resolve().parent

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def main():
    run_names = sys.argv[1:3] if len(sys.argv) >= 3 else ["run-1", "run-2"]
    assert len(run_names) == 2 and run_names[0] != run_names[1]
    outs = []
    for name in run_names:
        assert name.replace("-", "").isalnum(), "run names must be simple IDs"
        directory = OWN / "runs" / name
        result = directory / "native-coverage-audit.json"
        manifest = directory / "run-manifest.json"
        assert result.is_file() and not result.is_symlink() and not manifest.exists()
        data = json.loads(result.read_text())
        assert data["method_id"] == "native-geotiff-coverage-and-pixel-controls"
        assert data["outcome"] == "passed"
        outs.append({"run": name, "path": str(result.relative_to(OWN)), "sha256": digest(result), "bytes": result.stat().st_size,
                     "audit_code_sha256": data["input_bindings"]["audit_code"]["sha256"],
                     "input_bindings": data["input_bindings"]})
        manifest.write_text(json.dumps({"schema": "worldatlas-source-run-v1", "run": name,
                                        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                                        "method_id": data["method_id"], "outcome": data["outcome"],
                                        "output": {"path": str(result.relative_to(OWN)), "bytes": result.stat().st_size, "sha256": digest(result)},
                                        "audit_code": data["input_bindings"]["audit_code"],
                                        "input_bindings": data["input_bindings"],
                                        "interpretation": "Only native headers, three exact one-pixel controls and geometric tile-footprint coverage; no monthly surface-water counts."}, indent=2, sort_keys=True) + "\n")
    assert outs[0]["sha256"] == outs[1]["sha256"]
    repro = OWN / f"reproducibility-{run_names[0]}-{run_names[1]}.json"
    assert not repro.exists()
    repro.write_text(json.dumps({"schema": "worldatlas-source-reproducibility-v1", "method_id": "native-geotiff-coverage-and-pixel-controls",
                                 "status": "reproduced-byte-identically", "runs": outs,
                                 "run_one_sha256": outs[0]["sha256"], "run_two_sha256": outs[1]["sha256"],
                                 "limits": ["This repeated source-footprint phase does not rerun the refused 578,813,952-byte full monthly pixel phase.",
                                            "Equal bytes show deterministic output from the same pinned sources and method; they do not certify geographic truth or physical classification."]}, indent=2, sort_keys=True) + "\n")
    print(f"matching audit outputs: {outs[0]['sha256']}; reproducibility receipt {digest(repro)}")

if __name__ == "__main__":
    main()
