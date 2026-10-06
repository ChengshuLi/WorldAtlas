#!/usr/bin/env python3
"""Reproduce exact source overlays and descriptive WorldCover samples for #1243."""
import hashlib, json, gzip, pathlib, sys, math, os
import rasterio
import numpy as np
from shapely.geometry import shape, mapping, box
from shapely.strtree import STRtree
from shapely.ops import unary_union
from shapely import contains_xy

ROOT=pathlib.Path(__file__).resolve().parent
OUT=pathlib.Path(os.environ.get('OUTPUT_DIR', ROOT/'outputs')); OUT.mkdir(parents=True,exist_ok=True)

def readj(p): return json.loads(pathlib.Path(p).read_text())
def sha(b): return hashlib.sha256(b).hexdigest()
def geomhash(g): return sha(g.wkb)
def jwrite(p,x): pathlib.Path(p).write_text(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n')

components=readj(ROOT/'inputs/component-features.geojson')['features']
fragments=readj(ROOT/'inputs/original-fragments.geojson')['features']
contacts=readj(ROOT/'inputs/contact-features.geojson')['features']
roster=readj(ROOT/'inputs/family-roster.json')
assert len(components)==10 and len(fragments)==10 and len(contacts)==5
assert {f['id'] for f in components}==set(roster['component_ids'])
assert {f['id'] for f in contacts}==set(roster['contact_ids'])

admin={}
for country,code in [('COD','COD'),('AGO','AGO')]:
 p=ROOT/f'sources/administrative/gb-{country}-ADM2-ADM2-consumed-simplified.geojson'
 d=readj(p); admin[country]=d['features']; assert len(admin[country])==({'COD':189,'AGO':161}[country])

# Geometry overlays against every consumed source feature. Exact source coordinates,
# no repair, snapping, buffering, reprojection, or nearest-feature assignment.
rows=[]
for comp in sorted(components,key=lambda f:f['id']):
 cg=shape(comp['geometry']); item={'component_id':comp['id'],'component_geometry_sha256':geomhash(cg),'admin_sources':{}}
 for country,features in admin.items():
  geoms=[shape(f['geometry']) for f in features]
  tree=STRtree(geoms)
  bbox_ix=sorted(map(int,tree.query(cg)))
  ix=tree.query(cg,predicate='intersects')
  hits=[]
  for i in sorted(map(int,ix)):
   fg=geoms[i]; inter=cg.intersection(fg)
   if inter.is_empty: continue
   feat=features[i]
   hits.append({'source_feature_index':i,'source_feature_id':feat.get('id'),'shapeID':feat['properties'].get('shapeID'),'shapeName':feat['properties'].get('shapeName'),'source_geometry_sha256':geomhash(fg),'intersection_geometry_sha256':geomhash(inter),'intersection_wkb_hex':inter.wkb_hex,'intersection_type':inter.geom_type,'intersection_area_degrees2':inter.area,'bbox_candidate':bool(cg.envelope.intersects(fg.envelope))})
  union=unary_union([geoms[i] for i in sorted(map(int,ix))]) if len(ix) else None
  diff=cg.difference(union) if union else cg
  reverse=union.difference(cg) if union else cg.difference(cg)
  bbox_rows=[{'source_feature_index':i,'shapeID':features[i]['properties'].get('shapeID'),'shapeName':features[i]['properties'].get('shapeName'),'source_geometry_sha256':geomhash(geoms[i]),'exact_intersects':i in set(map(int,ix))} for i in bbox_ix]
  item['admin_sources'][country]={'bbox_candidates':bbox_rows,'bbox_candidate_count':len(bbox_rows),'intersecting_features':hits,'intersecting_count':len(hits),'positive_area_intersections':sum(h['intersection_area_degrees2']>0 for h in hits),'zero_area_intersections':sum(h['intersection_area_degrees2']==0 for h in hits),'intersecting_admin_union_wkb_hex':union.wkb_hex if union else None,'intersecting_admin_union_geometry_sha256':geomhash(union) if union else None,'component_minus_intersecting_admin_union_wkb_hex':diff.wkb_hex,'component_minus_union_geometry_sha256':geomhash(diff),'component_minus_union_area_degrees2':diff.area,'intersecting_admin_union_minus_component_wkb_hex':reverse.wkb_hex,'intersecting_admin_union_minus_component_geometry_sha256':geomhash(reverse),'intersecting_admin_union_minus_component_area_degrees2':reverse.area}
 rows.append(item)
# Whole-source Natural Earth reference intersections; source itself is incomplete and not a water authority.
water=json.loads(gzip.decompress((ROOT/'sources/natural-earth/natural-earth-lakes.geojson.gz').read_bytes()))
waterfeats=water['features']; wgeoms=[shape(f['geometry']) for f in waterfeats]; wt=STRtree(wgeoms)
for item,comp in zip(rows,sorted(components,key=lambda f:f['id'])):
 cg=shape(comp['geometry']); ids=sorted(map(int,wt.query(cg,predicate='intersects'))); hits=[]
 for i in ids:
  inter=cg.intersection(wgeoms[i])
  if not inter.is_empty:
   hits.append({'feature_index':i,'feature_id':waterfeats[i].get('id'),'geometry_sha256':geomhash(wgeoms[i]),'intersection_wkb_hex':inter.wkb_hex,'intersection_geometry_sha256':geomhash(inter),'intersection_type':inter.geom_type,'area_degrees2':inter.area})
 item['natural_earth_lakes']={'intersecting_features':hits,'count':len(hits),'positive_area_count':sum(h['area_degrees2']>0 for h in hits),'zero_area_count':sum(h['area_degrees2']==0 for h in hits)}
# Combined complete consumed-product union and symmetric residuals per component.
for rec,comp in zip(rows,sorted(components,key=lambda f:f['id'])):
 cg=shape(comp['geometry']); combined=[]
 for country in ('COD','AGO'):
  indices=[x['source_feature_index'] for x in rec['admin_sources'][country]['intersecting_features']]
  combined += [shape(admin[country][i]['geometry']) for i in indices]
 u=unary_union(combined) if combined else None
 residual=cg.difference(u) if u else cg
 reverse=u.difference(cg) if u else cg.difference(cg)
 rec['combined_consumed_admin_source_union']={'union_geometry_sha256':geomhash(u) if u else None,'union_wkb_hex':u.wkb_hex if u else None,'component_minus_union_geometry_sha256':geomhash(residual),'component_minus_union_wkb_hex':residual.wkb_hex,'component_minus_union_area_degrees2':residual.area,'union_minus_component_geometry_sha256':geomhash(reverse),'union_minus_component_wkb_hex':reverse.wkb_hex,'union_minus_component_area_degrees2':reverse.area}
# Independent Natural Earth physical-land reference, retained as a coarse
# boundary/land polygon overlay only, never as a complete hydrology or shoreline.
land=json.loads(gzip.decompress((ROOT/'sources/natural-earth/natural-earth-land.geojson.gz').read_bytes()))
land_features=land['features']; land_geoms=[shape(f['geometry']) for f in land_features]; land_tree=STRtree(land_geoms)
for rec,comp in zip(rows,sorted(components,key=lambda f:f['id'])):
 cg=shape(comp['geometry']); bbox_ids=sorted(map(int,land_tree.query(cg))); exact_ids=sorted(map(int,land_tree.query(cg,predicate='intersects'))); hits=[]; land_intersections=[]
 for i in exact_ids:
  inter=cg.intersection(land_geoms[i])
  if not inter.is_empty:
   land_intersections.append(inter); hits.append({'source_feature_index':i,'source_feature_id':land_features[i].get('id'),'source_geometry_sha256':geomhash(land_geoms[i]),'intersection_geometry_sha256':geomhash(inter),'intersection_wkb_hex':inter.wkb_hex,'intersection_type':inter.geom_type,'intersection_area_degrees2':inter.area})
 union=unary_union(land_intersections) if land_intersections else None
 residual=cg.difference(union) if union else cg; reverse=union.difference(cg) if union else cg.difference(cg)
 rec['natural_earth_land']={'source_feature_count':len(land_features),'bbox_candidates':[{'source_feature_index':i,'source_feature_id':land_features[i].get('id'),'source_geometry_sha256':geomhash(land_geoms[i]),'exact_intersects':i in set(exact_ids)} for i in bbox_ids],'intersecting_features':hits,'count':len(hits),'positive_area_count':sum(h['intersection_area_degrees2']>0 for h in hits),'zero_area_count':sum(h['intersection_area_degrees2']==0 for h in hits),'intersecting_land_union_wkb_hex':union.wkb_hex if union else None,'intersecting_land_union_geometry_sha256':geomhash(union) if union else None,'component_minus_intersecting_land_union_wkb_hex':residual.wkb_hex,'component_minus_intersecting_land_union_geometry_sha256':geomhash(residual),'component_minus_intersecting_land_union_area_degrees2':residual.area,'intersecting_land_union_minus_component_wkb_hex':reverse.wkb_hex,'intersecting_land_union_minus_component_geometry_sha256':geomhash(reverse),'intersecting_land_union_minus_component_area_degrees2':reverse.area}
jwrite(OUT/'geometry-overlays.json',{'method':'exact planar overlay in source EPSG:4326 coordinates; no geometry repair or coordinate operation','components':rows})

# Strict-interior pixel-centre counts for ESA WorldCover v200. Class counts are
# descriptive observations, not a full polygon water classification.
tile_dir=pathlib.Path(os.environ.get('WORLD_COVER_DIR', ROOT/'sources/worldcover-v200'))
tilepaths=sorted(tile_dir.glob('*_Map.tif'))
assert len(tilepaths)==2, 'Restore the two exact pinned WorldCover tiles; see sources/worldcover-v200/retrieval.json'
expected={'ESA_WorldCover_10m_2021_v200_S09E015_Map.tif':'6033c776f2b66117f15b563aa0429a8afb9f6c993da15740ff949b814081e611','ESA_WorldCover_10m_2021_v200_S09E018_Map.tif':'5f0e07b325e5a5ed8e7a372fa7c38472d3395b93f39cf9bace9999fe8727f68f'}
assert {p.name:sha(p.read_bytes()) for p in tilepaths}==expected, 'WorldCover tile bytes differ from pinned originals'
counts=[]; tilemeta=[]; cover_boxes=[]
for p in tilepaths:
 with rasterio.open(p) as ds:
  cover_boxes.append(box(ds.bounds.left,ds.bounds.bottom,ds.bounds.right,ds.bounds.top))
  tilemeta.append({'file':p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes()),'crs':str(ds.crs),'width':ds.width,'height':ds.height,'transform':list(ds.transform)[:6],'nodata':ds.nodata,'bounds':[ds.bounds.left,ds.bounds.bottom,ds.bounds.right,ds.bounds.top]})
coverage=unary_union(cover_boxes)
coverage_check={f['id']:bool(coverage.covers(shape(f['geometry']))) for f in components}
assert all(coverage_check.values()), 'WorldCover tile footprints do not cover every complete component geometry'
for comp in sorted(components,key=lambda f:f['id']):
 g=shape(comp['geometry']); byclass={}; pixels=0
 for p in tilepaths:
  with rasterio.open(p) as ds:
   if not g.intersects(shape({'type':'Polygon','coordinates':[[[ds.bounds.left,ds.bounds.bottom],[ds.bounds.right,ds.bounds.bottom],[ds.bounds.right,ds.bounds.top],[ds.bounds.left,ds.bounds.top],[ds.bounds.left,ds.bounds.bottom]]]})): continue
   from rasterio.windows import from_bounds
   win=from_bounds(*g.bounds,transform=ds.transform).round_offsets().round_lengths()
   win=win.intersection(rasterio.windows.Window(0,0,ds.width,ds.height))
   if win.width<=0 or win.height<=0: continue
   arr=ds.read(1,window=win)
   tr=ds.window_transform(win); rr,cc=np.indices(arr.shape); xs=tr.c+(cc+0.5)*tr.a+(rr+0.5)*tr.b; ys=tr.f+(cc+0.5)*tr.d+(rr+0.5)*tr.e
   mask=contains_xy(g,xs,ys); vals=arr[mask]; pixels+=int(mask.sum())
   vals,nums=np.unique(vals,return_counts=True)
   for v,n in zip(vals,nums): byclass[str(int(v))]=byclass.get(str(int(v)),0)+int(n)
 counts.append({'component_id':comp['id'],'strict_interior_pixel_centres':pixels,'class_counts':dict(sorted(byclass.items(),key=lambda z:int(z[0]))),'class_80_water_observation_pixels':byclass.get('80',0),'class_90_wetland_observation_pixels':byclass.get('90',0),'interpretation':'class 80/90 presence is observed at sampled pixel centres; absence is not evidence of dry land; no full-shape certification'})
jwrite(OUT/'worldcover-samples.json',{'source':'ESA WorldCover 10m 2021 v200','full_component_tile_footprint_coverage':coverage_check,'sampling':'strict polygon interior at pixel centres; native EPSG:4326 tiles; class 0 preserved as NoData/unknown','tiles':tilemeta,'components':counts})
# Exact compact summary with generated scalar bindings later.
summary={'component_count':len(components),'original_fragment_count':len(fragments),'contact_count':len(contacts),'admin_source_feature_counts':{k:len(v) for k,v in admin.items()},'natural_earth_lakes_feature_count':len(waterfeats),'worldcover_tile_count':len(tilepaths),'family_cause_status':'unknown','geographic_approval':'unapproved','source_approval':False,'all_component_source_lineage_linked':True}
# Every component receives a full-scope disposition. Prior complete-source screening
# is explicitly separate from these current overlays and from any causal approval.
prior=readj(ROOT/'inputs/prior-source-screen.json')
priorrows={r['component']:r['screen'] for r in prior['rows']}
assessment=[]
for comp,rec,wc in zip(sorted(components,key=lambda f:f['id']),rows,counts):
 screen=priorrows[comp['id']]
 assessment.append({'component_id':comp['id'],'classification':'unresolved','reason':'Administrative-source intersection/coverage and 2021 land-cover point samples do not establish physical water status, original processing loss, or causal stage.','prior_full_source_screen_status':screen['row']['status'],'prior_source_operation_consistency_unknown':screen['operation_consistency_unknown'],'unique_compatible_recorded_subject':screen['row'].get('uniquely_covering_compatible_recorded_subject'),'positive_area_source_feature_count':sum(v['positive_area_intersections'] for v in rec['admin_sources'].values()),'zero_area_source_feature_count':sum(v['zero_area_intersections'] for v in rec['admin_sources'].values()),'component_minus_combined_admin_union_area_degrees2':rec['combined_consumed_admin_source_union']['component_minus_union_area_degrees2'],'original_water_status':comp['properties'].get('water_status'),'original_diagnostics':comp['properties'].get('diagnostic_nearby_locations'),'original_unmeasured_fragment_ids':comp['properties'].get('unmeasured_fragment_ids'),'original_fragment_ids':[x['id'] for x in comp['properties'].get('fragment_bindings',[])],'natural_earth_lake_hits':rec['natural_earth_lakes']['count'],'natural_earth_land_feature_hits':rec['natural_earth_land']['count'],'natural_earth_land_intersection_area_degrees2':sum(x['intersection_area_degrees2'] for x in rec['natural_earth_land']['intersecting_features']),'worldcover_class_80_observation_pixels':wc['class_80_water_observation_pixels'],'worldcover_class_90_observation_pixels':wc['class_90_wetland_observation_pixels'],'worldcover_limit':'2021 land cover at sampled pixel centres; neither full-shape hydrology nor historical 2018/2019 water authority'})
jwrite(OUT/'component-assessment.json',{'family_id':roster['id'],'component_count':len(assessment),'prior_screen_sha256':sha((ROOT/'inputs/prior-source-screen.json').read_bytes()),'classification_scope':'all ten; no causal assignment, physical-water certification, geometry proposal, ownership change, or repair approval','components':assessment})
summary['component_assessment_count']=len(assessment)
summary['successor_linked_component_count']=len(readj(ROOT/'inputs/current-successor-vintage.json')['target_component_lineage'])
summary['prior_unique_compatible_screen_count']=sum(x['unique_compatible_recorded_subject'] is not None for x in assessment)
summary['prior_mixed_partial_screen_count']=sum(x['unique_compatible_recorded_subject'] is None for x in assessment)
jwrite(OUT/'summary.json',summary)

# Resolve every preserved original fragment and each full contact feature against
# the same complete consumed administrative products. Store complete exact intersections.
fragment_contact=[]
for layer,features in [('original-fragments',fragments),('contacts',contacts)]:
 for feature in sorted(features,key=lambda f:f['id']):
  fg=shape(feature['geometry']); rec={'layer':layer,'feature_id':feature['id'],'geometry_sha256':geomhash(fg),'admin_sources':{}}
  for country,source_features in admin.items():
   gs=[shape(f['geometry']) for f in source_features]; tree=STRtree(gs)
   bbox_ids=sorted(map(int,tree.query(fg)))
   exact=[]
   for i in bbox_ids:
    src=source_features[i]; sg=gs[i]; inter=fg.intersection(sg)
    if not inter.is_empty:
     exact.append({'source_feature_index':i,'source_feature_id':src.get('id'),'shapeID':src['properties'].get('shapeID'),'shapeName':src['properties'].get('shapeName'),'source_geometry_sha256':geomhash(sg),'intersection_geometry_sha256':geomhash(inter),'intersection_wkb_hex':inter.wkb_hex,'intersection_type':inter.geom_type,'intersection_area_degrees2':inter.area})
   rec['admin_sources'][country]={'bbox_candidates':[{'source_feature_index':i,'source_feature_id':source_features[i].get('id'),'shapeID':source_features[i]['properties'].get('shapeID'),'shapeName':source_features[i]['properties'].get('shapeName'),'source_geometry_sha256':geomhash(gs[i]),'exact_intersects':bool(fg.intersects(gs[i]))} for i in bbox_ids],'bbox_candidate_count':len(bbox_ids),'intersecting_features':exact,'intersecting_count':len(exact),'positive_area_intersections':sum(x['intersection_area_degrees2']>0 for x in exact),'zero_area_intersections':sum(x['intersection_area_degrees2']==0 for x in exact)}
  fragment_contact.append(rec)
jwrite(OUT/'fragment-contact-overlays.json',{'method':'exact planar overlay in source EPSG:4326 coordinates; no repair, snapping, buffering or assignment','features':fragment_contact})
