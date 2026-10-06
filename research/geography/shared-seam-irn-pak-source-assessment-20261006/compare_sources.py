import importlib.util, json, sys
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import shape, Polygon
from shapely.ops import transform
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("native",ROOT/"coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/reproduce.py")
native=importlib.util.module_from_spec(spec); spec.loader.exec_module(native)
src=ROOT/"coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/originals"
prop=ROOT/"coordination/engineering/iran-pakistan-joint-proposal-971-20261005-local10/originals"
T=Transformer.from_crs("EPSG:4326","EPSG:6933",always_xy=True).transform
S={
 "IRN":("26516999B17111396986996","gb:IRN:ADM2:26516999B17111396986996","IRN-ADM2-native.geojson",prop/"osm-saravan-relation-6555069-full.json",6555069,"framework:province:sistan-and-baluchestan:ed7f0643a0ed",[(537693,"Sistan and Baluchestan Province","Q939575",6555069)]),
 "PAK":("60131773B78019453337506","gb:PAK:ADM2:60131773B78019453337506","PAK-ADM2-native.geojson",src/"osm-panjgur-relation-3229274-full.json",3229274,"framework:province:balochistan:c6b6e17e4739",[(16347101,"Makran Division","Q3308229",3229274),(357968,"Balochistan","Q163239",16347101)])
}
def read(p): return json.loads(Path(p).read_text())
def one(xs,pred,label):
 ys=[x for x in xs if pred(x)]
 if len(ys)!=1: raise ValueError(f"{label}: expected one, got {len(ys)}")
 return ys[0]
def area_report(a,b):
 a=transform(T,a); b=transform(T,b)
 if not a.is_valid or not b.is_valid: raise ValueError("invalid projected geometry")
 inter=a.intersection(b).area; union=a.union(b).area
 return {"measurement_crs":"EPSG:6933","unit":"m2","geoboundaries_area":a.area,"osm_area":b.area,"intersection":inter,"union":union,"gb_covered_by_osm":inter/a.area,"osm_covered_by_gb":inter/b.area,"iou":inter/union,"symmetric_difference_fraction":(union-inter)/union,"limit":"Equal-area whole-feature comparison; not positional accuracy, authority, legal boundary, or water proof."}
