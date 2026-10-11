"""Join the qualified Norway subset; preserve all thirty-one original outcomes."""
import base64,gzip,hashlib,io,json,pathlib,resource,subprocess,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[3];OWN=HERE.parent.relative_to(ROOT).as_posix();BASE='6a99a7606b9c2d11ac8cd093610653d4cd5d1382';sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
def main():
 head,vintage=sys.argv[1:]
 if git('rev-parse','HEAD').decode().strip()!=head:raise ValueError('Exact execution HEAD required')
 pins=[]
 for p in [OWN+'/tools/build_handoff.py',OWN+'/tools/handoff-inputs.json','scripts/evidence/immutable.py']:
  b=(ROOT/p).read_bytes()
  if b!=git('show',head+':'+p):raise ValueError('Unfrozen control')
  pins.append({'path':p,'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes'})
 ns={'__name__':'nor_immutable','__file__':str(ROOT/'scripts/evidence/immutable.py')};exec(compile(git('show',head+':scripts/evidence/immutable.py'),ns['__file__'],'exec'),ns);base=ns['Baseline'](ROOT,head,pins,max_phase_bytes=128*1024**2);canon=ns['canonical_json'];dest=ns['NewVintage'](base,OWN+'/',vintage,['source-handoff.json','all31-dispositions.json']);inputs={}
 def read(p,commit=head,pin=None,decode=False):
  line=git('ls-tree','-z',commit,'--',p).decode().rstrip('\0');fields,path=line.split('\t');mode,kind,oid=fields.split()
  if (mode,kind,path)!=('100644','blob',p):raise ValueError('Nonordinary immutable body')
  base.admit(commit+':'+p,int(git('cat-file','-s',oid)));b=git('cat-file','blob',oid);d={'commit':commit,'path':p,'mode':mode,'blob':oid,'bytes':len(b),'sha256':sha(b)}
  if pin and any(d[k]!=pin[k] for k in ['bytes','sha256']):raise ValueError('Whole bytes mismatch')
  inputs[commit+':'+p]=d
  if decode:
   size=pin['uncompressed_bytes'];base.admit('decoded:'+commit+':'+p,size)
   with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:b=f.read(size+1)
   if len(b)!=size or sha(b)!=pin['uncompressed_sha256']:raise ValueError('Whole decoded mismatch')
  return b
 own=lambda p:json.loads(read(OWN+'/'+p))
 config=own('tools/handoff-inputs.json');policy_raw=read(OWN+'/policy/literal-union-source-policy-v1.json');policy=json.loads(policy_raw);premise_rows=own('vintages/source-premises-001/result.json')['rows'];premises={r['component_id']:r for r in premise_rows}
 if sha(policy_raw)!=config['policy_sha256'] or policy['policy_id']!='retained-base-or-whole-original-component-20261011-v1':raise ValueError('Literal operation policy drift')
 roster=own('source-qualification/roster.json');wanted=roster['candidate_ids'];selected=config['component_ids'];locators=own('physical-locators.json');strict=own('vintages/nor31-strict-001/strict-predicates.json');current=own('vintages/nor31-current-neighbors-001/result.json');candidates=[r['feature'] for r in own('vintages/nor31-original-candidates-001/original-candidates.json')];comparisons=[r['comparison'] for r in own('vintages/nor31-original-classification-001/original-comparison-rows.json')];source_metadata=own('sources/administrative/custody.json');screen=own('vintages/nor31-delivered-physical-screen-001/delivered-physical-screen.json');screen_rows={r['row']['component_id']:r['row'] for r in screen['rows']}
 if not(len(wanted)==len(set(wanted))==31 and current['scopeIds']==wanted and strict['scope_ids']==wanted and [f['id'] for f in candidates]==wanted and [r['component'] for r in comparisons]==wanted):raise ValueError('Thirty-one-member scope mismatch')
 if current['baseline']!=BASE or strict['baseline_commit']!=BASE or len(set(selected))!=len(selected) or not set(selected).issubset(wanted):raise ValueError('Wrong selected epoch/scope')
 cm={f['id']:f for f in candidates};am={r['component']:r for r in comparisons};sm={r['component_id']:r for r in strict['results']};physical={};native={};restorations=[]
 report=json.loads(read('coordination/engineering/global-physical-comparison-20261006/results/report.json',BASE));pp={r['path']:r for r in report['products']};projections=[];retained_inverse_products=[]
 # Reuse genuine frozen per-product inverses, whose complete original encoded and
 # decoded identities were checked in their own completed resource-bounded phases.
 # Metadata assembly authenticates those publications and the exact selected rows;
 # the unchanged SOURCE reader later consumes every requested whole product itself.
 for part in sorted({locators[cid]['path'].split('-')[1].split('.')[0] for cid in selected}):
  pre='vintages/nor31-physical-part-'+part+'-001/'
  publication=own(pre+'publication.json');receipt=own(pre+'receipt.json');pr=own(pre+'physical-records.json');qr=own(pre+'queried-source-metadata.json')
  if publication.get('status')!='complete' or receipt['baseline']!=BASE:raise ValueError('Unqualified original inverse')
  published={p['path']:p for p in publication['outputs']}
  if len(published)!=len(publication['outputs']):raise ValueError('Duplicate inverse output')
  for f in ['receipt.json','physical-records.json','queried-source-metadata.json']:
   name=OWN+'/'+pre+f;actual=inputs[head+':'+name];declared=published[name]
   if any(actual[k]!=declared[k] for k in ['bytes','sha256']):raise ValueError('Inverse output identity mismatch')
  original=receipt['original_product'];name=original['path'];published_whole=published[OWN+'/'+pre+name]
  if original!=pp[name] or any(published_whole[k]!=original[k] for k in ['bytes','sha256']):raise ValueError('Original whole-product report mismatch')
  if not isinstance(receipt['restored_complete_rows'],int) or receipt['restored_complete_rows']<1:raise ValueError('Missing whole row count')
  if [r['component_id'] for r in pr]!=receipt['component_ids'] or [r['component_id'] for r in qr]!=receipt['component_ids']:raise ValueError('Inverse selected/query rows differ')
  for r in pr:
   if r['component_id'] in physical:raise ValueError('Duplicate physical identity')
   physical[r['component_id']]=r
  for r in qr:native[r['component_id']]=r
  restored={'path':name,'whole_original_bytes':original['bytes'],'whole_original_sha256':original['sha256'],'decoded_bytes':original['uncompressed_bytes'],'decoded_sha256':original['uncompressed_sha256'],'rows':receipt['restored_complete_rows']}
  projections.append(restored);restorations.append(receipt);retained_inverse_products.append({'receipt':inputs[head+':'+OWN+'/'+pre+'receipt.json'],'publication':inputs[head+':'+OWN+'/'+pre+'publication.json'],'whole_output':published_whole})
 if set(physical)!=set(selected) or set(native)!=set(selected):raise ValueError('Incomplete exact selected physical/query custody')
 sources=[r['reused_source_receipt'] for r in restorations]
 if not sources or any(s!=sources[0] for s in sources):raise ValueError('Ambiguous reused original source product')
 src=sources[0];expected=pp['sources-000.jsonl.gz']
 if {'path':src['path'],'bytes':src['whole_original_bytes'],'sha256':src['whole_original_sha256'],'hash_kind':'file-bytes','uncompressed_bytes':src['decoded_bytes'],'uncompressed_sha256':src['decoded_sha256']}!=expected:raise ValueError('Reused source product descriptor differs')
 projections.append(src)
 # Original dispatch membership is passive accounting, independently read from all seven products.
 pre='coordination/engineering/worldwide-native-batches-1184-20261006/current-run-one/';ip=pre+'report.json';index=json.loads(read(ip,BASE));out={p['path']:p for group in index['outputs'].values() for p in group};batches=json.loads(read(pre+'current-operational-batches-000.json.gz',BASE,out[pre+'current-operational-batches-000.json.gz'],True));bf={fid:b for b in batches for fid in b['fine_family_ids']}
 if len(batches)!=594 or len(bf)!=15610 or index['component_count']!=95173:raise ValueError('Wrong original programme')
 seen=set();members={};families={}
 for p in sorted(p for p in out if '/current-batches-' in p):
  rows=json.loads(read(p,BASE,out[p],True))
  for f in rows:
   for cid in f['component_ids']:
    if cid in seen:raise ValueError('Duplicate original component membership')
    seen.add(cid)
    if cid in wanted:
     members[cid]={'component_id':cid,'original_batch_id':bf[f['id']]['id'],'original_family_id':f['id']};families[f['id']]=f
 if len(seen)!=95173 or set(members)!=set(wanted):raise ValueError('Incomplete original mapping')
 source=read(OWN+'/sources/administrative/gb-NOR-ADM2-consumed-simplified.geojson');features=json.loads(source)['features']
 if sha(source)!=source_metadata['whole_original_sha256'] or len(source)!=source_metadata['whole_original_bytes'] or len(features)!=431:raise ValueError('Consumed complete administrative source differs')
 cases=[];pb=[];cb=[];tb={}
 for cid in selected:
  candidate=cm[cid];comparison=am[cid];context=next(r for r in current['rows'] if r['component_id']==cid);target_id=comparison['uniquely_covering_compatible_recorded_subject']['id'];target=next(r['feature'] for r in context['candidate_neighbors'] if r['feature']['id']==target_id)
  if not premises[cid]['source_compatible'] or set(sm[cid]['failed_predicates'])-{'candidate_current_target_no_positive_area_overlap','no_positive_area_any_current_neighbor'} or physical[cid]['status']!='mapped-land-support':raise ValueError('Unsupported selected case')
  if any(r.get('positive_area') for r in sm[cid]['current_neighbor_hits'] if r['id']!=target_id) or any(r.get('positive_area') and r['target_id']!=target_id for r in sm[cid]['current_addition_hits']):raise ValueError('Foreign owner overlap')
  if sha(canon(candidate))!=physical[cid]['candidate_feature_sha256'] or sha(canon(candidate))!=comparison['full_component_feature_sha256'] or sha(canon(target))!=sm[cid]['current_target_feature_sha256']:raise ValueError('Whole identity mismatch')
  positive=[r for r in comparison['feature_intersections'] if r['intersection']['planar_area_coordinate_units_squared']>0]
  if len(positive)!=1 or not positive[0]['source_feature_covers_entire_component']:raise ValueError('Original unique-source coverage differs')
  payload={'component_id':cid,'candidate_feature_sha256':sha(canon(candidate)),'candidate_geometry_sha256':physical[cid]['candidate_geometry_sha256'],'target_stable_location_id':target_id,'unsupported_candidate_remainder_included':False,'source_supported_intersection_fragments':[{'intersection_geometry':positive[0]['intersection']['geometry']}],'target_current_feature':{'feature_sha256':sha(canon(target)),'geometry_sha256':sha(canon(target['geometry'])),'parent_id':target['properties']['parent_id']}}
  cases.append({'component_id':cid,'original_candidate_feature':candidate,'retained_payload':payload,'retained_source_operation_row':{'source_comparison_record':comparison,'positive_area_recorded_source_subject_ids':[target_id],'positive_area_source_feature_intersections':[r['binding'] for r in positive]}})
  pb.append({'component_id':cid,'physical_comparison':{'row':physical[cid]},'original_queried_source_metadata':[{'original_source_record_metadata':r} for r in native[cid]['sources']]})
  cb.append({'component_id':cid,'feature_sha256':sha(canon(candidate)),'feature_bytes_base64':base64.b64encode(canon(candidate)).decode(),'derived_js_canonical_sha256':context['derived_js_feature_sha256']})
  tb[target_id]={'target_id':target_id,'feature_sha256':sha(canon(target)),'feature_bytes_base64':base64.b64encode(canon(target)).decode(),'geometry_sha256':sha(canon(target['geometry'])),'geometry_bytes_base64':base64.b64encode(canon(target['geometry'])).decode()}
 dispositions=[{'component_id':cid,'original_gap_membership':members[cid],'retained_detector_area_m2':cm[cid]['properties']['measured_fragment_area_sum_m2'],'physical_status':screen_rows[cid]['status'],'disposition':'proposed-source-relative-handoff' if cid in selected else 'held-original-source-premise-failure' if cid in premises else 'held-incomplete-whole-physical-inverse' if cid in locators else 'held-physical-mixed-or-unknown','strict_predicates':sm[cid],'resolved':False} for cid in wanted]
 scope={'execution_cohort_id':config['execution_cohort_id'],'scopeIds':selected,'original_gap_membership':{'version':1,'index':inputs[BASE+':'+ip],'members':[members[cid] for cid in selected]},'original_membership_evidence':{'programme_batches':594,'programme_components':95173,'qualification_scope':31,'all_qualification_members':[members[cid] for cid in wanted]},'candidate_source_native_bindings':cases,'original_physical_comparison_bindings':pb,'original_candidate_canonical_bindings':cb,'original_target_canonical_bindings':list(tb.values()),'consumed_source_bindings':[{'source_id':'gb:NOR:ADM2','whole_bytes':len(source),'whole_sha256':sha(source),'feature_count':431,'original_source_custody':source_metadata}],'current_neighbor_binding':current,'literal_union_source_policy':{'path':OWN+'/policy/literal-union-source-policy-v1.json','sha256':sha(policy_raw),'body':policy,'reviewed_interpretation_only':True,'accepted_ancestry_claim':False,'independent_review':'https://github.com/ChengshuLi/WorldAtlas/issues/1732#issuecomment-6110654265'},'incremental_continuous_area_m2':None,'physical_restoration':{'restorations':projections,'completed_inverse_receipts':restorations,'reused_whole_products':retained_inverse_products,'metadata_assembly_redecoded_whole_products':False},'retained_necessary_predicates':{'execution_commit':strict['execution_head'],'path':OWN+'/vintages/nor31-strict-001/strict-predicates.json','sha256':inputs[head+':'+OWN+'/vintages/nor31-strict-001/strict-predicates.json']['sha256'],'method':'One actual current-context execution of existing strict source/current predicates.'},'constructor_disposition':{'source_relative_premises_supported':True,'source_admission_requires_independent_review':True,'literal_representation':'Complete unchanged current target plus complete unchanged candidate primitives. No coordinate normalization.'},'unknowns':['Independent source and geometry review remains required.','Current physical or legal truth, source observation dates and processing cause remain unapproved.','Remaining twelve original candidates retain explicit physical, whole-inverse or SOURCE hash-domain blocks; all original strict and dissolve diagnostics remain unchanged.','SOURCE/NATIVE, current selected continuous conservation, package/reader/picker/renderer delivery and release readback remain engineering work.'],'execution_commit':head,'consumed_inputs':list(inputs.values())}
 summary={'scope_count':31,'proposed_count':len(selected),'proposed_ids':selected,'inherited_detector_area_m2':sum(cm[i]['properties']['measured_fragment_area_sum_m2'] for i in selected),'rows':dispositions,'scientific_or_publication_approval':False}
 if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>512*1024**2:raise ValueError('RSS exceeded')
 dest.publish({'source-handoff.json':scope,'all31-dispositions.json':summary});print(json.dumps({'proposed_count':len(selected),'logical_bytes':sum(base.consumed.values()),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}))
if __name__=='__main__':main()
