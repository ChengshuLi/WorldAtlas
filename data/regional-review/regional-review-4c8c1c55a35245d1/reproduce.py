#!/usr/bin/env python3
"""Reproduce issue #461's pinned source identity, scope, and diagnostic screens.

Run from repository root after installing requirements.txt and with scripts/ on
PYTHONPATH. This script reads original baseline blobs with `git show`; it never
writes to baseline data. All generated reports remain in this issue-owned folder.
"""
from __future__ import annotations
import csv, hashlib, json, subprocess, sys, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASELINE = "bb7e3321dd65413c4029fc9fb85ccb1da1d0d43f"
PACKET = "regional-review-4c8c1c55a35245d1"

def raw_at(path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{BASELINE}:{path}"])

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def read_json_at(path: str):
    return json.loads(raw_at(path))

def write_json(path: str, value):
    from evidence.immutable import canonical_json
    (HERE / path).write_bytes(canonical_json(value))

def name_key(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value).casefold()
    return "".join(c for c in folded if c.isalnum())

def repair_mojibake(value: str) -> str:
    try:
        repaired = value.encode("latin-1").decode("utf-8")
        return repaired
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value

def feature_id(f):
    return f.get("id") or f.get("properties", {}).get("id")

def point_counts(coords):
    n = 0
    stack = [coords]
    while stack:
        x = stack.pop()
        if isinstance(x, list) and x and isinstance(x[0], (int, float)):
            n += 1
        elif isinstance(x, list):
            stack.extend(x)
    return n

def ring_count(coords):
    n = 0
    stack = [coords]
    while stack:
        x = stack.pop()
        if isinstance(x, list) and x and isinstance(x[0], list) and x[0] and isinstance(x[0][0], (int, float)):
            n += 1
        elif isinstance(x, list):
            stack.extend(x)
    return n

def geometry_area(g):
    from shapely.geometry import shape
    from evidence.geometry import land_area_m2
    return land_area_m2(shape(g) if isinstance(g, dict) else g)

def file_descriptor(path: str, data: bytes):
    return {"path": path, "bytes": len(data), "sha256": sha(data), "hash_kind": "file-bytes"}

def main():
    scope = json.loads((HERE / "issue-scope.json").read_text(encoding="utf-8"))
    wanted = set(scope["member_location_ids"])
    assert len(wanted) == 226 == scope["location_count"]
    assert scope["batch_id"] == "regional-review:" + "4c8c1c55a35245d1"

    index = read_json_at("data/world-index.json")
    index_paths = ["data/" + x for x in index["parts"] if x.startswith("geography/part-")]
    parents = {x["id"]: x for x in read_json_at("data/hierarchy.json")}
    atlas = {}
    subject_file = {}
    for path in index_paths:
        for f in read_json_at(path).get("features", []):
            ident = feature_id(f)
            if ident in wanted:
                assert ident not in atlas, f"duplicate Atlas feature {ident}"
                atlas[ident] = f
                subject_file[ident] = path
    assert set(atlas) == wanted, f"Atlas scope missing {len(wanted-set(atlas))} or has duplicate rows"

    raw_sources = {}
    source_meta = {}
    for code in ("CAF", "CMR"):
        rel = f"sources/geoBoundaries-{code}-ADM3.geojson"
        meta_rel = f"sources/geoboundaries-{code}-ADM3-metadata.json"
        collection = json.loads((HERE / rel).read_text(encoding="utf-8"))
        meta = json.loads((HERE / meta_rel).read_text(encoding="utf-8"))
        source_meta[code] = meta
        for f in collection["features"]:
            p = f["properties"]
            ident = f"gb:{code}:ADM3:{p['shapeID']}"
            if ident in wanted:
                assert ident not in raw_sources, f"duplicate raw source feature {ident}"
                raw_sources[ident] = f
    assert set(raw_sources) == wanted, f"source scope mismatch missing={len(wanted-set(raw_sources))} extra={len(set(raw_sources)-wanted)}"

    location_rows, province_rows, area_rows, geom_rows = [], [], [], []
    name_exact = repaired_count = geom_exact = official_csv_count = 0
    atlas_name_parent_map = defaultdict(set)
    for ident, feature in atlas.items():
        props = feature["properties"]
        atlas_name_parent_map[name_key(props["name"])].add(props["parent_id"])
    duplicate_name_parent_ids = {ident for ident, feature in atlas.items()
        if len(atlas_name_parent_map[name_key(feature["properties"]["name"])]) > 1}
    country_stats = defaultdict(Counter)
    province_members = defaultdict(list)
    area_members = defaultdict(list)
    cmr_crosswalk = {}
    crosswalk_path = HERE / "official-cmr-parent-crosswalk.csv"
    if crosswalk_path.exists():
        with crosswalk_path.open(encoding="utf-8", newline="") as fp:
            for r in csv.DictReader(fp):
                assert r["location_id"] not in cmr_crosswalk, "duplicate official crosswalk subject"
                cmr_crosswalk[r["location_id"]] = r
        cmr_ids = {i for i in wanted if i.startswith("gb:CMR:")}
        assert set(cmr_crosswalk) == cmr_ids, "official crosswalk must cover exact CMR subset"
        for ident, r in cmr_crosswalk.items():
            assert r["status"] in ("matched", "unmatched")
            if r["status"] == "matched":
                assert name_key(r["source_name_repaired"]) == name_key(r["official_subdivision"]), f"official name mismatch {ident}"
                assert name_key(r["atlas_parent_name"]) == name_key(r["official_division"]), f"official parent mismatch {ident}"
    for ident in sorted(wanted):
        af, sf = atlas[ident], raw_sources[ident]
        ap, sp = af["properties"], sf["properties"]
        country = ident.split(":")[1]
        parent = parents[ap["parent_id"]]
        area = parents[parent["parent_id"]]
        raw_name = sp["shapeName"]
        repaired = repair_mojibake(raw_name)
        exact = ap["name"] == raw_name
        decoded = ap["name"] == repaired
        name_exact += int(exact)
        repaired_count += int(decoded and not exact)
        gtype = sf["geometry"]["type"]
        agtype = af["geometry"]["type"]
        exact_geometry = sf["geometry"] == af["geometry"]
        geom_exact += int(exact_geometry)
        source_area = geometry_area(sf["geometry"])
        atlas_area = geometry_area(af["geometry"])
        from shapely.geometry import shape
        from evidence.geometry import canonical_land
        sg = canonical_land(shape(sf["geometry"]))
        ag = canonical_land(shape(af["geometry"]))
        from shapely import symmetric_difference, union_all
        from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
        diff = symmetric_difference(sg, ag)
        if diff.is_empty:
            symmetric_area = 0.0
        else:
            stack = [diff]; polygon_parts = []
            while stack:
                item = stack.pop()
                if item.geom_type == "Polygon": polygon_parts.append(item)
                elif item.geom_type in ("MultiPolygon", "GeometryCollection"): stack.extend(item.geoms)
            symmetric_area = geometry_area(union_all(polygon_parts)) if polygon_parts else 0.0
        rel_delta = (atlas_area - source_area) / source_area
        sym_ratio = symmetric_area / max(source_area, atlas_area)
        ckey = "verified_name_parent" if country == "CMR" and ident in cmr_crosswalk and cmr_crosswalk[ident]["status"] == "matched" else "unresolved"
        official_mismatch = country == "CMR" and ident in cmr_crosswalk and cmr_crosswalk[ident]["status"] == "unmatched"
        duplicate_name_parent = ident in duplicate_name_parent_ids
        classification = "correction_needed" if official_mismatch or duplicate_name_parent else "insufficient_evidence"
        if official_mismatch:
            reason = "Official 2021 name/parent crosswalk mismatch requires reconciliation"
        elif duplicate_name_parent:
            reason = "Same normalized Atlas feature name occurs under distinct parent IDs; reconcile identity and parent before treating either relationship as supported"
        else:
            reason = "Identity/source role evidence does not verify current legal boundary, completeness, or full parent geometry"
        row = {
            "id": ident,
            "country_code": country,
            "atlas_name": ap["name"],
            "source_name": raw_name,
            "source_name_after_reversible_utf8_repair": repaired,
            "name_match": "exact" if exact else "reversible-utf8-latin1-repair" if decoded else "mismatch",
            "atlas_parent_id": ap["parent_id"],
            "atlas_parent_name": parent["name"],
            "area_id": area["id"],
            "area_name": area["name"],
            "source_feature_id": sp["shapeID"],
            "source_layer": sp["shapeType"],
            "source_role_claim": source_meta[country].get("boundaryCanonical") or "blank/unknown in pinned metadata",
            "source_vintage": source_meta[country].get("boundaryYear"),
            "atlas_containing_file": subject_file[ident],
            "classification": classification,
            "official_cmr_crosswalk_status": ckey if country == "CMR" else "not-applicable",
            "name_parent_review_flags": ["duplicate-normalized-feature-name-under-distinct-parent-IDs; reconcile exact source identity and parent"] if duplicate_name_parent else [],
            "boundary_status": "unverified against current legal/official geometry",
            "geometry_review_flags": (["source-or-Atlas-multipart; inspect disconnected components against authoritative evidence"] if (gtype == "MultiPolygon" or agtype == "MultiPolygon") else []) + (["absolute area delta exceeds 5%; trace preparation and compare authoritative current boundary"] if abs(rel_delta) > 0.05 else []) + (["symmetric difference exceeds 10% of larger polygon; inspect lineage and authoritative evidence"] if sym_ratio > 0.10 else []),
            "reason": reason,
        }
        location_rows.append(row)
        province_members[ap["parent_id"]].append(ident)
        area_members[area["id"]].append(ident)
        country_stats[country]["features"] += 1
        country_stats[country]["source_names_exact"] += int(exact)
        country_stats[country]["source_names_encoding_repaired"] += int(decoded and not exact)
        country_stats[country]["geometries_exact"] += int(exact_geometry)
        geom_rows.append({
            "location_id": ident, "source_feature_id": sp["shapeID"],
            "source_geometry_type": gtype, "atlas_geometry_type": agtype,
            "source_components": len(sf["geometry"]["coordinates"]) if gtype == "MultiPolygon" else 1,
            "atlas_components": len(af["geometry"]["coordinates"]) if agtype == "MultiPolygon" else 1,
            "source_ring_count": ring_count(sf["geometry"]["coordinates"]),
            "atlas_ring_count": ring_count(af["geometry"]["coordinates"]),
            "source_coordinate_count": point_counts(sf["geometry"]["coordinates"]),
            "atlas_coordinate_count": point_counts(af["geometry"]["coordinates"]),
            "source_atlas_geometry_exact": exact_geometry,
            "source_land_area_m2": round(source_area, 3),
            "atlas_land_area_m2": round(atlas_area, 3),
            "atlas_signed_area_delta_pct": round(rel_delta * 100, 4),
            "symmetric_difference_area_m2": round(symmetric_area, 3),
            "symmetric_difference_pct_of_larger": round(sym_ratio * 100, 4),
            "interpretation": "diagnostic difference only; not an official boundary error test",
        })

    for p in scope["province_scopes"]:
        pid = p["id"]
        members = province_members.get(pid, [])
        correction_members = [x["id"] for x in location_rows if x["id"] in members and x["classification"] == "correction_needed"]
        province_rows.append({
            **p,
            "owned_member_count_reproduced": len(members),
            "member_ids": sorted(members),
            "classification": "correction_needed" if correction_members else "insufficient_evidence",
            "correction_needed_member_ids": sorted(correction_members),
            "reason": ("CAF member identity/parent reconciliation is required for the listed duplicate-name records; group purpose and current boundaries remain unverified." if correction_members and all(x.startswith("gb:CAF:") for x in correction_members) else "Source-to-2021 official name/parent reconciliation is required for listed Cameroon members; group purpose and current boundaries remain unverified." if correction_members and all(x.startswith("gb:CMR:") for x in correction_members) else "Listed member identity/parent reconciliation is required; group purpose and current boundaries remain unverified.") if correction_members else "Packet grouping is a reference parent label; source-to-current official parent boundaries and neighboring purpose need full crosswalk.",
        })
        assert len(members) <= p["full_province_locations"]
        if not p["partial"]: assert len(members) == p["full_province_locations"]
    for a in scope["area_scopes"]:
        members = area_members.get(a["id"], [])
        area_rows.append({
            **a,
            "owned_member_count_reproduced": len(members),
            "member_ids": sorted(members),
            "classification": "insufficient_evidence",
            "reason": "Area purpose, full national-source coverage, and combined cross-packet parent/neighbor fit remain integration decisions.",
            "cross_packet_reference": "#460 owns the other Cameroon subset; #462 owns another subset of the West-Central-Tropical-Africa regional inventory.",
        })
        assert len(members) == a["owned_member_location_count"]

    assert len(location_rows) == len(wanted) == 226
    assert len(province_rows) == len(scope["province_scopes"])
    assert len(area_rows) == len(scope["area_scopes"])

    # Generator controls: accept the exact recorded roster and reject a roster
    # that omits a real subject. This validates the mechanism, not geography.
    def validate_roster(actual, expected):
        if len(actual) != len(set(actual)) or set(actual) != set(expected):
            raise ValueError("subject roster is not an exact unique match")
    validate_roster(sorted(raw_sources), wanted)
    generator_positive = {"version": 1, "method_id": "packet-generator", "kind": "positive-control", "outcome": "passed",
        "subjects": len(location_rows), "provinces": len(province_rows), "areas": len(area_rows),
        "all_subjects_found": len(raw_sources) == len(wanted)}
    negative_rejected = False
    try:
        validate_roster(sorted(raw_sources)[1:], wanted)
    except ValueError:
        negative_rejected = True
    assert negative_rejected
    generator_negative = {"version": 1, "method_id": "packet-generator", "kind": "negative-control", "outcome": "passed",
        "control": "reject incomplete subject roster", "rejected": negative_rejected}
    write_json("packet-generator-positive-control.json", generator_positive)
    write_json("packet-generator-negative-control.json", generator_negative)
    write_json("location-assessments.json", {"assessment_status": "initial review; not regional certification", "locations": location_rows})
    write_json("province-assessments.json", {"provinces": province_rows})
    write_json("area-assessments.json", {"areas": area_rows})
    with (HERE / "source-geometry-screen.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(geom_rows[0]), lineterminator="\n")
        w.writeheader(); w.writerows(geom_rows)

    duplicate_official_codes = {}
    for row in cmr_crosswalk.values():
        code = row.get("official_2021_code", "")
        if code and " | " not in code:
            duplicate_official_codes.setdefault(code, []).append(row["location_id"])
    duplicate_official_codes = {k: sorted(v) for k,v in duplicate_official_codes.items() if len(v) > 1}
    duplicate_name_parent_conflicts = [{"normalized_name": name, "ids": sorted(ident for ident, f in atlas.items() if name_key(f["properties"]["name"]) == name), "parent_ids": sorted(parent_ids)} for name, parent_ids in sorted(atlas_name_parent_map.items()) if len(parent_ids) > 1]
    measured = {
        "status": "PASS: reproduced scope/source association and diagnostic metrics",
        "baseline_commit": BASELINE,
        "scope_subjects": len(wanted),
        "source_feature_count": len(raw_sources),
        "location_assessment_rows": len(location_rows),
        "province_assessment_rows": len(province_rows),
        "area_assessment_rows": len(area_rows),
        "source_name_exact": name_exact,
        "source_name_repaired": repaired_count,
        "source_atlas_geometry_exact": geom_exact,
        "countries": {k: dict(v) for k,v in country_stats.items()},
        "geometry_delta_over_5_percent": sum(abs(x["atlas_signed_area_delta_pct"]) > 5 for x in geom_rows),
        "multipart_source_features": sum(x["source_components"] > 1 for x in geom_rows),
        "multipart_atlas_features": sum(x["atlas_components"] > 1 for x in geom_rows),
        "source_atlas_component_count_changed": sum(x["source_components"] != x["atlas_components"] for x in geom_rows),
        "geometry_symdiff_over_10_percent": sum(x["symmetric_difference_pct_of_larger"] > 10 for x in geom_rows),
        "crosswalk_rows": len(cmr_crosswalk),
        "official_name_parent_matches": sum(x["status"] == "matched" for x in cmr_crosswalk.values()),
        "official_name_parent_unmatched": sum(x["status"] == "unmatched" for x in cmr_crosswalk.values()),
        "duplicate_codes_within_scoped_rows": duplicate_official_codes,
        "source_feature_totals": {code: source_meta[code].get("admUnitCount") for code in ("CAF", "CMR")},
        "duplicate_name_parent_conflicts_count": len(duplicate_name_parent_conflicts),
        "duplicate_name_parent_conflicts": duplicate_name_parent_conflicts,
        "limit": "These checks do not prove legal boundaries, official completeness, adjacency, or land coverage.",
    }
    write_json("source-screen-results.json", measured)

    # Positive control: identical geometry has no symmetric difference and a
    # finite positive WGS84 area. Negative control: observed Zina polygons are
    # materially different; this is a screen trigger, not proof which is legal.
    control_id = "gb:CAF:ADM3:52401652B11380714258081"
    control_geom = canonical_land(shape(raw_sources[control_id]["geometry"]))
    positive = symmetric_difference(control_geom, control_geom)
    positive_control = {"version": 1, "method_id": "geometry-screen", "kind": "positive-control", "outcome": "passed",
        "feature_id": control_id, "control": "identical normalized polygon pair has zero symmetric-difference area",
        "expected_symmetric_difference_m2": 0.0, "observed_symmetric_difference_m2": 0.0 if positive.is_empty else geometry_area(positive),
        "land_area_m2": round(geometry_area(control_geom), 3)}
    assert positive.is_empty and positive_control["land_area_m2"] > 0
    negative_id = "gb:CMR:ADM3:9386221B59068819347143"  # Zina
    negative_row = next(x for x in geom_rows if x["location_id"] == negative_id)
    negative_control = {"version": 1, "method_id": "geometry-screen", "kind": "negative-control", "outcome": "passed",
        "feature_id": negative_id, "control": "known observed source/Atlas pair exceeds the 10% diagnostic symmetric-difference threshold",
        "threshold_percent": 10.0, "observed_percent": negative_row["symmetric_difference_pct_of_larger"],
        "interpretation": "lineage review trigger only; not a legal boundary error test"}
    assert negative_control["observed_percent"] > negative_control["threshold_percent"]
    write_json("geometry-positive-control.json", positive_control)
    write_json("geometry-negative-control.json", negative_control)
    print(json.dumps(measured, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
