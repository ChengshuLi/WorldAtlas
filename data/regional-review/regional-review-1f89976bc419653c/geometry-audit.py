#!/usr/bin/env python3
"""Reproduce polygon screens with Shapely 2.0.7; ratios are EPSG:4326 planar only."""
import json, pathlib, sys, re, unicodedata
try:
    import shapely
    from shapely.geometry import shape, Point
    from shapely.ops import unary_union
    from shapely.validation import make_valid
except ImportError as exc:
    raise SystemExit("Install Shapely 2.0.7 in an isolated environment and set PYTHONPATH") from exc
if shapely.__version__ != "2.0.7": raise SystemExit(f"Expected Shapely 2.0.7, got {shapely.__version__}")
PACKET=pathlib.Path(__file__).resolve().parent; ROOT=PACKET.parents[2]
scope=json.loads((PACKET/"issue-scope-pinned.json").read_text()); wanted=set(scope["member_location_ids"])
atlas={}
for path in sorted((ROOT/"data/geography").glob("part-*.json")):
    for f in json.loads(path.read_text())["features"]:
        if f["id"] in wanted: atlas[f["id"]]=f
def file(key): return json.loads((PACKET/"sources"/f"geoBoundaries-{key}.geojson").read_text())["features"]
def index(key): return {f["properties"]["shapeID"]:f for f in file(key)}
src={k:index(k) for k in ["CAF-ADM3","COD-ADM2","COG-ADM2","TCD-ADM2"]}
parents={k:index(k) for k in ["CAF-ADM2","COD-ADM1","COG-ADM1","TCD-ADM1"]}
eco=json.loads((PACKET/"sources/resolve-selected-query.json").read_text())
eco={"resolve:"+str(f["properties"]["ECO_ID"]):f for f in eco["features"]}
def geom(f): return shape(f["geometry"])
def valid(g): return g if g.is_valid else make_valid(g)
def ratio(a,b): return round(a/b,8) if b else None
def norm(text): return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", text).encode("ascii","ignore").decode().lower())
rows=[]
physical_by_predecessor={}
for fid in scope["member_location_ids"]:
    f=atlas[fid];p=f["properties"];m=p["metadata"];derived=fid.startswith("atlas:physical:")
    key="TCD-ADM2" if derived else {"gb:CAF:ADM3":"CAF-ADM3","gb:COD:ADM2":"COD-ADM2","gb:COG:ADM2":"COG-ADM2","gb:TCD:ADM2":"TCD-ADM2"}[m["source_id"]]
    orig=m["source_member_ids"][0].rsplit(":",1)[1] if derived else m["original_id"]
    ag=geom(f);sg=geom(src[key][orig]);ar=valid(ag);sr=valid(sg);common=ar.intersection(sr).area
    parent_key={"CAF-ADM3":"CAF-ADM2","COD-ADM2":"COD-ADM1","COG-ADM2":"COG-ADM1","TCD-ADM2":"TCD-ADM1"}[key]
    point=m.get("representative_point"); candidates=[]
    if point:
        pt=Point(point)
        candidates=[g for g in parents[parent_key].values() if geom(g).covers(pt)]
    parent_name=candidates[0]["properties"]["shapeName"] if len(candidates)==1 else None
    row={"location_id":fid,"source_feature_id":orig,"atlas_valid":ag.is_valid,"source_valid":sg.is_valid,
         "atlas_components":len(ag.geoms) if hasattr(ag,"geoms") else 1,"source_components":len(sg.geoms) if hasattr(sg,"geoms") else 1,
         "atlas_share_overlapping_source_feature_planar":ratio(common,ar.area),"source_feature_share_overlapping_atlas_planar":ratio(common,sr.area),
         "source_parent_point_candidates":len(candidates),"source_parent_by_point":parent_name,
         "atlas_parent_slug":p.get("parent_id","").split(":")[2]}
    if len(candidates)==1:
        pg=valid(geom(candidates[0]));row["atlas_subject_share_in_source_parent_planar"]=ratio(ar.intersection(pg).area,ar.area)
    if derived:
        ef=eco[m["source_id"]];eg=valid(geom(ef));expected=valid(sr.intersection(eg))
        row.update({"ecoregion_id":m["source_id"],"ecoregion_name":ef["properties"]["ECO_NAME"],
                    "atlas_share_in_ecoregion_planar":ratio(ar.intersection(eg).area,ar.area),
                    "atlas_share_in_admin_x_ecoregion_intersection_planar":ratio(ar.intersection(expected).area,ar.area),
                    "expected_intersection_share_covered_by_atlas_planar":ratio(ar.intersection(expected).area,expected.area)})
        physical_by_predecessor.setdefault(orig,[]).append(ar)
    rows.append(row)
