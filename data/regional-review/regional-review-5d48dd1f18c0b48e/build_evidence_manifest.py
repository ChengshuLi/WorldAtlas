#!/usr/bin/env python3
"""Build evidence-quality v1 for issue #467 from the retained packet."""
import hashlib, json, subprocess
from pathlib import Path
P=Path(__file__).resolve().parent; ROOT=P.parents[2]; REL=P.relative_to(ROOT).as_posix()
BASE="fdab75892d979b995a1d20f311006aeeddb770b5"
def digest(b): return hashlib.sha256(b).hexdigest()
def candidate(p):
 b=(ROOT/p).read_bytes(); return {"path":p,"bytes":len(b),"sha256":digest(b),"hash_kind":"file-bytes"}
def baseline(p):
 b=subprocess.check_output(["git","-C",str(ROOT),"show",f"{BASE}:{p}"])
 return {"path":p,"bytes":len(b),"sha256":digest(b),"hash_kind":"file-bytes"}
scope=json.loads((P/"scope-source-inventory.json").read_text()); facts=json.loads((P/"source-facts-manifest.json").read_text())
ids=sorted(scope["exact_subjects"]); idhash=digest(json.dumps(ids,separators=(",",":"),ensure_ascii=False).encode())
basepaths=["data/world-index.json","data/hierarchy.json","data/geography/part-1.json","data/geography/part-4.json","data/geography/part-9.json","data/geography/part-15.json","data/geography/part-16.json","data/geography/part-17.json","data/geography/part-23.json","data/macro-foundation/regional-handoffs.json.gz","data/macro-foundation/current-membership-inventory.json.gz"]
bf=[baseline(x) for x in basepaths]
pins={"world-index":bf[0]["sha256"],"hierarchy-file":bf[1]["sha256"],"subject-features":bf[2]["sha256"],"regional-handoffs":bf[-2]["sha256"],"current-membership-inventory":bf[-1]["sha256"]}
pinfiles={"world-index":basepaths[0],"hierarchy-file":basepaths[1],"subject-features":basepaths[2],"regional-handoffs":basepaths[-2],"current-membership-inventory":basepaths[-1]}
retained=[]; sources=[]
for s in facts["sources"]:
 files=[]
 for key,hkey in [("geometry","sha256"),("metadata","metadata_sha256")]:
  p=s[key]; b=(P/p).read_bytes(); f={"path":(P/p).relative_to(ROOT).as_posix(),"bytes":len(b),"sha256":digest(b),"hash_kind":"file-bytes"}; retained.append(f); files.append(f)
 assert [f["sha256"] for f in files]==[s["sha256"],s["metadata_sha256"]]
 sources.append({"id":s["source_id"],"url":s["url"],"role":s["role"],"vintage":s["vintage"],"retrieved_at":"2026-10-04","license":{"status":"redistributable","terms":s["license"]+"; retain source attribution and metadata."},"retention":"retained","verification":"verified","temporal_status":"reference","files":files})
for ident,title,url,role,verified in [
 ("benin-tbs-2011","INStaD Tableau de Bord Social 2011 pp. 28, 30","https://www.instad.bj/images/docs/insae-publications/annuelles/TBS/Archive/TBS%202011.pdf","Official 12-department/77-commune hierarchy; restore and inspect cited pages.",True),
 ("burkina-stanford-bv378fk8507","UT Austin/Stanford catalog Communes Burkina Faso 2007","https://geodata-cdn.lib.utexas.edu/catalog/stanford-bv378fk8507","Exact record establishes commune role, 2007 vintage, level 3 and public-domain status.",True),
 ("burkina-insd-2007","INSD Annuaire statistique 2007 Tables 01.01/01.03","https://web2.insd.bf/sites/default/files/2021-12/Annuaire_statistique_National_2007.pdf","Indexed official excerpts only; complete PDF unavailable, so full named crosswalk remains unverified.",False),
 ("benin-annuaire-2019","INStaD Annuaire statistique 2019 Tables 01.01–01.12","https://www.instad.bj/images/docs/insae-publications/annuelles/AS-INSAE/Archive/Annee_2019/Annuaire_INSAE_2019.pdf","Indexed excerpts only; temporary official PDF error, not a completed commune crosswalk.",False),
 ("burkina-territorial-reorganization-2025","Burkina Faso Ministry 2025 reorganization","https://www.matd.gov.bf/accueil/actualites/details?cHash=268871d043c3b736e5d3721ee1c06cb7&tx_news_pi1%5Baction%5D=detail&tx_news_pi1%5Bcontroller%5D=News&tx_news_pi1%5Bnews%5D=1079","Temporal caution; do not project current administrative counts onto 2007 source.",True)]:
 sources.append({"id":ident,"url":url,"role":title+". "+role,"vintage":"as cited in source-research.md","retrieved_at":"2026-10-04","license":{"status":"unknown","terms":"No reuse license verified; full bytes not retained."},"retention":"restoration-only","verification":"verified" if verified else "unverified","temporal_status":"reference","restoration":f"Restore from {url}; see source-facts-manifest.json for cited pages and limitations.","limit":role})
outputs=[]
for p in sorted(P.rglob("*")):
 if p.is_file() and p.name!="evidence-quality.json":
  q=p.relative_to(ROOT).as_posix()
  if not any(q==f["path"] for f in retained): outputs.append(candidate(q))
