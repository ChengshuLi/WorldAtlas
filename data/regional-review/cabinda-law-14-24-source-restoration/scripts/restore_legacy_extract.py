#!/usr/bin/env python3
"""Restore the four scoped 2018 geoBoundaries features from its pinned source."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_URL = (
    "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/"
    "9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbHumanitarian/"
    "AGO/ADM2/geoBoundaries-AGO-ADM2.geojson"
)
SOURCE_SHA256 = "44e58b2a8c2fefb9369294a32e2adde3e3637b9e02e8f1e2c53b400bec04f404"
TARGET_IDS = {
    "16411231B22766430211667",
    "16411231B42954517222252",
    "16411231B63355352791940",
    "16411231B679187258105",
}
OUT = Path(__file__).resolve().parents[1] / "sources/geoboundaries-2018/cabinda-four-features.geojson"


def main() -> None:
    request = Request(SOURCE_URL, headers={"User-Agent": "WorldAtlas-geography-evidence/1"})
    with urlopen(request, timeout=60) as response:
        original = response.read()
    digest = hashlib.sha256(original).hexdigest()
    if digest != SOURCE_SHA256:
        raise SystemExit(f"pinned source hash mismatch: {digest}")

    collection = json.loads(original)
    found: dict[str, dict] = {}
    for feature in collection.get("features", []):
        props = feature.get("properties", {})
        source_id = props.get("shapeID")
        if source_id in TARGET_IDS:
            if source_id in found:
                raise SystemExit(f"duplicate source feature: {source_id}")
            found[source_id] = feature
    if set(found) != TARGET_IDS:
        raise SystemExit(f"source roster mismatch; missing={sorted(TARGET_IDS - set(found))}")

    result = {
        "type": "FeatureCollection",
        "name": "geoBoundaries 2018 AGO ADM2 Cabinda scoped extract",
        "features": [found[source_id] for source_id in sorted(TARGET_IDS)],
    }
    payload = (json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists() and OUT.read_bytes() != payload:
        raise SystemExit(f"refusing to replace existing evidence: {OUT}")
    OUT.write_bytes(payload)
    print(json.dumps({
        "source_url": SOURCE_URL,
        "source_sha256": digest,
        "source_bytes": len(original),
        "source_feature_count": len(collection.get("features", [])),
        "target_feature_count": len(found),
        "extract_path": str(OUT),
        "extract_sha256": hashlib.sha256(payload).hexdigest(),
        "extract_bytes": len(payload),
        "license": "CC BY 3.0 IGO; attribution retained in source-inventory.json",
    }, indent=2))


if __name__ == "__main__":
    main()
