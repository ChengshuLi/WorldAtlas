"""Authenticate full original/supported/held/native constructor conservation.
Usage: python check-accounting.py READ_ONLY_REPO AUTHORITY_COMMIT FRESH_OUTPUT
"""
import collections,gzip,hashlib,io,json,os,pathlib,subprocess,sys
assert len(sys.argv)==4
W=pathlib.Path(sys.argv[1]).absolute();H=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();P='coordination/engineering/uk-native-repair-20261017'
assert len(H)==40 and all(c in '0123456789abcdef' for c in H) and O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents))
sha=lambda b:hashlib.sha256(b).hexdigest();pins=[];total=0;MAX=64*1024*1024;PHASE=256*1024*1024;env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
def read(p,c=H):
 global total
 assert p and not p.startswith('/') and all(x not in ['', '.', '..'] for x in p.split('/'))
 cmd=['git','-c','protocol.allow=never','-C',str(W)];meta,name=subprocess.check_output(cmd+['ls-tree','-z',c,'--',p],env=env).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and name.decode()==p
 n=int(subprocess.check_output(cmd+['cat-file','-s',oid],env=env));assert 0<n<=MAX;b=subprocess.check_output(cmd+['cat-file','blob',oid],env=env);assert len(b)==n and hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==oid
 pin={'commit':c,'path':p,'mode':mode,'git_blob_oid':oid,'bytes':n,'sha256':sha(b)}
 if p.endswith('.gz'):
  with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:d=f.read(MAX+1)
  assert len(d)<=MAX;pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 total+=n+pin.get('decoded_bytes',0);assert total<=PHASE;pins.append(pin);return json.loads(b)
def keys(rows,reason=False):
 out={}
 for r in rows:
  for run in r['runs']:
   assert len(run)==(4 if reason else 3)
   a,z,o=run[:3];assert all(type(v)==int for v in [r['y'],a,z,o]) and 0<=a<z<=262166 and 0<=r['y']<262166 and o>0
   for x in range(a,z):
    k=(x,r['y'],o);assert k not in out;out[k]=run[3] if reason else None
 return out
frozen=[]
for b in range(18,22):frozen+=read(P+f'/frozen-queue/block-{b:03}.json.gz')
original={(x,y,o[0]):kind for y,a,z,o,s,kind in frozen for x in range(a,z)};assert len(original)==89390==sum(z-a for y,a,z,*_ in frozen) and len(frozen)==19349
scope=read(P+'/source-stage/source-scope-assessment.json');context=read(P+'/context-001/complete-context.json');historical=read(P+'/historical-001/historical-applicability.json');partition=read(P+'/qualified-native-inputs-001/original-scope-partition.json')
diag=read(P+'/native-diagnostic-001/native-diagnostic.json');support=keys(diag['supported_rows']);dh=keys(diag['held_rows']);requested=keys(diag['requested_rows']);london={k for k in original if k[2]==13};assert len(london)==640 and set(requested)==set(original)-london and not(set(support)&set(dh)) and set(support)|set(dh)==set(requested)
held=keys(read(P+'/qualified-native-inputs-001/held-original.json')['rows'],True);patch=keys(read(P+'/qualified-native-inputs-001/native-patch.json')['rows']);assert set(patch)==set(support) and set(held)==set(dh)|london and not(set(patch)&set(held)) and set(patch)|set(held)==set(original)
assert len(support)==diag['supported_cells']==partition['supported_cells'] and len(dh)==diag['held_cells'] and len(held)==partition['held_cells']
decisions=keys(diag['decision_rows'],True);assert set(decisions)==set(requested) and {k for k,r in decisions.items() if r=='assigned_cells'}==set(support)
assert all(held[k]==decisions[k] for k in dh) and all(held[k]=='held-mixed-source-positive-authority-not-qualified' for k in london)
source=read(P+'/qualified-native-inputs-001/source-evidence.json');fullsource=read(P+'/native-inputs-001/source-evidence.json');assert {k:v for k,v in source.items() if k!='targets'}=={k:v for k,v in fullsource.items() if k!='targets'}
fulltargets={t['pixelIndex']:t for t in fullsource['targets']};targets={t['pixelIndex']:t for t in source['targets']};assert len(targets)==len(source['targets']) and set(targets)=={k[2] for k in support}
classes={'land':'mapped_land_support','inland-water':'mapped_inland_water_support'}
for o,t in targets.items():
 assert {k:v for k,v in t.items() if k!='coverage_rows'}=={k:v for k,v in fulltargets[o].items() if k!='coverage_rows'}
 coverage=keys([{'y':r['y'],'runs':[[a,z,o,c] for a,z,c in r['runs']]} for r in t['coverage_rows']],True);assert set(coverage)=={k for k in support if k[2]==o} and all(c==classes[original[k]] for k,c in coverage.items())
