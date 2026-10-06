#!/usr/bin/env python3
"""Reproduce #413 source-to-Atlas identity, roster, and scope reconciliation.

Uses only Python's standard library and retained source files. It deliberately
does not score polygon correctness: the official comparison sources do not
provide a rights-cleared, compatible-vintage vector boundary set for both
countries.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SCOPE = json.loads((ROOT / "source/issue-scope.json").read_text())
ISSUE = json.loads((ROOT / "source/issue-snapshot.json").read_text())
PART = json.loads((REPO / "data/geography/part-28.json").read_text())
HIERARCHY = json.loads((REPO / "data/hierarchy.json").read_text())
ADMIN_SOURCES = json.loads((REPO / "data/administrative-sources.json").read_text())
ATLAS = {f["properties"]["id"]: f["properties"] for f in PART["features"]}
HIERARCHY_IDS = {row["id"] for row in HIERARCHY}
MEMBERS = set(SCOPE["member_location_ids"])
EXPECTED_EASTERN_2022 = {
    "Chadiza", "Chama", "Chasefu", "Chipangali", "Chipata", "Kasenengwa",
    "Katete", "Lumezi", "Lundazi", "Lusangazi", "Mambwe", "Nyimba",
    "Petauke", "Sinda", "Vubwi",
}
EXPECTED_HARARE_2022 = {"Harare Urban", "Chitungwiza Urban", "Epworth"}
FULL_SOURCE_SHA256 = {
    # ZMB's 35,998,492-byte source exceeds the repository evidence input cap;
    # the exact Git LFS object was retrieved/hashed, then omitted with a pinned
    # restoration locator. The smaller Atlas-pinned simplified original stays.
    "ZMB": "ff4a4c8a92f7416b8457f423b339f2623b10f59410339911a0427fcee8434f17",
    "ZWE": "074a3632634b9448bb4043580fe7199e0b2f64ec68bd2f98932a2c68b3795b88",
}
BASELINE_COMMIT = "90f04d30cf773b5be538bc3d85d4d9051768deef"
BASELINE_FILE_SHA256 = {
    "data/geography/part-28.json": "2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d",
    "data/hierarchy.json": "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b",
    "data/administrative-sources.json": "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633",
}


def load_source(iso: str, suffix: str):
    path = ROOT / f"source/geoboundaries/geoBoundaries-{iso}-ADM2{suffix}"
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    for relpath, expected_hash in BASELINE_FILE_SHA256.items():
        assert sha256(REPO / relpath) == expected_hash, f"Baseline input changed: {relpath}"
    features = {
        "ZMB": load_source("ZMB", "_simplified.geojson")["features"],
        "ZWE": load_source("ZWE", "_simplified.geojson")["features"],
    }
    src_by_id = {
        iso: {f["properties"]["shapeID"]: f["properties"] for f in rows}
        for iso, rows in features.items()
    }
    assert len(MEMBERS) == 102 == SCOPE["location_count"]
    scope_hash = hashlib.sha256(json.dumps(sorted(SCOPE["member_location_ids"]), ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    issue_scope_match = re.search(r"```json\s*(\{.*?\})\s*```", ISSUE["body"], re.DOTALL)
    assert issue_scope_match, "Could not locate the machine-readable workload scope in the saved issue body"
    issue_scope = json.loads(issue_scope_match.group(1))
    assert issue_scope["member_location_ids"] == SCOPE["member_location_ids"]
    assert issue_scope["member_location_ids_sha256"] == SCOPE["member_location_ids_sha256"]
    # Preserve and report the legacy issue pin exactly. Its recorded digest
    # currently differs from the standard compact-JSON digest of the frozen
    # ID list, so do not silently rewrite the issue snapshot or call the pin
    # verified. Exact membership is still checked independently below.
    assert all(subject_id in ATLAS for subject_id in MEMBERS)
    assert all(parent["id"] in HIERARCHY_IDS for parent in SCOPE["province_scopes"])
    parent_counts = {
        parent["id"]: sum(ATLAS[subject_id].get("parent_id") == parent["id"] for subject_id in MEMBERS)
        for parent in SCOPE["province_scopes"]
    }
    assert all(parent_counts[parent["id"]] == parent["full_province_locations"] for parent in SCOPE["province_scopes"])
    assert set(src_by_id["ZMB"]) == {
        props["metadata"]["original_id"]
        for props in ATLAS.values()
        if props.get("metadata", {}).get("source_id") == "gb:ZMB:ADM2"
    }

    # Count each ZWE source feature once whether its Atlas representation is a
    # direct district row or a member of the explicitly declared city composite.
    zwe_direct = {
        p["metadata"]["original_id"]: p
        for p in ATLAS.values()
        if p.get("metadata", {}).get("source_id") == "gb:ZWE:ADM2"
    }
    city = ATLAS["atlas:city:ZWE-525"]
    city_members = city["metadata"]["source_member_ids"]
    city_original_ids = {member.rsplit(":", 1)[-1] for member in city_members}
    zwe_unrepresented = set(src_by_id["ZWE"]) - set(zwe_direct) - city_original_ids
    zwe_multiple = (set(zwe_direct) & city_original_ids)
    assert len(src_by_id["ZMB"]) == 116
    assert len(src_by_id["ZWE"]) == 91
    assert len(zwe_direct) == 87
    assert len(city_original_ids) == 4
    assert not zwe_unrepresented, sorted(zwe_unrepresented)
    assert not zwe_multiple, sorted(zwe_multiple)
    assert city_original_ids == {
        "62879985B31454704835515",  # Chitungwiza
        "62879985B25596949610081",  # Epworth
        "62879985B33947363062254",  # Harare
        "62879985B75244512710705",  # Harare Rural
    }
    # Negative control: omit one Harare source member from a copied crosswalk;
    # reconciliation must surface that exact previously represented source ID.
    negative_control_id = sorted(city_original_ids)[0]
    negative_control_missing = set(src_by_id["ZWE"]) - set(zwe_direct) - (city_original_ids - {negative_control_id})
    assert negative_control_missing == {negative_control_id}

    zmb_scoped = [ATLAS[i] for i in MEMBERS if i.startswith("gb:ZMB:ADM2:")]
    zwe_scoped = [ATLAS[i] for i in MEMBERS if i.startswith("gb:ZWE:ADM2:")]
    assert len(zmb_scoped) == 14
    assert len(zwe_scoped) == 87
    assert len(MEMBERS - {p["id"] for p in zmb_scoped + zwe_scoped}) == 1
    assert {src_by_id["ZMB"][p["metadata"]["original_id"]]["shapeName"] for p in zmb_scoped} <= EXPECTED_EASTERN_2022

    # The authoritative 2022 roster has 15 Eastern Province districts. The
    # frozen framework's 14 Eastern features omit Chama, which is in #412's
    # separate Zambia slice and currently parented to Muchinga in Atlas.
    eastern_scope = next(x for x in SCOPE["province_scopes"] if x["id"] == "framework:province:eastern:30af294f5002")
    assert eastern_scope["full_province_locations"] == 14
    assert EXPECTED_EASTERN_2022 - {
        src_by_id["ZMB"][p["metadata"]["original_id"]]["shapeName"] for p in zmb_scoped
    } == {"Chama"}
    chama_id = "gb:ZMB:ADM2:96606910B17560798529879"
    assert ATLAS[chama_id]["parent_id"] == "framework:province:muchinga:9fae5443c064"
    assert chama_id not in MEMBERS

    # Official 2022 ZIMSTAT material uses a three-unit Harare Province roster;
    # the gB source's four 2020-era source units are not four independent Atlas
    # locations and must not be reported as missing.
    harare_scope = next(x for x in SCOPE["province_scopes"] if x["id"] == "framework:province:harare:8fab9cec64d9")
    assert harare_scope["full_province_locations"] == 1
    assert EXPECTED_HARARE_2022 == {"Harare Urban", "Chitungwiza Urban", "Epworth"}

    # `administrative-sources.json` pins the simplified geoBoundaries files;
    # prove those exact bytes, and separately fingerprint the full-resolution
    # LFS objects retained in this packet.
    hash_summary = {}
    for iso in ("ZMB", "ZWE"):
        catalog_hash = ADMIN_SOURCES[f"gb:{iso}:ADM2"]["sha256"]
        simplified = ROOT / f"source/geoboundaries/geoBoundaries-{iso}-ADM2_simplified.geojson"
        full = ROOT / f"source/geoboundaries/geoBoundaries-{iso}-ADM2.geojson"
        assert sha256(simplified) == catalog_hash
        assert catalog_hash == ("58e9df3f95bb4c7539e5fb48839b246b2bfb12694cf5db3ed595240156016c60" if iso == "ZMB" else "3486ef2803574e63db97e2a35b6688bb327cb8d6ff5e439691c1cc3068ddb424")
        if full.exists():
            assert sha256(full) == FULL_SOURCE_SHA256[iso]
            full_rows = json.loads(full.read_text())["features"]
            assert {f["properties"]["shapeID"] for f in full_rows} == set(src_by_id[iso])
            assert {f["properties"]["shapeID"]: f["properties"]["shapeName"] for f in full_rows} == {
                k: v["shapeName"] for k, v in src_by_id[iso].items()
            }
        else:
            assert iso == "ZMB"  # only this source is above the evidence input cap
        hash_summary[iso] = {
            "catalog_simplified_sha256": catalog_hash,
            "retrieved_full_resolution_sha256": FULL_SOURCE_SHA256[iso],
            "full_resolution_retained": full.exists(),
            "feature_count": len(features[iso]),
        }

    provinces = {p["id"]: p for p in SCOPE["province_scopes"]}
    rows = []
    for subject_id in sorted(MEMBERS):
        p = ATLAS[subject_id]
        meta = p.get("metadata", {})
        source_id = meta.get("source_id", "")
        if subject_id == "atlas:city:ZWE-525":
            rows.append({
                "subject_id": subject_id, "subject_name": p["name"], "subject_kind": "location",
                "source_id": source_id, "source_row_id": ";".join(city_members),
                "source_name": "Harare; Harare Rural; Chitungwiza; Epworth",
                "atlas_parent_id": p.get("parent_id", ""), "atlas_parent_name": "Harare",
                "tier_classification": "insufficient-evidence",
                "geometry_assessment": "insufficient-evidence",
                "finding": "Atlas composite aggregates all four 2020 source ADM2 units under an Atlas City identity. Pinned Natural Earth calls the source feature type City but records GN name Harare Province; ZIMSTAT describes Harare Province as several districts (2022: Harare Urban, Chitungwiza Urban, Epworth). These sources support competing city/metro/province interpretations; the intended territory and current boundary remain unproven and need a sourced engineering reassessment.",
                "evidence_refs": "geoboundaries-zwe;natural-earth-admin1;zimstat-harare-2012;zimstat-districts-2022",
            })
            continue
        iso = "ZMB" if source_id == "gb:ZMB:ADM2" else "ZWE"
        original_id = meta.get("original_id", "")
        source = src_by_id[iso][original_id]
        rows.append({
            "subject_id": subject_id, "subject_name": p["name"], "subject_kind": "location",
            "source_id": source_id, "source_row_id": original_id,
            "source_name": source["shapeName"], "atlas_parent_id": p.get("parent_id", ""),
            "atlas_parent_name": next((x["name"] for x in SCOPE["province_scopes"] if x["id"] == p.get("parent_id")), ""),
            "tier_classification": "justified",
            "geometry_assessment": "insufficient-evidence",
            "finding": "Named geoBoundaries ADM2 district identity and Atlas source-row ID/name join are supported. Tier judgment is about administrative role only; source/display boundary equivalence and current legal linework are not independently established.",
            "evidence_refs": "geoboundaries-zmb;zamstats-2022-eastern" if iso == "ZMB" else "geoboundaries-zwe;zimstat-districts-2022",
        })

    for prov in SCOPE["province_scopes"]:
        parent_id = prov["id"]
        child_rows = [ATLAS[sid] for sid in MEMBERS if ATLAS[sid].get("parent_id") == parent_id]
        if parent_id.endswith(":eastern:30af294f5002"):
            classification = "correction-needed"
            finding = "Pinned 2020 ADM1 parent/membership has 14 locations; current official 2022/2023 sources list 15 Eastern districts including Chama, whose Atlas parent remains Muchinga. #412 owns Chama; coordinate the parent and boundary-vintage decision there."
            refs = "zamstats-2022-eastern;zamstats-eastern-projections-2023-2047;chama-council-idp-2025;eastern-province-admin"
        elif parent_id.endswith(":harare:8fab9cec64d9"):
            classification = "insufficient-evidence"
            finding = "The only scoped child is a City identity represented by four ADM2 source districts; official 2022 ZIMSTAT places Harare Urban, Chitungwiza Urban, and Epworth within Harare Province. The province is a supported administrative parent, but this packet cannot establish whether the Atlas child is a justified metropolitan city territory or an over-broad repeated province tier. Reassess the City footprint and time-specific roster."
            refs = "zimstat-districts-2022;zimstat-harare-2012;natural-earth-admin1"
        else:
            classification = "justified"
            finding = "Official ZIMSTAT 2022 report recognizes this member as one of Zimbabwe's ten provinces, and the Atlas child tier is district-level. This supports the administrative roles only; province linework/currentness and each district polygon remain unverified."
            refs = "zimstat-districts-2022"
        rows.append({
            "subject_id": parent_id, "subject_name": prov["name"], "subject_kind": "province_parent",
            "source_id": "gb:ZMB:ADM1" if prov["name"] == "Eastern" else "zimstat:2022-province",
            "source_row_id": "", "source_name": prov["name"], "atlas_parent_id": "",
            "atlas_parent_name": "", "tier_classification": classification,
            "geometry_assessment": "insufficient-evidence", "finding": finding,
            "evidence_refs": refs,
        })

    out = ROOT / "subject-assessment.csv"
    fields = list(rows[0])
    with out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "issue": 413,
        "baseline_commit": BASELINE_COMMIT,
        "baseline_files": BASELINE_FILE_SHA256,
        "scope_release": SCOPE["release"],
        "scope_member_ids_sha256": scope_hash,
        "scope_member_ids_declared_sha256": SCOPE["member_location_ids_sha256"],
        "scope_member_ids_declared_hash_matches": scope_hash == SCOPE["member_location_ids_sha256"],
        "scope_ids_match_saved_issue_body": issue_scope["member_location_ids"] == SCOPE["member_location_ids"],
        "scope_location_count": len(MEMBERS),
        "scope_ids_present": True,
        "source_counts": {iso: len(features[iso]) for iso in features},
        "scope_counts": {"zmb_eastern": len(zmb_scoped), "zwe_direct_districts": len(zwe_scoped), "atlas_city_composite": 1, "province_parents": len(provinces)},
        "zwe_source_features_represented_once": len(zwe_direct) + len(city_original_ids),
        "zwe_source_features_represented_fraction": (len(zwe_direct) + len(city_original_ids)) / len(src_by_id["ZWE"]),
        "zwe_unrepresented_source_ids": sorted(zwe_unrepresented),
        "controls": {
            "positive": {"source_features_represented_once": len(zwe_direct) + len(city_original_ids), "source_features": len(src_by_id["ZWE"]), "passed": len(zwe_direct) + len(city_original_ids) == len(src_by_id["ZWE"])},
            "negative": {"deliberately_omitted_source_id": negative_control_id, "detected_unrepresented_source_ids": sorted(negative_control_missing), "passed": negative_control_missing == {negative_control_id}},
        },
        "zmb_eastern_2022_official_units": len(EXPECTED_EASTERN_2022),
        "zmb_eastern_2022_units_outside_issue_413": sorted(EXPECTED_EASTERN_2022 - {src_by_id['ZMB'][p['metadata']['original_id']]['shapeName'] for p in zmb_scoped}),
        "zwe_harare_2022_official_units": sorted(EXPECTED_HARARE_2022),
        "assessment_rows": len(rows),
        "assessment_csv_sha256": sha256(out),
        "province_scope_parent_counts": parent_counts,
        "classification_counts": dict(Counter(row["tier_classification"] for row in rows)),
        "geometry_assessment_counts": dict(Counter(row["geometry_assessment"] for row in rows)),
        "hashes": hash_summary,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
