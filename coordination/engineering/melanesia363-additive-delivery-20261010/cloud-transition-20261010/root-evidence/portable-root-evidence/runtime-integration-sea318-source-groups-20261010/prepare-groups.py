from pathlib import Path
import json,hashlib,subprocess,gzip,collections,base64,copy
root=Path('.cache/runtime-integration-sea318-source-groups-20261010');old=Path('.cache/runtime-integration-sea318-current458-20261010');meta=Path('.cache/runtime-integration-sea318-source30-20261010');repo='.worldatlas-checkout';commit='0635e6d935f6953005e87a2b1290ddacbe55f337';current='c28077da970ae39550e5edea790a266b060d3de5'
def load(p):return json.load(open(p))
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n');return fp(p)
def fp(p):b=p.read_bytes();return {'path':str(p.resolve()),'bytes':len(b),'sha256':sha(b)}
def tree(c,p):
 line=subprocess.check_output(['git','-C',repo,'ls-tree','-z',c,'--',p]).decode().rstrip('\0');mode,kind,t=line.split(' ',2);blob,n=t.split('\t');assert kind=='blob' and n==p;return {'commit':c,'path':p,'mode':mode,'blob':blob}
def desc(x):
 p={k:v for k,v in x.items()if k in ['commit','path','mode','blob','bytes','sha256','uncompressed_bytes','uncompressed_sha256']};p['blob']=x.get('blob',x.get('git_blob_oid'));return p
