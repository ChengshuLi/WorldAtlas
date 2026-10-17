import subprocess,json,hashlib,collections,os,pathlib
import sys
R,BASE,HEAD,OUT=sys.argv[1:]
P='coordination/engineering/cuba-estonia-denmark-delivery-20261017/'
E=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_NO_REPLACE_OBJECTS='1')
def raw(c,p):return subprocess.check_output(['git','--no-replace-objects','-c','protocol.allow=never','-C',R,'show',c+':'+p],env=E)
def pin(c,p):
 b=raw(c,p); m=subprocess.check_output(['git','--no-replace-objects','-C',R,'ls-tree','-z',c,'--',p],env=E).rstrip(b'\0');meta,name=m.split(b'\t');mode,kind,oid=meta.decode().split();assert name.decode()==p and mode=='100644' and kind=='blob';assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid
 return dict(commit=c,path=p,mode=mode,git_blob_oid=oid,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()),json.loads(b)
def auth(q):
 actual,v=pin(q['commit'],q['path'])
 for k in actual:assert actual[k]==q[k],(k,actual,q)
 return v
def rows(v):
 d=collections.defaultdict(list)
 for r in v['rows']:d[r['y']]+=[x[:3] for x in r['runs']]
 return d
def normalize(d):
 count=0;out={}
 for y,rs in d.items():
  out[y]=rr=[]
  for a,b,o in sorted(rs):
   assert b>a
   if rr:
    assert a>=rr[-1][1],('overlap',y,a,b,o,rr[-1])
    if a==rr[-1][1] and o==rr[-1][2]:rr[-1][1]=b;count+=b-a;continue
   rr.append([a,b,o]);count+=b-a
 return out,count

def selected(c):
 _,selector=pin(c,'data/ownership-selection.json');sp,side=pin(c,selector['additive_release']['path']);assert sp['bytes']==selector['additive_release']['bytes'] and sp['sha256']==selector['additive_release']['sha256'];return selector,side
_,scope=pin(HEAD,P+'source-native-inputs.json')
_,config=pin(HEAD,P+'config/compose.json')
assert config['selector']['commit']==BASE
s,old=selected(BASE);oldpatch=auth(old['logical_asset_map']['patch']);prior=rows(oldpatch);assert normalize(prior)[1]==5910911
allq=[];packages=[];original_union=rows(oldpatch)
for package in scope['packages']:
 qs=package['quartets'];allq+=qs;own=collections.defaultdict(list)
 for q in qs:
  for role in q:auth(q[role])
  for y,rr in rows(auth(q['native_patch'])).items():own[y]+=rr
 original=rows(auth(package['original_patch']))
 for y,rr in original.items():original_union[y]+=rr
 keys=lambda d:{(y,x,o) for y,rr in d.items() for a,b,o in rr for x in range(a,b)}
 ok,sk=keys(original),keys(own);assert sk<=ok;hk=ok-sk
 if package['literal_holds']:
  held=auth(package['literal_holds']);literal=keys(rows(held)) if isinstance(held,dict) else {(v['y'],v['x'],v['pixelIndex']) for v in held};assert hk==literal
 else:assert not hk
 assert (len(ok),len(sk),len(hk))==(package['original_cells'],package['supported_cells'],package['held_cells'])
 oc,sc,hc=[collections.Counter(o for y,x,o in k) for k in [ok,sk,hk]]
 packages.append(dict(country=package['country'],original_cells=len(ok),supported_cells=len(sk),held_cells=len(hk),original_owners=len(oc),supported_owners=len(sc),wholly_held_owners=len(set(oc)-set(sc)),per_owner=[dict(owner=o,original=oc[o],supported=sc[o],held=hc[o]) for o in sorted(oc)]))
 for y,rr in own.items():prior[y]+=rr
assert allq==config['authorities']
assert normalize(original_union)[1]==5917136
assert auth(config['selector'])==s
_,patch=pin(HEAD,P+'composition-001/patch.json');assert normalize(rows(patch))==normalize(prior);assert normalize(prior)[1]==5995774
_,ledger=pin(HEAD,P+'composition-001/selected-ledger.json');_,registry=pin(HEAD,P+'composition-001/authority-registry.json');oldledger=auth(old['logical_asset_map']['ledger']);oldreg=auth(old['authority_registry']);canon=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'))
for before,after in [(oldledger['rows'],ledger['rows']),(oldreg['entries'],registry['entries'])]:assert not(collections.Counter(map(canon,before))-collections.Counter(map(canon,after)))
heldrows=lambda rr:[r for r in rr if r.get('disposition') not in ('assigned','zero-cell')]
assert collections.Counter(map(canon,heldrows(oldledger['rows'])))==collections.Counter(map(canon,heldrows(ledger['rows'])))
report=dict(kind='actual-native-and-original-hold-conservation',baseline_commit=BASE,candidate_commit=HEAD,packages=packages,original_cells=88703,new_supported_cells=84863,new_held_cells=3840,prior_native_cells=5910911,composed_native_cells=5995774,removed_cells=0,reassigned_cells=0,prior_ledger_rows=len(oldledger['rows']),composed_ledger_rows=len(ledger['rows']),prior_authorities=len(oldreg['entries']),composed_authorities=len(registry['entries']),prior_held_rows=len(heldrows(oldledger['rows'])),composed_held_rows=len(heldrows(ledger['rows'])),literal_prior_rows_authorities_holds_preserved=True,literal_reviewed_quartets_preserved=True,complete_original_sets_disjoint_from_accepted_patch=True,limits=['Immutable native/accounting evidence; no scientific producer replay. Current selected-owner-zero and actual emitted-consumer acceptance remain separate mandatory gates.','Estonia original holds and all whole-source limits remain. Cuba and Denmark are eligible for original source-relative package completion only after final acceptance.'])
try:
 t,new=selected(HEAD)
 if t!=s:
  assert {k:v for k,v in t.items() if k!='additive_release'}=={k:v for k,v in s.items() if k!='additive_release'}
  assert auth(new['logical_asset_map']['patch'])==patch and auth(new['logical_asset_map']['ledger'])==ledger and auth(new['authority_registry'])==registry
  report['final_selected_readback_matches_composition']=True
except KeyError:raise
with open(OUT,'x') as f:json.dump(report,f,separators=(',',':'));f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='packages'}))
