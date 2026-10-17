import collections,gzip,hashlib,json,pathlib,subprocess,sys,resource
W,BASE,HEAD,OUT=sys.argv[1:]
output=pathlib.Path(OUT)
assert output.parent.resolve(strict=True)==output.parent.absolute(), 'Ordinary output parent required'
assert not output.exists() and not output.is_symlink(), 'Fresh output required'
P='coordination/engineering/five-repair-delivery-20261017/'
inputs={}
def raw(c,p):
 row=subprocess.check_output(['git','-c','protocol.allow=never','-C',W,'ls-tree','-z',c,'--',p]).rstrip(b'\0');meta,name=row.split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and name.decode()==p
 size=int(subprocess.check_output(['git','-c','protocol.allow=never','-C',W,'cat-file','-s',oid]))
 with subprocess.Popen(['git','-c','protocol.allow=never','-C',W,'cat-file','blob',oid],stdout=subprocess.PIPE) as proc:
  b=proc.stdout.read(size+1);assert len(b)==size and not proc.stdout.read(1) and proc.wait()==0
 assert hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 inputs[c+':'+p]=dict(commit=c,path=p,mode=mode,git_blob_oid=oid,bytes=size,sha256=hashlib.sha256(b).hexdigest());return b
def data(c,p):
 b=raw(c,p);return json.loads(gzip.decompress(b) if p.endswith('.gz') else b)
def pin(q):
 b=raw(q['commit'],q['path']);assert len(b)==q['bytes'] and hashlib.sha256(b).hexdigest()==q['sha256'];return json.loads(b)
def normal(rows):
 d=collections.defaultdict(list)
 for r in rows:
  for run in r['runs']:d[r['y']].append(run[:3])
 result=[]
 for y,rs in sorted(d.items()):
  merged=[]
  for a,z,o in sorted(rs):
   assert z>a and (not merged or a>=merged[-1][1]),(y,a,z,o)
   if merged and a==merged[-1][1] and o==merged[-1][2]:merged[-1][1]=z
   else:merged.append([a,z,o])
  result.append(dict(y=y,runs=merged))
 return result
def counts(rows):
 c=collections.Counter()
 for r in rows:
  for a,z,o,*rest in r['runs']:c[o]+=z-a
 return c
def subtract(original,support):
 by={r['y']:r['runs'] for r in normal(support)};out=[]
 for row in normal(original):
  runs=[];s=by.get(row['y'],[]);i=0
  for a,z,o in row['runs']:
   while i<len(s) and s[i][1]<=a:i+=1
   x=a
   while i<len(s) and s[i][0]<z:
    l,h,so=s[i];assert so==o and x<=l<h<=z
    if x<l:runs.append([x,l,o])
    x=h;i+=1
   if x<z:runs.append([x,z,o])
  if runs:out.append(dict(y=row['y'],runs=runs))
 assert normal(support+out)==normal(original)
 return out
