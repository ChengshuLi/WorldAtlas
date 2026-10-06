#!/usr/bin/env python3
"""Reproduce Henderson's Natural Earth component lineage against the pinned baseline."""
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "data/regional-review/henderson-island-boundary-20261005"
CURRENT = "data/geography/part-28.json"
SOURCE = "data/regional-review/regional-review-14a242c4cb0781a7/source/natural-earth/ne_10m_admin_1_scoped-admin-features.json"
EXPECTED_SOURCE_SHA = "dd3f4a5683c713fd89c00b41748d89771f905ef236feaacb7887818085f3d96e"
EXPECTED_CURRENT_SHA = "2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d"
HIERARCHY = "data/hierarchy.json"
EXPECTED_HIERARCHY_SHA = "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b"
EXPECTED_PARENT = "framework:province:pitcairn-islands:d483df587794"
EXPECTED_BBOX = [-128.350250, -24.413670, -128.290151, -24.324314]

def sha(data): return hashlib.sha256(data).hexdigest()
def close(ring): return ring[0] == ring[-1]
def canonical(ring):
    pts = [tuple(round(float(v), 4) for v in p) for p in ring[:-1]]
    rotations = []
    for seq in (pts, list(reversed(pts))):
        rotations.extend(tuple(seq[i:] + seq[:i]) for i in range(len(seq)))
    return min(rotations)
def bbox(poly):
    pts = [p for ring in poly for p in ring]
    return [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]
def descriptor(rel):
    raw=(ROOT/rel).read_bytes(); return {"path":rel,"sha256":sha(raw),"bytes":len(raw)}
def load(rel): return json.loads((ROOT/rel).read_text())

src_desc=descriptor(SOURCE); cur_desc=descriptor(CURRENT); hierarchy_desc=descriptor(HIERARCHY)
assert hierarchy_desc["sha256"] == EXPECTED_HIERARCHY_SHA, "baseline hierarchy file changed"
assert src_desc["sha256"] == EXPECTED_SOURCE_SHA, "retained Natural Earth extract changed"
assert cur_desc["sha256"] == EXPECTED_CURRENT_SHA, "baseline Henderson-containing file changed"
features=load(SOURCE)["features"]
parents=[f for f in features if f.get("properties",{}).get("adm0_a3")=="PCN" and f.get("properties",{}).get("name")=="Pitcairn Islands"]
assert len(parents)==1, f"expected one Pitcairn Admin-1 feature, got {len(parents)}"
parent=parents[0]
assert parent["geometry"]["type"]=="MultiPolygon" and len(parent["geometry"]["coordinates"])==4
components=parent["geometry"]["coordinates"]
boxes=[bbox(poly) for poly in components]
assert boxes[2] == EXPECTED_BBOX, f"Henderson coordinate window changed: {boxes[2]}"
assert all(sum(1 for b in boxes if all(abs(x-y)<1e-12 for x,y in zip(b,EXPECTED_BBOX)))==1 for _ in [0]), "Henderson component window not unique"
current=[f for f in load(CURRENT)["features"] if f.get("id")=="PCN+00?"]
assert len(current)==1
cf=current[0]
assert cf["properties"].get("parent_id")==EXPECTED_PARENT and cf["geometry"]["type"]=="Polygon"
cring=cf["geometry"]["coordinates"][0]
assert close(cring) and len(cring)==9
henders=[i for i,p in enumerate(components) if all(abs(x-y)<1e-12 for x,y in zip(bbox(p),EXPECTED_BBOX))]
assert len(henders)==1
idx=henders[0]; sring=components[idx][0]
hierarchy=load(HIERARCHY)
parents_h=[x for x in hierarchy if x.get("id")==EXPECTED_PARENT]
assert len(parents_h)==1 and parents_h[0].get("name")=="Pitcairn Islands" and parents_h[0].get("metadata",{}).get("child_count")==4, "parent identity or four-child context changed"
assert close(sring) and len(sring)==9
same=canonical(cring)==canonical(sring)
assert same, "rounded source component does not match current ring"
neg=[]
for i,poly in enumerate(components):
    if i==idx: continue
    ring=poly[0]
    equal=canonical(cring)==canonical(ring)
    assert not equal, f"negative control component {i} unexpectedly matches Henderson"
    neg.append({"component":i,"bbox":boxes[i],"ring_positions":len(ring),"matches_current_after_rounding":equal})
lineage={"subject_id":"PCN+00?","parent_id":EXPECTED_PARENT,"source_feature_name":parent["properties"]["name"],"source_feature_adm1_code":parent["properties"].get("adm1_code"),"source_vintage_commit":"ca96624a56bd078437bca8184e78163e5039ad19","source_extract_sha256":src_desc["sha256"],"current_containing_file_sha256":cur_desc["sha256"],"hierarchy_file_sha256":hierarchy_desc["sha256"],"parent_name":parents_h[0]["name"],"parent_child_count":parents_h[0]["metadata"]["child_count"],"component_count":len(components),"henderson_component":idx,"henderson_source_bbox":boxes[idx],"source_ring_positions":len(sring),"current_ring_positions":len(cring),"current_unique_vertices":len(cring)-1,"source_unique_vertices":len(sring)-1,"matched_unique_vertices":sum(1 for _ in cring[:-1]),"rounded_coordinate_match":same,"rounding_decimals":4,"coordinate_order_and_winding_ignored":True,"other_components":neg,"interpretation":"Source lineage match only; no evidence of contemporary shoreline accuracy, legal boundary, or complete land/islet coverage."}
(PACKET/"findings/component-lineage.json").write_text(json.dumps(lineage,indent=2)+"\n")
positive={"method_id":"rounded-component-lineage","kind":"positive-control","outcome":"passed","evidence_path":"data/regional-review/henderson-island-boundary-20261005/findings/component-lineage.json","assertion":"unique Henderson source component canonical ring equals current feature ring after rounding to four decimal places","observed_vertices":len(cring)-1,"source_vertices":len(sring)-1,"matched":True}
(PACKET/"findings/positive-control.json").write_text(json.dumps(positive,indent=2)+"\n")
negative={"method_id":"rounded-component-lineage","kind":"negative-control","outcome":"passed","evidence_path":"data/regional-review/henderson-island-boundary-20261005/findings/negative-controls.json","assertion":"each of the three other named-group components differs from the Henderson feature after rounding","controls":neg}
(PACKET/"findings/negative-controls.json").write_text(json.dumps(negative,indent=2)+"\n")
print(json.dumps({"component_lineage":lineage,"positive_control":positive,"negative_control":negative},indent=2))
