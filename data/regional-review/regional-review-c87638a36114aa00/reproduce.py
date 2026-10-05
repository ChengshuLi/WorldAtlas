#!/usr/bin/env python3
"""Reproduce identity, source-roster and non-geometric screening for issue #416.
No GIS overlay is performed. Official NSI package is optional and not redistributed.
"""
import argparse, csv, hashlib, json, pathlib, re, sqlite3, unicodedata
HERE=pathlib.Path(__file__).resolve().parent
REPO=HERE.parents[2]
SCOPE=json.loads((HERE/"scope.json").read_text())
IDS=set(SCOPE["member_location_ids"])
EXPECTED_SCOPE_SHA="a079a3eae5616a0fd1e1bf62580b44382de6438f14db51810a91f2848d412822"
EXPECTED_SOURCE={"ALB":"a81463d94654464bc2c668c45eb97a9d134e7d929d89b00ae155d2d634705e5a","BGR":"9283bb685efb08fa983934f4b986467c5495244cbd554dd9458b51e2857e9335","BIH":"d0196a097d9d517f7db6a8013889892c0ab5aab3d7dfd2e74fd5b22152ff8857"}
EXPECTED_METADATA={"ALB":"11f3c1c5841134e516260983ffa0ffaa8da9a1ff32e4eabdd577925baa77dc8f","BGR":"0d5e4e89424d470ff5f17e61606494f13a66842ad9b6ccebffd11f8aecea060b","BIH":"0f3b1b576502435a6a5c13465a06b2617074b19f93427ee1b4144fd6d36282b1"}
EXPECTED_BASELINE={"part-0.json":"bcad5408720e0f50165e794636fd44e02913e5e4649d73c8aa422b94562d32f3","part-1.json":"4f267b0bd2e29d2b6fcac27695dc60c919317f58d43cabef21518b5cdfde5ee7","part-2.json":"93eeb8f5dab7d8ca6c86593f7ab7b1310312757abcef33d4e7200a270624a1bf","part-29.json":"077e3bdfb18a42318e27bad840bba823a5049ced449407584fb4b9be2ef67c7a"}
def digest(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
 return h.hexdigest()
def norm(value):
 value=unicodedata.normalize("NFKD",str(value or "")).encode("ascii","ignore").decode().lower()
 return re.sub(r"[^a-z0-9]","",value)
def load_features(path): return json.loads(path.read_text())["features"]
base=[]
for path in sorted((REPO/"data/geography").glob("part-*.json")): base.extend(load_features(path))
baseline={f["properties"]["id"]:f for f in base}
assert digest(HERE/"scope.json")==EXPECTED_SCOPE_SHA
assert len(IDS)==230 and IDS.issubset(baseline)
for name,expected in EXPECTED_BASELINE.items():
 assert digest(REPO/"data/geography"/name)==expected, f"baseline pin mismatch: {name}"
by_iso={"ALB":[],"BGR":[],"BIH":[]}
for code,level in [("ALB","ADM2"),("BGR","ADM2"),("BIH","ADM3")]:
 src=HERE/f"source/geoboundaries/{code}/geoBoundaries-{code}-{level}-metaData.json"
 data=HERE/f"source/geoboundaries/{code}/geoBoundaries-{code}-{level}.geojson"
 assert digest(data)==EXPECTED_SOURCE[code], f"source hash mismatch: {data}"
 assert digest(src)==EXPECTED_METADATA[code], f"metadata hash mismatch: {src}"
 by_iso[code]=load_features(data)
print("scope_members",len(IDS))
print("baseline_parts",json.dumps({str(x.relative_to(REPO)):digest(x) for x in sorted((REPO/"data/geography").glob("part-*.json"))},sort_keys=True))
print("source_features",json.dumps({k:len(v) for k,v in by_iso.items()},sort_keys=True))
# Exact identity linkage and structural screening only.
rows=[]
source_maps={k:{f["properties"].get("shapeID"):f["properties"] for f in v} for k,v in by_iso.items()}
for ident in sorted(IDS):
 f=baseline[ident]; q=f["properties"]; m=q.get("metadata",{}); iso=m.get("source_id","").split(":")[1]
 member_ids=m.get("source_member_ids") or (["gb:"+iso+":"+m.get("administrative_level","")+":"+m.get("original_id","")] if m.get("original_id") else [])
 source_names=[]; missing=[]
 for member in member_ids:
  bits=member.split(":"); sid=bits[-1]
  sp=source_maps.get(iso,{}).get(sid)
  if sp is None: missing.append(member)
  else: source_names.append(sp.get("shapeName",""))
 status="insufficient-evidence"; flag="source polygon correctness and current completeness not independently established"
 if iso=="ALB": flag="source metadata says District / rrethe, not the current 61-municipality tier; source restoration and correct tier remain unresolved"
 if iso=="BGR": flag="municipality identity and parent need official roster comparison; polygon accuracy/currentness remain unresolved"
 if iso=="BIH" and ident=="gb:BIH:ADM3:43093233B26529153732630":
  status="correction-needed"; flag="official RS 2024 list identifies this named municipality in the City of Istočno Sarajevo, whose constituents are RS local units; Atlas parent is Sarajevo Canton"
 if iso=="BGR" and q.get("name") in ("Ruzhinsi","Georgi Bamyanovo","Strumyarni"):
  status="correction-needed"; flag="source English name did not exact-match retained NSI 2024 English-name roster in the performed comparison; likely spelling/transliteration or identity issue requires authoritative resolution; exact NSI source archive/hash/restoration steps in SOURCES.md"
 if missing: flag += "; original source member not found in pinned source file"
 rows.append({"id":ident,"name":q.get("name",""),"country":iso,"parent_id":q.get("parent_id",""),"source_id":m.get("source_id",""),"source_member_ids":";".join(member_ids),"source_names":";".join(source_names),"missing_source_ids":";".join(missing),"assessment":status,"finding":flag,"boundary_status":"insufficient-evidence"})
for iso,features in by_iso.items():
 sourceids={f["properties"].get("shapeID") for f in features}
 scoped=[r for r in rows if r["country"]==iso]
 print("scoped_source_linkage",iso,len(scoped),"missing",sum(bool(r["missing_source_ids"]) for r in scoped),"unique_source_members",len({member for r in scoped for member in r["source_member_ids"].split(";") if member}))

out=HERE/"location-assessments.csv"
with out.open("w",newline="",encoding="utf-8") as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
# Exact source roster reconciliation for each packet and issue-owned per-province completeness.
province=[]
for x in SCOPE["province_scopes"]:
 members=[baseline[i]["properties"] for i in IDS if baseline[i]["properties"].get("parent_id")==x["id"]]
 province.append({"province_id":x["id"],"province_name":x["name"],"issue_members":len(members),"full_province_count":x["full_province_locations"],"partial":x["partial"],"boundary_assessment":"not independently compared to authoritative reusable polygons"})
with (HERE/"province-review.csv").open("w",newline="",encoding="utf-8") as f:
 w=csv.DictWriter(f,fieldnames=list(province[0]),lineterminator="\n");w.writeheader();w.writerows(province)
for iso,features in by_iso.items():
 count=sum(1 for r in rows if r["country"]==iso)
 print("issue_country_members",iso,count)
 print("source_count",iso,len(features))
parser=argparse.ArgumentParser()
parser.add_argument("--nsi-gpkg",help="optional locally restored NSI LAU 2024.1 GeoPackage; see SOURCES.md")
args=parser.parse_args()
if args.nsi_gpkg:
 gpkg=pathlib.Path(args.nsi_gpkg)
 expected="edf3ae6060f6e5cad1daedfcef5febbd21d9809112b6e26a87cf44ae0f17deab"
 assert digest(gpkg)==expected, "NSI GeoPackage hash does not match the reviewed 2024.1 source"
 con=sqlite3.connect(str(gpkg))
 official=con.execute("select NameLatin,DistrictCode from Obshtini_2024_1").fetchall()
 by_name={norm(row[0]):row[1] for row in official}
 bgr=[r for r in rows if r["country"]=="BGR"]
 unmatched=sorted(r["source_names"].split(";")[0] for r in bgr if norm(r["source_names"].split(";")[0]) not in by_name)
 assert len(official)==265 and len(bgr)==52
 codes={"VID":"vidin","PER":"pernik","KNL":"kyustendil","MON":"montana","SOF":"sofia-city","BLG":"blagoevgrad"}
 counts={}; parent_mismatches=[]
 for r in bgr:
  name=r["source_names"].split(";")[0]; code=by_name.get(norm(name)); parent=r["parent_id"].split(":")[2]
  key=(parent,code); counts[str(key)]=counts.get(str(key),0)+1
  if code and codes.get(code)!=parent: parent_mismatches.append({"id":r["id"],"district_code":code,"atlas_parent":parent})
 assert not parent_mismatches
 print("BGR_NSILAU_exact_name_matches",len(bgr)-len(unmatched))
 print("BGR_NSILAU_unmatched_source_spellings",json.dumps(unmatched,ensure_ascii=False))
 print("BGR_NSILAU_parent_code_groups",json.dumps(counts,sort_keys=True))
 print("BGR_NSILAU_parent_code_mismatches",json.dumps(parent_mismatches))
else:
 print("BGR_NSI_official_roster","not locally restored; use SOURCES.md instructions")
print("assessment_counts",json.dumps({s:sum(r["assessment"]==s for r in rows) for s in ("justified","correction-needed","insufficient-evidence")},sort_keys=True))
print("per_location_assessments",len(rows))
