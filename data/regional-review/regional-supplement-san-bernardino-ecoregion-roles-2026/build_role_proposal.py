#!/usr/bin/env python3
"""Build a four-subject, evidence-only RESOLVE source-role correction proposal."""
import gzip
import hashlib
import html
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
BASE_COMMIT = "fbd3bf4991dbd5a9bf89a79b14e5b4deb6225ff9"
PACKET = "data/regional-review/regional-review-2178b81fa886cfb6"
SUBJECTS = {
    "atlas:physical:5dcc72971bb4b1ede2f5": (433, "Mojave desert"),
    "atlas:physical:9cfc4fc5de3925d6f841": (435, "Sonoran desert"),
    "atlas:physical:d76eb273e99a0f96a575": (424, "California montane chaparral and woodlands"),
    "atlas:physical:dcc393fbc988381d899c": (422, "California coastal sage and chaparral"),
}
CHAIN = [
    "{id}", "framework:province:california:f695c774b8ba",
    "framework:area:pacific:31aced66907e",
    "framework:region:western-north-america:d2a1c2775a57",
    "framework:subcontinent:northern-america:477e054b32f2",
    "framework:continent:north-america:1ca27616f338",
]


def baseline(path):
    return subprocess.check_output(["git", "show", f"{BASE_COMMIT}:{path}"])


