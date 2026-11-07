"""Combine authenticated resolver outputs without geographic cell patches.

This pure helper assumes caller reruns pinned source resolvers and checks their
inputs. Root IDs are valid only for the current component generation.
"""
def need(v,m):
 if not v:raise ValueError(m)
def combine(compiled,snapshot,reports,mainland_roots):
 need(isinstance(reports,list) and isinstance(mainland_roots,(set,frozenset)),'invalid mixed claims input')
 affiliations={a['affiliation_id']:a for a in snapshot['affiliations']};bindings={b['entity_id']:b['code'] for b in snapshot['category_bindings'] if b.get('physical_class')=='land'};selected=set(compiled['affiliation_ids']);seen=set();roots={}
 schemas={'source-point-component-report-v1':{'source_point_component_v1','source_point_named_region_component_v1','raw_json_city_named_region_component_v1','osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1','geonames_zip_island_named_region_component_v1','geonames_zip_named_list1_component_v1','geonames_zip_airport_named_region_component_v1'},'source-polygon-component-report-v1':{'component_intersection_v1','osm_relation_component_intersection_v1','component_containment_v1','component_containment_excluding_source_v1','osm_archipelago_component_intersection_v1','osm_archipelago_component_containment_v1','osm_archipelago_anchored_rings_intersection_v1','osm_way_component_containment_v1','osm_relation_component_containment_v1','osm_land_archive_component_intersection_v1','osm_land_archive_component_containment_v1'},'source-label-ecoregion-component-report-v1':{'label_contained_ecoregion_contact_v1'}}
 for report in reports:
  methods=schemas.get(report.get('schema'));need(methods and report.get('status')=='research-only-not-a-build' and report.get('revision')==compiled['revision'] and report.get('entity_revision')==compiled['entity_revision'] and isinstance(report.get('claims'),list),'invalid resolver report')
  for c in report['claims']:
   aid=c.get('affiliation_id');a=affiliations.get(aid);method=c.get('method');need(aid in selected and aid not in seen and isinstance(a,dict) and method in methods and method==a.get('method') and c.get('entity_id')==a.get('entity_id') and c.get('entity_code')==bindings.get(a['entity_id']),'claim/selection mismatch')
   ids=[c.get('component_id')] if method in {'source_point_component_v1','source_point_named_region_component_v1','raw_json_city_named_region_component_v1','osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1','geonames_zip_island_named_region_component_v1','geonames_zip_named_list1_component_v1','geonames_zip_airport_named_region_component_v1'} else c.get('component_ids')
   need(isinstance(ids,list) and ids and len(ids)<=1000000 and len(set(ids))==len(ids) and all(type(r) is int and 0<=r<0xffffffff and r not in mainland_roots for r in ids),'invalid or mainland component claim')
   for root in ids:
    claim={'affiliation_id':aid,'entry_ids':compiled['affiliation_entry_links'][aid],'code':c['entity_code']};existing=roots.setdefault(root,[]);need(all(old['code']==claim['code'] for old in existing),'conflicting component target');existing.append(claim)
   seen.add(aid)
 need(seen==selected,'selected affiliation not resolved');return roots

def protected_requirements(snapshot, compiled):
 """Read optional, affiliation-scoped protected baseline witness groups."""
 selected=set(compiled['affiliation_ids']);aff={a['affiliation_id']:a for a in snapshot['affiliations']};out={}
 for aid in selected:
  a=aff.get(aid);need(isinstance(a,dict),'missing protected affiliation');ev=a.get('evidence');need(isinstance(ev,dict),'invalid protected evidence')
  if 'protected_witness_group_ids' not in ev:continue
  ids=ev['protected_witness_group_ids'];need(a.get('method')=='component_intersection_v1' and a.get('scope')=='land' and type(a.get('entity_id')) is int,'unsupported protected affiliation')
  need(isinstance(ids,list) and 0<len(ids)<=100 and all(isinstance(x,str) and x for x in ids) and len(set(ids))==len(ids),'invalid protected witness groups');out[aid]=ids
 return out

