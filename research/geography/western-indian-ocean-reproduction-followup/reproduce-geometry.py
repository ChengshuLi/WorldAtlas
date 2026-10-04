#!/usr/bin/env python3
"""Recreate equal-area source/current overlays and assigned-location overlap screens."""
from __future__ import annotations
import json
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from pyproj import Transformer
from reproduction_common import (SCOPE, FEATURES, HIERARCHY as H,
    BASELINE, PACKET_COMMIT,
    index_feature_property, metric as ratio_diff, pinned_bytes,
    pinned_json, write_candidate)

INPUT='data/regional-review/regional-review-4f180b98473f1071/'
tr=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform
def eq(g):
    return transform(tr,g)

def compare_layer(source_file,source_key,source_prefix,expected_n):
    src=json.loads(pinned_bytes(INPUT+'sources/'+source_file,'issue_packet'))['features']
    source_by_id=index_feature_property(src,source_key,f'{source_file} {source_key}')
    rows=[]
    for i,f in FEATURES.items():
        p=f['properties']; m=p.get('metadata',{}); sid=m.get('source_id','')
        if not sid.startswith(source_prefix): continue
        key=i[len(sid)+1:] if i.startswith(sid+':') else sid.rsplit(':',1)[-1]
        s=source_by_id.get(key)
        if not s: raise SystemExit(f'{i} missing from {source_file}: {key}')
        sg=shape(s['geometry']); cg=shape(f['geometry'])
        sm=ratio_diff(eq(sg),eq(cg))
        rows.append({'id':i,'name':p['name'],'source_name':s['properties'].get('shapeName'),'source_shape_id':key,'source_geom_type':sg.geom_type,'source_components':len(sg.geoms) if sg.geom_type=='MultiPolygon' else 1,'source_valid':sg.is_valid,'current_geom_type':cg.geom_type,'current_components':len(cg.geoms) if cg.geom_type=='MultiPolygon' else 1,'current_valid':cg.is_valid,**sm})
    if len(rows)!=expected_n: raise SystemExit(f'{source_prefix} matched {len(rows)} != {expected_n}')
    return rows

rows=[]
rows += compare_layer('geoBoundaries-MDG-ADM2-2020.geojson','shapeID','gb:MDG:ADM2',119)
rows += compare_layer('geoBoundaries-MUS-ADM1-2017.geojson','shapeID','gb:MUS:ADM1',12)
rows += compare_layer('geoBoundaries-SYC-ADM2-2020.geojson','shapeID','gb:SYC:ADM2',8)
# Comoros is a retained three-island composite, compare the complete union.
com=pinned_json(INPUT+'sources/geoBoundaries-COM-ADM1-2017.geojson','issue_packet')['features']
com_union=unary_union([eq(shape(f['geometry'])) for f in com])
cf=FEATURES['atlas:territory:COM']; cg=eq(shape(cf['geometry']))
com_compare=ratio_diff(com_union,cg)
com_compare.update({'current_id':'atlas:territory:COM','source_ids':[f['properties']['shapeID'] for f in com],'source_names':[f['properties']['shapeName'] for f in com],'source_feature_count':len(com)})
# Four Natural Earth records are the source identity for the corresponding compact island/territory locations.
ne=pinned_json(INPUT+'sources/natural-earth-10m-admin1-selected.geojson','issue_packet')['features']
ne_by_id=index_feature_property(ne,'adm1_code','Natural Earth adm1_code')
ne_rows=[]
for i,f in FEATURES.items():
    sid=f['properties'].get('metadata',{}).get('source_id','')
    if not sid.startswith('natural-earth:'): continue
    key=sid.split(':')[-1]; s=ne_by_id[key]
    sg=shape(s['geometry']); cg=shape(f['geometry']); met=ratio_diff(eq(sg),eq(cg))
    props=s['properties']
    ne_rows.append({'id':i,'source_id':sid,'source_name':props.get('name'),'source_admin':props.get('admin'),'source_type':props.get('type_en') or props.get('type'),'source_iso':props.get('iso_3166_2'),'current_name':f['properties']['name'],'source_geom_type':sg.geom_type,'source_components':len(sg.geoms) if sg.geom_type=='MultiPolygon' else 1,'current_geom_type':cg.geom_type,'current_components':len(cg.geoms) if cg.geom_type=='MultiPolygon' else 1,'source_valid':sg.is_valid,'current_valid':cg.is_valid,**met})
