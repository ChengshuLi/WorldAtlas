"""Prepare complete original bindings for existing pure SOURCE predicates only."""
import base64,hashlib,json,pathlib,subprocess,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[3];OWN=HERE.parent.relative_to(ROOT).as_posix();sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
head,vintage=sys.argv[1:]
if git('rev-parse','HEAD').decode().strip()!=head:raise ValueError('Exact HEAD required')
locators=json.loads(git('show',head+':'+OWN+'/physical-locators.json'));plan=json.loads(git('show',head+':'+OWN+'/physical-plan.json'));parts=sorted({locators[cid]['path'].split('-')[1].split('.')[0] for cid in plan['component_ids']});names=[OWN+'/tools/build_premise_input.py',OWN+'/physical-locators.json',OWN+'/physical-plan.json',OWN+'/vintages/candidate-custody-001/original-components.json',OWN+'/vintages/current-neighbors-001/result.json',OWN+'/vintages/administrative-custody-002/comparison-rows.json','scripts/evidence/immutable.py']+[OWN+'/vintages/physical-custody-'+p+'-002/'+f for p in parts for f in ['physical-records.json','queried-source-metadata.json']];pins=[]
for p in names:
 b=(ROOT/p).read_bytes()
 if b!=git('show',head+':'+p):raise ValueError('Unfrozen input')
 pins.append({'path':p,'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes'})
ns={'__name__':'aus_immutable','__file__':str(ROOT/'scripts/evidence/immutable.py')};exec(compile(git('show',head+':scripts/evidence/immutable.py'),ns['__file__'],'exec'),ns);base=ns['Baseline'](ROOT,head,pins,max_phase_bytes=32*1024**2);canon=ns['canonical_json'];dest=ns['NewVintage'](base,OWN+'/',vintage,['premise-input.json']);read=lambda p:json.loads(base.pinned_bytes(OWN+'/'+p));candidates=[c for c in read('vintages/candidate-custody-001/original-components.json') if c['id'] in plan['component_ids']];
if [c['id'] for c in candidates]!=plan['component_ids']:raise ValueError('Changed viable custody cohort')
current=read('vintages/current-neighbors-001/result.json');comparisons={r['component']:r for r in read('vintages/administrative-custody-002/comparison-rows.json')};physical={r['component_id']:r for p in parts for r in read('vintages/physical-custody-'+p+'-002/physical-records.json')};native={r['component_id']:r for p in parts for r in read('vintages/physical-custody-'+p+'-002/queried-source-metadata.json')};cases=[];pb=[];cb=[];tb={}
# Existing method15 authenticates original target bytes, rather than a JS
# reserialization. Reuse the genuine selected reader's whole source identities.
target_sources={};target_source_inputs=[]
for target_id in sorted({comparisons[c['id']]['uniquely_covering_compatible_recorded_subject']['id'] for c in candidates}):
 contexts=[n for row in current['rows'] for n in row['candidate_neighbors'] if n['feature']['id']==target_id]
 if not contexts or any(n!=contexts[0] for n in contexts):raise ValueError('Ambiguous actual target record')
 e=contexts[0]['certificate_entry'];path=e[4]
 if path not in target_sources:
  descriptors=[d for d in current['source_inputs'] if d['path']==path and d.get('whole_body_consumed')]
  if len(descriptors)!=1:raise ValueError('Missing whole actual target source')
  d=descriptors[0];line=git('ls-tree','-z',current['baseline'],'--',path).decode().rstrip('\0');fields,actual_path=line.split('\t');mode,kind,oid=fields.split()
  if (mode,kind,actual_path,oid)!=('100644','blob',path,d['git_blob_oid']):raise ValueError('Target whole source identity changed')
  base.admit('original-target-source:'+path,d['bytes']);raw=git('cat-file','blob',oid)
  if len(raw)!=d['bytes'] or sha(raw)!=d['sha256']:raise ValueError('Target whole bytes changed')
  fs=json.loads(raw)['features']
  if len({f['id'] for f in fs})!=len(fs):raise ValueError('Duplicate target source identity')
  target_sources[path]=fs;target_source_inputs.append({**d,'commit':current['baseline']})
 original=target_sources[path][e[5]]
 if original['id']!=target_id or original!=contexts[0]['feature']:raise ValueError('Original target is not actual selected complete value')
 tb[target_id]={'target_id':target_id,'feature_sha256':sha(canon(original)),'feature_bytes_base64':base64.b64encode(canon(original)).decode(),'geometry_sha256':sha(canon(original['geometry'])),'geometry_bytes_base64':base64.b64encode(canon(original['geometry'])).decode()}
for c in candidates:
 cid=c['id'];a=comparisons[cid];context=next(r for r in current['rows'] if r['component_id']==cid);target_id=a['uniquely_covering_compatible_recorded_subject']['id'];t=next(n['feature'] for n in context['candidate_neighbors'] if n['feature']['id']==target_id);positive=[r for r in a['feature_intersections'] if r['intersection']['planar_area_coordinate_units_squared']>0]
 if len(positive)!=1 or sha(canon(c))!=physical[cid]['candidate_feature_sha256']:raise ValueError('Original source/physical identity mismatch')
 payload={'component_id':cid,'candidate_feature_sha256':sha(canon(c)),'candidate_geometry_sha256':physical[cid]['candidate_geometry_sha256'],'target_stable_location_id':target_id,'unsupported_candidate_remainder_included':False,'source_supported_intersection_fragments':[{'intersection_geometry':positive[0]['intersection']['geometry']}],'target_current_feature':{'feature_sha256':tb[target_id]['feature_sha256'],'geometry_sha256':tb[target_id]['geometry_sha256'],'parent_id':t['properties']['parent_id']}}
 cases.append({'component_id':cid,'original_candidate_feature':c,'retained_payload':payload,'retained_source_operation_row':{'source_comparison_record':a,'positive_area_recorded_source_subject_ids':[target_id],'positive_area_source_feature_intersections':[r['binding'] for r in positive]}});pb.append({'component_id':cid,'physical_comparison':{'row':physical[cid]},'original_queried_source_metadata':[{'original_source_record_metadata':r} for r in native[cid]['sources']]});cb.append({'component_id':cid,'feature_sha256':sha(canon(c)),'feature_bytes_base64':base64.b64encode(canon(c)).decode(),'derived_js_canonical_sha256':context['derived_js_feature_sha256']})
scope={'scopeIds':[c['id'] for c in candidates],'candidate_source_native_bindings':cases,'original_physical_comparison_bindings':pb,'original_candidate_canonical_bindings':cb,'original_target_canonical_bindings':list(tb.values()),'current_neighbor_binding':current,'execution_commit':head,'original_target_source_inputs':target_source_inputs,'consumed_inputs':pins,'limits':['Pure SOURCE predicate diagnostic input only; no source handoff, acceptance, native qualification or release.']};dest.publish({'premise-input.json':scope});print('Prepared exact complete premise input for',len(candidates),'candidates')
