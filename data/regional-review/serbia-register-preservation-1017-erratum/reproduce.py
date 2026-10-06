#!/usr/bin/env python3
"""Reproduce the exact-scope Serbia register crosswalk from retained inputs.

Roster evidence establishes name/code/administrative-parent relationships only;
it does not establish legal boundary or polygon equivalence.
"""
import argparse, csv, hashlib, io, json, re, subprocess, sys, tempfile, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
BASELINE_COMMIT = "efc79fe809a05cff04aa4d0446c8dc169e8c639f"
sys.path.insert(0, str(REPO / "scripts"))
from evidence.immutable import Baseline, VERSION as PREPARATION_VERSION
PACKET = REPO / "data/regional-review/regional-review-d282e62cf0209796"
SORS = REPO / "data/regional-review/followup-serbia-422-admin-crosswalk-20261005"
UPSTREAM = REPO / "data/regional-review/followup-yugoslavia-423-serbia-register-20261005"
ISSUE = ROOT / "source/issue-snapshot.json"
CLAIM = ROOT / "source/claim-receipt.json"
OUT = ROOT / "outputs/run"
VALIDATION = ROOT / "validation/run"
PINS = {
 "data/regional-review/regional-review-d282e62cf0209796/scope.json":"7456674ffc3ede4604fd243aaece1dbbb80868f5d3de08efa6868a8574f7884e",
 "data/regional-review/regional-review-d282e62cf0209796/unit-assessments.json":"98e3d72e5f497b71488e1a233a457d6be31e675de196e6ee7595b1e06a0529c1",
 "data/regional-review/regional-review-d282e62cf0209796/source/geoboundaries-9469f09/geoBoundaries-SRB-ADM2.geojson":"f94ba868818e4f87dd24bc97aeaf37732cc23f6744facd1010cd91d2349fc884",
 "data/regional-review/regional-review-d282e62cf0209796/source/geoboundaries-9469f09/geoBoundaries-SRB-ADM2-metaData.json":"65d65d75249a6b766fc5e7bc0d856d1cca9ea67d04b53db1a151678891c11312",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/sors-cities-municipalities-2017.xls":"75a7236c08c13b43bebc12a797456de74bfa9e1dd6f352a821efbce271cd4d62",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/sors-cities-municipalities-current-2026-10-05.xlsx":"3a7790a65c77a537da848a66c71ba1495c5e0bdfe1021587979a551dcb7ebafa",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/derived/sors-2017-roster-normalized.csv":"0690c7732fc3ee73fad9c3438c7a60e707837ab51bc724559842c9e362420524",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/derived/sors-current-roster-normalized.csv":"92286089f3d21d2d9ab7cf93c2e68f37c374cd8aadf4a21763cbbcc69d00d6c4",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/derived/subject-crosswalk.csv":"a5a01d678c51cf273aa5afd8194d10c1b103176f8fe30ac50d0ccc9e69ec2751",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/sors-retrieval.json":"0fbef22728b0c1b9d8051c17ab2de37d0c005d71189c86416b5af642a6e55ca7",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/geoBoundaries-SRB-ADM2-2017.geojson":"f94ba868818e4f87dd24bc97aeaf37732cc23f6744facd1010cd91d2349fc884",
 "data/regional-review/followup-serbia-422-admin-crosswalk-20261005/source-issue-998.json":"14ee2b74b7553e94a4a6280d3133ede8be7006cc2585df547b11486663d3bcab",
 "data/regional-review/followup-yugoslavia-423-serbia-register-20261005/evidence-quality.json":"b1960ec2d570c3cb25face81996f32530acffa0d10a2776f6dac04a2f8b90c35",
 "data/regional-review/followup-yugoslavia-423-serbia-register-20261005/source/baseline-inputs.json":"83142e579ad8d5ad6f1d7465867222911d5a53f12705909e2d8fcbcbb5a8645a",
 "data/regional-review/followup-yugoslavia-423-serbia-register-20261005/RESEARCH.md":"f66680723d42d19a0d2dcfc562d397164d0a9ee4f5404c50624700fe32ca23fc",
 "data/regional-review/followup-yugoslavia-423-serbia-register-20261005/reproduce.py":"132d8d1029a6bd6aa8d9d70096bfd1f02f1fafef9f7a00c20573c101772bf51e",
 "data/regional-review/followup-yugoslavia-423-serbia-register-20261005/source/claim-receipt.json":"65ecd5614fb822e5541d17ae81f355798c0aaff42a0ab27c11a23279466bf88a",
 "data/regional-review/followup-yugoslavia-423-serbia-register-20261005/source/issue-snapshot.json":"069823947dd744094f94f0d7b8fce5c098068fc5df4390496cc8b5a3cb3f4cd6",
 "data/regional-review/followup-yugoslavia-423-serbia-register-20261005/sources/derived/neighboring-city-municipality-context.csv":"dee71868bcad9d57b4b9806f3fc30eb1f0ddee0ea4c0abd486e464daa0c29c69",
 "data/regional-review/followup-yugoslavia-423-serbia-register-20261005/sources/derived/parent-register-comparison.csv":"55202bca39e3bd5e5df17afaf398af8b687f8973788fb163dbe883be47469a29",
 "data/regional-review/followup-yugoslavia-423-serbia-register-20261005/sources/derived/reproduction-summary.json":"01246dc83a59a5a9029c6e953f22889e989d3168dd312c59c4f04576b5e9d1af",
 "data/regional-review/followup-yugoslavia-423-serbia-register-20261005/sources/derived/subject-crosswalk.csv":"c3e30e6d773056f55e20a39b073beff54eadc485bc547931f36f7e5c134e926f",
 "data/regional-review/followup-yugoslavia-423-serbia-register-20261005/validation/controls.json":"c7aa5fcfd04119d66800c3fca8764c647b1a6fa3c896203f6ec5e72b1a8013a2",
 "data/geography/part-22.json":"f7ac47c8a9012651773264a31bfd6b360394ad029dd1f9cf88d63150953070d3",
 "data/hierarchy.json":"568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b",
 "data/world-index.json":"a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03",
}
ORIGINAL_OUTPUTS = {
 "sources/derived/subject-crosswalk.csv":"c3e30e6d773056f55e20a39b073beff54eadc485bc547931f36f7e5c134e926f",
 "sources/derived/parent-register-comparison.csv":"55202bca39e3bd5e5df17afaf398af8b687f8973788fb163dbe883be47469a29",
 "sources/derived/neighboring-city-municipality-context.csv":"dee71868bcad9d57b4b9806f3fc30eb1f0ddee0ea4c0abd486e464daa0c29c69",
 "sources/derived/reproduction-summary.json":"01246dc83a59a5a9029c6e953f22889e989d3168dd312c59c4f04576b5e9d1af",
 "validation/controls.json":"c7aa5fcfd04119d66800c3fca8764c647b1a6fa3c896203f6ec5e72b1a8013a2",
}
TRANSLIT = str.maketrans({"а":"a","б":"b","в":"v","г":"g","д":"d","ђ":"dj","е":"e","ж":"z","з":"z","и":"i","ј":"j","к":"k","л":"l","љ":"lj","м":"m","н":"n","њ":"nj","о":"o","п":"p","р":"r","с":"s","т":"t","ћ":"c","у":"u","ф":"f","х":"h","ц":"c","ч":"c","џ":"dz","ш":"s","č":"c","ć":"c","š":"s","ž":"z","đ":"dj"})
def norm(s):
 s=unicodedata.normalize("NFKD",str(s or "").casefold()).translate(TRANSLIT)
 return re.sub(r"[^a-z0-9]+","", "".join(c for c in s if not unicodedata.combining(c)))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def readcsv(p):
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def readcsv_bytes(raw):
 with io.TextIOWrapper(io.BytesIO(raw),encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
EXPECTED_IDS_SHA256="b26fd29386bda15d9bc6544b3e83cda977abedac7222fa03f17bc3c29752ed0f"
METHOD="serbia-register-preservation"
def valid_scope(ids):
 return (isinstance(ids,list) and len(ids)==67 and all(isinstance(x,str) for x in ids)
         and len(set(ids))==67
         and hashlib.sha256(json.dumps(ids,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()==EXPECTED_IDS_SHA256)
def pin_matches(path,expected):
 return path.is_file() and digest(path)==expected
def preflight(destinations):
 existing=[str(p) for p in destinations if p.exists()]
 if existing: raise FileExistsError("refusing pre-existing output(s): "+", ".join(existing))
 root=ROOT.resolve()
 for path in destinations:
  requested=path.absolute()
  try: relative=requested.relative_to(root)
  except ValueError: raise ValueError("output path escapes the issue-owned prefix: "+str(path))
  cursor=root
  for part in relative.parts:
   cursor=cursor/part
   if cursor.exists() and cursor.is_symlink(): raise ValueError("symlink in output path: "+str(cursor))
  resolved=path.resolve()
  try: resolved.relative_to(root)
  except ValueError: raise ValueError("resolved output path escapes the issue-owned prefix: "+str(path))
def emit(products,out_dir):
 destinations={out_dir/name:data for name,data in products.items()}
 # Inspect all five destinations before creating directories or opening any output.
 preflight(destinations)
 handles=[]; created=[]
 try:
  for path in destinations:
   path.parent.mkdir(parents=True,exist_ok=True)
  for path in destinations:
   handle=path.open("xb"); handles.append((path,handle)); created.append(path)
  # All exclusive opens succeed before any product bytes are written.
  for path,handle in handles: handle.write(destinations[path])
  for _,handle in handles: handle.flush()
 except Exception:
  for _,handle in handles:
   try: handle.close()
   except Exception: pass
  for path in created:
   try:
    if path.stat().st_size==0:path.unlink()
   except FileNotFoundError: pass
  raise
 else:
  for _,handle in handles: handle.close()

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument("--output-dir",type=Path,required=True,help="new run directory; outputs are exclusive")
 args=parser.parse_args()
 if not args.output_dir.is_absolute(): args.output_dir=REPO/args.output_dir
 issue=json.loads(ISSUE.read_text()); body=issue["body"]
 assert issue["number"]==1186 and issue["state"]=="open"
 m=re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->",body,re.S); assert m
 contract=json.loads(m.group(1)); eq=contract["evidence_quality"]
 assert contract["owned_paths"]==["data/regional-review/serbia-register-preservation-1017-erratum/"]
 assert contract["evidence_quality"]["manifest_path"]=="data/regional-review/serbia-register-preservation-1017-erratum/evidence-quality.json"
 assert valid_scope(eq["subject_ids"]),"issue scope is missing, duplicated, outside the pinned roster or reordered"
 claim=json.loads(CLAIM.read_text())
 assert claim["issue_number"]==1186 and "\"accepted\":true" in claim["body"].replace(" ","")
 baseline_files=[]; immutable={}
 for rel,sha in PINS.items():
  raw=subprocess.check_output(["git","-C",str(REPO),"show",f"{BASELINE_COMMIT}:{rel}"])
  actual=hashlib.sha256(raw).hexdigest()
  assert actual==sha,(rel,actual,sha)
  baseline_files.append({"path":rel,"bytes":len(raw),"sha256":sha,"hash_kind":"file-bytes"})
  immutable[rel]=raw
 baseline=Baseline(REPO,BASELINE_COMMIT,baseline_files)
 for rel,sha in ORIGINAL_OUTPUTS.items():
  p=UPSTREAM/rel
  assert pin_matches(p,sha),("preserved original",rel,digest(p) if p.exists() else "missing",sha)
 assessments=json.loads(immutable["data/regional-review/regional-review-d282e62cf0209796/unit-assessments.json"])["rows"]
 ledger={r["location_id"]:r for r in assessments}
 hierarchy={r["id"]:r for r in json.loads(immutable["data/hierarchy.json"])}
 issue998=json.loads(immutable["data/regional-review/followup-serbia-422-admin-crosswalk-20261005/source-issue-998.json"])
 m998=re.search(r"<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->",issue998["body"],re.S); assert m998
 contract998=json.loads(m998.group(1)); ids998=contract998["evidence_quality"]["subject_ids"]
 assert len(ids998)==78 and len(set(ids998))==78 and not set(ids998).intersection(eq["subject_ids"])
 atlas=json.loads(immutable["data/geography/part-22.json"])
 atlas_rows=[f["properties"] for f in atlas["features"] if f.get("properties",{}).get("id") in eq["subject_ids"]]
 atlas_by_id={r["id"]:r for r in atlas_rows}
 assert len(atlas_rows)==len(atlas_by_id)==67
 gb=json.loads(immutable["data/regional-review/regional-review-d282e62cf0209796/source/geoboundaries-9469f09/geoBoundaries-SRB-ADM2.geojson"])
 features={f["properties"]["shapeID"]:f for f in gb["features"]}
 old=readcsv_bytes(immutable["data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/derived/sors-2017-roster-normalized.csv"])
 cur=readcsv_bytes(immutable["data/regional-review/followup-serbia-422-admin-crosswalk-20261005/sources/derived/sors-current-roster-normalized.csv"])
 def c(v):
  try:return str(int(float(v)))
  except:return str(v or "")
 output=[]
 for sid in eq["subject_ids"]:
  a=ledger[sid]; f=features[a["source_shape_id"]]
  af=atlas_by_id[sid]
  assert af["name"]==a["name"] and af["parent_id"]==a["parent_id"]
  parent=hierarchy.get(af["parent_id"])
  assert parent and parent["name"]==a["province_name"]
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
 assert all(r["code_preserved"] and r["parent_code_preserved"] for r in output)
 def csv_bytes(rows):
  f=io.StringIO(newline=""); w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
  return f.getvalue().encode("utf-8")
 parents={}
 for r in output: parents.setdefault(r["atlas_parent_id"],[]).append(r)
 parentrows=[]
 for pid,rs in sorted(parents.items()):
  codes={c(r["sors_current_unit_code"]) for r in rs}; dc=c(rs[0]["sors_current_district_code"])
  official={c(r["unit_code"]) for r in cur if c(r["district_code"])==dc}
  parentrows.append({"atlas_parent_id":pid,"atlas_parent_name":rs[0]["atlas_parent_name"],"sors_admin_district_code":dc,"sors_admin_district_name":rs[0]["sors_current_district_name"],"atlas_scoped_children":len(codes),"current_sors_primary_roster_codes":len(official),"exact_roster_completeness":codes==official,"missing_codes":";".join(sorted(official-codes)),"extra_codes":";".join(sorted(codes-official))})
 assert len(parentrows)==12
 # Adjacent city-municipality tier retained as context, not additional subjects.
 citycodes={c(r["sors_current_unit_code"]):r for r in output if r["atlas_name"].endswith(" City")}
 urban=[]
 for r in cur:
  cc=c(r.get("unit_code")); uc=c(r.get("urban_municipality_code"))
  if cc in citycodes and uc:
   urban.append({"city_subject_id":citycodes[cc]["location_id"],"city_code":cc,"city_name":r["unit_name"],"urban_municipality_code":uc,"urban_municipality_name":r["urban_municipality_name"],"separate_atlas_subject":False})
 assert len(urban)==9
 summary={"subject_count":len(output),"unique_2017_matches":sum(r["2017_unique_match_count"]==1 for r in output),"unique_current_matches":sum(r["current_unique_match_count"]==1 for r in output),"code_preserved":sum(r["code_preserved"] for r in output),"parent_code_preserved":sum(r["parent_code_preserved"] for r in output),"parent_count":len(parentrows),"parents_matching_all_current_primary_roster_codes":sum(x["exact_roster_completeness"] for x in parentrows),"neighboring_city_municipality_rows":len(urban),"limitations":["Roster matches do not demonstrate boundary/polygon equivalence or legal territorial status.","2017 workbook reference date is 2017-12-31; current workbook has no explicit reference date and was retrieved 2026-10-05.","Current official polygon extract, effective date, CRS, feature-level comparison, and redistribution terms were not obtained.","SORS national aggregate counts include Kosovo-and-Metohija-coded rows; scoped Serbia labels/counts do not resolve territorial status."]}
 # Exercise the actual admission and pin helpers with destructive cases in private scratch.
 with tempfile.TemporaryDirectory(dir=ROOT) as td:
  scratch=Path(td); last=scratch/"validation/controls.json"; last.parent.mkdir(parents=True)
  sentinel=b"AUDITOR EXISTING OUTPUT SENTINEL\n"; last.write_bytes(sentinel)
  attempted={scratch/name:b"new" for name in ["sources/derived/subject-crosswalk.csv","sources/derived/parent-register-comparison.csv","sources/derived/neighboring-city-municipality-context.csv","sources/derived/reproduction-summary.json","validation/controls.json"]}
  try: preflight(attempted)
  except FileExistsError: preserved=last.read_bytes()==sentinel and not any(p.exists() for p in list(attempted)[:-1])
  else: preserved=False
  wrong=scratch/"wrong-input"; wrong.write_bytes(b"mutated immutable input")
  wrong_pin_rejected=not pin_matches(wrong,PINS["data/world-index.json"])
  missing_rejected=not valid_scope(eq["subject_ids"][:-1])
  duplicate_rejected=not valid_scope(eq["subject_ids"][:-1]+[eq["subject_ids"][0]])
  outside_rejected=not valid_scope(eq["subject_ids"][:-1]+["gb:SRB:ADM2:OUTSIDE-SCOPE"])
  assert preserved and wrong_pin_rejected and missing_rejected and duplicate_rejected and outside_rejected
 controls={"method_id":METHOD,"kind":"generator","outcome":"passed","evidence_path":"data/regional-review/serbia-register-preservation-1017-erratum/validation/negative-control.json","checks":[
  {"control_id":"positive-exact-scope","outcome":"passed","detail":"exact 67-ID ordered issue roster accepted and tied to its canonical SHA256"},
  {"control_id":"negative-missing-subject","outcome":"passed","detail":"66-ID fixture rejected by the production scope validator before emission"},
  {"control_id":"negative-duplicate-subject","outcome":"passed","detail":"duplicate-ID fixture rejected by the production scope validator before emission"},
  {"control_id":"negative-outside-subject","outcome":"passed","detail":"outside-roster fixture rejected by the production scope validator before emission"},
  {"control_id":"negative-mutated-input","outcome":"passed","detail":"changed byte fixture rejected by the production whole-file pin verifier"},
  {"control_id":"negative-late-preexisting-output","outcome":"passed","detail":"fifth-destination sentinel rejected before any of the four earlier output paths were created; sentinel bytes unchanged"}
 ]}
 products={
  "sources/derived/subject-crosswalk.csv":csv_bytes(output),
  "sources/derived/parent-register-comparison.csv":csv_bytes(parentrows),
  "sources/derived/neighboring-city-municipality-context.csv":csv_bytes(urban),
  "sources/derived/reproduction-summary.json":(json.dumps(summary,ensure_ascii=False,indent=2)+"\n").encode(),
  "validation/controls.json":(json.dumps(controls,ensure_ascii=False,indent=2)+"\n").encode(),
 }
 expected_generated={
  "sources/derived/subject-crosswalk.csv":"c3e30e6d773056f55e20a39b073beff54eadc485bc547931f36f7e5c134e926f",
  "sources/derived/parent-register-comparison.csv":"55202bca39e3bd5e5df17afaf398af8b687f8973788fb163dbe883be47469a29",
  "sources/derived/neighboring-city-municipality-context.csv":"dee71868bcad9d57b4b9806f3fc30eb1f0ddee0ea4c0abd486e464daa0c29c69",
  "sources/derived/reproduction-summary.json":"01246dc83a59a5a9029c6e953f22889e989d3168dd312c59c4f04576b5e9d1af",
 }
 for rel,sha in expected_generated.items():
  assert hashlib.sha256(products[rel]).hexdigest()==sha,("reproduced historical output differs",rel)
 emit(products,args.output_dir)
 for rel,sha in ORIGINAL_OUTPUTS.items():
  assert pin_matches(UPSTREAM/rel,sha),("original output changed",rel)
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
