"""Authenticate full original/supported/held/native constructor conservation.
Usage: python check-accounting.py READ_ONLY_REPO AUTHORITY_COMMIT FRESH_OUTPUT
"""
import collections,gzip,hashlib,io,json,os,pathlib,subprocess,sys
assert len(sys.argv)==4
W=pathlib.Path(sys.argv[1]).absolute();H=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();P='coordination/engineering/papua-new-guinea-native-repair-20261017'
assert len(H)==40 and all(c in '0123456789abcdef' for c in H) and O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents))
sha=lambda b:hashlib.sha256(b).hexdigest();pins=[];total=0;env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
def read(p,c=H):
 global total
 assert p and not p.startswith('/') and all(x not in ['', '.', '..'] for x in p.split('/'))
 cmd=['git','-c','protocol.allow=never','-C',str(W)];meta,name=subprocess.check_output(cmd+['ls-tree','-z',c,'--',p],env=env).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and name.decode()==p
 n=int(subprocess.check_output(cmd+['cat-file','-s',oid],env=env));assert n>0;b=subprocess.check_output(cmd+['cat-file','blob',oid],env=env);assert len(b)==n and hashlib.sha1(b'blob '+str(n).encode()+b'\0'+b).hexdigest()==oid
 pin={'commit':c,'path':p,'mode':mode,'git_blob_oid':oid,'bytes':n,'sha256':sha(b)}
 if p.endswith('.gz'):
  with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:d=f.read()
  pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
 total+=n+pin.get('decoded_bytes',0);pins.append(pin);return json.loads(b)
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
for b in range(32,35):frozen+=read(P+f'/frozen-queue/block-{b:03}.json.gz')
original={(x,y,o[0]):kind for y,a,z,o,s,kind in frozen for x in range(a,z)};assert len(original)==56552==sum(z-a for y,a,z,*_ in frozen) and len(frozen)==20060
scope=read(P+'/source-stage/source-scope-assessment.json');context=read(P+'/context-001/complete-context.json');historical=read(P+'/historical-001/historical-applicability.json');prior=read(P+'/prior-001/prior-melanesia-applicability.json');partition=read(P+'/qualified-native-inputs-002/original-scope-partition.json');interpretation=read(P+'/interpretation-001/construction-and-source-limits.json')
diag=read(P+'/native-diagnostic-001/native-diagnostic.json');support=keys(diag['supported_rows']);dh={k:r for k,r in keys(diag['decision_rows'],True).items() if r!='assigned_cells'};assert set(dh)==set(keys(diag['held_rows']));requested=keys(diag['requested_rows']);assert set(requested)==set(original) and not(set(support)&set(dh)) and set(support)|set(dh)==set(requested)
diagnostic_support=set(support)
review=read(P+'/qualified-native-inputs-002/prior-source-fitness-holds.json');review_keys={tuple(k) for k in review['original_keys']}
prior_keys={tuple(k) for r in prior['component_rows'] for k in r['provisional_source_fitness_hold_keys']};assert review_keys==prior_keys and len(review_keys)==prior['source_fitness_hold_cells']
components={r['component_id']:r for r in prior['component_rows']}
for r in review['components']:
 a=components[r['component_id']];assert r['complete_original_outcome']==a['complete_original_outcome'] and r['complete_original_comparison']==a['complete_original_comparison'] and r['complete_original_remainder']==a['complete_original_remainder'] and a['prior_class']=='held'
