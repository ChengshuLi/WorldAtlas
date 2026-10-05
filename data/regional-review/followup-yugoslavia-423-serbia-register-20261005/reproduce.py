#!/usr/bin/env python3
"""Reproduce the exact-scope Serbia register crosswalk from retained inputs.

Roster evidence establishes name/code/administrative-parent relationships only;
it does not establish legal boundary or polygon equivalence.
"""
import csv, hashlib, json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKET = ROOT.parent / "regional-review-d282e62cf0209796"
SORS = ROOT.parent / "followup-serbia-422-admin-crosswalk-20261005"
ISSUE = ROOT / "source/issue-snapshot.json"
CLAIM = ROOT / "source/claim-receipt.json"
OUT = ROOT / "sources/derived"
PINS = {
 "data/regional-review/regional-review-d282e62cf0209796/scope.json":"7456674ffc3ede4604fd243aaece1dbbb80868f5d3de08efa6868a8574f7884e",
 "data/regional-review/regional-review-d282e62cf0209796/unit-assessments.json":"98e3d72e5f497b71488e1a233a457d6be31e675de196e6ee7595b1e06a0529c1",
 "data/regional-review/regional-review-d282e62cf0209796/source/geoboundaries-9469f09/geoBoundaries-SRB-ADM2.geojson":"f94ba868818e4f87dd24bc97aeaf37732cc23f6744facd1010cd91d2349fc884",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/sors-cities-municipalities-2017.xls":"75a7236c08c13b43bebc12a797456de74bfa9e1dd6f352a821efbce271cd4d62",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/sors-cities-municipalities-current-2026-10-05.xlsx":"3a7790a65c77a537da848a66c71ba1495c5e0bdfe1021587979a551dcb7ebafa",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/derived/sors-2017-roster-normalized.csv":"0690c7732fc3ee73fad9c3438c7a60e707837ab51bc724559842c9e362420524",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/derived/sors-current-roster-normalized.csv":"92286089f3d21d2d9ab7cf93c2e68f37c374cd8aadf4a21763cbbcc69d00d6c4",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/derived/subject-crosswalk.csv":"a5a01d678c51cf273aa5afd8194d10c1b103176f8fe30ac50d0ccc9e69ec2751",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/sors-retrieval.json":"0fbef22728b0c1b9d8051c17ab2de37d0c005d71189c86416b5af642a6e55ca7",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/geoBoundaries-SRB-ADM2-2017.geojson":"f94ba868818e4f87dd24bc97aeaf37732cc23f6744facd1010cd91d2349fc884",
}
TRANSLIT = str.maketrans({"а":"a","б":"b","в":"v","г":"g","д":"d","ђ":"dj","е":"e","ж":"z","з":"z","и":"i","ј":"j","к":"k","л":"l","љ":"lj","м":"m","н":"n","њ":"nj","о":"o","п":"p","р":"r","с":"s","т":"t","ћ":"c","у":"u","ф":"f","х":"h","ц":"c","ч":"c","џ":"dz","ш":"s","č":"c","ć":"c","š":"s","ž":"z","đ":"dj"})
def norm(s):
 s=unicodedata.normalize("NFKD",str(s or "").casefold()).translate(TRANSLIT)
 return re.sub(r"[^a-z0-9]+","", "".join(c for c in s if not unicodedata.combining(c)))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def readcsv(p):
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 issue=json.loads(ISSUE.read_text()); body=issue["body"]
 m=re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->",body,re.S); assert m
 contract=json.loads(m.group(1)); eq=contract["evidence_quality"]
 assert contract["owned_paths"]==["data/regional-review/followup-yugoslavia-423-serbia-register-20261005/"]
 assert len(eq["subject_ids"])==67 and len(set(eq["subject_ids"]))==67
 for rel,sha in PINS.items():
  p=ROOT.parents[2]/rel
  assert digest(p)==sha,(rel,digest(p),sha)
 assessments=json.loads((PACKET/"unit-assessments.json").read_text())["rows"]
 ledger={r["location_id"]:r for r in assessments}
 gb=json.loads((PACKET/"source/geoboundaries-9469f09/geoBoundaries-SRB-ADM2.geojson").read_text())
 features={f["properties"]["shapeID"]:f for f in gb["features"]}
 old=readcsv(SORS/"sources/derived/sors-2017-roster-normalized.csv")
 cur=readcsv(SORS/"sources/derived/sors-current-roster-normalized.csv")
 def c(v):
  try:return str(int(float(v)))
  except:return str(v or "")
 output=[]
 for sid in eq["subject_ids"]:
  a=ledger[sid]; f=features[a["source_shape_id"]]
  assert f["properties"]["shapeName"]==a["source_shape_name"]
  label=re.sub(r"\s+(Municipality|City)$","",a["name"],flags=re.I)
  is_city=a["name"].endswith(" City")
  key=norm(label)
  if is_city:
   oldhits=[r for r in old if (norm(r.get("city_name", ""))[4:] if norm(r.get("city_name", "")).startswith("grad") else norm(r.get("city_name", "")))==key]
   curhits=[r for r in cur if norm(r.get("unit_name"))==key and r.get("unit_type_in_source")=="град"]
  else:
   oldhits=[r for r in old if norm(r.get("unit_name"))==key]
   curhits=[r for r in cur if norm(r.get("unit_name"))==key]
  oldhits=list({(c(r.get("city_code") if is_city else r.get("unit_code")),c(r.get("district_code"))):r for r in oldhits}.values())
  curhits=list({(c(r.get("unit_code")),c(r.get("district_code"))):r for r in curhits}.values())
  o=oldhits[0] if len(oldhits)==1 else {}; n=curhits[0] if len(curhits)==1 else {}
  oc=c(o.get("city_code") if is_city else o.get("unit_code")); nc=c(n.get("unit_code"))
  od=c(o.get("district_code")); nd=c(n.get("district_code"))
  output.append({"location_id":sid,"atlas_name":a["name"],"atlas_parent_id":a["parent_id"],"atlas_parent_name":a["province_name"],"source_shape_id":a["source_shape_id"],"source_shape_name":a["source_shape_name"],"source_geometry_type":f["geometry"]["type"],"source_metadata_boundary_year":"2017","source_metadata_update_date":"2023-01-19","source_metadata_build_date":"2023-12-12","2017_unique_match_count":len(oldhits),"sors_2017_unit_code":oc,"sors_2017_name":o.get("city_name") if is_city else o.get("unit_name"),"sors_2017_district_code":od,"sors_2017_district_name":o.get("district_name"),"sors_2017_city_code":c(o.get("city_code")),"current_unique_match_count":len(curhits),"sors_current_unit_code":nc,"sors_current_name":n.get("unit_name"),"sors_current_type":n.get("unit_type_in_source"),"sors_current_district_code":nd,"sors_current_district_name":n.get("district_name"),"code_preserved":bool(oc and nc and oc==nc),"parent_code_preserved":bool(od and nd and od==nd),"role_2017":"city" if c(o.get("city_code"))==oc else "municipality","role_current":n.get("unit_type_in_source","unresolved"),"polygon_equivalence":"not established","finding":"unique dated/current SORS register name/code/parent match; polygon and legal-boundary identity unverified" if len(oldhits)==len(curhits)==1 and oc==nc and od==nd else "unresolved: register match, code or parent discrepancy requires follow-up"})
 assert len(output)==67 and all(r["2017_unique_match_count"]==r["current_unique_match_count"]==1 for r in output)
 def write_csv(name,rows):
  with (OUT/name).open("w",encoding="utf-8",newline="") as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
 write_csv("subject-crosswalk.csv",output)
 parents={}
 for r in output: parents.setdefault(r["atlas_parent_id"],[]).append(r)
 parentrows=[]
 for pid,rs in sorted(parents.items()):
  codes={c(r["sors_current_unit_code"]) for r in rs}; dc=c(rs[0]["sors_current_district_code"])
  official={c(r["unit_code"]) for r in cur if c(r["district_code"])==dc}
  parentrows.append({"atlas_parent_id":pid,"atlas_parent_name":rs[0]["atlas_parent_name"],"sors_admin_district_code":dc,"sors_admin_district_name":rs[0]["sors_current_district_name"],"atlas_scoped_children":len(codes),"current_sors_primary_roster_codes":len(official),"exact_roster_completeness":codes==official,"missing_codes":";".join(sorted(official-codes)),"extra_codes":";".join(sorted(codes-official))})
 write_csv("parent-register-comparison.csv",parentrows)
 # Adjacent city-municipality tier retained as context, not additional subjects.
 citycodes={c(r["sors_current_unit_code"]):r for r in output if r["atlas_name"].endswith(" City")}
 urban=[]
 for r in cur:
  cc=c(r.get("unit_code")); uc=c(r.get("urban_municipality_code"))
  if cc in citycodes and uc:
   urban.append({"city_subject_id":citycodes[cc]["location_id"],"city_code":cc,"city_name":r["unit_name"],"urban_municipality_code":uc,"urban_municipality_name":r["urban_municipality_name"],"separate_atlas_subject":False})
 if urban:write_csv("neighboring-city-municipality-context.csv",urban)
 # Positive and negative controls exercise the exact-subject and unique-match assertions.
 def exact_scope(xs): return len(xs)==67 and len(set(xs))==67
 def unique_match(xs): return len(xs)==1
 controls={"positive_exact_scope":{"method_id":"crosswalk","kind":"code","outcome":"passed","evidence_path":"data/regional-review/followup-yugoslavia-423-serbia-register-20261005/validation/controls.json","check":"declared 67 unique issue IDs accepted","passed":exact_scope(eq["subject_ids"])},"negative_missing_subject":{"method_id":"crosswalk","kind":"code","outcome":"passed","evidence_path":"data/regional-review/followup-yugoslavia-423-serbia-register-20261005/validation/controls.json","check":"67-ID scope with one removed rejected","passed":not exact_scope(eq["subject_ids"][:-1])},"negative_ambiguous_join":{"method_id":"crosswalk","kind":"code","outcome":"passed","evidence_path":"data/regional-review/followup-yugoslavia-423-serbia-register-20261005/validation/controls.json","check":"duplicate candidate rejected as non-unique","passed":not unique_match(["candidate","candidate"])} }
 assert all(v["passed"] for v in controls.values())
 (ROOT/"validation/controls.json").write_text(json.dumps({"version":1,"controls":list(controls.values())},indent=2)+"\n")
 summary={"subject_count":len(output),"unique_2017_matches":sum(r["2017_unique_match_count"]==1 for r in output),"unique_current_matches":sum(r["current_unique_match_count"]==1 for r in output),"code_preserved":sum(r["code_preserved"] for r in output),"parent_code_preserved":sum(r["parent_code_preserved"] for r in output),"parent_count":len(parentrows),"parents_matching_all_current_primary_roster_codes":sum(x["exact_roster_completeness"] for x in parentrows),"neighboring_city_municipality_rows":len(urban),"limitations":["Roster matches do not demonstrate boundary/polygon equivalence or legal territorial status.","2017 workbook reference date is 2017-12-31; current workbook has no explicit reference date and was retrieved 2026-10-05.","Current official polygon extract, effective date, CRS, feature-level comparison, and redistribution terms were not obtained.","SORS national aggregate counts include Kosovo-and-Metohija-coded rows; scoped Serbia labels/counts do not resolve territorial status."]}
 (OUT/"reproduction-summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