specs=[('Russia','ec8dd6711677fb77586441bbd5ef2d34488df2b6','russia-repair-delivery-20261017',(2566967,2557516,9451,334)),('Angola','86b089e2b82a2e85264c96b11188854f2d1bce4a','angola-repair-delivery-20261017',(170526,141263,29263,47)),('Japan','c76c45be06853204183bad2b858081ef37bd8d40','japan-native-repair-20261017',(106333,106333,0,556)),('Canada','5329b46001c4423a042f2ec3d0845d56a4b43756','canada-repair-delivery-20261017',(438062,437959,103,209)),('UK','e50dadbb6c8e948d8cbc57444e8178e6ef37a137','uk-native-repair-20261017',(89390,88722,668,91))]
config=data(HEAD,P+'config/compose.json');allq=[];packages=[];all_original=[];all_supported=[];subjects=[]
for name,h,folder,expected in specs:
 prefix='coordination/engineering/'+folder+'/'
 if name=='Russia':qs=data(h,prefix+'config/compose.json')['authorities']
 elif name=='Angola':qs=[data(h,prefix+'config/conservative-authority-quartet.json')]
 elif name=='Canada':qs=data(h,prefix+'source-review/qualified-authority-handoff.json')['authorities']
 else:qs=[data(h,prefix+'handoff/native-authority-quartet.json')]
 allq+=qs;supported=[]
 for q in qs:
  r=pin(q['native_patch'])['rows'];supported+=r;assert sum(counts(r).values())==sum(v['native_cells'] for v in pin(q['ledger'])['ledger_rows'])
  pin(q['rule_preimage']);pin(q['source_authority'])
 if name=='Canada':
  original=[];package=data(h,prefix+'frozen-original-001/package.json')
  for block in package['native_blocks']:
   for y,a,z,owners,sources,kind in data(h,prefix+f'frozen-original-001/block-{block:03}.json.gz'):
    assert len(owners)==1;original.append(dict(y=y,runs=[[a,z,owners[0]]]))
 else:original=data(h,prefix+'source-stage/native-patch.json')['rows']
 held=subtract(original,supported)
 hp={'Russia':'native-partition-preaccept-001/held-native-patch.json','Angola':'conservative-002/held-native-rows.json','UK':'qualified-native-inputs-001/held-original.json'}.get(name)
 if hp:assert normal(held)==normal(data(h,prefix+hp)['rows'])
 oc,sc,hc=map(counts,[original,supported,held]);sub=data(h,prefix+'evidence-quality.json')['subject_ids'];actual=(sum(oc.values()),sum(sc.values()),sum(hc.values()),len(sub));assert actual==expected and len(oc)==len(set(sub))
 packages.append(dict(name=name,requested_cells=actual[0],supported_cells=actual[1],held_cells=actual[2],original_subjects=actual[3],supported_owners=len(sc),held_owners=len(hc),wholly_held_owners=len(set(oc)-set(sc)),per_owner=[dict(owner=o,requested=oc[o],supported=sc[o],held=hc[o]) for o in sorted(oc)]));subjects+=sub;all_original+=original;all_supported+=supported
assert config['authorities']==allq and len(subjects)==len(set(subjects))==1237
selector=data(BASE,'data/ownership-selection.json');side=pin(dict(selector['additive_release'],commit=selector['additive_release'].get('commit',BASE)));before=pin(side['logical_asset_map']['patch'])['rows'];normal(before+all_original);proposed=normal(before+all_supported);after=data(HEAD,P+'composition-001/patch.json')['rows'];assert normal(after)==proposed
oldledger=pin(side['logical_asset_map']['ledger']);oldreg=pin(side['authority_registry']);ledger=data(HEAD,P+'composition-001/selected-ledger.json');reg=data(HEAD,P+'composition-001/authority-registry.json');canon=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'))
for a,b in [(oldledger['rows'],ledger['rows']),(oldreg['entries'],reg['entries'])]:assert not(collections.Counter(map(canon,a))-collections.Counter(map(canon,b)))
heldrows=lambda rr:[r for r in rr if r.get('disposition') not in ('assigned','zero-cell')]
assert collections.Counter(map(canon,heldrows(oldledger['rows'])))==collections.Counter(map(canon,heldrows(ledger['rows'])))
report=dict(kind='exact-five-package-interval-conservation',baseline_commit=BASE,candidate_commit=HEAD,packages=packages,original_subjects=len(subjects),requested_cells=sum(counts(all_original).values()),supported_cells=sum(counts(all_supported).values()),held_cells=sum(x['held_cells'] for x in packages),prior_cells=sum(counts(before).values()),proposed_cumulative_cells=sum(counts(proposed).values()),removed_cells=0,reassigned_cells=0,prior_ledger_rows=len(oldledger['rows']),proposed_ledger_rows=len(ledger['rows']),prior_authorities=len(oldreg['entries']),proposed_authorities=len(reg['entries']),prior_held_rows=len(heldrows(oldledger['rows'])),proposed_held_rows=len(heldrows(ledger['rows'])),literal_quartets_preserved=True,original_package_sets_disjoint_from_each_other_and_prior_patch=True,inputs=list(inputs.values()),measured_input_bytes=sum(x['bytes'] for x in inputs.values()),authenticated_input_files=len(inputs),largest_input_bytes=max(x['bytes'] for x in inputs.values()),observed_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,limits=['Immutable native intervals only; no source/physical science rerun. Exact byte-sized reads and measured memory do not impose a hard RSS bound.','Current owner-zero and actual selected/emitted asset/GPU/Canvas acceptance remain mandatory. Only Japan can complete after final delivery.'])
assert (report['requested_cells'],report['supported_cells'],report['held_cells'],report['proposed_cumulative_cells'])==(3371278,3331793,39485,5541379)
with open(OUT,'x') as f:json.dump(report,f,separators=(',',':'));f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('packages','inputs')}))
