#!/usr/bin/env python3
"""Reproduce seven Arctic candidate geometric fit checks from pinned source inputs."""
from __future__ import annotations
import gzip, hashlib, json, sys
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[3]
PACKET=Path(__file__).resolve().parent
CONTEXT=ROOT/'coordination/engineering/eastern-two-gap-repair-20261007/run-two/full-four-family-context.json.gz'
INDEX=ROOT/'coordination/engineering/eastern-two-gap-repair-20261007/input-index.json'
CANDIDATES=[
 ('physical-component:12c9ec9813490ce8602fb26ee2e54225b99c28bbd29794a7f8ac9ee60f109e8a',15,'atlas:physical:CAN-15:NWT','Sachs Harbour','Victoria Lowlands'),
 ('physical-component:52452c5923a0ed15767ebdf150727924778349b7d9ba4370b616d1d70c0ccddd',15,'atlas:physical:CAN-15:NWT','Region 1, Unorganized','Victoria Lowlands'),
 ('physical-component:add031b7195352292c8529323c8b99dd75002af629116b229e84be981893ca8d',25,'atlas:physical:CAN-25:NUN','Baffin, Unorganized','Foxe–Boothia Lowlands'),
 ('physical-component:2aca267603c8eace3a6d0a52d4e3f0b70a47506b94d2ea9e1d500e43aab4632c',25,'atlas:physical:CAN-25:NUN','Baffin, Unorganized','Foxe–Boothia Lowlands'),
 ('physical-component:265c983a61231e3a5c2cf4bb2f7b97896d47afefe925a9eb85934101a78515a8',25,'atlas:physical:CAN-25:NUN','Baffin, Unorganized','Foxe–Boothia Lowlands'),
 ('physical-component:17bb5b7f043b0fb2b447b8ccef216e530fed4595da1aec0feb1dea235bed0dbd',25,'atlas:physical:CAN-25:NUN','Baffin, Unorganized','Foxe–Boothia Lowlands'),
 ('physical-component:54dc96cd3d0edd92ff9d9399d8364e17735d12f11407f707d57912f9f6a66475',25,'atlas:physical:CAN-25:NUN','Baffin, Unorganized','Foxe–Boothia Lowlands'),
]
def read_json(p): return json.loads(Path(p).read_bytes())
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
 ctx=json.loads(gzip.decompress(CONTEXT.read_bytes()))
 comps={x['id']:x for x in ctx['components']}
 idx=read_json(ROOT/'data/world-index.json')
 current=[]
 for rel in idx['parts']:
  d=read_json(ROOT/'data'/rel)
  current.extend((f['id'],shape(f['geometry'])) for f in d['features'])
 assert len(current)==49625, len(current)
 atlas_features={f['id']:f for f in read_json(ROOT/'data/geography/part-29.json')['features']}
 hierarchy={x['id']:x for x in read_json(ROOT/'data/hierarchy.json')}
 native=read_json(PACKET/'sources/aafc-ecoregions.native.geojson')['features']
 v22=json.loads(gzip.decompress((PACKET/'sources/aafc-terrestrial-ecoregions-v2.2.geojson.gz').read_bytes()))['features']
 provinces=json.loads(gzip.decompress((PACKET/'sources/aafc-ecoprovinces-baseline-arcgis-layer0.geojson.gz').read_bytes()))['features']
 idxdata=read_json(INDEX)
 retired_parts=[]
 for i in range(47,54):
  name=f'i{i:03d}.bin.gz'; alias=next(a for a in idxdata['aliases'] if a['ordinary']['path'].endswith(name))
  compressed=(ROOT/'coordination/engineering/eastern-two-gap-repair-20261007'/alias['ordinary']['path']).read_bytes()
  assert sha(compressed)==alias['ordinary']['sha256']
  decoded=gzip.decompress(compressed); assert sha(decoded)==alias['ordinary']['decoded_sha256']
  retired_parts.append(decoded)
 retired_bytes=b''.join(retired_parts); assert sha(retired_bytes)=='c072bbe6e7f96789e3a6165e9075eb3271050e1e1614f2923f03169480537184'
 retired=json.loads(retired_bytes)
 retired_ids={
  'ECO15':['gb:CAN:ADM3:43193130B40321569586625','gb:CAN:ADM3:43193130B96648191896746'],
  'ECO25':['gb:CAN:ADM3:43193130B13052897136233','gb:CAN:ADM3:43193130B30076837012949','gb:CAN:ADM3:43193130B6772247703215']}
 old={x['id']:x for x in retired['locations']}
 geojson={'type':'FeatureCollection','features':[]}
 results=[]
 for cid,eid,target_id,admin,parent in CANDIDATES:
  candidate=shape(comps[cid]['geometry']); target=shape(atlas_features[target_id]['geometry'])
  def by_id(features,key): return [shape(f['geometry']) for f in features if f['properties'].get(key)==eid]
  native_source=by_id(native,'ECOREGION_ID'); v22_source=by_id(v22,'ECOREGION_ID')
  assert len(native_source)==len(v22_source)==1, (cid,len(native_source),len(v22_source))
  native_envelopes=[{'id':f['properties'].get('ECOREGION_ID'),'name':f['properties'].get('ECOREGION_NAME_EN')} for f in native if shape(f['geometry']).covers(candidate)]
  v22_envelopes=[{'id':f['properties'].get('ECOREGION_ID'),'name':f['properties'].get('ECOREGION_NAME_EN')} for f in v22 if shape(f['geometry']).covers(candidate)]
  wrong_eid=25 if eid==15 else 15
  wrong_native=next(f for f in native if f['properties'].get('ECOREGION_ID')==wrong_eid)
  wrong_v22=next(f for f in v22 if f['properties'].get('ECOREGION_ID')==wrong_eid)
  cross_group_control={'native_wrong_region_covers_candidate':shape(wrong_native['geometry']).covers(candidate),'v22_wrong_region_covers_candidate':shape(wrong_v22['geometry']).covers(candidate),'native_intersection_area_deg2':shape(wrong_native['geometry']).intersection(candidate).area,'v22_intersection_area_deg2':shape(wrong_v22['geometry']).intersection(candidate).area}
  hits=[]
  for fid,g in current:
   if g.intersects(candidate):
    inter=g.intersection(candidate)
    hits.append({'id':fid,'dimension':'area' if inter.area>0 else ('line' if inter.length>0 else 'point'),'area_deg2':inter.area,'length_degrees':inter.length})
  old_union=target.union(candidate)
  loss=target.difference(old_union); gain=old_union.difference(target)
  candidate_not_added=candidate.difference(gain)
  gain_candidate_difference=gain.symmetric_difference(candidate)
  candidate_target_overlap=candidate.intersection(target)
  neighbor_intersections=[]
  for fid,g in current:
   if fid!=target_id and g.intersects(candidate):
    inter=g.intersection(candidate)
    if inter.area>0: neighbor_intersections.append({'id':fid,'dimension':'area','area_deg2':inter.area,'length_degrees':inter.length,'geometry':mapping(inter)})
  parent_id=2.3 if eid==15 else 2.7
  parent_hits=[]
  for f in provinces:
   if f['properties'].get('ECOPROVINCE_ID')==parent_id:
    pg=shape(f['geometry'])
    if pg.intersects(candidate): parent_hits.append({'objectid':f['properties'].get('OBJECTID'),'name':f['properties'].get('ECOPROVINCE_NAME_EN'),'covers':pg.covers(candidate),'intersection_area_deg2':pg.intersection(candidate).area})
  refs=[]
  for rid in retired_ids['ECO15' if eid==15 else 'ECO25']:
   ref=old[rid]; rg=shape(ref['geometry']); inter=rg.intersection(candidate)
   refs.append({'id':rid,'name':ref['name'],'parent_chain':ref['parent_chain'],'relation':'candidate-covered-by-reference' if rg.covers(candidate) else ('positive-area-overlap' if inter.area>0 else ('line-contact' if inter.length>0 else ('point-contact' if not inter.is_empty else 'disjoint'))),'intersection_area_deg2':inter.area,'intersection_length_degrees':inter.length,'intersection_geometry':mapping(inter) if not inter.is_empty else None})
  strict=loss.is_empty and gain.equals(candidate) and old_union.is_valid and len(neighbor_intersections)==0
  if strict: geojson['features'].append({'type':'Feature','id':cid,'properties':{'component_id':cid,'target_id':target_id,'status':'proposed-exact-no-loss-addition'},'geometry':mapping(old_union)})
  target_row=atlas_features[target_id]
  target_parent=hierarchy.get(target_row['properties']['parent_id'])
  target_hierarchy_row=hierarchy.get(target_id)
  target_member_ids=target_row['properties'].get('metadata',{}).get('source_member_ids',[])
  retired_ids_for_group=retired_ids['ECO15' if eid==15 else 'ECO25']
  native_record=next(f for f in native if f['properties'].get('ECOREGION_ID')==eid)
  v22_record=next(f for f in v22 if f['properties'].get('ECOREGION_ID')==eid)
  parent_name=parent_hits[0]['name'] if parent_hits else None
  native_parent_match=round(float(native_record['properties'].get('ECOPROVINCE_ID')),1)==parent_id
  v22_parent_match=round(float(v22_record['properties'].get('ECOPROVINCE_ID')),1)==parent_id
  atlas_parent_match=bool(target_parent and target_parent.get('name')==parent_name)
  results.append({'component_id':cid,'source_ecoregion_id':eid,'atlas_target_id':target_id,'administrative_reference':admin,'source_parent':parent,
   'candidate_geometry':mapping(candidate),'candidate_area_deg2':candidate.area,
   'native_source_name':next(f['properties']['ECOREGION_NAME_EN'] for f in native if f['properties'].get('ECOREGION_ID')==eid),
   'v22_source_name':next(f['properties']['ECOREGION_NAME_EN'] for f in v22 if f['properties'].get('ECOREGION_ID')==eid),
   'native_source_properties':native_record['properties'],'v22_source_properties':v22_record['properties'],
   'atlas_target_name':target_row['properties']['name'],'atlas_target_parent_id':target_row['properties']['parent_id'],
   'atlas_target_source_member_ids':target_member_ids,'retired_context_ids_match_target_source_members':set(target_member_ids)==set(retired_ids_for_group),
   'ecoregion_parent_id_matches_source_parent_both_editions':native_parent_match and v22_parent_match,
   'atlas_hierarchy_parent_name_matches_source_parent_name':atlas_parent_match,
   'atlas_target_hierarchy_record':target_hierarchy_row,'atlas_parent_hierarchy_record':target_parent,
   'candidate_valid':candidate.is_valid,'candidate_area_deg2':candidate.area,
   'native_covering_named_envelopes':native_envelopes,'v22_covering_named_envelopes':v22_envelopes,
   'cross_group_adverse_control':cross_group_control,
   'exactly_one_covering_named_envelope_both_editions':len(native_envelopes)==len(v22_envelopes)==1 and native_envelopes[0]['id']==eid and v22_envelopes[0]['id']==eid,
   'native_source_covers_candidate':native_source[0].covers(candidate),'v22_source_covers_candidate':v22_source[0].covers(candidate),
   'native_vs_v22_symmetric_difference_deg2':native_source[0].symmetric_difference(v22_source[0]).area,
   'target_source_covers_candidate':target.covers(candidate),'active_feature_hits':hits,
   'only_intended_target_hit':len(hits)==1 and hits[0]['id']==target_id,
   'source_parent_coverage_records':parent_hits,'retired_administrative_reference_context':refs,
   'union_valid':old_union.is_valid,'union_geometry_type':old_union.geom_type,'union_area_deg2':old_union.area,'union_geometry':mapping(old_union),
   'union_loss_area_deg2':loss.area,'union_gain_area_deg2':gain.area,'loss_geometry':mapping(loss) if not loss.is_empty else None,'gain_geometry':mapping(gain) if not gain.is_empty else None,'candidate_not_added_area_deg2':candidate_not_added.area,'candidate_not_added_geometry':mapping(candidate_not_added) if not candidate_not_added.is_empty else None,'gain_candidate_symmetric_difference_area_deg2':gain_candidate_difference.area,'gain_candidate_symmetric_difference_geometry':mapping(gain_candidate_difference) if not gain_candidate_difference.is_empty else None,'candidate_target_overlap_area_deg2':candidate_target_overlap.area,'candidate_target_overlap_geometry':mapping(candidate_target_overlap) if not candidate_target_overlap.is_empty else None,
   'new_neighbor_intersections':neighbor_intersections,
   'strict_lossless_addition':strict,
   'decision':'repair-ready-geometric-proposal' if strict and len(hits)==1 and hits[0]['id']==target_id else 'unresolved-topology-or-neighbor-condition'})
 out={'method':'GEOS/Shapely topological predicates and union; area fields are square degrees except where explicitly labeled','active_feature_count':len(current),'active_part_count':len(idx['parts']),'component_count':len(results),'retired_archive_sha256':sha(retired_bytes),'retired_location_count':len(retired['locations']),'results':results,
      'limitations':['Geometric source fit does not establish historical cause, land/water status, boundary authority, or approval.','Native AAFC and v2.2 are distinct editions; coverage is reported separately.']}
 raw=(json.dumps(out,sort_keys=True,separators=(',',':'))+'\n').encode(); (PACKET/'candidate-decisions.json').write_bytes(raw)
 (PACKET/'proposed-additions.geojson').write_text(json.dumps(geojson,sort_keys=True,separators=(',',':'))+'\n')
 print(json.dumps({'status':'reproduced','components':len(results),'active_features':len(current),'decisions':[{'id':r['component_id'],'decision':r['decision']} for r in results],'sha256':sha(raw)},sort_keys=True))
if __name__=='__main__': main()
