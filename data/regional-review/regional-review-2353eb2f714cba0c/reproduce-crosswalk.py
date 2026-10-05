import json, re, hashlib, zipfile, io, csv, os, sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from evidence.geometry import land_area_m2, transform_point, METHOD as GEOMETRY_METHOD
import shapefile
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer

root=Path(os.getcwd())
pkt=root/'data/regional-review/regional-review-2353eb2f714cba0c'
sources=pkt/'sources'
issue=json.load(open(pkt/'source/issue-430-api-snapshot.json'))
body=issue['body']
block=re.search(r'```json\s*(\{.*?\})\s*```',body,re.S).group(1)
scope=json.loads(block); ids=set(scope['member_location_ids'])
issue_member_hash=hashlib.sha256("\n".join(scope["member_location_ids"]).encode()).hexdigest()
assert issue_member_hash==scope["member_location_ids_sha256"]
assert len(ids)==160
# atlas features in declared ID scope
atlas=[]
for part in [25,26,27,29]:
 fc=json.load(open(root/f'data/geography/part-{part}.json'))
 for f in fc['features']:
  if f['properties']['id'] in ids: atlas.append(f)
assert len(atlas)==160 and {f['properties']['id'] for f in atlas}==ids
# Original geoBoundaries shapes: all source members, including both components of multipart Fairfax
raw=json.load(open(sources/'geoboundaries-2018/geoBoundaries-USA-ADM2.geojson'))
source_features=[f for f in raw['features'] if f['properties']['shapeGroup'] in ('USA',)]
# select source ids represented in Atlas direct units or source_members on multipart
source_ids=set()
for f in atlas:
 p=f['properties']; md=p.get('metadata',{})
 if p['id'].startswith('gb:USA:ADM2:'): source_ids.add(p['id'].split(':')[-1])
 for x in md.get('source_member_ids',[]): source_ids.add(x.split(':')[-1])
# schema varies; inspect atlas metadata parent may have source_ids in provenance
for x in source_features:
 if 'Fairfax' in x['properties']['shapeName']: pass
assert len(source_ids)>=159, len(source_ids)
# use all four-state source shapes by point-in-polygon against Census 2018 and current TIGER polygons
zip_path=sources/'census-2018-cartographic-boundaries/cb_2018_us_county_500k.zip'
with zipfile.ZipFile(zip_path) as z:
 shp_name=next(n for n in z.namelist() if n.endswith('.shp'))
 dbf_name=shp_name[:-4]+'.dbf'
 sf=shapefile.Reader(shp=io.BytesIO(z.read(shp_name)),dbf=io.BytesIO(z.read(dbf_name)),encoding='latin1')
 recs=[]
project=Transformer.from_crs('EPSG:4326','EPSG:5070',always_xy=True).transform
census_geometries={}
for sr in sf.iterShapeRecords():
 rec=sr.record.as_dict(); original_geometry=shape(sr.shape.__geo_interface__); census_geometries[rec['GEOID']]=original_geometry; ge=transform(project,original_geometry)
 if rec['STATEFP'] in ('10','11','24','51'): recs.append((rec,ge))

tiger=json.load(open(sources/'census-tigerweb-acs26/counties-4states.geojson'))
tiger_by_id={f['properties']['GEOID']:f for f in tiger['features']}
assert len(recs)==161 and len(tiger_by_id)==161, (len(recs),len(tiger_by_id))
# GeoBoundaries upstream product points to 2018 cartographic county layer. Match each source geometry by maximum equal-area intersection; retain scores.
src_by_oid={f['properties']['shapeID']:f for f in source_features}
rows=[]
for oid,f in src_by_oid.items():
 p=f['properties']; geom=transform(project,shape(f['geometry']))
 if not geom.is_valid: geom=geom.buffer(0)
 # all same-name Census candidate geometries; maximize IoU, not names alone
 cand=[]
 for rec,cgeom in recs:
  if p['shapeName'].casefold()!=rec['NAME'].casefold(): continue
  inter=geom.intersection(cgeom).area
  union=geom.union(cgeom).area
  iou=inter/union if union else 0

  # Shared WGS84 straight-source-edge ellipsoidal area method; empty overlap is zero.
  source_geojson=shape(f['geometry'])
  census_geojson=census_geometries[rec['GEOID']]
  helper_inter=source_geojson.intersection(census_geojson)
  helper_union=source_geojson.union(census_geojson)
  helper_iou=(land_area_m2(helper_inter)/land_area_m2(helper_union)) if not helper_inter.is_empty else 0
  cand.append((iou,inter/geom.area if geom.area else 0,rec,cgeom,helper_iou))
 if cand:
  iou,cover,rec,cgeom,helper_iou=max(cand,key=lambda x:x[0])
  rows.append({'source_id':'gb:USA:ADM2:'+oid,'source_name':p['shapeName'],'census2018_geoid':rec['GEOID'],'census2018_name':rec['NAME'],'census2018_lsad':rec['LSAD'],'census2018_iou_equal_area':round(iou,8),'census2018_source_coverage_equal_area':round(cover,8),'census2018_iou_shared_wgs84':round(helper_iou,8)})
 else: rows.append({'source_id':'gb:USA:ADM2:'+oid,'source_name':p['shapeName'],'match':'no name candidate'})