def verify_protected(requirements,snapshot,baseline,stage2_report,request,witness_report,witness_sha,poly_resolution):
 """Fail if an affiliation touches a selected baseline sentinel; never persist root IDs.

 Caller authenticates both Neon exports, the monitored stage-2 report and the
 resolution report hash, and rehashes all these inputs after this check.
 """
 need(isinstance(requirements,dict),'invalid protected requirements')
 if not requirements:return []
 need(isinstance(witness_report,dict) and witness_report.get('schema')=='mainland-witness-resolution-v1' and witness_report.get('status')=='selected-research-identity-claims-not-mainland-proof','invalid protected witness report')
 need(isinstance(witness_sha,str) and len(witness_sha)==64 and stage2_report.get('resolution_report_sha256')==witness_sha,'protected resolution not bound to stage2')
 need(witness_report.get('snapshot_sha256')==request['baseline_snapshot_sha256'] and witness_report.get('decision_revision')==baseline['decision_revision']['id'] and witness_report.get('entity_revision')==baseline['entity_revision']['id'],'protected resolution revision mismatch')
 need(witness_report.get('component_manifest_sha256')==request['component_manifest_sha256'] and witness_report.get('input_sha256')==request['input_sha256'] and witness_report.get('grid')==request['grid'],'protected resolution physical or component mismatch')
 bg=baseline.get('mainland_witness_groups');wg=witness_report.get('groups');ww=witness_report.get('witnesses');need(isinstance(bg,list) and isinstance(wg,list) and isinstance(ww,list),'invalid witness groups')
 def unique(rows,key):
  d={}
  for row in rows:
   need(isinstance(row,dict) and isinstance(row.get(key),str) and row[key] not in d,'duplicate or malformed witness identity');d[row[key]]=row
  return d
 basegroups=unique(bg,'group_id');groups=unique(wg,'group_id');witnesses=unique(ww,'witness_id');basewitnesses=unique(baseline.get('mainland_witnesses',[]),'witness_id')
 affiliations={a['affiliation_id']:a for a in snapshot['affiliations']};claims=unique(poly_resolution.get('claims',[]),'affiliation_id');checks=[]
 for aid,ids in sorted(requirements.items()):
  a=affiliations.get(aid);claim=claims.get(aid);need(isinstance(a,dict) and isinstance(claim,dict) and claim.get('entity_id')==a.get('entity_id') and claim.get('method')==a.get('method')=='component_intersection_v1','protected claim target mismatch');roots=claim.get('component_ids');need(isinstance(roots,list) and roots and all(type(x) is int and 0<=x<0xffffffff for x in roots) and len(set(roots))==len(roots),'invalid protected claim roots')
  for gid in ids:
   g=basegroups.get(gid);r=groups.get(gid);need(isinstance(g,dict) and g.get('execution_status')=='selected_for_research' and g.get('role')=='sentinel' and g.get('decision_revision')==baseline['decision_revision']['id'] and g.get('target_entity_ids')==[] and isinstance(r,dict) and r.get('role')=='sentinel' and r.get('target_entity_ids')==[],'unknown or unsupported protected witness group')
   ws=g.get('witness_ids');need(isinstance(ws,list) and ws and len(set(ws))==len(ws) and all(isinstance(w,str) and w in witnesses and witnesses[w].get('group_id')==gid for w in ws),'protected witness members mismatch');need({w for w,z in witnesses.items() if z.get('group_id')==gid}==set(ws),'extra protected witness member');need(all(w in basewitnesses and basewitnesses[w].get('execution_status')=='selected_for_research' and basewitnesses[w].get('decision_revision')==baseline['decision_revision']['id'] and all(witnesses[w].get(k)==basewitnesses[w].get(k) for k in ('point_feature_id','identity_feature_id')) for w in ws),'protected witness source identity mismatch')
   root=r.get('component_id_current_generation_only');need(type(root) is int and 0<=root<0xffffffff,'invalid protected resolved root');need(root not in roots,'protected witness component hit by selected affiliation')
   checks.append({'affiliation_id':aid,'target_entity_id':a['entity_id'],'witness_group_id':gid,'status':'clear'})
 return checks