def json_bytes(path):
    return json.loads(baseline(path))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    assessment_path = f"{PACKET}/assessment.json"
    scope_path = f"{PACKET}/scope.json"
    sources_path = f"{PACKET}/sources.json"
    audit_path = f"{PACKET}/derived-portion-audit.json"
    world_path = "data/geography/part-25.json"
    resolve_path = f"{PACKET}/sources/resolve-ca-ecoregions-4.geojson.gz"
    resolve_layer_path = f"{PACKET}/sources/resolve-layer0-metadata.json"
    resolve_item_path = f"{PACKET}/sources/resolve-arcgis-item-metadata.json"
    county_path = f"{PACKET}/sources/geoboundaries-USA-ADM2-2018.geojson.gz"
    county_meta_path = f"{PACKET}/sources/geoboundaries-USA-ADM2-metadata.json"
    tiger_path = f"{PACKET}/sources/tigerline-2024-western-county-neighbors.geojson.gz"

    assessment = json_bytes(assessment_path)
    scope = json_bytes(scope_path)
    source_registry = json_bytes(sources_path)
    audit = json_bytes(audit_path)
    world = json.loads(baseline(world_path))
    resolve = json.loads(gzip.decompress(baseline(resolve_path)))
    resolve_layer = json_bytes(resolve_layer_path)
    resolve_item = json_bytes(resolve_item_path)
    county = json.loads(gzip.decompress(baseline(county_path)))
    county_meta = json_bytes(county_meta_path)
    tiger = json.loads(gzip.decompress(baseline(tiger_path)))

    member_ids = set(scope["member_location_ids"])
    require(set(SUBJECTS) <= member_ids, "Issue subjects are absent from the pinned #487 scope")
    rows = {row["location_id"]: row for row in assessment["locations"]}
    features = {feature.get("id", feature.get("properties", {}).get("id")): feature
                for feature in world["features"]}
    eco_features = {feature["properties"]["ECO_ID"]: feature for feature in resolve["features"]}
    county_features = {feature["properties"].get("shapeID"): feature for feature in county["features"]}
    tiger_features = {feature["properties"]["GEOID"]: feature for feature in tiger["features"]}
    county_feature = county_features.get("52423323B23069932539838")
    tiger_feature = tiger_features.get("06071")
    require(county_feature and county_feature["properties"]["shapeName"] == "San Bernardino",
            "2018 ADM2 predecessor identity mismatch")
    require(county_meta["boundaryYear"] == "2018" and county_meta["boundaryCanonical"] == "Counties",
            "2018 ADM2 source metadata mismatch")
    require(tiger_feature and tiger_feature["properties"]["NAMELSAD"] == "San Bernardino County" and
            tiger_feature["properties"]["CLASSFP"] == "H1", "2024 Census county-equivalent identity mismatch")

    item_description = html.unescape(re.sub(r"<[^>]+>", " ", resolve_item.get("description", "")))
    item_description = re.sub(r"\s+", " ", item_description).strip()
    require("natural, rather than political, boundaries" in item_description and
            "ecological habitats" in item_description, "RESOLVE ecological description is missing")
    require("creativecommons.org/licenses/by/4.0/" in resolve_item.get("licenseInfo", "") and
            "RESOLVE" in resolve_item.get("accessInformation", ""), "RESOLVE attribution/license evidence is missing")
    require(resolve_layer["id"] == 0 and resolve_layer["name"] == "Biomes and Ecoregions 2017",
            "Unexpected RESOLVE layer identity")
    data_edit_ms = resolve_layer["editingInfo"]["dataLastEditDate"]
    layer_data_last_edit = datetime.fromtimestamp(data_edit_ms / 1000, timezone.utc).date().isoformat()
    audit_rows = {row["location_id"]: row for row in audit["fragments"]}

    proposed = []
    for subject_id, (eco_id, eco_name) in SUBJECTS.items():
        require(subject_id in rows and subject_id in features, f"Assigned subject missing: {subject_id}")
        row, feature, eco = rows[subject_id], features[subject_id], eco_features.get(eco_id)
        require(eco is not None, f"RESOLVE feature missing for ECO_ID {eco_id}")
        props = feature["properties"]
        metadata = props["metadata"]
        chain = row["full_parent_chain"]
        require([node["id"] for node in chain] == [value.format(id=subject_id) for value in CHAIN],
                f"Full parent chain changed for {subject_id}")
        require(row["source_role_metadata_review"]["current_source_role"] == "Counties" and
                row["source_role_metadata_review"]["source_role_agrees"] is False,
                f"Expected source-role mismatch missing for {subject_id}")
        require(metadata["source_id"] == f"resolve:{eco_id}" and
                metadata["source_role"] == "Counties" and
                metadata["original_id"] == "52423323B23069932539838" and
                metadata["source_member_ids"] == ["gb:USA:ADM2:52423323B23069932539838"],
                f"Current identity/source links changed for {subject_id}")
        eprops = eco["properties"]
        require(eprops["ECO_NAME"] == eco_name and eprops["LICENSE"] == "CC-BY 4.0",
                f"RESOLVE source value/license mismatch for ECO_ID {eco_id}")
        portion = audit_rows.get(subject_id)
        require(portion and portion["eco_id"] == eco_id and portion["eco_name"] == eco_name and
                portion["predecessor_shape_id"] == "52423323B23069932539838",
                f"Inherited portion audit mismatch for {subject_id}")

        old = row["source_role_metadata_review"]
        suggested_role = "Ecological ecoregion portion"
        reason = (f"Physical-geography location for the part of RESOLVE 2017 ECO_ID {eco_id} "
                  f"({eco_name}) associated with the 2018 San Bernardino ADM2 predecessor. "
                  "The county is the source intersection context, not this location's government, "
                  "administrative role, or political-ownership claim.")
        geometry_bytes = json.dumps(feature["geometry"], sort_keys=True, separators=(",", ":")).encode()
        proposed.append({
            "id": subject_id,
            "name": row["name"],
            "assessment": "supported source-role correction proposal",
            "current": {
                "source_id": metadata["source_id"],
                "source_role": old["current_source_role"],
                "administrative_level": old["current_administrative_level"],
                "selection_reason": old["current_selection_reason"],
                "location_basis": metadata["location_basis"],
                "source_name": metadata["source_name"],
            },
            "proposed": {
                "source_id": metadata["source_id"],
                "source_role": suggested_role,
                "administrative_level": old["current_administrative_level"],
                "selection_reason": reason,
                "location_basis": metadata["location_basis"],
            },
            "physical_source": {
                "publisher_attribution": "RESOLVE, Esri",
                "dataset": resolve_layer["name"],
                "source_vintage": "2017",
                "layer_data_last_edit": layer_data_last_edit,
                "eco_id": eco_id,
                "eco_name": eco_name,
                "biome": eprops["BIOME_NAME"],
                "realm": eprops["REALM"],
                "feature_license": eprops["LICENSE"],
                "source_role": "Ecological ecoregion with natural rather than political boundaries",
                "evidence_quote": "ecoregions draw on natural, rather than political, boundaries",
                "canonical_item": "https://www.arcgis.com/home/item.html?id=37ea320eebb647c6838c23f72abae5ef",
                "canonical_layer": "https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Resolve_Ecoregions/FeatureServer/0",
            },
            "administrative_intersection_context": {
                "predecessor_source": "geoBoundaries USA ADM2, 2018; Census MAF/TIGER-derived",
                "predecessor_shape_id": "52423323B23069932539838",
                "predecessor_name": "San Bernardino",
                "2024_census_geoid": "06071",
                "2024_census_name": "San Bernardino County",
                "2024_classfp": "H1",
                "interpretation": "The county defines the clipped/intersection context only; it does not define this feature as a county.",
            },
            "preservation": {
                "parent_chain": [{"id": node["id"], "name": node["name"], "level": node["level"],
                                  "parent_id": node.get("parent_id")} for node in chain],
                "existing_source_member_ids": metadata["source_member_ids"],
                "original_geometry_sha256_canonical_json": sha(geometry_bytes),
                "geometry_action": "preserve unchanged; this evidence packet contains no replacement geometry",
            },
            "inherited_scope_screens": {
                "settlement_screen": row["settlement_screen"],
                "physical_land_screen": row["physical_land_screen"],
                "remainders_islands_disconnected_review": row["remainders_islands_disconnected_review"],
                "political_historical_distinction": row["political_historical_distinction"],
                "decision_basis": row["decision_basis"],
                "unresolved": row["unresolved"],
                "portion_overlay": portion,
            },
            "source_ids": ["resolve-2017-ecoregions", "geoboundaries-usa-adm2-2018",
                           "census-tigerline-2024-counties", "worldatlas-packet-487"],
        })

    require(len(proposed) == len(SUBJECTS) == 4, "Assigned roster is not exhaustive")
    # All 4 inputs are ecological ecoregion IDs; Census/ADM2 evidence is a separate derivation context.
    result = {
        "version": 1,
        "issue": 597,
        "baseline_commit": BASE_COMMIT,
        "assessment_date_utc": assessment["date_utc"],
        "scope": {
            "assigned_subject_ids": list(SUBJECTS),
            "assigned_count": len(SUBJECTS),
            "assessed_count": len(proposed),
            "role_mismatch_count": sum(item["current"]["source_role"] != item["proposed"]["source_role"] for item in proposed),
            "all_four_in_parent_scope": True,
        },
        "source_role_finding": {
            "supported_role": "Ecological ecoregion portion",
            "tier": "Named physical region portion (preserved existing administrative_level description)",
            "reason": "RESOLVE source and all four ECO_ID links identify natural ecological regions; San Bernardino county is a derivation/intersection context only.",
            "selection_rule": "Select the county × named-ecoregion fragment as physical geography; do not label it a county, transfer its county predecessor to political ownership, or change its stable location identity.",
            "review_kind": "Source and geometry identity; proposal only",
        },
        "administrative_predecessor": {
            "shape_id": "52423323B23069932539838",
            "name": "San Bernardino",
            "2018_level": "ADM2 county",
            "2024_geoid": "06071",
            "2024_name": "San Bernardino County",
            "2024_classfp": "H1",
            "source_paths": [county_path, county_meta_path, tiger_path],
        },
        "parent_fragment_union_screen": audit["parent_union"],
        "neighbor_consistency": {
            "finding": "All four assigned subjects retain the same California → Pacific → Western North America parent chain. This source-role correction makes no county adjacency or shared-boundary claim.",
            "inherited_neighbor_packet": f"{PACKET}/neighbor-screen.json",
            "limitation": "Neighbor, water-edge and exact boundary screens are inherited #487 evidence, not remeasured here; no shared boundary or parent footprint is changed.",
        },
        "subjects": proposed,
        "source_provenance": {
            "resolve_dataset": resolve_layer["name"],
            "resolve_item_title": resolve_item["title"],
            "resolve_item_attribution": resolve_item["accessInformation"].strip(),
            "resolve_license": "CC BY 4.0",
            "resolve_layer_data_last_edit": layer_data_last_edit,
            "parent_assessment_sha256": sha(baseline(assessment_path)),
            "parent_sources_registry_sha256": sha(baseline(sources_path)),
        },
        "metrics": {"subject_count_assessed": 4, "source_role_mismatch_count": 4},
        "limitations": [
            "All settlement, physical-land, county-water, island, remainder and neighbor values are inherited #487 screens, not independently recomputed in #597.",
            "Census Places is not a complete settlement gazetteer; GSHHG representative points and component counts do not certify all land, islands or coastline.",
            "The inherited four-piece union differs from the 2018 county predecessor by a 24.520472 km² symmetric-difference screen; this does not identify a legal remainder or support moving a shared line.",
            "RESOLVE ecoregions describe ecological systems, not sovereignty, county government or historical political ownership.",
            "This is a source-role/rationale proposal for engineering review, not shared hierarchy/geometry approval and not authorization for history imports.",
        ],
    }
    (ROOT / "proposed-role-corrections.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": "proposed-role-corrections.json", "sha256": sha((ROOT / "proposed-role-corrections.json").read_bytes()),
                      "subjects": result["scope"], "resolve_data_last_edit": layer_data_last_edit}, indent=2))


if __name__ == "__main__":
    main()
