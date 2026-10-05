#!/usr/bin/env python3
"""Reproduce the exact-source hash lineage and 279 subject crosswalk for #981."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OWNED = ROOT / "data/regional-review/usa-adm2-lineage-428"
UPSTREAM = OWNED / "sources/upstream-2018"
PARENT = ROOT / "data/regional-review/regional-review-528e53393a4376b4"
ISSUE_SNAPSHOT = OWNED / "source/issue-api-response.json"
COMMIT_SNAPSHOT = OWNED / "source/upstream-commit-api.json"
FULL_PATH = UPSTREAM / "geoBoundaries-USA-ADM2.geojson"
SIMPLE_PATH = UPSTREAM / "geoBoundaries-USA-ADM2_simplified.geojson"
META_PATH = UPSTREAM / "geoBoundaries-USA-ADM2-metaData.json"
EXPECTED_COMMIT = "ec33c238d801aeb9dfe83e87025560b9383c695d"
EXPECTED_UPSTREAM_COMMIT = "9469f09592ced973a3448cf66b6100b741b64c0d"
CATALOG_ID = "gb:USA:ADM2"
SOURCE_PREFIX = "gb:USA:ADM2:"


def raw(path: Path) -> bytes:
    return path.read_bytes()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_desc(path: Path, relative: str | None = None) -> dict:
    data = raw(path)
    return {"path": relative or path.relative_to(ROOT).as_posix(), "bytes": len(data),
            "sha256": sha(data), "hash_kind": "file-bytes"}


def load(path: Path):
    return json.loads(raw(path))


def lfs(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.fullmatch(r"version https://git-lfs.github.com/spec/v1\noid sha256:([a-f0-9]{64})\nsize ([0-9]+)\n?", text)
    if not match:
        raise AssertionError(f"Not an exact Git LFS pointer: {path}")
    return {"pointer_sha256": sha(raw(path)), "pointer_bytes": len(raw(path)),
            "object_sha256": match.group(1), "object_bytes": int(match.group(2))}


def positions(geometry) -> int:
    count = 0
    def walk(value):
        nonlocal count
        if isinstance(value, list) and len(value) >= 2 and all(isinstance(x, (int, float)) for x in value[:2]):
            count += 1
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(geometry.get("coordinates") if geometry else None)
    return count


def main() -> None:
    subprocess.check_call(["git", "merge-base", "--is-ancestor", EXPECTED_COMMIT, "HEAD"], cwd=ROOT)
    baseline = EXPECTED_COMMIT

    issue = load(ISSUE_SNAPSHOT)
    block = re.search(r"<!-- worldatlas-work:v1\s*([\s\S]*?)\s*-->", issue["body"])
    if not block:
        raise AssertionError("Issue #981 snapshot has no work contract")
    contract = json.loads(block.group(1))
    quality = contract["evidence_quality"]
    if (issue["number"] != 981 or contract["mode"] != "geography" or contract["max_prs"] != 1 or
            contract["depends_on"] != [428] or contract["owned_paths"] != ["data/regional-review/usa-adm2-lineage-428/"] or
            quality["manifest_path"] != "data/regional-review/usa-adm2-lineage-428/evidence-quality.json" or
            quality["review_kind"] != "source"):
        raise AssertionError("Current issue contract differs from reviewed #981 scope")
    ids = quality["subject_ids"]
    if len(ids) != 279 or len(set(ids)) != 279 or any(not item.startswith(SOURCE_PREFIX) for item in ids):
        raise AssertionError("Issue contract must contain the exact 279 unique gb:USA:ADM2 subjects")
    expected_ids = set(ids)

    prior_scope = load(PARENT / "scope.json")
    prior_ids = prior_scope["member_location_ids"]
    if set(prior_ids) != expected_ids or len(prior_ids) != 279:
        raise AssertionError("#981 roster differs from closed #428 packet's exact 279 subjects")

    catalog = load(ROOT / "data/administrative-sources.json")[CATALOG_ID]
    full_bytes, simple_bytes, meta_bytes = raw(FULL_PATH), raw(SIMPLE_PATH), raw(META_PATH)
    full_hash, simple_hash, meta_hash = sha(full_bytes), sha(simple_bytes), sha(meta_bytes)
    full_pointer = lfs(UPSTREAM / "geoBoundaries-USA-ADM2.geojson.lfs-pointer")
    simple_pointer = lfs(UPSTREAM / "geoBoundaries-USA-ADM2_simplified.geojson.lfs-pointer")
    meta_pointer = lfs(UPSTREAM / "geoBoundaries-USA-ADM2-metaData.json.lfs-pointer")
    pointer_refs = {
        "all_zip": lfs(UPSTREAM / "geoBoundaries-USA-ADM2-all.zip.lfs-pointer"),
        "topojson": lfs(UPSTREAM / "geoBoundaries-USA-ADM2.topojson.lfs-pointer"),
    }
    parent_restoration = load(PARENT / "source/geoBoundaries-restoration.json")
    if ((PARENT / "source/geoBoundaries-USA-ADM2.geojson.lfs-pointer").read_bytes() !=
            (UPSTREAM / "geoBoundaries-USA-ADM2.geojson.lfs-pointer").read_bytes() or
            (PARENT / "source/geoBoundaries-USA-ADM2-metaData.json.lfs-pointer").read_bytes() !=
            (UPSTREAM / "geoBoundaries-USA-ADM2-metaData.json.lfs-pointer").read_bytes() or
            parent_restoration.get("restored_object_sha256") != full_hash or
            parent_restoration.get("restored_object_bytes") != len(full_bytes) or
            parent_restoration.get("pointer_sha256") != full_pointer["pointer_sha256"]):
        raise AssertionError("Current full/metadata LFS objects differ from the immutable #428 restoration evidence")
    for name, data, pointer in [("full GeoJSON", full_bytes, full_pointer),
                                ("simplified GeoJSON", simple_bytes, simple_pointer),
                                ("metadata", meta_bytes, meta_pointer)]:
        if sha(data) != pointer["object_sha256"] or len(data) != pointer["object_bytes"]:
            raise AssertionError(f"Retained {name} does not match its exact LFS object pointer")
    if catalog["sha256"] != simple_hash:
        raise AssertionError("Catalog digest no longer matches the retained simplified GeoJSON object")
    if catalog.get("simplifiedGeometryGeoJSON") != "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/USA/ADM2/geoBoundaries-USA-ADM2_simplified.geojson":
        raise AssertionError("Catalog simplified URL differs from the pinned upstream artifact")
    if catalog["sha256"] == full_hash or simple_hash == full_hash:
        raise AssertionError("Expected distinct full-resolution and simplified artifact byte hashes")

    full, simplified, metadata = load(FULL_PATH), load(SIMPLE_PATH), load(META_PATH)
    full_features, simple_features = full["features"], simplified["features"]
    def feature_index(features, label):
        result = {}
        for row in features:
            props = row.get("properties") or {}
            shape_id = props.get("shapeID")
            if not isinstance(shape_id, str) or shape_id in result:
                raise AssertionError(f"Missing/duplicate shapeID in {label}")
            result[shape_id] = row
        return result
    full_by_id = feature_index(full_features, "full GeoJSON")
    simple_by_id = feature_index(simple_features, "simplified GeoJSON")
    if len(full_features) != 3233 or len(full_by_id) != 3233 or metadata.get("admUnitCount") != "3233":
        raise AssertionError("Full GeoJSON feature/unique-ID count differs from upstream metadata")
    if len(simple_features) != 3233 or len(simple_by_id) != 3233 or set(full_by_id) != set(simple_by_id):
        raise AssertionError("Simplified GeoJSON inventory does not preserve the same 3,233 source IDs")
    if metadata.get("boundaryType") != "ADM2" or metadata.get("boundaryCanonical") != "Counties" or metadata.get("boundaryYear") != "2018":
        raise AssertionError("Unexpected upstream source role, tier, or vintage")

    index = load(ROOT / "data/world-index.json")
    all_seen: dict[str, list[str]] = {}
    feature_by_subject = {}
    containing_by_subject = {}
    indexed_paths = [ROOT / "data" / item for item in index["parts"]]
    if len(indexed_paths) != 36:
        raise AssertionError(f"Unexpected world-index part inventory size: {len(indexed_paths)}")
    for path in indexed_paths:
        if not path.is_file():
            raise AssertionError(f"Missing world-index feature part: {path.relative_to(ROOT)}")
        collection = load(path)
        for feature in collection.get("features", []):
            fid = feature.get("id") or (feature.get("properties") or {}).get("id")
            if fid in expected_ids:
                all_seen.setdefault(fid, []).append(path.relative_to(ROOT).as_posix())
                feature_by_subject[fid] = feature
                containing_by_subject[fid] = path.relative_to(ROOT).as_posix()
    if set(all_seen) != expected_ids or any(len(paths) != 1 for paths in all_seen.values()):
        raise AssertionError("One or more scoped Atlas IDs are missing or duplicated across world-index parts")

    hierarchy_rows = load(ROOT / "data/hierarchy.json")
    hierarchy = {row["id"]: row for row in hierarchy_rows}
    assessments_path = PARENT / "runs/verified-one/county-assessments.jsonl"
    assessments = [json.loads(line) for line in assessments_path.read_text(encoding="utf-8").splitlines() if line]
    by_assessment = {row["subject_id"]: row for row in assessments}
    if len(assessments) != 279 or set(by_assessment) != expected_ids:
        raise AssertionError("Closed #428 per-subject assessment does not exactly cover this scope")
    state_counts = Counter()
    subject_rows = []
    different_geometry = 0
    full_vertices = simple_vertices = 0
    subject_shape_ids = {item: item[len(SOURCE_PREFIX):] for item in ids}
    for subject_id in sorted(ids):
        shape_id = subject_shape_ids[subject_id]
        if shape_id not in full_by_id or shape_id not in simple_by_id:
            raise AssertionError(f"Scoped shapeID absent from upstream source variants: {shape_id}")
        full_row, simple_row = full_by_id[shape_id], simple_by_id[shape_id]
        fp, sp = full_row["properties"], simple_row["properties"]
        atlas = feature_by_subject[subject_id]
        props = atlas["properties"]
        meta = props.get("metadata") or {}
        parent_id = props.get("parent_id")
        parent = hierarchy.get(parent_id)
        assess = by_assessment[subject_id]
        if (fp.get("shapeGroup") != "USA" or fp.get("shapeType") != "ADM2" or
                sp.get("shapeName") != fp.get("shapeName") or props.get("name") != fp.get("shapeName") or
                meta.get("source_id") != CATALOG_ID or meta.get("source_role") != "Counties" or
                meta.get("reference_year") != "2018" or meta.get("original_id") != shape_id or
                not parent or parent.get("level") != "province" or parent.get("id") != parent_id or
                parent.get("name") not in ("Georgia", "Kentucky") or
                assess.get("source_shape_id") != shape_id or assess.get("source_shape_type") != "ADM2" or
                assess.get("atlas_source_role") != "Counties" or assess.get("parent_id") != parent_id):
            raise AssertionError(f"Source/Atlas/prior reviewed state-parent crosswalk differs for {subject_id}")
        expected_fips = {"Georgia": "13", "Kentucky": "21"}[parent["name"]]
        if assess.get("state_fips") != expected_fips:
            raise AssertionError(f"Prior #428 state-FIPS crosswalk disagrees with Atlas parent for {subject_id}")
        state_counts[parent["name"]] += 1
        if full_row.get("geometry") != simple_row.get("geometry"):
            different_geometry += 1
        full_vertices += positions(full_row.get("geometry"))
        simple_vertices += positions(simple_row.get("geometry"))
        subject_rows.append({
            "atlas_id": subject_id,
            "atlas_name": props["name"],
            "atlas_containing_file": containing_by_subject[subject_id],
            "atlas_parent_id": parent_id,
            "atlas_parent_name": parent["name"],
            "source_shape_id": shape_id,
            "source_shape_name": fp["shapeName"],
            "source_shape_group": fp["shapeGroup"],
            "source_shape_type": fp["shapeType"],
            "source_full_geometry_type": (full_row.get("geometry") or {}).get("type"),
            "source_simplified_geometry_type": (simple_row.get("geometry") or {}).get("type"),
            "source_geometry_identical_across_variants": full_row.get("geometry") == simple_row.get("geometry"),
            "prior_2018_census_geoid": assess.get("census_geoid_2018"),
            "prior_census_state_fips": assess.get("state_fips"),
            "parent_basis": "Pinned Atlas state parent, corroborated by #428's reviewed 2018 Census county crosswalk; GeoBoundaries shapeGroup is USA and has no state-parent field.",
            "boundary_adjudication": "not-established-by-this-source-lineage-packet"
        })
    if dict(state_counts) != {"Georgia": 159, "Kentucky": 120}:
        raise AssertionError(f"Unexpected state-parent scope counts: {dict(state_counts)}")

    commit = load(COMMIT_SNAPSHOT)
    if commit.get("sha") != EXPECTED_UPSTREAM_COMMIT or commit.get("commit", {}).get("committer", {}).get("date") != "2023-12-13T04:03:07Z":
        raise AssertionError("Upstream GitHub API commit snapshot differs from source packet pin")
    source_commit_date = commit["commit"]["committer"]["date"]

    baseline_paths = [
        "data/world-index.json", "data/hierarchy.json", "data/geographic-releases/current-manifest.json",
        "data/administrative-sources.json", "data/macro-foundation/current-membership-inventory.json.gz",
        "data/macro-foundation/review-index.json", "data/macro-foundation/regional-handoffs.json.gz",
        "data/macro-foundation/macro-certificate.json", "data/macro-foundation/approved-boundary-decisions.json",
        "data/regional-review/regional-review-528e53393a4376b4/scope.json",
        "data/regional-review/regional-review-528e53393a4376b4/findings.md",
        "data/regional-review/regional-review-528e53393a4376b4/runs/verified-one/county-assessments.jsonl",
        "data/regional-review/regional-review-528e53393a4376b4/source/geoBoundaries-restoration.json",
        "data/regional-review/regional-review-528e53393a4376b4/source/geoBoundaries-USA-ADM2.geojson.lfs-pointer",
        "data/regional-review/regional-review-528e53393a4376b4/source/geoBoundaries-USA-ADM2-metaData.json.lfs-pointer",
    ] + [f"data/{part}" for part in index["parts"]]
    baseline_paths = sorted(set(baseline_paths))
    baseline_files = [file_desc(ROOT / path, path) for path in baseline_paths]
    pins = quality["pins"]
    if any(not any(row["path"] == path and row["sha256"] == digest for row in baseline_files)
           for path, digest in pins.items()):
        raise AssertionError("Issue pin does not match an actual baseline file")
    source_paths = [
        FULL_PATH, SIMPLE_PATH, META_PATH,
        UPSTREAM / "geoBoundaries-USA-ADM2.geojson.lfs-pointer",
        UPSTREAM / "geoBoundaries-USA-ADM2_simplified.geojson.lfs-pointer",
        UPSTREAM / "geoBoundaries-USA-ADM2-metaData.json.lfs-pointer",
        UPSTREAM / "geoBoundaries-USA-ADM2-all.zip.lfs-pointer",
        UPSTREAM / "geoBoundaries-USA-ADM2.topojson.lfs-pointer",
    ]
    source_files = [file_desc(path) for path in source_paths]
    api_and_restoration_paths = [
        "source/issue-api-response.json", "source/upstream-commit-api.json", "source/api-retrieval.json",
        "sources/upstream-2018/retrieval.json", "sources/upstream-2018/simplified-object-retrieval.json"
    ]
    api_descriptors = [file_desc(OWNED / path, f"data/regional-review/usa-adm2-lineage-428/{path}")
                       for path in api_and_restoration_paths]
    input_record = {
        "version": 1,
        "issue": 981,
        "baseline_commit": baseline,
        "issue_contract_subject_ids_sha256_sorted_json": sha(json.dumps(sorted(ids), separators=(",", ":")).encode()),
        "prior_packet_subject_ids_sha256_sorted_json": sha(json.dumps(sorted(prior_ids), separators=(",", ":")).encode()),
        "baseline_files": baseline_files,
        "retained_source_files": source_files,
        "retrieval_and_prior_evidence_files": api_descriptors,
        "scope_note": "Source and boundary claims are limited to the exact 279 issue IDs; no regional approval or legal-boundary finding."
    }
    input_bytes = (json.dumps(input_record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (OWNED / "findings/input-manifest.json").write_bytes(input_bytes)
    input_hash = sha(input_bytes)

    subject_jsonl = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in subject_rows).encode()
    (OWNED / "findings/subject-crosswalk.jsonl").write_bytes(subject_jsonl)
    metrics = [
        ("full_national_feature_count", len(full_features), "features"),
        ("full_national_unique_shape_ids", len(full_by_id), "shape IDs"),
        ("simplified_national_feature_count", len(simple_features), "features"),
        ("simplified_unique_shape_ids", len(simple_by_id), "shape IDs"),
        ("full_to_simplified_matching_shape_ids", len(set(full_by_id) & set(simple_by_id)), "shape IDs"),
        ("scoped_exact_subject_count", len(ids), "subjects"),
        ("scoped_subjects_found_once_in_each_upstream_variant", len(subject_rows), "subjects"),
        ("scoped_subjects_found_once_across_world_index", len(all_seen), "subjects"),
        ("georgia_parent_subject_count", state_counts["Georgia"], "subjects"),
        ("kentucky_parent_subject_count", state_counts["Kentucky"], "subjects"),
        ("catalog_sha256_matches_simplified_object", int(catalog["sha256"] == simple_hash), "boolean"),
        ("catalog_sha256_matches_full_object", int(catalog["sha256"] == full_hash), "boolean"),
        ("full_source_vertex_count", full_vertices, "vertices"),
        ("simplified_source_vertex_count", simple_vertices, "vertices"),
        ("subject_geometries_differ_across_full_and_simplified", different_geometry, "subjects"),
    ]
    result = {
        "version": 1,
        "issue": 981,
        "retrieved_at_utc": "2026-10-05T15:44:27.025339Z",
        "baseline_commit": baseline,
        "upstream": {
            "repository": "wmgeolab/geoBoundaries",
            "commit": EXPECTED_UPSTREAM_COMMIT,
            "commit_date": source_commit_date,
            "metadata": {key: metadata.get(key) for key in ["boundaryID", "boundaryISO", "boundaryYear", "boundaryType", "boundarySource", "boundaryCanonical", "boundaryLicense", "admUnitCount", "sourceDataUpdateDate", "buildDate"]},
            "files": {
                "full_geojson": {"bytes": len(full_bytes), "sha256": full_hash, **full_pointer},
                "simplified_geojson": {"bytes": len(simple_bytes), "sha256": simple_hash, **simple_pointer},
                "metadata_json": {"bytes": len(meta_bytes), "sha256": meta_hash, **meta_pointer},
            "all_zip_lfs_pointer": pointer_refs["all_zip"],
                "topojson_lfs_pointer": pointer_refs["topojson"],
                "previous_full_object_restoration_receipt": parent_restoration
            },
            "catalog_record": {"source_id": CATALOG_ID, "sha256": catalog["sha256"],
                               "simplifiedGeometryGeoJSON": catalog.get("simplifiedGeometryGeoJSON"),
                               "gjDownloadURL": catalog.get("gjDownloadURL")},
            "digest_finding": "The catalog sha256 equals the exact LFS object hash for simplifiedGeometryGeoJSON (16249e8d...). It does not identify the full GeoJSON bytes (81fdd384...). The two artifacts retain the same 3,233 unique shapeIDs; many scoped geometries differ as expected for a simplified representation.",
            "license_limit": "Upstream metadata declares Public Domain and cites the U.S. Census MAF/TIGER database. This is recorded as the upstream product statement, not a legal boundary determination."
        },
        "scope": {
            "subject_count": len(ids),
            "subjects_sha256_sorted_json": sha(json.dumps(sorted(ids), separators=(",", ":")).encode()),
            "matches_closed_428_scope": True,
            "atlas_feature_occurrences_across_all_index_parts": len(all_seen),
            "atlas_containing_file_counts": dict(sorted(Counter(containing_by_subject.values()).items())),
            "state_parent_counts": dict(sorted(state_counts.items())),
            "shape_id_join_count_full": len(subject_rows),
            "shape_id_join_count_simplified": len(subject_rows),
            "prior_2018_census_crosswalk_rows_verified": len(assessments),
            "legal_or_current_boundary_adjudication": False,
            "neighboring_granularity": "geoBoundaries national ADM2 Counties set: 3,233 distinct shapeIDs; scoped Atlas county IDs parented to State-level framework records. The raw GeoBoundaries features carry shapeGroup=USA, not a per-feature state-parent field."
        },
        "input_manifest_sha256": input_hash,
        "subject_crosswalk_path": "findings/subject-crosswalk.jsonl",
        "subject_crosswalk_sha256": sha(subject_jsonl),
        "metrics": [{"id": name, "value": value, "unit": unit, "input_sha256": input_hash, "vintage": "baseline", "evaluation_commit": baseline} for name, value, unit in metrics],
        "conclusions": [
            {"status": "supported", "source_id": "geoboundaries-usa-adm2-2018", "text": "For this exact 279-ID scope, each Atlas source ID joins one-to-one to the corresponding full and simplified 2018 GeoBoundaries feature by exact shapeID; the national variants each contain 3,233 unique shapeIDs, matching metadata count."},
            {"status": "supported", "source_id": "geoboundaries-usa-adm2-2018", "text": "The repository catalog sha256 identifies the simplifiedGeometryGeoJSON LFS object, not the full-resolution GeoJSON. Both hashes and exact object sizes are verified against immutable commit 9469f09592ced973a3448cf66b6100b741b64c0d."},
            {"status": "unresolved", "source_id": "geoboundaries-usa-adm2-2018", "text": "The product count and hash lineage do not establish legal boundaries, currentness, universal county equivalence, shoreline/island completeness, or the wider custom region's meaning."}
        ],
        "engineering_handoff": "Preserve data/administrative-sources.json sha256=16249e8d795aaded6a72910a8c72115a073814b25ee902d61ccc9a9490c6641a; it matches the declared simplifiedGeometryGeoJSON artifact. If engineering needs an unambiguous checksum contract, document the hash target/path in a separate scoped engineering change. Do not repin this catalog field to the full GeoJSON digest based on the prior mismatch alone.",
        "boundary_note": "Per-subject County role/state parent is cross-referenced to the already reviewed #428 packet. This source-lineage audit does not repeat that packet's boundary comparison or convert Census TIGER/CBF overlap into legal correctness."
    }
    (OWNED / "findings/source-lineage-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": "passed", "baseline": baseline, "subjects": len(ids),
                      "features_full": len(full_features), "features_simplified": len(simple_features),
                      "catalog_sha_matches_simplified": catalog["sha256"] == simple_hash,
                      "atlas_part_counts": result["scope"]["atlas_containing_file_counts"],
                      "state_parent_counts": dict(state_counts), "different_subject_geometries": different_geometry,
                      "input_manifest_sha256": input_hash, "crosswalk_sha256": sha(subject_jsonl) }, indent=2))


if __name__ == "__main__":
    main()