assert review_keys<=diagnostic_support and not review_keys&set(dh)
held=keys(read(P+'/qualified-native-inputs-002/held-original.json')['rows'],True);patch=keys(read(P+'/qualified-native-inputs-002/native-patch.json')['rows']);assert set(patch)==diagnostic_support-review_keys and held=={**dh,**{k:'unresolved_prior_source_fitness' for k in review_keys}} and not(set(patch)&set(held)) and set(patch)|set(held)==set(original)
assert len(diagnostic_support)==diag['supported_cells'] and len(dh)==diag['held_cells'] and len(patch)==partition['supported_cells'] and len(held)==partition['held_cells']
support={k:v for k,v in support.items() if k not in review_keys}
decisions=keys(diag['decision_rows'],True);assert set(decisions)==set(requested) and {k for k,r in decisions.items() if r=='assigned_cells'}==diagnostic_support and all(held[k]==decisions[k] for k in dh)
source=read(P+'/qualified-compaction-001/source-evidence.json');fullsource=read(P+'/compaction-001/source-evidence.json');assert {k:v for k,v in source.items() if k!='targets'}=={k:v for k,v in fullsource.items() if k!='targets'}
fulltargets={t['id']:t for t in fullsource['targets']};targets={t['id']:t for t in source['targets']};assert len(targets)==len(source['targets']) and set(targets)=={t['id'] for t in fullsource['targets'] if t['pixelIndex'] in {k[2] for k in support}}
classes={'land':'mapped_land_support','inland-water':'mapped_inland_water_support'};owner_targets=collections.defaultdict(list);owner_coverage={}
for ident,t in targets.items():
 assert {k:v for k,v in t.items() if k!='coverage_rows'}=={k:v for k,v in fulltargets[ident].items() if k!='coverage_rows'};o=t['pixelIndex'];owner_targets[o].append(t)
 if 'coverage_rows' not in t:continue
 coverage=keys([{'y':r['y'],'runs':[[a,z,o,c] for a,z,c in r['runs']]} for r in t['coverage_rows']],True);assert set(coverage)=={k for k in support if k[2]==o} and all(c==classes[original[k]] for k,c in coverage.items());assert o not in owner_coverage or owner_coverage[o]==coverage;owner_coverage[o]=coverage
assert set(owner_targets)==set(owner_coverage)=={k[2] for k in support}
physical=read(P+'/physical-001/whole-target-support.json');physical_by={r['target']:r for r in physical['results']};assert len(physical_by)==len(physical['results'])==scope['source_members'];assert set(fulltargets)==set(physical_by)
con=read(P+'/native-authority-001/constructor-result.json');rows=con['ledger_rows'];assert con['kind']=='existing-source-target-native-constructor-result' and len(rows)==len(owner_targets) and len({r['target_id'] for r in rows})==len(rows) and len({r['pixelIndex'] for r in rows})==len(rows) and all(r['disposition']=='assigned' for r in rows)
ak=keys([r for t in rows for r in t['native_rows']]);assert set(ak)==set(patch) and sum(t['native_cells'] for t in rows)==len(ak)
for t in rows:
 own=keys(t['native_rows']);atoms=owner_targets[t['pixelIndex']];assert len(own)==t['native_cells'] and all(k[2]==t['pixelIndex'] for k in own) and all(t['target_id']==a.get('target_id',a['id']) and t['base_geometry']==a['base_geometry'] for a in atoms)
for role,path in [('source_evidence',P+'/qualified-compaction-001/source-evidence.json'),('native_patch',P+'/qualified-native-inputs-002/native-patch.json')]:
 locator=con['inputs'][role];assert locator['path']==path.replace('qualified-native-inputs-002','qualified-native-inputs-001');actual=read(locator['path'],locator['commit']);present=source if role=='source_evidence' else read(path);assert actual==present
