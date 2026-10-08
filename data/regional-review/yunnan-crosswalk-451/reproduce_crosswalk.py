#!/usr/bin/env python3
"""Reproduce source-only identity and adjacency observations for issue #914.
Requires Python 3.11+ and Shapely 2.x. Does not compare to legal boundaries.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data/regional-review/regional-review-9b38f58111efd323/sources/geoboundaries-chn-adm2-2017.geojson"
TARGETS = {
"17275852B22092438679853":"Qujingshi",
"17275852B6036299829891":"Zhaotongshi",
"17275852B42043031438117":"Ludingshi",
"17275852B47269106522129":"Jianshanxian",
"17275852B72941365568170":"Milexian",
"17275852B76506385801060":"Wenshanxian",
"17275852B98994351670446":"Mengzixian",
}
raw=SOURCE.read_bytes(); doc=json.loads(raw)
all_features=[]
for f in doc["features"]:
    p=f.get("properties",{})
    fid=str(p.get("shapeID", ""))
    all_features.append((fid,p,shape(f["geometry"])))
selected=[x for x in all_features if x[0] in TARGETS]
if {x[0] for x in selected} != set(TARGETS):
    raise SystemExit("target source roster mismatch")
rows=[]
for fid,p,g in sorted(selected):
    neighbors=[]
    for oid,op,og in all_features:
        if oid != fid and g.boundary.intersects(og.boundary):
            length=g.boundary.intersection(og.boundary).length
            if length > 0:
                neighbors.append({"source_shape_id":oid,"source_name":op.get("shapeName"),"shared_boundary_degrees":round(length,8)})
    rows.append({
      "subject_id":"gb:CHN:ADM2:"+fid,
      "source_name":TARGETS[fid],
      "properties":p,
      "geometry_type":g.geom_type,
      "valid":g.is_valid,
      "component_count":len(g.geoms) if hasattr(g,"geoms") else 1,
      "bounds_wgs84":list(g.bounds),
      "source_neighbor_count":len(neighbors),
      "source_neighbors":sorted(neighbors,key=lambda n:n["source_name"] or ""),
      "boundary_metric_limit":"Intersection length is in raw coordinate degrees; source-internal adjacency only, not independent/legal boundary evidence."
    })
result={"source":str(SOURCE.relative_to(ROOT)),"source_bytes":len(raw),"source_sha256":hashlib.sha256(raw).hexdigest(),"source_feature_count":len(doc["features"]),"target_count":len(rows),"method":"Shapely boundary intersection against all features in the retained source file; names and IDs are read from source properties.","limits":["This measures source-internal adjacency only.","No authoritative legal map or independent county polygon is compared.","Validity and component count do not establish territorial identity, completeness, vintage correctness, or legal boundary position."],"subjects":rows}
print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
