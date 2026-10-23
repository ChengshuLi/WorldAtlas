"""Keep only genuinely diagnosed source-relative support; account for every original key.
Usage: python prepare-supported.py READ_ONLY_REPO DIAGNOSTIC_COMMIT FRESH_OUTPUT
This does not construct authority. It preserves original holds and complete source inputs.
"""
import collections,gzip,hashlib,io,json,os,pathlib,subprocess,sys,math,struct
W=pathlib.Path(sys.argv[1]).absolute();H=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();P='coordination/engineering/papua-new-guinea-native-repair-20261017';assert len(sys.argv)==4 and len(H)==40 and all(c in '0123456789abcdef' for c in H) and O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents))
sha=lambda b:hashlib.sha256(b).hexdigest();pins=[];total=0;env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
def read(p,c=H,parse=True):
 global total
 assert p and not p.startswith('/') and all(x not in ['', '.', '..'] for x in p.split('/'))
 cmd=['git','-c','protocol.allow=never','-C',str(W)];meta,name=subprocess.check_output(cmd+['ls-tree','-z',c,'--',p],env=env).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and name.decode()==p
 n=int(subprocess.check_output(cmd+['cat-file','-s',oid],env=env));assert n>0;b=subprocess.check_output(cmd+['cat-file','blob',oid],env=env);assert len(b)==n and hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==oid
 pin={'commit':c,'path':p,'mode':mode,'git_blob_oid':oid,'bytes':n,'sha256':sha(b)}
 if p.endswith('.gz'):
  with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:d=f.read()
  pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 total+=n+pin.get('decoded_bytes',0);pins.append(pin);return json.loads(b) if parse else b
frozen=[]
for b in range(32,35):frozen+=read(P+f'/frozen-queue/block-{b:03}.json.gz')
original={(x,y,o[0]):kind for y,a,z,o,s,kind in frozen for x in range(a,z)};assert len(original)==56552==sum(z-a for y,a,z,*_ in frozen) and len(frozen)==20060
source=read(P+'/compaction-001/source-evidence.json');equivalence=read(P+'/compaction-001/whole-negative-equivalence.json');diag=read(P+'/native-diagnostic-001/native-diagnostic.json');supported={};held={}
for row in diag['supported_rows']:
 for a,z,o in row['runs']:
  for x in range(a,z):assert (x,row['y'],o) not in supported;supported[(x,row['y'],o)]=original[(x,row['y'],o)]
for row in diag['decision_rows']:
 for a,z,o,reason in row['runs']:
  if reason=='assigned_cells':continue
  for x in range(a,z):assert (x,row['y'],o) not in held;held[(x,row['y'],o)]=reason
assert set(held)=={(x,r['y'],o) for r in diag['held_rows'] for a,z,o in r['runs'] for x in range(a,z)}
assert {(x,r['y'],o) for r in diag['requested_rows'] for a,z,o in r['runs'] for x in range(a,z)}==set(original)
# Authenticate the transformation; a stale or forged proof cannot authorize changed operands.
source_pin=equivalence['original_source'];prep=read(P+'/compaction-001/preparation.json')
for name in ['source-evidence.json','whole-negative-equivalence.json']:
 actual=next(p for p in pins if p['path']==P+'/compaction-001/'+name)
 assert {k:actual[k] for k in ['bytes','sha256']}==prep['outputs'][name]
fullsource=read(source_pin['path'],source_pin['commit']);assert pins[-1]==source_pin
assert {k:v for k,v in source.items() if k!='targets'}=={k:v for k,v in fullsource.items() if k!='targets'}
assert len(source['targets'])==len(fullsource['targets'])==len(equivalence['targets'])==equivalence['targets_count']
assert equivalence['original_operands']==sum(len(t['territorial_exclusions']) for t in fullsource['targets'])
physical_pin=fullsource['physical_input'];stages=read(physical_pin['path'],physical_pin['commit']);assert pins[-1]==physical_pin;stageby={s['target']:s for s in stages};assert len(stageby)==len(stages)
lat_pin=fullsource['native_latitudes'];lat=read(lat_pin['path'],lat_pin['commit'],False);assert pins[-1]==lat_pin;size=fullsource['native_contract']['size'];assert len(lat)==8*size
negative_geometries=[]
for operand in equivalence['complete_negative_operands']:
 pin=operand['pin'];fc=read(pin['path'],pin['commit']);assert pins[-1]==pin;negative_geometries.append(fc['features'][operand['feature_ordinal']]['geometry'])
