import json,pathlib,subprocess,os,hashlib,gzip
W=pathlib.Path(__file__).resolve().parents[1];HEAD='19858cf7aa887efad5d0c6ba0736d5672bf0aef5';BASE='defe4dea8d79963350f34bd09fe80d1825049ed5';P='coordination/engineering/greenland-repair-delivery-20261017/';consumed=[]
def read(commit,path):
 cmd=['git','-c','protocol.allow=never','-C',str(W)];env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'};row=subprocess.check_output(cmd+['ls-tree','-z',commit,'--',path],env=env);meta,name=row.rstrip(b'\0').split(b'\t');mode,typ,oid=meta.decode().split();assert mode=='100644' and typ=='blob';raw=subprocess.check_output(cmd+['cat-file','blob',oid],env=env);assert len(raw)<=33554432;d={'commit':commit,'path':path,'git_blob_oid':oid,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 if path.endswith('.gz'):raw=gzip.decompress(raw);assert len(raw)<=33554432;d.update(decoded_bytes=len(raw),decoded_sha256=hashlib.sha256(raw).hexdigest())
 consumed.append(d);return json.loads(raw)
e=read(HEAD,P+'native-inputs-001/source-evidence.json');idx=read(BASE,'data/world-index.json');owners=read(e['owner_roster']['commit'],e['owner_roster']['path']);expected_ids={o['id'] for o in owners};assert len(expected_ids)==len(owners);seen={};grl=[];parents=set()
for p in idx['parts']:
 d=read(BASE,'data/'+p)
 for f in d['features']:
  sid=f['id'];assert sid==f['properties']['id'] and sid not in seen;seen[sid]=p;m=f['properties']['metadata'];atoms=m.get('source_member_ids',[])
  if sid.startswith('gb:GRL:ADM1:') or any(x.startswith('gb:GRL:ADM1:') for x in atoms):grl.append({'id':sid,'source_members':atoms,'source_id':m.get('source_id'),'part':p,'parent':f['properties']['parent_id']});parents.add(f['properties']['parent_id'])
assert set(seen)==expected_ids
mem=read(HEAD,P+'source-review/complete-primary-membership.json');expected_grl={r['id'] for s in mem['splits'] for r in s['descendants']}|{t['id'] for t in e['targets']};assert {r['id'] for r in grl}==expected_grl and len(grl)==11
result={'head':HEAD,'baseline':BASE,'reviewer':os.environ['CODEX_THREAD_ID'],'world_index_parts':len(idx['parts']),'canonical_features':len(seen),'canonical_ids_exactly_equal_complete_owner_roster':True,'complete_Greenland_source_family_members':grl,'source_family_members':11,'source_family_parent_count':len(parents),'consumed':consumed,'unique_raw_plus_decoded_input_bytes':sum(d['bytes']+d.get('decoded_bytes',0) for d in consumed)};assert result['unique_raw_plus_decoded_input_bytes']<=268435456
(W/'.review-greenland/canonical-probe-result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',result['world_index_parts'],result['canonical_features'],result['source_family_members'],result['source_family_parent_count'],result['unique_raw_plus_decoded_input_bytes'])
