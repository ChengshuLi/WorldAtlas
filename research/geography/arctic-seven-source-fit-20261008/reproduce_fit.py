#!/usr/bin/env python3
"""Reproduce seven Arctic candidate geometric fit checks from pinned source inputs."""
from __future__ import annotations
import gzip, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
PACKET=Path(__file__).resolve().parent
from source_phase_runtime import require_phase, read_bytes, read_json, write_packet_output, predecessor_execution, execution_plan, execution_plan_sha256
CONTEXT=ROOT/'coordination/engineering/eastern-two-gap-repair-20261007/run-two/full-four-family-context.json.gz'
CANDIDATES=[
 ('physical-component:12c9ec9813490ce8602fb26ee2e54225b99c28bbd29794a7f8ac9ee60f109e8a',15,'atlas:physical:CAN-15:NWT','Sachs Harbour','Victoria Lowlands'),
 ('physical-component:52452c5923a0ed15767ebdf150727924778349b7d9ba4370b616d1d70c0ccddd',15,'atlas:physical:CAN-15:NWT','Region 1, Unorganized','Victoria Lowlands'),
 ('physical-component:add031b7195352292c8529323c8b99dd75002af629116b229e84be981893ca8d',25,'atlas:physical:CAN-25:NUN','Baffin, Unorganized','Foxe-Boothia Lowlands'),
 ('physical-component:2aca267603c8eace3a6d0a52d4e3f0b70a47506b94d2ea9e1d500e43aab4632c',25,'atlas:physical:CAN-25:NUN','Baffin, Unorganized','Foxe-Boothia Lowlands'),
 ('physical-component:265c983a61231e3a5c2cf4bb2f7b97896d47afefe925a9eb85934101a78515a8',25,'atlas:physical:CAN-25:NUN','Baffin, Unorganized','Foxe-Boothia Lowlands'),
 ('physical-component:17bb5b7f043b0fb2b447b8ccef216e530fed4595da1aec0feb1dea235bed0dbd',25,'atlas:physical:CAN-25:NUN','Baffin, Unorganized','Foxe-Boothia Lowlands'),
 ('physical-component:54dc96cd3d0edd92ff9d9399d8364e17735d12f11407f707d57912f9f6a66475',25,'atlas:physical:CAN-25:NUN','Baffin, Unorganized','Foxe-Boothia Lowlands'),
]
def sha(b): return hashlib.sha256(b).hexdigest()
def disposition(criteria): return 'repair-ready-geometric-proposal' if all(criteria.values()) else 'unresolved-topology-or-neighbor-condition'
def main():
 require_phase('source-fit')
 from shapely.geometry import shape, mapping
 sys.path.insert(0,str(ROOT/'scripts'))
 from evidence.geometry import land_area_m2, METHOD as GEOGRAPHIC_METHOD
 ctx=json.loads(gzip.decompress(read_bytes(CONTEXT)))
 comps={x['id']:x for x in ctx['components']}
 native_extraction=read_json(PACKET/'native-archive-extraction.json')
 assert native_extraction['status']=='native-member-extracted'
 assert native_extraction['member_byte_identical_to_retained_file'] is True
 retired_receipt=predecessor_execution(PACKET/'retired-member-context-phase2.json')
 assert retired_receipt['phase']=='retired-context'
 plan=execution_plan()
 native_phase=next(x for x in plan['phases'] if x['name']=='native-archive-extract')
 native_output=f"{native_phase['owned_path']}vintages/{native_phase['vintage']}/native-archive-extraction.json"
 assert any(x['path']==native_output for x in retired_receipt['predecessors'])
 atlas_features={f['id']:f for f in read_json(ROOT/'data/geography/part-29.json')['features']}
 hierarchy={x['id']:x for x in read_json(ROOT/'data/hierarchy.json')}
 native=read_json(PACKET/'sources/aafc-ecoregions.native.geojson')['features']
 v22=read_json(ROOT/'data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-terrestrial-ecoregions-v2.2.geojson')['features']
 provinces=read_json(ROOT/'data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-ecoprovinces-baseline-arcgis-layer0.geojson')['features']
 retired=read_json(PACKET/'retired-member-context-phase2.json')
 assert retired['location_count']==19050 and retired['archive_sha256']=='c072bbe6e7f96789e3a6165e9075eb3271050e1e1614f2923f03169480537184'
 retired_ids={
  'ECO15':['gb:CAN:ADM3:43193130B40321569586625','gb:CAN:ADM3:43193130B96648191896746'],
  'ECO25':['gb:CAN:ADM3:43193130B13052897136233','gb:CAN:ADM3:43193130B30076837012949','gb:CAN:ADM3:43193130B6772247703215']}
 old={x['id']:x for x in retired['locations']}
 assert len(old)==5
 geojson={'type':'FeatureCollection','features':[]}
 candidate_geometries={cid:shape(comps[cid]['geometry']) for cid,*_ in CANDIDATES}
 hits_by={cid:[] for cid,*_ in CANDIDATES}; neighbors_by={cid:[] for cid,*_ in CANDIDATES}
 target_ids={cid:target for cid,_eid,target,_admin,_parent in CANDIDATES}
 scan_paths=['neighbor-scan-a.json','neighbor-scan-b.json','neighbor-scan-c.json','neighbor-scan-d.json']
 idx=read_json(ROOT/'data/world-index.json')
 active_feature_count=0; active_part_count=0; scanned_paths=[]
 scanned_feature_ids=[]
 for scan_name in scan_paths:
  scan=read_json(PACKET/scan_name)
  scan_receipt=predecessor_execution(PACKET/scan_name)
  assert scan['version']==2
  assert scan_receipt['phase']=='neighbor-scan-'+scan['partition'].lower()
  plan=execution_plan()
  assert scan_receipt['baseline_commit']==plan['execution_commit']
  assert scan_receipt['plan_sha256']==execution_plan_sha256()
  scan_inputs={row['path']:row for row in scan_receipt['baseline_inputs']}
  expected_pins={row['path']:row for row in plan['baseline_files']}
  for path,row in scan_inputs.items():
   expected=expected_pins.get(path)
   assert expected and row['bytes']==expected['bytes'] and row['sha256']==expected['sha256']
  assert scan_inputs['data/world-index.json']['sha256']==sha(read_bytes(ROOT/'data/world-index.json'))
  assert scan_inputs['coordination/engineering/eastern-two-gap-repair-20261007/run-two/full-four-family-context.json.gz']['sha256']==sha(read_bytes(CONTEXT))
  active_feature_count+=scan['active_feature_count']; active_part_count+=scan['active_part_count']
  assert scan['candidate_ids']==sorted(candidate_geometries)
  assert len(scan['active_feature_ids'])==scan['active_feature_count']
  assert len(scan['active_feature_ids'])==len(set(scan['active_feature_ids']))
  assert all(isinstance(identity,str) and identity for identity in scan['active_feature_ids'])
  assert sum(row['feature_count'] for row in scan['roster'])==scan['active_feature_count']
  for part_row in scan['roster']:
   pinned=scan_inputs.get(part_row['path'])
   assert pinned and pinned['bytes']==part_row['bytes'] and pinned['sha256']==part_row['sha256']
  scanned_feature_ids.extend(scan['active_feature_ids'])
  scanned_paths.extend(row['path'].removeprefix('data/') for row in scan['roster'])
  for cid in candidate_geometries:
   hits_by[cid].extend(scan['hits_by_candidate'][cid])
   neighbors_by[cid].extend(scan['neighbors_by_candidate'][cid])
 assert active_feature_count==49625, active_feature_count
 assert active_part_count==36, active_part_count
 assert len(scanned_feature_ids)==49625 and len(set(scanned_feature_ids))==49625
 assert len(scanned_paths)==len(set(scanned_paths))==len(idx['parts']) and set(scanned_paths)==set(idx['parts'])
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
  hits=hits_by[cid]
  old_union=target.union(candidate)
  loss=target.difference(old_union); gain=old_union.difference(target)
  candidate_not_added=candidate.difference(gain)
  gain_candidate_difference=gain.symmetric_difference(candidate)
  candidate_target_overlap=candidate.intersection(target)
  neighbor_intersections=neighbors_by[cid]
  parent_id=2.3 if eid==15 else 2.7
  parent_hits=[]
  for f in provinces:
   if f['properties'].get('ECOPROVINCE_ID')==parent_id:
    pg=shape(f['geometry'])
    if pg.intersects(candidate): parent_hits.append({'objectid':f['properties'].get('OBJECTID'),'ecoprovince_id':f['properties'].get('ECOPROVINCE_ID'),'name':f['properties'].get('ECOPROVINCE_NAME_EN'),'covers':pg.covers(candidate),'intersection_area_deg2':pg.intersection(candidate).area})
  refs=[]
  for rid in retired_ids['ECO15' if eid==15 else 'ECO25']:
   ref=old[rid]; rg=shape(ref['geometry']); inter=rg.intersection(candidate)
   refs.append({'id':rid,'name':ref['name'],'parent_chain':ref['parent_chain'],'relation':'candidate-covered-by-reference' if rg.covers(candidate) else ('positive-area-overlap' if inter.area>0 else ('line-contact' if inter.length>0 else ('point-contact' if not inter.is_empty else 'disjoint'))),'intersection_area_deg2':inter.area,'intersection_length_degrees':inter.length,'intersection_geometry':mapping(inter) if not inter.is_empty else None})
  strict=loss.is_empty and gain.equals(candidate) and old_union.is_valid and len(neighbor_intersections)==0
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
  target_source_id_match=target_row['properties'].get('metadata',{}).get('source_id')==f'aafc:ecoregion:{eid}'
  parent_covering=[x for x in parent_hits if x['covers']]
  one_parent_envelope=len(parent_covering)==1 and round(float(parent_covering[0]['ecoprovince_id']),1)==parent_id
  retired_admin_match=all((old[x['id']]['parent_chain'][0].endswith(':NWT' if eid==15 else ':NUN')) for x in refs)
  criteria={
   'valid_candidate':candidate.is_valid,
   'exactly_one_named_source_envelope_in_both_editions':len(native_envelopes)==len(v22_envelopes)==1 and native_envelopes[0]['id']==eid and v22_envelopes[0]['id']==eid,
   'source_parent_identity_matches_both_editions':native_parent_match and v22_parent_match and one_parent_envelope and parent_covering[0]['name']==parent,
   'current_atlas_source_identity_matches_ecoregion':target_source_id_match,
   'current_hierarchy_parent_name_matches_source_parent':atlas_parent_match,
   'retired_source_members_match_target_and_expected_admin_parent':set(target_member_ids)==set(retired_ids_for_group) and retired_admin_match,
   'only_intended_active_target_intersects':len(hits)==1 and hits[0]['id']==target_id,
   'no_new_positive_area_active_neighbor_overlap':len(neighbor_intersections)==0,
   'valid_exact_no_loss_union':old_union.is_valid and loss.is_empty,
   'full_candidate_is_new_union_gain':gain.equals(candidate),
  }
  decision=disposition(criteria)
  if decision=='repair-ready-geometric-proposal': geojson['features'].append({'type':'Feature','id':cid,'properties':{'component_id':cid,'target_id':target_id,'status':'proposed-exact-no-loss-addition'},'geometry':mapping(old_union)})
  results.append({'component_id':cid,'source_ecoregion_id':eid,'atlas_target_id':target_id,'administrative_reference':admin,'source_parent':parent,
   'candidate_geometry':mapping(candidate),'candidate_area_deg2':candidate.area,'candidate_land_area_m2':land_area_m2(candidate),
   'native_source_name':next(f['properties']['ECOREGION_NAME_EN'] for f in native if f['properties'].get('ECOREGION_ID')==eid),
   'v22_source_name':next(f['properties']['ECOREGION_NAME_EN'] for f in v22 if f['properties'].get('ECOREGION_ID')==eid),
   'native_source_properties':native_record['properties'],'v22_source_properties':v22_record['properties'],
   'atlas_target_name':target_row['properties']['name'],'atlas_target_parent_id':target_row['properties']['parent_id'],
   'atlas_target_source_member_ids':target_member_ids,'retired_context_ids_match_target_source_members':set(target_member_ids)==set(retired_ids_for_group),
   'atlas_target_source_id_matches_ecoregion':target_source_id_match,'retired_context_admin_parent_matches_target_group':retired_admin_match,
   'ecoregion_parent_id_matches_source_parent_both_editions':native_parent_match and v22_parent_match,
   'atlas_hierarchy_parent_name_matches_source_parent_name':atlas_parent_match,
   'repair_ready_criteria':criteria,'missing_prerequisites':[k for k,v in criteria.items() if not v],
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
   'decision':decision})
 ready_count=sum(r['decision']=='repair-ready-geometric-proposal' for r in results)
 out={'method':'GEOS/Shapely topological predicates and union; square-degree values are planar residual diagnostics; candidate physical areas use the shared WGS84 source-edge helper.','geography_method_id':'exact-aafc-envelope-and-topology','active_feature_count':active_feature_count,'active_part_count':active_part_count,'component_count':len(results),'repair_ready_count':ready_count,'unresolved_count':len(results)-ready_count,'exactly_one_covering_named_envelope_count':sum(r['exactly_one_covering_named_envelope_both_editions'] for r in results),'native_feature_count':len(native),'native_unique_ecoregion_id_count':len({f['properties'].get('ECOREGION_ID') for f in native}),'retired_archive_sha256':retired['archive_sha256'],'retired_location_count':retired['location_count'],'retired_archive_decoded_bytes':retired['decoded_input_bytes'],'results':results,
      'limitations':['Geometric source fit does not establish historical cause, land/water status, boundary authority, or approval.','Native AAFC and v2.2 are distinct editions; coverage is reported separately.']}
 raw=(json.dumps(out,sort_keys=True,separators=(',',':'))+'\n').encode(); write_packet_output(PACKET/'candidate-decisions.json',raw)
 write_packet_output(PACKET/'proposed-additions.geojson',(json.dumps(geojson,sort_keys=True,separators=(',',':'))+'\n').encode())
 positive=next(r for r in results if r['component_id'].endswith('12c9ec9813490ce8602fb26ee2e54225b99c28bbd29794a7f8ac9ee60f109e8a'))
 pos={'method_id':'exact-aafc-envelope-and-topology','kind':'positive-control','scope':'full-candidate-fit-result','outcome':'passed' if disposition(positive['repair_ready_criteria'])=='repair-ready-geometric-proposal' and all(positive['repair_ready_criteria'].values()) else 'failed','component_id':positive['component_id'],'criteria':positive['repair_ready_criteria'],'decision':positive['decision']}
 flipped=[]
 for premise in positive['repair_ready_criteria']:
  altered=dict(positive['repair_ready_criteria']); altered[premise]=False
  flipped.append({'premise':premise,'criteria':altered,'decision':disposition(altered),'rejected':disposition(altered)=='unresolved-topology-or-neighbor-condition'})
 cross_group={r['component_id']:r['cross_group_adverse_control'] for r in results}
 neg={'method_id':'exact-aafc-envelope-and-topology','kind':'negative-control','scope':'decision-gate-unit-check-plus-cross-group-source-envelope-check','adverse_input_fixture':False,'interpretation':'Independent premise flips exercise only the disposition gate. Cross-group checks are actual geometric comparisons against the retained native and v2.2 source envelopes; this record is not a full pipeline adverse-input fixture.','outcome':'passed' if all(row['rejected'] for row in flipped) and all(not row['native_wrong_region_covers_candidate'] and not row['v22_wrong_region_covers_candidate'] for row in cross_group.values()) else 'failed','independent_premise_flips':flipped,'cross_group_covers':cross_group}
 write_packet_output(PACKET/'positive-control.json',(json.dumps(pos,sort_keys=True,separators=(',',':'))+'\n').encode())
 write_packet_output(PACKET/'negative-control.json',(json.dumps(neg,sort_keys=True,separators=(',',':'))+'\n').encode())
 print(json.dumps({'status':'reproduced','components':len(results),'active_features':active_feature_count,'decisions':[{'id':r['component_id'],'decision':r['decision']} for r in results],'sha256':sha(raw)},sort_keys=True))
if __name__=='__main__': main()
