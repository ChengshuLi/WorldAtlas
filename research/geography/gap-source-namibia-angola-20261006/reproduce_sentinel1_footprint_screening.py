#!/usr/bin/env python3
"""Recompute Sentinel-1 STAC scene-footprint coverage from retained queries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "sources" / "sentinel-1-aws"
INPUT = ROOT / "inputs" / "original-components.geojson"
OUTPUT = SOURCE_DIR / "footprint-screening.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    components = json.loads(INPUT.read_text())["features"]
    geometries = [(feature["id"], shape(feature["geometry"])) for feature in components]
    report = json.loads(OUTPUT.read_text())
    if report["input"]["sha256"] != sha256(INPUT):
        raise SystemExit("original component input hash changed")
    for period in report["periods"]:
        response_path = SOURCE_DIR / period["response_file"]
        if sha256(response_path) != period["response_sha256"]:
            raise SystemExit(f"retained STAC response hash mismatch: {response_path.name}")
        items = json.loads(response_path.read_text())["features"]
        groups: dict[tuple[str, int | None, str | None], list[dict]] = {}
        for item in items:
            properties = item["properties"]
            key = (
                properties.get("datetime", "")[:10],
                properties.get("sat:relative_orbit"),
                properties.get("sat:orbit_state"),
            )
            groups.setdefault(key, []).append(item)

        group_report = []
        for key, group_items in sorted(groups.items()):
            union = unary_union([shape(item["geometry"]) for item in group_items])
            intersects = [component_id for component_id, geom in geometries if union.intersects(geom)]
            covered = [component_id for component_id, geom in geometries if union.covers(geom)]
            group_report.append(
                {
                    "acquisition_date": key[0],
                    "relative_orbit": key[1],
                    "orbit_state": key[2],
                    "item_ids": [item["id"] for item in group_items],
                    "item_count": len(group_items),
                    "candidate_ids_intersecting": intersects,
                    "intersecting_count": len(intersects),
                    "candidate_ids_fully_covered_by_footprint_union": covered,
                    "fully_covered_count": len(covered),
                }
            )
        all_scenes = unary_union([shape(item["geometry"]) for item in items]) if items else None
        aggregate = {
            "item_count": len(items),
            "intersecting_count": sum(all_scenes.intersects(geom) for _, geom in geometries) if all_scenes else 0,
            "fully_covered_count": sum(all_scenes.covers(geom) for _, geom in geometries) if all_scenes else 0,
            "candidate_ids_fully_covered": [
                component_id for component_id, geom in geometries if all_scenes and all_scenes.covers(geom)
            ],
            "individual_candidate_scene_counts": {
                component_id: sum(shape(item["geometry"]).intersects(geom) for item in items)
                for component_id, geom in geometries
            },
        }
        period["groups"] = group_report
        period["all_returned_scene_footprints_union"] = aggregate
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