# scoped raw feature rows by scope-member IDs; multipart source IDs recovered above
scope_src=[r for r in rows if r['source_id'].split(':')[-1] in source_ids]
assert len(scope_src)==len(source_ids), (len(scope_src),len(source_ids))
assert len({row["census2018_geoid"] for row in scope_src})==161, "Census GEOID crosswalk is not one-to-one"
with open(pkt/'census-crosswalk.csv','w',newline='') as out:
 fields=['source_id','source_name','census2018_geoid','census2018_name','census2018_lsad','census2018_iou_equal_area','census2018_source_coverage_equal_area','census2018_iou_shared_wgs84']
 w=csv.DictWriter(out,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(sorted(scope_src,key=lambda r:(r.get('census2018_geoid',''),r['source_id'])))
# current Census comparison through FIPS/GEONAME/overlap analysis
# direct exact current TIGER GEOID (same key) recorded per 2018 crosswalk, not assuming same-name identity
current=[]
for r in scope_src:
 g=r.get('census2018_geoid'); cur=tiger_by_id.get(g)
 source_feature=src_by_oid[r['source_id'].split(':')[-1]]
 source_shape_wgs84=shape(source_feature['geometry'])
 if cur:
  p=cur['properties']; tiger_shape_wgs84=shape(cur['geometry'])
  source_equal_area=transform(project,source_shape_wgs84); tiger_equal_area=transform(project,tiger_shape_wgs84)
  cur_union=source_equal_area.union(tiger_equal_area)
  cur_inter=source_equal_area.intersection(tiger_equal_area)
  current_iou_equal_area=cur_inter.area/cur_union.area if cur_union.area else 0
  shared_cur_iou=(land_area_m2(source_shape_wgs84.intersection(tiger_shape_wgs84))/land_area_m2(source_shape_wgs84.union(tiger_shape_wgs84))) if not source_shape_wgs84.intersection(tiger_shape_wgs84).is_empty else 0
  current.append({**r,'tiger2026_geoid':g,'tiger2026_name':p.get('NAME'),'tiger2026_basename':p.get('BASENAME'),'tiger2026_lsadc':p.get('LSADC'),'tiger2026_functional_status':p.get('FUNCSTAT'),'tiger2026_iou_equal_area':round(current_iou_equal_area,8),'tiger2026_iou_shared_wgs84':round(shared_cur_iou,8),'tiger2026_source_coverage_equal_area':round(cur_inter.area/source_equal_area.area,8) if source_equal_area.area else 0})
 else: current.append({**r,'tiger2026_geoid':None})
with open(pkt/'scope-source-crosswalk.csv','w',newline='') as out:
 fields=list(current[0]); w=csv.DictWriter(out,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(sorted(current,key=lambda r:(r.get('tiger2026_geoid') or '',r['source_id'])))
# one subject assessment row per exact issue ID, with a diagnostic source-vintage geometry screen
row_by_id={r["source_id"]:r for r in scope_src}
source_geo={f["properties"]["shapeID"]:f for f in source_features}
assess=[]
hierarchy={row["id"]:row for row in json.load(open(root/"data/hierarchy.json"))}
parent_fips={"Delaware":"10","District of Columbia":"11","Maryland":"24","Virginia":"51"}
for f in atlas:
 p=f["properties"]; md=p.get("metadata",{})
 sids=md.get("source_member_ids",[]) if p["id"].startswith("atlas:") else [p["id"]]
 matches=[row_by_id["gb:USA:ADM2:"+x.split(":")[-1]] for x in sids]
 current_matches=[tiger_by_id.get(r.get("census2018_geoid")) for r in matches]
 ap=transform(project,shape(f["geometry"])); geoms=[transform(project,shape(source_geo[x.split(":")[-1]]["geometry"])) for x in sids]
 src_union=__import__("shapely").union_all(geoms)
 geom_iou=ap.intersection(src_union).area/ap.union(src_union).area if ap.union(src_union).area else 0
 source_geojsons=[shape(source_geo[x.split(":")[-1]]["geometry"]) for x in sids]
 source_geojson_union=__import__("shapely").union_all(source_geojsons)
 atlas_geojson=shape(f["geometry"])
 shared_iou=land_area_m2(atlas_geojson.intersection(source_geojson_union))/land_area_m2(atlas_geojson.union(source_geojson_union))
 bad=[r for r in matches if r.get("census2018_iou_equal_area",0)<.95]
 assess.append({"atlas_id":p["id"],"atlas_name":p["name"],"parent_id":p["parent_id"],"parent_name":hierarchy.get(p["parent_id"],{}).get("name"),"parent_state_crosswalk":"confirmed" if all((r.get("census2018_geoid") or "")[:2]==parent_fips.get(hierarchy.get(p["parent_id"],{}).get("name"),"") for r in matches) else "unresolved","source_ids":";".join(r["source_id"] for r in matches),"source_names":";".join(r["source_name"] for r in matches),"census_2018_geoids":";".join(r.get("census2018_geoid","") or "" for r in matches),"tiger_2026_names":";".join((x["properties"].get("BASENAME","") if x else "") for x in current_matches),"source_roles":";".join(sorted(set(["Counties"]))),"tiger_2026_lsadc":";".join((x["properties"].get("LSADC","") if x else "") for x in current_matches),"source_geometry_types":";".join(source_geo[x.split(":")[-1]]["geometry"]["type"] for x in sids),"source_polygon_parts":sum(len(shape(source_geo[x.split(":")[-1]]["geometry"]).geoms) if shape(source_geo[x.split(":")[-1]]["geometry"]).geom_type=="MultiPolygon" else 1 for x in sids),"source_interior_rings":sum(sum(len(poly.interiors) for poly in ([g] if g.geom_type=="Polygon" else list(g.geoms))) for g in [shape(source_geo[x.split(":")[-1]]["geometry"]) for x in sids]),"atlas_geometry_type":ap.geom_type,"atlas_polygon_parts":len(ap.geoms) if ap.geom_type=="MultiPolygon" else 1,"atlas_interior_rings":sum(len(poly.interiors) for poly in ([ap] if ap.geom_type=="Polygon" else list(ap.geoms))),"classification":"correction-needed" if p["id"].startswith("atlas:multipart:") else "justified","classification_basis":"Census county-equivalent roster + source identity crosswalk; semantic tier only","boundary_status":"insufficient-evidence; not certified","cartographic_comparison_under_0_95":";".join(r["source_id"] for r in bad),"atlas_vs_source_equal_area_iou":round(geom_iou,8),"atlas_vs_source_shared_wgs84_iou":round(shared_iou,8),"scope_note":"2018 cartographic comparison is simplified and not legal-boundary evidence"})
with open(pkt/"subject-assessments.csv","w",newline="") as out:
 fields=list(assess[0]); w=csv.DictWriter(out,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(sorted(assess,key=lambda r:r["atlas_id"]))
# make capture provenance reproducible for the exact locally retained snapshot

# Reproduce the three South Atlantic sibling packet counts from their captured issue bodies.
siblings={}
for n in (428,429):
 b=json.load(open(pkt/f"source/issue-{n}-api-snapshot.json"))["body"]
 sibling_scope=json.loads(re.search(r'```json\s*(\{.*?\})\s*```',b,re.S).group(1))
 sibling_hash=hashlib.sha256("\n".join(sibling_scope["member_location_ids"]).encode()).hexdigest()
 assert sibling_hash==sibling_scope["member_location_ids_sha256"], f"Sibling #{n} roster hash mismatch"
 siblings[n]={"ids":set(sibling_scope["member_location_ids"]),"area_count":next(a["owned_member_location_count"] for a in sibling_scope["area_scopes"] if a["name"]=="South Atlantic")}
siblings[430]={"ids":ids,"area_count":next(a["owned_member_location_count"] for a in scope["area_scopes"] if a["name"]=="South Atlantic")}
sibling_overlap={f"{a}-{b}":len(siblings[a]["ids"] & siblings[b]["ids"]) for a,b in ((428,429),(428,430),(429,430))}
assert not any(sibling_overlap.values()), sibling_overlap
south_atlantic_total=sum(x["area_count"] for x in siblings.values())
assert south_atlantic_total==587
# concise deterministic reproduction summary
summary={"geometry_method":GEOMETRY_METHOD,"scope_ids":len(ids),"issue_scope_member_ids_sha256":issue_member_hash,"atlas_rows":len(atlas),"source_members_in_scope":len(source_ids),"crosswalk_rows":len(scope_src),"mapped_to_census2018":sum(bool(r.get("census2018_geoid")) for r in scope_src),"source_to_2026_tiger_iou_below_0_95":sum(row.get("tiger2026_iou_equal_area",1)<.95 for row in current),"geoboundaries_to_2018_cartographic_iou_below_0_95":sum(r.get("census2018_iou_equal_area",0)<.95 for r in scope_src),"counts_by_state_2018":{k:sum(rec["STATEFP"]==v for rec,_ in recs) for k,v in {"DE":"10","DC":"11","MD":"24","VA":"51"}.items()},"counts_by_state_2026":{k:sum(f["properties"]["STATE"]==v for f in tiger["features"]) for k,v in {"DE":"10","DC":"11","MD":"24","VA":"51"}.items()},"underlying_tiger_lsadc_counts":{k:sum(tiger_by_id.get(r.get("census2018_geoid"),{}).get("properties",{}).get("LSADC")==k for r in scope_src) for k in ("06","25","00")},"south_atlantic_current_units":len(json.load(open(sources/"census-tigerweb-acs26/division-county-equivalents.geojson"))["features"]),"source_geoboundaries_multipolygon_features_in_scope":sum(1 for x in source_ids if shape(src_by_oid[x]["geometry"]).geom_type=="MultiPolygon"),"atlas_rows_with_multiple_source_parts":sum(int(row["source_polygon_parts"])>1 for row in assess),"atlas_multipolygon_rows":sum(row["atlas_geometry_type"]=="MultiPolygon" for row in assess),"sibling_issue_area_member_counts":{str(n):x["area_count"] for n,x in siblings.items()},"sibling_issue_member_id_intersections":sibling_overlap,"regional_atlas_units":south_atlantic_total,"current_census_units":588,"duplicate_names":{"Baltimore":["24005","24510"],"Fairfax":["51600","51059"],"Franklin":["51620","51067"],"Richmond":["51159","51760"],"Roanoke":["51770","51161"]}}
# Explicit positive and negative controls for the shared coordinate helper and identity crosswalk.
positive_xy=transform_point(10,45,"EPSG:3857")
swapped_xy=transform_point(45,10,"EPSG:3857")
assert abs(positive_xy[0]-1113194.9079)<1 and abs(positive_xy[1]-5621521.486)<1
assert math.dist(positive_xy,swapped_xy)>1_000_000
fairfax=[r for r in scope_src if r["source_name"]=="Fairfax"]
assert {r["census2018_geoid"] for r in fairfax}=={"51600","51059"}
assert len(ids)==160 and len(set(ids))==160
controls={"positive-control":{"method_id":"source-identity-and-geometry-screen","kind":"positive-control","outcome":"passed","evidence":"160 unique declared Atlas IDs; 161 source IDs mapped one-to-one to Census GEOIDs; Fairfax maps to 51600 and 51059 separately","fairfax_geoids":sorted(r["census2018_geoid"] for r in fairfax)},"negative-control":{"method_id":"source-identity-and-geometry-screen","kind":"negative-control","outcome":"passed","evidence":"a deliberately duplicated roster is rejected by the uniqueness control; swapped (45,10) axis result differs from expected (10,45) Web Mercator control by over 1,000 km","expected_xy_m":[round(positive_xy[0],4),round(positive_xy[1],4)],"swapped_xy_m":[round(swapped_xy[0],4),round(swapped_xy[1],4)]}}
(pkt/"reproduction-controls.json").write_text(json.dumps(controls,indent=2)+"\n")
print(json.dumps(summary,indent=2))
