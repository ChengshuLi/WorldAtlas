#!/usr/bin/env python3
"""Reproduce the Chad fragment lineage screens from immutable PR-base bytes."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = "data/regional-review/chad-ecoregion-role-20261005/"
VINTAGE = OWNED + "vintages/20261005-r4/"
BASE = "e063b72150b294898d83277d04a5dfc165600664"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))
from evidence.geometry import METHOD, VERSION as GEOMETRY_VERSION, land_area_m2
from evidence.immutable import Baseline, canonical_json, descriptor, sha256, write_new_vintage
from shapely import make_valid, union_all
from shapely.geometry import Polygon, shape
from shapely.validation import explain_validity

IDS = [
    "atlas:physical:039e9aed4c3f60bdb4b3",
    "atlas:physical:1a8dfa5d55e056663801",
    "atlas:physical:211ad3000d0e261c1959",
    "atlas:physical:45fbb334fdad853f2c06",
    "atlas:physical:49cee21465f10da9661b",
    "atlas:physical:4ef653826b687f699627",
    "atlas:physical:6fb3186a475bbf01eafd",
    "atlas:physical:9e00def6045964a40a34",
    "atlas:physical:a22d3e30f8f05346e690",
    "atlas:physical:b5f3e1387c85754a83e2",
    "atlas:physical:bb2738933d8402555a90",
    "atlas:physical:cb3b4c07ca149f790a56",
    "atlas:physical:cfe1c57c717a4f565b55",
    "atlas:physical:d6cf62f7d9d4452b2869",
    "atlas:physical:e19768af527b61d7a0e8",
    "atlas:physical:e74339c4e4f9d2bab2fc",
    "atlas:physical:f580491d6010c19d648c",
]
FILES = [
    "data/hierarchy.json",
    "data/world-index.json",
    "data/geography/part-23.json",
    "data/validation/macro-publication-v5.json",
    "data/regional-review/regional-review-1f89976bc419653c/assessment.json",
    "data/regional-review/regional-review-1f89976bc419653c/baseline-members.geojson.gz",
    "data/regional-review/regional-review-1f89976bc419653c/geometry-audit.json",
    "data/regional-review/regional-review-1f89976bc419653c/issue-scope-pinned.json",
    "data/regional-review/regional-review-1f89976bc419653c/source-register.json",
    "data/regional-review/regional-review-1f89976bc419653c/sources/geoBoundaries-TCD-ADM1.geojson",
    "data/regional-review/regional-review-1f89976bc419653c/sources/geoBoundaries-TCD-ADM2.geojson",
    "data/regional-review/regional-review-1f89976bc419653c/sources/geoboundaries-current-TCD-ADM1-metadata.json",
    "data/regional-review/regional-review-1f89976bc419653c/sources/geoboundaries-current-TCD-ADM2-metadata.json",
    "data/regional-review/regional-review-1f89976bc419653c/sources/resolve-item-metadata.json",
    "data/regional-review/regional-review-1f89976bc419653c/sources/resolve-layer-metadata.json",
    "data/regional-review/regional-review-1f89976bc419653c/sources/resolve-selected-query.json",
]
PIN_PATHS = {
    "hierarchy": "data/hierarchy.json",
    "footprints": "data/regional-review/regional-review-1f89976bc419653c/baseline-members.geojson.gz",
    "tcd_adm2_source": "data/regional-review/regional-review-1f89976bc419653c/sources/geoBoundaries-TCD-ADM2.geojson",
    "resolve_selected_features": "data/regional-review/regional-review-1f89976bc419653c/sources/resolve-selected-query.json",
}


def git_blob(path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{BASE}:{path}"])


def baseline() -> Baseline:
    files = []
    for path in FILES:
        raw = git_blob(path)
        row = descriptor(path, raw)
        if path.endswith(".gz"):
            unpacked = gzip.decompress(raw)
            row.update({"uncompressed_bytes": len(unpacked), "uncompressed_sha256": sha256(unpacked)})
        files.append(row)
    return Baseline(ROOT, BASE, files)


def read_json(b: Baseline, path: str):
    return json.loads(b.read(path))


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", value)


def polygonal_valid_copy(geom):
    """Return an explicit diagnostic make-valid clone; original source stays intact."""
    if geom.is_valid:
        return geom, {"original_valid": True, "validity_reason": "Valid Geometry", "repair": "none"}
    repaired = make_valid(geom)
    parts = []

    def collect(g):
        if g.geom_type == "Polygon":
            parts.append(g)
        elif hasattr(g, "geoms"):
            for child in g.geoms:
                collect(child)

    collect(repaired)
    if not parts:
        raise ValueError("make_valid produced no polygonal components")
    result = union_all(parts)
    if result.is_empty or not result.is_valid or result.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError("Diagnostic polygon extraction was not valid polygonal land")
    return result, {"original_valid": False, "validity_reason": explain_validity(geom),
                    "repair": "shapely.make_valid; retain polygonal components and union for screening only"}


def close(a: float, b: float, tolerance: float = 1e-10) -> bool:
    return math.isclose(a, b, rel_tol=tolerance, abs_tol=tolerance)


def overlay_land_area(geom) -> float:
    """Measure polygonal overlay pieces only; line/point touches have zero land area."""
    if geom.is_empty:
        return 0.0
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return land_area_m2(geom)
    pieces = []
    def collect(g):
        if g.geom_type == "Polygon":
            pieces.append(g)
        elif hasattr(g, "geoms"):
            for child in g.geoms:
                collect(child)
    collect(geom)
    return land_area_m2(union_all(pieces)) if pieces else 0.0


def build(b: Baseline):
    p = "data/regional-review/regional-review-1f89976bc419653c/"
    atlas_doc = read_json(b, "data/geography/part-23.json")
    archived = json.loads(__import__("gzip").decompress(b.read(p + "baseline-members.geojson.gz")))
    parent_by_id = {f["id"]: f for f in archived["features"]}
    atlas_by_id = {f["id"]: f for f in atlas_doc["features"] if f.get("id") in IDS}
    if set(atlas_by_id) != set(IDS) or set(parent_by_id).intersection(IDS) != set(IDS):
        raise ValueError("Pinned Atlas/ancestor evidence does not contain the exact roster")
    if any(atlas_by_id[i] != parent_by_id[i] for i in IDS):
        raise ValueError("Current Atlas feature differs from the retained ancestor evidence")

    adm2_features = read_json(b, p + "sources/geoBoundaries-TCD-ADM2.geojson")["features"]
    adm1_features = read_json(b, p + "sources/geoBoundaries-TCD-ADM1.geojson")["features"]
    eco_features = read_json(b, p + "sources/resolve-selected-query.json")["features"]
    adm2 = {f["properties"]["shapeID"]: f for f in adm2_features}
    adm1 = {f["properties"]["shapeID"]: f for f in adm1_features}
    ecos = {str(f["properties"]["ECO_ID"]): f for f in eco_features}
    if len(adm2_features) != 70 or len(adm1_features) != 23 or set(ecos) != {"53", "822", "823", "842", "844"}:
        raise ValueError("Pinned source roster/counts changed")

    scope = read_json(b, p + "issue-scope-pinned.json")
    publication = read_json(b, "data/validation/macro-publication-v5.json")["release"]
    source_register = read_json(b, p + "source-register.json")
    current_meta = read_json(b, p + "sources/geoboundaries-current-TCD-ADM2-metadata.json")
    resolve_item = read_json(b, p + "sources/resolve-item-metadata.json")
    resolve_layer = read_json(b, p + "sources/resolve-layer-metadata.json")
    inherited_audit = read_json(b, p + "geometry-audit.json")
    audit_by_id = {x["location_id"]: x for x in inherited_audit["subjects"] if x["location_id"] in IDS}
    tcd_source = source_register["sources"]
    adm1_meta = next(x for x in tcd_source if x["source_id"] == "gb:TCD:ADM1")
    tcd_meta = next(x for x in tcd_source if x["source_id"] == "gb:TCD:ADM2")
    resolve_meta = [x for x in tcd_source if x["source_id"] == "RESOLVE-ECOREGIONS-2017"]
    if len(audit_by_id) != len(IDS):
        raise ValueError("Inherited audit lacks one or more exact subjects")

    resolved_ecos = {}
    eco_validity = {}
    for eco_id, f in ecos.items():
        original = shape(f["geometry"])
        repaired, status = polygonal_valid_copy(original)
        resolved_ecos[eco_id] = repaired
        eco_validity[eco_id] = {"eco_id": int(eco_id), "eco_name": f["properties"]["ECO_NAME"],
                                "original_geometry_valid": status["original_valid"],
                                "validity_reason": status["validity_reason"], "diagnostic_operation": status["repair"],
                                }

    parent_cache = {key: shape(f["geometry"]) for key, f in adm1.items()}
    tcd_geoms = {key: shape(f["geometry"]) for key, f in adm2.items()}
    if any(not g.is_valid for g in list(parent_cache.values()) + list(tcd_geoms.values())):
        raise ValueError("An administrative source input is invalid; stop rather than repair it")

    rows, metric_rows = [], []

    def add_metric(metric_id, value, unit, numerator, denominator, input_path, basis):
        value = float(value)
        if not math.isfinite(value) or denominator <= 0 or not close(value, numerator / denominator):
            raise ValueError("Invalid metric arithmetic: " + metric_id)
        metric_rows.append({"id": metric_id, "value": value, "unit": unit, "numerator": float(numerator),
                            "denominator": float(denominator), "input_sha256": b.pins[input_path]["sha256"],
                            "evaluation_commit": BASE, "vintage": "current", "basis": basis})
        return value

    group_fragments = {}
    fragment_geoms = {}
    for ident in IDS:
        f = atlas_by_id[ident]
        meta = f["properties"]["metadata"]
        eco_id = meta["source_id"].split(":", 1)[1]
        member_ids = meta["source_member_ids"]
        if len(member_ids) != 1 or not member_ids[0].startswith("gb:TCD:ADM2:"):
            raise ValueError("Unexpected predecessor membership")
        admin_id = member_ids[0].rsplit(":", 1)[1]
        if eco_id not in ecos or admin_id not in adm2:
            raise ValueError("Subject lineage does not resolve to pinned source members")
        a = shape(f["geometry"])
        if not a.is_valid:
            raise ValueError("Atlas subject geometry is invalid")
        t = tcd_geoms[admin_id]
        e = resolved_ecos[eco_id]
        expected = t.intersection(e)
        if expected.is_empty:
            raise ValueError("Expected administrative/ecological intersection is empty")
        overlap_expected = a.intersection(expected)
        overlap_admin = a.intersection(t)
        overlap_eco = a.intersection(e)
        atlas_area = land_area_m2(a)
        expected_area = land_area_m2(expected)
        intersection_area = land_area_m2(overlap_expected)
        admin_intersection_area = land_area_m2(overlap_admin)
        eco_intersection_area = land_area_m2(overlap_eco)
        idtag = ident.rsplit(":", 1)[1]
        m_admin = add_metric("fragment_" + idtag + "_inside_predecessor_share", admin_intersection_area / atlas_area,
                             "fraction", admin_intersection_area, atlas_area, "data/geography/part-23.json",
                             "WGS84 area of Atlas feature intersecting its pinned 2019 ADM2 predecessor divided by Atlas feature area")
        m_eco = add_metric("fragment_" + idtag + "_inside_ecoregion_share", eco_intersection_area / atlas_area,
                           "fraction", eco_intersection_area, atlas_area, "data/geography/part-23.json",
                           "WGS84 area of Atlas feature intersecting its pinned 2017 RESOLVE ecological feature divided by Atlas feature area")
        m_intersection = add_metric("fragment_" + idtag + "_expected_intersection_coverage", intersection_area / expected_area,
                                    "fraction", intersection_area, expected_area, "data/geography/part-23.json",
                                    "WGS84 area of Atlas feature covered by ADM2×ecoregion intersection divided by that intersection area")
        tfeature = adm2[admin_id]
        efeature = ecos[eco_id]
        eprops = efeature["properties"]
        tprops = tfeature["properties"]
        parent = None
        parent_hits = []
        t_area = land_area_m2(t)
        for pid, pg in parent_cache.items():
            x = overlay_land_area(t.intersection(pg))
            share = x / t_area
            if share > 0.0001:
                parent_hits.append((share, pid, x))
        parent_hits.sort(reverse=True)
        if not parent_hits:
            raise ValueError("No source ADM1 parent candidate")
        parent_share, parent_id, parent_intersection = parent_hits[0]
        parent_feature = adm1[parent_id]
        source_parent = parent_feature["properties"]["shapeName"]
        source_parent_slug = norm(source_parent)
        atlas_parent_slug = f["properties"]["parent_id"].split(":")[2]
        m_parent = add_metric("fragment_" + idtag + "_predecessor_parent_share", parent_intersection / t_area,
                              "fraction", parent_intersection, t_area, "data/regional-review/regional-review-1f89976bc419653c/sources/geoBoundaries-TCD-ADM1.geojson",
                              "WGS84 area of predecessor ADM2 covered by the top-overlap source ADM1 parent divided by predecessor area")
        group_fragments.setdefault(admin_id, []).append(a)
        fragment_geoms[ident] = a
        row = {
            "atlas_id": ident, "atlas_name": f["properties"]["name"], "atlas_parent_id": f["properties"]["parent_id"],
            "atlas_parent_slug": atlas_parent_slug, "atlas_source_role_recorded": meta["source_role"],
            "atlas_source_name_recorded": meta["source_name"], "atlas_selection_reason_recorded": meta["selection_reason"],
            "atlas_semantic_review_status": meta.get("semantic_review", {}).get("status"),
            "atlas_source_id": meta["source_id"], "atlas_ecological_source_member": {"eco_id": int(eco_id),
                "eco_name": eprops["ECO_NAME"], "biome_name": eprops.get("BIOME_NAME"), "realm": eprops.get("REALM"),
                "license": eprops.get("LICENSE")},
            "engineering_metadata_proposal": {
                "source_name": "RESOLVE Ecoregions and Biomes (2017)",
                "source_role": "Ecological fragment",
                "selection_reason": ("Selected as a physical portion associated with RESOLVE 2017 ECO_ID " + eco_id +
                    " (" + eprops["ECO_NAME"] + "). The linked 2019 TCD ADM2 feature " + admin_id + " (" + tprops["shapeName"] +
                    ") is retained as predecessor lineage, not asserted as the selected whole-unit boundary. The exact historical clipping recipe, full ecological completeness, and tier suitability remain unverified."),
                "source_member_ids": meta["source_member_ids"],
                "source_id": meta["source_id"],
                "source_url": meta["source_url"],
                "preservation": "Proposal changes descriptive source metadata only; it retains the exact Atlas ID, source_id, source_member_ids, footprint, Atlas parent, and release pins."
            },
            "atlas_administrative_predecessor": {"source_id": "gb:TCD:ADM2:" + admin_id,
                "source_feature_id": admin_id, "source_name": tprops["shapeName"], "source_level": tprops["shapeType"],
                "source_vintage": "2019", "atlas_recorded_original_id": meta.get("original_id"),
            "source_parent_adm1_id": parent_id, "source_parent_adm1_name": source_parent,
                "source_parent_adm1_vintage": "2017",
                "source_parent_area_share_screen": parent_share, "parent_name_normalization_matches_atlas_parent": source_parent_slug == norm(atlas_parent_slug),
                "other_source_adm1_intersections": [{"id": x[1], "name": adm1[x[1]]["properties"]["shapeName"], "share": x[0]} for x in parent_hits[1:]]},
            "geometry_screen": {"atlas_area_m2": atlas_area, "intersection_expected_m2": intersection_area,
                "expected_admin_x_ecoregion_m2": expected_area, "fragment_inside_administrative_predecessor_share": m_admin,
                "fragment_inside_ecoregion_share": m_eco, "expected_intersection_covered_by_fragment_share": m_intersection,
                "evidence_limits": ["WGS84 straight-source-edge ellipsoidal area after explicitly recorded diagnostic make_valid on the source ecoregion only when invalid.",
                    "Overlay correspondence is not proof of source production steps, legal boundary truth, ecological completeness, or tier suitability."]},
            "inherited_planar_screen": audit_by_id[ident]
        }
        rows.append(row)

    # Summarize each distinct administrative predecessor, with source neighbors at the same 2019 ADM2 level.
    predecessor_rows = []
    for admin_id in sorted(group_fragments, key=lambda key: adm2[key]["properties"]["shapeName"].casefold()):
        source = adm2[admin_id]
        source_geom = tcd_geoms[admin_id]
        parts = group_fragments[admin_id]
        parts_union = union_all(parts)
        source_area = land_area_m2(source_geom)
        covered_geom = source_geom.intersection(parts_union)
        covered_area = land_area_m2(covered_geom)
        uncovered_area = land_area_m2(source_geom.difference(parts_union))
        tag = re.sub("[^a-z0-9]+", "_", norm(source["properties"]["shapeName"])).strip("_")
        ratio = add_metric("predecessor_" + tag + "_fragment_union_coverage", covered_area / source_area, "fraction",
                           covered_area, source_area, PIN_PATHS["tcd_adm2_source"],
                           "WGS84 area of union of exact scoped Atlas fragments intersecting the pinned 2019 ADM2 feature divided by that feature area")
        unrepresented_km2 = uncovered_area / 1_000_000
        add_metric("predecessor_" + tag + "_unrepresented_area_km2", unrepresented_km2, "km²",
                   unrepresented_km2, 1.0, PIN_PATHS["tcd_adm2_source"],
                   "WGS84 area of the pinned 2019 ADM2 feature outside the union of its exact scoped Atlas fragments, expressed in square kilometres")
        nonoverlap = 0.0
        for ix, left in enumerate(parts):
            for right in parts[ix + 1:]:
                overlap = left.intersection(right)
                if not overlap.is_empty:
                    nonoverlap += overlay_land_area(overlap)
        neighbors = []
        for other_id, other in adm2.items():
            if other_id == admin_id:
                continue
            shared = source_geom.boundary.intersection(shape(other["geometry"]).boundary)
            if shared.length > 1e-6:
                neighbors.append({"id": other_id, "name": other["properties"]["shapeName"],
                                  "shared_boundary_length_degrees_screen": float(shared.length)})
        neighbors.sort(key=lambda x: (x["name"].casefold(), x["id"]))
        # Resolve predecessor's dominant ADM1 parent independently at the source-unit level.
        parent_intersections = []
        for parent_id, parent in adm1.items():
            overlap = overlay_land_area(source_geom.intersection(parent_cache[parent_id]))
            share = overlap / source_area
            if share > 0.0001:
                parent_intersections.append({"id": parent_id, "name": parent["properties"]["shapeName"],
                                             "area_share": share})
        parent_intersections.sort(key=lambda x: (-x["area_share"], x["name"].casefold(), x["id"]))
        predecessor_rows.append({
            "source_id": "gb:TCD:ADM2:" + admin_id, "source_feature_id": admin_id,
            "name": source["properties"]["shapeName"], "level": source["properties"]["shapeType"],
            "source_vintage": "2019", "fragment_count": len(parts),
            "fragment_ids": [r["atlas_id"] for r in rows if r["atlas_administrative_predecessor"]["source_feature_id"] == admin_id],
            "source_parent_adm1_candidates_by_area": parent_intersections,
            "same_level_neighboring_adm2_units_by_shared_boundary": neighbors,
            "fragment_union_area_m2": land_area_m2(parts_union), "source_area_m2": source_area,
            "covered_area_m2": covered_area, "uncovered_area_m2": uncovered_area,
            "fragment_union_coverage_share": ratio, "fragment_pairwise_positive_area_overlap_m2": nonoverlap,
            "metric_id": "predecessor_" + tag + "_fragment_union_coverage",
            "unrepresented_area_metric_id": "predecessor_" + tag + "_unrepresented_area_km2",
            "limits": ["Atlas portions may be derived/clipped representations, not boundaries of the predecessor units.",
                       "Coverage is a geometric screen in source-vintage geometry and is not a legal boundary or completeness determination.",
                       "Shared-boundary adjacency is an EPSG:4326 planar topology screen; point-only contacts are excluded by the length threshold."]
        })

    results = {
        "version": 1,
        "issue": 875,
        "baseline_commit": BASE,
        "retrieved_at_utc": "2026-10-05",
        "subject_ids": IDS,
        "subject_ids_sha256": hashlib.sha256(json.dumps(sorted(IDS), separators=(",", ":")).encode()).hexdigest(),
        "preservation_checks": {"exact_roster_present_in_atlas_part_23": len(atlas_by_id) == len(IDS),
            "all_17_features_byte_semantics_match_retained_ancestor_features": True,
            "source_ids_members_geometry_and_parents_unchanged": True,
            "geography_or_release_files_modified": False},
        "pinned_release_context": {"release_id": publication["id"], "version": publication["version"],
            "hierarchy_sha256": publication["hierarchy_sha256"], "footprints_sha256": publication["footprints_sha256"],
            "release_file": "data/validation/macro-publication-v5.json"},
        "source_scope": {"resolve_features": [{"eco_id": int(k), "eco_name": ecos[k]["properties"]["ECO_NAME"],
            "biome_name": ecos[k]["properties"].get("BIOME_NAME"), "realm": ecos[k]["properties"].get("REALM"),
            "license": ecos[k]["properties"].get("LICENSE"), "atlas_fragment_count": sum(r["atlas_source_id"] == "resolve:" + k for r in rows),
            "original_geometry_valid": eco_validity[k]["original_geometry_valid"], "validity_reason": eco_validity[k]["validity_reason"],
            "diagnostic_operation": eco_validity[k]["diagnostic_operation"]} for k in sorted(ecos, key=int)],
            "tcd_adm2_source_feature_count": len(adm2_features), "tcd_adm1_source_feature_count": len(adm1_features),
            "tcd_adm2_source_role": tcd_meta["issue_source_role"], "tcd_adm2_source_vintage": tcd_meta["issue_source_vintage"],
            "tcd_adm2_source_sha256": tcd_meta["original_sha256"], "tcd_adm2_source_license": tcd_meta["issue_license"],
            "tcd_adm2_upstream_source": tcd_meta["upstream_source"], "tcd_adm2_mutable_metadata_sha256": tcd_meta["mutable_current_metadata_sha256"],
            "tcd_adm1_parent_screen": {"source_vintage": "2017", "feature_count": 23,
                "source": "OpenStreetMap, Wambacher", "license": "ODbL 1.0",
                "sha256": adm1_meta["original_sha256"], "source_retrieved_utc": adm1_meta["retrieved_utc"],
                "restoration_url": adm1_meta["immutable_restoration_url"],
                "mutable_metadata_sha256": adm1_meta["mutable_current_metadata_sha256"],
                "mutable_metadata_fields": adm1_meta["mutable_current_metadata_fields"],
                "vintage_mismatch_limit": "This retained 2017 ADM1 source is only a spatial parent screen for 2019 ADM2 units; it is not a same-vintage authoritative hierarchy crosswalk."},
            "resolve_item_id": resolve_item["id"], "resolve_item_title": resolve_item["title"],
            "resolve_layer_name": resolve_layer["name"], "resolve_layer_data_last_edit_epoch_ms": resolve_layer.get("editingInfo", {}).get("dataLastEditDate"),
            "resolve_query_sha256": next(x["original_sha256"] for x in resolve_meta if x["file"].endswith("resolve-selected-query.json")),
            "source_retrieval_details": {x["file"].split("/")[-1]: {"retrieved_utc": x["retrieved_utc"], "sha256": x["original_sha256"], "url": x.get("restoration_url") or x.get("immutable_restoration_url")} for x in resolve_meta + [adm1_meta, tcd_meta]}},
        "source_member_lineage": rows,
        "predecessor_units": predecessor_rows,
        "geometry_method": {**METHOD, "helper_version": GEOMETRY_VERSION,
            "diagnostic_source_repair": "Invalid original RESOLVE polygons are preserved byte-for-byte. make_valid() plus polygonal-component union is applied to in-memory clones only for overlays; no repaired geometry is exported or treated as source truth.",
            "overlay": "Shapely 2.1.2 planar topology in EPSG:4326 followed by shared-helper WGS84 straight-source-edge ellipsoidal area measurement; output ratios compare calculated areas. The 2017 ODbL ADM1 layer used for parent screening is vintage-mismatched with the 2019 CC BY 3.0 IGO ADM2 predecessor layer.",
            "neighbor_method": "2019 ADM2 polygon-boundary intersections with positive shared planar length greater than 1e-6 degrees; this is a same-source-version adjacency screen."},
        "metrics": metric_rows,
        "interpretation": {
            "finding": "The 17 records combine a 2017 RESOLVE ecological feature key with one 2019 TCD ADM2 predecessor member. The current fields 'Departments' and the administrative selection reason describe the predecessor as though it were the selected delineation; they do not describe the ecological fragment keys or prove the fragment construction recipe.",
            "proposed_role_wording": "Ecological fragment with 2019 administrative predecessor lineage",
            "proposed_selection_reason_wording": "Physical portion attributed to a named 2017 RESOLVE terrestrial ecoregion; linked 2019 TCD ADM2 department records predecessor lineage only. Original clipping recipe, boundary completeness, and suitability at this Atlas tier remain unverified.",
            "engineering_handoff": "For exactly the 17 listed physical IDs, preserve IDs, source_member_ids, source_id, geometry, Atlas parent and release pins; correct only descriptive provenance fields after validating their schema. Do not relabel the feature as a complete department or certify the ecology-derived partition. Record source role and selection rationale as a composite ecological fragment with a predecessor crosswalk.",
            "source_role_confidence": "High that the source-role/selection wording is materially misleading; medium that the exact ecological/admin overlay is the original production algorithm because no original generation recipe/versioned inputs were retained.",
            "completeness": "Source-vintage geometric screens show near-complete union coverage of the six 2019 ADM2 predecessors, but leave small slivers and cannot establish modern completeness, political legality, ecological completeness, or intended territorial level.",
            "regional_approval": "Not approved; evidence-only source role and lineage review."
        }
    }
    return results


def analytic_box_area(west, south, east, north):
    # Independent exact ellipsoid-strip primitive used only for the control rectangle.
    a, f = 6378137.0, 1 / 298.257223563
    e2 = f * (2 - f)
    e = math.sqrt(e2)
    def strip(lat):
        u = math.sin(math.radians(lat))
        return a*a*(1-e2)/2*(u/(1-e2*u*u)+math.atanh(e*u)/e)
    return math.radians(east-west) * (strip(north) - strip(south))


def controls(result):
    from shapely.geometry import box
    positive_geom = box(0, 0, 1.01, 0.01)
    measured = land_area_m2(positive_geom)
    expected = analytic_box_area(0, 0, 1.01, 0.01)
    if not math.isclose(measured, expected, rel_tol=1e-10):
        raise ValueError("Positive geometry control did not match independent analytic area")
    bowtie = Polygon([(0, 0), (1, 1), (0, 1), (1, 0), (0, 0)])
    rejected = False
    try:
        land_area_m2(bowtie)
    except ValueError:
        rejected = True
    if not rejected:
        raise ValueError("Negative geometry control was silently accepted")
    canonical = canonical_json({"z": 1, "a": 2}).decode()
    if canonical != '{"a":2,"z":1}\n':
        raise ValueError("Positive generator control failed")
    nan_rejected = False
    try:
        canonical_json({"not_finite": float("nan")})
    except ValueError:
        nan_rejected = True
    if not nan_rejected:
        raise ValueError("Negative generator control was silently accepted")
    return {
        "geometry-positive": {"method_id": "geodesic-overlays", "kind": "positive-control", "outcome": "passed",
            "control": "WGS84 helper rectangle area agrees with independent ellipsoid-strip analytic calculation.",
            "helper_area_m2": measured, "analytic_area_m2": expected, "relative_tolerance": 1e-10},
        "geometry-negative": {"method_id": "geodesic-overlays", "kind": "negative-control", "outcome": "passed",
            "control": "Self-intersecting bow-tie source polygon is rejected by the shared area helper; no silent repair."},
        "generator-positive": {"method_id": "packet-generator", "kind": "positive-control", "outcome": "passed",
            "control": "Canonical JSON sorts keys, uses compact UTF-8, and writes one trailing newline."},
        "generator-negative": {"method_id": "packet-generator", "kind": "negative-control", "outcome": "passed",
            "control": "Canonical JSON rejects non-finite numeric values."}
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Rebuild in memory and compare existing owned outputs")
    args = parser.parse_args()
    b = baseline()
    result_one = build(b)
    first = canonical_json(result_one)
    result_two = build(b)
    second = canonical_json(result_two)
    reproducible = sha256(first) == sha256(second)
    if not reproducible:
        raise SystemExit("Two independent in-memory runs differ")
    payloads = {"lineage-assessment.json": first}
    outputs = controls(result_one)
    for key, body in outputs.items():
        payloads[key + ".json"] = canonical_json(body)
    payloads["reproducibility.json"] = canonical_json({"method_id": "packet-generator", "kind": "reproducibility", "outcome": "passed",
        "run_one_sha256": sha256(first), "run_two_sha256": sha256(second), "input_commit": BASE,
        "description": "Two independent in-memory builds from the same immutable baseline and pinned files produced byte-identical canonical JSON."})
    directory = ROOT / VINTAGE
    if args.check:
        for filename, expected in payloads.items():
            path = directory / filename
            if not path.is_file() or path.read_bytes() != expected:
                raise SystemExit("Reproduction mismatch: " + str(path))
        print(json.dumps({"ok": True, "mode": "check", "baseline": BASE, "outputs": {k: sha256(v) for k, v in payloads.items()}}, sort_keys=True))
        return
    for filename, raw in payloads.items():
        write_new_vintage(b, OWNED, "20261005-r4", filename, json.loads(raw))
    print(json.dumps({"ok": True, "mode": "write-once", "baseline": BASE, "outputs": {k: sha256(v) for k, v in payloads.items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
