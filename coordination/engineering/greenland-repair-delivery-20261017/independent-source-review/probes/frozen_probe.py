import os,sys,json,gzip,hashlib,subprocess,pathlib,collections,bisect
W=pathlib.Path(__file__).resolve().parents[1];HEAD='19858cf7aa887efad5d0c6ba0736d5672bf0aef5';BASE='defe4dea8d79963350f34bd09fe80d1825049ed5';Q='coordination/engineering/global-current-cell-work-queue-20261014/';P='coordination/engineering/greenland-repair-delivery-20261017/'
consumed={}
def sha(b):return hashlib.sha256(b).hexdigest()
def raw(commit,path):
 cmd=['git','-c','protocol.allow=never','-C',str(W)];env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
 def git(*args):return subprocess.check_output(cmd+list(args),env=env)
 meta,name=git('ls-tree','-z',commit,'--',path).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert name.decode()==path and kind=='blob' and mode in ['100644','100755'];n=int(git('cat-file','-s',oid));assert n<=33554432;b=git('cat-file','blob',oid);assert len(b)==n
 consumed[(commit,path)]={'commit':commit,'path':path,'bytes':n,'sha256':sha(b),'git_blob_oid':oid};return b

def decoded(commit,path):
 b=gzip.decompress(raw(commit,path));assert len(b)<=33554432;consumed[(commit,path)].update(decoded_bytes=len(b),decoded_sha256=sha(b));return b

def document(name):return json.loads(raw(BASE,Q+name))
queue=document('source-package-queue.json');pkg=next(p for p in queue['packages'] if p['package_id']=='gb-GRL-ADM1--repair-evaluation');assert pkg==json.loads(raw(HEAD,P+'source-stage/package.json'))
census=document('source-census-summary.json');physical=document('physical-unassigned-summary.json');roster=json.loads(decoded(BASE,Q+'source-feature-roster.json.gz'))
for name,body in [('source-census-summary.json',census),('physical-unassigned-summary.json',physical)]:
 pin=queue.get('input_sha256',{}).get(name)
 if pin:assert sha(raw(BASE,Q+name))==pin
result={'head':HEAD,'reviewer':os.environ['CODEX_THREAD_ID'],'method':'Independent original frozen source-candidate interval/physical-support intersection, complete requested block input hashes, all target candidate rows; no stock extractor invoked','blocks':[]}
for b in pkg['native_blocks']:
 def read_intervals(kind):
  pin=census['blocks'][b] if kind=='source-candidates' else next(x for x in physical['phases'][b]['files'] if x['kind']==kind)
  parts=pin.get('parts',[{'path':kind+'-block-%03d.json.gz'%b,**pin}]);out=[]
  for part in parts:
   blob=raw(BASE,Q+part['path']);assert sha(blob)==part['sha256'];body=gzip.decompress(blob);assert len(body)<=33554432 and sha(body)==part['decoded_sha256'];consumed[(BASE,Q+part['path'])].update(decoded_bytes=len(body),decoded_sha256=sha(body));out+=json.loads(body)
  if pin.get('parts'):assert sha((json.dumps(out,separators=(',',':'))+'\n').encode())==pin['decoded_sha256']
  return out
 source=read_intervals('source-candidates');land={r['y']:r['runs'] for r in read_intervals('physical-support')};water={r['y']:r['runs'] for r in read_intervals('inland-water-support')};actual=[]
 for row in source:
  y=row['y']
  for a,z,owners,sids in row['runs']:
   if owners not in [[21253],[21254]]:continue
   mapped=[s for s in sids if roster[s-1]['owners']];assert mapped
   family=min(roster[s-1]['family_index'] for s in mapped)
   if family!=138:continue
   events=collections.defaultdict(lambda:[0,0]);events[a];events[z]
   for cl,lookup in enumerate([land,water]):
    spans=lookup.get(y,[]);ends=[r[1] for r in spans];start=bisect.bisect_right(ends,a)
    for p,q,*_ in spans[start:]:
     if p>=z:break
     lo=max(a,p);hi=min(z,q)
     if lo<hi:events[lo][cl]+=1;events[hi][cl]-=1
   state=[0,0];previous=a
   for x,delta in sorted(events.items()):
    if x>previous and any(state):
     assert not all(state);actual.append([y,previous,x,owners,sids,'land' if state[0] else 'inland-water'])
    state[0]+=delta[0];state[1]+=delta[1];previous=x
   assert state==[0,0]
 frozen=json.loads(decoded(HEAD,P+'source-stage/frozen-block-%03d.json.gz'%b));assert actual==frozen,('block mismatch',b,len(actual),len(frozen));count=sum(r[2]-r[1] for r in actual);result['blocks'].append({'block':b,'intervals':len(actual),'cells':count,'literal_rows_match':True});print(b,len(actual),count,flush=True)
result['total_cells']=sum(r['cells'] for r in result['blocks']);result['total_intervals']=sum(r['intervals'] for r in result['blocks']);assert result['total_cells']==502216 and result['total_intervals']==62096
result['consumed']=list(consumed.values());result['unique_raw_plus_decoded_input_bytes']=sum(d['bytes']+d.get('decoded_bytes',0) for d in consumed.values());assert result['unique_raw_plus_decoded_input_bytes']<=268435456
(W/'.review-greenland/frozen-probe-result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS complete frozen interval rederivation',result['unique_raw_plus_decoded_input_bytes'])
