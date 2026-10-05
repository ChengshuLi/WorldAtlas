#!/usr/bin/env python3
"""Reproduce the issue-463 roster/source crosswalk and scoped review states."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "sources" / "geoboundaries-9469f09"
SOURCES = {
    "COD": {
        "path": SOURCE_DIR / "COD-ADM2.geojson",
        "metadata_path": SOURCE_DIR / "COD-geoBoundaries-api-current-metadata.json",
        "source_id": "gb:COD:ADM2",
        "license": "Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)",
        "role_claim": "territory, city",
        "vintage_claim": "2019",
        "scope_count": 169,
    },
    "GAB": {
        "path": SOURCE_DIR / "GAB-ADM2.geojson",
        "metadata_path": SOURCE_DIR / "GAB-geoBoundaries-api-current-metadata.json",
        "source_id": "gb:GAB:ADM2",
        "license": "Creative Commons Attribution 3.0 License",
        "role_claim": "Department",
        "vintage_claim": "2018",
        "scope_count": 30,
    },
    "GNQ": {
        "path": SOURCE_DIR / "GNQ-ADM2.geojson",
        "metadata_path": SOURCE_DIR / "GNQ-geoBoundaries-api-current-metadata.json",
        "source_id": "gb:GNQ:ADM2",
        "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "role_claim": "District",
        "vintage_claim": "2013",
        "scope_count": 28,
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    scope = read(ROOT / "scope.json")
    baseline = read(ROOT / "baseline-unit-inventory.json")
    source_inventory = read(ROOT / "source-inventory.json")
    scope_ids = scope["member_location_ids"]
    scope_set = set(scope_ids)
    baseline_by_id = {row["id"]: row for row in baseline["rows"]}
    assert len(scope_ids) == scope["location_count"] == 227
    assert len(scope_set) == len(scope_ids), "duplicate issue members"
    assert scope_set == set(baseline_by_id), "baseline context roster differs from issue pin"

    features_by_country = {}
    for country, descriptor in SOURCES.items():
        doc = read(descriptor["path"])
        features = doc["features"]
        ids = [f"gb:{country}:ADM2:{feature['properties']['shapeID']}" for feature in features]
        assert len(ids) == len(set(ids)), f"duplicate native IDs in {country} source"
        features_by_country[country] = {
            f"gb:{country}:ADM2:{feature['properties']['shapeID']}": feature
            for feature in features
        }

    # Independently verify retained source bytes against the source inventory.
    source_rows = {entry["source_id"].split(":")[1]: entry for entry in source_inventory["geoBoundaries_sources"]}
    for country, descriptor in SOURCES.items():
        entry = source_rows[country]
        assert sha256(descriptor["path"]) == entry["geometry_sha256"]
        assert len(features_by_country[country]) == entry["feature_count"]
        assert sha256(descriptor["metadata_path"]) == entry["metadata_sha256"]
        citation_path = SOURCE_DIR / f"{country}-CITATION-AND-USE.txt"
        assert sha256(citation_path) == entry["citation_and_use_sha256"]
        metadata = read(descriptor["metadata_path"])
        assert metadata.get("boundaryID") == entry["boundary_id"]
        assert metadata.get("boundaryCanonical") == entry["canonical_role"]
        assert str(metadata.get("boundaryYearRepresented")) == entry["boundary_year_represented"]
        assert metadata.get("boundaryLicense") == entry["boundary_license"]

    # Positive control: every scoped native ID resolves to exactly one feature.
    # Negative controls: a fabricated native ID and a duplicate issue member are rejected.
    source_owner = {native_id: country for country, features in features_by_country.items() for native_id in features}
    missing = sorted(scope_set - set(source_owner))
    assert not missing, f"scoped IDs absent from retained sources: {missing[:5]}"
    fabricated = "gb:GNQ:ADM2:NOT-A-RELEASE-ID"
    assert fabricated not in source_owner, "negative control unexpectedly resolved"
    duplicate_roster = scope_ids + [scope_ids[0]]
    duplicate_rejected = len(duplicate_roster) != len(set(duplicate_roster))
    assert duplicate_rejected, "duplicate-member negative control failed"

    official_parent_mismatch = {
        "gb:GNQ:ADM2:11065452B42024070816207": {
            "status": "correction-needed",
            "finding_id": "gnq-elobey-chico-parent-role",
        },
        "gb:GAB:ADM2:22940354B92057182831829": {
            "status": "correction-needed",
            "finding_id": "gab-doutsita-parent-tier",
        }
    }
    assessments = []
    geometry_entries = []
    for native_id in sorted(scope_set):
        country = source_owner[native_id]
        feature = features_by_country[country][native_id]
        source_name = feature["properties"].get("shapeName")
        row = baseline_by_id[native_id]
        geom = feature.get("geometry") or {}
        geometry_type = geom.get("type")
        coords = geom.get("coordinates")
        components = coords if geometry_type == "MultiPolygon" else [coords] if geometry_type == "Polygon" else []
        rings = sum(len(poly) for poly in components)
        vertices = sum(len(ring) for poly in components for ring in poly)
        def points(value):
            if isinstance(value, list) and len(value) >= 2 and all(isinstance(v, (int, float)) for v in value[:2]):
                yield value
            elif isinstance(value, list):
                for child in value:
                    yield from points(child)
        points_list = list(points(coords))
        bbox = [
            min((point[0] for point in points_list), default=None),
            min((point[1] for point in points_list), default=None),
            max((point[0] for point in points_list), default=None),
            max((point[1] for point in points_list), default=None),
        ]
        geometry_entries.append({
            "id": native_id,
            "shapeName": feature.get("properties", {}).get("shapeName"),
            "shapeType": feature.get("properties", {}).get("shapeType"),
            "shapeGroup": feature.get("properties", {}).get("shapeGroup"),
            "shapeISO": feature.get("properties", {}).get("shapeISO"),
            "geometry": {"geometry_type": geometry_type, "component_count": len(components), "ring_count": rings,
                         "coordinate_vertex_count": vertices, "bbox_lonlat": bbox, "empty": not points_list},
        })
        decision = official_parent_mismatch.get(native_id, {"status": "insufficient-evidence"})
        assessments.append({
            "id": native_id,
            "source_name": source_name,
            "atlas_name_at_baseline": row["name"],
            "atlas_parent_id_at_baseline": row["parent_id"],
            "atlas_parent_name_at_baseline": row.get("parent_name"),
            "source_id": SOURCES[country]["source_id"],
            "source_role_issue_claim": SOURCES[country]["role_claim"],
            "source_role_provider_metadata": read(SOURCES[country]["metadata_path"]).get("boundaryCanonical"),
            "source_vintage_issue_claim": SOURCES[country]["vintage_claim"],
            "source_vintage_provider_metadata": read(SOURCES[country]["metadata_path"]).get("boundaryYearRepresented"),
            "status": decision["status"],
            "finding_id": decision.get("finding_id"),
            "reason": (
                "The native ID and source feature resolve, but the legal identity/role, complete current roster, "
                "exact parent correspondence and legally authoritative boundary are not established for this "
                "unit. The source ADM2 label and provider metadata are not legal classification evidence."
                if decision["status"] == "insufficient-evidence" else
                "The pinned source calls this Doutsita and the issue assigns it to a standalone Atlas "
                "province wrapper. Gabon's Ministry of Interior 2018 page lists the official division "
                "Doutsila among Nyanga's six departments (while also reporting 48 departments total). "
                "This is a sourced department/parent mismatch and a spelling crosswalk proposal; the "
                "exact legal boundary and whether the spelling is an alias or source error remain unresolved."
                if decision.get("finding_id") == "gab-doutsita-parent-tier" else
                "The pinned 2013 source feature identifies Elobey Chico; its provider metadata gives the "
                "canonical role as Unknown, while the migrated issue describes its role as District. The "
                "Atlas parent scope groups it as a standalone province; "
                "the Equatorial Guinea territorial account names Elobey Chico as an island within Cogo "
                "District (Litoral Province), not as a province. This is a parent-role correction finding "
                "only; no boundary is approved and current delimitation evidence remains incomplete."
            ),
        })

    country_scope_counts = Counter(source_owner[native_id] for native_id in sorted(scope_set))
    country_source_counts = {country: len(features) for country, features in features_by_country.items()}
    assert dict(country_scope_counts) == {c: d["scope_count"] for c, d in SOURCES.items()}
    assert country_source_counts == {"COD": 189, "GAB": 49, "GNQ": 28}
    assert len(assessments) == 227
    geometry_summary = {}
    for country in SOURCES:
        entries = [entry for entry in geometry_entries if f":{country}:" in entry["id"]]
        geometry_summary[country] = {
            "scoped_features": len(entries),
            "geometry_types": dict(Counter(entry["geometry"]["geometry_type"] for entry in entries)),
            "multipart_ids": [entry["id"] for entry in entries if entry["geometry"]["component_count"] > 1],
            "empty_geometries": [entry["id"] for entry in entries if entry["geometry"]["empty"]],
            "shapeType_values": dict(Counter(str(entry["shapeType"]) for entry in entries)),
            "unnamed_features": [entry["id"] for entry in entries if not entry["shapeName"]],
        }
    geometry_outputs = {
        "version": 1,
        "issue": 463,
        "source_release": "geoBoundaries commit 9469f09",
        "scope_sha256": sha256(ROOT / "scope.json"),
        "summary": geometry_summary,
        "per_location_screen": geometry_entries,
        "method": "Directly count GeoJSON Polygon/MultiPolygon coordinate components/rings/vertices and compute lon/lat coordinate bounds for each scoped source feature. This does not test geometry validity, topology, disputed boundaries, or legal territory; polygon components can represent islands/coastline as well as disconnected administrative territory.",
    }
    (ROOT / "source-geometry-screen.json").write_text(json.dumps(geometry_outputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    hierarchy_path = ROOT.parents[2] / "data" / "hierarchy.json"
    hierarchy = read(hierarchy_path)
    hierarchy_by_id = {unit["id"]: unit for unit in hierarchy}
    assert sha256(hierarchy_path) == baseline["reference_files"]["hierarchy.json"]
    province_groups = {}
    for row in baseline["rows"]:
        province_groups.setdefault(row["parent_id"], []).append(row)
    province_assessments = []
    for province in scope["province_scopes"]:
        members = province_groups.get(province["id"], [])
        assert len(members) == province["full_province_locations"]
        statuses = Counter(next(item["status"] for item in assessments if item["id"] == row["id"]) for row in members)
        province_assessments.append({
            "province_id": province["id"], "name": province["name"], "owned_member_count": len(members),
            "scope_full_count": province["full_province_locations"], "partial_scope": province["partial"],
            "location_ids": [row["id"] for row in members], "assessment_counts": dict(statuses),
            "assessment": "See individual location_assessments in location-assessments.json; no province-level certification.",
        })
    assert len(province_assessments) == 38
    (ROOT / "province-assessments.json").write_text(json.dumps({"version":1,"issue":463,"province_count":len(province_assessments),"provinces":province_assessments},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    area_assessments = []
    for area in scope["area_scopes"]:
        members = [row for row in baseline["rows"] if hierarchy_by_id[row["parent_id"]].get("parent_id") == area["id"]]
        assert len(members) == area["owned_member_location_count"]
        unit = hierarchy_by_id[area["id"]]
        metadata = unit.get("metadata", {})
        area_assessments.append({
            "area_id":area["id"],"name":area["name"],"owned_member_count":area["owned_member_location_count"],
            "full_scope_count":area["full_area_location_count"],"partial_scope":area["partial"],
            "scope_member_ids":[row["id"] for row in members],"scoped_parent_province_ids":sorted({row["parent_id"] for row in members}),
            "declared_reference_basis":metadata.get("basis"),"source":unit.get("source"),"source_url":unit.get("source_url"),
            "declared_current_review":metadata.get("semantic_review"),
            "assessment":"Issue workload membership follows pinned baseline location→province→area parent links. This proves current reference membership only, not area boundary or intended Atlas purpose.",
        })
    assert len(area_assessments) == 5
    (ROOT / "area-assessments.json").write_text(json.dumps({"version":1,"issue":463,"area_count":len(area_assessments),"areas":area_assessments},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    outputs = {
        "version": 1,
        "issue": 463,
        "baseline_commit": baseline["baseline_commit"],
        "scope_sha256": sha256(ROOT / "scope.json"),
        "source_file_sha256": {country: sha256(d["path"]) for country, d in SOURCES.items()},
        "source_feature_counts": country_source_counts,
        "scoped_subject_counts": dict(country_scope_counts),
        "controls": {
            "outcome": "passed",
            "positive": "227/227 exact issue IDs resolve to one retained native source feature",
            "negative": "fabricated native ID rejected; explicit duplicate roster rejected by uniqueness check",
            "limit": "These controls verify roster linkage only, not territorial meaning, completeness, parentage or boundary accuracy.",
        },
        "classifications": dict(Counter(row["status"] for row in assessments)),
        "location_assessments": assessments,
    }
    (ROOT / "location-assessments.json").write_text(json.dumps(outputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
