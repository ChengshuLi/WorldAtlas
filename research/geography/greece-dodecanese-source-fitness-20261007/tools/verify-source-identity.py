#!/usr/bin/env python3
"""Read-only check of pinned Greek ADM3 source bytes and 11 source/contact IDs."""
import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

SOURCE_COMMIT = "1bf4bb01d76a76953d4a11308f5af2dd50fe3365"
SOURCE_PATH = "coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-GRC-ADM3-000.bin.gz"
BASELINE_COMMIT = "5fa15de475f17ff93e205b767857d1e41a30949e"
CURRENT_PATH = "data/geography/part-9.json"
SOURCE_ENCODED_SHA256 = "55dcb304944675e95c3530f02b71da019a6f647d38300cf1b7a337659fa87b5b"
SOURCE_DECODED_SHA256 = "72179d50a8a85aa9fecf996761f905db9e8a59f4eb882f8481f88651692b7e18"


def git_bytes(root: Path, commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), "show", f"{commit}:{path}"])


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="WorldAtlas repository root")
    parser.add_argument("--handoff", default="research/geography/greece-dodecanese-source-fitness-20261007/inputs/greek-complete-source-ready-handoff.json")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    handoff = json.loads((root / args.handoff).read_text(encoding="utf-8"))
    encoded = git_bytes(root, SOURCE_COMMIT, SOURCE_PATH)
    decoded = gzip.decompress(encoded)
    if sha256(encoded) != SOURCE_ENCODED_SHA256 or sha256(decoded) != SOURCE_DECODED_SHA256:
        raise SystemExit("Pinned original source bytes changed")
    source = json.loads(decoded)
    features = source.get("features")
    if not isinstance(features, list) or len(features) != 326:
        raise SystemExit("Original source feature count changed")
    source_ids = {"gb:GRC:ADM3:" + f.get("properties", {}).get("shapeID", "") for f in features}
    contacts = handoff["contact_ids"]
    missing_source = sorted(set(contacts) - source_ids)
    if len(contacts) != 11 or missing_source:
        raise SystemExit(f"Original source contacts changed or are missing: {missing_source}")
    current = json.loads(git_bytes(root, BASELINE_COMMIT, CURRENT_PATH))
    current_ids = {f.get("id", f.get("properties", {}).get("id")) for f in current.get("features", [])}
    missing_current = sorted(set(contacts) - current_ids)
    if missing_current:
        raise SystemExit(f"Pinned current contact features are missing: {missing_current}")
    names = {"gb:GRC:ADM3:" + f["properties"]["shapeID"]: f["properties"].get("shapeName") for f in features}
    print(json.dumps({"status": "pass", "encoded_bytes": len(encoded), "encoded_sha256": sha256(encoded),
                      "decoded_bytes": len(decoded), "decoded_sha256": sha256(decoded),
                      "original_feature_count": len(features), "contact_count": len(contacts),
                      "contact_names": {contact: names[contact] for contact in contacts},
                      "current_contact_container": CURRENT_PATH, "current_contact_count": len(contacts)},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
