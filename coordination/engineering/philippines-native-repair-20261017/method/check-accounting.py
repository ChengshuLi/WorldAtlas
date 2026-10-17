"""Authenticate full original/supported/held/native constructor conservation.
Usage: python check-accounting.py READ_ONLY_REPO AUTHORITY_COMMIT FRESH_OUTPUT
"""
import collections,gzip,hashlib,io,json,os,pathlib,subprocess,sys
assert len(sys.argv)==4
W=pathlib.Path(sys.argv[1]).absolute();H=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();P='coordination/engineering/philippines-native-repair-20261017'
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
for b in range(28,32):frozen+=read(P+f'/frozen-queue/block-{b:03}.json.gz')
original={(x,y,o[0]):kind for y,a,z,o,s,kind in frozen for x in range(a,z)};assert len(original)==96607==sum(z-a for y,a,z,*_ in frozen) and len(frozen)==36123
scope=read(P+'/source-stage/source-scope-assessment.json');context=read(P+'/context-001/complete-context.json');historical=read(P+'/historical-001/historical-applicability.json');prior=read(P+'/prior-001/prior-record-applicability.json');partition=read(P+'/qualified-native-inputs-001/original-scope-partition.json');interpretation=read(P+'/interpretation-001/construction-and-source-limits.json')
diag=read(P+'/native-diagnostic-002/native-diagnostic.json');support=keys(diag['supported_rows']);dh=keys(diag['held_rows'],True);requested=keys(diag['requested_rows']);assert set(requested)==set(original) and not(set(support)&set(dh)) and set(support)|set(dh)==set(requested)
held=keys(read(P+'/qualified-native-inputs-001/held-original.json')['rows'],True);patch=keys(read(P+'/qualified-native-inputs-001/native-patch.json')['rows']);assert set(patch)==set(support) and held==dh and not(set(patch)&set(held)) and set(patch)|set(held)==set(original)
assert len(support)==diag['supported_cells']==partition['supported_cells'] and len(dh)==diag['held_cells'] and len(held)==partition['held_cells']
decisions=keys(diag['decision_rows'],True);assert set(decisions)==set(requested) and {k for k,r in decisions.items() if r=='assigned_cells'}==set(support) and all(held[k]==decisions[k] for k in dh)
source=read(P+'/qualified-native-inputs-001/source-evidence.json');fullsource=read(P+'/native-inputs-002/source-evidence.json');assert {k:v for k,v in source.items() if k!='targets'}=={k:v for k,v in fullsource.items() if k!='targets'}
fulltargets={t['id']:t for t in fullsource['targets']};targets={t['id']:t for t in source['targets']};assert len(targets)==len(source['targets']) and set(targets)=={t['id'] for t in fullsource['targets'] if t['pixelIndex'] in {k[2] for k in support}}
classes={'land':'mapped_land_support','inland-water':'mapped_inland_water_support'};owner_targets=collections.defaultdict(list);owner_coverage={}
for ident,t in targets.items():
 assert {k:v for k,v in t.items() if k!='coverage_rows'}=={k:v for k,v in fulltargets[ident].items() if k!='coverage_rows'};o=t['pixelIndex'];owner_targets[o].append(t)
 if 'coverage_rows' not in t:continue
 coverage=keys([{'y':r['y'],'runs':[[a,z,o,c] for a,z,c in r['runs']]} for r in t['coverage_rows']],True);assert set(coverage)=={k for k in support if k[2]==o} and all(c==classes[original[k]] for k,c in coverage.items());assert o not in owner_coverage or owner_coverage[o]==coverage;owner_coverage[o]=coverage
assert set(owner_targets)==set(owner_coverage)=={k[2] for k in support}
physical=read(P+'/physical-001/whole-target-support.json');physical_by={r['target']:r for r in physical['results']};assert len(physical_by)==len(physical['results'])==scope['source_members'];assert set(fulltargets)==set(physical_by)
oldconfig=read(P+'/config/source-evidence.json');newconfig=read(P+'/config/source-evidence-classed.json');assert {k:v for k,v in oldconfig.items() if k!='source_evidence'}=={k:v for k,v in newconfig.items() if k!='source_evidence'}
a,b=oldconfig['source_evidence'],newconfig['source_evidence'];assert {k:v for k,v in a.items() if k!='targets'}=={k:v for k,v in b.items() if k!='targets'} and len(a['targets'])==len(b['targets']);empty_corrections=[]
for old,new in zip(a['targets'],b['targets']):
 assert {k:v for k,v in old.items() if k!='coverage_classes'}=={k:v for k,v in new.items() if k!='coverage_classes'}
 expected=[]
 for kind in old['coverage_classes']:
  g=physical_by[old['id']]['support'][kind]
  if g=={'type':'GeometryCollection','geometries':[]}:empty_corrections.append((old['id'],kind))
  else:assert g['type'] in ['Polygon','MultiPolygon'] and g['coordinates'];expected.append(kind)
 assert expected==new['coverage_classes'] and expected