def bounds(g):
 assert set(g)=={'type','coordinates'} and g['type'] in ['Polygon','MultiPolygon'];polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates'];assert polys;out=[]
 for poly in polys:
  assert poly;xs=[];ys=[];seam=False
  for ring in poly:
   assert len(ring)>=4 and ring[0]==ring[-1]
   for i,p in enumerate(ring):
    assert len(p)==2 and all(type(n) in [int,float] and math.isfinite(n) for n in p) and abs(p[0])<=180 and abs(p[1])<=90
    xs.append(p[0]);ys.append(p[1]);seam|=i>0 and abs(p[0]-ring[i-1][0])>180
  lo,hi=min(xs),max(xs)
  if seam or hi-lo>180:lo,hi=-180,180
  out.append([lo,min(ys),hi,max(ys)])
 return out
hit=lambda a,b:a[0]<=b[2] and b[0]<=a[2] and a[1]<=b[3] and b[1]<=a[3]
kept=dropped=0
for old,new,proof in zip(fullsource['targets'],source['targets'],equivalence['targets']):
 assert old['id']==new['id']==proof['id'] and old['pixelIndex']==new['pixelIndex']==proof['pixelIndex']
 assert {k:v for k,v in old.items() if k!='territorial_exclusions'}=={k:v for k,v in new.items() if k!='territorial_exclusions'}
 stage=stageby[old['id']];assert stage['selected']['id']==old.get('target_id',old['id']) and stage['selected']['geometry']==old['base_geometry'] and stage['consumed']['properties']['shapeID']==old['id'].removeprefix(old['source_family']+':')
 ob=bounds(stage['consumed']['geometry']);sb=bounds(old['base_geometry']);assert ob==proof['original_bounds'] and sb==proof['selected_bounds']
 mb=[]
 for row in old['coverage_rows']:
  y=struct.unpack_from('<d',lat,row['y']*8)[0];assert math.isfinite(y)
  for a,z,kind in row['runs']:assert 0<=a<z<=size;mb.append([(a+.5)*360/size-180,y,(z-.5)*360/size-180,y])
 assert old['territorial_exclusions']==negative_geometries and len(proof['decisions'])==len(negative_geometries)
 expected=[]
 for ordinal,(g,decision,operand) in enumerate(zip(negative_geometries,proof['decisions'],equivalence['complete_negative_operands'])):
  nb=bounds(g);assert nb==operand['bounds'];oc=any(hit(a,b) for a in nb for b in ob);sc=any(hit(a,b) for a in nb for b in sb);mc=any(hit(a,b) for a in nb for b in mb);retain=oc or sc or mc
  assert decision['original_negative_ordinal']==ordinal and decision['original_whole_bounds_contact']==oc and decision['selected_whole_bounds_contact']==sc and decision['original_full_mask_bounds_contact']==mc and decision['new_negative_ordinal']==(len(expected) if retain else None)
  assert decision['decision']==('retained_exact_whole_operand' if retain else 'omitted_proven_disjoint_whole_operand')
  if retain:expected.append(g);kept+=1
  else:dropped+=1
 assert new['territorial_exclusions']==expected
