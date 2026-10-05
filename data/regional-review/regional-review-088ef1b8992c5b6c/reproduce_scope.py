#!/usr/bin/env python3
"""Reproduce the #468 source, hierarchy and geometry diagnostics."""
import csv
import gzip
import hashlib
import json
import pathlib
import unicodedata

from shapely.affinity import translate
from shapely.geometry import box, shape

from evidence.geometry import METHOD, canonical_land, land_area_m2

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED = ROOT / "data/regional-review/regional-review-088ef1b8992c5b6c"
SOURCES = OWNED / "sources/geoboundaries-9469f09"
SHARED_CIV_PACKET = ROOT / "data/regional-review/regional-review-ab07a23bcfd9b1db"
BASELINE = json.loads(gzip.decompress((OWNED / "baseline-members.geojson.gz").read_bytes()))
SCOPE = json.loads((OWNED / "issue-scope-pinned.json").read_text())
RECEIPT = json.loads((OWNED / "baseline-receipt.json").read_text())


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load_geo(name):
    path = SOURCES / name
    raw = path.read_bytes()
    return path, raw, json.loads(raw)


def repair_source_text(value):
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def norm_name(value):
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return " ".join("".join(c if c.isalnum() else " " for c in text).split())


def component_count(g):
    return len(g.geoms) if g.geom_type == "MultiPolygon" else 1


def polygon_area(g):
    if g.is_empty:
        return 0.0
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return land_area_m2(g)
    if g.geom_type == "GeometryCollection":
        return sum(polygon_area(part) for part in g.geoms)
    return 0.0


scope_ids = set(SCOPE["member_location_ids"])
atlas = {f["properties"]["id"]: f for f in BASELINE["features"]}
if len(atlas) != 221 or set(atlas) != scope_ids:
    raise SystemExit("Baseline extracted geometry is not the exact issue roster")
hierarchy = json.loads(__import__("subprocess").check_output([
    "git", "-C", str(ROOT), "show", f'{RECEIPT["baseline_commit"]}:data/hierarchy.json'
]))
hierarchy = {x["id"]: x for x in hierarchy}

layers = {}
input_hashes = {"baseline-members.geojson.gz": sha((OWNED / "baseline-members.geojson.gz").read_bytes())}
for rel in ("issue-scope-pinned.json", "baseline-receipt.json", "claim-receipt.json", "issue-metadata.json"):
    input_hashes[str((OWNED / rel).relative_to(ROOT))] = sha((OWNED / rel).read_bytes())
for code, levels in (("BFA", ("ADM2", "ADM3")), ("CIV", ("ADM2", "ADM3"))):
    for level in levels:
        fname = f"geoBoundaries-{code}-{level}.geojson"
        path, raw, data = load_geo(fname)
        layers[(code, level)] = data["features"]
        input_hashes[str(path.relative_to(ROOT))] = sha(raw)
        meta_path, meta_raw, _ = load_geo(f"geoBoundaries-{code}-{level}-metaData.json")
        input_hashes[str(meta_path.relative_to(ROOT))] = sha(meta_raw)

ids_by_code = {
    "BFA": {x for x in scope_ids if x.startswith("gb:BFA:ADM3:")},
    "CIV": {x for x in scope_ids if x.startswith("gb:CIV:ADM3:")},
}
name_counts = {}
for code in ids_by_code:
    name_counts[code] = {}
    for f in layers[(code, "ADM3")]:
        name = repair_source_text(f["properties"].get("shapeName", ""))
        name_counts[code][name.casefold()] = name_counts[code].get(name.casefold(), 0) + 1

roster_path = OWNED / "evidence/bfa-insd-2019-commune-roster.csv"
roster_rows = list(csv.DictReader(roster_path.open(encoding="utf-8"))) if roster_path.exists() else []
roster_names = {}
for row in roster_rows:
    key = norm_name(row["commune"])
    roster_names.setdefault(key, []).append(row)
civ_roster = {r["issue_id"]: r for r in csv.DictReader(
    (OWNED / "evidence/civ-cavally-2019-project-roster.csv").open(encoding="utf-8")
)}
if len(civ_roster) != 17:
    raise SystemExit("Cavally source roster must contain all 17 exact issue IDs")
cntig_path = SHARED_CIV_PACKET / "sources/cntig-ocha-subprefectures-query-2025.geojson"
cntig_meta_path = SHARED_CIV_PACKET / "sources/cntig-ocha-subprefectures-layer-metadata.json"
cntig_raw = cntig_path.read_bytes()
cntig_meta_raw = cntig_meta_path.read_bytes()
if sha(cntig_raw) != "11deee85b6d41698d371846b0fd57cac6ad7b28a723e686c1ab6a0e149c3065e":
    raise SystemExit("Shared CNTIG/OCHA official layer changed from the #469 pin")