def main():
 atlas={}
 for part in (11,17):
  for f in read(ROOT/f"data/geography/part-{part}.json")["features"]: atlas[f.get("id",f.get("properties",{}).get("id"))]=f
 hierarchy=read(ROOT/"data/hierarchy.json"); out={"version":1,"issue":1115,"method":"Complete geoBoundaries feature and OSM relation boundaries, exact OSM node identity, equal-area EPSG:6933 whole-shape comparison.","subjects":{}}
 parent_src=prop/"osm-way-239441239-relations.json"
 for country,(sid,aid,gfile,ofile,rid,expected_parent,parents) in S.items():
  gd=read(src/gfile); gf=one(gd["features"],lambda f:f["properties"].get("shapeID")==sid,sid)
  names=[f.get("properties",{}).get("shapeName","") for f in gd["features"]]
  namesakes=[n for n in names if n.casefold()==gf["properties"]["shapeName"].casefold()]
  if len(namesakes)!=1: raise ValueError("nonunique exact namesake")
  af=atlas[aid]
  if af["properties"]["parent_id"]!=expected_parent: raise ValueError("atlas parent mismatch")
  od=read(ofile); rel=one(od["elements"],lambda e:e.get("type")=="relation" and e.get("id")==rid,str(rid))
  og,assembly=native.assemble_osm_boundary(od,rid); tags=rel["tags"]
  chain=[]
  for pid,pname,qid,child in parents:
   p=one(read(parent_src)["elements"],lambda e:e.get("type")=="relation" and e.get("id")==pid,str(pid))
   contained=any(m.get("type")=="relation" and m.get("ref")==child for m in p.get("members",[]))
   if not contained or p.get("tags",{}).get("wikidata")!=qid: raise ValueError("parent chain mismatch")
   chain.append({"osm_parent_relation":pid,"name":p.get("tags",{}).get("name:en",p.get("tags",{}).get("name")),"wikidata":qid,"admin_level":p.get("tags",{}).get("admin_level"),"timestamp":p.get("timestamp"),"contains_relation":child})
  ts=[e["timestamp"] for e in od["elements"] if e.get("type") in ("node","way") and e.get("timestamp")]
  out["subjects"][country]={"geoBoundaries":{"shapeID":sid,"shapeName":gf["properties"].get("shapeName"),"shapeGroup":gf["properties"].get("shapeGroup"),"shapeType":gf["properties"].get("shapeType"),"shapeISO":gf["properties"].get("shapeISO"),"other_properties":[k for k in gf["properties"] if k not in {"shapeID","shapeName","shapeGroup","shapeType","shapeISO"}],"complete_country_features":len(gd["features"]),"exact_namesakes":len(namesakes)},"osm":{"relation_id":rid,"name":tags.get("name"),"name_en":tags.get("name:en"),"aliases":{k:v for k,v in tags.items() if k.startswith("name:") or k in {"name","alt_name","official_name","short_name"}},"admin_level":tags.get("admin_level"),"place":tags.get("place"),"wikidata":tags.get("wikidata"),"wikipedia":tags.get("wikipedia"),"relation_edit":rel["timestamp"],"member_edit_min":min(ts),"member_edit_max":max(ts),"dated_node_way_count":len(ts),"outer_way_count":assembly["boundary_way_count"]},"atlas":{"id":aid,"parent_id":expected_parent,"parent_name":next((x.get("name") for x in hierarchy if x.get("id")==expected_parent),None)},"osm_parent_chain":chain,"whole_geometry":area_report(shape(gf["geometry"]),og),"crosswalk":"Authored research cross-provider mapping candidate supported by country/source IDs, names and aliases, country-specific admin role, OSM Wikidata identity, exact OSM parent membership/names, unique exact geoBoundaries namesake in complete country source, and full-feature geometry concordance. No source supplies a common geoBoundaries-to-OSM ID; this is not an upstream-issued crosswalk or official adjudication."}
 # Meaningful reject controls: unknown GB id and mismatched OSM parent must fail.
 wrong_id=False
 try: one(read(src/S["IRN"][2])["features"],lambda f:f["properties"].get("shapeID")=="26516999B00000000000000","wrong id")
 except ValueError: wrong_id=True
 p=one(read(parent_src)["elements"],lambda e:e.get("type")=="relation" and e.get("id")==537693,"Iran province")
 wrong_parent=not any(m.get("type")=="relation" and m.get("ref")==3229274 for m in p.get("members",[]))
 # Measurement controls: real target overlays produce bounded positive IoU; invalid input is rejected.
 positive_measurements=all(0 < v["whole_geometry"]["iou"] <= 1 for v in out["subjects"].values())
 invalid_geometry_rejected=False
 try: area_report(Polygon([(0,0),(1,1),(1,0),(0,1),(0,0)]), shape(read(src/S["IRN"][2])["features"][0]["geometry"]))
 except ValueError: invalid_geometry_rejected=True
 if len(out["subjects"])!=2 or not wrong_id or not wrong_parent or any(v["whole_geometry"]["intersection"]<=0 for v in out["subjects"].values()) or not positive_measurements or not invalid_geometry_rejected: raise SystemExit("crosswalk source/measurement control failed")
 out["measurement_controls"]={"positive":{"method_id":"whole-subject-overlay","kind":"positive-control","outcome":"passed","target_iou_in_unit_interval":positive_measurements,"subjects":{k:{"iou":v["whole_geometry"]["iou"],"intersection_m2":v["whole_geometry"]["intersection"],"union_m2":v["whole_geometry"]["union"]} for k,v in out["subjects"].items()},"limit":"Positive planar overlay check validates calculation range, not positional accuracy or authority."},"negative":{"method_id":"whole-subject-overlay","kind":"negative-control","outcome":"passed","self_intersecting_polygon_rejected":invalid_geometry_rejected,"case":"Self-intersecting projected source polygon must be rejected before overlay."}}
 out["controls"]={"method_id":"source-crosswalk-whole-feature","kind":"source","outcome":"passed","positive":"Both exact feature/relation IDs, source-native parent chains, unique source namesakes, and whole geometry overlaps resolved.","negative":[{"rejected":wrong_id,"case":"nonexistent geoBoundaries feature ID"},{"rejected":wrong_parent,"case":"assign Panjgur to Iran province relation"}],"limit":"Controls validate the lookup and parent membership path; they do not certify official/legal/historical identity."}
 return out
if __name__=="__main__":
 out=main(); target=ROOT/"research/geography/shared-seam-irn-pak-source-assessment-20261006/whole-geometry-comparison.json"
 target.write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")
 for key in ("positive","negative"):
  (target.parent/f"whole-geometry-{key}-control.json").write_text(json.dumps(out["measurement_controls"][key],sort_keys=True,separators=(",",":"))+"\n")
 print(json.dumps({"output":str(target),"controls":out["controls"],"measurement_controls":out["measurement_controls"],"subjects":{k:v["whole_geometry"] for k,v in out["subjects"].items()}},ensure_ascii=False,indent=2))
