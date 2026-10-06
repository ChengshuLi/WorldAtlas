#!/usr/bin/env python3
"""Reproduce the exact 45-member follow-up from issue #395's pinned assessment."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
BASE = ROOT / "data/regional-review/regional-review-626fdf640aab94e2"
ASSESSMENT_PATH = BASE / "findings/member-assessments.json"
ASSESSMENT_SHA256 = "55e20fc63247dd81a3d23dac405811c34e7dee79dc7b7a72712febbe813d913f"
BASELINE_COMMIT = "8e1162e3e364cebdec700ec796e2730379494922"
CURRENT_BASE = "00664f04790641a9e0c0b29535823076ed243b93"
EXPECTED_SCOPE_HASH = "bfc28011d523d063794c21c09eb7a3671e2215bc285a5ce786d4d3e17448b561"
ISSUE_PINS = {
    "prior_member_assessments": ASSESSMENT_SHA256,
    "prior_issue_scope": "bd01cfec3fa206b2e99dd3505c923fbec185be16842da260b440800fa9cd2117",
    "prior_scoped_source_features": "7eb4cba61f0d17bfacb634c08aff3ec4873ece62734d518b51614bf061a5a129",
    "prior_current_features": "44aa8bed8c6d3f6b7f4c553007efbaa82d39ff384790e95c06d1e3615ad4f070",
}

CITY_TEXT = "city/urban okrug"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def exact_scope(ids):
    if len(ids) != 45 or len(set(ids)) != 45 or ids != sorted(ids):
        raise ValueError("issue subject scope must contain exactly 45 unique sorted IDs")
    return sha256(json.dumps(ids, ensure_ascii=False, separators=(",", ":")).encode())


def source_refs(row, category):
    refs = ["prior-geoboundaries-adm2"]
    province = row["province_name"]
    if category == "ecoregion-fragment":
        refs.append("prior-resolve-ecoregions")
    elif category == "city-name-role":
        refs += {
            "Altai Krai": ["altai-krai-rosstat-municipal-list", "altai-krai-rosstat-2024-yearbook"],
            "Tomsk Oblast": ["tomsk-oblast-rosstat-list"],
            "Yamalo-Nenets Autonomous Okrug": ["yamal-nenets-mchs-profile"],
            "Khanty-Mansiysk Autonomous Okrug – Ugra": ["khanty-mansi-63oz-municipal-boundaries-law", "nefteyugansk-official-charter", "nizhnevartovsk-official-charter"],
            "Omsk Oblast": ["omsk-oblast-rosstat-list"],
        }.get(province, [])
    else:
        refs += {
            "Altai Krai": ["altai-krai-rosstat-municipal-list"],
            "Novosibirsk Oblast": ["novosibirsk-oblast-rosstat-list"],
            "Omsk Oblast": ["omsk-oblast-rosstat-list"],
            "Yamalo-Nenets Autonomous Okrug": ["yamal-nenets-mchs-profile"],
        }.get(province, [])
    return refs


def role_review(row, category):
    province = row["province_name"]
    if category == "ecoregion-fragment":
        return {
            "observed_role": "Physical ecoregion portion derived by intersecting one of four administrative source districts; not itself a complete administrative district.",
            "current_role": "Ecological region fragment; it must not be described as an administrative Raion without a separate product decision.",
            "status": "correction-needed",
            "boundary_status": "The retained 2017-derived ecological geometry is inspectable; neither a current ecoregion vintage nor a current legal administrative boundary was established.",
            "neighboring_granularity": "The physical roster contains partial subdivisions cut by ECO_ID across larger ADM2 districts, while the adjacent administrative roster uses whole named units.",
            "recommendation": "Engineering/product owner should decide whether these IDs belong in a physical/ecological product layer or whether source_role and selection rationale need an explicit non-administrative type. Preserve IDs, geometry and source lineage until that decision.",
        }
    if category == "city-name-role":
        if province == "Tomsk Oblast":
            current = "The official Tomskstat roster lists the three city entities in this packet under Tomsk Oblast city okrugs."
            refs_note = "2026-crawled official roster text; no boundary geometry."
        elif province == "Yamalo-Nenets Autonomous Okrug":
            current = "The official MChS regional profile places this named city among the six city okrugs; the four in-scope city names match that roster."
            refs_note = "The retained page capture is 2026-10-05; a current web extraction also listed this roster."
        elif province == "Khanty-Mansiysk Autonomous Okrug – Ugra":
            current = "Regional Law 63-oz is the official source for municipal urban-okrug status and boundary schemes; current official Nefteyugansk and Nizhnevartovsk charters separately confirm urban-okrug status for those municipalities. The law's 2026 amendment state was not verified."
            refs_note = "Status evidence is statutory/municipal; it does not equate a municipal okrug with an administrative city-of-district-significance tier."
        elif province == "Omsk Oblast":
            current = "The official Omskstat list dated 2026-01-01 lists Omsk as a city okrug."
            refs_note = "The extracted roster has no territorial geometry."
        elif province == "Altai Krai" and row["source_unit_name"] == "городской округ Славгород":
            current = "Official Treasury search text records Slavgorod's conversion to the municipal okrug named city Slavgorod. This is a municipality-type change from the 2017 feature label; the 2026 official list DOCX was not retrieved."
            refs_note = "Do not continue to call the current unit a city okrug based only on its 2017 source name."
        elif province == "Altai Krai":
            current = "The 2017 feature name says city okrug. Earlier official Rosstat statistical tables classify this group as city okrugs, and Rosstat publishes a 2026 law-based municipal-list DOCX; that DOCX was not retrieved, so the individual 2026 status is not independently verified here."
            refs_note = "Use as a role lead only; not proof of current legal status or geometry."
        else:
            current = "A municipal city-type entity is identified by the historical feature name; current legal hierarchy and footprint need the linked official crosswalk source."
            refs_note = "Current legal tier and boundary remain unresolved."
        return {
            "observed_role": "2017 source feature name identifies a city / city-okrug form; the Atlas source_role field is Raion.",
            "current_role": current,
            "status": "insufficient-evidence",
            "boundary_status": "The source feature is a 2017 boundary vintage built in 2023. No law-backed current boundary geometry or complete component crosswalk was retrieved for this subject.",
            "neighboring_granularity": "Official statistical/legal rosters distinguish city okrugs from municipal districts and municipal okrugs. These are municipal-government forms; their equivalence to the Atlas's intended district tier is a separate hierarchy decision.",
            "recommendation": "Add a sourced role crosswalk that preserves municipal type separately from the shared Atlas tier. Do not bulk demote city territories or change geometry solely because a role string differs.",
            "source_note": refs_note,
        }
    if province == "Yamalo-Nenets Autonomous Okrug":
        current = "Official MChS lists the matching district-named entity within the seven municipal okrugs; that roster supports entity-role/name, not boundary components."
    elif province == "Novosibirsk Oblast":
        current = "Official Rosstat's current roster distinguishes city Novosibirsk as an urban okrug and Novosibirsky District as a municipal district; this supports class/parent context but not either source feature's separate components."
    elif province == "Omsk Oblast":
        current = "Official Omskstat's 2026-01-01 roster places the district-named territories in a changing municipal-okrug/municipal-district framework; exact row equivalence needs the retrieved register and local laws."
    else:
        current = "The 2017 ADM2 source confirms this as a multipart source feature with the stated component count. The current administrative roster and legal boundary annex were not retrieved for a component-by-component match."
    return {
        "observed_role": f"2017 geoBoundaries source row named {row['source_unit_name']}; source_role Raion; {row['geometry_type']} with {row['component_count']} polygon components.",
        "current_role": current,
        "status": "insufficient-evidence",
        "boundary_status": "No independent official polygon/annex comparison verified every component, omission, inclusion, island, or present-day extent. The source's 2017 vintage and parent match do not certify current geography.",
        "neighboring_granularity": "Other scope neighbors include municipal districts and city/municipal okrugs, while the old ADM2 source groups all as Raion. Name/type rosters alone do not establish that these multipart polygons are equivalent or exhaustive.",
        "recommendation": "Keep the 2017 component count as a source fact only. Restore current law annexes or an authorized official boundary layer, align every component to that source, and report unresolved islands/disconnected areas. No geometry edit is proposed.",
    }


def main():
    raw = ASSESSMENT_PATH.read_bytes()
    if sha256(raw) != ASSESSMENT_SHA256:
        raise SystemExit("pinned parent assessment bytes differ")
    parent = json.loads(raw)
    if parent["issue"] != 395 or parent["base_commit"] != BASELINE_COMMIT:
        raise SystemExit("unexpected parent assessment vintage")
    selected = [r for r in parent["rows"] if r["assessment"] != "justified"]
    ids = sorted(r["atlas_id"] for r in selected)
    subject_hash = exact_scope(ids)
    if subject_hash != EXPECTED_SCOPE_HASH:
        raise SystemExit("derived subject roster does not match issue #1092")
    controls = {"positive_exact_roster": "passed"}
    for invalid in (ids[:-1], sorted(ids + [ids[0]])):
        try:
            exact_scope(invalid)
        except ValueError:
            continue
        raise SystemExit("negative scope control unexpectedly passed")
    controls["negative_missing_or_duplicate_subject"] = "passed"
    rows = []
    for r in sorted(selected, key=lambda item: item["atlas_id"]):
        if r["source_kind"] == "ecoregion-raion-fragment":
            category = "ecoregion-fragment"
        elif CITY_TEXT in r["rationale"]:
            category = "city-name-role"
        else:
            category = "multipart-component-review"
        detail = role_review(r, category)
        rows.append({
            "subject_id": r["atlas_id"],
            "name": r["atlas_name"],
            "source_unit_id": r["source_unit_id"],
            "source_unit_name": r["source_unit_name"],
            "parent_id": r["parent_id"],
            "parent_name": r["province_name"],
            "source_kind": r["source_kind"],
            "source_role": r["atlas_source_role"],
            "source_boundary_year": r["source_boundary_year"],
            "source_data_update_date": r["source_data_update_date"],
            "source_build_date": r["source_build_date"],
            "source_license": r["source_dataset_license"],
            "source_geometry_type": r["geometry_type"],
            "source_component_count": r["component_count"],
            "category": category,
            "assessment": detail.pop("status"),
            "source_feature_sha256": r["source_evidence_sha256"],
            "prior_assessment": r["assessment"],
            "prior_rationale": r["rationale"],
            "sources": source_refs(r, category),
            **detail,
        })
    counts = {name: sum(row["category"] == name for row in rows) for name in
              ("ecoregion-fragment", "city-name-role", "multipart-component-review")}
    if counts != {"ecoregion-fragment": 11, "city-name-role": 25, "multipart-component-review": 9}:
        raise SystemExit(f"unexpected category counts: {counts}")
    if len(rows) != 45:
        raise SystemExit("subject count mismatch")
    output = {
        "version": 1,
        "issue": 1092,
        "source_issue": 395,
        "review_base_commit": CURRENT_BASE,
        "prior_packet_baseline_commit": BASELINE_COMMIT,
        "subject_ids_sha256": subject_hash,
        "counts": counts,
        "controls": controls,
        "assessments": rows,
        "scope_limit": "Source and role evidence only. No current legal boundary geometry was verified for the 45 subjects; the packet does not certify a regional interior.",
    }
    out = OWNED / "findings/followup-assessments.json"
    out.write_bytes(canonical(output))
    scope = {
        "version": 1,
        "issue": 1092,
        "parent_issue": 395,
        "base_commit": CURRENT_BASE,
        "subject_ids": ids,
        "subject_ids_sha256": subject_hash,
        "owned_paths": ["data/regional-review/west-siberia-roles-followup-20261006/"],
        "pins": ISSUE_PINS,
    }
    scope_path = OWNED / "baseline/issue-contract.json"
    scope_path.write_bytes(canonical(scope))
    for control_kind in ("positive-control", "negative-control"):
        control = {"method_id": "followup-generator", "kind": control_kind, "outcome": "passed", "positive": control_kind == "positive-control", "evidence": controls}
        (OWNED / f"findings/{control_kind}.json").write_bytes(canonical(control))
    print(json.dumps({"assessment_sha256": sha256(out.read_bytes()), "issue_contract_sha256": sha256(scope_path.read_bytes()), "subject_ids_sha256": subject_hash, "counts": counts, "controls": controls}, sort_keys=True))


if __name__ == "__main__":
    main()
