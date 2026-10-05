#!/usr/bin/env python3
"""Reproduce the issue-462 source roster and point-parent evidence screens.

This script only reads the repository baseline and retained source snapshots.
It writes generated research records within this packet's owned directory.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import pathlib
import re
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[3]
PACKET = pathlib.Path(__file__).resolve().parent
SCOPE = json.loads((PACKET / "issue-scope-pinned.json").read_text())


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj: object) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def norm(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", ascii_value)


def in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def contains(geometry: dict, point: list[float]) -> bool:
    x, y = point
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    for polygon in polygons:
        if in_ring(x, y, polygon[0]) and not any(in_ring(x, y, ring) for ring in polygon[1:]):
            return True
    return False


def geometry_stats(geometry: dict) -> dict:
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    vertices = sum(len(ring) for polygon in polygons for ring in polygon)
    return {"geometry_type": geometry["type"], "polygon_components": len(polygons), "rings": sum(len(p) for p in polygons), "coordinate_pairs": vertices}


def load_features() -> dict:
    wanted = set(SCOPE["member_location_ids"])
    found = {}
    for part in sorted((ROOT / "data/geography").glob("part-*.json")):
        for feature in json.loads(part.read_text())["features"]:
            if feature["id"] in wanted:
                found[feature["id"]] = feature
    if set(found) != wanted:
        raise SystemExit(f"scope mismatch: missing {sorted(wanted - set(found))[:5]}")
    return found


def source_indexes() -> dict:
    sources = {}
    for path in (PACKET / "sources").glob("geoBoundaries-*.geojson"):
        source = json.loads(path.read_text())
        stem = path.stem
        key = stem[len("geoBoundaries-"):] if stem.startswith("geoBoundaries-") else stem
        sources[key] = {
            item["properties"]["shapeID"]: item for item in source["features"]
        }
    return sources


def source_key(feature: dict) -> tuple[str, str]:
    metadata = feature["properties"]["metadata"]
    if metadata["source_id"] == "gb:CAF:ADM3":
        return "CAF-ADM3", metadata["original_id"]
    if metadata["source_id"] == "gb:COD:ADM2":
        return "COD-ADM2", metadata["original_id"]
    if metadata["source_id"] == "gb:COG:ADM2":
        return "COG-ADM2", metadata["original_id"]
    if metadata["source_id"] == "gb:TCD:ADM2":
        return "TCD-ADM2", metadata["original_id"]
    members = metadata.get("source_member_ids", [])
    if len(members) != 1:
        raise SystemExit(f"unexpected derived source lineage for {feature['id']}: {members}")
    return "TCD-ADM2", members[0].rsplit(":", 1)[1]


def parent_dataset(source_code: str) -> str:
    return {"CAF": "CAF-ADM2", "COD": "COD-ADM1", "COG": "COG-ADM1", "TCD": "TCD-ADM1"}[source_code]


def area_for(feature_id: str) -> str:
    if feature_id.startswith("gb:CAF:"):
        return "Central African Republic"
    if feature_id.startswith("gb:COD:"):
        return "Democratic Republic of the Congo"
    if feature_id.startswith("gb:COG:"):
        return "Congo"
    return "Chad"


def main() -> None:
    features = load_features()
    index = source_indexes()
    members = [features[item] for item in SCOPE["member_location_ids"]]
    baseline_bytes = canonical({"type": "FeatureCollection", "features": members})
    (PACKET / "baseline-members.geojson.gz").write_bytes(gzip.compress(baseline_bytes, mtime=0))

    eco = {}
    query_path = PACKET / "sources/resolve-selected-query.json"
    if query_path.exists():
        query = json.loads(query_path.read_text())
        eco = {f"resolve:{feature['properties']['ECO_ID']}": feature["properties"] for feature in query["features"]}
    rows = []
    parent_mismatches = []
    for feature in members:
        props = feature["properties"]
        meta = props["metadata"]
        source_name, original_id = source_key(feature)
        source = index[source_name].get(original_id)
        if source is None:
            raise SystemExit(f"retained source does not contain {feature['id']} -> {source_name}/{original_id}")
        source_props = source["properties"]
        country = source_name[:3]
        candidate_dataset = parent_dataset(country)
        candidates = []
        point = meta.get("representative_point")
        if point:
            candidates = [s["properties"]["shapeName"] for s in index[candidate_dataset].values() if contains(s["geometry"], point)]
        parent_id = props.get("parent_id")
        # Framework province IDs encode the normalized display parent in component three.
        parent_slug = parent_id.split(":")[2] if parent_id and len(parent_id.split(":")) > 2 else None
        mismatch = len(candidates) == 1 and norm(candidates[0]) != norm(parent_slug or "")
        if mismatch:
            parent_mismatches.append({"location_id": feature["id"], "name": props["name"], "atlas_parent_slug": parent_slug, "pinned_source_parent_by_representative_point": candidates[0]})
        derived_physical = feature["id"].startswith("atlas:physical:")
        eco_properties = eco.get(meta["source_id"], {})
        classification = "correction-needed" if derived_physical else "insufficient-evidence"
        findings = ["Current atlas source_role says Departments, but the named source ID is a RESOLVE ecological feature; source role/selection rationale do not describe the retained lineage."] if derived_physical else ["The retained administrative source establishes a named source feature and its vintage/license metadata; this packet has not obtained a current authoritative national boundary/code crosswalk or independent completeness evidence for this subject."]
        if len(candidates) != 1:
            findings.append(f"Representative-point containment screen found {len(candidates)} candidate source parent polygons; this is not a complete polygon overlay.")
        elif mismatch:
            findings.append(f"Representative point falls in pinned source parent {candidates[0]!r}, while the current atlas parent slug is {parent_slug!r}; investigate exact boundary/vintage and parent identity before changing parent.")
        else:
            findings.append(f"Representative point falls in one pinned source parent candidate ({candidates[0]!r}) whose normalized name agrees with the atlas parent slug; this does not prove full polygon fit or current legal parentage.")
        if country == "COG":
            findings.append("Current feature metadata records topology_conflicts=5 and says shared display coverage was reconciled against Natural Earth reference borders before finer source geometry; original source and current published shape are not assumed identical.")
        rows.append({
            "location_id": feature["id"], "name": props["name"], "area_scope": area_for(feature["id"]),
            "atlas_parent_id": parent_id, "atlas_parent_slug": parent_slug,
            "classification": classification, "source_id": meta["source_id"],
            "source_role_recorded": meta.get("source_role"), "source_vintage_recorded": meta.get("reference_year"),
            "source_license_recorded": meta.get("license"), "source_feature_id": original_id,
            "source_feature_name": source_props.get("shapeName"), "source_level": source_props.get("shapeType"),
            "ecological_source_feature_name": eco_properties.get("ECO_NAME"), "ecological_source_license": eco_properties.get("LICENSE"),
            "source_feature_geometry": geometry_stats(source["geometry"]),
            "atlas_geometry": geometry_stats(feature["geometry"]),
            "source_parent_candidates_by_point": candidates,
            "source_parent_point_screen": "one-name-match" if len(candidates) == 1 and not mismatch else "one-name-disagreement" if mismatch else "not-unique",
            "findings": findings,
        })

    summary = {
        "issue_number": 462,
        "retrieved_utc": "2026-10-05",
        "baseline_main": "b7aab8b8d353eb3510cf7323da7bc2dcde10147b",
        "scope": {k: SCOPE[k] for k in ["batch_id", "region_id", "location_count", "member_location_ids_sha256", "release", "frozen_region_geometry_sha256", "frozen_region_member_ids_sha256", "owned_evidence_path"]},
        "counts": {"total": len(rows), "by_source_id": dict(sorted(__import__("collections").Counter(row["source_id"] for row in rows).items())), "correction_needed": sum(row["classification"] == "correction-needed" for row in rows), "insufficient_evidence": sum(row["classification"] == "insufficient-evidence" for row in rows), "justified": 0, "point_parent_name_disagreements": len(parent_mismatches)},
        "area_scope_coverage": [{**area, "issue_scope_is_partial": area["partial"], "observed_subjects": sum(row["area_scope"] == area["name"] for row in rows)} for area in SCOPE["area_scopes"]],
        "province_scope_coverage": [{**province, "observed_subjects": sum(row["atlas_parent_id"] == province["id"] for row in rows)} for province in SCOPE["province_scopes"]],
        "source_point_parent_disagreements": parent_mismatches,
        "source_parent_point_screen_limit": "Representative-point containment and normalized name comparison only. It does not prove whole-polygon parent containment, national legal status, source completeness, shared-boundary accuracy, or fit to current administrative geography.",
        "subjects": sorted(rows, key=lambda row: row["location_id"]),
    }
    (PACKET / "assessment.json").write_bytes(canonical(summary))


if __name__ == "__main__":
    main()
