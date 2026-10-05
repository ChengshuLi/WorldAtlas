#!/usr/bin/env python3
"""Reproduce the exact #442 Argentina ADM2 name/code/geometry screening."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform


ROOT = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
EXPECTED_ORIGINAL_SHA256 = "f35dae5a257302dea5bd1549ae135baf82e7ee7491918854c3db9bbdec890177"
EXPECTED_CURRENT_SHA256 = "5bdf36f66a5fd93d00b93b5cb28c1d71a0212848325612e84d3fbf5764870e87"
EXPECTED_ORIGINAL_BYTES = 69_702_323
EXPECTED_CURRENT_BYTES = 3_634_462

# CODPROV is the official INDEC two-digit province code. These are the six
# parents declared by this legacy packet, whose native roster is issue-pinned.
NAME_ALIASES = {
    "ezeiza": {"josemezeiza"},
    "coroneldemarinalrosales": {"coroneldemarinaleonardorosales"},
    "bolivar": {"sancarlosdebolivar"},
    "constitucion": {"villaconstitucion"},
}
PARENT_CODES = {
    "framework:province:buenos-aires:df466c06286c": "06",
    "framework:province:cordoba:beae6ba6b36e": "14",
    "framework:province:chaco:87e685fd273c": "22",
    "framework:province:formosa:6ec8d4a4a329": "34",
    "framework:province:la-pampa:d10ea068ae3a": "42",
    "framework:province:santa-fe:1f6b7cf8fad3": "82",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold()
    value = re.sub(r"^(departamento|departamentos|partido|partidos|dpto\.?|depto\.?)\s+", "", value)
    return "".join(ch for ch in value if ch.isalnum())


def read_collection(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if value.get("type") != "FeatureCollection" or not isinstance(value.get("features"), list):
        raise ValueError(f"Not a GeoJSON FeatureCollection: {path}")
    return value


def issue_scope(path: Path) -> tuple[dict, list[str]]:
    issue = json.loads(path.read_text(encoding="utf-8"))
    match = re.search(r"Machine-readable exact workload scope.*?```json\s*(.*?)\s*```", issue["body"], re.S)
    if not match:
        raise ValueError("Exact machine-readable workload scope is missing")
    scope = json.loads(match.group(1))
    ids = scope.get("member_location_ids")
    if issue.get("number") != 442 or not isinstance(ids, list) or len(ids) != 241 or len(set(ids)) != 241:
        raise ValueError("Unexpected #442 subject inventory")
    if scope.get("member_location_ids_sha256") != "63f3030ff6c3903e9578994651bf1a316c689d2568d263ed4813dd7171423ee6":
        raise ValueError("#442 subject digest changed")
    computed_digest = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    if computed_digest != scope["member_location_ids_sha256"]:
        raise ValueError("#442 exact subject ID digest does not reproduce")
    return scope, ids


def load_atlas(ids: list[str]) -> tuple[dict, dict, dict]:
    hierarchy = json.loads((ROOT / "data/hierarchy.json").read_text(encoding="utf-8"))
    hierarchy_by_id = {row["id"]: row for row in hierarchy}
    index = json.loads((ROOT / "data/world-index.json").read_text(encoding="utf-8"))
    features = {}
    for relative in index["parts"]:
        part = read_collection(ROOT / "data" / relative)
        for feature in part["features"]:
            identifier = feature.get("id") or feature["properties"].get("id")
            if identifier in ids:
                if identifier in features:
                    raise ValueError(f"Duplicate baseline identity: {identifier}")
                features[identifier] = feature
    if set(features) != set(ids):
        missing = sorted(set(ids) - set(features))
        raise ValueError(f"Missing baseline identities: {missing[:5]}")
    for identifier, feature in features.items():
        parent_id = feature["properties"].get("parent_id")
        if parent_id not in PARENT_CODES or parent_id not in hierarchy_by_id:
            raise ValueError(f"Unexpected #442 parent for {identifier}: {parent_id}")
    return features, hierarchy_by_id, {
        "world_index_sha256": sha256_file(ROOT / "data/world-index.json"),
        "hierarchy_sha256": sha256_file(ROOT / "data/hierarchy.json"),
    }


def geom_summary(geometry: dict, to_equal_area: Transformer) -> dict:
    geom = shape(geometry)
    if geom.is_empty or geom.geom_type not in ("Polygon", "MultiPolygon"):
        return {"geometry_type": geom.geom_type, "valid": geom.is_valid, "usable": False}
    projected = transform(to_equal_area.transform, geom)
    parts = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    return {
        "geometry_type": geom.geom_type,
        "component_count": len(parts),
        "valid": bool(geom.is_valid),
        "area_km2_equal_area": projected.area / 1_000_000 if geom.is_valid else None,
        "projected": projected if geom.is_valid else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.resolve().parent != OWNED.resolve():
        raise ValueError("Output must be written directly under the issue-owned directory")
    if args.original.stat().st_size != EXPECTED_ORIGINAL_BYTES or sha256_file(args.original) != EXPECTED_ORIGINAL_SHA256:
        raise ValueError("Pinned 2020 geoBoundaries LFS source bytes differ")
    if args.current.stat().st_size != EXPECTED_CURRENT_BYTES or sha256_file(args.current) != EXPECTED_CURRENT_SHA256:
        raise ValueError("Dated IGN capture differs; retain it as a separate source vintage")

    pinned_scope, ids = issue_scope(args.issue)
    atlas, parents, baseline_hashes = load_atlas(ids)
    original = read_collection(args.original)["features"]
    current = read_collection(args.current)["features"]
    original_by_id = {f.get("properties", {}).get("shapeID"): f for f in original}
    if len(original_by_id) != len(original):
        raise ValueError("Original source has missing or duplicate shapeID")
    current_by_code = defaultdict(list)
    for f in current:
        p = f.get("properties", {})
        current_by_code[str(p.get("CODPROV", ""))].append(f)
    codes = [str(f.get("properties", {}).get("CODINDEC", "")).strip() for f in current]
    blank_code_features = [f for f in current if not str(f.get("properties", {}).get("CODINDEC", "")).strip()]
    nonblank_codes = [code for code in codes if code]
    if len(current) != 529 or len(nonblank_codes) != 526 or len(set(nonblank_codes)) != len(nonblank_codes) or len(blank_code_features) != 3:
        raise ValueError("Unexpected IGN roster; expected 529 features, 526 unique nonblank INDEC codes, and 3 blank-code records")

    to_equal_area = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)
    rows = []
    positive_controls = []
    negative_controls = []
    for identifier in sorted(ids):
        original_id = identifier.split(":")[-1]
        source = original_by_id.get(original_id)
        if source is None:
            raise ValueError(f"Scoped identity absent from original source: {identifier}")
        source_name = source["properties"].get("shapeName", "")
        atlas_props = atlas[identifier]["properties"]
        parent_id = atlas_props["parent_id"]
        parent_name = parents[parent_id]["name"]
        province_code = PARENT_CODES[parent_id]
        candidates = []
        for f in current:
            p = f["properties"]
            names = {canonical(str(p.get("NAM", ""))), canonical(str(p.get("FNA", "")))}
            aliases = NAME_ALIASES.get(canonical(source_name), {canonical(source_name)})
            if aliases & names:
                candidates.append(f)
        left = geom_summary(source["geometry"], to_equal_area)
        candidate_scores = []
        if len(candidates) > 1 and left["valid"]:
            for candidate in candidates:
                candidate_geom = geom_summary(candidate["geometry"], to_equal_area)
                score = None
                if candidate_geom["valid"]:
                    union = left["projected"].union(candidate_geom["projected"]).area
                    score = left["projected"].intersection(candidate_geom["projected"]).area / union if union else None
                candidate_scores.append((score, candidate))
            positive = sorted((item for item in candidate_scores if item[0] is not None and item[0] > 0), key=lambda item: item[0], reverse=True)
            if positive and positive[0][0] >= 0.95 and (len(positive) == 1 or positive[0][0] > positive[1][0] + 1e-9):
                candidates = [positive[0][1]]
        status = "matched-name-and-parent-code" if len(candidates) == 1 and str(candidates[0]["properties"].get("CODPROV", "")).strip() == province_code else (
            "matched-name-parent-code-mismatch" if len(candidates) == 1 else ("unmatched" if not candidates else "ambiguous"))
        current_feature = candidates[0] if len(candidates) == 1 else None
        right = geom_summary(current_feature["geometry"], to_equal_area) if current_feature else None
        iou = None
        if right and left["valid"] and right["valid"]:
            a = left["projected"]
            b = right["projected"]
            union = a.union(b).area
            if union > 0:
                iou = a.intersection(b).area / union
        row = {
            "id": identifier,
            "baseline_name": source_name,
            "parent_id": parent_id,
            "parent_name": parent_name,
            "province_code": province_code,
            "match_status": status,
            "assessment_classification": "correction-needed" if status == "matched-name-parent-code-mismatch" else "insufficient-evidence",
            "assessment_finding": ("Exact normalized-name identity candidate has a current IGN province code different from the frozen atlas parent; propose a source-backed parent assignment review, no hierarchy edit in this packet." if status == "matched-name-parent-code-mismatch" else "This row remains insufficient-evidence for geographic certification. A source/name/code match is a present-day identity cross-check only; source completeness, precise legal boundary, reuse rights/vintage, and suitability as a general-purpose geographic location remain unverified."),
            "current_name": current_feature["properties"].get("NAM") if current_feature else None,
            "current_geographic_name": current_feature["properties"].get("FNA") if current_feature else None,
            "current_indec_code": current_feature["properties"].get("CODINDEC") if current_feature else None,
            "candidate_count": len(candidates),
            "ambiguous_candidates": [{"name": f["properties"].get("NAM"), "geographic_name": f["properties"].get("FNA"), "province_code": str(f["properties"].get("CODPROV", "")).strip(), "indec_code": f["properties"].get("CODINDEC")} for f in candidates] if len(candidates) > 1 else [],
            "current_province_code": str(current_feature["properties"].get("CODPROV", "")).strip() if current_feature else None,
            "parent_code_agrees": bool(current_feature and str(current_feature["properties"].get("CODPROV", "")).strip() == province_code),
            "parent_handoff": ("Candidate is framework:province:salta:7e3f9095353a, but this moves membership from the Argentina Northeast area into Argentina Northwest; coordinate with #441 and #943 before any change." if current_feature and str(current_feature["properties"].get("CODPROV", "")).strip() == "86" and province_code != "86" else ("Code 30 indicates Entre Ríos, but no Entre Ríos province ID is a direct child of the frozen Argentina Northeast area; resolve the Level 4 area roster with #441 before creating or moving a parent." if current_feature and str(current_feature["properties"].get("CODPROV", "")).strip() == "30" and province_code != "30" else None)),
            "current_unit_type": current_feature["properties"].get("Tipo_de_Un") if current_feature else None,
            "current_division_type": current_feature["properties"].get("Tipo_de_di") if current_feature else None,
            "baseline_geometry": {k: v for k, v in left.items() if k != "projected"},
            "current_geometry": ({k: v for k, v in right.items() if k != "projected"} if right else None),
            "equal_area_iou": round(iou, 9) if iou is not None else None,
            "geometry_limit": "Planar intersection in EPSG:6933 after transforming generalized 0.001-degree-offset/five-decimal IGN output; triage only, not cadastral or legal validation.",
        }
        rows.append(row)
        if source_name == "Chacabuco" and parent_id == "framework:province:chaco:87e685fd273c":
            positive_controls.append(row)
            wrong_parent_candidates = [f for f in current_by_code["14"] if canonical(source_name) in {
                canonical(str(f["properties"].get("NAM", ""))), canonical(str(f["properties"].get("FNA", "")))}]
            negative_controls.append({"id": identifier, "wrong_province_code": "14", "candidate_count": len(wrong_parent_candidates)})

    if len(rows) != len(ids) or len(positive_controls) != 1 or not negative_controls or negative_controls[0]["candidate_count"] != 0:
        raise ValueError("Scope or positive/negative province-parent control failed")

    counts = Counter(row["match_status"] for row in rows)
    ious = [row["equal_area_iou"] for row in rows if row["equal_area_iou"] is not None]
    summary = {
        "version": 1,
        "issue": 442,
        "scope_count": len(rows),
        "issue_scope_location_count": pinned_scope["location_count"],
        "scope_subject_sha256": pinned_scope["member_location_ids_sha256"],
        "baseline_commit": "b8c0eadc86cf2992719393e7c90858a2b58fcff5",
        "baseline_input_hashes": baseline_hashes,
        "original_source": {"file_bytes": args.original.stat().st_size, "sha256": sha256_file(args.original), "feature_count": len(original)},
        "current_source": {"file_bytes": args.current.stat().st_size, "sha256": sha256_file(args.current), "feature_count": len(current)},
        "current_source_roster": {"unique_nonblank_indec_codes": len(set(nonblank_codes)), "blank_code_feature_count": len(blank_code_features), "blank_code_feature_names": sorted(str(f.get("properties", {}).get("NAM", "")) for f in blank_code_features)},
        "source_join_status_counts": dict(sorted(counts.items())),
        "individual_assessment_counts": dict(sorted(Counter(row["assessment_classification"] for row in rows).items())),
        "geometry_results": {
            "valid_pair_count": len(ious),
            "invalid_or_missing_pair_count": len(rows) - len(ious),
            "iou_lt_0_95_count": sum(value < 0.95 for value in ious),
            "iou_min": round(min(ious), 9) if ious else None,
            "iou_median": round(sorted(ious)[len(ious) // 2], 9) if ious else None,
            "iou_max": round(max(ious), 9) if ious else None,
        },
        "component_review": {
            "source_multipart_count": sum(row["baseline_geometry"].get("component_count", 1) > 1 for row in rows),
            "source_multipart_rows": [{"id": row["id"], "name": row["baseline_name"], "components": row["baseline_geometry"].get("component_count")} for row in rows if row["baseline_geometry"].get("component_count", 1) > 1],
            "current_valid_multipart_count": sum(bool(row["current_geometry"] and row["current_geometry"].get("valid") and row["current_geometry"].get("component_count", 1) > 1) for row in rows),
            "current_valid_multipart_rows": [{"id": row["id"], "name": row["baseline_name"], "components": row["current_geometry"].get("component_count")} for row in rows if row["current_geometry"] and row["current_geometry"].get("valid") and row["current_geometry"].get("component_count", 1) > 1],
            "limit": "Multipart component counts flag geometry for named-island/fragment review only. They do not identify legal islands or prove every component is complete.",
        },
        "positive_controls": [{"id": row["id"], "current_indec_code": row["current_indec_code"], "match_status": row["match_status"]} for row in positive_controls],
        "negative_controls": negative_controls,
        "method": {
            "name_normalization": "Unicode NFKD, casefold, remove diacritics and non-alphanumeric characters; strip initial Departamento/Partido/Dpto./Depto. label. Explicit aliases: Ezeiza/José M. Ezeiza; Coronel de Marina L. Rosales/Coronel de Marina Leonardo Rosales; Bolívar/San Carlos de Bolívar; Constitución/Villa Constitución.",
            "candidate_partition": "Match normalized source name against the national roster; report whether current INDEC province code agrees with the frozen atlas parent. Ambiguous names remain unjoined.",
            "geometry_crs": "EPSG:6933 (WGS 84 / NSIDC EASE-Grid 2.0 Global, equal-area projection); GeoJSON axes interpreted longitude, latitude.",
            "geometry_method": "2020 geoBoundaries versus dated IGN 2026-10-05 generalized-source IoU. Repeated normalized names are disambiguated only when exactly one candidate has IoU >= 0.95. Invalid source geometries are preserved and not silently repaired.",
            "software": "Python 3.12; NumPy 2.3.5; Shapely 2.1.2; pyproj 3.7.2; requirements.txt",
            "limitations": ["IGN's service does not state layer vintage or reuse license.", "IGN geometry was requested with 0.001-degree maximum offset and five-decimal precision.", "Planar IoU is only a source-representation triage signal and does not adjudicate legal boundary, coastline, cadastral, or disconnected-land completeness.", "A name and INDEC code match does not prove the atlas's parent or geographic area is correct."],
        },
    }

    args.output.write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for row in rows) + "\n", encoding="utf-8")
    summary_path = OWNED / "comparison-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "summary": summary, "output": str(args.output), "summary_path": str(summary_path)}, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
