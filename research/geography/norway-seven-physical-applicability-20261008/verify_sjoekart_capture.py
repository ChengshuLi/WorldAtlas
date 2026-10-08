#!/usr/bin/env python3
"""Verify retained bounded Kartverket WFS custody offline; never reads coordinates."""
from __future__ import annotations
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "sources" / "sjoekart-dybdedata-wfs-20261008"
INDEX = SOURCE / "source-snapshot-index.json"

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]

def main() -> None:
    index = json.loads(INDEX.read_text())
    if index["record_count"] != len(index["captures"]) or len(index["captures"]) != 14:
        raise SystemExit("capture count/index mismatch")
    total = 0
    rows = []
    for capture in index["captures"]:
        path = (ROOT / capture["path"]).resolve()
        if SOURCE.resolve() not in path.parents:
            raise SystemExit("capture path escapes source folder")
        raw = path.read_bytes()
        if len(raw) != capture["bytes"] or sha(raw) != capture["sha256"]:
            raise SystemExit(f"retained bytes mismatch: {path.name}")
        root = ET.fromstring(raw)
        features = [child for member in root if local(member.tag) == "member" for child in list(member)]
        ids = [next((value for key, value in feature.attrib.items() if local(key) == "id"), None) for feature in features]
        if len(features) != capture["member_count"] or ids != capture["feature_ids"]:
            raise SystemExit(f"feature-member identity mismatch: {path.name}")
        if root.get("numberMatched") != capture["number_matched_attribute"] or root.get("numberReturned") != capture["number_returned_attribute"]:
            raise SystemExit(f"raw count attributes mismatch: {path.name}")
        total += len(raw)
        rows.append({"path": capture["path"], "bytes": len(raw), "sha256": sha(raw), "members": len(features), "ids_match": True})
    if total != index["total_response_bytes"]:
        raise SystemExit("total byte count mismatch")
    print(json.dumps({"status": "offline-custody-verified", "response_count": len(rows), "feature_count": sum(x["members"] for x in rows), "bytes": total, "geometry_read": False, "response_files": rows}, indent=2))

if __name__ == "__main__":
    main()
