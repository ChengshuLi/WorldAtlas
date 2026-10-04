#!/usr/bin/env python3
"""Verify source fingerprints, exact issue scope, and deterministic full assessment."""
from __future__ import annotations
import csv, gzip, hashlib, json, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parent
REPO=ROOT.parents[2]

def sha(b): return hashlib.sha256(b).hexdigest()
def file_sha(path): return sha(pathlib.Path(path).read_bytes())

def check(condition, message):
    if not condition: raise AssertionError(message)

scope=json.loads((ROOT/"scope.json").read_text())
issue_scope=json.loads((ROOT/"issue-scope-pinned.json").read_text())
issue=json.loads((ROOT/"issue-metadata.json").read_text())
check(issue["number"]==479,"actual issue metadata must be #479")
check(issue_scope["member_location_ids"]==scope["member_location_ids"],"pinned scope IDs changed")
check(sha((ROOT/"issue-scope-pinned.json").read_bytes())==scope["issue_scope_sha256"],"issue scope snapshot hash mismatch")
ids=scope["member_location_ids"]
check(len(ids)==49 and len(set(ids))==49,"scope must be exactly 49 unique IDs")
check(sha("\n".join(ids).encode())==scope["member_location_ids_sha256"],"member ID digest mismatch")
check(sum(i.startswith("gb:SLE:ADM2:") for i in ids)==12,"Sierra Leone scope count mismatch")
check(sum(i.startswith("gb:TGO:ADM2:") for i in ids)==37,"Togo scope count mismatch")
claim=json.loads((ROOT/"claim-receipt.json").read_text())
check(claim["accepted"] and claim["issue_number"]==479 and claim["claim"]["active"],"confirmed active claim receipt required")
check(claim["claim"]["owned_paths"]==["data/regional-review/regional-review-9d08839e1cdb0c8f/"],"claim owned path mismatch")

baseline=scope["published_region_baseline"]
check(baseline["baseline_git_commit"]=="cf6598d9f6b7a03a0953006ba47bc0af565ac6e8","baseline commit must remain truthful")
for path,want in baseline["authoritative_snapshot_hashes"].items():
    check(file_sha(REPO/path)==want,f"baseline source snapshot changed: {path}")
projection=json.loads(gzip.decompress((REPO/baseline["current_projection_snapshot"]).read_bytes()))
projected={r["id"]:r for r in projection["locations"]}
baseline_rows=json.loads((ROOT/"baseline-members.json").read_text())
check([projected[i] for i in ids]==baseline_rows,"member inventory does not reproduce from the pinned main projection snapshot")

acq=json.loads((ROOT/"sources/acquisition.json").read_text())
retained=[]
def walk(value):
    if isinstance(value,dict):
        if isinstance(value.get("file"),str) and "gzip_sha256" in value and "restored_sha256" in value: retained.append(value)
        for v in value.values(): walk(v)
    elif isinstance(value,list):
        for v in value: walk(v)
walk(acq)
check(retained,"source register has no retained original files")
for record in retained:
    path=ROOT/record["file"].replace("sources/","sources/",1)
    compressed=path.read_bytes()
    check(len(compressed)==record["gzip_bytes"],f"compressed source size mismatch: {path.name}")
    check(sha(compressed)==record["gzip_sha256"],f"compressed source hash mismatch: {path.name}")
    raw=gzip.decompress(compressed)
    check(len(raw)==record["restored_bytes"],f"restored source size mismatch: {path.name}")
    check(sha(raw)==record["restored_sha256"],f"restored source hash mismatch: {path.name}")

register=json.loads((ROOT/"sources.json").read_text())
check(len(register["sources"])==7,"canonical source register incomplete")
check((ROOT/"physical-source-access.json").exists(),"physical source access limitation missing")
settlement_validation=json.loads((ROOT/"settlement-validation.json").read_text())
check(settlement_validation["source_file_sha256"]=="14dfbb508605c7c6c8937a9197c505f683f0f73be74c3c1c673aba1c03ffb0a7","analysis-only source hash mismatch")