by={r['pixelIndex']:r for r in scope['target_checks']};counts=collections.Counter(k[2] for k in original);sc=collections.Counter(k[2] for k in support);hc=collections.Counter(k[2] for k in held);assert len(by)==130 and set(by)==set(counts) and all(counts[o]==r['candidate_cells'] for o,r in by.items())
foreign={tuple(k) for f in context['foreign_natural_earth_hits'] for k in f['native_cells']}|{tuple(k) for k in scope['foreign_country_native_cells']}|{tuple(k) for k in scope['foreign_original_source_native_cells']};assert foreign==set(dh) and foreign<=set(held) and not foreign&set(support)
historicalkeys={tuple(k) for r in historical['native_overlap_rows'] for k in r['cells']};assert historicalkeys<=set(original) and len(historicalkeys)==historical['native_overlap_cells'];assert len({r['id'] for r in historical['native_overlap_rows']})==historical['native_overlap_candidates']
ownerrows=[{'owner':o,'id':by[o]['id'],'original_cells':counts[o],'supported_cells':sc[o],'held_cells':hc[o]} for o in sorted(counts)];assert ownerrows==partition['owner_counts']
equivalence=read(P+'/compaction-001/whole-negative-equivalence.json')
result={'version':1,'original_cells':len(original),'original_intervals':len(frozen),'original_owners':len(counts),'original_decoded_interval_sha256':sha((json.dumps(frozen,separators=(',',':'))+'\n').encode()),'supported_cells':len(support),'held_cells':len(held),'native_diagnostic_supported_cells':len(diagnostic_support),'native_diagnostic_held_cells':len(dh),'prior_source_fitness_held_cells':len(review_keys),'supported_owners':len(sc),'wholly_held_owners':len(set(counts)-set(sc)),'source_members':scope['source_members'],'complete_gb_source_features':scope['complete_source_feature_count'],'complete_foreign_source_features':scope['complete_foreign_source_feature_count'],'complete_catalogue_products':context['original_source_products'],'complete_catalogue_features':context['original_source_features'],'foreign_ownerless_features':context['foreign_ownerless_features'],'foreign_ownerless_candidate_cells':context['foreign_ownerless_candidate_cells'],'foreign_country_original_and_adm1_held_cells':len(foreign),'separate_physical_companion_cells':context['physical_companion']['native_cells'],'separate_physical_companion_owners':len(context['physical_companion']['owners']),'complete_historical_candidates':historical['complete_historical_candidates'],'historical_overlap_candidates':historical['native_overlap_candidates'],'historical_overlap_cells':len(historicalkeys),'historical_overlap_supported_cells':len(historicalkeys&set(support)),'historical_overlap_held_cells':len(historicalkeys&set(held)),'complete_prior_components':prior['complete_prior_components'],'complete_prior_literal_nonempty_remainders':prior['complete_prior_literal_nonempty_remainders'],'whole_physical_issue_bearing_atoms':sum(bool(r['issues']) for r in physical['results']),'original_negative_operands':equivalence['original_operands'],'retained_negative_operands':equivalence['retained_operands'],'proven_disjoint_negative_operands':equivalence['omitted_whole_disjoint_operands'],'supported_physical_class_counts':dict(collections.Counter(original[k] for k in support)),'held_physical_class_counts':dict(collections.Counter(original[k] for k in held)),'held_reason_counts':dict(collections.Counter(held.values())),'exact_original_supported_held_partition':True,'exact_supported_patch_review_filtered_diagnostic_constructor_keys_equal':True,'all_positive_source_physical_inputs_unchanged':True,'whole_negative_equivalence_verified_by_supported_writer':True,'owner_counts':ownerrows,'inputs':pins,'limits':['This source-relative constructor does not establish current selected owner-zero, final selected/emitted acceptance, contemporary legal boundaries or current dry land.','All 130 source construction and semantic limits, complete prior mixed-source-support and numeric-closure questions remain. Exact native contacts do not clear historical whole candidates.','The separate physical-interpretation companion remains uncredited. Product dates, licences, source disagreements and every original interval are retained.','All complete positive source/physical fields remain. Only source-proven supported coverage survives; negative omission is independently proven against complete original, selected and original mask bounds.']}
b=(json.dumps(result,separators=(',',':'))+'\n').encode();assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
with (O/'original-scope-disposition.json').open('xb') as f:f.write(b)
with (O/'preparation.json').open('x') as f:json.dump({'complete':True,'bytes':len(b),'sha256':sha(b)},f);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['inputs','owner_counts','limits']}))
