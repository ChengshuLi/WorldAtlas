"""Keep only genuinely diagnosed source-relative support; account for every original key.
Usage: python prepare-supported.py READ_ONLY_REPO DIAGNOSTIC_COMMIT FRESH_OUTPUT
This does not construct authority. It preserves original holds and complete source inputs.
"""
import collections,gzip,hashlib,io,json,os,pathlib,subprocess,sys
W=pathlib.Path(sys.argv[1]).absolute();H=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();P='coordination/engineering/philippines-native-repair-20261017';assert len(sys.argv)==4 and len(H)==40 and all(c in '0123456789abcdef' for c in H) and O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents))
sha=lambda b:hashlib.sha256(b).hexdigest();pins=[];total=0;MAX=64*1024*1024;PHASE=256*1024*1024;env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
def read(p):
 global total
 assert p and not p.startswith('/') and all(x not in ['', '.', '..'] for x in p.split('/'))
 cmd=['git','-c','protocol.allow=never','-C',str(W)];meta,name=subprocess.check_output(cmd+['ls-tree','-z',H,'--',p],env=env).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and name.decode()==p
 n=int(subprocess.check_output(cmd+['cat-file','-s',oid],env=env));assert 0<n<=MAX;b=subprocess.check_output(cmd+['cat-file','blob',oid],env=env);assert len(b)==n and hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==oid
 pin={'commit':H,'path':p,'mode':mode,'git_blob_oid':oid,'bytes':n,'sha256':sha(b)}
 if p.endswith('.gz'):
  with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:d=f.read(MAX+1)
  assert len(d)<=MAX;pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 total+=n+pin.get('decoded_bytes',0);assert total<=PHASE;pins.append(pin);return json.loads(b)
frozen=[]
for b in range(28,32):frozen+=read(P+f'/frozen-queue/block-{b:03}.json.gz')
original={(x,y,o[0]):kind for y,a,z,o,s,kind in frozen for x in range(a,z)};assert len(original)==96607==sum(z-a for y,a,z,*_ in frozen) and len(frozen)==36123
source=read(P+'/native-inputs-002/source-evidence.json');diag=read(P+'/native-diagnostic-002/native-diagnostic.json');supported={};held={}
for row in diag['supported_rows']:
 for a,z,o in row['runs']:
  for x in range(a,z):assert (x,row['y'],o) not in supported;supported[(x,row['y'],o)]=original[(x,row['y'],o)]
for row in diag['decision_rows']:
 for a,z,o,reason in row['runs']:
  if reason=='assigned_cells':continue
  for x in range(a,z):assert (x,row['y'],o) not in held;held[(x,row['y'],o)]=reason
assert set(held)=={(x,r['y'],o) for r in diag['held_rows'] for a,z,o in r['runs'] for x in range(a,z)}
assert {(x,r['y'],o) for r in diag['requested_rows'] for a,z,o in r['runs'] for x in range(a,z)}==set(original)
source_pin=next(p for p in pins if p['path']==P+'/native-inputs-002/source-evidence.json')
assert all(source_pin[k]==diag['original_pins']['source_evidence'][k] for k in ['path','bytes','sha256','git_blob_oid'])
assert len(supported)==diag['supported_cells'] and len(held)==diag['held_cells'] and not (set(supported)&set(held)) and set(supported)|set(held)==set(original)
assert set(supported).isdisjoint(held) and set(supported)|set(held)==set(original)
def pack(data,with_value):
 rows=collections.defaultdict(list)
 for (x,y,o),value in sorted(data.items(),key=lambda kv:(kv[0][1],kv[0][0],kv[0][2])):
  run=[x,x+1,o]+([value] if with_value else[])
  if rows[y] and rows[y][-1][1]==x and rows[y][-1][2:]==run[2:]:rows[y][-1][1]=x+1
  else:rows[y].append(run)
 return [{'y':y,'runs':rs} for y,rs in sorted(rows.items())]
classes={'land':'mapped_land_support','inland-water':'mapped_inland_water_support'};owners={k[2] for k in supported};targets=[]
for t in source['targets']:
 if t['pixelIndex'] not in owners:continue
 original_rows=t.get('coverage_rows')
 if original_rows is None:
  targets.append(t);continue
 cover={(x,r['y'],t['pixelIndex']):kind for r in original_rows for a,z,kind in r['runs'] for x in range(a,z)}
 own={k:v for k,v in supported.items() if k[2]==t['pixelIndex']};assert all(cover[k]==classes[v] for k,v in own.items());cr=[]
 for r in pack({k:classes[v] for k,v in own.items()},True):cr.append({'y':r['y'],'runs':[[a,z,c] for a,z,o,c in r['runs']]})
 targets.append({**t,'coverage_rows':cr})
assert {t['pixelIndex'] for t in targets}==owners;source['targets']=targets
counts=collections.Counter(k[2] for k in original);sc=collections.Counter(k[2] for k in supported);hc=collections.Counter(k[2] for k in held);reasons=collections.Counter(held.values());scope=read(P+'/source-stage/source-scope-assessment.json');by={r['pixelIndex']:r for r in scope['target_checks']};assert set(by)==set(counts)
summary={'version':1,'original_cells':len(original),'original_intervals':len(frozen),'original_owners':len(counts),'supported_cells':len(supported),'held_cells':len(held),'supported_owners':len(sc),'wholly_held_owners':len(set(counts)-set(sc)),'held_reason_counts':dict(reasons),'owner_counts':[{'owner':o,'id':by[o]['id'],'original_cells':counts[o],'supported_cells':sc[o],'held_cells':hc[o]} for o in sorted(counts)],'original_scope_conserved':True,'inputs':pins,'limits':['This diagnostic partition grants no native authority or accepted repair credit. The stock constructor must consume the exact emitted source and patch.','All original source/physical inputs and negative operands remain; source rows are restricted to the genuinely supported requested centres only.','Current selected owner-zero and final emitted conservation remain delivery obligations.']}
products={'source-evidence.json':source,'native-patch.json':{'rows':pack(supported,False)},'held-original.json':{'rows':pack(held,True)},'original-scope-partition.json':summary};encoded={n:(json.dumps(j,ensure_ascii=False,separators=(',',':'))+'\n').encode() for n,j in products.items()};assert total+sum(map(len,encoded.values()))<=PHASE and all(len(b)<=MAX for b in encoded.values());assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
for n,b in encoded.items():
 with (O/n).open('xb') as f:f.write(b)
with (O/'preparation.json').open('x') as f:json.dump({'complete':True,'outputs':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in encoded.items()}},f);f.write('\n')
print(json.dumps({k:summary[k] for k in ['original_cells','supported_cells','held_cells','supported_owners','wholly_held_owners','held_reason_counts']}))
