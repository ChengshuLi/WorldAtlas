#!/usr/bin/env python3
"""Offline, read-only exhaustive audit of all current CSDs in issue #609's ten CDs."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
SOURCES = PACKET / "sources"
PARENT_DIR = ROOT / "data/regional-review/regional-review-4254da254d94f450"
TARGETS = ["5901", "5933", "5939", "5941", "5949", "5951", "5953", "5955", "5957", "5959"]
EXPECTED_PARENT_FILES = {
    "sources/statistics-canada-bc-census-divisions-2021.geojson.gz": "8a31cf19ad0694638c88275fec9ff1005970cd8600ca6baed245b8826756e9bf",
    "sources/statistics-canada-bc-census-subdivisions-2021.geojson.gz": "a16ca45708ab0ccd898994e5e792187d5a108741c2ff6f5f9f74e91242206ad4",
    "sources/geoboundaries-CAN-ADM3-2016.geojson": "9d292ebf9a09010fc81ee5fa69683b4a8ba1b0d969bb20f6b90ffc587d3f215f",
    "sources/statistics-canada-bc-population-centres-2021.geojson.gz": None,
    "sources/canadian-geographical-names-populated-places-BC.geojson.gz": None,
    "sources/current-parent-chains.json.gz": "aa0c1643d376baa9b7478d26886510718d3c0e242782df004e2defd028938290",
}
TO3347 = Transformer.from_crs("EPSG:4326", "EPSG:3347", always_xy=True).transform


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_gzip_json(path: Path) -> dict:
    with gzip.open(path, "rb") as stream:
        return json.load(stream)


def geom(feature: dict):
    g = shape(feature["geometry"])
    return g if g.is_valid else make_valid(g)


def projected(g):
    return transform(TO3347, g)


def feature_file(path: Path) -> list[dict]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            return json.load(stream).get("features", [])
    return read_json(path).get("features", [])


def federal_features() -> list[dict]:
    by_key: dict[tuple[str, str], dict] = {}
    for path in sorted(SOURCES.glob("nrcan-alclb-cd-*.geojson.gz")):
        for feature in feature_file(path):
            p = feature["properties"]
            key = (str(p.get("adminAreaId", "")), str(p.get("OBJECTID", "")))
            by_key[key] = feature
    return list(by_key.values())


def tree_for(features: list[dict]):
    shapes = [geom(f) for f in features]
    return shapes, STRtree(shapes)


def overlap_candidates(target, features: list[dict], shapes: list, tree: STRtree):
    tp = projected(target)
    rows = []
    for idx in tree.query(target, predicate="intersects"):
        g = shapes[int(idx)]
        gp = projected(g)
        inter = gp.intersection(tp).area
        if inter <= 0:
            continue
        rows.append((inter, gp.area, int(idx)))
    rows.sort(reverse=True)
    return tp, rows


def member_id_map() -> dict[str, str]:
    assessment = read_json(PARENT_DIR / "assessment.json")
    result: dict[str, str] = {}
    for row in assessment["locations"]:
        location_id = row.get("location_id", "")
        for part in row.get("full_parent_chain", []):
            for source_id in part.get("metadata", {}).get("source_member_ids", []):
                result[source_id] = location_id
    return result


def source_type_name(code: str) -> str:
    return {
        "RDA": "regional district electoral area",
        "IRI": "Indian reserve (census subdivision type)",
        "S-É": "Indian settlement (census subdivision type)",
        "NL": "Nisga'a land (census subdivision type)",
        "RGM": "regional municipality",
    }.get(code, "municipality or other census subdivision type")


def main() -> None:
    # Reconfirm the immutable parent evidence used for all inherited source files.
    parent_manifest = read_json(PARENT_DIR / "sources-manifest.json")
    parent_inventory = {row["path"]: row for row in parent_manifest["files"]}
    input_receipt = {}
    for relative, expected_hash in EXPECTED_PARENT_FILES.items():
        path = PARENT_DIR / relative
        data = path.read_bytes()
        actual_hash = hashlib.sha256(data).hexdigest()
        assert relative in parent_inventory, relative
        assert actual_hash == parent_inventory[relative]["sha256"], relative
        if expected_hash:
            assert actual_hash == expected_hash, relative
        input_receipt[relative] = {"bytes": len(data), "sha256": actual_hash}

    cd_features = read_gzip_json(PARENT_DIR / "sources/statistics-canada-bc-census-divisions-2021.geojson.gz")["features"]
    csd_features = read_gzip_json(PARENT_DIR / "sources/statistics-canada-bc-census-subdivisions-2021.geojson.gz")["features"]
    gb_features = read_json(PARENT_DIR / "sources/geoboundaries-CAN-ADM3-2016.geojson")["features"]
    pc_features = read_gzip_json(PARENT_DIR / "sources/statistics-canada-bc-population-centres-2021.geojson.gz")["features"]
    place_features = read_gzip_json(PARENT_DIR / "sources/canadian-geographical-names-populated-places-BC.geojson.gz")["features"]
    target_cds = {f["properties"]["CDUID"]: f for f in cd_features if f["properties"]["CDUID"] in TARGETS}
    assert set(target_cds) == set(TARGETS)
    target_cd_geom = {cd: geom(f) for cd, f in target_cds.items()}
    target_csds = [f for f in csd_features if f["properties"]["CSDUID"][:4] in TARGETS]
    csds_by_cd: dict[str, list[dict]] = defaultdict(list)
    for f in target_csds:
        csds_by_cd[f["properties"]["CSDUID"][:4]].append(f)
    assert len(target_csds) == 335
    assert all(len(csds_by_cd[cd]) > 0 for cd in TARGETS)

    gb_member_map = member_id_map()
    current_chains = read_gzip_json(PARENT_DIR / "sources/current-parent-chains.json.gz")
    current_chain_by_location = {
        row["id"]: json.dumps([
            {"id": tier.get("id"), "name": tier.get("name"), "reference_owner": tier.get("reference_owner")}
            for tier in row["parent_chain"]
        ], ensure_ascii=False, separators=(",", ":"))
        for row in current_chains
    }
    gb_shapes, gb_tree = tree_for(gb_features)
    bc_rds = feature_file(SOURCES / "bc-regional-districts-and-stikine.geojson.gz")
    bc_eas = feature_file(SOURCES / "bc-electoral-areas.geojson.gz")
    bc_munis = feature_file(SOURCES / "bc-municipalities.geojson.gz")
    rd_shapes, rd_tree = tree_for(bc_rds)
    ea_shapes, ea_tree = tree_for(bc_eas)
    muni_shapes, muni_tree = tree_for(bc_munis)
    federal = federal_features()
    fed_shapes, fed_tree = tree_for(federal)
    pc_shapes, pc_tree = tree_for(pc_features)
    place_shapes, place_tree = tree_for(place_features)

    # One-sided overlays are cartographic reconciliation screens, not legal area decisions.
    cd_union_rows = {}
    for cd, cd_feature in target_cds.items():
        current = target_cd_geom[cd]
        members = [geom(f) for f in csds_by_cd[cd]]
        union = unary_union(members)
        cp, up = projected(current), projected(union)
        cd_union_rows[cd] = {
            "official_cd_name": cd_feature["properties"]["CDNAME"],
            "csd_count": len(members),
            "csd_type_counts": dict(sorted(Counter(f["properties"]["CSDTYPE"] for f in csds_by_cd[cd]).items())),
            "official_cd_land_area_km2": cd_feature["properties"]["LANDAREA"],
            "projected_csd_union_km2": round(up.area / 1e6, 6),
            "projected_cd_area_km2": round(cp.area / 1e6, 6),
            "cd_area_covered_by_csd_union_pct": round(100 * cp.intersection(up).area / cp.area, 8),
            "csd_union_area_covered_by_cd_pct": round(100 * cp.intersection(up).area / up.area, 8),
            "cd_csd_symdiff_km2": round(cp.symmetric_difference(up).area / 1e6, 8),
        }

    rows = []
    gb_seen_by_cd: dict[str, set[str]] = defaultdict(set)
    official_rows_by_cd: dict[str, dict] = {}
    for cd in TARGETS:
        cdg = target_cd_geom[cd]
        cdp, rd_candidates = overlap_candidates(cdg, bc_rds, rd_shapes, rd_tree)
        ea_candidates = overlap_candidates(cdg, bc_eas, ea_shapes, ea_tree)[1]
        muni_candidates = overlap_candidates(cdg, bc_munis, muni_shapes, muni_tree)[1]
        population_candidates = overlap_candidates(cdg, pc_features, pc_shapes, pc_tree)[1]
        place_point_indices = [int(i) for i in place_tree.query(cdg, predicate="contains")]
        official_rows_by_cd[cd] = {
            "regional_district_or_stikine_intersections": [
                {"name": bc_rds[i]["properties"].get("ADMIN_AREA_NAME"), "boundary_type": bc_rds[i]["properties"].get("ADMIN_AREA_BOUNDARY_TYPE"), "coverage_of_cd_pct": round(100 * area / cdp.area, 6)}
                for area, _, i in rd_candidates if area / cdp.area > 1e-7
            ],
            "electoral_area_feature_count_intersecting_cd": sum(1 for area, _, _ in ea_candidates if area > 1),
            "municipality_feature_count_intersecting_cd": sum(1 for area, _, _ in muni_candidates if area > 1),
            "statistics_canada_population_centre_names": [pc_features[i]["properties"].get("PCNAME") for area, _, i in population_candidates if area > 1],
            "population_centre_count": sum(1 for area, _, _ in population_candidates if area > 1),
            "geographical_names_populated_place_points": [place_features[i]["properties"].get("GEONAME") for i in place_point_indices],
            "geographical_names_populated_place_count": len(place_point_indices),
        }

    for csd in target_csds:
        p = csd["properties"]
        cd = p["CSDUID"][:4]
        current = geom(csd)
        cp = projected(current)
        area = cp.area
        _, gb_candidates = overlap_candidates(current, gb_features, gb_shapes, gb_tree)
        source_union = unary_union([gb_shapes[i] for _, _, i in gb_candidates]) if gb_candidates else None
        source_cover = cp.intersection(projected(source_union)).area if source_union is not None else 0
        for _, _, i in gb_candidates:
            gb_seen_by_cd[cd].add(gb_features[i]["properties"]["shapeID"])
        gb_best = []
        for inter, ga, i in gb_candidates[:3]:
            gp = gb_features[i]["properties"]
            sid = "gb:CAN:ADM3:" + gp["shapeID"]
            gb_best.append({
                "name": gp["shapeName"],
                "source_id": sid,
                "coverage_of_current_csd_pct": round(100 * inter / area, 5) if area else 0,
                "current_csd_coverage_of_source_pct": round(100 * inter / ga, 5) if ga else 0,
                "already_a_member_of_location_id": gb_member_map.get(sid),
            })

        # Appropriate current BC legal-boundary crosswalk for the specific Statistics Canada CSD role.
        legal_candidates = []
        legal_source = None
        legal_tree = None
        if p["CSDTYPE"] == "RDA":
            legal_source, legal_tree = bc_eas, ea_tree
        elif p["CSDTYPE"] in {"CY", "DM", "T", "VL", "RGM"}:
            legal_source, legal_tree = bc_munis, muni_tree
        legal_best = []
        if legal_source is not None:
            _, legal_candidates = overlap_candidates(current, legal_source, (ea_shapes if legal_source is bc_eas else muni_shapes), legal_tree)
            for inter, la, i in legal_candidates[:3]:
                q = legal_source[i]["properties"]
                legal_best.append({
                    "legal_boundary_name": q.get("ADMIN_AREA_NAME"),
                    "boundary_abbreviation": q.get("ADMIN_AREA_ABBREVIATION"),
                    "parent_area_name": q.get("ADMIN_AREA_GROUP_NAME"),
                    "boundary_type": q.get("ADMIN_AREA_BOUNDARY_TYPE"),
                    "coverage_of_current_csd_pct": round(100 * inter / area, 5) if area else 0,
                    "current_csd_coverage_of_legal_feature_pct": round(100 * inter / la, 5) if la else 0,
                    "oic_number": q.get("OIC_MO_NUMBER"),
                    "oic_year": q.get("OIC_MO_YEAR"),
                })

        reserve_candidates = []
        reserve_union = []
        if p["CSDTYPE"] == "IRI":
            _, candidates = overlap_candidates(current, federal, fed_shapes, fed_tree)
            for inter, fa, i in candidates:
                q = federal[i]["properties"]
                t = q.get("distributionTypeEng") or ""
                if "reserve" not in t.lower():
                    continue
                reserve_union.append(fed_shapes[i])
                reserve_candidates.append((inter, fa, i))
            reserve_candidates.sort(reverse=True)
        reserve_coverage = 0
        if reserve_union:
            reserve_coverage = cp.intersection(projected(unary_union(reserve_union))).area
        reserve_names = []
        for inter, fa, i in reserve_candidates[:3]:
            q = federal[i]["properties"]
            reserve_names.append({
                "federal_boundary_name": q.get("adminAreaNameEng"),
                "federal_boundary_id": q.get("adminAreaId"),
                "distribution_type": q.get("distributionTypeEng"),
                "coverage_of_csd_pct": round(100 * inter / area, 5) if area else 0,
            })

        pc_names = []
        for inter, _, i in overlap_candidates(current, pc_features, pc_shapes, pc_tree)[1]:
            if inter > 1:
                pc_names.append(pc_features[i]["properties"].get("PCNAME"))
        place_indices = [int(i) for i in place_tree.query(current, predicate="contains")]
        local_place_names = [place_features[i]["properties"].get("GEONAME") for i in place_indices]

        row = {
            "cd_code": cd,
            "cd_name": target_cds[cd]["properties"]["CDNAME"],
            "csd_uid": p["CSDUID"],
            "csd_name": p["CSDNAME"],
            "csd_type_code": p["CSDTYPE"],
            "csd_type_official_expansion": source_type_name(p["CSDTYPE"]),
            "land_area_km2_statistics_canada": p["LANDAREA"],
            "2016_geoboundaries_candidates": json.dumps(gb_best, ensure_ascii=False, separators=(",", ":")),
            "2016_source_union_coverage_pct": round(100 * source_cover / area, 5) if area else 0,
            "current_bc_legal_boundary_candidates": json.dumps(legal_best, ensure_ascii=False, separators=(",", ":")),
            "federal_indian_reserve_coverage_pct": round(100 * reserve_coverage / area, 5) if p["CSDTYPE"] == "IRI" and area else "",
            "federal_indian_reserve_candidates": json.dumps(reserve_names, ensure_ascii=False, separators=(",", ":")),
            "statistics_canada_population_centres": json.dumps(pc_names, ensure_ascii=False, separators=(",", ":")),
            "geographical_names_populated_places": json.dumps(local_place_names, ensure_ascii=False, separators=(",", ":")),
            "assessment_status": "CSD row crosswalked to 2021 type, 2016 source candidates, applicable current BC legal layer, federal reserve candidates where applicable, and retained settlement sources; candidates are not legal equivalence or Atlas tier decisions",
        }
        rows.append(row)

    # Source-feature and cross-CD adjacency inventories; adjacent unassigned CD IDs are explicit.
    assignment = read_json(PARENT_DIR / "assessment.json")["british_columbia_admin_source_crosswalk_by_census_division"]
    direct_assigned_cd_codes = {code for code, value in assignment.items() if value.get("assigned_district_id")}
    all_cd_geoms = {f["properties"]["CDUID"]: geom(f) for f in cd_features}
    neighbor_map = {}
    for cd in TARGETS:
        boundary = all_cd_geoms[cd].boundary
        neighbors = []
        for other, g in all_cd_geoms.items():
            if other == cd or not boundary.intersects(g.boundary):
                continue
            shared = projected(boundary.intersection(g.boundary)).length
            if shared > 100:
                neighbors.append({"cd_code": other, "direct_admin_location_in_parent_packet": other in direct_assigned_cd_codes, "shared_edge_km": round(shared / 1000, 4)})
        neighbor_map[cd] = sorted(neighbors, key=lambda x: x["cd_code"])

    source_roster = {}
    for cd in TARGETS:
        cd_projected = projected(all_cd_geoms[cd])
        roster = []
        for feature, feature_shape in zip(gb_features, gb_shapes):
            feature_projected = projected(feature_shape)
            intersection_area = cd_projected.intersection(feature_projected).area
            if intersection_area <= 1:
                continue
            p = feature["properties"]
            source_id = "gb:CAN:ADM3:" + p["shapeID"]
            roster.append({
                "shape_id": p["shapeID"],
                "shape_name": p["shapeName"],
                "atlas_source_member_location_id": gb_member_map.get(source_id),
                "current_atlas_parent_chain": current_chain_by_location.get(gb_member_map.get(source_id)),
                "percent_of_2016_feature_intersecting_2021_cd": round(100 * intersection_area / feature_projected.area, 6) if feature_projected.area else 0,
                "percent_of_2021_cd_intersecting_2016_feature": round(100 * intersection_area / cd_projected.area, 6) if cd_projected.area else 0,
            })
        source_roster[cd] = sorted(roster, key=lambda x: x["shape_id"])

    summary = {
        "issue": 609,
        "review_date_utc": "2026-10-03",
        "exact_subjects": TARGETS,
        "subject_count": len(TARGETS),
        "current_statistics_canada_csd_count": len(rows),
        "input_pins": input_receipt,
        "cd_assessments": {
            cd: {
                **cd_union_rows[cd],
                **official_rows_by_cd[cd],
                "unique_2016_geoboundaries_feature_ids_intersecting_csd_union": len(gb_seen_by_cd[cd]),
                "unique_2016_geoboundaries_feature_ids_intersecting_cd": len(source_roster[cd]),
                "2016_geoboundaries_cd_intersection_roster": source_roster[cd],
                "2016_candidates_intersecting_csd_union_but_not_cd": sorted(gb_seen_by_cd[cd] - {row["shape_id"] for row in source_roster[cd]}),
                "2016_candidates_intersecting_cd_but_not_csd_union": sorted({row["shape_id"] for row in source_roster[cd]} - gb_seen_by_cd[cd]),
                "adjacent_census_divisions": neighbor_map[cd],
            }
            for cd in TARGETS
        },
        "source_layer_counts": {
            "statistics_canada_2021_csd_features_in_scope": len(rows),
            "data_bc_legal_regional_district_and_stikine_features": len(bc_rds),
            "data_bc_legal_electoral_area_features": len(bc_eas),
            "data_bc_legal_municipality_features": len(bc_munis),
            "nrcan_federal_aboriginal_legal_boundaries_unique_by_object_id": len(federal),
        },
        "method_limits": [
            "All overlay measurements are reprojection/area matching screens in EPSG:3347, not legal re-surveys.",
            "Statistics Canada CSDs are census statistical subdivisions; type labels do not by themselves establish an Atlas location tier.",
            "The NRCan ALCLB product includes Indian reserves and certain claim lands but its own definition explicitly excludes Indian Settlements and Indian Communities.",
            "Population Centre polygons follow Statistics Canada's urban-size/density definition; Canadian Geographical Names populated-place points are a named-place source, not a complete rural settlement inventory.",
            "The current DataBC layer notes that metes-and-bounds Letters Patent prevail in the event of a discrepancy; its digital lines can differ from present regional-district administration practice.",
        ],
    }
    with (PACKET / "csd-crosswalk.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (PACKET / "cd-assessments.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cds": {cd: {"csds": summary["cd_assessments"][cd]["csd_count"], "types": summary["cd_assessments"][cd]["csd_type_counts"], "cd_coverage_pct": summary["cd_assessments"][cd]["cd_area_covered_by_csd_union_pct"]} for cd in TARGETS}, "source_layer_counts": summary["source_layer_counts"]}, indent=2))


if __name__ == "__main__":
    main()
