#!/usr/bin/env python3
"""Compare the exact #451 source polygons with pinned Atlas geometries.

This measures source-to-Atlas representation lineage only. It is not a test of
legal boundary accuracy, topology, or completeness.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "2bab7a0fc8b84e1d792d57996abf9f08539d1876"
SOURCE_PATH = ROOT / "sources/geoboundaries-chn-adm2-2017.geojson"
SCOPE_PATH = ROOT / "scope.json"
OUTPUT_PATH = ROOT / "findings/boundary-lineage-comparison.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def baseline_blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"])


def feature_id(feature: dict) -> str | None:
    return feature.get("id") or (feature.get("properties") or {}).get("id")


def vertices_and_bbox(geometry: dict) -> tuple[int, int, list[float], int]:
    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geom_type == "Polygon":
        polygons = [coordinates]
    elif geom_type == "MultiPolygon":
        polygons = coordinates
    else:
        raise ValueError(f"Unsupported geometry type: {geom_type}")
    vertex_count = ring_count = 0
    west, south, east, north = math.inf, math.inf, -math.inf, -math.inf
    for polygon in polygons:
        for ring in polygon:
            ring_count += 1
            for point in ring:
                if len(point) < 2 or not all(math.isfinite(float(value)) for value in point[:2]):
                    raise ValueError("Invalid coordinate")
                lon, lat = float(point[0]), float(point[1])
                if abs(lon) > 180 or abs(lat) > 90:
                    raise ValueError("Coordinate outside longitude/latitude range")
                vertex_count += 1
                west, south = min(west, lon), min(south, lat)
                east, north = max(east, lon), max(north, lat)
    return len(polygons), ring_count, [west, south, east, north], vertex_count


def canonical_ring(ring: list[list[float]]) -> tuple[tuple[float, float], ...]:
    points = [(round(float(point[0]), 4), round(float(point[1]), 4)) for point in ring]
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    if not points:
        return ()
    candidates = []
    for oriented in (points, list(reversed(points))):
        start = min(range(len(oriented)), key=lambda i: oriented[i:]+oriented[:i])
        rotated = oriented[start:] + oriented[:start]
        candidates.append(tuple(rotated))
    return min(candidates)


def canonical_geometry(geometry: dict) -> tuple:
    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    polygons = [coordinates] if geom_type == "Polygon" else coordinates if geom_type == "MultiPolygon" else None
    if polygons is None:
        raise ValueError(f"Unsupported geometry type: {geom_type}")
    normalized = []
    for polygon in polygons:
        rings = [canonical_ring(ring) for ring in polygon]
        if not rings:
            raise ValueError("Polygon has no rings")
        normalized.append((rings[0], *sorted(rings[1:])))
    return tuple(sorted(normalized))


def main() -> None:
    scope = json.loads(SCOPE_PATH.read_text())
    ids = scope["member_location_ids"]
    if len(ids) != 40 or len(set(ids)) != 40:
        raise ValueError("Expected exactly 40 unique scoped IDs")
    source_raw = SOURCE_PATH.read_bytes()
    source = json.loads(source_raw)
    source_features = {f.get("properties", {}).get("shapeID"): f for f in source["features"]}
    if len(source_features) != len(source["features"]):
        raise ValueError("Duplicate source shapeID")
    index_raw = baseline_blob("data/world-index.json")
    index = json.loads(index_raw)
    hierarchy = json.loads(baseline_blob("data/hierarchy.json"))
    by_parent = {row["id"]: row for row in hierarchy}
    baseline_features: dict[str, tuple[dict, str, str]] = {}
    for relative in index["parts"]:
        path = f"data/{relative}"
        raw = baseline_blob(path)
        parsed = json.loads(raw)
        digest = sha256(raw)
        for feature in parsed["features"]:
            ident = feature_id(feature)
            if ident in ids:
                if ident in baseline_features:
                    raise ValueError(f"Duplicate Atlas ID {ident}")
                baseline_features[ident] = (feature, path, digest)
    if set(baseline_features) != set(ids):
        raise ValueError("Pinned Atlas source does not contain the exact scope")

    rows = []
    for ident in ids:
        source_id = ident.rsplit(":", 1)[-1]
        sf = source_features.get(source_id)
        if not sf or not sf.get("geometry"):
            raise ValueError(f"Missing retained source feature {source_id}")
        atlas_feature, atlas_path, atlas_hash = baseline_features[ident]
        atlas_geometry = atlas_feature.get("geometry")
        source_geometry = sf["geometry"]
        props = atlas_feature.get("properties") or {}
        parent_id = props.get("parent_id")
        if parent_id not in by_parent:
            raise ValueError(f"Missing baseline parent for {ident}")
        sparts, srings, sbbox, svertices = vertices_and_bbox(source_geometry)
        aparts, arings, abbox, avertices = vertices_and_bbox(atlas_geometry)
        same_4dp = canonical_geometry(source_geometry) == canonical_geometry(atlas_geometry)
        rows.append({
            "id": ident,
            "source_shape_id": source_id,
            "source_name": sf["properties"].get("shapeName"),
            "atlas_name": props.get("name"),
            "parent_id": parent_id,
            "parent_name": by_parent[parent_id].get("name"),
            "source_geometry_type": source_geometry["type"],
            "atlas_geometry_type": atlas_geometry["type"],
            "source_polygon_parts": sparts,
            "atlas_polygon_parts": aparts,
            "source_ring_count": srings,
            "atlas_ring_count": arings,
            "source_vertex_count": svertices,
            "atlas_vertex_count": avertices,
            "source_bbox_lon_lat": [round(x, 6) for x in sbbox],
            "atlas_bbox_lon_lat": [round(x, 6) for x in abbox],
            "same_geometry_after_coordinate_rounding_to_4dp_and_ring_normalization": same_4dp,
            "atlas_feature_file": atlas_path,
            "atlas_feature_file_sha256": atlas_hash,
            "interpretation": "representation comparison only; not official-boundary validation"
        })

    summary = {
        "version": 1,
        "issue": 451,
        "generated_at": "2026-10-05",
        "scope_count": len(rows),
        "unique_scope_count": len({row["id"] for row in rows}),
        "pinned_atlas_baseline_commit": BASELINE,
        "inputs": {
            "scope": {"path": str(SCOPE_PATH.relative_to(ROOT.parent.parent.parent)), "sha256": sha256(SCOPE_PATH.read_bytes())},
            "retained_source": {"path": str(SOURCE_PATH.relative_to(ROOT.parent.parent.parent)), "bytes": len(source_raw), "sha256": sha256(source_raw)},
            "world_index": {"path": "data/world-index.json", "sha256": sha256(index_raw)},
            "hierarchy": {"path": "data/hierarchy.json", "sha256": sha256(baseline_blob("data/hierarchy.json"))}
        },
        "results": {
            "unique_source_features": len(rows),
            "same_at_4dp": sum(row["same_geometry_after_coordinate_rounding_to_4dp_and_ring_normalization"] for row in rows),
            "different_at_4dp": sum(not row["same_geometry_after_coordinate_rounding_to_4dp_and_ring_normalization"] for row in rows),
            "source_parts_total": sum(row["source_polygon_parts"] for row in rows),
            "atlas_parts_total": sum(row["atlas_polygon_parts"] for row in rows),
            "source_rings_total": sum(row["source_ring_count"] for row in rows),
            "atlas_rings_total": sum(row["atlas_ring_count"] for row in rows),
            "source_vertices_total": sum(row["source_vertex_count"] for row in rows),
            "atlas_vertices_total": sum(row["atlas_vertex_count"] for row in rows),
            "per_location": rows
        },
        "limits": [
            "The 2017 geoBoundaries file declares County Level but has no parent IDs or official administrative codes; it cannot independently validate current prefecture assignments.",
            "A coordinate comparison with Atlas is lineage evidence only. Equality or difference does not establish legal boundary correctness, completeness, topology, island coverage, or the cause of simplification/editing.",
            "The apparent four-decimal comparison is a reproducible representation check and not a source precision or accuracy guarantee.",
            "Official current roster and code sources cited by the companion area/parent assessment have not been retained as source bytes; their entries include URLs and restoration instructions."
        ]
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "issue": 451,
        "scope_count": summary["scope_count"],
        "same_at_4dp": summary["results"]["same_at_4dp"],
        "different_at_4dp": summary["results"]["different_at_4dp"],
        "source_parts_total": summary["results"]["source_parts_total"],
        "atlas_parts_total": summary["results"]["atlas_parts_total"],
        "source_vertices_total": summary["results"]["source_vertices_total"],
        "atlas_vertices_total": summary["results"]["atlas_vertices_total"],
        "output": str(OUTPUT_PATH)
    }, indent=2))


if __name__ == "__main__":
    main()
