#!/usr/bin/env python3
"""Reproduce bounded source-shape and parent-size diagnostics for issue #423.

This is a screening aid only. Geometry type, names, and packet child counts do
not establish feature role, complete territory membership, or legal boundaries.
"""
import collections
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
OUTPUT = ROOT / "anomaly-screen.json"
INPUTS = [
    "scope.json",
    "unit-assessments.json",
    "province-assessments.json",
    "neighboring-context.json",
    "source/geoboundaries-9469f09/geoBoundaries-SRB-ADM2.geojson",
    "source/geoboundaries-9469f09/geoBoundaries-SVN-ADM2.geojson",
]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    scope = json.loads((ROOT / "scope.json").read_text(encoding="utf-8"))
    units = json.loads((ROOT / "unit-assessments.json").read_text(encoding="utf-8"))["rows"]
    parent_doc = json.loads((ROOT / "province-assessments.json").read_text(encoding="utf-8"))
    parents = parent_doc["assessments"]
    neighbor = json.loads((ROOT / "neighboring-context.json").read_text(encoding="utf-8"))
    member_ids = scope["member_location_ids"]
    if len(member_ids) != 278 or len(set(member_ids)) != 278:
        raise SystemExit("issue scope count/uniqueness changed")
    if hashlib.sha256("\n".join(sorted(member_ids)).encode()).hexdigest() != scope["member_location_ids_sha256"]:
        raise SystemExit("exact issue member hash changed")
    if len(units) != 278 or len(parents) != 17:
        raise SystemExit("unit/parent ledger count changed")

    wanted_shapes = {row["source_shape_id"] for row in units}
    feature_by_id = {}
    for source_path in INPUTS[-2:]:
        collection = json.loads((ROOT / source_path).read_text(encoding="utf-8"))
        for feature in collection["features"]:
            shape_id = feature.get("properties", {}).get("shapeID")
            if shape_id in wanted_shapes:
                if shape_id in feature_by_id:
                    raise SystemExit(f"duplicate source shape join: {shape_id}")
                feature_by_id[shape_id] = feature
    if set(feature_by_id) != wanted_shapes:
        raise SystemExit("scoped source shape join is incomplete")

    geometry_types = collections.Counter()
    multipart = []
    source_names = []
    for row in units:
        feature = feature_by_id[row["source_shape_id"]]
        geometry = feature.get("geometry") or {}
        kind = geometry.get("type")
        geometry_types[kind] += 1
        coordinates = geometry.get("coordinates") or []
        component_count = len(coordinates) if kind == "MultiPolygon" else (1 if kind == "Polygon" else 0)
        source_names.append((row["location_id"], row["source_shape_name"]))
        if kind == "MultiPolygon":
            multipart.append({"location_id": row["location_id"], "source_name": row["source_shape_name"], "parent_id": row["parent_id"], "polygon_components": component_count})
    if dict(geometry_types) != {"Polygon": 276, "MultiPolygon": 2}:
        raise SystemExit(f"unexpected scoped geometry-type screen: {geometry_types}")

    remainder_pattern = re.compile(r"other|remainder|unassigned|unknown|non[- ]?municip|remaining", re.I)
    lexical_hits = [{"location_id": subject, "source_name": name} for subject, name in source_names if remainder_pattern.search(name)]
    parent_rows = sorted(
        ({"parent_id": row["province_id"], "name": row["name"], "packet_member_count": row["packet_member_count"]} for row in parents),
        key=lambda row: row["parent_id"],
    )
    inputs = {path: {"sha256": digest((ROOT / path).read_bytes()), "hash_kind": "file-bytes"} for path in INPUTS}
    result = {
        "version": 1,
        "issue": 423,
        "baseline_commit": "c944e017796005726150abef19763db9ffd07154",
        "method": "Exact issue IDs joined by retained geoBoundaries shapeID; count GeoJSON Polygon/MultiPolygon components and scoped parent-member counts; apply a documented lexical screen to source names. No boundary overlay or legal-role inference.",
        "inputs": inputs,
        "scope": {"location_count": len(member_ids), "member_location_ids_sha256": scope["member_location_ids_sha256"], "source_rows_joined": len(feature_by_id), "parent_count": len(parent_rows)},
        "source_geometry_type_screen": {
            "counts": dict(sorted(geometry_types.items())),
            "multipolygon_features": sorted(multipart, key=lambda row: row["location_id"]),
            "finding": "Two Slovenia ADM2 source features have two Polygon components each. This flags disconnected geometry for source review; it does not show that either feature is an urban city, an island, complete, or legally equivalent to the current territory.",
        },
        "anonymous_remainder_name_screen": {
            "pattern": remainder_pattern.pattern,
            "matched_source_names": lexical_hits,
            "finding": "No scoped source names match this lexical screen. It does not establish completeness or exclude unnamed/unrepresented remainders outside this issue's 278-ID sample.",
        },
        "parent_size_screen": {
            "parents": parent_rows,
            "finding": "The two Slovenia cohesion-region parents have 147 and 61 scoped children; the 12 Serbian district parents have 3-8 scoped children each; three coastal municipality-duplicating parents are singletons. Counts are packet membership only and do not establish full parent rosters or comparable administrative tiers.",
        },
        "acceptance_checks": [
            {"topic": "fragmented city territories", "status": "insufficient-evidence", "finding": "Two multi-part source geometries are identified above, but Serbia's per-feature current role is unresolved and neither source category nor a full authoritative overlay establishes city-territory fragmentation.", "follow_up_issue": 1018},
            {"topic": "province-sized locations", "status": "insufficient-evidence", "finding": "ADM2 source level and Atlas Municipality labels do not establish relative territory size; no complete, comparable official extent or area assessment is retained.", "follow_up_issue": 1018},
            {"topic": "anonymous administrative remainders", "status": "lexically-screened-only", "finding": "No names match the recorded term screen; the sample and name screen cannot establish absence of unrepresented remainder units.", "follow_up_issue": 1017},
            {"topic": "disconnected territories", "status": "insufficient-evidence", "finding": "Two MultiPolygon source records (four components total) are identified; component topology, attribution, and current-boundary correspondence were not validated.", "follow_up_issue": 1018},
            {"topic": "omitted islands", "status": "insufficient-evidence", "finding": "The 278 rows are a partial Yugoslavia-area workload, not a complete national island inventory; omissions cannot be assessed from these sources. Complete-region integration in #415 must reconcile named-land and neighboring-packet coverage.", "follow_up_issue": 415},
            {"topic": "repeated or inconsistent tiers", "status": "correction-candidate", "finding": "The 17 parents mix Serbian administrative districts, Slovenia NUTS2 cohesion regions, and three same-municipality coastal singleton parents. Their tier compatibility and complete hierarchy require a source-backed decision.", "follow_up_issue": 1018},
            {"topic": "oversized groups", "status": "screened-incomplete", "finding": "Packet parent counts vary from 3-8 for scoped Serbian districts to 61/147 for Slovenia cohesion regions; different roles and partial membership prevent a correctness inference.", "follow_up_issue": 1018},
            {"topic": "weak parents", "status": "correction-candidate", "finding": "All 17 exact parents are individually assessed; the three one-child coastal records duplicate their municipality identities, while source completeness and geometry compatibility remain unresolved.", "follow_up_issue": 1018},
            {"topic": "neighboring granularity", "status": "handoff", "finding": "Hodoš is outside this issue's scope, belongs to #424, and remains an integration question for #415; Serbia/SVN parent tiers also differ in meaning.", "follow_up_issue": 415},
        ],
        "limitations": [
            "Geometry-type and lexical screens are not authoritative role, completeness, or boundary evidence.",
            "The Serbian 67 current territorial roles and official current boundaries remain unresolved.",
            "All 278 boundary-equivalence findings remain insufficient-evidence.",
            "The issue owns only a partial set of Yugoslavia area members; integration belongs to #415 and Hodoš data ownership remains with #424.",
        ],
    }
    encoded = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if "--write" in sys.argv[1:]:
        with OUTPUT.open("xb") as stream:
            stream.write(encoded)
        print(f"created {OUTPUT.relative_to(ROOT)} sha256={digest(encoded)}")
    else:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != encoded:
            raise SystemExit("anomaly-screen.json does not reproduce byte-for-byte; preserve it and investigate")
        print(f"reproduced {OUTPUT.relative_to(ROOT)} sha256={digest(encoded)}")


if __name__ == "__main__":
    main()
