#!/usr/bin/env python3
"""Bind the five Greenland gap records to current selected Atlas targets.

This reuses retained physical-comparison results. It does not run source
coverage, classify land/water, or write production geography.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import shapely
from shapely.geometry import shape


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from evidence.geometry import METHOD as GEOMETRY_METHOD, VERSION as GEOMETRY_VERSION, land_area_m2

OUTPUT = Path(__file__).with_name("greenland-five-target-mapping.json")
COMMIT = "59acfabec9a22acebdb312010d37a43c8956ba8f"
ADMIN_COMPARISON_COMMIT = "12e90af4ff876e619a8eb0e6c1445821573500e6"
TARGET_ID = "gb:GRL:ADM1:42512837B82481266018751"
SOURCE_SUBJECT_ID = TARGET_ID
SOURCE_PRODUCT = "gb:GRL:ADM1"
IDS = {
    "physical-component:0441b8d2c49152a8ad4e5c8a0426eba450eb7298957b46eceadcac5c59c904ad",
    "physical-component:074e4f2fbdd5d53d94cd654c9737406325cfc851b36abb17940b3609187a2cc2",
    "physical-component:26f7658cfe2bed03c9cca108e8c2d08277f9efdd0a8143c308a7d6d0357662ee",
    "physical-component:f840c42d9967e89c74e47e4693392c474df5bfd4014d7c04acee9d04f58ed2f5",
    "physical-component:ff63cb9b104fd5baada0f18a8426c9d0e11ddb99ceed1392c7f6f715e4b27064",
}
EXPECTED_PHYSICAL_SHARDS = {
    "coordination/engineering/global-physical-comparison-20261006/results/components-001.jsonl.gz": (
        "516f23d0d48752b91cec80f245f49ea6f8ceff0f9b804ace46fd46f78d32faaf",
        "bae1e4f36090a32a42fd406178e9ab21e5d4fbfe893c36d3f7abbb1bd564ca4f",
    ),
    "coordination/engineering/global-physical-comparison-20261006/results/components-002.jsonl.gz": (
        "ae72b98588ea16ca58bd73bc6349fd497b813154d5a452dae881501dd28504a5",
        "b63f7b7a0675b9cbf8d2f7d5e7ee317497a5a63e8e70a41af5155dc36fce43bc",
    ),
    "coordination/engineering/global-physical-comparison-20261006/results/components-010.jsonl.gz": (
        "3bc42aca221488b5974803e82a4b6746291b4694acab5f61d4912e4849169416",
        "fce4e059f37697591a0bdf6259a46cdb2cdc1125c5c4c422d859aaa1ac284599",
    ),
    "coordination/engineering/global-physical-comparison-20261006/results/components-068.jsonl.gz": (
        "174658349676fc4be49a24013712c99a336280582d4a98d1693d3938939b482a",
        "f6eaf06605d49883fc07f879f57d25c7d37f664f62180f3a56376c93b7b46746",
    ),
    "coordination/engineering/global-physical-comparison-20261006/results/components-070.jsonl.gz": (
        "e86af0a7da7736ee728bceb856a7277becbbb93235d8785d23f416e90b82f47e",
        "e4e7add1fe4ee69e767cb710ede5075d6152ed4aa26aeb28e72e296e738a53dd",
    ),
}
EXPECTED_ADMIN_SHARDS = {
    "coordination/engineering/global-actionability-routing-20261007/results/admin-bindings-000.bin.gz": (
        "fa75a261900a8daecaf79d5ec52ff98c558c75113f125ce37b3a6cd823884e84",
        "d11952aaa416de1f46c27801b159b95487dfd7cb5b9e38db692b3334e4899a86",
    ),
    "coordination/engineering/global-actionability-routing-20261007/results/admin-bindings-001.bin.gz": (
        "1ef86a2583ec6abfd84f58d443c31b4884c567be263cdbb39de0e80cd2f8849f",
        "0b45b984c5c4636f622ff4f04d2b7174e8cf6c30d70bab63ddf9e2f25dc982c1",
    ),
    "coordination/engineering/global-actionability-routing-20261007/results/admin-bindings-007.bin.gz": (
        "06389d188e7b544f187a471c4ebfba937d8f07ccbfadba68d5f302888304b81f",
        "e1f9dad27239a5d5f8dd38c0132bc08ea28e8482d394a3fee9eb53ebdfcf30b6",
    ),
    "coordination/engineering/global-actionability-routing-20261007/results/admin-bindings-008.bin.gz": (
        "57a60c413f397633712a7f20663c4423cc4ab1abfb0f597790c66d385da72dc8",
        "91fe1012b01980cbcfc0f309f5d3fbfc321b0135c80a103f1dd5210c1a7a78db",
    ),
}
EXPECTED_TARGET_FILES = {
    "data/location-policy.json": "efab4528fd4b7b180815ef82de93480f490ef8fa48ad9ef32d1f9d76a64b7fb9",
    "data/administrative-sources.json": "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633",
    "data/geography/part-9.json": "9a3bd8c8846cad2cd4ff681cf1f9341b876fdba4041214c52dcefecb5918aba6",
    "data/regional-review/regional-review-a9f03b364bdefa4a/sources/geoboundaries-GRL-ADM1-9469f09.geojson": "a3132d9511f99c11a70aa40969567e29aa6f12d347117286025f87c6cdde86b0",
}


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{COMMIT}:{path}"])


def git_bytes_at(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{commit}:{path}"])


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: str):
    return json.loads(git_bytes(path))


def main() -> None:
    provenance_files = {}
    for path, expected in EXPECTED_TARGET_FILES.items():
        raw = git_bytes(path)
        actual = sha(raw)
        assert actual == expected, f"Pinned geography/source drift: {path} {actual}"
        provenance_files[path] = {"bytes": len(raw), "sha256": actual}

    policy = load_json("data/location-policy.json")["countries"]["GRL"]
    source = load_json("data/administrative-sources.json")[SOURCE_PRODUCT]
    geo = load_json("data/geography/part-9.json")
    target = next(f for f in geo["features"] if f.get("id") == TARGET_ID)
    assert target["properties"]["metadata"]["source_id"] == SOURCE_PRODUCT
    assert target["properties"]["metadata"]["original_id"] == "42512837B82481266018751"

    # Record every selected geography part consumed by the all-target overlap scan.
    geography_parts = []
    all_features = []
    for path in subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-tree", "-r", "--name-only", COMMIT, "data/geography"],
        text=True,
    ).splitlines():
        if not path.endswith(".json"):
            continue
        raw = git_bytes(path)
        geography_parts.append({"path": path, "bytes": len(raw), "sha256": sha(raw)})
        all_features.extend(json.loads(raw).get("features", []))
    selected_features = [f for f in all_features if f.get("geometry")]
    selected_targets = [
        f for f in selected_features
        if f.get("properties", {}).get("metadata", {}).get("source_id") == SOURCE_PRODUCT
    ]
    source_subject_targets = [
        f for f in selected_targets
        if f.get("properties", {}).get("metadata", {}).get("original_id") == "42512837B82481266018751"
    ]
    assert len(source_subject_targets) == 1 and source_subject_targets[0]["id"] == TARGET_ID
    target_geometry = shape(target["geometry"])

    # Reuse the fully retained comparison records; mapped-land support is the
    # candidate geometry here because each immutable row records source_covers_candidate=true.
    physical_records = {}
    physical_sources = {}
    for path, (encoded_sha, decoded_sha) in EXPECTED_PHYSICAL_SHARDS.items():
        raw = git_bytes(path)
        assert sha(raw) == encoded_sha, f"Encoded comparison shard drift: {path}"
        decoded = gzip.decompress(raw)
        assert sha(decoded) == decoded_sha, f"Decoded comparison shard drift: {path}"
        physical_sources[path] = {
            "encoded_bytes": len(raw), "encoded_sha256": encoded_sha,
            "decoded_bytes": len(decoded), "decoded_sha256": decoded_sha,
        }
        for ordinal, line in enumerate(decoded.splitlines()):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            component_id = row.get("component_id")
            if component_id in IDS:
                assert component_id not in physical_records, f"Duplicate physical row: {component_id}"
                assert any(rel.get("source_covers_candidate") is True for rel in row.get("query_relations", [])), component_id
                geom = row["complete_support"]["mapped_land_support"]["geometry"]
                physical_records[component_id] = {
                    "path": path, "ordinal_in_decoded_shard": ordinal,
                    "row_sha256": sha(line), "physical_status": row.get("physical_status"),
                    "route_status": row.get("status"), "source_vintage": row.get("source_vintage"),
                    "gshhg_support_area_m2": row["complete_support"]["mapped_land_support"]["area_m2"],
                    "source_covers_candidate": True, "geometry": geom,
                }
    assert set(physical_records) == IDS, f"Missing retained rows: {IDS-set(physical_records)}"

    # Bind the five candidate IDs to the already-computed administrative
    # comparison rows. No source coverage operation is repeated here.
    admin_rows = {}
    admin_sources = {}
    for path, (encoded_sha, decoded_sha) in EXPECTED_ADMIN_SHARDS.items():
        raw = git_bytes_at(ADMIN_COMPARISON_COMMIT, path)
        assert sha(raw) == encoded_sha, f"Encoded admin-binding shard drift: {path}"
        decoded = gzip.decompress(raw)
        assert sha(decoded) == decoded_sha, f"Decoded admin-binding shard drift: {path}"
        admin_sources[path] = {
            "encoded_bytes": len(raw), "encoded_sha256": encoded_sha,
            "decoded_bytes": len(decoded), "decoded_sha256": decoded_sha,
        }
        for ordinal, line in enumerate(decoded.splitlines()):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            component_id = row.get("component")
            if component_id not in IDS:
                continue
            assert component_id not in admin_rows, f"Duplicate admin-binding row: {component_id}"
            assert len(row.get("observations", [])) == 1, component_id
            observation = row["observations"][0]
            subject = observation.get("uniquely_covering_compatible_recorded_subject", {})
            assert observation.get("status") == "one-compatible-recorded-subject-uniquely-covers-component", component_id
            assert observation.get("source_products") == [SOURCE_PRODUCT], component_id
            assert subject.get("id") == SOURCE_SUBJECT_ID, component_id
            assert subject.get("original_feature_sha256") == "a66112308aa6b1ef4316884ab61c55c18c98ae65c902169be659fb816c9eef53", component_id
            assert subject.get("reference_year") == "2020", component_id
            assert observation.get("surface_status") == "unverified", component_id
            admin_rows[component_id] = {
                "path": path, "ordinal_in_decoded_shard": ordinal,
                "row_sha256": sha(line), "source_comparison_packet": observation.get("packet"),
                "source_comparison_status": observation.get("status"),
                "source_products": observation.get("source_products"),
                "unique_subject_id": subject.get("id"),
                "unique_subject_feature_sha256": subject.get("original_feature_sha256"),
                "source_reference_year": subject.get("reference_year"),
                "source_parent_id": subject.get("original_parent_id"),
                "surface_status": observation.get("surface_status"),
                "cause_status": observation.get("cause_status"),
                "unknowns": observation.get("unknowns"),
                "current_feature_sha256": observation.get("full_component_feature_sha256"),
                "current_geometry_sha256": observation.get("component_geometry_sha256"),
            }
    assert set(admin_rows) == IDS, f"Missing retained source-comparison rows: {IDS-set(admin_rows)}"

    # These are source-relative GSHHG mapped-land support geometries, not the
    # original whole candidate pointsets. Coverage does not establish equality.
    mapped_land_support_geometries = {cid: shape(record["geometry"]) for cid, record in physical_records.items()}
    rows = []
    for component_id in sorted(IDS):
        geometry = mapped_land_support_geometries[component_id]
        target_intersection = geometry.intersection(target_geometry)
        candidate_area_m2 = land_area_m2(geometry)
        target_intersection_area_m2 = land_area_m2(target_intersection) if not target_intersection.is_empty and target_intersection.geom_type in ("Polygon", "MultiPolygon") else 0.0
        positive_targets = []
        touching_targets = []
        for feature in selected_features:
            feature_geometry = shape(feature["geometry"])
            if not geometry.intersects(feature_geometry):
                continue
            intersection = geometry.intersection(feature_geometry)
            props = feature.get("properties", {})
            entry = {
                "selected_target_id": feature.get("id"),
                "name": props.get("name"),
                "intersection_area_m2": land_area_m2(intersection) if not intersection.is_empty and intersection.geom_type in ("Polygon", "MultiPolygon") else 0.0,
                "mapped_land_support_area_fraction": (land_area_m2(intersection) / candidate_area_m2) if not intersection.is_empty and intersection.geom_type in ("Polygon", "MultiPolygon") and candidate_area_m2 else 0.0,
            }
            if entry["intersection_area_m2"] > 0:
                positive_targets.append(entry)
            elif not intersection.is_empty:
                touching_targets.append(entry)
        rows.append({
            "component_id": component_id,
            "family_id": "gap-source-batch:cc585007c02df55450a8c0e6",
            "unique_recorded_source_product": SOURCE_PRODUCT,
            "unique_recorded_source_subject_id": SOURCE_SUBJECT_ID,
            "source_reference_year": "2020",
            "source_geometry_sha256": "a66112308aa6b1ef4316884ab61c55c18c98ae65c902169be659fb816c9eef53",
            "selected_target_id": TARGET_ID,
            "gshhg_mapped_land_support_area_m2": physical_records[component_id]["gshhg_support_area_m2"],
            "geometry_helper_mapped_land_support_area_m2": candidate_area_m2,
            "mapped_land_support_target_intersection_area_m2": target_intersection_area_m2,
            "mapped_land_support_target_intersection_fraction": target_intersection_area_m2 / candidate_area_m2 if candidate_area_m2 else None,
            "mapped_land_support_positive_area_targets": positive_targets,
            "mapped_land_support_boundary_contacts": touching_targets,
            "candidate_target_overlap_status": "not-computed-from-original-candidate-pointset",
            "physical_route_status": physical_records[component_id]["route_status"],
            "physical_comparison_status": physical_records[component_id]["physical_status"],
            "physical_authority": "unapproved",
            "source_vintage": physical_records[component_id]["source_vintage"],
            "retained_physical_comparison": {
                "path": physical_records[component_id]["path"],
                "ordinal_in_decoded_shard": physical_records[component_id]["ordinal_in_decoded_shard"],
                "row_sha256": physical_records[component_id]["row_sha256"],
                "source_covers_candidate": True,
            },
            "retained_admin_source_comparison": admin_rows[component_id],
        })
    pairwise = []
    ids_sorted = sorted(IDS)
    for i, left in enumerate(ids_sorted):
        for right in ids_sorted[i + 1:]:
            pairwise.append({
                "left": left, "right": right,
                "intersection_area_m2": land_area_m2(mapped_land_support_geometries[left].intersection(mapped_land_support_geometries[right]))
                if not mapped_land_support_geometries[left].intersection(mapped_land_support_geometries[right]).is_empty
                and mapped_land_support_geometries[left].intersection(mapped_land_support_geometries[right]).geom_type in ("Polygon", "MultiPolygon") else 0.0,
            })

    result = {
        "version": 1,
        "status": "admin-subject-mapping-with-source-support-overlay-only",
        "scope": "five Greenland components only; source-only evidence; no production writes",
        "source_commit": COMMIT,
        "geometry_method": {"helper_version": GEOMETRY_VERSION, **GEOMETRY_METHOD,
                            "topology_operation": "Shapely 2.1.2 intersection/covers in WGS84 longitude-latitude coordinates",
                            "overlay_scope": "retained GSHHG mapped-land support geometries against current selected geography; not exact original-candidate overlays",
                            "identity_limit": "source_covers_candidate=true proves source-relative coverage, not point-for-point equality with the whole candidate pointset"},
        "software": {"python": sys.version.split()[0], "shapely": shapely.__version__},
        "source_input_files": provenance_files,
        "selected_geography_parts": geography_parts,
        "source_metadata": {
            "product_id": SOURCE_PRODUCT,
            "reference_year": source["boundaryYearRepresented"],
            "administrative_level": source["boundaryType"],
            "canonical_role": source["boundaryCanonical"],
            "source_lineage": source["boundarySource"],
            "license": source["boundaryLicense"],
            "license_detail": source["licenseDetail"],
            "source_url": source["gjDownloadURL"],
            "source_file_sha256": "a3132d9511f99c11a70aa40969567e29aa6f12d347117286025f87c6cdde86b0",
            "consumed_subject_id": SOURCE_SUBJECT_ID,
            "consumed_subject_geometry_sha256": "a66112308aa6b1ef4316884ab61c55c18c98ae65c902169be659fb816c9eef53",
        },
        "selected_target": {
            "id": TARGET_ID,
            "name": target["properties"]["name"],
            "parent_id": target["properties"]["parent_id"],
            "source_id": target["properties"]["metadata"]["source_id"],
            "original_id": target["properties"]["metadata"]["original_id"],
            "source_role": target["properties"]["metadata"]["source_role"],
            "reference_year": target["properties"]["metadata"]["reference_year"],
            "selection_reason": target["properties"]["metadata"]["selection_reason"],
            "hierarchy_overlap": target["properties"]["metadata"]["hierarchy_overlap"],
            "geographic_overlap": target["properties"]["metadata"]["geographic_overlap"],
            "same_source_product_selected_locations": [
                {"id": f["id"], "name": f["properties"]["name"],
                 "original_id": f["properties"]["metadata"].get("original_id")}
                for f in selected_targets
            ],
            "same_source_subject_target_count": len(source_subject_targets),
        },
        "current_source_policy": policy,
        "physical_comparison_shards": physical_sources,
        "admin_comparison_commit": ADMIN_COMPARISON_COMMIT,
        "admin_comparison_shards": admin_sources,
        "candidate_rows": rows,
        "mapped_land_support_pairwise_intersections": pairwise,
        "limits": [
            "The unique admin-source witness identifies one stable existing administrative target; it does not approve this source as physical boundary authority.",
            "The saved target scan uses source-relative mapped-land support geometries, not the whole original candidate pointsets.",
            "Candidate-to-target overlap and pairwise candidate geometry relations remain unestablished by this scan.",
            "Mapped-land comparison geometry is source-relative to GSHHG 2.3.7; observation dates are heterogeneous and authority remains unapproved.",
            "No exact candidate-target overlay or native-cell measurement was performed; no repair geometry was proposed or written.",
            "This scan is source-support geometry only, not candidate conservation, fresh source coverage, or land/water adjudication.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "rows": len(rows), "target": TARGET_ID,
                      "target_mapping_count": len(source_subject_targets), "output": str(OUTPUT)}))


if __name__ == "__main__":
    main()
