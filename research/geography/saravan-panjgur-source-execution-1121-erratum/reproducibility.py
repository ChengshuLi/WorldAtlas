"""Compare complete deterministic payload sets from the two real CLIs."""
import hashlib
import json
from pathlib import Path

from authenticated import OWNED, ROOT, CapturedBaseline, load_trusted_helper, output_writer

PACKET = ROOT / OWNED


def hash_run(prefix):
    root = PACKET / "vintages" / prefix
    names = ["result.json", "positive-control.json", "negative-control.json"]
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}


def aggregate(rows):
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def run():
    results = []
    for method, one, two in [
        ("authenticated-source-comparison", "comparison-verified-1", "comparison-verified-2"),
        ("osm-shared-edge-source-membership", "shared-edge-verified-1", "shared-edge-verified-2"),
    ]:
        first, second = hash_run(one), hash_run(two)
        first_sha, second_sha = aggregate(first), aggregate(second)
        if first != second or first_sha != second_sha:
            raise ValueError(f"Two complete {method} payload runs are not byte-for-byte reproducible")
        results.append({"method_id": method, "kind": "reproducibility", "outcome": "passed",
            "run_one_sha256": first_sha, "run_two_sha256": second_sha,
            "payload_files": first, "fresh_vintages": [one, two],
            "note": "All result and positive/negative control payloads match exactly; path-specific publication receipts are separate."})
    return results


if __name__ == "__main__":
    results = run()
    manifest = json.loads((PACKET / "evidence-quality.json").read_bytes())
    helper = load_trusted_helper(manifest)
    base = CapturedBaseline(helper, manifest)
    writer = output_writer(base, "reproducibility-verified", ["comparison.json", "shared-edge.json"])
    records = writer.publish_bytes({name: (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        for name, value in zip(["comparison.json", "shared-edge.json"], results)})
    print(json.dumps({"records": records, "results": results}, ensure_ascii=False, indent=2))
