#!/usr/bin/env python3
"""Reproduce issue #408's pinned scope and row-level source/parent audit.

Run from the repository root with Python 3 standard library only:
  python3 data/regional-review/regional-review-173ccc74c2fd93ae/reproduce-scope.py

This verifies identity/source joins and framework assignment. It deliberately
does not certify current legal boundaries, completeness, or neighbor topology.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
from collections import Counter, defaultdict

PACKET = pathlib.Path("data/regional-review/regional-review-173ccc74c2fd93ae")
SCOPE_PATH = PACKET / "scope.json"
ISSUE_PATH = PACKET / "source/issue-408-api-snapshot.json"
SOURCE_PATH = pathlib.Path("data/regional-review/regional-review-9b38f58111efd323/sources/geoboundaries-chn-adm2-2017.geojson")
SOURCE_META_PATH = pathlib.Path("data/regional-review/regional-review-9b38f58111efd323/sources/geoboundaries-chn-adm2-metadata.json")
SOURCE_CITATION_PATH = pathlib.Path("data/regional-review/regional-review-9b38f58111efd323/sources/geoboundaries-citation-and-use.txt")
NE_DB_PATH = pathlib.Path("data/regional-review/regional-review-365cbd6478904888/source/natural-earth-admin1/ne_10m_admin_1_states_provinces.dbf")
BASELINE = "1451fb0788892ff9db6415e6ce6704bdd13d8f9a"
SOURCE_SHA256 = "2b68d8a808742fc6d7acd769584db960d8fc2c25b9f1d20e3e98c72e9f1c4d34"
METADATA_SHA256 = "7f609da61c856d022a9bf83b35fb271d78ebb5855ad2c1cdff337e51acdec58a"
CITATION_SHA256 = "f6ea7572bea6036c4cdcacf8c0ca7bf09098d4e600d19546d7432533e9a290d5"
NATURAL_EARTH_DBF_SHA256 = "7b3244333680d6aec58cc49bde9484177a0baa44c974ec9d371a8f7f1cdb5359"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob(path: str) -> bytes:
    return subprocess.run(["git", "show", f"{BASELINE}:{path}"], check=True, stdout=subprocess.PIPE).stdout


def baseline_hash(path: str) -> str:
    return sha(git_blob(path))


def feature_map(files):
    result = {}
    for path in files:
        doc = read_json(path)
        for feature in doc.get("features", []):
            props = feature["properties"]
            ident = props["id"]
            if ident in result:
                raise AssertionError(f"duplicate Atlas feature id {ident}")
            result[ident] = (feature, path.as_posix())
    return result


def coordinate_pairs(value):
    if isinstance(value, (list, tuple)) and len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
        yield (value[0], value[1])
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from coordinate_pairs(child)


def ring_counts(geometry):
    """Return polygon count and total rings for Polygon/MultiPolygon GeoJSON."""
    kind, coords = geometry["type"], geometry["coordinates"]
    polygons = [coords] if kind == "Polygon" else coords if kind == "MultiPolygon" else []
    return len(polygons), sum(len(polygon) for polygon in polygons)


def read_dbf_rows(path: pathlib.Path):
    """Read dBase III character fields needed for Natural Earth identity joins."""
    import struct
    raw = path.read_bytes()
    records = struct.unpack_from("<I", raw, 4)[0]
    header_len = struct.unpack_from("<H", raw, 8)[0]
    record_len = struct.unpack_from("<H", raw, 10)[0]
    fields, offset = [], 32
    while raw[offset] != 13:
        desc = raw[offset:offset + 32]
        name = desc[:11].split(b"\0", 1)[0].decode("ascii")
        length = desc[16]
        fields.append((name, offset - 31, length))
        offset += 32
    rows = []
    for index in range(records):
        rec = raw[header_len + index * record_len: header_len + (index + 1) * record_len]
        if rec[:1] == b"*":
            continue
        row = {}
        field_offset = 1
        for name, _, length in fields:
            row[name] = rec[field_offset:field_offset + length].decode("utf-8", "ignore").replace("\0", "").strip()
            field_offset += length
        rows.append(row)
    return raw, rows


def compact_json_array_fields(document, field_names):
    """Keep high-cardinality JSON records legible while limiting one row per line."""
    for field in field_names:
        marker = json.dumps(field) + ": ["
        start = document.index(marker) + len(marker) - 1
        depth, quoted, escaped, end = 0, False, False, None
        for index in range(start, len(document)):
            char = document[index]
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
                continue
            if char == '"':
                quoted = True
            elif char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    end = index
                    break
        if end is None:
            raise AssertionError(f"unterminated JSON array for {field}")
        # Recover the array value from the still-valid pretty JSON document.
        prefix = document[:start]
        suffix = document[end + 1:]
        array = json.loads(document[start:end + 1])
        compact = "[\n" + ",\n".join("    " + json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for item in array) + "\n  ]"
        document = prefix + compact + suffix
    return document


def main():
    scope = read_json(SCOPE_PATH)
    issue = read_json(ISSUE_PATH)
    body = issue["body"]
    if sha(body.encode("utf-8")) != scope["issue_body_sha256"]:
        raise AssertionError("saved issue body changed")
    blocks = re.findall(r"<!--\s*worldatlas-work:v1\s*(\{.*?\})\s*-->", body, re.S)
    if len(blocks) != 1:
        raise AssertionError(f"expected exactly one work contract, found {len(blocks)}")
    contract = json.loads(blocks[0])
    workload = scope["workload"]
    ids = workload["member_location_ids"]
    compact_ids = json.dumps(ids, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    digest = sha(compact_ids)
    if len(ids) != 200 or len(set(ids)) != 200 or digest != scope["member_location_ids_sha256"]:
        raise AssertionError("issue member roster/count/digest mismatch")
    if ids != workload["member_location_ids"] or contract.get("owned_paths") != ["data/regional-review/regional-review-173ccc74c2fd93ae/"]:
        raise AssertionError("contract ownership or issue roster mismatch")
    if contract.get("max_prs") != 2 or contract.get("mode") != "geography":
        raise AssertionError("unexpected issue work contract")

    # Verify the frozen release against the actual archived Git blobs, not the
    # current v6 hierarchy or current manifest.
    pins = {row["path"]: row for row in scope["baseline_files"]}
    verified_baseline = {}
    for path, row in pins.items():
        raw = git_blob(path)
        if sha(raw) != row["sha256"] or len(raw) != row["bytes"]:
            raise AssertionError(f"historical baseline bytes differ: {path}")
        verified_baseline[path] = {"sha256": sha(raw), "bytes": len(raw)}
    hierarchy_v5 = json.loads(git_blob("data/hierarchy.json"))
    units_v5 = {x["id"]: x for x in hierarchy_v5}
    handoffs = json.loads(__import__("gzip").decompress(git_blob("data/macro-foundation/regional-handoffs.json.gz")))
    projections = json.loads(__import__("gzip").decompress(git_blob("data/macro-foundation/current-membership-projection.json.gz")))
    release_doc = json.loads(__import__("gzip").decompress(git_blob("data/geographic-releases/releases-v5-gzip.json.gz")))
    region = workload["region_id"]

    def records(doc):
        if isinstance(doc, list):
            return doc
        for key in ("regions", "handoffs", "projections", "releases", "items"):
            if isinstance(doc.get(key), list):
                return doc[key]
        return []

    handoff_rows = handoffs.get("regions", [])
    projection_rows = projections.get("groups", [])
    release_rows = release_doc.get("releases", [])
    handoff = next((r for r in handoff_rows if r.get("region_id") == region), None)
    projection = next((r for r in projection_rows if r.get("id") == region), None)
    release_record = next((r for r in release_rows if r.get("id") == scope["release"]["id"]), None)
    if handoff is None or projection is None or release_record is None:
        raise AssertionError("pinned v5 handoff/projection/release record missing")
    # The geographic group stores the exact ordered scope including the two
    # compact territory IDs; the separate location table is sorted differently.
    if projection.get("member_location_ids") != ids:
        raise AssertionError("issue roster differs from archived v5 projection order")
    if release_record.get("hierarchy_sha256") != scope["release"]["hierarchy_sha256"] or release_record.get("footprints_sha256") != scope["release"]["footprints_sha256"]:
        raise AssertionError("archived v5 release descriptor does not match issue pins")
    envelope = handoff.get("envelope", {})
    if envelope.get("geometry_sha256") != scope["frozen_region_geometry_sha256"] or envelope.get("member_location_ids_sha256") != scope["frozen_region_member_ids_sha256"] or envelope.get("locations") != 200:
        raise AssertionError("archived v5 regional handoff envelope pins do not match issue")
    if scope["release"]["hierarchy_sha256"] != baseline_hash("data/hierarchy.json"):
        raise AssertionError("issue hierarchy pin differs from archived v5 hierarchy")
    if region not in json.dumps(handoff, ensure_ascii=False):
        raise AssertionError("v5 handoff does not identify issue region")

    atlas = feature_map(sorted(pathlib.Path("data/geography").glob("part-*.json")))
    missing = sorted(set(ids) - atlas.keys())
    if missing:
        raise AssertionError(f"missing scoped Atlas features: {missing[:5]}")
    extra = sorted((set(atlas) & set(ids)) - set(ids))
    if extra:
        raise AssertionError(f"unexpected scope features: {extra[:5]}")

    source_bytes = SOURCE_PATH.read_bytes()
    source = json.loads(source_bytes)
    source_features = source["features"]
    by_source_id = defaultdict(list)
    for feature in source_features:
        p = feature["properties"]
        by_source_id[p["shapeID"]].append(feature)
    source_hash = sha(source_bytes)
    source_meta_bytes = SOURCE_META_PATH.read_bytes()
    source_meta_hash = sha(source_meta_bytes)
    citation_bytes = SOURCE_CITATION_PATH.read_bytes()
    citation_hash = sha(citation_bytes)
    if source_hash != SOURCE_SHA256 or source_meta_hash != METADATA_SHA256 or citation_hash != CITATION_SHA256 or len(source_features) != 2391:
        raise AssertionError("retained geoBoundaries original/metadata/citation bytes differ from pins")
    ne_db_bytes, ne_db_rows = read_dbf_rows(NE_DB_PATH)
    if sha(ne_db_bytes) != NATURAL_EARTH_DBF_SHA256:
        raise AssertionError("retained Natural Earth DBF differs from pinned source hash")
    ne_by_code = {r["adm1_code"]: r for r in ne_db_rows if r.get("adm1_code")}
    if len(ne_by_code) != len([r for r in ne_db_rows if r.get("adm1_code")]):
        raise AssertionError("Natural Earth admin1 code uniqueness check failed")
    current_units = {x["id"]: x for x in read_json(pathlib.Path("data/hierarchy.json"))}
    area_by_id = {x["id"]: x for x in workload["area_scopes"]}
    parent_scope = {x["id"]: x for x in workload["province_scopes"]}
    rows = []
    area_counts = Counter()
    parent_counts = Counter()
    source_join_counts = Counter()
    v5_property_changes = []
    old_parts = {}
    for ident in ids:
        feature, path = atlas[ident]
        p = feature["properties"]
        parent_id = p.get("parent_id")
        parent = current_units.get(parent_id)
        if parent_id not in parent_scope or parent is None:
            raise AssertionError(f"parent missing/out of issue scope: {ident} -> {parent_id}")
        area_id = parent.get("parent_id")
        if area_id not in area_by_id:
            raise AssertionError(f"parent's area missing/out of issue scope: {ident} -> {area_id}")
        area_counts[area_id] += 1
        parent_counts[parent_id] += 1
        source_id = p.get("metadata", {}).get("source_id")
        matched_source = None
        source_feature = None
        name_match = None
        source_shape_id = None
        if ident.startswith("gb:CHN:ADM2:"):
            source_shape_id = ident.rsplit(":", 1)[1]
            matches = by_source_id.get(source_shape_id, [])
            source_join_counts[len(matches)] += 1
            if len(matches) != 1:
                raise AssertionError(f"source join not one-to-one for {ident}: {len(matches)}")
            source_feature = matches[0]
            matched_source = source_feature["properties"]
            name_match = p.get("name") == matched_source.get("shapeName")
            if not name_match or matched_source.get("shapeGroup") != "CHN" or matched_source.get("shapeType") != "ADM2":
                raise AssertionError(f"source ID/name/role mismatch for {ident}")
            source_status = "unique_id_and_name_match_to_retained_2017_source"
            source_role = "geoBoundaries CHN ADM2 / declared County Level"
        else:
            source_status = "separate_atlas_compact_territory_identity_not_in_CHN_ADM2_file"
            source_role = "Atlas compact territory aggregation; Natural Earth lineage declared"

        # Compare identity and footprint to the issue's frozen v5 geographic
        # parts, independently of the current v6 hierarchy. Properties may
        # legitimately contain later review metadata; those differences are
        # recorded rather than silently treated as a v5 fact.
        relpath = path
        if relpath not in old_parts:
            old_parts[relpath] = json.loads(git_blob(relpath))
        old_doc = old_parts[relpath]
        old_feature = next((f for f in old_doc.get("features", []) if f.get("properties", {}).get("id") == ident), None)
        if old_feature is None:
            raise AssertionError(f"feature absent from v5 part: {ident}")
        old_geom = old_feature.get("geometry")
        current_geom = feature.get("geometry")
        same_geometry = sha(json.dumps(old_geom, ensure_ascii=False, separators=(",", ":")).encode()) == sha(json.dumps(current_geom, ensure_ascii=False, separators=(",", ":")).encode())
        if not same_geometry:
            v5_property_changes.append({"id": ident, "geometry_changed_since_v5": True})
        source_geometry = source_feature.get("geometry") if source_feature else None
        source_coordinates = list(coordinate_pairs(source_geometry.get("coordinates"))) if source_geometry else []
        atlas_coordinates = list(coordinate_pairs(current_geom.get("coordinates"))) if current_geom else []
        source_point_count = len(source_coordinates) if source_geometry else None
        atlas_point_count = len(atlas_coordinates) if current_geom else None
        source_bbox = [min(x for x, y in source_coordinates), min(y for x, y in source_coordinates), max(x for x, y in source_coordinates), max(y for x, y in source_coordinates)] if source_coordinates else None
        source_polygons, source_rings = ring_counts(source_geometry) if source_geometry else (None, None)
        atlas_polygons, atlas_rings = ring_counts(current_geom) if current_geom else (None, None)
        source_4dp_geometry_match = None
        if source_geometry and current_geom:
            # Recursively round coordinate numbers while leaving GeoJSON structure intact.
            def rounded(value):
                if isinstance(value, (int, float)):
                    return round(value, 4)
                if isinstance(value, list):
                    return [rounded(x) for x in value]
                if isinstance(value, dict):
                    return {k: rounded(v) for k, v in value.items()}
                return value
            source_4dp_geometry_match = rounded(source_geometry) == rounded(current_geom)
        source_members = p.get("metadata", {}).get("source_member_ids", [])
        natural_earth_member_codes = [member for member in source_members if member in ne_by_code]
        natural_earth_member_names = [ne_by_code[member].get("name_en", "") or ne_by_code[member].get("name", "") for member in natural_earth_member_codes]
        manual_finding = None
        if ident == "gb:CHN:ADM2:17275852B41190306193582":
            manual_finding = "parent_correction_needed: 2017 geoBoundaries source feature Wenchangxian has a Hainan-island mainland bbox, while Atlas current framework parent is Sansha. Official Hainan 2024 yearbook and 2024 statistical bulletin treat Wenchang and Sansha as distinct units; Sansha is the island/reef/sea jurisdiction. Preserve geometry pending official boundary comparison; route parent/name correction to engineering."
        elif ident == "gb:CHN:ADM2:17275852B86431238150342":
            manual_finding = "historical_name_tier_review: source calls this Qiongshan City; current official Hainan administrative roster lists Haikou, not Qiongshan City. Current Haikou parent may be semantically right, but the 2017 source geometry must be reconciled to present Haikou district boundaries."
        elif ident == "gb:CHN:ADM2:17275852B93743910489906":
            manual_finding = "historical_name_tier_review: source calls this Dongfang Li Autonomous County; current official Hainan roster lists Dongfang City. Parent label reflects current city while source label/role does not."
        elif ident == "gb:CHN:ADM2:17275852B38939963469829":
            manual_finding = "label_review: source/Atlas romanization Chanzhoushi differs from official Hainan Statistical Yearbook's Danzhou."
        elif ident == "gb:CHN:ADM2:17275852B80309702523612":
            manual_finding = "label_review: source/Atlas romanization Shanyashi differs from official Hainan Statistical Yearbook's Sanya."
        correction_ids = {
            "gb:CHN:ADM2:17275852B41190306193582",
            "gb:CHN:ADM2:17275852B86431238150342",
            "gb:CHN:ADM2:17275852B93743910489906",
            "gb:CHN:ADM2:17275852B38939963469829",
            "gb:CHN:ADM2:17275852B80309702523612",
        }
        row_classification = "correction-needed" if ident in correction_ids else "insufficient-evidence"
        if ident in ("atlas:territory:HKG", "atlas:territory:MAC"):
            expected_code = "HKG" if ident.endswith("HKG") else "MAC"
            if len(natural_earth_member_codes) != (18 if expected_code == "HKG" else 1) or any(ne_by_code[x].get("adm0_a3") != expected_code for x in natural_earth_member_codes):
                raise AssertionError(f"Natural Earth source-member identity mismatch for {ident}")
        rows.append({
            "id": ident,
            "atlas_name": p.get("name"),
            "atlas_feature_path": path,
            "source_id": source_id,
            "source_role": source_role,
            "source_shape_id": source_shape_id,
            "source_shape_name": matched_source.get("shapeName") if matched_source else None,
            "source_join_status": source_status,
            "source_name_exact_match": name_match,
            "source_vintage": "2017 boundaryYear; source build 2023-12-12" if matched_source else "Undated modern reference",
            "source_geometry_type": source_geometry.get("type") if source_geometry else None,
            "atlas_geometry_type": current_geom.get("type") if current_geom else None,
            "source_vertex_count": source_point_count,
            "atlas_vertex_count": atlas_point_count,
            "source_bbox_wgs84_lonlat": source_bbox,
            "source_ring_count": source_rings,
            "atlas_ring_count": atlas_rings,
            "source_geometry_equals_atlas_after_4dp_rounding": source_4dp_geometry_match,
            "natural_earth_admin1_member_ids": natural_earth_member_codes,
            "natural_earth_admin1_member_names": natural_earth_member_names,
            "area_id": area_id,
            "area_name": area_by_id[area_id]["name"],
            "current_main_parent_id": parent_id,
            "current_main_parent_name": parent["name"],
            "scope_parent_expected_count": parent_scope[parent_id]["full_province_locations"],
            "current_parent_assignment_assessment": (
                "cross_border_planning_group_not_an_official_administrative_parent"
                if parent["name"] in ("Hong Kong–Shenzhen", "Macao–Zhuhai", "Guangzhou–Foshan")
                else "framework_parent_matches_issue_name; official row-specific present-day jurisdiction not independently proved"
            ),
            "geometry_unchanged_from_pinned_v5_feature": same_geometry,
            "current_legal_boundary_assessment": "insufficient_evidence_2017_generalized_source_is_not_a_current_official_legal_boundary_layer",
            "neighboring_granularity_assessment": "insufficient_evidence_no_independent_current_boundary_or_topological_neighbor_check",
            "row_finding": manual_finding,
            "classification": row_classification,
            "classification_basis": (
                "Sourced current-name/tier or parent discrepancy requires engineering crosswalk; boundary remains unverified."
                if row_classification == "correction-needed" else
                "No sourced row-specific present-day boundary, parent, completeness, and neighboring-granularity validation; source identity match alone is insufficient."
            ),
        })

    for area in workload["area_scopes"]:
        if area_counts[area["id"]] != area["owned_member_location_count"]:
            raise AssertionError(f"area count mismatch: {area['name']}")
    for parent_id, spec in parent_scope.items():
        if parent_counts[parent_id] != spec["full_province_locations"]:
            raise AssertionError(f"parent count mismatch: {spec['name']}")
    if sum(1 for r in rows if r["source_shape_id"] is not None) != 198:
        raise AssertionError("expected exactly 198 geoBoundaries rows")
    if source_join_counts != Counter({1: 198}):
        raise AssertionError(f"unexpected source join cardinality {source_join_counts}")
    hkg = next(r for r in rows if r["id"] == "atlas:territory:HKG")
    mac = next(r for r in rows if r["id"] == "atlas:territory:MAC")
    all_hkg_codes = sorted(r["adm1_code"] for r in ne_db_rows if r.get("adm0_a3") == "HKG")
    if sorted(hkg["natural_earth_admin1_member_ids"]) != all_hkg_codes:
        raise AssertionError("HKG Natural Earth aggregation does not equal the retained HKG admin1 rows")
    if mac["natural_earth_admin1_member_ids"] != ["MAC+00?"]:
        raise AssertionError("MAC Natural Earth member does not resolve to the retained Macau admin1 row")

    current_hierarchy_bytes = pathlib.Path("data/hierarchy.json").read_bytes()
    current_hierarchy_hash = sha(current_hierarchy_bytes)
    evaluation_commit = scope["current_main_comparison"]["main_commit"]
    evaluation_hierarchy_bytes = subprocess.run(
        ["git", "show", f"{evaluation_commit}:data/hierarchy.json"],
        check=True, stdout=subprocess.PIPE,
    ).stdout
    if sha(evaluation_hierarchy_bytes) != scope["current_main_comparison"]["current_hierarchy_sha256"] or current_hierarchy_hash != scope["current_main_comparison"]["current_hierarchy_sha256"]:
        raise AssertionError("current hierarchy differs from the explicitly pinned evaluation-main commit")
    source_meta = read_json(SOURCE_META_PATH)
    parent_assessments = []
    for parent_id, spec in sorted(parent_scope.items(), key=lambda item: item[1]["name"]):
        current = current_units.get(parent_id, {})
        metadata = current.get("metadata", {})
        semantic = metadata.get("semantic_review", {})
        name = spec["name"]
        area_name = next((r["area_name"] for r in rows if r["current_main_parent_id"] == parent_id), None)
        is_hainan = area_name == "Hainan"
        is_gba = name in ("Hong Kong–Shenzhen", "Guangzhou–Foshan", "Macao–Zhuhai")
        parent_assessments.append({
            "id": parent_id,
            "name": name,
            "area": area_name,
            "scoped_member_count": parent_counts[parent_id],
            "expected_member_count": spec["full_province_locations"],
            "classification": "correction-needed" if is_hainan else "insufficient-evidence",
            "purpose_classification": "justified" if is_gba else "insufficient-evidence",
            "purpose_basis": "Official 2019 Greater Bay Area outline identifies this as a cooperation pole; that supports planning purpose only, not administrative parentage or boundary." if is_gba else metadata.get("basis"),
            "source_role_and_vintage": "2017 geoBoundaries CHN ADM2 declared County Level; source has no per-feature official current parent code." if not is_gba else "Cross-border planning group; membership draws on HKG/MAC compact territory records and CHN ADM2 features.",
            "review_reasons": metadata.get("review_reasons", []),
            "remaining_semantic_review_reasons": semantic.get("remaining_reasons", []),
            "boundary_status": semantic.get("boundary_status", "not a legal administrative boundary" if is_gba else "open"),
            "classification_basis": "Current Hainan source set includes county-level units represented by a province-tier framework, plus known roster/parent discrepancies; engineering and authoritative current crosswalk needed." if is_hainan else ("Purpose supported as a planning pole, but identity membership, source lineage, boundaries, parent semantics, and neighboring granularity remain unverified." if is_gba else "Source role/vintage and scoped membership were inspected, but canonical parent source/role, row-level present-day parentage, boundaries, and neighbor consistency remain unverified."),
        })
    area_assessments = []
    for area in workload["area_scopes"]:
        name = area["name"]
        is_hainan = name == "Hainan"
        area_assessments.append({
            "id": area["id"], "name": name,
            "scoped_member_count": area_counts[area["id"]],
            "expected_member_count": area["full_area_location_count"],
            "classification": "correction-needed" if is_hainan else "insufficient-evidence",
            "purpose_basis": "Provincial geographic grouping; HKG/MAC inclusion is geographic aggregation and does not change political ownership." if name == "Guangdong" else "Province-level grouping as represented in the pinned framework.",
            "boundary_and_neighbor_review": "insufficient-evidence; current official GIS geometry, source lineage/reuse terms, and independent neighbor topology were not recovered.",
            "completeness_finding": "2023 official roster has 19 entries; issue scope has 18, omits Wuzhishan, and includes historical Qiongshan City source row." if is_hainan else "Issue member count matches pinned workload; that count does not prove geographic completeness or boundary correctness.",
        })

    multipart_rows = [r for r in rows if r["atlas_geometry_type"] == "MultiPolygon"]
    single_location_parents = [p for p in parent_assessments if p["scoped_member_count"] == 1]
    checklist_assessments = [
        {"topic": "fragmented_city_territories", "classification": "insufficient-evidence", "observed": [r["id"] for r in multipart_rows if r["atlas_name"] in ("Shenzhenshi", "Hong Kong")], "finding": "Multipart representation is present for Shenzhen and Hong Kong; no current official geometry was available to validate fragments or municipal subunits."},
        {"topic": "province_sized_locations", "classification": "insufficient-evidence", "observed": [], "finding": "No current official boundaries or reproducible area comparisons were available to determine whether any location is province-sized or otherwise anomalous."},
        {"topic": "anonymous_administrative_remainders", "classification": "correction-needed", "observed": [r["id"] for r in rows if r["id"] == "atlas:territory:MAC"], "finding": "The MAC aggregation includes one unnamed geoBoundaries predecessor in addition to Natural Earth MAC+00?; source identity and territorial correspondence of that predecessor need restoration and review."},
        {"topic": "disconnected_territories", "classification": "insufficient-evidence", "observed": [r["id"] for r in multipart_rows], "finding": "Four Atlas features are MultiPolygon (Hong Kong, Shenzhenshi, Napoxian, Jingxixian); component count/type alone cannot establish whether islands, enclaves, or detached mainland fragments are complete or legitimate."},
        {"topic": "omitted_islands_or_units", "classification": "correction-needed", "observed": ["framework:area:hainan:9b346a58616c"], "finding": "Official Hainan 2023 roster contains Wuzhishan, absent from this area's 18 pinned records; island/coastal completeness for the other areas remains unverified."},
        {"topic": "repeated_or_mismatched_tiers", "classification": "insufficient-evidence", "observed": [p["id"] for p in parent_assessments if p["area"] == "Hainan"], "finding": "All mainland source rows declare geoBoundaries County Level, while framework parent groups use province tier and declared prefecture-level purposes; Hainan directly groups county-level jurisdictions. Resolve parent/tier semantics without inferring from ADM numbers."},
        {"topic": "oversized_groups", "classification": "insufficient-evidence", "observed": [{"id": p["id"], "name": p["name"], "count": p["scoped_member_count"]} for p in parent_assessments if p["scoped_member_count"] >= 10], "finding": "Largest issue parent groups contain 10–13 scoped rows; counts are not a semantic criterion, and current source/neighbor evidence is insufficient to approve or reject these groupings."},
        {"topic": "weak_parent_assignments", "classification": "correction-needed", "observed": ["gb:CHN:ADM2:17275852B41190306193582"], "finding": "The Wenchangxian source feature is on Hainan Island but assigned to Sansha; official evidence supports a sourced parent correction handoff. Other row-level parent assignments lack current official crosswalks."},
        {"topic": "neighboring_unit_consistency", "classification": "insufficient-evidence", "observed": [r["id"] for r in rows], "finding": "No current official cross-border GIS layers, legal boundary bytes, or independent topology/scale comparison were recovered for Guangdong, Guangxi, Hainan, HKG, MAC, or neighboring jurisdictions."},
        {"topic": "single_location_parent_groups", "classification": "insufficient-evidence", "observed": [p["id"] for p in single_location_parents], "finding": "Eighteen groups contain a single scoped child (including Dongguan and Zhongshan); source role, coextensive tiers, and local parent semantics require individual review, not automatic rejection."},
    ]

    result = {
        "version": 1,
        "issue": 408,
        "scope_issue_body_sha256": scope["issue_body_sha256"],
        "pinned_scope_release": scope["release"],
        "pinned_v5_baseline_commit": BASELINE,
        "current_evaluation_commit": evaluation_commit,
        "issue_ordered_member_digest": digest,
        "scope_count": len(ids),
        "unique_scope_count": len(set(ids)),
        "atlas_feature_matches": len(ids),
        "v5_archived_pins_verified": verified_baseline,
        "v5_archived_projection_matches_exact_order": True,
        "v5_archived_handoff_envelope_matches_issue_geometry_and_member_pins": True,
        "geoBoundaries_source": {"path": SOURCE_PATH.as_posix(), "sha256": source_hash, "bytes": len(source_bytes), "metadata_path": SOURCE_META_PATH.as_posix(), "metadata_sha256": source_meta_hash, "citation_path": SOURCE_CITATION_PATH.as_posix(), "citation_sha256": citation_hash, "declared_boundary_id": source_meta.get("boundaryID"), "declared_boundary_year": source_meta.get("boundaryYear"), "declared_boundary_type": source_meta.get("boundaryType"), "declared_canonical_role": source_meta.get("boundaryCanonical"), "declared_license": source_meta.get("boundaryLicense"), "declared_source_data_update_date": source_meta.get("sourceDataUpdateDate"), "declared_build_date": source_meta.get("buildDate"), "upstream_source_url_as_retained": source_meta.get("boundarySourceURL"), "feature_count": len(source_features), "scope_join_count": 198, "unique_exact_shapeID_joins": 198, "atlas_name_matches": 198},
        "natural_earth_admin1_source": {
            "path": NE_DB_PATH.as_posix(),
            "sha256": sha(ne_db_bytes),
            "bytes": len(ne_db_bytes),
            "declared_source_repo_commit": "ca96624a56bd078437bca8184e78163e5039ad19",
            "dbf_records": len(ne_db_rows),
            "HKG_member_records": sum(1 for r in ne_db_rows if r.get("adm0_a3") == "HKG"),
            "MAC_member_records": sum(1 for r in ne_db_rows if r.get("adm0_a3") == "MAC"),
            "HKG_ids_match_Atlas_aggregation": True,
            "MAC_member_id_matches_Atlas_aggregation": True
        },
        "current_hierarchy_sha256": current_hierarchy_hash,
        "area_counts": dict(sorted((area_by_id[k]["name"], v) for k, v in area_counts.items())),
        "parent_counts": dict(sorted((parent_scope[k]["name"], v) for k, v in parent_counts.items())),
        "current_v6_hierarchy_rows": len(current_units),
        "geometry_changes_from_v5": v5_property_changes,
        "source_to_atlas_geometry_lineage": {
            "198_geoBoundaries_rows_measured": sum(1 for r in rows if r["source_shape_id"] is not None),
            "geometries_identical_after_4dp_rounding": sum(1 for r in rows if r["source_geometry_equals_atlas_after_4dp_rounding"] is True),
            "geometries_different_after_4dp_rounding": sum(1 for r in rows if r["source_geometry_equals_atlas_after_4dp_rounding"] is False),
            "source_vertices": sum(r["source_vertex_count"] or 0 for r in rows),
            "atlas_vertices": sum(r["atlas_vertex_count"] or 0 for r in rows),
            "source_minus_atlas_vertices": sum((r["source_vertex_count"] or 0) - (r["atlas_vertex_count"] or 0) for r in rows),
            "interpretation": "A difference establishes a transformation, not geographic error; no current official boundary comparison or topology validation was performed."
        },
        "rows": rows,
        "parent_assessments": parent_assessments,
        "area_assessments": area_assessments,
        "checklist_assessments": checklist_assessments,
        "findings": [
            "The 198 CHN records are reproducibly joined by exact geoBoundaries shapeID and exact Romanized shapeName against the retained 2017 CHN ADM2 source.",
            "Identity and exact labels do not independently establish present-day legal boundaries, local completeness, or neighbor granularity.",
            "The source declares County Level but supplies no per-feature administrative parent code; current framework parent assignment requires row-level official corroboration that this packet does not establish.",
            "The three paired Atlas framework parents are expressly planning-cooperation poles (Hong Kong–Shenzhen, Guangzhou–Foshan, Macao–Zhuhai), not administrative jurisdictions; do not interpret them as legal parentage.",
            "Hong Kong and Macao use separate compact territory aggregations and have different source lineage/role from CHN ADM2 rows.",
            "No boundary approval, complete-region certification, release repin, historical transfer, or production change is established."
        ],
        "scope_completeness_findings": [{
            "area": "Hainan",
            "issue_scope_location_count": area_counts[next(k for k,v in area_by_id.items() if v["name"] == "Hainan")],
            "official_roster_source": "Hainan Statistical Yearbook 2024, table 1-1 (administrative divisions, 2023); official 2024 statistical bulletin for current city/county groups",
            "official_roster_count": 19,
            "missing_current_unit": "Wuzhishan City",
            "duplicate_or_historical_unit_in_source_roster": "Qiongshan City (now within Haikou's district structure; current official 2023 roster has Haikou, not Qiongshan City)",
            "result": "current Hainan administrative roster is not fully represented by the 18 scoped 2017-source rows; confirm a current authoritative boundary/identity mapping before treating this area as complete"
        }],
    }
    out = compact_json_array_fields(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2), ("rows", "parent_assessments", "area_assessments", "checklist_assessments")) + "\n"
    target = PACKET / "row-assessments.json"
    target.write_text(out, encoding="utf-8")
    print(json.dumps({"result": "passed_with_explicit_geographic_limits", "rows": len(rows), "exact_source_joins": 198, "source_name_matches": 198, "parent_groups": len(parent_counts), "areas": dict((area_by_id[k]["name"], v) for k,v in area_counts.items()), "output": target.as_posix(), "output_sha256": sha(out.encode())}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise
