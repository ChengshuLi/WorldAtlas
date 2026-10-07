#!/usr/bin/env python3
"""Derive the standard reproducibility receipt from immutable actual run outputs."""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OWNED = ROOT / "data/regional-review/west-siberia-roles-followup-20261006"
ERRATUM = OWNED / "findings/errata-20261007"
ORIGINAL_RESULT = ERRATUM / "reproduction-result.json"
OUTPUT = ERRATUM / "reproduction-receipt.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def main():
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise RuntimeError("final receipt destination is occupied; do not overwrite")
    original_raw = ORIGINAL_RESULT.read_bytes()
    original = json.loads(original_raw)
    if original.get("outcome") != "passed" or len(original.get("runs", [])) != 2:
        raise RuntimeError("two successful actual run receipts are required")
    products = []
    for run_id, run in zip(("run-one", "run-two"), original["runs"]):
        directory = ERRATUM / run_id
        manifest_raw = (directory / "run-manifest.json").read_bytes()
        manifest = json.loads(manifest_raw)
        actual = []
        for name in ("assessment.json", "issue-contract.json", "positive-control.json", "negative-control.json"):
            raw = (directory / name).read_bytes()
            actual.append({"name": name, "bytes": len(raw), "sha256": sha(raw)})
        if actual != [{"name": Path(x["path"]).name, "bytes": x["bytes"], "sha256": x["sha256"]} for x in manifest["products"]]:
            raise RuntimeError("immutable run product differs from its run manifest")
        aggregate = sha(canonical(actual))
        if aggregate != run.get("content_sha256") or manifest.get("process_id") != run.get("process_id"):
            raise RuntimeError("immutable run products differ from original two-run receipt")
        products.append({"run_id": run_id, "content_sha256": aggregate, "run_manifest_sha256": sha(manifest_raw), "products": actual})
    if products[0]["content_sha256"] != products[1]["content_sha256"]:
        raise RuntimeError("independent complete run products differ")
    result = {
        "version": 1,
        "method_id": "west-siberia-20261007-erratum",
        "kind": "reproducibility",
        "outcome": "passed",
        "run_one_sha256": products[0]["content_sha256"],
        "run_two_sha256": products[1]["content_sha256"],
        "runs": products,
        "derived_from_reproduction_result_sha256": sha(original_raw),
        "finalizer_sha256": sha(Path(__file__).read_bytes()),
        "evaluation_commit": original["evaluation_commit"],
        "originals_before": original["originals_before"],
        "originals_after": original["originals_after"],
        "independent_equal_product_hashes": True,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    with OUTPUT.open("xb") as stream:
        stream.write(canonical(result))
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": "passed", "run_one_sha256": result["run_one_sha256"], "run_two_sha256": result["run_two_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