assert equivalence['all_other_source_fields_unchanged'] and equivalence['original_operands']==kept+dropped and equivalence['retained_operands']==kept and equivalence['omitted_whole_disjoint_operands']==dropped
assert all(source_pin[k]==diag['original_pins']['source_evidence'][k] for k in ['path','bytes','sha256','git_blob_oid'])
assert len(supported)==diag['supported_cells'] and len(held)==diag['held_cells'] and not (set(supported)&set(held)) and set(supported)|set(held)==set(original)
# Keep specific unresolved independent source-fitness findings as exact original holds.
# Derive membership from the authenticated complete prior packet, never a copied count.
prior=read(P+'/prior-001/prior-melanesia-applicability.json');review_holds={};review_components=[];already_native_held=set()
for r in prior['component_rows']:
 if not r['provisional_source_fitness_hold_keys']:continue
 assert r['prior_class']=='held' or r['literal_remainder_native_cells']
 if r['prior_class']=='held':assert r['prior_outcome'].startswith('held-')
 review_components.append({'component_id':r['component_id'],'original_keys':r['provisional_source_fitness_hold_keys'],'complete_original_outcome':r['complete_original_outcome'],'complete_original_comparison':r['complete_original_comparison'],'complete_original_remainder':r['complete_original_remainder']})
 for cell in r['provisional_source_fitness_hold_keys']:
  k=tuple(cell);assert k in original;review_holds[k]='unresolved_prior_source_fitness'
  if k in held:already_native_held.add(k)
  elif k in supported:held[k]=review_holds[k];del supported[k]
  else:assert k in review_holds and k in held
assert set(review_holds)=={tuple(k) for k in prior['source_fitness_hold_keys']} and len(review_holds)==prior['source_fitness_hold_cells']
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
summary={'version':1,'original_cells':len(original),'original_intervals':len(frozen),'original_owners':len(counts),'supported_cells':len(supported),'held_cells':len(held),'supported_owners':len(sc),'wholly_held_owners':len(set(counts)-set(sc)),'held_reason_counts':dict(reasons),'native_diagnostic_supported_cells':diag['supported_cells'],'native_diagnostic_held_cells':diag['held_cells'],'prior_source_fitness_held_cells':len(review_holds),'prior_source_fitness_already_native_held_cells':len(already_native_held),'owner_counts':[{'owner':o,'id':by[o]['id'],'original_cells':counts[o],'supported_cells':sc[o],'held_cells':hc[o]} for o in sorted(counts)],'original_scope_conserved':True,'inputs':pins,'limits':['This diagnostic and independent-review partition grants no native authority or accepted repair credit. The stock constructor must consume the exact emitted source and patch.','All complete original source/physical inputs remain. The separately pinned whole-negative equivalence proof removes only operands disjoint from full original sources, full selected targets and every original mask interval; retained operands are exact. Coverage rows contain only supported centres.','Current selected owner-zero and final emitted conservation remain delivery obligations.']}
products={'source-evidence.json':source,'native-patch.json':{'rows':pack(supported,False)},'held-original.json':{'rows':pack(held,True)},'prior-source-fitness-holds.json':{'reason':'unresolved_prior_source_fitness','original_keys':sorted(review_holds),'components':review_components,'review_urls':['https://github.com/ChengshuLi/WorldAtlas/pull/1639#issuecomment-6097837251','https://github.com/ChengshuLi/WorldAtlas/issues/1647#issuecomment-6162649556'],'limit':'The new source-relative geometric diagnostic does not resolve these exact prior mixed-source-support/whole-source-fitness and unknown-physical/numeric-closure questions. These original keys are held, not counted as supported delivery.'},'original-scope-partition.json':summary};encoded={n:(json.dumps(j,ensure_ascii=False,separators=(',',':'))+'\n').encode() for n,j in products.items()};assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
for n,b in encoded.items():
 with (O/n).open('xb') as f:f.write(b)
with (O/'preparation.json').open('x') as f:json.dump({'complete':True,'outputs':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in encoded.items()}},f);f.write('\n')
print(json.dumps({k:summary[k] for k in ['original_cells','supported_cells','held_cells','supported_owners','wholly_held_owners','held_reason_counts']}))