con=read(P+'/native-authority-001/constructor-result.json');rows=con['ledger_rows'];assert con['kind']=='existing-source-target-native-constructor-result' and len(rows)==len(owner_targets) and len({r['target_id'] for r in rows})==len(rows) and len({r['pixelIndex'] for r in rows})==len(rows) and all(r['disposition']=='assigned' for r in rows)
ak=keys([r for t in rows for r in t['native_rows']]);assert set(ak)==set(patch) and sum(t['native_cells'] for t in rows)==len(ak)
for t in rows:
 own=keys(t['native_rows']);atoms=owner_targets[t['pixelIndex']];assert len(own)==t['native_cells'] and all(k[2]==t['pixelIndex'] for k in own) and all(t['target_id']==a.get('target_id',a['id']) and t['base_geometry']==a['base_geometry'] for a in atoms)
for role,path in [('source_evidence',P+'/qualified-native-inputs-001/source-evidence.json'),('native_patch',P+'/qualified-native-inputs-001/native-patch.json')]:
 locator=con['inputs'][role];assert locator['path']==path;actual=read(locator['path'],locator['commit']);present=source if role=='source_evidence' else read(path);assert actual==present
by={r['pixelIndex']:r for r in scope['target_checks']};counts=collections.Counter(k[2] for k in original);sc=collections.Counter(k[2] for k in support);hc=collections.Counter(k[2] for k in held);assert len(by)==864 and set(by)==set(counts) and all(counts[o]==r['candidate_cells'] for o,r in by.items())
foreign={tuple(k) for f in context['foreign_natural_earth_hits'] for k in f['native_cells']}|{tuple(k) for k in scope['foreign_country_native_cells']};assert foreign<=set(held) and not foreign&set(support)
historicalkeys={tuple(k) for r in historical['native_overlap_rows'] for k in r['cells']};assert historicalkeys<=set(original) and len(historicalkeys)==historical['native_overlap_cells'];assert len({r['id'] for r in historical['native_overlap_rows']})==historical['native_overlap_candidates']
ownerrows=[{'owner':o,'id':by[o]['id'],'original_cells':counts[o],'supported_cells':sc[o],'held_cells':hc[o]} for o in sorted(counts)];assert ownerrows==partition['owner_counts']
aggregate_owners={o for o,r in by.items() if len(r['source_atoms'])>1};aggregatekeys={k for k in original if k[2] in aggregate_owners};assert len(aggregatekeys)==interpretation['aggregate_original_cells']
result={'version':1,'original_cells':len(original),'original_intervals':len(frozen),'original_owners':len(counts),'original_decoded_interval_sha256':sha((json.dumps(frozen,separators=(',',':'))+'\n').encode()),'supported_cells':len(support),'held_cells':len(held),'supported_owners':len(sc),'wholly_held_owners':len(set(counts)-set(sc)),'source_members':scope['source_members'],'aggregate_targets':len(aggregate_owners),'aggregate_source_members':sum(len(by[o]['source_atoms']) for o in aggregate_owners),'aggregate_cells':len(aggregatekeys),'complete_gb_source_features':scope['complete_source_feature_count'],'complete_catalogue_products':context['original_source_products'],'complete_catalogue_features':context['original_source_features'],'foreign_ownerless_features':context['foreign_ownerless_features'],'foreign_ownerless_candidate_cells':context['foreign_ownerless_candidate_cells'],'foreign_country_and_adm1_held_cells':len(foreign),'separate_physical_companion_cells':context['physical_companion']['native_cells'],'separate_physical_companion_owners':len(context['physical_companion']['owners']),'complete_historical_candidates':historical['complete_historical_candidates'],'historical_overlap_candidates':historical['native_overlap_candidates'],'historical_overlap_cells':len(historicalkeys),'historical_overlap_supported_cells':len(historicalkeys&set(support)),'historical_overlap_held_cells':len(historicalkeys&set(held)),'prior_nine_gap_overlap_cells':prior['nine_gap_native_contact_cells'],'prior_22_component_overlap_cells':prior['prior_22_native_contact_cells'],'complete_prior_sea_components':prior['complete_sea_components'],'complete_prior_sea_families':prior['complete_sea_families'],'whole_physical_issue_bearing_atoms':sum(bool(r['issues']) for r in physical['results']),'empty_positive_classes_removed':len(empty_corrections),'supported_physical_class_counts':dict(collections.Counter(original[k] for k in support)),'held_physical_class_counts':dict(collections.Counter(original[k] for k in held)),'held_reason_counts':dict(collections.Counter(held.values())),'exact_original_supported_held_partition':True,'exact_supported_patch_diagnostic_constructor_keys_equal':True,'all_source_physical_negative_inputs_unchanged':True,'owner_counts':ownerrows,'inputs':pins,'limits':['This source-relative constructor does not establish current selected owner-zero, final selected/emitted acceptance, contemporary legal boundaries or current dry land.','All five aggregate semantic decisions and complete prior whole-component/source-fitness limits remain open. Exact native contacts do not clear historical whole candidates.','The separate physical-interpretation companion remains uncredited. All original product-specific dates, licence terms and conflicts remain.','Only per-atom empty positive classes were corrected; complete physical results including every residual, whole source families, all 932 source atoms and exact original class rows are retained.']}
b=(json.dumps(result,separators=(',',':'))+'\n').encode();assert total+len(b)<=PHASE and len(b)<=MAX and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
with (O/'original-scope-disposition.json').open('xb') as f:f.write(b)
with (O/'preparation.json').open('x') as f:json.dump({'complete':True,'bytes':len(b),'sha256':sha(b)},f);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['inputs','owner_counts','limits']}))
