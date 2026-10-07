"""Reconcile deterministic exact overlay results into the 28-candidate/9-family table."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
scope=json.loads((ROOT/'inputs/immutable-scope-and-inputs.json').read_bytes())
rows=json.loads((ROOT/'results/source-overlays.json').read_bytes())
physical=json.loads((ROOT/'inputs/existing-physical-row-scope.json').read_bytes())
byphysical={x['component_id']:x['row'] for x in physical['selected_whole_rows']}
route={x['component']:x for x in scope['routing_rows']}
family={x['id']:x for x in scope['families_full_records']}
component_features={x['id']:x for x in scope['full_candidate_features']}
fragment_features={x['id']:x for x in scope['full_original_fragment_features']}
contact_features={x['id']:x for x in scope['full_current_contact_features']}
if set(route)!=set(scope['components']) or set(byphysical)!=set(scope['components']) or len(rows['targets'])!=49:raise ValueError('input/output complete target closure differs')
source_products=('geoboundaries-full','geoboundaries-atlas-simplified')
source_index={p:{'component':{},'contact':{}} for p in source_products}
mlit_index={'component':{},'contact':{}}
for x in rows['pairwise_exact_overlays']:
 t=x['target_kind'];tid=x['target_id'];p=x['source_product']
 target={'source_id':x['source_id'],'source_record':x['source_record'],'predicate_status':x['predicate_status'],'intersects':x.get('intersects'),'source_covers_target':x.get('source_covers_target'),'target_covers_source':x.get('target_covers_source'),'equal':x.get('equal'),'intersection_area_degrees2':x.get('intersection_area_degrees2'),'intersection_geometry_sha256':x.get('intersection_geometry_sha256'),'source_geometry_sha256':x['source_geometry_sha256']}
 if p in source_index:source_index[p][t].setdefault(tid,[]).append(target)
 elif p=='mlit-n03-2017':mlit_index[t].setdefault(tid,[]).append(target)
 else:raise ValueError('unexpected source product')
for p in source_index:
 for t in source_index[p]:
  for tid in source_index[p][t]:source_index[p][t][tid].sort(key=lambda x:x['source_id'])
for t in mlit_index:
 for tid in mlit_index[t]:mlit_index[t][tid].sort(key=lambda x:(str(x['source_id']),x['source_record'].get('record_ordinal',-1)))
# Source-specific comparisons preserve absence meaning: no row is emitted only
# when the complete source feature's envelope is disjoint from the target.
component_rows=[]
for cid in sorted(scope['components']):
 r=route[cid];f=component_features[cid];fam=family[r['family']];prior=byphysical[cid]
 targets={p:source_index[p]['component'].get(cid,[]) for p in source_products}
 full_by={x['source_id']:x for x in targets[source_products[0]]}
 simpl_by={x['source_id']:x for x in targets[source_products[1]]}
 union=sorted(set(full_by)|set(simpl_by))
 changed=[]
 for sid in union:
  a=full_by.get(sid);b=simpl_by.get(sid)
  ai=a.get('intersects') if a else False;bi=b.get('intersects') if b else False
  ac=a.get('source_covers_target') if a else False;bc=b.get('source_covers_target') if b else False
  if ai!=bi or ac!=bc:changed.append({'shapeID':sid,'full_intersects':ai,'simplified_intersects':bi,'full_covers':ac,'simplified_covers':bc})
 nrows=mlit_index['component'].get(cid,[])
 selected=[x for x in nrows if x['predicate_status']=='exact-predicates' and x.get('intersects') is True]
 unresolved=[x for x in nrows if x['predicate_status']!='exact-predicates']
 bindings=[]
 for binding in f['properties'].get('fragment_bindings',[]):
  frag=fragment_features[binding['id']]
  bindings.append({'fragment_id':binding['id'],'whole_feature_sha256':sha(canon(frag)),'whole_geometry_sha256':sha(canon(frag['geometry'])),'feature_sha256_expected':binding['feature_sha256']})
 next_action={
  'land-plus-compatible-original-processing-reproduction-candidate':'Keep unknown/unapproved; test only the exact existing Atlas simplified source lineage against the candidate and affected neighbors before proposing any processing reproduction.',
  'land-with-admin-partial-or-unbound-source-fitness-review':'Keep unknown/unapproved; bind the missing/partial original administrative-source identity and its complete candidate-scale geometry before any processing comparison.',
  'mixed-support-retain-whole-source-fitness-review':'Keep mixed support unresolved; obtain candidate-scale coastline/hydrography evidence and compare the complete source before any land/water interpretation.',
  'outside-source-domain-unclassified':'Retain outside-L1 context as unclassified; do not fill from a replacement or neighboring unit.'}[r['next_prerequisite']]
 component_rows.append({'component_id':cid,'family_id':r['family'],'complete_family_component_count':fam['component_count'],'family_numeric_first_member_count':fam['numeric_closure_component_count'],'routing_category':r['next_prerequisite'],'all_28_in_scope':True,'current_whole_feature_sha256':r['current_feature_sha256'],'current_whole_geometry_sha256':r['current_geometry_sha256'],'original_detector_fragment_bindings':bindings,'unmeasured_fragment_ids':r['unmeasured_fragment_ids'],'current_administrative_assignment':f['properties'].get('administrative_assignment'),'current_water_status_observation':f['properties'].get('water_status'),'prior_routed_physical_status':r['physical_status'],'prior_physical_authority':r['physical_authority'],'reused_GSHHG_complete_result':{'status':prior['status'],'physical_status':prior['physical_status'],'physical_authority':prior['physical_authority'],'source_vintage':prior['source_vintage'],'mapped_land_support':prior['complete_support']['mapped_land_support']['area_m2'],'mapped_inland_water_support':prior['complete_support']['mapped_inland_water_support']['area_m2'],'outside_mapped_L1_context':prior['complete_support']['outside_mapped_L1_context']['area_m2'],'unresolved':prior['unresolved'],'limits':prior['physical_limits']},'geoboundaries_full_bbox_candidates':len(targets[source_products[0]]),'geoboundaries_full_exact_intersections':sum(x.get('intersects') is True for x in targets[source_products[0]]),'geoboundaries_simplified_bbox_candidates':len(targets[source_products[1]]),'geoboundaries_simplified_exact_intersections':sum(x.get('intersects') is True for x in targets[source_products[1]]),'full_vs_simplified_predicate_or_cover_changes':changed,'full_intersection_sourceIDs':[x['source_id'] for x in targets[source_products[0]] if x.get('intersects') is True],'simplified_intersection_sourceIDs':[x['source_id'] for x in targets[source_products[1]] if x.get('intersects') is True],'MLIT_bbox_candidate_records':len(nrows),'MLIT_exact_intersection_records':[{'record_ordinal':x['source_record']['record_ordinal'],'record_number':x['source_record']['record_number'],'N03_007':x['source_id'],'N03_001':x['source_record']['N03_001'],'N03_002':x['source_record']['N03_002'],'N03_003':x['source_record']['N03_003'],'N03_004':x['source_record']['N03_004'],'intersection_area_jgd2011_degrees2':x.get('intersection_area_jgd2011_degrees2'),'intersection_geometry_sha256':x.get('intersection_geometry_sha256')} for x in selected],'MLIT_unresolved_records':len(unresolved),'recommended_next_action':next_action,'physical_truth_cause_and_authority':'unknown/unapproved'})
family_rows=[]
for fid in sorted(scope['families']):
 record=family[fid]; members=sorted(record['complete_component_ids']);bycat={}
 for cid in members:bycat[route[cid]['next_prerequisite']]=bycat.get(route[cid]['next_prerequisite'],0)+1
 if sum(bycat.values())!=record['component_count'] or record['numeric_closure_component_count']!=0:raise ValueError('family complete roster/count reconciliation differs')
 family_rows.append({'family_id':fid,'complete_component_ids':members,'complete_component_count':record['component_count'],'numeric_first_member_count':record['numeric_closure_component_count'],'component_disposition_counts':bycat,'source_fitness':'unapproved-for-all-components','dispatch_ready':record['dispatch_ready'],'unresolved_components':[cid for cid in members if route[cid]['physical_authority']!='unapproved' or route[cid]['physical_status']!='mapped-land-support'],'reconciliation':'All complete family members retained; no numeric-first rows added; no family repair or geographic approval.'})
contact_rows=[]
for cid in sorted(scope['contacts']):
 b={p:next(x for x in rows['contact_shapeID_bindings'] if x['source_product']==p and x['target_id']==cid) for p in source_products}
 n=mlit_index['contact'].get(cid,[])
 contact_rows.append({'contact_id':cid,'current_whole_geometry_sha256':sha(canon(contact_features[cid]['geometry'])),'source_shapeID':cid.rsplit(':',1)[-1],'full_product_exact_identity_binding':{k:b[source_products[0]].get(k) for k in ('source_geometry_sha256','intersects','source_covers_target','equal','intersection_area_degrees2')},'atlas_simplified_exact_identity_binding':{k:b[source_products[1]].get(k) for k in ('source_geometry_sha256','intersects','source_covers_target','equal','intersection_area_degrees2')},'full_vs_simplified_sameID_geometry_equal':b[source_products[0]].get('source_geometry_sha256')==b[source_products[1]].get('source_geometry_sha256'),'geoboundaries_full_spatial_intersections':len(source_index[source_products[0]]['contact'].get(cid,[])),'geoboundaries_simplified_spatial_intersections':len(source_index[source_products[1]]['contact'].get(cid,[])),'MLIT_bbox_candidate_records':len(n),'MLIT_exact_intersections':sum(x['predicate_status']=='exact-predicates' and x.get('intersects') is True for x in n),'physical_authority':'unapproved'})
expected={'land-plus-compatible-original-processing-reproduction-candidate':11,'land-with-admin-partial-or-unbound-source-fitness-review':10,'mixed-support-retain-whole-source-fitness-review':3,'outside-source-domain-unclassified':4}
counts={}
for x in component_rows:counts[x['routing_category']]=counts.get(x['routing_category'],0)+1
if counts!=expected or len(family_rows)!=9 or len(contact_rows)!=21 or len(component_rows)!=28:raise ValueError('global source-fitness table closure/dispositions differ')
out={'schema':'japan-nine-gap-family-source-fitness-table-v1','comparison_performed':False,'source_overlay_output_sha256':sha((ROOT/'results/source-overlays.json').read_bytes()),'scope_sha256':sha((ROOT/'inputs/immutable-scope-and-inputs.json').read_bytes()),'component_disposition_counts':counts,'component_rows':component_rows,'family_rows':family_rows,'contact_rows':contact_rows,'recommendation':'No source-supported repair, land/water classification, cause, ownership or geography approval is established. Preserve all original category counts and unknowns. Further source/geometry review remains required.'}
(ROOT/'results/source-fitness-table.json').write_bytes(canon(out))
print(json.dumps({'components':len(component_rows),'families':len(family_rows),'contacts':len(contact_rows),'dispositions':counts,'output_bytes':(ROOT/'results/source-fitness-table.json').stat().st_size,'sha256':sha((ROOT/'results/source-fitness-table.json').read_bytes())},ensure_ascii=False))
