#!/usr/bin/env python3
"""Reproduce the bounded Inaccessible Island source and parent checks."""
from __future__ import annotations

import gzip
import hashlib
import json
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUBJECT = "atlas:island:geonames:3370905"
PROVINCE = "framework:province:tristan-da-cunha:33a276e2dcef"
AREA = "framework:area:tristan-da-cunha:9cc13f608018"
REGION = "framework:region:south-atlantic-islands:242a7633c849"
EXPECTED_HIERARCHY = "03d23534f87cdd0582bcb228780f00f65090bec2e8a760acbab528383f28549d"
OSM_GZIP = "data/macro-improvements/three-island-restoration/inaccessible-original-map.osm.gz"
DRY_WKB_GZIP = "data/macro-improvements/three-island-restoration/inaccessible-island-dry-land.wkb.gz"
EXPECTED_EXTRA_WAYS = {"29308363", "29308364", "478370353", "682698552", "888027621"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_polygon_wkb(data: bytes) -> list[list[tuple[float, float]]]:
    """Read the simple 2D Polygon WKB used by the retained candidate geometry."""
    endian = "<" if data[0] == 1 else ">"
    geometry_type = struct.unpack_from(endian + "I", data, 1)[0] & 0xFF
    if geometry_type != 3:
        raise AssertionError(f"expected Polygon WKB, got type {geometry_type}")
    offset = 5
    ring_count = struct.unpack_from(endian + "I", data, offset)[0]
    offset += 4
    rings = []
    for _ in range(ring_count):
        point_count = struct.unpack_from(endian + "I", data, offset)[0]
        offset += 4
        points = []
        for _ in range(point_count):
            points.append(struct.unpack_from(endian + "dd", data, offset))
            offset += 16
        rings.append(points)
    if offset != len(data):
        raise AssertionError("unexpected trailing bytes in WKB")
    return rings


def inside(point: tuple[float, float], ring: list[tuple[float, float]]) -> bool:
    x, y = point
    result = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            result = not result
    return result


def main() -> None:
    hierarchy_bytes = (ROOT / "data/hierarchy.json").read_bytes()
    assert sha(hierarchy_bytes) == EXPECTED_HIERARCHY
    hierarchy = json.loads(hierarchy_bytes)
    units = {item["id"]: item for item in hierarchy}
    assert units[PROVINCE]["parent_id"] == AREA
    assert units[AREA]["parent_id"] == REGION
    assert units[REGION]["parent_id"] == "framework:subcontinent:atlantic-islands:49ea8d869118"
    assert units[units[REGION]["parent_id"]]["parent_id"] == "framework:continent:africa:d14fc0b285b2"
    missing_profile_path = ROOT / "data/macro-foundation/new-location-source-profiles-v4.json.gz"
    assert not missing_profile_path.exists()

    indexed_paths = json.loads((ROOT / "data/world-index.json").read_text())["parts"]
    features = []
    for relpath in indexed_paths:
        feature_collection = json.loads((ROOT / "data" / relpath).read_text())
        features.extend(feature_collection.get("features", []))
    by_id = {feature.get("properties", {}).get("id"): feature for feature in features}
    target = by_id[SUBJECT]
    assert target["properties"]["parent_id"] == PROVINCE
    assert target["geometry"]["type"] == "Polygon"
    assert len(target["geometry"]["coordinates"]) == 2  # exterior plus Skua Pond hole
    province_children = sorted(
        feature["properties"]["id"] for feature in features
        if feature.get("properties", {}).get("parent_id") == PROVINCE
    )
    assert province_children == ["SHN-4865", SUBJECT]

    source = gzip.decompress((ROOT / OSM_GZIP).read_bytes())
    assert sha(source) == "9d2440339d46a04aa820c6a51f493dfe0cdb94e8ad49738b8c45a9d0c3f6be73"
    osm = ET.fromstring(source)
    nodes = {node.attrib["id"]: (float(node.attrib["lon"]), float(node.attrib["lat"])) for node in osm.findall("node")}
    ways = {way.attrib["id"]: way for way in osm.findall("way")}
    island = next(
        relation for relation in osm.findall("relation")
        if relation.attrib.get("id") == "9704046"
    )
    island_tags = {tag.attrib["k"]: tag.attrib["v"] for tag in island.findall("tag")}
    assert island_tags.get("name") == "Inaccessible Island"
    assert island_tags.get("place") == "island"
    members = island.findall("member")
    outer = [member.attrib["ref"] for member in members if member.attrib.get("role") == "outer"]
    assert len(outer) == 12 and all(member.attrib.get("role") == "outer" for member in members)
    assert all(ways[way_id] is not None for way_id in outer)

    rings = read_polygon_wkb(gzip.decompress((ROOT / DRY_WKB_GZIP).read_bytes()))
    assert len(rings) == 2  # dry-land exterior and Skua Pond hole
    outside = []
    for way_id in sorted(EXPECTED_EXTRA_WAYS):
        way = ways[way_id]
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
        refs = [node.attrib["ref"] for node in way.findall("nd")]
        assert tags.get("natural") == "coastline" and refs[0] == refs[-1]
        assert way_id not in outer
        points = [nodes[node_id] for node_id in refs[:-1]]
        mean = (sum(point[0] for point in points) / len(points), sum(point[1] for point in points) / len(points))
        assert not inside(mean, rings[0])
        outside.append({"way_id": way_id, "tags": tags})

    family_names = {"gough island", "nightingale islands", "alex island", "middle island", "stoltenhoff island"}
    current_names = {
        feature.get("properties", {}).get("name", "").strip().casefold()
        for feature in features
    }
    absent_family_names = sorted(family_names - current_names)
    assert {"gough island", "nightingale islands", "stoltenhoff island"}.issubset(absent_family_names)

    print(json.dumps({
        "status": "verified",
        "scope_location_count": 1,
        "hierarchy_sha256": sha(hierarchy_bytes),
        "issue_hint_profile_path_absent": "data/macro-foundation/new-location-source-profiles-v4.json.gz",
        "parent_chain": [SUBJECT, PROVINCE, AREA, REGION, units[REGION]["parent_id"], units[units[REGION]["parent_id"]]["parent_id"]],
        "province_current_children": province_children,
        "indexed_feature_parts": len(indexed_paths),
        "inaccessible_relation_outer_way_count": len(outer),
        "candidate_dry_land_rings": len(rings),
        "separate_outside_coastline_ways": outside,
        "named_family_members_absent_by_exact_current_name": absent_family_names,
        "limitations": ["Point-in-polygon uses each small ring's vertex mean and does not infer its area or location assignment.", "Source extract is bounded around Inaccessible; it cannot certify remote island-family completeness."],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
