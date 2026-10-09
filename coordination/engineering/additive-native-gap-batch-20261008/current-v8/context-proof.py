from pathlib import Path
import json,gzip,hashlib,subprocess,shutil
R=Path('/Users/chengshuli/world-atlas-workspace');O=Path(__file__).resolve().parent;W=R/'WorldAtlas';H='f2b129423c04d32b4b47ea36abae198651c50dae';B=R/'.cache/1295-normal-consumer-materialization-20261008/image-df881';base=B/'data/canonical-grid/eastern-v8';sha=lambda b:hashlib.sha256(b).hexdigest();can=lambda v:(json.dumps(v,sort_keys=True,separators=(',',':'))+'\n').encode()
receipt=json.loads((O/'receipt.json').read_bytes());assert receipt['immutable_commit']==H
mapraw=(B/'.cache/1295-canonical-j1UONR/canonical-objects/canonical-path-map.json').read_bytes();assert sha(mapraw)==receipt['canonical_path_map_sha256'];mapping=json.loads(mapraw);bindings={q['target']:q for q in mapping['logical_targets']}
def git(p):return subprocess.check_output(['git','-C',str(W),'show',H+':'+p])
def checked(pin):
 raw=(B/pin['path']).read_bytes();bind=bindings[pin['path']];assert len(raw)==pin['bytes']==bind['bytes'] and sha(raw)==pin['sha256']==bind['sha256'];return raw,bind
stage_raw=git('data/native-context-migration/manifest.json');stage=json.loads(stage_raw);ir,ib=checked(stage['after_context']);index=json.loads(ir);tr,tb=checked(stage['after_context_image']);transport=json.loads(tr);assert index['locations']==49625 and index['owner_sha256']=='90facdfa2c74a935e7e64fe2b2467de3b09f3b816eb96ba350f4f5bacb2227c2'
(O/'context-index.json').write_bytes(ir);(O/'context-transport-index.json').write_bytes(tr)
manifest=json.loads((base/'manifest.json').read_bytes());pointer=manifest['original_assets']['bounds'];boundsraw=subprocess.check_output(['git','-C',str(W),'show',pointer['commit']+':'+pointer['path']]);assert sha(boundsraw)==pointer['sha256']==manifest['bounds']['sha256'];boundsdec=gzip.decompress(boundsraw);bounds=json.loads(boundsdec);assert len(bounds)==len({v['index']for v in bounds})==len({v['id']for v in bounds})==49625;byowner={v['index']:v for v in bounds};(O/'bounds.json.gz').write_bytes(boundsraw)
windows=receipt['windows'];owners={v['owner_index']:v['target_id']for v in windows};assert len(owners)==7
for v in windows:assert byowner[v['owner_index']]['id']==v['target_id'] and byowner[v['owner_index']]['province_id']==v['parent_id']
chosen=[d for d in index['parts']if any(d['first_owner']<=i<d['first_owner']+d['owners']for i in owners)];assert len(chosen)==3
whole=[];decoded_parts={}
for d in chosen:
 f=next(v for v in transport['files']if v['path']==d['path']);assert f['bytes']==d['bytes'] and f['sha256']==d['sha256'] and f['mode']=='100644' and f['original_binding']['original_product']==d
 relevant=[v for v in transport['parts']if v['offset']<f['offset']+f['bytes'] and v['offset']+v['decoded_bytes']>f['offset']];chunks=[]
 for v in relevant:
  if v['path']not in decoded_parts:
   pin={'path':str(Path(stage['after_context_image']['path']).parent/v['path']),'bytes':v['bytes'],'sha256':v['sha256']};raw,bind=checked(pin);assert len(raw)<=33554432;dec=gzip.decompress(raw);assert len(dec)==v['decoded_bytes']<=33554432 and sha(dec)==v['decoded_sha256'];decoded_parts[v['path']]=dec;(O/v['path']).write_bytes(raw);whole.append({'descriptor':v,'canonical_binding':bind,'whole_encoded_decoded_verified':True})
  start=max(f['offset'],v['offset']);end=min(f['offset']+f['bytes'],v['offset']+v['decoded_bytes']);chunks.append(decoded_parts[v['path']][start-v['offset']:end-v['offset']])
 raw=b''.join(chunks);assert len(raw)==d['bytes'] and sha(raw)==d['sha256'];dec=gzip.decompress(raw);assert len(dec)==d['decoded_bytes'] and sha(dec)==d['decoded_sha256'];rows=json.loads(dec);assert len(rows)==d['owners'];target=O/d['path'];target.parent.mkdir(exist_ok=True);target.write_bytes(raw)
 for i in owners:
  if d['first_owner']<=i<d['first_owner']+d['owners']:
   record=rows[i-d['first_owner']];assert record['id']==owners[i];(O/('owner-'+str(i)+'.json')).write_bytes(can(record))
proof={'kind':'current-selected-v8-complete-context-and-owner-binding','immutable_commit':H,'selected_manifest_sha256':receipt['selected_manifest_sha256'],'selected_release':receipt['selected_release'],'context_index_pin':stage['after_context'],'context_transport_index_pin':stage['after_context_image'],'context_index_canonical_binding':ib,'context_transport_index_canonical_binding':tb,'original_stage_sha256':sha(stage_raw),'complete_bounds':{'original_pointer':pointer,'encoded_bytes':len(boundsraw),'encoded_sha256':sha(boundsraw),'decoded_bytes':len(boundsdec),'decoded_sha256':sha(boundsdec),'owners':49625},'seven_target_bindings':[byowner[i]for i in sorted(owners)],'complete_containing_contexts':chosen,'whole_transport_containers':whole,'actual_records':[{'owner_index':i,'target_id':owners[i],'path':'owner-'+str(i)+'.json','bytes':(O/('owner-'+str(i)+'.json')).stat().st_size,'sha256':sha((O/('owner-'+str(i)+'.json')).read_bytes())}for i in sorted(owners)],'limits':['Current selected v8 test baseline; successor N2 refresh remains required.','Whole original encoded containing bodies and complete seven records, not raw Git geometry; no source approval, GIS or native assignments.']}
(O/'context-owner-proof.json').write_bytes(can(proof));print(json.dumps({'targets':7,'complete_context_parts':len(chosen),'whole_transport_containers':len(whole),'native_assignment':False}))
