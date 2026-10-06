#!/usr/bin/env python3
"""Reproduce the bounded Kosovo four-ID identity and parent source review.

Reads immutable baseline Git blobs and the retained #999 evidence. Writes only
the two deterministic outputs in this issue-owned directory.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

BASELINE = "96f2a6d201236ba62f471535db240b123de60c09"
OWNED = Path("research/geography/southeast-b6-kosovo-4-2026-10-05")
SUBJECTS = [
    ("gb:XKX:ADM1:2360587B11570115914955", "District of Mitrovica", "framework:province:district-of-mitrovica:f4149a641a12", "Mitrovicë", ["Mitrovicë", "Mitrovica e Veriut", "Leposaviq", "Skenderaj", "Vushtrri", "Zubin Potok", "Zveçan"]),
    ("gb:XKX:ADM1:2360587B15813948402025", "District of Peja", "framework:province:district-of-peja:68d54986d0ba", "Pejë", ["Deçan", "Istog", "Klinë", "Pejë"]),
    ("gb:XKX:ADM1:2360587B89959345704230", "District of Prizren", "framework:province:district-of-prizren:5ea331ce3ec0", "Prizren", ["Dragash", "Prizren", "Suharekë", "Mamushë"]),
    ("gb:XKX:ADM1:2360587B9056373484571", "District of Gjakova", "framework:province:district-of-gjakova:86f71e89a8e2", "Gjakovë", ["Gjakovë", "Rahovec", "Malishevë", "Junik"]),
]
EXPECTED_PIN_HASHES = {
    "data/world-index.json": "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03",
    "data/hierarchy.json": "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b",
    "data/geographic-releases/current-manifest.json": "85075dd4eceebf5bc8e7b554fb4e1573aed2c5baae546ca21746643852c55b81",
    "data/macro-foundation/current-membership-inventory.json.gz": "db58f274debe5917f7fa21fdd2ab563f4761cfb673bd814b6402708fa10b06ab",
    "data/regional-review/regional-review-ef67318527f5f3a3/sources/geoBoundaries-GRC-ADM3.geojson.gz": "c0c518f1b87a09b52776accff437a4aae5c82061cc0127342305f777b56ac7b2",
    "data/regional-review/regional-review-c64d17e99f61d668/source/geoboundaries-9469f09/GRC/ADM3/geoBoundaries-GRC-ADM3-metaData.json": "0c0956d301dd1e04cb2586e27237e91d4509c9ecdb3471210989315cda013d2d",
    "data/geographic-releases/current-manifest.json": "85075dd4eceebf5bc8e7b554fb4e1573aed2c5baae546ca21746643852c55b81",
    "data/macro-foundation/macro-certificate.json": "f50f70fcb0756712ab7a7a388bc8cada093080518f07d3a6f7329758980ea81b",
    "data/macro-foundation/regional-handoffs.json.gz": "29af5204c1f28d2616d7d8d8bb18e5d718c8c1e6dab3637868b03a2381b5db2a",
    "data/macro-foundation/approved-boundary-decisions.json": "b67d5a3bcf8101cffb089c0262286378a80bb642cd6dde33f7721419227e3f18",
    "data/geography/part-9.json": "9a3bd8c8846cad2cd4ff681cf1f9341b876fdba4041214c52dcefecb5918aba6",
    "data/geography/part-28.json": "2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d",
    "data/geography/part-29.json": "077e3bdfb18a42318e27bad840bba823a5049ced449407584fb4b9be2ef67c7a",
}
SOURCE_PATH = "data/regional-review/regional-review-3c4fe25a21fa428d/source/gb/gb-XKX-ADM1.geojson"
METADATA_PATH = "data/regional-review/regional-review-3c4fe25a21fa428d/source/gb/XKX-ADM1-geoBoundaries-XKX-ADM1-metaData.json"
RESTORED_RESEARCH = "data/regional-review/followup-kosovo-422-district-source-20261005/RESEARCH.md"
RESTORATION = "data/regional-review/followup-kosovo-422-district-source-20261005/SOURCE_RESTORATION.md"
SOURCE_CROSSWALK = "research/geography/southeast-b6-kosovo-4-2026-10-05/prior-source-crosswalk.json"
KAS_TABLE = "research/geography/southeast-b6-kosovo-4-2026-10-05/prior-kas-extract.json"
PRIOR_CROSSWALK_SHA256 = "7339a45153c1a7e6f7c594b6c87be2f8b6294e7407ec63ab2598c839bb4cc5e7"
KAS_EXTRACT_SHA256 = "0f33913b6a36b057ecc9d51cbe7e14c11954fc1d3a89565eb63a64ffb4be6fff"
KAS_HASH = "aa322791fa3d683e8f054c57551437e754846b5094f4b413879011c152a6cb0f"
LAW_HASH = "4d45a816aaef692e52d037b121cb49f1a4cbcbb81f6fcc4332aa01583e2ba246"
ORIGINAL_LAW_HASH = "a44c1ed6b3e0ac3d2e102158122f47b008f79796c088b4bc0f03d6569a44afff"
CENSUS_HASH = "efe9dad731595df9ac5e5a87d2dd9fd76308db92713476251a5e3f9bec74a909"


def git_blob(root: Path, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), "show", f"{BASELINE}:{path}"])


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    world = json.loads(git_blob(root, "data/world-index.json"))
    hierarchy = json.loads(git_blob(root, "data/hierarchy.json"))
    parts = {p: json.loads(git_blob(root, p)) for p in ("data/geography/part-28.json",)}
    geojson_raw = git_blob(root, SOURCE_PATH)
    metadata_raw = git_blob(root, METADATA_PATH)
    prior_crosswalk_raw = (root / SOURCE_CROSSWALK).read_bytes()
    kas_raw = (root / KAS_TABLE).read_bytes()
    assert sha(prior_crosswalk_raw) == PRIOR_CROSSWALK_SHA256
    assert sha(kas_raw) == KAS_EXTRACT_SHA256
    prior_crosswalk = json.loads(prior_crosswalk_raw)
    kas = json.loads(kas_raw)
    geo = json.loads(geojson_raw)
    metadata = json.loads(metadata_raw)
    by_id = {f.get("id", f.get("properties", {}).get("shapeID")): f for f in geo["features"]}
    atlas = {f.get("id", f.get("properties", {}).get("id")): f for f in parts["data/geography/part-28.json"]["features"]}
    hierarchy_by_id = {x["id"]: x for x in hierarchy}
    kas_by_name = {x["name"]: x["municipalities"] for x in kas["regions"]}
    prior_by_id = {x["shape_id"]: x for x in prior_crosswalk["features"]}
    findings = []
    for sid, name, parent_id, region, municipalities in SUBJECTS:
        source_id = sid.split(":")[-1]
        source = by_id.get(source_id)
        current = atlas.get(sid)
        parent = hierarchy_by_id.get(parent_id)
        assert source and current and parent
        assert source.get("properties", {}).get("shapeName") == name
        assert source.get("properties", {}).get("shapeID") == source_id
        assert current["properties"]["name"] == name
        assert current["properties"]["metadata"]["original_id"] == source_id
        assert current["properties"]["parent_id"] == parent_id
        assert kas_by_name[region] == municipalities
        assert parent["metadata"]["source"] == "gb:XKX:ADM1"
        assert parent["metadata"]["child_count"] == 1
        cross = prior_by_id[source_id]
        assert cross["source_name"] == name and cross["kas_statistical_region_name"] == region
        findings.append({
            "subject_id": sid,
            "atlas_name": name,
            "parent": {"id": parent_id, "name": parent["name"], "level": parent["level"], "child_count": parent["metadata"]["child_count"], "status": "provisional same-name single-child container; legal parent purpose unresolved"},
            "source_feature": {"shape_id": source_id, "name": source["properties"]["shapeName"], "source_type": source["properties"].get("shapeType"), "source_group": source["properties"].get("shapeGroup"), "same_id_in_atlas": True},
            "source_metadata": {"canonical": metadata.get("boundaryCanonical"), "adm_unit_count": metadata.get("admUnitCount"), "boundary_year": metadata.get("boundaryYear"), "source_data_update_date": metadata.get("sourceDataUpdateDate"), "build_date": metadata.get("buildDate"), "boundary_source": metadata.get("boundarySource"), "boundary_license": metadata.get("boundaryLicense")},
            "kas_2022_proposal": {"region_name": region, "member_municipalities": municipalities, "member_count": len(municipalities), "administrative_region": False},
            "municipality_identity": "unresolved: label uniquely matches a proposed non-administrative statistical region and also a municipality in that group; no authorized same-vintage municipal vector was compared to this feature geometry",
            "polygon_identity": "unresolved: name/membership correspondence is not a geometric boundary match; historical polygon lineage does not identify OSM relations or source snapshot",
            "engineering_handoff": "Coordinate all seven Kosovo feature IDs across #999 and #1008 with the regional integrator before changing source-role resolution, parent semantics, area/code assignments or geometry. Obtain a lawful KCA municipal vector and explicit reuse terms; aggregate its 38 municipality polygons by the KAS 2022 table and compare with documented CRS, precision and per-region disagreement results.",
        })
    pin_checks = {}
    for path, expected in EXPECTED_PIN_HASHES.items():
        pin_checks[path] = {"sha256": sha(git_blob(root, path)), "expected": expected}
        assert pin_checks[path]["sha256"] == expected, (path, pin_checks[path])
    parent_rows = [hierarchy_by_id[x[2]] for x in SUBJECTS]
    assert all(x["metadata"]["child_count"] == 1 for x in parent_rows)
    assert len(geo["features"]) == 7 and int(metadata.get("admUnitCount")) == 48
    assert len(kas["regions"]) == 7 and kas["administrative_count"] == 38
    assert sum(len(r["municipalities"]) for r in kas["regions"]) == 38
    assert len({m for r in kas["regions"] for m in r["municipalities"]}) == 38
    assert len(prior_by_id) == len(geo["features"])
    assert {x["source_name"] for x in prior_crosswalk["features"]} == {f["properties"]["shapeName"] for f in geo["features"]}
    assert {x["kas_statistical_region_name"] for x in prior_crosswalk["features"]} == set(kas_by_name)
    result = {
        "version": 1,
        "issue": 1008,
        "baseline_commit": BASELINE,
        "source_inputs": {
            "geojson": {"path": SOURCE_PATH, "bytes": len(geojson_raw), "sha256": sha(geojson_raw), "feature_count": len(geo["features"])},
            "metadata": {"path": METADATA_PATH, "bytes": len(metadata_raw), "sha256": sha(metadata_raw), "reported_adm_unit_count": metadata.get("admUnitCount")},
            "prior_kas_extract": {"path": KAS_TABLE, "file_sha256": sha(kas_raw), "source_pdf_sha256": KAS_HASH, "administrative_municipalities": kas["administrative_count"], "proposal_regions": len(kas["regions"])},
            "prior_crosswalk": {"path": SOURCE_CROSSWALK, "sha256": sha(prior_crosswalk_raw)},
            "world_index": {"sha256": sha(git_blob(root, "data/world-index.json")), "entry_count": len(world)},
            "pinned_inputs": pin_checks,
        },
        "collection_controls": {
            "actual_payload_features": len(geo["features"]),
            "metadata_reported_count": metadata.get("admUnitCount"),
            "count_disagreement_preserved": len(geo["features"]) != metadata.get("admUnitCount"),
            "kas_unique_municipality_count": len({m for r in kas["regions"] for m in r["municipalities"]}),
            "seven_geo_names_match_seven_kas_region_names_only": True,
            "geometry_equivalence_tested": False,
        },
        "subjects": findings,
        "legal_and_boundary_context": {
            "current_consolidated_law": {"url": "https://gzk.rks-gov.net/ActDetail.aspx?ActID=107377", "publication_date": "2025-07-08", "retrieved": "2026-10-05", "sha256": LAW_HASH, "fact": "Municipalities are legal administrative units with boundaries defined through cadastral zones; no digital boundary geometry is supplied by this record."},
            "original_law": {"url": "https://gzk.rks-gov.net/ActDocumentDetail.aspx?ActID=2518", "publication_date": "2008-06-02", "retrieved": "2026-10-05", "sha256": ORIGINAL_LAW_HASH, "fact": "Original municipal-boundary statute; explicitly provides for separate North Mitrovica and South Mitrovica municipalities. Historic text does not by itself prove current vector geometry."},
            "kas_2024_census": {"url": "https://askapi.rks-gov.net/Custom/5f6ee57f-f5e1-4cac-86d4-6e68447a0f91.pdf", "retrieved": "2026-10-05", "sha256": CENSUS_HASH, "fact": "Publication map credits municipal boundaries to KCA 2024; map is not vector data or a reuse license."},
            "kca_geoportal": {"url": "https://geoportal.rks-gov.net/portal/main", "manual_url": "https://geoportal.rks-gov.net/assets/documents/Manual-Gjeoportal.pdf", "fact": "Official portal/manual identifies Administrative Units layers for municipal/local boundaries; no public downloadable vector and applicable data reuse terms were verified for this review."},
        },
        "neighboring_granularity": prior_crosswalk["neighboring_source_layers"],
        "conclusions": [
            {"status": "supported", "statement": "For each of the four names, the pinned 2021-representative seven-feature source has a same-name record as KAS's 2022 proposal for a Level III non-administrative region, and KAS lists multiple municipalities in each region.", "sources": ["geoBoundaries-xkx-adm1", "kas-2022-regions"]},
            {"status": "unresolved", "statement": "Whether each source polygon geometrically equals the matching KAS region, one or more current legal municipalities, or another boundary construction. No comparable lawful boundary vector was obtained.", "sources": ["geoBoundaries-xkx-adm1", "kca-boundary-authority"]},
            {"status": "unresolved", "statement": "The current-municipality identity of each individual polygon, especially whether Mitrovica includes both North and South municipalities; current law supports distinct legal municipalities but does not furnish comparable vector geometry.", "sources": ["kosovo-consolidated-law", "kosovo-original-law", "kas-2022-regions", "kca-boundary-authority"]},
            {"status": "unresolved", "statement": "Whether existing same-name province nodes represent legal parents; each is a retained single-child container whose evidence is derived from the same source feature.", "sources": ["atlas-pinned-records", "kas-2022-regions"]},
            {"status": "unresolved", "statement": "Original OSM snapshot, source relation IDs, explanation for metadata count 48, and reuse compatibility of this exact service-derived feature set.", "sources": ["geoBoundaries-xkx-adm1", "osm-license-record", "prior-source-restoration"]},
        ],
    }
    write_json(root / OWNED / "reproduction.json", result)
    write_json(root / OWNED / "findings.json", {"version": 1, "issue": 1008, "subjects": findings, "limits": result["conclusions"]})
    controls = [
        {"method_id": "pinned-source-and-role-review", "kind": "positive-control", "outcome": "passed", "evidence_path": "research/geography/southeast-b6-kosovo-4-2026-10-05/positive-control.json",
         "assertions": {"all_four_issue_ids_found_in_atlas_and_source": True, "all_four_source_names_match_retained_kas_regions": True, "all_four_parent_ids_match_and_are_single_child": True, "member_counts": [len(x[4]) for x in SUBJECTS]}},
        {"method_id": "pinned-source-and-role-review", "kind": "negative-control", "outcome": "passed", "evidence_path": "research/geography/southeast-b6-kosovo-4-2026-10-05/negative-control.json",
         "assertions": {"wrong_inference": "metadata admUnitCount is the number of features in the retained source payload", "observed_payload_features": len(geo["features"]), "observed_metadata_admUnitCount": int(metadata["admUnitCount"]), "wrong_inference_rejected": len(geo["features"]) != int(metadata["admUnitCount"]), "each_name_only_municipality_inference_rejected_by_multi_member_kas_roster": all(len(x[4]) > 1 for x in SUBJECTS)}},
    ]
    for control in controls:
        record = {k: control[k] for k in ("method_id", "kind", "outcome", "assertions")}
        write_json(root / control["evidence_path"], record)
    print(json.dumps({"status": "passed", "baseline": BASELINE, "subjects": len(findings), "pin_count": len(pin_checks), "outputs": ["findings.json", "reproduction.json", "positive-control.json", "negative-control.json"]}, indent=2))


if __name__ == "__main__":
    main()
