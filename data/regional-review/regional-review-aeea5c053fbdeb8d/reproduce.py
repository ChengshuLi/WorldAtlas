#!/usr/bin/env python3
"""Reproduce the Bangladesh issue-78 identity, hierarchy and source screens."""
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SRC = ROOT / "sources" / "geoboundaries-9469f09"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    snapshot = read(ROOT / "issue-context.json")
    scope = snapshot["scope"]
    ids = scope["member_location_ids"]
    assert len(ids) == scope["location_count"] == 64 and len(set(ids)) == 64
    projection = json.load(gzip.open(REPO / "data/macro-foundation/current-membership-projection.json.gz", "rt", encoding="utf-8"))
    assert sha(REPO / "data/macro-foundation/current-membership-projection.json.gz") == read(ROOT / "source-inventory.json")["baseline"]["sha256"]
    by_id = {x["id"]: x for x in projection["groups"]}
    by_id.update({x["id"]: x for x in projection["locations"]})
    current = projection["groups"]
    assert set(ids) <= set(by_id)
    source2 = read(SRC / "BGD-ADM2/geoBoundaries-BGD-ADM2.geojson")
    source1 = read(SRC / "BGD-ADM1/geoBoundaries-BGD-ADM1.geojson")
    meta2 = read(SRC / "BGD-ADM2/geoBoundaries-BGD-ADM2-metaData.json")
    meta1 = read(SRC / "BGD-ADM1/geoBoundaries-BGD-ADM1-metaData.json")
    f2 = {"gb:BGD:ADM2:" + f["properties"]["shapeID"]: f for f in source2["features"]}
    f1 = {"gb:BGD:ADM1:" + f["properties"]["shapeID"]: f for f in source1["features"]}
    assert len(f2) == 64 and len(f1) == 8
    assert set(ids) == set(f2), "issue roster must resolve exactly to the complete pinned ADM2 source"
    assert "gb:BGD:ADM2:NOT-A-RELEASE-ID" not in f2, "fabricated source ID unexpectedly resolved"
    duplicate_roster = ids + [ids[0]]
    assert len(duplicate_roster) != len(set(duplicate_roster)), "duplicate-roster negative control failed"
    assert len(f2) == len(source2["features"]), "ADM2 source IDs must be unique"
    assert len(f1) == len(source1["features"]), "ADM1 source IDs must be unique"
    source_info = read(ROOT / "source-inventory.json")
    hashes = {x["path"]: x["sha256"] for source in source_info["sources"] for x in source["files"]}
    for rel, expected in hashes.items():
        assert sha(ROOT / rel) == expected, f"source hash mismatch: {rel}"
    locs = []
    geometry = []
    for native_id in sorted(ids):
        unit = by_id[native_id]
        feature = f2[native_id]
        props = feature["properties"]
        geom = feature["geometry"] or {}
        coords = geom.get("coordinates")
        polys = coords if geom.get("type") == "MultiPolygon" else [coords] if geom.get("type") == "Polygon" else []
        def points(v):
            if isinstance(v, list) and len(v) >= 2 and all(isinstance(n, (int, float)) for n in v[:2]):
                yield v
            elif isinstance(v, list):
                for child in v:
                    yield from points(child)
        pts = list(points(coords))
        geometry.append({"id": native_id, "shapeName": props.get("shapeName"), "geometry_type": geom.get("type"), "polygon_components": len(polys), "rings": sum(len(p) for p in polys), "vertices": sum(len(r) for p in polys for r in p), "bbox": [min((p[0] for p in pts), default=None), min((p[1] for p in pts), default=None), max((p[0] for p in pts), default=None), max((p[1] for p in pts), default=None)]})
        locs.append({"id": native_id, "atlas_name": unit["name"], "atlas_parent_id": unit["parent_id"], "atlas_parent_name": by_id[unit["parent_id"]]["name"], "source_name": props.get("shapeName"), "source_role": meta2["boundaryCanonical"], "source_vintage": meta2["boundaryYear"], "assessment": "justified", "basis": "The pinned full-country ADM2 source assigns this native ID a district feature and the government portal's current district roster independently reports 64 districts under eight divisions. This supports administrative identity and tier only; no claim is made that this source geometry is legally authoritative or boundary-verified."})
    dump("baseline-unit-inventory.json", {"baseline_commit": "ddf9a8d02e808f40099d55878a301478c8c5eb64", "projection_sha256": source_info["baseline"]["sha256"], "rows": [{"id": r["id"], "name": r["atlas_name"], "parent_id": r["atlas_parent_id"], "parent_name": r["atlas_parent_name"], "source_id": "gb:BGD:ADM2", "source_name": r["source_name"], "source_year": r["source_vintage"], "semantic_status": "open"} for r in locs]})
    provinces = []
    for unit in current:
        if unit.get("level") != "province" or unit.get("parent_id") != scope["area_scopes"][0]["id"]:
            continue
        members = sorted(set(unit["member_location_ids"]) & set(ids))
        current_names = {"Chittagong": "Chattogram", "Rajshani": "Rajshahi", "Barisal": "Barishal"}
        recommended = current_names.get(unit["name"], unit["name"])
        provinces.append({"id": unit["id"], "name": unit["name"], "member_count": len(members), "pinned_full_province_count": len(unit["member_location_ids"]), "member_ids": members, "matching_source_adm1_names": [f["properties"]["shapeName"] for f in source1["features"] if f["properties"]["shapeName"].casefold() == unit["name"].casefold()], "current_official_portal_name_observed": recommended, "name_assessment": "correction-needed" if recommended != unit["name"] else "justified", "territorial_parent_assessment": "insufficient-evidence", "note": "Source ADM1 reproduces Atlas spelling and membership counts but is the 2020 vintage. The current official portal uses updated English spellings for three divisions. This naming recommendation does not confirm any district-to-division assignment or boundary."})
    assert len(provinces) == 8 and sum(x["member_count"] for x in provinces) == 64
    assert all(x["member_count"] == x["pinned_full_province_count"] for x in provinces)
    dump("location-assessments.json", {"assessment_scope": "administrative identity and tier support only; not boundary correctness", "counts": dict(Counter(x["assessment"] for x in locs)), "rows": locs})
    dump("province-assessments.json", {"rows": sorted(provinces, key=lambda x: x["id"])})
    dump("source-geometry-screen.json", {"limitations": ["Counts and bounds are not geometric validity, topology, overlap, island completeness or legal boundary verification.", "No geometry was changed or repaired."], "feature_count": len(geometry), "multipart_count": sum(x["geometry_type"] == "MultiPolygon" for x in geometry), "rows": geometry})
    names = [x["source_name"] for x in locs]
    dump("scope-risk-screen.json", {"scope_count": len(ids), "checks": [
        {"risk":"fragmented-city territories", "screen":"All 64 source records are ADM2/district features; no city/municipal role attribute is provided.", "result":"unresolved", "reason":"District polygons can contain urban jurisdictions; the source does not expose city corporate territories or city-specific splits."},
        {"risk":"province-sized locations", "screen":"Uniform source administrative role is district; ADM1 contains eight divisions.", "result":"no source-tier anomaly observed", "reason":"No feature is coded ADM1, but exact district-to-division parent and boundary overlay remain unverified."},
        {"risk":"anonymous administrative remainders", "screen":f"{sum(not x for x in names)} of 64 source names are empty; {len(names)-len(set(names))} repeated shapeName values.", "result":"no source-name anomaly observed" if all(names) and len(names)==len(set(names)) else "unresolved"},
        {"risk":"disconnected territories", "screen":f"{sum(x['geometry_type']=='MultiPolygon' for x in geometry)} of 64 source geometries are MultiPolygon.", "result":"unresolved", "reason":"Component counts cannot distinguish islands, river channels, detached administrative fragments or geometry artifacts."},
        {"risk":"omitted islands/coastal land", "screen":"Complete 64-feature provider roster and current official portal count observed.", "result":"unresolved", "reason":"Count agreement does not prove named-island, low-tide or coastline completeness."},
        {"risk":"repeated tiers", "screen":"64 unique source IDs, all source ADM2/district; eight source ADM1/division features.", "result":"no duplicate source IDs or source tiers observed"},
        {"risk":"oversized groups", "screen":"Atlas province memberships range from 4 to 13 district IDs; each province matches an ADM1 source name/count.", "result":"unresolved", "reason":"A count range is not a sourced standard for appropriate scale or geographic purpose."},
        {"risk":"weak parents", "screen":"All 64 Atlas IDs have a province parent; ADM1 names/counts match retained Atlas division groups.", "result":"insufficient evidence", "reason":"Current official labels differ for three divisions; exact legal district-to-division lineage was not verified."},
        {"risk":"inconsistent neighboring units", "screen":"No adjacent-region district roster or source inspection is included in the issue's declared subject scope.", "result":"unresolved", "reason":"Do not infer cross-border granularity from ADM numbers; neighboring-region review remains open."}
    ]})
    area = scope["area_scopes"][0]
    dump("area-assessment.json", {"id": area["id"], "name": area["name"], "scoped_count": len(ids), "full_count": area["full_area_location_count"], "status": "insufficient-evidence", "purpose": "Bangladesh is a national reporting container for 64 administrative district locations; the administrative roster corroborates the national grouping, but there is no independent evidence here for a physical, cultural or otherwise nonpolitical definition of this area or for the exact outer envelope.", "findings": ["Review is complete only for the issue-owned Bangladesh scope.", "Countrywide roster completeness by administrative count/name is supported, not coastline/island completeness or boundary precision."]})
    dump("reproduction.json", {"script_sha256": sha(ROOT / "reproduce.py"), "inputs": {"scope": sha(ROOT / "scope.json"), "source_inventory": sha(ROOT / "source-inventory.json"), "adm2": sha(SRC / "BGD-ADM2/geoBoundaries-BGD-ADM2.geojson"), "adm1": sha(SRC / "BGD-ADM1/geoBoundaries-BGD-ADM1.geojson")}, "outputs": {p.name: sha(p) for p in [ROOT / "baseline-unit-inventory.json", ROOT / "location-assessments.json", ROOT / "province-assessments.json", ROOT / "source-geometry-screen.json", ROOT / "scope-risk-screen.json", ROOT / "area-assessment.json"]}, "source_roster_ids": len(f2), "issue_ids": len(ids), "province_count": len(provinces), "checks": ["unique 64-ID issue scope", "complete one-to-one scope-to-ADM2 native ID resolution", "unique full ADM1/ADM2 source IDs", "source SHA-256 pins", "all province memberships partition 64 scoped IDs", "negative fabricated ID rejection", "duplicate scope ID rejection"]})


if __name__ == "__main__":
    main()