if len(ne_rows)!=4: raise SystemExit('expected four Natural Earth location records')
# Compare parent group partitions for Madagascar to its 22 raw 2017 ADM1 source polygons.
mdg1=pinned_json(INPUT+'sources/geoBoundaries-MDG-ADM1-2017.geojson','issue_packet')['features']
mdg1_by_name=index_feature_property([{**f,'properties':{**f['properties'],'_normalized_name':f['properties']['shapeName'].casefold()}} for f in mdg1],'_normalized_name','geoBoundaries MDG ADM1 shapeName')
mad_parent_rows=[]
for p in SCOPE['province_scopes']:
    if p['id'] not in H or H[p['id']].get('parent_id')!='framework:area:madagascar:319396eea00d': continue
    name=p['name']
    source=mdg1_by_name.get(name.casefold())
    members=[]
    for i,f in FEATURES.items():
        cur=f['properties']['parent_id']
        if cur==p['id']: members.append(i)
    if not source:
        mad_parent_rows.append({'province_id':p['id'],'province_name':name,'member_count':len(members),'source_match':False,'finding':'parent name not directly matched to 2017 ADM1; crosswalk required'})
        continue
    parent_shape=shape(source['geometry'])
    child_union=unary_union([shape(FEATURES[i]['geometry']) for i in members])
    met=ratio_diff(eq(parent_shape),eq(child_union))
    mad_parent_rows.append({'province_id':p['id'],'province_name':name,'member_count':len(members),'source_shape_name':source['properties']['shapeName'],'source_shape_id':source['properties']['shapeID'],'source_valid':parent_shape.is_valid,'member_ids':members,**met})
# Pairwise interior overlap: record candidate substantive overlaps and all near-coincident pairs.
ids=list(FEATURES)
geoms={i:eq(shape(FEATURES[i]['geometry'])) for i in ids}
tree=STRtree([geoms[i] for i in ids]); pair_rows=[]
for ai,i in enumerate(ids):
    for jx in tree.query(geoms[i]):
        j=ids[int(jx)]
        if j<=i: continue
        inter=geoms[i].intersection(geoms[j]).area/1e6
        if inter>0.001:
            pair_rows.append({'id_a':i,'name_a':FEATURES[i]['properties']['name'],'id_b':j,'name_b':FEATURES[j]['properties']['name'],'intersection_km2':inter,'area_a_km2':geoms[i].area/1e6,'area_b_km2':geoms[j].area/1e6,'intersection_over_smaller_percent':100*inter/min(geoms[i].area,geoms[j].area) if min(geoms[i].area,geoms[j].area)>0 else None})
report={'method':{'projection':'EPSG:6933 equal-area cylindrical for all area/overlap measurements','repair':'Raw validity is captured before comparison. shapely.make_valid is applied only to ephemeral comparison clones; retained source and published geometries are never repaired. Only valid Polygon/MultiPolygon results are supported.','symmetric_difference':'100 × area(source symmetric-difference current)/area(source union current)','overlap':'Current assigned location interiors intersected pairwise; pairs below 0.001 km² omitted. Geometric overlaps are leads, not assertions about law or geology.'},'baseline_commit':BASELINE,'source_commit':PACKET_COMMIT,'current_scope_count':len(FEATURES),'geoBoundaries_location_comparisons':{'count':len(rows),'summary':{'median_symmetric_difference_percent':sorted(x['symmetric_difference_of_union_percent'] for x in rows)[len(rows)//2],'max_symmetric_difference_percent':max(x['symmetric_difference_of_union_percent'] for x in rows),'count_over_5_percent':sum(x['symmetric_difference_of_union_percent']>5 for x in rows),'count_over_20_percent':sum(x['symmetric_difference_of_union_percent']>20 for x in rows),'invalid_source_count':sum(not x['source_valid'] for x in rows),'invalid_current_count':sum(not x['current_valid'] for x in rows)},'per_location':rows},'comoros_composite':com_compare,'natural_earth_location_comparisons':ne_rows,'madagascar_parent_2017_ADM1_vs_scoped_2020_ADM2_union':{'count':len(mad_parent_rows),'summary':{'unmatched_parent_names':[x['province_name'] for x in mad_parent_rows if not x.get('source_match',True)],'max_symmetric_difference_percent':max((x.get('symmetric_difference_of_union_percent') or 0 for x in mad_parent_rows),default=0)},'per_parent':mad_parent_rows},'current_location_pairwise_overlaps_over_0_001_km2':sorted(pair_rows,key=lambda x:x['intersection_km2'],reverse=True)}
write_candidate('geometry-comparison.json',report)
print(json.dumps({'GB locations':len(rows),'median symmetric difference %':report['geoBoundaries_location_comparisons']['summary']['median_symmetric_difference_percent'],'max symmetric difference %':report['geoBoundaries_location_comparisons']['summary']['max_symmetric_difference_percent'],'GB pairs >5%':report['geoBoundaries_location_comparisons']['summary']['count_over_5_percent'],'Comoros':com_compare,'Natural Earth comparisons':[(x['id'],round(x['symmetric_difference_of_union_percent'],6)) for x in ne_rows],'Madagascar parent max diff %':report['madagascar_parent_2017_ADM1_vs_scoped_2020_ADM2_union']['summary'],'pairwise overlaps':len(pair_rows),'top overlaps':report['current_location_pairwise_overlaps_over_0_001_km2'][:8]},ensure_ascii=False,indent=2))
