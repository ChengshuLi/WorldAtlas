#!/usr/bin/env python3
"""Compare the two genuine COD singleton resource controls, preserving custody differences."""
from pathlib import Path
import json,hashlib,gzip
R=Path.cwd();base=R/".cache/native-grid-candidates"
old=R/"coordination/engineering/nor-grc-congo-delivery-20261011/retained/cod-002"
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def read(p):return json.loads(p.read_bytes())
def encoded(p):return p.read_bytes()
def publication(directory):
 p=read(directory/"publication.json")
 # Product descriptors are authenticated before comparing their scientific content.
 assert p["version"]==1 and p["complete"] is True
 assert set(p) in [{"version","complete","facts","inventory"},{"version","complete","facts","inventory","assets"}]
 values=[{"path":"facts.json",**p["facts"]},{"path":"inventory.jsonl.gz",**p["inventory"]}]+p.get("assets",[])
 assert len({d["path"] for d in values})==len(values)
 for d in values:
  raw=(directory/d["path"]).read_bytes()
  assert len(raw)==d["bytes"] and sha(raw)==d["sha256"],d["path"]
  if "uncompressed_bytes" in d:
   decoded=gzip.decompress(raw);assert len(decoded)==d["uncompressed_bytes"] and sha(decoded)==d["uncompressed_sha256"]
 return p
def ledger(d):
 x=read(d/"ledger-batch.json")
 assert set(x)=={"assigned_cells","base_reference","kind","parent_inventory","rows","rule_sha256","scope_ids","version"}
 del x["rule_sha256"]
 for row in x["rows"]:
  del row["source_receipt_sha256"]
 return x
def features(d):
 x=read(d/"features.json")
 for f in x:
  a=f["additiveFootprint"]
  assert set(a)=={"additions","base_geometry_sha256","baseline_release_sha256","kind","ledger_sha256","rule_sha256","version"}
  del a["ledger_sha256"];del a["rule_sha256"]
  for row in a["additions"]:del row["source_receipt_sha256"]
 return x
sources=[base/f"cod-002-v2-{label}-source" for label in ["a","b"]]
natives=[base/f"cod-002-v2-{label}-native" for label in ["a","b"]]
for directory in sources+natives:publication(directory)
records=[]
for source,native in zip(sources,natives):
 source_sha=sha(encoded(source/"facts.json"));l=read(native/"ledger-batch.json");p=read(native/"patch-batch.json")
 assert l["assigned_cells"]==41 and len(l["rows"])==1 and all(row["source_receipt_sha256"]==source_sha for row in l["rows"])
 assert p["ledger_sha256"]==sha(encoded(native/"ledger-batch.json")) and p["rule_sha256"]==l["rule_sha256"]
 assert sum(end-start for row in p["rows"] for start,end,owner in row["runs"])==41
 for f in read(native/"features.json"):
  a=f["additiveFootprint"];assert a["ledger_sha256"]==p["ledger_sha256"] and a["rule_sha256"]==p["rule_sha256"]
  assert all(row["source_receipt_sha256"]==source_sha for row in a["additions"])
 records.append({"source_facts_sha256":source_sha,"native_ledger_sha256":p["ledger_sha256"],"rule_sha256":p["rule_sha256"]})
for phase,dirs in [("source",sources),("native",natives)]:
 bodies=[encoded(d/"inventory.jsonl.gz") for d in dirs]+[encoded(old/phase/"inventory.jsonl.gz")]
 assert bodies[0]==bodies[1]==bodies[2],phase+" exact inventory changed"
whole=["owners-batch.json.gz","base-native-manifest.json","owner-window.json","virtual-owner-window.json"]
for name in whole:
 bodies=[encoded(d/name) for d in natives]+[encoded(old/"native"/name)]
 assert bodies[0]==bodies[1]==bodies[2],name
ledgers=[ledger(d) for d in natives]+[ledger(old/"native")];assert ledgers[0]==ledgers[1]==ledgers[2]
feats=[features(d) for d in natives]+[features(old/"native")];assert feats[0]==feats[1]==feats[2]
patches=[read(d/"patch-batch.json") for d in natives]+[read(old/"native"/"patch-batch.json")]
for key in ["base_reference","kind","rows","version"]:
 assert patches[0][key]==patches[1][key]==patches[2][key],key
report={"kind":"cod002-two-issued-resource-control-scientific-comparison","whole_equal_to_each_other_and_original":["source/inventory.jsonl.gz","native/inventory.jsonl.gz"]+["native/"+x for x in whole],"ledger_excluded_derived_fields":["rule_sha256","rows[].source_receipt_sha256"],"feature_excluded_derived_fields":["[].additiveFootprint.ledger_sha256","[].additiveFootprint.rule_sha256","[].additiveFootprint.additions[].source_receipt_sha256"],"patch_compared_fields":["base_reference","kind","rows","version"],"all_other_ledger_and_feature_fields_equal":True,"scope_ids":ledgers[0]["scope_ids"],"assigned_cells":41,"native_row_count":len(patches[0]["rows"]),"whole_custody_hashes":records}
out=R/".cache/resource-control-wave-002/scientific-comparison.json"
with out.open("x") as f:json.dump(report,f,indent=2);f.write("\n")
print(json.dumps(report))