if sha(cntig_meta_raw) != "49855a9332d87b143f04e9914559867475fda45b28f6a186af864e3a02134868":
    raise SystemExit("Shared CNTIG/OCHA metadata changed from the #469 pin")
cntig = json.loads(cntig_raw)
if len(cntig["features"]) != 510:
    raise SystemExit("Pinned CNTIG/OCHA service snapshot must contain 510 features")
cntig_features = cntig["features"]
for rel in (
    "evidence/bfa-insd-2019-commune-roster.csv",
    "evidence/civ-cavally-2019-project-roster.csv",
    "sources/official-bfa/INSD-local-poverty-2019-report.pdf",
    "sources/official-civ/CI-SCIO-Agroforet-EIES-2026.pdf",
):
    p = OWNED / rel
    if p.exists():
        input_hashes[str(p.relative_to(ROOT))] = sha(p.read_bytes())
input_hashes[str(cntig_path.relative_to(ROOT))] = sha(cntig_raw)
input_hashes[str(cntig_meta_path.relative_to(ROOT))] = sha(cntig_meta_raw)

rows = []
for code in ("BFA", "CIV"):
    source_by_id = {}
    for f in layers[(code, "ADM3")]:
        pid = f["properties"]["shapeID"]
        source_by_id[f"gb:{code}:ADM3:{pid}"] = f
    if not ids_by_code[code] <= set(source_by_id):
        raise SystemExit(f"Missing scoped native IDs from {code} source")
    parent_features = []
    for f in layers[(code, "ADM2")]:
        geom = canonical_land(shape(f["geometry"]))
        parent_features.append({"name": repair_source_text(f["properties"]["shapeName"]), "geometry": geom,
                                "area_m2": polygon_area(geom)})
    for identity in sorted(ids_by_code[code]):
        sf = source_by_id[identity]
        af = atlas[identity]
        sp, ap = sf["properties"], af["properties"]
        source_name = repair_source_text(sp.get("shapeName", ""))
        atlas_name = ap.get("name", "")
        sg, ag = canonical_land(shape(sf["geometry"])), canonical_land(shape(af["geometry"]))
        sa, aa = polygon_area(sg), polygon_area(ag)
        ia = polygon_area(sg.intersection(ag))
        source_id_name_count = name_counts[code][source_name.casefold()]
        overlaps = []
        for pf in parent_features:
            area = polygon_area(sg.intersection(pf["geometry"]))
            if area > 0:
                overlaps.append((area, pf["name"]))
        overlaps.sort(reverse=True)
        atlas_parent_id = ap.get("parent_id")
        atlas_parent = hierarchy.get(atlas_parent_id, {}).get("name")
        top_parent = overlaps[0][1] if overlaps else None
        top_share = overlaps[0][0] / sa if overlaps else 0.0
        top_parent_feature = next((pf for pf in parent_features if pf["name"] == top_parent), None)
        parent_share = overlaps[0][0] / top_parent_feature["area_m2"] if overlaps and top_parent_feature and top_parent_feature["area_m2"] else 0.0
        name_match = source_name.casefold() == atlas_name.casefold()
        name_normal = norm_name(source_name) == norm_name(atlas_name)
        if code == "BFA":
            matches = roster_names.get(norm_name(source_name), [])
            roster_status = "unique-name-match" if len(matches) == 1 else "ambiguous-name-match" if matches else "not-found-in-extracted-incomplete-roster"
            classification = "insufficient-evidence"
            uncertainty = [
                "2007 native shapeID-to-current-commune official code/crosswalk was not found.",
                "INSD 2019 Annex 6 states 351 communes; reproducible text extraction currently recovers only 342 rows, so nonmatches are not evidence of absence.",
                "The 2017 ADM2 largest-overlap province is a spatial comparator, not a legal parent identifier.",
                "MATD's 2025 reorganization summary provides counts, not commune-level continuity or geometry.",
            ]
        else:
            civic = civ_roster[identity]
            current_matches = [f["properties"] for f in cntig_features
                               if norm_name(repair_source_text(f["properties"].get("admin3Name", ""))) == norm_name(atlas_name)
                               and norm_name(f["properties"].get("admin1Name", "")) == norm_name("Cavally")]
            if len(current_matches) > 1:
                raise SystemExit(f"Non-unique official CNTIG name/region match for {identity}")
            current_iou = None
            if current_matches:
                current_feature = next(f for f in cntig_features if f["properties"] is current_matches[0])
                cg = canonical_land(shape(current_feature["geometry"]))
                ci = polygon_area(sg.intersection(cg))
                cu = polygon_area(sg.union(cg))
                current_iou = ci / cu if cu else 0.0
            matches = [civic] if civic["name_match"] in ("match", "current-2026-government-confirmed-variant") else []
            roster_status = civic["name_match"]
            classification = "correction-needed" if len(current_matches) == 1 else "insufficient-evidence"
            uncertainty = [
                "2021 geoBoundaries layer labels all 510 records Departments but has no per-feature official code or department parent.",
                "The retained CNTIG/OCHA service identifies admin3Name as sub-prefecture and admin2Name as department; its 2018–2023 reference period and 2025 service edit do not establish a statutory code crosswalk or legal boundary date.",
                "The 2016 ADM2 overlay is a parent-name geometry comparison, not a 2021 statutory crosswalk.",
                "The 2019 AfDB report is older, project-specific evidence and is not needed for the current unique CNTIG name/region matches; retain it as dated context only.",
                "The official report PDF could not be retained after direct retrieval returned HTTP 403; the indexed official text roster was used, with restoration URL and limitation recorded.",
                "A separate 2026 government project report is local coverage and is not a full official-code or boundary crosswalk.",
                "The 510-feature current service versus DGAT's 509 created (475 open) count discrepancy remains unresolved; no complete-country claim follows.",
            ]
            if civic["name_match"] == "spelling-unresolved":
                uncertainty.append("The issue source spelling does not uniquely match the cited 2019 official spelling; no fuzzy reassignment is proposed.")
        rows.append({
            "id": identity,
            "country": "Burkina Faso" if code == "BFA" else "Côte d’Ivoire",
            "source_shapeID": sp["shapeID"],
            "source_name_raw": sp.get("shapeName"),
            "source_name_repaired": source_name,
            "atlas_name": atlas_name,
            "source_name_exact_after_repair": name_match,
            "source_name_normalized_match": name_normal,
            "source_name_duplicate_count_in_national_source": source_id_name_count,
            "atlas_parent_id": atlas_parent_id,
            "atlas_parent_name": atlas_parent,
            "largest_overlay_parent_name": top_parent,
            "largest_overlay_share_of_source_area": top_share,
            "source_shape_area_km2": sa / 1_000_000,
            "largest_overlay_parent_area_share": parent_share,
            "atlas_source_iou": ia / (aa + sa - ia),
            "atlas_component_count": component_count(shape(af["geometry"])),
            "source_component_count": component_count(shape(sf["geometry"])),
            "official_2019_name_roster_match_status": roster_status,
            "official_2019_department": (matches[0]["department"] if code == "CIV" and matches else None),
            "official_2019_subprefecture_name": (matches[0]["official_2019_subprefecture"] if code == "CIV" and matches else None),
            "official_cntig_current_match_count_name_region": (len(current_matches) if code == "CIV" else None),
            "official_cntig_current_admin3_name": (current_matches[0].get("admin3Name") if code == "CIV" and current_matches else None),
            "official_cntig_current_admin2_department": (current_matches[0].get("admin2Name") if code == "CIV" and current_matches else None),
            "official_cntig_current_admin1_region": (current_matches[0].get("admin1Name") if code == "CIV" and current_matches else None),
            "official_cntig_current_fid": (current_matches[0].get("FID") if code == "CIV" and current_matches else None),
            "official_cntig_2025_geometry_iou_wgs84": current_iou if code == "CIV" else None,
            "classification": classification,
            "uncertainty": uncertainty,
        })

