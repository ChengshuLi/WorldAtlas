#!/usr/bin/env python3
"""Check the retained seven-case result ledger without rerunning GIS."""
from __future__ import annotations
import copy, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "physical-applicability-v1.json"
PLAN = ROOT / "bounded-measurement-plan.json"
OVERLAY = ROOT.parents[0] / "norway-adm2-source-fit-1492/vintages/exact-overlay-acceptance-20261008/overlay-v1.json"
METHOD = "norway-physical-applicability-measurement"
EXPECTED_IDS = {
    "physical-component:1f5426f5180aa4f5b7fd9991b5ae4816d56cb642c31d0937a4977da516f28f2b",
    "physical-component:764b247eb21da38adac0b925bededbbb4dccaefa4b52b16976f20543a7ac3384",
    "physical-component:7bad7bdf9b1203fe6c676eb2efde10b09ce394ad7d6d554eb557709d7704df35",
    "physical-component:8fb9f3f0d7df1c96ac452792fd4a9dbc7a45a576437550dd5b198424ceca14a9",
    "physical-component:a92cac9c4c3d3a91286eca0e4890becd63441647c7fe7c4cdcc5e1aa167d4803",
    "physical-component:b6ba064b4525f0c75459a8d1aa05c25e9740cc46b9964f96983d61d6a9b4253a",
    "physical-component:eb2b6c25d1a2b8ead2bcb67f7e0423b5f1cc5609ac3f600bb98cd6d5cb11db40",
}

def validate(data: dict, overlay: dict) -> None:
    cases = data["cases"]
    if {row["component_id"] for row in cases} != EXPECTED_IDS or len(cases) != 7:
        raise ValueError("seven-subject roster mismatch")
    if data["scope"]["candidate_context_count"] != 15 or data["scope"]["complete_family_member_count"] != 400 or data["scope"]["positive_length_neighbor_count"] != 36:
        raise ValueError("15/400/36 context mismatch")
    if set(data["scope"]["candidate_ids"]) != set(overlay["scope"]["selected_ids"]):
        raise ValueError("selected candidate context differs from predecessor")
    if data["scope"]["family_member_ids"] != overlay["scope"]["complete_family_member_ids"] or data["scope"]["neighbor_ids"] != overlay["scope"]["complete_positive_length_neighbor_ids"]:
        raise ValueError("complete family or neighbor roster differs from predecessor")
    ctl = data["controls"]
    if not ctl["all_7_added_areas_equal_pinned_1492_receipt"] or ctl["relation_rows"] != 252 or ctl["expected_relation_rows"] != 252 or ctl["own_target_rows"] != 7 or ctl["evaluated_neighbor_relations"] != 245:
        raise ValueError("receipt or neighbor ledger closure mismatch")
    if len(data["neighbor_relations"]) != 252 or sum(x["relation_status"] == "own-current-target-preserved-by-union" for x in data["neighbor_relations"]) != 7:
        raise ValueError("neighbor row population mismatch")
    if any(row["status"] == "physical-applicability-resolved" for row in cases) or data["stages"]["geographic_approval"] != "unapproved":
        raise ValueError("unknown physical classification was promoted")
    if data["stages"]["implementation"] != "not-proposed":
        raise ValueError("implementation proposal was introduced")

def main() -> None:
    data=json.loads(RESULT.read_text()); plan=json.loads(PLAN.read_text()); overlay=json.loads(OVERLAY.read_text())
    validate(data,overlay)
    positive={"version":1,"method_id":METHOD,"kind":"positive-control","outcome":"passed","checks":{"exact_seven_subjects":True,"15_400_36_context_matches_predecessor":True,"all_added_area_receipts_match":True,"252_relation_rows_close":True,"7_own_targets_and_245_neighbor_relations":True,"no_physical_approval_or_implementation_claim":True},"result_sha256":hashlib.sha256(RESULT.read_bytes()).hexdigest()}
    positive_path=ROOT/"control-positive.json"; positive_path.write_text(json.dumps(positive,indent=2)+"\n")
    negative_checks=[]
    altered=copy.deepcopy(data); altered["scope"]["complete_family_member_count"]=399
    try: validate(altered,overlay)
    except ValueError as exc: negative_checks.append({"mutation":"family_member_count=399","rejected":True,"reason":str(exc)})
    else: raise SystemExit("negative control failed: mutated family count was accepted")
    altered=copy.deepcopy(data); altered["neighbor_relations"].pop()
    try: validate(altered,overlay)
    except ValueError as exc: negative_checks.append({"mutation":"remove_one_neighbor_relation","rejected":True,"reason":str(exc)})
    else: raise SystemExit("negative control failed: missing neighbor row was accepted")
    negative={"version":1,"method_id":METHOD,"kind":"negative-control","outcome":"passed","checks":negative_checks,"result_sha256":hashlib.sha256(RESULT.read_bytes()).hexdigest()}
    (ROOT/"control-negative.json").write_text(json.dumps(negative,indent=2)+"\n")
    print(json.dumps({"status":"passed","positive":positive,"negative":negative},indent=2))

if __name__=="__main__": main()
