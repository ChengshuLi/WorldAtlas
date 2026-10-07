#!/usr/bin/env python3
"""Resolve the pinned 70-component scope to its exact source geometries."""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
from pathlib import Path

from shapely.geometry import shape, box


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "research/geography/portugal-spain-gap-source-families-20261007"
INDEX = PACKAGE / "inputs/complete-input-index.json"
OUTPUT = PACKAGE / "inputs/selected-70-component-geometries.geojson"
REPORT = PACKAGE / "inputs/jrc-2024-window-plan.json"
PIXEL = 0.00025
IMAGE_SIZE = 40000
TILE_SIZE = 1024


def main() -> None:
    index = json.loads(INDEX.read_text())
    wanted = set(index["scope"]["component_ids"])
    found = {}
    used_inputs = []
    for alias in index["component_v3_alias_resolution"]:
        desc = alias["ordinary_payload_descriptor"]
        raw = subprocess.check_output(["git", "show", f"{desc['commit']}:{desc['path']}"], cwd=ROOT)
        if len(raw) != desc["bytes"] or hashlib.sha256(raw).hexdigest() != desc["sha256"]:
            raise SystemExit(f"pinned payload mismatch: {desc['path']}")
        decoded = gzip.decompress(raw)
        if hashlib.sha256(decoded).hexdigest() != alias["virtual_original_descriptor"]["uncompressed_sha256"]:
            raise SystemExit(f"decoded payload mismatch: {desc['path']}")
        collection = json.loads(decoded)
        used_inputs.append({"commit": desc["commit"], "path": desc["path"], "bytes": len(raw), "sha256": desc["sha256"]})
        for feature in collection["features"]:
            fid = feature.get("id")
            if fid in wanted:
                if fid in found:
                    raise SystemExit(f"duplicate component geometry: {fid}")
                found[fid] = feature
    if set(found) != wanted:
        raise SystemExit(f"scope mismatch: wanted={len(wanted)} found={len(found)}")

    features = []
    per_component = []
    tiles = set()
    for fid in sorted(wanted):
        source = found[fid]
        geom = shape(source["geometry"])
        if geom.is_empty or not geom.is_valid:
            raise SystemExit(f"invalid pinned geometry: {fid}")
        features.append({"type": "Feature", "id": fid, "properties": {"source_payload_id": fid}, "geometry": source["geometry"]})
        candidate = []
        minx, miny, maxx, maxy = geom.bounds
        for north in (40, 50):
            south = north - 10
            tile_box = box(-10, south, 0, north)
            part = geom.intersection(tile_box)
            if part.is_empty:
                continue
            x0, y0, x1, y1 = part.bounds
            c0 = max(0, min(IMAGE_SIZE - 1, int((x0 + 10) / PIXEL)))
            c1 = max(0, min(IMAGE_SIZE - 1, int((x1 + 10) / PIXEL)))
            r0 = max(0, min(IMAGE_SIZE - 1, int((north - y1) / PIXEL)))
            r1 = max(0, min(IMAGE_SIZE - 1, int((north - y0) / PIXEL)))
            for tr in range(r0 // TILE_SIZE, r1 // TILE_SIZE + 1):
                for tc in range(c0 // TILE_SIZE, c1 // TILE_SIZE + 1):
                    key = (north, tr, tc)
                    candidate.append(key)
                    tiles.add(key)
        per_component.append({"component_id": fid, "bbox": [minx, miny, maxx, maxy], "source_feature_area_deg2": geom.area, "candidate_full_resolution_tiles": [list(t) for t in sorted(set(candidate))]})

    OUTPUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")) + "\n")
    out_hash = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    plan = {
        "schema": "worldatlas-jrc-2024-window-plan-v1",
        "scope_component_count": len(features),
        "component_roster_sha256": index["scope"]["component_ids_sha256"],
        "source_geometry_payloads": used_inputs,
        "selected_geometry_file": {"path": str(OUTPUT.relative_to(ROOT)), "bytes": OUTPUT.stat().st_size, "sha256": out_hash},
        "raster_product": {"name": "JRC Global Surface Water monthly history v1.5", "year": 2024, "tiles": ["10W_30N", "10W_40N"], "pixel_size_degrees": PIXEL, "pixel_type": "unsigned 8-bit categorical", "full_resolution": [IMAGE_SIZE, IMAGE_SIZE], "internal_tile_size": TILE_SIZE},
        "unique_full_resolution_tiles": len(tiles),
        "unique_source_month_tile_assets": len(tiles) * 12,
        "components": per_component,
        "limits": [
            "Tile windows bound the read but do not establish water, ownership, cause, or historical state.",
            "Raster summaries use source-grid pixel centers; partial pixels and unsampled geometry remain unknown.",
            "The 2024 product is a current seasonal observation context and is not a historical substitute for the 2018 and 2020 administrative source vintages."
        ]
    }
    REPORT.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"selected_components": len(features), "unique_tiles": len(tiles), "source_month_tile_assets": len(tiles) * 12, "geometry_sha256": out_hash, "plan_sha256": hashlib.sha256(REPORT.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
