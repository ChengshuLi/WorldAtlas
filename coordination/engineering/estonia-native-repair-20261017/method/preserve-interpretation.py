"""Preserve distinct source roles, exact recorded name corrections and open interpretation.
Usage: python preserve-interpretation.py READ_ONLY_REPO FRESH_OUTPUT
"""
import collections,gzip,hashlib,io,json,os,pathlib,resource,subprocess,sys,time
W,O=map(lambda v:pathlib.Path(v).absolute(),sys.argv[1:]);H='3b3e9e675cfb37999d5665438f9fbf25bbd4238b';S='7571d0d79cedb6ceee8e494b504522596ecea94d';P='coordination/engineering/estonia-native-repair-20261017/'
assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents))
pins={};total=0;started=time.monotonic();sha=lambda b:hashlib.sha256(b).hexdigest();env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
def read(path,commit=H,expected=None):
 global total
 assert path and not path.startswith('/') and all(x not in ['', '.', '..'] for x in path.split('/'))
 cmd=['git','-c','protocol.allow=never','-C',str(W)];meta,name=subprocess.check_output(cmd+['ls-tree','-z',commit,'--',path],env=env).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and name.decode()==path
 size=int(subprocess.check_output(cmd+['cat-file','-s',oid],env=env));assert size>0
 b=subprocess.check_output(cmd+['cat-file','blob',oid],env=env);assert len(b)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 pin={'path':path,'commit':commit,'mode':mode,'git_blob_oid':oid,'bytes':size,'sha256':sha(b)}
 if expected:assert size==expected['bytes'] and sha(b)==expected['sha256']
 if path.endswith('.gz'):
  with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:d=f.read()
  pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
  if expected:assert len(b)==expected['decoded_bytes'] and sha(b)==expected['decoded_sha256']
 if (commit,path) not in pins:total+=size+pin.get('decoded_bytes',0)
 pins[(commit,path)]=pin;return b
js=lambda p,h=H:json.loads(read(p,h))

a=js(P+'source-stage/source-scope-assessment.json',S);targets={r['id']:r for r in a['target_checks']};decisions=js('data/geographic-decisions/europe.json');follow=js('data/geographic-semantic-followup/europe.json.gz');metadata=js('data/administrative-sources.json');hierarchy=js('data/hierarchy.json');code=read('scripts/apply-geographic-decisions.py').decode();assert "location_metadata_changes" in code
current={f['id']:f for f in js('data/geography/part-8.json')['features'] if f['id'] in targets};assert set(current)==set(targets)
roles=collections.Counter();role_cells=collections.Counter();corrections=[];role_changes=[]
for ident,t in targets.items():
 assert t['source_atoms']==[ident];f=current[ident];m=f['properties']['metadata'];assert m==t['metadata'] and t['raw_source_name']
 roles[m['source_role']]+=1;role_cells[m['source_role']]+=t['candidate_cells']
 if t['display_name_differs']:
  r=next(r for r in decisions['location_changes'] if r['id']==ident);assert r['current_name']==t['raw_source_name'] and r['new_name']==t['name'] and t['raw_source_name'].encode('latin1').decode('utf8')==t['name'];corrections.append(r)
 for r in decisions.get('location_metadata_changes',[]):
  if r['id']==ident:assert all(m[k]==v for k,v in r['changes'].items());role_changes.append(r)
review=[r for r in decisions['location_review'] if set(r['ids'])&set(targets)];follow_rows=[r for r in follow['locations'] if r['id'] in targets];assert {r['id'] for r in follow_rows}==set(targets)
for r in follow_rows:assert r['source_id']=='gb:EST:ADM2'
parent_ids={f['properties']['parent_id'] for f in current.values()};by={r['id']:r for r in hierarchy};chains={}
for ident,f in current.items():
 p=f['properties']['parent_id'];chain=[];seen=set()
 while p:
  assert p not in seen;seen.add(p);r=by[p];chain.append(r);p=r.get('parent_id')
 chains[ident]=chain
notices=[]
for p in ['research/geography/usa31-gap-family-source-fitness-20261007/sources/GSHHG-LICENSE.TXT','research/geography/usa31-gap-family-source-fitness-20261007/sources/GSHHG-README.TXT','coordination/engineering/global-physical-sources-20261006/COPYING.LESSERv3']:
 b=read(p)
 if p.endswith('LICENSE.TXT'):assert b'version 3 or later' in b
 if p.endswith('README.TXT'):assert b'v3 or any earlier version' in b
 notices.append({'path':p,'bytes':len(b),'sha256':sha(b)})
result={'version':1,'source_role_counts':dict(roles),'source_role_original_cells':dict(role_cells),'direct_source_members':sum(len(r['source_atoms']) for r in targets.values()),'recorded_encoding_corrections':corrections,'recorded_unit_role_corrections':role_changes,'current_location_decisions':review,'complete_selected_semantic_followup':follow_rows,'current_parent_chains':chains,'parent_decisions':[r for r in decisions['decisions'] if r['id'] in {p['id'] for c in chains.values() for p in c}],'recorded_product_metadata':{k:v for k,v in metadata.items() if k.startswith('gb:EST:')},'physical_licence_notices':notices,'physical_licence_status':'Retained data LICENSE says LGPL version 3 or later; retained README says v3 or any earlier version. Both complete original notices and LGPL text remain authenticated; wording conflict is unresolved.','inputs':list(pins.values()),'limits':['All 90 original targets are direct literal municipal source units. Pre-reform rural/urban roles and geographic parents remain explicit, without converting them to current municipal jurisdictions.','The source-stage context selector originally read the unrelated Oceania decision file and therefore retained no matching regional decision rows. This complete Europe decisions/followup read is the correction: all 90 actual target rows and entire parent chains are authenticated here; source geometries and scientific inputs are unchanged. The stage method is corrected for future use without relabeling the original execution.','All selected source-role, parent correspondence, urban fragmentation, source omission and local geographic-purpose questions remain open; same-ID geometry identity is not semantic approval.','Actual ADM2 count is 214 unique features; provider metadata advertises 215. Full catalogue bodies and identities are authenticated; no missing feature is invented or completeness inferred from the advertised count.','Recorded 2016/2017 represented dates, update/build dates and complete ODbL notices remain distinct. Official 2013/2014 merger evidence contradicts three specific named 2017 municipal targets; their exact original cells are separately held. Other dates alone impose no blanket refusal.','The complete historical and physical-source results remain source-relative evidence. No present sovereignty, historical affiliation, contemporary dry-land or whole source-fitness clearance follows.']}
body=(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n').encode();assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
with (O/'construction-and-source-limits.json').open('xb') as f:f.write(body)
with (O/'preparation.json').open('x') as f:json.dump({'complete':True,'bytes':len(body),'sha256':sha(body)},f);f.write('\n')
print(json.dumps({'source_roles':dict(roles),'role_cells':dict(role_cells),'name_corrections':len(corrections),'unit_role_corrections':len(role_changes),'semantic_followup':len(follow_rows),'processing_bytes':total}))
