#!/usr/bin/env python3
"""Build an additive subject and parent review from the immutable #474 packet."""
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
BASELINE = "0c6232db2b2f9531a479f0c752f66c4d12013f3b"
CURRENT_MAIN_BASE = "b0ade2e782003af8c9568ee98cb01582ef1bd13a"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def old_blob(path):
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"])


def norm(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", value)


scope = read_json(ROOT / "issue-scope.json")
assessment = read_json(ROOT / "assessment.json")
sources = read_json(ROOT / "sources.json")
pins = read_json(ROOT / "baseline-inputs.json")
ins = read_json(ROOT / "niger-ins-crosswalk.json")
ner_overlap = read_json(ROOT / "niger-parent-overlap.json")
mrt_overlap = read_json(ROOT / "mauritania-parent-overlap.json")
fragments = read_json(ROOT / "mauritania-fragment-reproduction.json")
assert pins["baseline_commit"] == BASELINE
assert len(scope["member_location_ids"]) == scope["location_count"] == 228
assert len(assessment["locations"]) == 228 and len(assessment["provinces"]) == 56

base_features = {}
feature_files = {}
for descriptor in pins["files"]:
    raw = old_blob(descriptor["path"])
    assert len(raw) == descriptor["bytes"]
    assert hashlib.sha256(raw).hexdigest() == descriptor["sha256"]
    if descriptor["path"].startswith("data/geography/"):
        for feature in json.loads(raw).get("features", []):
            ident = feature.get("properties", {}).get("id")
            if ident in scope["member_location_ids"]:
                assert ident not in base_features
                base_features[ident] = feature["properties"]
                feature_files[ident] = descriptor["path"]
hierarchy_doc = json.loads(old_blob("data/hierarchy.json"))
hierarchy = {row["id"]: row for row in hierarchy_doc}
assert set(base_features) == set(scope["member_location_ids"])

location_rows = {row["id"]: row for row in assessment["locations"]}
ins_rows = {row["id"]: row for row in ins["scoped_rows"]}
ner_rows = {row["id"]: row for row in ner_overlap["subjects"]}
mrt_rows = {row["id"]: row for row in mrt_overlap["rows"]}
fragment_rows = {}
for row in fragments["rows"]:
    for ident in row["atlas_ids"]:
        assert ident not in fragment_rows
        fragment_rows[ident] = row

resolve_doc = read_json(ROOT / "sources/resolve/features-2017-ids.json")
resolve_by_id = {f["properties"]["ECO_ID"]: f["properties"] for f in resolve_doc["features"]}
issue_findings = assessment["findings"]
city_finding = next(x for x in issue_findings if x["id"] == "NER-CITY-GRANULARITY")
city_source_members = base_features["atlas:city:NER-94"].get("metadata", {}).get("source_member_ids", [])
assert len(city_source_members) == 6
city_unit_ids = set(city_finding["subjects"])
city_unit_ids.discard("atlas:city:NER-94")
assert len(city_unit_ids) == 5

parent_name = {}
for ident, props in base_features.items():
    parent = props.get("parent_id")
    if parent in hierarchy:
        parent_name[ident] = hierarchy[parent].get("name", "")

scope_parent_ids = defaultdict(list)
for ident, props in base_features.items():
    scope_parent_ids[props.get("parent_id")].append(ident)

def refs_for(ident, source_class):
    if ident == "atlas:city:NER-94":
        return ["baseline/Natural-Earth-city-record", "niger/INS-2012", "geoboundaries/NER-ADM3"]
    if ident.startswith("gb:NER:ADM3:"):
        return ["niger/INS-2012", "geoboundaries/NER-ADM3", "geoboundaries/NER-ADM2"]
    if ident.startswith("gb:MRT:ADM2:"):
        return ["mauritania/DGAT-RGPH-2024", "mauritania/SNGM-2021-2023", "mauritania/AMI-2021", "geoboundaries/MRT-ADM2", "geoboundaries/MRT-ADM1"]
    return ["resolve/2017-ecoregions", "geoboundaries/MRT-ADM2", "mauritania/DGAT-RGPH-2024"]

def source_profile(ident):
    if ident.startswith("gb:NER:ADM3:"):
        return {
            "source_layer": "geoBoundaries NER ADM3",
            "source_role": "Communes (geoBoundaries canonical field); INS 2012 table's row vocabulary is commune under a named department and region.",
            "vintage": "2012 source/statistical reference; not asserted current",
            "feature_count": 266,
            "license": "geoBoundaries metadata claims CC BY 3.0; upstream source lists OCHA ROWCA/OpenStreetMap while CityPopulation terms leave geospatial reuse rights unresolved.",
            "license_status": "unresolved for geometry redistribution",
            "asset_status": "source geometry is not retained; restoration URL and exact SHA-256/bytes are in sources.json",
            "completeness": "266-unit 2012 INS/geoBoundaries source roster is identified; current legal roster and complete current boundaries are not established.",
        }
    if ident.startswith("gb:MRT:ADM2:"):
        return {
            "source_layer": "geoBoundaries MRT ADM2",
            "source_role": "Moughataa / administrative district per source metadata; current official individual unit identity is not independently matched.",
            "vintage": "2020 source; parent comparison uses 2015 ADM1",
            "feature_count": 57,
            "license": "CC BY 3.0 IGO per retained geoBoundaries metadata; upstream chain is recorded as WFP/OCHA ROWCA/HDX.",
            "license_status": "metadata claim retained; current source lineage and lawful contemporary replacement remain follow-up work",
            "asset_status": "geometry and metadata are retained with whole-file hashes in sources.json",
            "completeness": "The source layer has 57 features; dated Mauritanian government counts are 61 in the 2022 strategy and 63 attributed to RGPH 2024. Current full roster remains unresolved.",
        }
    if ident.startswith("atlas:physical:"):
        return {
            "source_layer": "RESOLVE Biomes and Ecoregions 2017",
            "source_role": "Ecological ecoregion; not an administrative or political unit.",
            "vintage": "2017 source; item data-last-edit 2022-01-28",
            "feature_count": 5,
            "license": "CC BY 4.0 item licenseInfo in retained ArcGIS item metadata.",
            "license_status": "metadata retained; original five feature bytes and item/source hashes are preserved",
            "asset_status": "source records retained under sources/resolve/",
            "completeness": "The records are derived intersections of a Moughataa and an ecological source polygon; they do not establish a complete physical-land, settlement or administrative roster.",
        }
    return {
        "source_layer": "Atlas Niamey source-city aggregation",
        "source_role": "Source label says city territory / capital district; six 2012 ADM3 source members are listed in the pinned baseline metadata.",
        "vintage": "Undated modern cartographic source; underlying members include 2012 units",
        "feature_count": 1,
        "license": "Underlying source license references are in semantic-report.json; a current urban extent or complete city roster is not established.",
        "license_status": "underlying city-source lineage requires follow-up review",
        "asset_status": "The exact city record and six member IDs are in the immutable baseline; underlying source geometry is not asserted current.",
        "completeness": "The six-member composite is a source aggregation, not proof of the current municipal or built-up urban extent.",
    }

subjects = []
for ident in scope["member_location_ids"]:
    props = base_features[ident]
    prior = location_rows[ident]
    profile = source_profile(ident)
    parent = props.get("parent_id")
    row = {
        "id": ident,
        "name": props.get("name"),
        "parent_id": parent,
        "parent_name": parent_name.get(ident),
        "source_class": prior["source_class"],
        "source_profile": profile,
        "classification": prior["review_classification"],
        "identity": {"outcome": "verified against frozen #474 baseline", "source_id": props.get("metadata", {}).get("source_id"), "source_feature_id": props.get("metadata", {}).get("original_id", ident.rsplit(":", 1)[-1]), "baseline_feature_file": feature_files[ident]},
        "cited_source_records": refs_for(ident, prior["source_class"]),
        "reviewed_questions": {
            "territorial_role": "See source_profile; administrative role is supported only at the stated source vintage and scope.",
            "parent_relationship": "See subject-specific source/official crosswalk below. Current legal boundary parentage remains unverified.",
            "boundary_relationship": "Diagnostic comparisons are vintage-limited; they do not establish legal boundary equality.",
            "completeness": profile["completeness"],
            "license": profile["license"],
            "neighboring_granularity": "See source-specific peer/dept/wilaya or ecological-fragment relationship below; a parent match does not certify tier purpose.",
        },
        "followups": [],
    }
    if ident.startswith("gb:NER:ADM3:"):
        cw = ins_rows[ident]
        ov = ner_rows[ident]
        normalized_source_parent = norm(cw.get("official_INS_2012_row", ["", ""])[1] if len(cw.get("official_INS_2012_row", [])) > 1 else "")
        normalized_atlas_parent = norm(parent_name.get(ident))
        top = ov.get("source_parent_candidates", [])
        max_fraction = max((c["subject_area_fraction"] for c in top), default=None)
        row["official_role_parent_crosswalk"] = {
            "official_INS_2012_row": cw.get("official_INS_2012_row"),
            "resolution": cw.get("resolution"),
            "official_department_matches_atlas_parent_name": normalized_source_parent == normalized_atlas_parent,
            "atlas_parent_name": parent_name.get(ident),
            "INS_limit": cw.get("official_role_limit"),
            "same_parent_scoped_subject_count": len(scope_parent_ids.get(parent, [])),
        }
        row["boundary_screen"] = {
            "source": "2012 ADM3 compared to all 67 retained 2018 ADM2 candidates in original PR #807 measurements",
            "maximum_subject_area_overlap_fraction": max_fraction,
            "candidates": top,
            "interpretation": "Vintage overlap only. A low or high fraction does not prove legal parentage or a boundary correction.",
            "source_geometry_retained": False,
            "source_hashes": ner_overlap["source_sha256"],
        }
        if ident in city_unit_ids:
            row["followups"].append("#806")
        if (cw.get("resolution") == "official-name-candidate-parent-unresolved" or (max_fraction is not None and max_fraction < 0.9)) and ident not in city_unit_ids:
            row["followups"].append("#833")
        row["followups"].append("#834")
    elif ident.startswith("gb:MRT:ADM2:"):
        ov = mrt_rows[ident]
        top = ov.get("candidate_parents", [])
        row["official_role_parent_crosswalk"] = {
            "source_name": props.get("name"),
            "source_parent_candidates": top,
            "top_candidate_name_matches_atlas_parent": ov.get("atlas_parent_matches_top_name"),
            "same_parent_scoped_subject_count": len(scope_parent_ids.get(parent, [])),
            "interpretation": "Name and 2015/2020 overlap are a historical source crosswalk; they do not establish today's statutory identity or boundary.",
        }
        row["boundary_screen"] = {"source": "2015 ADM1 candidate comparison", "candidates": top, "current_official_comparison": "not available in this packet; #804 owns the complete 69-member crosswalk", "interpretation": "Diagnostic overlap only."}
        row["followups"].append("#804")
    elif ident.startswith("atlas:physical:"):
        frag = fragment_rows[ident]
        eco = resolve_by_id.get(frag["ecoregion_id"], {})
        row["physical_source_crosswalk"] = {
            "moughataa_source_id": frag["moughataa_source_id"],
            "ecoregion_id": frag["ecoregion_id"],
            "ecoregion_name": eco.get("ECO_NAME"),
            "ecoregion_biome": eco.get("BIOME_NAME"),
            "role": "RESOLVE ecological polygon intersected with an administrative source polygon; not an administrative unit itself.",
            "intersection_screen": {k: frag[k] for k in ("expected_area_m2", "actual_area_m2", "symmetric_difference_m2", "symmetric_difference_fraction_of_expected", "actual_coverage_of_expected", "valid") if k in frag},
            "method_limit": fragments["method_details"],
        }
        row["followups"].append("#801")
    else:
        row["official_role_parent_crosswalk"] = {
            "source_member_ids": city_source_members,
            "official_city_context": "INS 2012 row/national municipality structure; current municipal/urban territory and six-member statutory relationship unresolved.",
            "finding": "NER-CITY-GRANULARITY",
            "special_city_comparison_subjects": sorted(city_unit_ids),
        }
        row["boundary_screen"] = {"source": "No independently validated current Niamey urban or legal-city polygon in this packet.", "interpretation": "Six source members and name aliases do not establish urban extent or administrative completeness."}
        row["followups"].append("#806")
        row["followups"].append("#834")
    row["followups"] = list(dict.fromkeys(row["followups"]))
    subjects.append(row)

assert len(subjects) == 228 and len({x["id"] for x in subjects}) == 228
assert Counter(x["source_class"] for x in subjects) == Counter({"Niger 2012 ADM3 source unit": 204, "Mauritania 2020 ADM2 source unit": 13, "Mauritania RESOLVE ecoregion fragment": 10, "Niamey composite city": 1})

province_assessment = {x["id"]: x for x in assessment["provinces"]}
province_rows = []
for pid, ids in sorted(scope_parent_ids.items()):
    if not pid:
        continue
    p = province_assessment[pid]
    members = [x for x in subjects if x["parent_id"] == pid]
    ins_status = Counter((x.get("official_role_parent_crosswalk", {}).get("resolution", "not-applicable") for x in members if x["id"].startswith("gb:NER:ADM3:")))
    province_rows.append({
        "id": pid,
        "name": hierarchy.get(pid, {}).get("name", p["name"]),
        "scope_member_ids": [x["id"] for x in members],
        "scope_count": len(members),
        "issue_classification": p["review_classification"],
        "source_basis": p["baseline_basis"],
        "official_INS_crosswalk_resolution_counts": dict(sorted(ins_status.items())),
        "source_parent_labels": sorted({v for x in members for v in [
            x.get("official_role_parent_crosswalk", {}).get("official_INS_2012_row", [None, None])[1]
            if len(x.get("official_role_parent_crosswalk", {}).get("official_INS_2012_row", [])) > 1
            else next((c.get("name") for c in x.get("official_role_parent_crosswalk", {}).get("source_parent_candidates", []) if c.get("name")), None)
        ] if v}),
        "purpose_and_completeness": p["notes"],
        "conclusion": "Individually classified insufficient-evidence. The source row/group mapping is documented; current legal parent purpose, complete present-day roster and source-to-baseline boundary agreement remain unresolved.",
        "members_followups": sorted({f for x in members for f in x["followups"]}),
    })
assert len(province_rows) == 56

area_rows = []
for area in scope["area_scopes"]:
    aid = area["id"]
    members = []
    for subject in subjects:
        cursor = subject["parent_id"]
        while cursor and cursor in hierarchy:
            if cursor == aid:
                members.append(subject["id"])
                break
            cursor = hierarchy[cursor].get("parent_id")
    existing = next(x for x in assessment["area_scopes"] if x["id"] == aid)
    assert len(members) == area["owned_member_location_count"] == existing["packet_owned_members"]
    area_rows.append({
        "id": aid,
        "name": area["name"],
        "scope_member_ids": members,
        "owned_count": len(members),
        "full_count": area["full_area_location_count"],
        "partial": area["partial"],
        "classification": existing["review_classification"],
        "baseline_basis": existing["baseline_basis"],
        "purpose_limit": existing["purpose_limit"],
        "conclusion": "Workload subset only. WGSRPD botanical-country grouping does not independently establish geographic-area tier purpose or political ownership; combined area review requires sibling packets and complete current source coverage.",
    })

out = {
    "version": 1,
    "issue": 474,
    "packet": scope["batch_id"],
    "created_from_current_main": CURRENT_MAIN_BASE,
    "frozen_issue_baseline": BASELINE,
    "release": scope["release"],
    "scope_pins": {k: scope[k] for k in ("frozen_region_geometry_sha256", "frozen_region_member_ids_sha256", "macro_certificate_sha256", "member_location_ids_sha256")},
    "counts": {"locations": len(subjects), "provinces": len(province_rows), "areas": len(area_rows), "niger_adm3": 204, "mauritania_adm2": 13, "ecological_fragments": 10, "city_aggregates": 1},
    "classification_counts": dict(sorted(Counter(x["classification"] for x in subjects).items())),
    "limits": ["The register binds prior source/geometry screens and adds subject-level interpretations; it does not independently validate all source polygons or certify a region.", "Niger source geometry is not retained because the metadata and upstream reuse rights do not establish a clear redistributable chain.", "Mauritania's 57/61/63 roster change, the 10 ecological fragment purposes and six special-city aggregation remain assigned to bounded follow-ups."],
    "subjects": subjects,
    "provinces": province_rows,
    "areas": area_rows,
    "prior_findings": issue_findings,
    "source_hashes": {
        "niger_ins_response": sources["niger_ins_2012"]["sha256"],
        "niger_adm3_metadata": sources["niger_geoboundaries_adm3"]["retained_metadata"]["sha256"],
        "niger_adm3_geometry_restoration": sources["niger_geoboundaries_adm3"]["geometry_not_retained"]["sha256"],
        "niger_adm2_geometry_restoration": sources["niger_geoboundaries_adm2"]["geometry_not_retained"]["sha256"],
        "mauritania_adm2_geometry": sources["mauritania_geoboundaries_adm2"]["retained_geometry"]["sha256"],
        "mauritania_adm2_metadata": sources["mauritania_geoboundaries_adm2"]["retained_metadata"]["sha256"],
        "mauritania_dgat_2024": sources["mauritania_dgat_current"]["sha256"],
        "mauritania_sngm_2021_2023": sources["mauritania_sngm_2021_2023"]["sha256"],
        "mauritania_ami_2021": sources["mauritania_2021_new_moughataas"]["sha256"],
        "resolve_features": sources["resolve_2017"]["retained"]["features-2017-ids.json"]["sha256"],
        "resolve_item": sources["resolve_2017"]["retained"]["item.json"]["sha256"],
    },
}
payload = json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
(ROOT / "completion-review.json").write_text(payload, encoding="utf-8")
print(json.dumps({"subjects": len(subjects), "provinces": len(province_rows), "areas": len(area_rows), "classification_counts": out["classification_counts"], "output_sha256": hashlib.sha256(payload.encode()).hexdigest()}, sort_keys=True))