positive = canonical_land(box(-2, 8, -1, 9))
positive_iou = polygon_area(positive.intersection(positive)) / polygon_area(positive.union(positive))
negative = translate(positive, xoff=10)
negative_iou = polygon_area(positive.intersection(negative)) / polygon_area(positive.union(negative))
if positive_iou != 1.0 or negative_iou != 0.0:
    raise SystemExit("Geometry controls failed")
control_dir = OWNED / "evidence/controls"
control_dir.mkdir(parents=True, exist_ok=True)
(control_dir / "geometry-positive-control.json").write_text(json.dumps({
    "method_id": "civ-cntig-cross-source-iou", "kind": "positive-control",
    "outcome": "passed", "identical_polygon_iou": positive_iou,
}, indent=2, sort_keys=True) + "\n")
(control_dir / "geometry-negative-control.json").write_text(json.dumps({
    "method_id": "civ-cntig-cross-source-iou", "kind": "negative-control",
    "outcome": "passed", "translated_disjoint_polygon_iou": negative_iou,
}, indent=2, sort_keys=True) + "\n")

groups = {}
for row in rows:
    groups[row["atlas_parent_id"]] = groups.get(row["atlas_parent_id"], 0) + 1
parent_status = []
for p in SCOPE["province_scopes"]:
    matched = [r for r in rows if r["atlas_parent_id"] == p["id"]]
    civ_current = [r for r in matched if r["country"] == "Côte d’Ivoire" and r["official_cntig_current_admin1_region"]]
    cavally_region_supported = (
        p["name"].casefold() == "cavally" and len(civ_current) == p["full_province_locations"] and
        all(norm_name(r["official_cntig_current_admin1_region"]) == norm_name(p["name"]) for r in civ_current)
    )
    parent_status.append({
        "id": p["id"], "name": p["name"], "scope_member_count": len(matched),
        "full_province_count": p["full_province_locations"], "partial": p["partial"],
        "countries": sorted({r["country"] for r in matched}),
        "official_cntig_admin1_region_match_count": len(civ_current),
        "classification": "justified" if cavally_region_supported else "insufficient-evidence",
        "reason": ("All 17 scoped members match the official CNTIG/OCHA admin1 region Cavally; Atlas region grouping is supported. The service separately gives four direct department labels, so Cavally is not asserted as each location's direct administrative parent." if cavally_region_supported else "Province-name grouping and source overlay do not establish current legal or operational parentage for every location."),
    })
