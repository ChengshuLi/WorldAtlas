import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
B=ROOT/"coordination/engineering"
IRN=B/"iran-pakistan-joint-proposal-971-20261005-local10/originals/osm-saravan-relation-6555069-full.json"
PAK=B/"iran-pakistan-native-seam-971-20261005-local09/originals/osm-panjgur-relation-3229274-full.json"
PARENT=B/"iran-pakistan-joint-proposal-971-20261005-local10/originals"
WAYS=[239441239,239453665]
def load(p): return json.loads(Path(p).read_text())
def elements(data): return {(e["type"],e["id"]):e for e in data["elements"]}
def verify(shared_way_ids=WAYS, parent_mutation=None):
 a,b=elements(load(IRN)),elements(load(PAK))
 for rid in (6555069,3229274):
  relation=(a if rid==6555069 else b)[("relation",rid)]
  for wid in shared_way_ids:
   if not any(m.get("type")=="way" and m.get("ref")==wid and m.get("role")=="outer" for m in relation["members"]):
    raise ValueError(f"county relation {rid} missing shared outer way {wid}")
 for wid in shared_way_ids:
  wa=a[("way",wid)]; wb=b[("way",wid)]
  if wa!=wb or wa.get("nodes")!=wb.get("nodes"): raise ValueError(f"way {wid} differs between complete county responses")
  for nid in wa["nodes"]:
   na,nb=a[("node",nid)],b[("node",nid)]
   if (na.get("lon"),na.get("lat"))!=(nb.get("lon"),nb.get("lat")): raise ValueError(f"node {nid} differs")
  path=PARENT/f"osm-way-{wid}-relations.json"
  pd=elements(load(path))
  for rid in (304938,307573):
   rel=pd[("relation",rid)]
   members=list(rel["members"])
   if parent_mutation==(wid,rid): members=[m for m in members if not (m.get("type")=="way" and m.get("ref")==wid)]
   if not any(m.get("type")=="way" and m.get("ref")==wid and m.get("role")=="outer" for m in members):
    raise ValueError(f"national parent relation {rid} missing shared outer way {wid}")
 return [{"way_id":wid,"nodes":len(a[("way",wid)]["nodes"]),"same_way_object":True,"same_node_sequence_and_coordinates":True,"outer_in_both_counties":True,"outer_in_both_national_relations":True} for wid in shared_way_ids]
positive=verify()
missing_way_rejected=False
try: verify([239441239,239453665,999])
except ValueError: missing_way_rejected=True
wrong_parent_rejected=False
try: verify(parent_mutation=(239441239,304938))
except ValueError: wrong_parent_rejected=True
if not missing_way_rejected or not wrong_parent_rejected: raise SystemExit("negative source controls did not reject altered inputs")
out={"method_id":"osm-shared-edge-source-membership","kind":"source","outcome":"passed","positive":positive,"negative":[{"rejected":missing_way_rejected,"case":"one expected shared way removed from the comparison scope"},{"rejected":wrong_parent_rejected,"case":"national parent relation 304938 omits the exact outer way"}],"limit":"Identical OSM IDs, member order, node coordinates and administrative relation membership establish shared topology in these retrieved OSM records only; they do not establish legal sovereignty, official source authority, boundary observation date, or water."}
target=ROOT/"research/geography/shared-seam-irn-pak-source-assessment-20261006/shared-edge-controls.json"
target.write_text(json.dumps(out,sort_keys=True,separators=(",",":"))+"\n")
print(json.dumps(out,indent=2))
