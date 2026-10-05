#!/usr/bin/env python3
"""Run packet-specific controls for the shared WGS84 geometry helper."""
import hashlib
import json
import sys
from pathlib import Path

from shapely.geometry import Polygon, shape

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "data/regional-review/followup-northern-macedonia-422-roster-20261005"
sys.path.insert(0, str(ROOT / "scripts"))
from evidence.geometry import land_area_m2, transform_point

BASELINE = "5b72dc3adf48b089c3319b18c3a447468196176a"
SOURCE_PATH = "data/regional-review/regional-review-3c4fe25a21fa428d/source/gb/gb-MKD-ADM2.geojson"
SOURCE_SHA256 = "0a0d7340810fb353c3faa37ab9afea20830ce6124083ffe6321182277da61d01"
METHOD = "hdx-source-equivalence-and-current-layer-crosswalk"


def main():
    raw = __import__("subprocess").check_output(["git", "-C", str(ROOT), "show", f"{BASELINE}:{SOURCE_PATH}"])
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise SystemExit("Pinned source bytes changed")
    geojson = json.loads(raw)
    geometry = shape(geojson["features"][0]["geometry"])
    x, y = transform_point(10, 45, "EPSG:3857")
    positive = {
        "version": 1, "method_id": METHOD, "kind": "positive-control", "outcome": "passed",
        "checks": {"longitude_first_transform": abs(x - 1113194.9079327357) < 1e-5 and abs(y - 5621521.486192066) < 1e-5,
                   "pinned_source_feature_positive_ellipsoidal_area": land_area_m2(geometry) > 0},
        "source_sha256": SOURCE_SHA256,
    }
    if not all(positive["checks"].values()):
        raise SystemExit("Positive geography control failed")
    negative_checks = {}
    try:
        transform_point(10, 95, "EPSG:3857")
    except ValueError:
        negative_checks["invalid_latitude_rejected"] = True
    try:
        land_area_m2(Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)]))
    except ValueError:
        negative_checks["invalid_geometry_rejected_without_repair"] = True
    negative = {"version": 1, "method_id": METHOD, "kind": "negative-control", "outcome": "passed", "checks": negative_checks}
    if len(negative_checks) != 2:
        raise SystemExit("Negative geography control failed")
    (PACKET / "geometry-positive-control.json").write_text(json.dumps(positive, indent=2) + "\n", encoding="utf-8")
    (PACKET / "geometry-negative-control.json").write_text(json.dumps(negative, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"positive": positive, "negative": negative}, sort_keys=True))


if __name__ == "__main__":
    main()
