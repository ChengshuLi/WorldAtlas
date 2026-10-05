#!/usr/bin/env python3
"""Reproduce issue 423's source identity and current-Slovenia point checks.

This intentionally does not claim polygon equivalence: source vertices and
representative points are diagnostics, not area-overlap or boundary approval.
"""
import collections
import gzip
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SOURCE = ROOT / "source"
GB = SOURCE / "geoboundaries-9469f09"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def point_on_segment(point, a, b, eps=2e-9):
    x, y = point
    dx, dy = b[0] - a[0], b[1] - a[1]
    cross = (x - a[0]) * dy - (y - a[1]) * dx
    if abs(cross) > eps * max(1.0, abs(dx) + abs(dy)):
        return False
    return min(a[0], b[0]) - eps <= x <= max(a[0], b[0]) + eps and min(a[1], b[1]) - eps <= y <= max(a[1], b[1]) + eps


def in_ring(point, ring):
    x, y = point
    inside = False
    for a, b in zip(ring, ring[1:]):
        if point_on_segment(point, a, b):
            return True
        if (a[1] > y) != (b[1] > y):
            xcross = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
            if x < xcross:
                inside = not inside
    return inside


def in_polygon(point, rings):
    return bool(rings) and in_ring(point, rings[0]) and not any(in_ring(point, hole) for hole in rings[1:])


def bounds(geometry):
    points = list(all_xy(geometry))
    return (min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)) if points else None


def in_geometry(point, geometry, extent=None):
    if not geometry:
        return False
    if extent and not (extent[0] - 1e-8 <= point[0] <= extent[2] + 1e-8 and extent[1] - 1e-8 <= point[1] <= extent[3] + 1e-8):
        return False
    kind, coordinates = geometry["type"], geometry["coordinates"]
    if kind == "Polygon":
        return in_polygon(point, coordinates)
    if kind == "MultiPolygon":
        return any(in_polygon(point, polygon) for polygon in coordinates)
    return False


def all_xy(geometry):
    if not geometry:
        return
    kind, coordinates = geometry["type"], geometry["coordinates"]
    if kind == "Polygon":
        for ring in coordinates:
            yield from ring
    elif kind == "MultiPolygon":
        for polygon in coordinates:
            for ring in polygon:
                yield from ring


def normalized_name(value):
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]", "", text)