con=read(P+'/native-authority-001/constructor-result.json');rows=con['ledger_rows'];assert con['kind']=='existing-source-target-native-constructor-result' and len(rows)==len(targets) and len({r['target_id'] for r in rows})==len(rows) and len({r['pixelIndex'] for r in rows})==len(rows) and all(r['disposition']=='assigned' for r in rows)
ak=keys([r for t in rows for r in t['native_rows']]);assert set(ak)==set(patch) and sum(t['native_cells'] for t in rows)==len(ak)
for t in rows:
 own=keys(t['native_rows']);assert len(own)==t['native_cells'] and all(k[2]==t['pixelIndex'] for k in own) and t['target_id']==targets[t['pixelIndex']]['id'] and t['base_geometry']==targets[t['pixelIndex']]['base_geometry']
for role,path in [('source_evidence',P+'/qualified-native-inputs-001/source-evidence.json'),('native_patch',P+'/qualified-native-inputs-001/native-patch.json')]:
 locator=con['inputs'][role];assert locator['path']==path;actual=read(locator['path'],locator['commit']);present=source if role=='source_evidence' else read(path);assert actual==present
by={r['pixelIndex']:r for r in scope['target_checks']};counts=collections.Counter(k[2] for k in original);sc=collections.Counter(k[2] for k in support);hc=collections.Counter(k[2] for k in held);assert len(by)==91 and set(by)==set(counts) and all(counts[o]==r['candidate_cells'] for o,r in by.items())
foreign={tuple(k) for f in context['foreign_natural_earth_hits'] for k in f['native_cells']};assert foreign<=set(held) and not foreign&set(support)
historicalkeys={tuple(k) for r in historical['native_overlap_rows'] for k in r['cells']};assert historicalkeys<=set(original) and len(historicalkeys)==historical['native_overlap_cells'];assert len({r['id'] for r in historical['native_overlap_rows']})==historical['native_overlap_candidates']
ownerrows=[{'owner':o,'id':by[o]['id'],'original_cells':counts[o],'supported_cells':sc[o],'held_cells':hc[o]} for o in sorted(counts)];assert ownerrows==partition['owner_counts']
result={'version':1,'original_cells':len(original),'original_intervals':len(frozen),'original_owners':len(counts),'supported_cells':len(support),'held_cells':len(held),'supported_owners':len(sc),'wholly_held_owners':len(set(counts)-set(sc)),'source_members':scope['source_members'],'london_member_count':scope['london_construction']['declared_members'],'london_cells':len(london),'complete_gb_source_features':scope['complete_gb_source_feature_count'],'complete_catalogue_products':context['original_source_products'],'complete_catalogue_features':context['original_source_features'],'foreign_ownerless_features':context['foreign_ownerless_features'],'foreign_ownerless_candidate_cells':context['foreign_ownerless_candidate_cells'],'foreign_country_and_adm1_held_cells':len(foreign),'separate_physical_companion_cells':context['physical_companion']['native_cells'],'separate_physical_companion_owners':len(context['physical_companion']['owners']),'complete_historical_candidates':historical['complete_historical_candidates'],'historical_overlap_candidates':historical['native_overlap_candidates'],'historical_overlap_cells':len(historicalkeys),'historical_overlap_supported_cells':len(historicalkeys&set(support)),'historical_overlap_held_cells':len(historicalkeys&set(held)),'supported_physical_class_counts':dict(collections.Counter(original[k] for k in support)),'held_physical_class_counts':dict(collections.Counter(original[k] for k in held)),'held_reason_counts':dict(collections.Counter(held.values())),'exact_original_supported_held_partition':True,'exact_supported_patch_diagnostic_constructor_keys_equal':True,'all_source_physical_negative_inputs_unchanged':True,'owner_counts':ownerrows,'inputs':pins,'limits':['This source-relative constructor does not establish current selected owner-zero, final selected/emitted acceptance, contemporary legal boundaries or current dry land.','London remains wholly held. Complete source and historical whole-candidate discrepancies remain; historical overlaps are accounted for, not independently cleared.','The separate physical-interpretation companion remains uncredited. All original product-specific source dates, licence terms and conflicts remain.']}
b=(json.dumps(result,separators=(',',':'))+'\n').encode();assert total+len(b)<=PHASE and len(b)<=MAX and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
with (O/'original-scope-disposition.json').open('xb') as f:f.write(b)
with (O/'preparation.json').open('x') as f:json.dump({'complete':True,'bytes':len(b),'sha256':sha(b)},f);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['inputs','owner_counts','limits']}))