cohort={}
for key,features in src.items():
    raw_shapes=[geom(f) for f in features.values()]; shapes=[valid(g) for g in raw_shapes]; ids=list(features)
    pairs=[]; touching=0
    for i,left in enumerate(shapes):
        for j in range(i+1,len(shapes)):
            if left.intersects(shapes[j]):
                if left.touches(shapes[j]): touching+=1
                area=left.intersection(shapes[j]).area
                if area>1e-12:pairs.append({"ids":[ids[i],ids[j]],"intersection_square_degrees":round(area,12)})
    cohort[key]={"feature_count":len(shapes),"valid_original_feature_count":sum(g.is_valid for g in raw_shapes),
                 "component_count_range":[min(len(g.geoms) if hasattr(g,"geoms") else 1 for g in shapes),max(len(g.geoms) if hasattr(g,"geoms") else 1 for g in shapes)],
                 "touching_neighbor_pair_count":touching,"positive_area_overlap_pair_count":len(pairs),"positive_area_overlap_pairs":pairs}
direct_tcd_ids={f["properties"]["metadata"]["original_id"] for fid,f in atlas.items() if fid.startswith("gb:TCD:ADM2:")}
physical_only=[]
for original_id,portions in sorted(physical_by_predecessor.items()):
    if original_id in direct_tcd_ids: continue
    source_geom=valid(geom(src["TCD-ADM2"][original_id])); combined=unary_union(portions)
    physical_only.append({"source_feature_id":original_id,"source_name":src["TCD-ADM2"][original_id]["properties"]["shapeName"],
                          "portion_subject_count":len(portions),"portion_location_ids":[r["location_id"] for r in rows if r.get("source_feature_id")==original_id and r.get("ecoregion_id")],
                          "source_admin_area_share_covered_by_all_atlas_physical_parts_planar":ratio(combined.intersection(source_geom).area,source_geom.area),
                          "source_admin_area_share_unrepresented_by_atlas_physical_parts_planar":ratio(source_geom.difference(combined).area,source_geom.area),
                          "limit":"Planar comparison to retained 2019 OCHA administrative feature; not legal extent or complete physical-land coverage."})
disagreements=[r for r in rows if r.get("source_parent_by_point") and norm(r["source_parent_by_point"])!=norm(r["atlas_parent_slug"])]
out={"tool":"Shapely","version":shapely.__version__,"crs":"EPSG:4326","area_method":"planar square degrees; within-feature screen only; not geodesic/equal-area",
     "scope_ids_sha256":scope["member_location_ids_sha256"],"subject_count":len(rows),"subjects":sorted(rows,key=lambda r:r["location_id"]),
     "full_source_cohort_overlaps":cohort,"source_parent_point_name_disagreements":disagreements,
     "chad_source_units_represented_only_by_physical_portions":physical_only,
     "subject_quality_summary":{"invalid_atlas_geometry_count":sum(not r["atlas_valid"] for r in rows),"invalid_original_source_geometry_count":sum(not r["source_valid"] for r in rows),
        "single_component_atlas_count":sum(r["atlas_components"]==1 for r in rows),"source_parent_under_99_percent_planar_containment_count":sum(r.get("atlas_subject_share_in_source_parent_planar",1)<.99 for r in rows)},
     "limits":["Point and polygon overlays test source correspondence, not legal boundary truth.","Positive-area sibling overlaps flag topology questions, not which feature is correct.","Planar square-degree ratios are not physical area or accuracy claims.","No official national source was substituted by these screens."]}
(PACKET/"geometry-audit.json").write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")
derived=[r for r in rows if "ecoregion_id" in r]
parent_ratios=[r.get("atlas_subject_share_in_source_parent_planar") for r in rows if r.get("atlas_subject_share_in_source_parent_planar") is not None]
print(json.dumps({"ok":True,"shapely":shapely.__version__,"subjects":len(rows),"cohort_positive_overlap_pairs":{k:v["positive_area_overlap_pair_count"] for k,v in cohort.items()},"parent_point_name_disagreements":disagreements,"derived_portions":len(derived),"derived_min_ecoregion_overlap":min(r["atlas_share_in_ecoregion_planar"] for r in derived),"derived_min_expected_intersection_coverage":min(r["expected_intersection_share_covered_by_atlas_planar"] for r in derived),"physical_only_source_units":len(physical_only),"physical_only_source_unit_coverage":{x["source_name"]:x["source_admin_area_share_covered_by_all_atlas_physical_parts_planar"] for x in physical_only},"parent_min_planar_containment":min(parent_ratios),"parent_under_99pct_count":sum(r<.99 for r in parent_ratios)}))