def main():
    scope = read(ROOT / "scope.json")
    source_collections = {}
    source_meta = {}
    for country in ("SRB", "SVN"):
        for level in ("ADM1", "ADM2"):
            key = f"{country}-{level}"
            base = f"geoBoundaries-{key}"
            fc = read(GB / f"{base}.geojson")
            meta = read(GB / f"{base}-metaData.json")
            source_collections[key] = {f["properties"]["shapeID"]: f for f in fc["features"]}
            source_meta[key] = meta

    # Current, licensed, official GURS municipality source. The service result
    # is a complete 212-feature response with numberMatched=212.
    official_fc = read(SOURCE / "gurs-municipal-boundaries.geojson")
    official = official_fc["features"]
    official_bounds = {id(f): bounds(f.get("geometry")) for f in official}
    official_by_name = {f.get("properties", {}).get("NAZIV"): f for f in official}
    bilingual_aliases = {
        "Piran / Pirano": "Piran",
        "Izola / Isola": "Izola",
        "Ankaran / Ancarano": "Ankaran",
    }
    atlas_by_id = {}
    for p in (REPO / "data/geography/part-22.json",):
        for feature in read(p)["features"]:
            atlas_by_id[feature["id"]] = feature
    hierarchy = read(REPO / "data/hierarchy.json")
    hierarchy_by_id = {x["id"]: x for x in hierarchy}
    rows = []
    member_ids = scope["member_location_ids"]
    for location_id in member_ids:
        atlas = atlas_by_id.get(location_id)
        if atlas is None:
            raise SystemExit(f"missing atlas member: {location_id}")
        props = atlas["properties"]
        country, level, shape_id = location_id.split(":", 3)[1:]
        collection = f"{country}-{level}"
        source_feature = source_collections[collection].get(shape_id)
        if source_feature is None:
            raise SystemExit(f"source shapeID absent: {location_id}")
        meta = props.get("metadata", {})
        province = hierarchy_by_id.get(atlas.get("properties", {}).get("parent_id"), {})
        rep = meta.get("representative_point")
        matches = []
        mapping_method = None
        if country == "SVN" and rep:
            matches = [f for f in official if in_geometry(tuple(rep), f.get("geometry"), official_bounds[id(f)])]
        official_record = matches[0] if len(matches) == 1 else None
        if official_record:
            mapping_method = "source representative point in official current boundary"
        elif country == "SVN" and source_feature["properties"].get("shapeName") in bilingual_aliases:
            official_record = official_by_name.get(bilingual_aliases[source_feature["properties"]["shapeName"]])
            if official_record:
                mapping_method = "explicit bilingual source-name alias to official current name; representative point falls outside current municipal polygon"
        source_points = list(all_xy(source_feature.get("geometry")))
        inside_vertex_count = 0
        sampled_points = []
        if official_record:
            stride = max(1, (len(source_points) + 24) // 25)
            sampled_points = source_points[::stride][:25]
            inside_vertex_count = sum(in_geometry(tuple(point), official_record["geometry"], official_bounds[id(official_record)]) for point in sampled_points)
        role_ok = meta.get("source_role") == "Municipality" and meta.get("reference_year") == "2017"
        source_ok = source_feature.get("properties", {}).get("shapeID") == meta.get("original_id")
        atlas_name = atlas.get("properties", {}).get("name") or ""
        official_name = official_record.get("properties", {}).get("NAZIV") if official_record else None
        bilingual = source_feature["properties"].get("shapeName") in {
            "Koper / Capodistria", "Piran / Pirano", "Izola / Isola", "Ankaran / Ancarano"
        }
        name_mismatch = bool(official_name and not bilingual and normalized_name(atlas_name) != normalized_name(official_name))
        name_finding = "correction-needed" if name_mismatch else "supported-bilingual-name" if bilingual and official_name else "matches-current-official-name" if official_name and normalized_name(atlas_name) == normalized_name(official_name) else "unresolved"
        rows.append({
            "location_id": location_id,
            "name": atlas.get("properties", {}).get("name"),
            "reference_owner": props.get("reference_owner"),
            "parent_id": props.get("parent_id"),
            "province_name": province.get("name"),
            "province_source": province.get("metadata", {}).get("source"),
            "source_collection": collection,
            "source_shape_id": shape_id,
            "source_shape_name": source_feature["properties"].get("shapeName"),
            "source_identity_match": source_ok,
            "source_role": meta.get("source_role"),
            "source_year": meta.get("reference_year"),
            "source_license": meta.get("license"),
            "source_data_update_date": source_meta[collection].get("sourceDataUpdateDate"),
            "source_build_date": source_meta[collection].get("buildDate"),
            "source_vertex_count": len(source_points),
            "source_vertex_sample_count": len(sampled_points),
            "current_official_point_matches": len(matches),
            "current_official_mapping_method": mapping_method,
            "current_official_code": official_record.get("properties", {}).get("SIFRA") if official_record else None,
            "current_official_name": official_record.get("properties", {}).get("NAZIV") if official_record else None,
            "current_official_feature_date": official_record.get("properties", {}).get("DATUM_SYS") if official_record else None,
            "sampled_source_vertex_share_inside_matched_official_unit": (inside_vertex_count / len(sampled_points)) if official_record and sampled_points else None,
            "identity_role_finding": "supported" if source_ok and role_ok and official_record else "unresolved",
            "name_finding": name_finding,
            "proposed_official_name": official_name if name_mismatch else None,
            "boundary_finding": "insufficient-evidence",
            "overall_classification": "correction-needed" if name_mismatch else "insufficient-evidence",
            "classification_reason": ("The source representative point maps to a unique current GURS municipality, whose official name differs from the retained Atlas/source name after case, diacritic and punctuation normalization; preserve the stable ID and review a sourced name crosswalk. Polygon equivalence remains unverified." if name_mismatch else "The exact source identity and municipal role are supported. Slovenia's current official name maps by point or an explicit bilingual alias; Serbia's current per-unit official register was not retained. Neither point nor sampled-vertex diagnostics establish polygon equivalence."),
        })

    expected = set(member_ids)
    if len(member_ids) != scope["location_count"] or len(expected) != scope["location_count"]:
        raise SystemExit("scope count or uniqueness failure")
    if collections.Counter(r["source_collection"] for r in rows) != {"SRB-ADM2": 67, "SVN-ADM2": 211}:
        raise SystemExit("unexpected scoped country/source counts")
    if not all(row["source_identity_match"] for row in rows):
        raise SystemExit("not every exact scoped ID matches the pinned source feature")
    official_matches = [r for r in rows if r["source_collection"] == "SVN-ADM2" and r["current_official_point_matches"] == 1]
    scope_text = "\n".join(sorted(member_ids))
    scope_hash = hashlib.sha256(scope_text.encode("utf-8")).hexdigest()
    if scope_hash != scope["member_location_ids_sha256"]:
        raise SystemExit(f"member ID hash mismatch: expected {scope['member_location_ids_sha256']}, got {scope_hash}")
    expected_commit = "1451fb0788892ff9db6415e6ce6704bdd13d8f9a"
    pinned_hierarchy = subprocess.check_output(["git", "show", f"{expected_commit}:data/hierarchy.json"], cwd=REPO)
    pinned_hierarchy_hash = hashlib.sha256(pinned_hierarchy).hexdigest()
    current_hierarchy_hash = hashlib.sha256((REPO / "data/hierarchy.json").read_bytes()).hexdigest()
    pinned_hierarchy_data = json.loads(pinned_hierarchy)
    pinned_area = next(x for x in pinned_hierarchy_data if x.get("id") == scope["area_scopes"][0]["id"])
    current_area = hierarchy_by_id[scope["area_scopes"][0]["id"]]
    def inventoried_members(area):
        for evidence in area.get("metadata", {}).get("semantic_review", {}).get("evidence", []):
            match = re.search(r"Current member inventory: (\d+) locations", evidence.get("inspected_fact", ""))
            if match:
                return int(match.group(1))
        return None
    pinned_member_note = inventoried_members(pinned_area)
    current_member_note = inventoried_members(current_area)
    inventory_rows = {}
    inventory_raw = {}
    for ref in (expected_commit, "origin/main"):
        inventory_raw[ref] = subprocess.check_output(["git", "show", f"{ref}:data/macro-foundation/current-membership-inventory.json.gz"], cwd=REPO)
        inventory = json.loads(gzip.decompress(inventory_raw[ref]))
        inventory_rows[ref] = next(x for x in inventory if x.get("id") == scope["area_scopes"][0]["id"])["member_location_ids"]
    pinned_area_ids = set(inventory_rows[expected_commit])
    current_area_ids = set(inventory_rows["origin/main"])
    pinned_members_hash = hashlib.sha256("\n".join(sorted(pinned_area_ids)).encode("utf-8")).hexdigest()
    current_members_hash = hashlib.sha256("\n".join(sorted(current_area_ids)).encode("utf-8")).hexdigest()
    if len(pinned_area_ids) != 1169 or len(current_area_ids) != 1169 or not set(member_ids).issubset(pinned_area_ids):
        raise SystemExit("issue members do not match the pinned/current complete area membership inventory")
    report = {
        "version": 1,
        "issue": 423,
        "scope_path": "scope.json",
        "scope_location_count": len(rows),
        "scope_member_ids_sha256": scope["member_location_ids_sha256"],
        "computed_scope_member_ids_sha256": scope_hash,
        "pinned_release_hierarchy": {
            "commit": expected_commit,
            "expected_sha256": scope["release"]["hierarchy_sha256"],
            "actual_sha256": pinned_hierarchy_hash,
            "current_main_sha256": current_hierarchy_hash,
            "pinned_area_child_count": pinned_area.get("metadata", {}).get("child_count"),
            "pinned_inventory_location_count": len(pinned_area_ids),
            "pinned_inventory_file_sha256": hashlib.sha256(inventory_raw[expected_commit]).hexdigest(),
            "current_main_inventory_location_count": len(current_area_ids),
            "current_main_inventory_file_sha256": hashlib.sha256(inventory_raw["origin/main"]).hexdigest(),
            "pinned_and_current_area_member_ids_sha256": pinned_members_hash,
            "current_area_member_ids_sha256": current_members_hash,
            "issue_members_are_subset_of_pinned_area": set(member_ids).issubset(pinned_area_ids),
            "issue_area_scope_count": scope["area_scopes"][0]["full_area_location_count"],
            "hierarchy_metadata_inventory_note_v5": pinned_member_note,
            "hierarchy_metadata_inventory_note_current": current_member_note,
            "issue_count_matches_pinned_inventory": len(pinned_area_ids) == scope["area_scopes"][0]["full_area_location_count"],
            "issue_count_matches_current_inventory": len(current_area_ids) == scope["area_scopes"][0]["full_area_location_count"],
            "interpretation": "The issue's 1169 area count and all 278 exact packet IDs match both the pinned-v5 complete membership inventory and current origin/main; the sorted full-area membership hash is unchanged. A hierarchy semantic-review evidence sentence still reports 1162, so that embedded narrative is stale and must not be reused as a current measurement.",
        },
        "source_counts": {k: len(v) for k, v in source_collections.items()},
        "source_metadata": source_meta,
        "slovenia_official_current_features": len(official),
        "slovenia_official_number_matched": official_fc.get("numberMatched"),
        "slovenia_official_point_match_count": len(official_matches),
        "slovenia_official_unique_name_code_match_count": len({r["current_official_code"] for r in rows if r["source_collection"] == "SVN-ADM2" and r["current_official_code"]}),
        "slovenia_name_correction_candidate_count": sum(r["name_finding"] == "correction-needed" for r in rows),
        "slovenia_bilingual_name_count": sum(r["name_finding"] == "supported-bilingual-name" for r in rows),
        "slovenia_official_point_unmatched_or_ambiguous": [r["location_id"] for r in rows if r["source_collection"] == "SVN-ADM2" and r["current_official_point_matches"] != 1],
        "rows": rows,
        "limitations": [
            "A point match is a current identity crosswalk diagnostic, not polygon-boundary equivalence.",
            "The source boundary vintage is 2017; buildDate Dec 12 2023 is not the boundary reference year.",
            "Current Serbia administrative geometry was not retained from Serbia's official register in this packet; Serbian boundary correspondence remains unresolved.",
            "The packet owns only 211 of the 212 Slovenia municipality descendants identified in the current hierarchy; Hodoš is outside the pinned issue scope and is not reassigned here.",
        ],
    }
    out = ROOT / "unit-assessments.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("scope_location_count", "source_counts", "slovenia_official_current_features", "slovenia_official_point_match_count", "slovenia_official_point_unmatched_or_ambiguous")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
