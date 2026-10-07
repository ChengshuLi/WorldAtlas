#!/usr/bin/env python3
"""Compare all 70 pinned components against both complete consumed products."""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform
from shapely.ops import unary_union
from shapely.strtree import STRtree


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "research/geography/portugal-spain-gap-source-families-20261007"
INDEX_PATH = PACKAGE / "inputs/complete-input-index.json"
GEOMETRY_PATH = PACKAGE / "inputs/selected-70-component-geometries.geojson"
OUTPUT = PACKAGE / "outputs/administrative-source-overlays.json"
AREA_CRS = "EPSG:6933"


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def covers_component(source, component, source_crs: str, component_crs: str) -> bool:
    if source_crs != component_crs:
        raise ValueError(f"coverage predicate CRS mismatch: {source_crs} != {component_crs}")
    return source.covers(component)


def main() -> None:
    index = json.loads(INDEX_PATH.read_text())
    components = json.loads(GEOMETRY_PATH.read_text())["features"]
    component_roster = set(index["scope"]["component_ids"])
    if len(components) != 70 or {f["id"] for f in components} != component_roster:
        raise SystemExit("selected geometry file does not match exact 70-component scope")
    component_geoms = {f["id"]: shape(f["geometry"]) for f in components}
    if not all(g.is_valid for g in component_geoms.values()):
        raise SystemExit("invalid original component geometry; no automatic repair was applied")
    project = Transformer.from_crs("EPSG:4326", AREA_CRS, always_xy=True).transform
    component_projected = {fid: transform(project, geom) for fid, geom in component_geoms.items()}
    products = []
    all_pairs = []
    per_component = {fid: {"component_id": fid, "product_results": []} for fid in component_geoms}
    for product in index["selected_source_products"]:
        parts = []
        for part_row in product["parts"]:
            descriptor = next(row["descriptor"] for row in index["source_product_payload_descriptors"] if row["source_key"] == product["key"] and row["part"]["ordinal"] == part_row["ordinal"])
            compressed = subprocess.check_output(["git", "show", f"{descriptor['commit']}:{descriptor['path']}"], cwd=ROOT)
            if len(compressed) != descriptor["bytes"] or sha(compressed) != descriptor["sha256"]:
                raise SystemExit(f"pinned source shard mismatch: {descriptor['path']}")
            original = gzip.decompress(compressed)
            if len(original) != part_row["uncompressed_bytes"] or sha(original) != part_row["uncompressed_sha256"]:
                raise SystemExit(f"pinned decoded source shard mismatch: {descriptor['path']}")
            parts.append(original)
        raw = b"".join(parts)
        if len(raw) != product["original_bytes"] or sha(raw) != product["original_sha256"]:
            raise SystemExit(f"complete original source product mismatch: {product['key']}")
        collection = json.loads(raw)
        if len(collection["features"]) != product["feature_count"]:
            raise SystemExit(f"source feature count mismatch: {product['key']}")
        features = []
        geoms = []
        projected_geoms = []
        for pos, feature in enumerate(collection["features"]):
            geom = shape(feature["geometry"])
            if geom.is_empty or not geom.is_valid:
                raise SystemExit(f"invalid source feature geometry in {product['key']} position {pos}; no automatic repair was applied")
            properties = feature["properties"]
            source_id = f"{product['key']}:{properties['shapeID']}"
            features.append({"source_id": source_id, "position": pos, "properties": properties})
            geoms.append(geom)
            projected_geoms.append(transform(project, geom))
        tree = STRtree(projected_geoms)
        control_source = projected_geoms[0]
        inside = control_source.representative_point()
        control_minx, control_miny, control_maxx, control_maxy = control_source.bounds
        outside = shape({"type": "Point", "coordinates": [control_maxx + max(1_000_000.0, control_maxx - control_minx + 1.0), control_maxy + max(1_000_000.0, control_maxy - control_miny + 1.0)]})
        coverage_controls = {
            "crs": AREA_CRS,
            "production_predicate": "covers_component(source_projected, component_projected, source_crs, component_crs)",
            "positive_control": {"source_feature_id": features[0]["source_id"], "component_geometry": "representative point of same projected source feature", "covered": covers_component(control_source, inside, AREA_CRS, AREA_CRS)},
            "negative_control": {"source_feature_id": features[0]["source_id"], "component_geometry": "point beyond projected source bounds", "covered": covers_component(control_source, outside, AREA_CRS, AREA_CRS)},
        }
        if not coverage_controls["positive_control"]["covered"] or coverage_controls["negative_control"]["covered"]:
            raise SystemExit(f"administrative source coverage predicate controls failed: {product['key']}")
        candidates = 0
        component_intersect_count = 0
        component_positive_area_count = 0
        component_union_cover_count = 0
        for fid, component in component_geoms.items():
            component_proj = component_projected[fid]
            indices = tree.query(component_proj, predicate="intersects")
            rows = []
            component_area = component_proj.area
            candidate_geometries = [projected_geoms[int(idx)] for idx in indices]
            union = unary_union(candidate_geometries) if candidate_geometries else None
            covered_area = component_proj.intersection(union).area if union is not None else 0.0
            union_fraction = covered_area / component_area if component_area else None
            fully_covered_by_union = union_fraction is not None and union_fraction >= 1.0 - 1e-9
            component_union_cover_count += fully_covered_by_union
            for idx in indices:
                idx = int(idx)
                source = projected_geoms[idx]
                intersection = component_proj.intersection(source)
                projected_area = intersection.area
                source_covers = covers_component(source, component_proj, AREA_CRS, AREA_CRS)
                row = {
                    "component_id": fid,
                    "source_product": product["key"],
                    "source_feature_id": features[idx]["source_id"],
                    "source_feature_position": features[idx]["position"],
                    "source_name": features[idx]["properties"].get("shapeName"),
                    "source_type": features[idx]["properties"].get("shapeType"),
                    "intersects": True,
                    "covers_component": source_covers,
                    "positive_area_overlap": projected_area > 0,
                    "intersection_area_m2_equal_area": projected_area,
                    "component_area_m2_equal_area": component_area,
                    "component_area_fraction": projected_area / component_area if component_area else None,
                }
                rows.append(row)
                all_pairs.append(row)
            candidates += len(rows)
            component_intersect_count += bool(rows)
            component_positive_area_count += any(r["positive_area_overlap"] for r in rows)
            per_component[fid]["product_results"].append({
                "source_product": product["key"],
                "recorded_vintage": product["source_represented_year_claim"],
                "recorded_license": product["recorded_license"],
                "source_feature_count": product["feature_count"],
                "intersecting_source_feature_count": len(rows),
                "positive_area_source_feature_count": sum(r["positive_area_overlap"] for r in rows),
                "covering_source_feature_count": sum(r["covers_component"] for r in rows),
                "union_coverage_area_m2_equal_area": covered_area,
                "union_coverage_fraction": union_fraction,
                "uncovered_area_fraction": (1.0 - union_fraction) if union_fraction is not None else None,
                "fully_covered_by_source_product_union": fully_covered_by_union,
                "intersections": rows,
            })
        positive_control = next((row for row in all_pairs if row["source_product"] == product["key"] and row["positive_area_overlap"]), None)
        if positive_control is None:
            raise SystemExit(f"no real positive-area control found for {product['key']}")
        negative_control = None
        for fid in sorted(component_geoms):
            component_proj = component_projected[fid]
            for i, source_proj in enumerate(projected_geoms):
                if not component_proj.intersects(source_proj):
                    negative_control = {
                        "component_id": fid,
                        "source_product": product["key"],
                        "source_feature_id": features[i]["source_id"],
                        "source_feature_position": features[i]["position"],
                        "intersects": False,
                        "distance_m_equal_area": component_proj.distance(source_proj),
                    }
                    break
            if negative_control:
                break
        if negative_control is None or negative_control["distance_m_equal_area"] <= 0:
            raise SystemExit(f"no real non-intersection control found for {product['key']}")
        products.append({
            "source_product": product["key"],
            "recorded_source_url": product["recorded_consumed_url"],
            "recorded_vintage": product["source_represented_year_claim"],
            "recorded_license": product["recorded_license"],
            "feature_count": product["feature_count"],
            "original_bytes": product["original_bytes"],
            "original_sha256": product["original_sha256"],
            "full_original_reassembled_and_hash_verified": True,
            "component_count_intersecting_any_feature": component_intersect_count,
            "component_count_with_positive_area_overlap": component_positive_area_count,
            "component_count_covered_by_union": component_union_cover_count,
            "intersecting_pair_count": candidates,
            "controls": {
                "positive_control": {k: positive_control[k] for k in ("component_id", "source_feature_id", "positive_area_overlap", "intersection_area_m2_equal_area")},
                "negative_control": negative_control,
                "coverage_predicate": coverage_controls,
            },
        })
    result = {
        "schema": "worldatlas-full-admin-source-overlay-v1",
        "component_roster_sha256": index["scope"]["component_ids_sha256"],
        "selected_geometry_sha256": hashlib.sha256(GEOMETRY_PATH.read_bytes()).hexdigest(),
        "area_method": "Transform original WGS84 geometry intersections to EPSG:6933 equal-area; report area only as a geometric diagnostic.",
        "source_products": products,
        "component_count": len(component_geoms),
        "pair_count": len(all_pairs),
        "components": [per_component[fid] for fid in sorted(per_component)],
        "limits": [
            "Both complete simplified administrative products were read from the exact pinned baseline source corpus and verified against original uncompressed byte hashes.",
            "Intersections and area fractions compare source geometry with diagnostic physical-component geometry; they do not establish ownership, rightful province, historical effective dates, or an approved boundary.",
            "The source products are simplified polygons. They are the inputs Atlas recorded as consumed, not a substitute for their unsimplified upstream files.",
            "No invalid geometry was repaired; the script stops if any source/component geometry is invalid.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"source_products": len(products), "components": len(component_geoms), "pairs": len(all_pairs), "sha256": sha(OUTPUT.read_bytes())}))


if __name__ == "__main__":
    main()