outputs=["assessment.json","assessment.csv","admin-groups.csv","admin1-source-comparison.csv","geometry-components.csv","settlement-point-anomalies.csv","source-vintage-crosswalk.csv","city-role-screen.json"]
before={name:file_sha(ROOT/name) for name in outputs}
subprocess.run([sys.executable,str(ROOT/"build_assessment.py")],cwd=REPO,check=True,stdout=subprocess.DEVNULL)
after={name:file_sha(ROOT/name) for name in outputs}
check(before==after,"assessment outputs are not byte deterministic")
assessment=json.loads((ROOT/"assessment.json").read_text())
rows=assessment["members"]
check(len(rows)==49 and len({r["id"] for r in rows})==49,"assessment must account for every unique pinned subject")
check({r["id"] for r in rows}==set(ids),"assessment subject inventory differs from the exact issue inventory")
check(sum(r["assessment_status"]=="correction-needed" for r in rows)==2,"expected exactly two sourced parent corrections")
check(sum(r["assessment_status"]=="insufficient-evidence" for r in rows)==47,"unresolved classifications must remain explicit")
check(sum(r["parent_assignment_assessment"]=="supported" for r in rows)==47,"parent assessment count mismatch")
check(sum(r["parent_assignment_assessment"]=="correction-needed" for r in rows)==2,"parent correction count mismatch")
check(sum(r["settlement_rows_for_current_code"] for r in rows)==13371,"scoped settlement code row count changed")
check(sum(r["settlement_points_outside_current_polygon"] for r in rows)==593,"spatial settlement anomaly count changed")
check(all(r["settlement_rows_for_current_code"]>0 for r in rows),"a pinned subject lacks a sourced settlement assessment")
check(len(list(csv.DictReader((ROOT/"geometry-components.csv").open())))==181,"component census incomplete")
check(len(list(csv.DictReader((ROOT/"settlement-point-anomalies.csv").open())))==593,"settlement outlier inventory incomplete")
check(len(list(csv.DictReader((ROOT/"source-vintage-crosswalk.csv").open())))==253,"positive-area crosswalk inventory incomplete")
check(len(list(csv.DictReader((ROOT/"admin-groups.csv").open())))==10,"area and province scope assessment incomplete")
check(assessment["area_and_province_assessment_count"]==10,"area/province group count mismatch")
check(len(assessment["admin1_source_comparison"]["rows"])==10,"admin1 source comparison incomplete")
city=json.loads((ROOT/"city-role-screen.json").read_text())
check([r["name"] for r in city["features"]]==["Lome Commune","Golfe","Agoe-Nyive"],"Lome urban-role screen incomplete")
check([r["polygon_components"] for r in city["features"]]==[1,2,1],"Lome source component inventory changed")
check([r["WCA_settlement_points_by_current_code"] for r in city["features"]]==[137,121,156],"Lome point screen changed")
check(len(city["shared_boundaries"])==3 and "remains unresolved" in city["finding"],"Lome continuity uncertainty missing")
check(all(n["areal_overlap_km2"]==0 for n in assessment["neighbor_edge_screen"]),"neighbor edge screen reports unresolved area overlap")
check(assessment["settlement_source_axis_check"]["geometry_x_matches_LAT_and_y_matches_LONG_within_1e-6"]==14981,"point coordinate axis screen changed")
check([x["name"] for x in assessment["scope_deltas"][0]["current_units_unmatched_to_legacy_names"]]==["Fabala","Karene"],"Sierra Leone source delta changed")
check([x["name"] for x in assessment["scope_deltas"][1]["current_units_unmatched_to_legacy_names"]]==["Agoe-Nyive","Naki-Ouest","Oti-Sud"],"Togo source delta changed")
check((ROOT/"correction-recommendations.json").exists(),"follow-up recommendations missing")
verification={"status":"passed","issue":479,"subjects_assessed":49,"area_and_province_groups_assessed":10,"admin1_cross_source_units_compared":10,"city_role_screen_features":3,"source_original_files_hash_checked":len(retained),
 "deterministic_outputs":outputs,"settlement_rows":13371,"settlement_geometry_outliers":593,
 "disconnected_components":181,"source_vintage_overlap_pairs":253,"neighbor_edges_screened":4,
 "limitations":"This verifies source integrity and reproducible evidence artifacts only; no geography, region, political ownership, or historical import is approved."}
(ROOT/"verification.json").write_text(json.dumps(verification,indent=2)+"\n")
print(json.dumps(verification,indent=2))