result = {
    "version": 1,
    "issue": 468,
    "scope_batch_id": SCOPE["batch_id"],
    "baseline_commit": RECEIPT["baseline_commit"],
    "scope_count": len(rows),
    "scope_ids_sha256": SCOPE["member_location_ids_sha256"],
    "helper": METHOD,
    "controls": {"identical_positive_iou": positive_iou, "translated_negative_iou": negative_iou},
    "input_hashes": input_hashes,
    "national_feature_counts": {code: len(layers[(code, "ADM3")]) for code in ("BFA", "CIV")},
        "official_bfa_extracted_roster_rows": len(roster_rows),
        "official_bfa_stated_roster_rows": 351,
    "official_civ_cavally_2019_roster_rows": len(civ_roster),
    "official_cntig_current_feature_count": len(cntig_features),
    "official_cntig_cavally_unique_name_region_matches": sum(r["official_cntig_current_match_count_name_region"] == 1 for r in rows if r["country"] == "Côte d’Ivoire"),
    "official_cntig_cavally_geometry_iou_wgs84_min_median_max": [
        min(r["official_cntig_2025_geometry_iou_wgs84"] for r in rows if r["country"] == "Côte d’Ivoire"),
        sorted(r["official_cntig_2025_geometry_iou_wgs84"] for r in rows if r["country"] == "Côte d’Ivoire")[8],
        max(r["official_cntig_2025_geometry_iou_wgs84"] for r in rows if r["country"] == "Côte d’Ivoire"),
    ],
    "province_assessments": parent_status,
    "locations": rows,
    "summary": {
        "classifications": {k: sum(row["classification"] == k for row in rows) for k in ("justified", "correction-needed", "insufficient-evidence")},
        "source_atlas_name_exact_after_repair": sum(r["source_name_exact_after_repair"] for r in rows),
        "source_atlas_name_normalized_match": sum(r["source_name_normalized_match"] for r in rows),
        "largest_overlay_parent_matches_atlas_parent": sum(r["largest_overlay_parent_name"].casefold() == (r["atlas_parent_name"] or "").casefold() for r in rows if r["largest_overlay_parent_name"] and r["atlas_parent_name"]),
        "province_group_classifications": {k: sum(p["classification"] == k for p in parent_status) for k in ("justified", "correction-needed", "insufficient-evidence")},
        "atlas_multipart": sum(r["atlas_component_count"] > 1 for r in rows),
        "source_multipart": sum(r["source_component_count"] > 1 for r in rows),
        "iou_min": min(r["atlas_source_iou"] for r in rows),
        "iou_median": sorted(r["atlas_source_iou"] for r in rows)[len(rows)//2],
        "iou_max": max(r["atlas_source_iou"] for r in rows),
    },
}
out = OWNED / "derived-analysis.json"
out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
province_size_candidates = [
    {"id": r["id"], "name": r["atlas_name"], "parent_comparator": r["largest_overlay_parent_name"],
     "source_area_km2": r["source_shape_area_km2"], "share_of_comparator_area": r["largest_overlay_parent_area_share"]}
    for r in rows if r["largest_overlay_parent_area_share"] >= 0.5
]
generic_remainder_terms = ("remainder", "rest of", "other", "unspecified", "unknown")
generic_named = [r["id"] for r in rows if any(term in norm_name(r["source_name_repaired"]) for term in generic_remainder_terms)]
screen = {
    "version": 1, "issue": 468, "scope_ids_sha256": SCOPE["member_location_ids_sha256"],
    "scope_count": len(rows), "individual_row_assessments_path": str((OWNED / "derived-analysis.json").relative_to(ROOT)),
    "concerns": [
        {"id": "fragmented-city-territories", "status": "unresolved",
         "screen": "No authoritative city/urban extent source is pinned for the 221 IDs; an administrative name or component count cannot determine a fragmented city territory.",
         "follow_up": "Acquire dated official city/urban extents for any claimed locality in a future bounded source review."},
        {"id": "province-sized-locations", "status": "flagged-candidates",
         "screen": "Compared each of 221 source polygons to its largest-overlap pinned ADM2 comparator using WGS84 ellipsoidal area. A >=0.50 comparator-area share is a review trigger only, not a legal-size threshold.",
         "candidates": province_size_candidates, "follow_up_issue": 854,
         "limit": "BFA ADM2 is 2017; comparator geometry and an area ratio do not determine current commune identity."},
        {"id": "anonymous-administrative-remainders", "status": "name-screen-complete",
         "screen": "Searched all 221 repaired native source names for remainder/rest-of/other/unspecified/unknown labels.",
         "matching_ids": generic_named, "limit": "A name-only token scan cannot detect unnamed remainder polygons or omissions."},
        {"id": "disconnected-territories", "status": "component-screen-complete",
         "screen": "Per-row Atlas and native-source polygon component counts are in derived-analysis.json.",
         "atlas_multipart_ids": [r["id"] for r in rows if r["atlas_component_count"] > 1],
         "source_multipart_count": sum(r["source_component_count"] > 1 for r in rows),
         "limit": "Multipart status alone does not establish islands, enclaves, continuity or legal correctness."},
        {"id": "omitted-islands-and-territorial-completeness", "status": "unresolved",
         "screen": "Both area scopes are partial (204/351 BFA; 17/510 CIV by issue pins). No complete current authoritative national roster and insular territory audit exists in this packet.",
         "limit": "Issue/source counts cannot establish omissions or completeness."},
        {"id": "repeated-administrative-tiers", "status": "role-conflict-identified",
         "screen": "BFA 2007 ADM3 metadata has blank canonical level; CIV 2021 ADM3 collection label Departments conflicts with CNTIG/OCHA admin3=sub-prefecture and admin2=department. Per-location parent and role data are recorded in derived-analysis.json.",
         "limit": "No current BFA code/role crosswalk is established; CIV's official current reference source does not provide statutory shapeID continuity."},
        {"id": "oversized-groups", "status": "scope-count-screen-complete",
         "screen": "All 28 province/group scopes list exact owned count, full comparator count, partial flag and row-level parent evidence in derived-analysis.json.",
         "limit": "Counts are workload metadata and do not validate region size, omitted neighbors or boundary fit."},
        {"id": "weak-parent-relationships", "status": "mixed-evidence",
         "screen": "Largest-area ADM2 overlay names match the Atlas parent label for all 221. All 17 Cavally members also match official CNTIG/OCHA admin1 region and have individually recorded admin2 department; all BFA current code parents remain unresolved.",
         "limit": "BFA overlays use 2017 comparators; CIV Atlas region parents intentionally bypass direct department parentage."},
        {"id": "inconsistent-neighboring-units", "status": "cross-source-screen-complete-with-unresolved-lineage",
         "screen": "Per-ID names, source geometry overlap, source parent overlay, and multipart counts are recorded. CIV current CNTIG/OCHA geometry IoU is computed per row; BFA source vintage is 2007.",
         "limit": "No source count, overlay or shape similarity establishes current legal lineage, cross-country tier equivalence or whole-area boundary completeness."}
    ]
}
(OWNED / "acceptance-screen.json").write_text(json.dumps(screen, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
print(json.dumps(result["summary"], indent=2))
print(f"output_sha256={sha(out.read_bytes())}")
