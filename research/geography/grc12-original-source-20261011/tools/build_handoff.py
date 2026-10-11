"""Join the qualified Greek subset; preserve all twelve original outcomes."""
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
 ns={'__name__':'grc_immutable','__file__':str(ROOT/'scripts/evidence/immutable.py')};exec(compile(git('show',head+':scripts/evidence/immutable.py'),ns['__file__'],'exec'),ns);base=ns['Baseline'](ROOT,head,pins,max_phase_bytes=256*1024**2);canon=ns['canonical_json'];dest=ns['NewVintage'](base,OWN+'/',vintage,['source-handoff.json','all12-dispositions.json']);inputs={}
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
 roster=own('roster.json');wanted=[r['component_id'] for r in roster['members']];selected=config['component_ids'];locators=own('physical-locators.json');strict=own('vintages/strict-predicates-001/strict-predicates.json');current=own('vintages/current-neighbors-001/result.json');candidates=own('vintages/candidate-custody-001/original-components.json');comparisons=own('vintages/administrative-custody-001/comparison-rows.json');source_metadata=own('vintages/administrative-custody-001/source-metadata.json')
 if not(len(wanted)==len(set(wanted))==12 and current['scopeIds']==wanted and strict['scope_ids']==wanted and [f['id'] for f in candidates]==wanted and [r['component'] for r in comparisons]==wanted):raise ValueError('Twelve-member scope mismatch')
 if current['baseline']!=BASE or strict['baseline_commit']!=BASE or len(set(selected))!=len(selected) or not set(selected).issubset(wanted):raise ValueError('Wrong selected epoch/scope')
 cm={f['id']:f for f in candidates};am={r['component']:r for r in comparisons};sm={r['component_id']:r for r in strict['results']};physical={};native={};restorations=[]
 for part in sorted({locators[cid]['path'].split('-')[1].split('.')[0] for cid in wanted}):
  pre='vintages/physical-custody-'+part+'-001/'
  for r in own(pre+'physical-records.json'):
   if r['component_id'] in physical:raise ValueError('Duplicate physical identity')
   physical[r['component_id']]=r
  for r in own(pre+'queried-source-metadata.json'):native[r['component_id']]=r
  restorations.append(own(pre+'receipt.json'))
 if set(physical)!=set(wanted) or set(native)!=set(wanted):raise ValueError('Incomplete exact physical/query custody')
 report=json.loads(read('coordination/engineering/global-physical-comparison-20261006/results/report.json',BASE));pp={r['path']:r for r in report['products']}
 for name in sorted({locators[cid]['path'] for cid in selected}):
  part=name.split('-')[1].split('.')[0];raw=read(OWN+'/vintages/physical-custody-'+part+'-001/'+name,pin=pp[name],decode=True);rows=[json.loads(l) for l in raw.splitlines()];ids=[r['component_id'] for r in rows]
  if len(ids)!=len(set(ids)):raise ValueError('Duplicate whole physical record')
  for cid in selected:
   if locators[cid]['path']==name and [r for r in rows if r['component_id']==cid]!=[physical[cid]]:raise ValueError('Original selected row differs')
 sourcepath='research/geography/ukraine-original-singleton-source-fit-20261010/vintages/physical-restoration-001/sources-000.jsonl.gz';sr=[json.loads(l) for l in read(sourcepath,BASE,pp['sources-000.jsonl.gz'],True).splitlines()];sb={r['id']:r for r in sr}
 if len(sb)!=len(sr):raise ValueError('Duplicate native source identity')
 for cid in selected:
  if any(sb[s['id']]!=s for s in native[cid]['sources']):raise ValueError('Full original queried metadata differs')
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
 source=read(OWN+'/vintages/administrative-custody-001/consumed-source.geojson');meta=source_metadata['registry_record'];catalogue=source_metadata['catalogue_record'];features=json.loads(source)['features']
 if sha(source)!=meta['sha256'] or sha(source)!=catalogue['original_sha256'] or len(features)!=326:raise ValueError('Consumed complete administrative source differs')
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
 dispositions=[{'component_id':cid,'original_gap_membership':members[cid],'retained_detector_area_m2':cm[cid]['properties']['measured_fragment_area_sum_m2'],'physical_status':physical[cid]['status'],'disposition':'proposed-source-relative-handoff' if cid in selected else 'held-original-source-premise-failure','strict_predicates':sm[cid],'resolved':False} for cid in wanted]
 scope={'execution_cohort_id':config['execution_cohort_id'],'scopeIds':selected,'original_gap_membership':{'version':1,'index':inputs[BASE+':'+ip],'members':[members[cid] for cid in selected]},'original_membership_evidence':{'programme_batches':594,'programme_components':95173,'qualification_scope':12,'all_qualification_members':[members[cid] for cid in wanted]},'candidate_source_native_bindings':cases,'original_physical_comparison_bindings':pb,'original_candidate_canonical_bindings':cb,'original_target_canonical_bindings':list(tb.values()),'consumed_source_bindings':[{'source_id':'gb:GRC:ADM3','whole_bytes':len(source),'whole_sha256':sha(source),'feature_count':326,'catalogue_record':catalogue,'registry_record':meta}],'current_neighbor_binding':current,'literal_union_source_policy':{'path':OWN+'/policy/literal-union-source-policy-v1.json','sha256':sha(policy_raw),'body':policy,'reviewed_interpretation_only':True,'accepted_ancestry_claim':False},'incremental_continuous_area_m2':None,'physical_restoration':restorations,'retained_necessary_predicates':{'execution_commit':strict['execution_head'],'path':OWN+'/vintages/strict-predicates-001/strict-predicates.json','sha256':inputs[head+':'+OWN+'/vintages/strict-predicates-001/strict-predicates.json']['sha256'],'method':'One actual current-context execution of existing strict source/current predicates.'},'constructor_disposition':{'source_relative_premises_supported':True,'source_admission_requires_independent_review':True,'literal_representation':'Complete unchanged current target plus complete unchanged candidate primitives. No coordinate normalization.'},'unknowns':['Independent source and geometry review remains required.','Current physical or legal truth, source observation dates and processing cause remain unapproved.','Remaining two original candidates retain explicit failed SOURCE outcomes; all original strict and dissolve diagnostics remain unchanged.','SOURCE/NATIVE, current selected continuous conservation, package/reader/picker/renderer delivery and release readback remain engineering work.'],'execution_commit':head,'consumed_inputs':list(inputs.values())}
 summary={'scope_count':12,'proposed_count':len(selected),'proposed_ids':selected,'inherited_detector_area_m2':sum(cm[i]['properties']['measured_fragment_area_sum_m2'] for i in selected),'rows':dispositions,'scientific_or_publication_approval':False}
 if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>512*1024**2:raise ValueError('RSS exceeded')
 dest.publish({'source-handoff.json':scope,'all12-dispositions.json':summary});print(json.dumps({'proposed_count':len(selected),'logical_bytes':sum(base.consumed.values()),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}))
if __name__=='__main__':main()