outmap={f["path"]:f for f in outputs}
geoscreen=outmap[f"{REL}/geographic-screen.json"]
manifest={"version":1,"issue":467,"lane":"geography","worker_id":"codex-01a10948-7d38-75d0-bc01-4cc28ea41f49-467-bf","subject_ids":ids,"subject_ids_sha256":idhash,
 "baseline":{"commit":BASE,"files":bf,"pins":pins,"pin_files":pinfiles,"subject_files":{i:basepaths[2] for i in ids}},"sources":sources,"outputs":outputs,
 "methods":[
  {"id":"source-role-crosswalk","kind":"source","description":"Resolve exact scoped IDs to pinned geoBoundaries source IDs/names and establish country-specific territorial roles from official statistical sources and the exact Stanford catalog item; retain temporal and completeness limits.","software":"Python 3.12 standard library","units":"source features, locations and administrative parent groups"},
  {"id":"geographic-overlay","kind":"geography","description":"Diagnostic source/current and child/parent polygon overlays with positive identity and negative disjoint controls; no geometry is changed and overlaps do not establish legal boundaries.","software":"Python 3.12.14; Shapely 2.1.2; pyproj 3.7.2; scripts/evidence/geometry.py worldatlas-evidence-geometry-v1","units":"WGS84 ellipsoidal m2 and area fractions","axis_order":"longitude-latitude","crs":"EPSG:4326","area_method":"WGS84 straight-source-edge ellipsoidal integral; Shapely planar lon/lat intersection numerator","distance_method":"WGS84 inverse geodesic"},
  {"id":"neighbor-tier-screen","kind":"measurement","description":"Compare neighboring current Atlas local-unit area distributions and source role/vintage metadata as context only.","software":"Python 3.12.14; Shapely 2.1.2; pyproj 3.7.2; shared helper","units":"source cohorts and WGS84 m2"},
  {"id":"packet-generators","kind":"generator","description":"Deterministically materialize exact roster, one assessment per location and parent, and control receipts.","software":"Python 3.12 standard library and pinned geometry dependencies","units":"IDs, parent groups, SHA-256"}],
 "metrics":[{"id":"scoped-locations","value":224,"unit":"locations","vintage":"baseline","input_sha256":pins["subject-features"],"evaluation_commit":BASE},{"id":"scoped-parents","value":30,"unit":"parent groups","vintage":"baseline","input_sha256":pins["subject-features"],"evaluation_commit":BASE},{"id":"insufficient-evidence","value":35,"unit":"locations","vintage":"baseline","input_sha256":geoscreen["sha256"],"evaluation_commit":BASE}],"summaries":[],
 "conclusions":[
  {"status":"supported","text":"The 2007 source layers represent local communes in both countries; Burkina Faso's ADM3 code is not used alone to infer that role. All 224 exact issue IDs and names match the retained source features.","source_ids":["gb:BEN:ADM2","gb:BFA:ADM3","benin-tbs-2011","burkina-stanford-bv378fk8507","burkina-insd-2007"]},
  {"status":"unresolved","text":"Thirty-three Benin child-to-department relationships lack a same-vintage official crosswalk; two Burkina current footprints have incompletely reproduced topology provenance. These 35 rows remain insufficient-evidence, and no error or correction is asserted.","source_ids":["gb:BEN:ADM2","gb:BEN:ADM1","gb:BFA:ADM3","gb:BFA:ADM2","benin-tbs-2011","burkina-insd-2007"]},
  {"status":"supported","text":"All 224 locations and 30 scoped parent groups have explicit assessments. The packet does not certify full national or regional coverage, approve the regional envelope, or permit imports.","source_ids":["gb:BEN:ADM2","gb:BFA:ADM3","benin-tbs-2011","burkina-stanford-bv378fk8507","burkina-insd-2007"]}],
 "stages":{"research":"complete","implementation":"proposed","geographic_approval":"unapproved"},"commands":[
  "PYTHONPATH=scripts/evidence:scripts python3 data/regional-review/regional-review-5d48dd1f18c0b48e/reproduce_scope.py",
  "PYTHONPATH=scripts/evidence:scripts python3 data/regional-review/regional-review-5d48dd1f18c0b48e/audit_geography.py",
  "PYTHONPATH=scripts/evidence:scripts python3 data/regional-review/regional-review-5d48dd1f18c0b48e/audit_neighbor_granularity.py",
  "PYTHONPATH=scripts/evidence:scripts python3 data/regional-review/regional-review-5d48dd1f18c0b48e/build_assessments.py",
  "PYTHONPATH=scripts/evidence:scripts python3 data/regional-review/regional-review-5d48dd1f18c0b48e/packet_controls.py",
  "node scripts/evidence-quality.mjs data/regional-review/regional-review-5d48dd1f18c0b48e/evidence-quality.json"],
 "change_receipts":[{"path":f["path"],"status":"added","previous_path":None} for f in outputs],"metric_bindings":[],"validation":[
  {"method_id":"source-role-crosswalk","kind":"source","outcome":"passed","evidence_path":f"{REL}/source-crosswalk-controls.json"},
  {"method_id":"geographic-overlay","kind":"geography","outcome":"passed","evidence_path":f"{REL}/geometry-controls.json"},
  {"method_id":"packet-generators","kind":"generator","outcome":"passed","evidence_path":f"{REL}/packet-generator-controls.json"}]}
(P/"evidence-quality.json").write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"outputs":len(outputs),"retained_source_files":len(retained),"baseline_files":len(bf),"subjects":len(ids)}))