fit=load(old/'administrative-source-rule-fit.json');original=load(meta/'SOURCE30-OPERAND-HANDOFF.json');joins=load(meta/'current-selected-target-owner-parent-joins.json');preimages={x['target_id']:x for x in load(meta/'current-selected-complete-target-preimages.json')};targets={x['target_id']:x for x in joins['targets']};groups=collections.defaultdict(list)
for row in fit['cases']:groups[row['source_product']['product_id']].append(row)
assert sum(map(len,groups.values()))==30 and len({x['component_id']for rows in groups.values()for x in rows})==30
assert not original['original363_component_id_overlap_ids'] and not original['overlap_ids']
querypins={x['path']:desc(x)for x in original['complete_original_query_pointsets']};querymetadata={x['source_id']:x for x in load(old/'BRN-original-query-metadata.json')};querycustody=[]
for q in querypins.values():
 id=int(q['path'].split('/')[-1].split('.')[0])
 if id in querymetadata:
  querycustody.append({'pin':q,'metadata_origin':fp(old/'BRN-original-query-metadata.json'),'reused_verified_original_metadata':True});continue
 raw=subprocess.check_output(['git','-C',repo,'cat-file','blob',q['blob']]);body=gzip.decompress(raw);assert len(raw)==q['bytes'] and sha(raw)==q['sha256'] and len(body)==q['uncompressed_bytes'] and sha(body)==q['uncompressed_sha256']
 source=json.loads(body)['source'];assert source['source_id']==id
 querymetadata[id]={k:v for k,v in source.items()if k not in ['polygon_geometry','complete_pointset_coordinates_when_no_polygon_object']}
 querycustody.append({'pin':q,'copied_native_metadata_sha256':sha(json.dumps(querymetadata[id]['native_metadata'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()),'encoded_decoded_whole_verified':True})
physicalpins={};physicalparsed={}
for row in fit['cases']:
 q=row['original_physical_query_custody'];pin=tree(commit,q['case_file']);raw=subprocess.check_output(['git','-C',repo,'cat-file','blob',pin['blob']]);body=gzip.decompress(raw);assert len(raw)==q['case_file_bytes'] and sha(raw)==q['case_file_sha256'] and sha(body)==q['case_file_uncompressed_sha256'];p=json.loads(body);assert p['case']['component_id']==row['component_id'] and p['case']['complete_current_component_candidate']['feature']==row['current_component_candidate']['feature']
 pin.update(bytes=len(raw),sha256=sha(raw),uncompressed_bytes=len(body),uncompressed_sha256=sha(body));physicalpins[row['component_id']]=pin;physicalparsed[row['component_id']]=len(body)
accepted=[]
for role,name in [('cases_path','administrative-source-rule-fit.json'),('outcomes_path','component-state-318.json'),('family_roster_path','family-roster-122.json')]:
 p='research/geography/southeast-asia-gap-batch-0393f64c-20261009/vintages/source-rule-fit-005/'+name;pin=tree(commit,p);pin.update(bytes=(old/name).stat().st_size,sha256=sha((old/name).read_bytes()));accepted.append((role,pin))
manifest=desc(joins['manifest']);assert tree(current,manifest['path'])['blob']==manifest['blob'];bounds=desc(joins['complete_owner_roster']);bounds.update(uncompressed_bytes=joins['complete_owner_roster']['decoded_bytes'],uncompressed_sha256=joins['complete_owner_roster']['decoded_sha256'])
base=load(old/'BRN-source-request-UNISSUED.json');oldgroup=load(Path('.cache/runtime-integration-source-grouping-20261010/group041-051-066-source-request-DRAFT.json'));oldgroupbytes=len(json.dumps(oldgroup,ensure_ascii=False,sort_keys=True,indent=2).encode()+b'\n');oldcaller=next(x['bytes']for x in oldgroup['executed_code']if x['path']=='scripts/additive-gap-repair.mjs');caller=next(x for x in base['executed_code']if x['path']=='scripts/additive-gap-repair.mjs');draftcodegrowth=max(0,caller['bytes']-oldcaller)
cohort=[x['component_id']for x in fit['cases']];index=[];pubfiles=[];routes=[]
for product,rows in groups.items():
 tag=product.replace(':','-');d=root/tag;d.mkdir(exist_ok=True);qids=[];targetids=[]
 for row in rows:
  target=row['original_administrative_comparison']['record']['uniquely_covering_compatible_recorded_subject']['id']
  if target not in targetids:targetids.append(target)
  for id in row['original_physical_query_custody']['complete_original_query_source_ids']:
   if id not in qids:qids.append(id)
 metadata=[querymetadata[id]for id in qids];bindings=[]
 for id in targetids:
  originalpre=preimages[id];binding={'target_id':id}
  for kind in ['feature','geometry']:
   b=originalpre['canonical_'+kind+'_utf8'].encode();binding[kind+'_sha256']=sha(b);binding[kind+'_bytes_base64']=base64.b64encode(b).decode()
  assert binding['feature_sha256']==targets[id]['recorded_subject']['original_feature_sha256'];bindings.append(binding)
 metadatafile=save(d/'original-query-metadata.json',metadata);bindingfile=save(d/'target-canonical-bindings.json',bindings);prefix='coordination/engineering/southeast-asia318-source-rule-delivery-20261010/groups/'+tag
 generated=[]
 for role,source,name in [('original_query_metadata_path',metadatafile,'original-query-metadata.json'),('target_canonical_bindings_path',bindingfile,'target-canonical-bindings.json')]:
  p={'commit':None,'path':prefix+'/'+name,'mode':'100644','blob':None,'bytes':source['bytes'],'sha256':source['sha256']};generated.append((role,p));pubfiles.append({'source':source,'destination':p['path'],'group':tag})
 inputs=[copy.deepcopy(p)for role,p in accepted]+[physicalpins[row['component_id']]for row in rows]
 for id in qids:
  q=next(x for x in querypins.values()if x['path'].endswith('/'+str(id)+'.json.gz'));inputs.append(q)
 productpin=desc(original['source_products'][product]);inputs.append(productpin);banks=[]
 for id in targetids:
  p=desc(targets[id]['source_containing_pin'])
  if not any(b['path']==p['path']for b in banks):
   assert tree(current,p['path'])['blob']==p['blob'];banks.append(p);inputs.append(p)
 inputs+=[manifest,bounds]+[p for role,p in generated];assert len({p['path']for p in inputs})==len(inputs)
 req=copy.deepcopy(base);req['destination']='sea318-source-'+tag+'-current353-UNISSUED';r={'version':1,'profile':'retained-consumed-administrative-source','geometry_scope':'full-component','expected_ids':[x['component_id']for x in rows],'cohort_ids':cohort,'administrative_products':[productpin],'manifest_path':manifest['path'],'bounds_path':bounds['path'],'target_banks':[b['path']for b in banks],'inputs':inputs}
 for role,p in accepted+generated:r[role]=p['path']
 req['source_rule']=r;pending=next(x for x in req['executed_code']if x['path']=='scripts/additive-gap-repair.mjs');pending['bytes']=None;pending['sha256']=None
 requestpin=save(d/'source-request-UNISSUED.json',req);save(d/'current-target-owner-parent-joins.json',[targets[id]for id in targetids])
 rawcost=sum(p['bytes']+p.get('uncompressed_bytes',0)for p in inputs);requestgrowth=2*(max(0,requestpin['bytes']-oldgroupbytes)+draftcodegrowth)
 parsedretained=bounds['uncompressed_bytes']+sum(p['bytes']for role,p in accepted)+sum(len(preimages[id]['canonical_feature_utf8'].encode())for id in targetids)+metadatafile['bytes']+bindingfile['bytes']
 parsescratch=max([productpin['uncompressed_bytes']]+[b['bytes']for b in banks]+[physicalparsed[x['component_id']]for x in rows]);parsedtotal=parsedretained+parsescratch
 direct=227594066+max(0,rawcost-44812729)+requestgrowth;selected=234493518+27128561+4194304+requestgrowth;floor=max(direct,selected)
 # Additional parsed graphs are stated separately, never hidden or claimed to
 # equal actual V8 heap/RSS. Only excess beyond existing8MiB metadata allowance
 # is prospectively charged here; conservative serialized graph size remains a
 # lower bound on implementation heap, not a promise of operating fit.
 explicitparsed=max(0,parsedtotal-8388608);complete=max(direct+explicitparsed,selected)
 cost={'whole_encoded_plus_decoded_input_bytes':rawcost,'input_descriptors':len(inputs),'full_retained_parsed_serialized_bytes':parsedretained,'maximum_one_complete_parse_scratch_bytes':parsescratch,'full_parsed_serialized_peak_bytes':parsedtotal,'existing_metadata_allowance_bytes':8388608,'additional_explicit_parsed_carry_bytes':explicitparsed,'stock_saved_direct_stage_prescription':direct,'stock_saved_selected_union_prescription':selected,'base_prescription_floor':floor,'conservative_explicit_parsed_floor':complete,'hard_union_limit':268435456,'classification':'OVERLIMIT_AT_CONSERVATIVE_FULL_PARSED_ACCOUNTING'if complete>268435456 else 'PROSPECTIVE_WITHIN_LIMIT_NOT_ISSUED_OR_HEAP_FIT','per_member_limit':33554432,'all_whole_encoded_decoded_members_within_limit':all(p['bytes']<=33554432 and p.get('uncompressed_bytes',0)<=33554432 for p in inputs),'output_reserve':4194304,'sample_stop':402653184,'lifetime_rss':536870912,'wall_seconds':1200,'new_storage_floor':16777216,'free_storage_floor':10737418240,'128_16_node_profile_unchanged':True,'final_combined_code_growth_pending':True,'limitations':['No operator/admission/heap/RSS fit claimed. Final combined caller bytes/hash and runtime must replace prospective draft basis.','Parsed serialization size is explicitly reported; actual JS graph allocation is not measured or invented. Do not launch overlimit groups or alter caps; sole-author existing issued admission controls decide any group.']};costpin=save(d/'prospective-accounting.json',cost)
 index.append({'group':tag,'product':product,'cases':len(rows),'expected_ids':r['expected_ids'],'target_ids':targetids,'query_ids':qids,'request':requestpin,'metadata':metadatafile,'target_bindings':bindingfile,'accounting':costpin,'floor':complete,'classification':cost['classification']});routes+=[{'component_id':x['component_id'],'group':tag,'original_ordinal':fit['cases'].index(x),'original_family':x['family_id'],'geometry_scope':'full-component','whole_gap_completion':False}for x in rows]
assert len(routes)==30 and len({x['component_id']for x in routes})==30
save(root/'query-metadata-whole-origin-custody.json',querycustody);save(root/'publication-filelist.json',pubfiles);save(root/'exact30-routing.json',routes);save(root/'groups-index.json',index)
print(json.dumps([{'group':x['group'],'cases':x['cases'],'floor':x['floor'],'classification':x['classification']}for x in index]))
