"""Prove exact original, diagnostic, untouched patch and genuine constructor conservation.
Usage: python check-accounting.py READ_ONLY_REPO AUTHORITY_COMMIT FRESH_OUTPUT
"""
import collections,gzip,hashlib,io,json,os,pathlib,resource,subprocess,sys,time
assert len(sys.argv)==4
W=pathlib.Path(sys.argv[1]).absolute();H=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();P='coordination/engineering/new-zealand-native-repair-20261017/'
assert len(H)==40 and all(c in '0123456789abcdef' for c in H) and O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents))
pins={};total=0;MAX=64*1024*1024;PHASE=256*1024*1024;started=time.monotonic();sha=lambda b:hashlib.sha256(b).hexdigest();env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
def read(path,commit=H,expected=None):
 global total
 assert time.monotonic()-started<180 and path and not path.startswith('/') and all(x not in ['', '.', '..'] for x in path.split('/'))
 cmd=['git','-c','protocol.allow=never','-C',str(W)];meta,name=subprocess.check_output(cmd+['ls-tree','-z',commit,'--',path],env=env).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and name.decode()==path
 size=int(subprocess.check_output(cmd+['cat-file','-s',oid],env=env));assert 0<size<=MAX
 b=subprocess.check_output(cmd+['cat-file','blob',oid],env=env);assert len(b)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 pin={'path':path,'commit':commit,'mode':mode,'git_blob_oid':oid,'bytes':size,'sha256':sha(b)}
 if expected:assert size==expected['bytes'] and sha(b)==expected['sha256']
 if path.endswith('.gz'):
  with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:d=f.read(MAX+1)
  assert len(d)<=MAX;pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
  if expected:assert len(b)==expected['decoded_bytes'] and sha(b)==expected['decoded_sha256']
 if (commit,path) not in pins:total+=size+pin.get('decoded_bytes',0)
 assert total<=PHASE;pins[(commit,path)]=pin;return b
js=lambda p,h=H:json.loads(read(p,h))

def keys(rows,reason=False):
 out={}
 for r in rows:
  for run in r['runs']:
   assert len(run)==(4 if reason else 3);a,z,o=run[:3];assert all(type(v)==int for v in [r['y'],a,z,o]) and 0<=a<z<=262166 and 0<=r['y']<262166 and o>0
   for x in range(a,z):
    k=(x,r['y'],o);assert k not in out;out[k]=run[3] if reason else None
 return out
frozen=[]
for b in range(38,42):frozen+=js(P+f'frozen-queue/block-{b:03}.json.gz')
original={(x,y,o[0]):kind for y,a,z,o,s,kind in frozen for x in range(a,z)};assert len(original)==56626==sum(z-a for y,a,z,*_ in frozen) and len(frozen)==17520
scope=js(P+'source-stage/source-scope-assessment.json');context=js(P+'context-001/complete-context.json');continuity=js(P+'context-001/census-ownership-continuity.json');historical=js(P+'historical-001/historical-applicability.json');prior=js(P+'prior-001/prior-island-applicability.json');interpretation=js(P+'interpretation-001/construction-and-source-limits.json');diag=js(P+'native-diagnostic-001/native-diagnostic.json');source=js(P+'native-inputs-001/source-evidence.json');patch=js(P+'source-stage/native-patch.json');physical=js(P+'physical-001/whole-target-support.json');con=js(P+'native-authority-001/constructor-result.json')
requested=keys(diag['requested_rows']);supported=keys(diag['supported_rows']);held=keys(diag['held_rows'],True);decisions=keys(diag['decision_rows'],True);patchkeys=keys(patch['rows']);priorholds={tuple(k) for k in prior['source_fitness_hold_keys']};assert len(priorholds)==prior['source_fitness_hold_cells'] and not priorholds
assert set(requested)==set(original)==set(supported)==set(patchkeys)==set(decisions) and not held and all(r=='assigned_cells' for r in decisions.values()) and len(supported)==diag['supported_cells'] and len(held)==diag['held_cells']
sourcepin=next(p for p in pins.values() if p['path']==P+'native-inputs-001/source-evidence.json');assert all(sourcepin[k]==diag['original_pins']['source_evidence'][k] for k in ['path','bytes','sha256','git_blob_oid'])
by={r['pixelIndex']:r for r in scope['target_checks']};counts=collections.Counter(k[2] for k in original);assert len(by)==70 and set(by)==set(counts) and all(r['source_atoms']==[r['id']] and counts[o]==r['candidate_cells'] for o,r in by.items())
targets={t['id']:t for t in source['targets']};assert len(targets)==len(source['targets'])==scope['source_members']==len(by);physical_by={r['target']:r for r in physical['results']};assert set(physical_by)==set(targets) and len(physical_by)==len(physical['results'])
for t in targets.values():
 o=t['pixelIndex'];assert t['id']==t['target_id']==by[o]['id'];coverage=keys([{'y':r['y'],'runs':[[a,z,o,c] for a,z,c in r['runs']]} for r in t['coverage_rows']],True);assert set(coverage)=={k for k in original if k[2]==o} and all(c=='mapped_land_support' and original[k]=='land' for k,c in coverage.items())
 assert t['coverage_classes']==['mapped_land_support'] and physical_by[t['id']]['support']['mapped_land_support']['type'] in ['Polygon','MultiPolygon']
rows=con['ledger_rows'];assert con['kind']=='existing-source-target-native-constructor-result' and len(rows)==len(by) and len({r['target_id'] for r in rows})==len(rows) and len({r['pixelIndex'] for r in rows})==len(rows) and all(r['disposition']=='assigned' for r in rows)
actual=keys([r for t in rows for r in t['native_rows']]);assert set(actual)==set(original) and sum(t['native_cells'] for t in rows)==len(actual)
for r in rows:
 own=keys(r['native_rows']);t=targets[r['target_id']];assert len(own)==r['native_cells']==counts[r['pixelIndex']] and all(k[2]==r['pixelIndex'] for k in own) and t['pixelIndex']==r['pixelIndex'] and t['base_geometry']==r['base_geometry']
for role,path,present in [('source_evidence',P+'native-inputs-001/source-evidence.json',source),('native_patch',P+'source-stage/native-patch.json',patch)]:
 loc=con['inputs'][role];assert loc['path']==path and js(path,loc['commit'])==present
foreign={tuple(k) for f in context['foreign_natural_earth_hits'] for k in f['native_cells']}|{tuple(k) for k in scope['foreign_country_native_cells']};assert not foreign and continuity['foreign_ownerless_features']==context['foreign_ownerless_features'] and continuity['all_roster_owners_rederived_from_complete_lineage']
historicalkeys={tuple(k) for r in historical['native_overlap_rows'] for k in r['cells']};assert historicalkeys<=set(original) and len(historicalkeys)==historical['native_overlap_cells'];ownerrows=[{'owner':o,'id':by[o]['id'],'original_cells':counts[o],'supported_cells':counts[o],'held_cells':0} for o in sorted(counts)]
role_counts=collections.Counter(r['metadata']['source_role'] for r in by.values());role_cells=collections.Counter()
for o,r in by.items():role_cells[r['metadata']['source_role']]+=counts[o]
assert dict(role_counts)==interpretation['source_role_counts'] and dict(role_cells)==interpretation['source_role_original_cells']
result={'version':1,'original_cells':len(original),'original_intervals':len(frozen),'original_owners':len(counts),'supported_cells':len(supported),'held_cells':len(held),'supported_owners':len(counts),'wholly_held_owners':0,'source_members':len(targets),'complete_gb_source_features':scope['complete_source_feature_count'],'complete_catalogue_products':context['original_source_products'],'complete_catalogue_features':context['original_source_features'],'foreign_ownerless_features':context['foreign_ownerless_features'],'foreign_ownerless_candidate_cells':context['foreign_ownerless_candidate_cells'],'foreign_country_and_adm1_held_cells':len(foreign),'separate_physical_companion_cells':context['physical_companion']['native_cells'],'separate_physical_companion_owners':len(context['physical_companion']['owners']),'complete_historical_candidates':historical['complete_historical_candidates'],'historical_overlap_candidates':historical['native_overlap_candidates'],'historical_overlap_cells':len(historicalkeys),'historical_overlap_supported_cells':len(historicalkeys),'historical_overlap_held_cells':0,'historical_overlap_without_domestic_tags':sum(not('gb:NZL:' in r['routing']['source_products'] or 'gb:NZL:' in r['routing']['unique_source_subject_id']) for r in historical['native_overlap_rows']),'prior_island_source_components':prior['complete_original_source_components_screened'],'prior_island_native_contacts':prior['source_fitness_hold_cells'],'whole_physical_issue_bearing_atoms':sum(bool(r['issues']) for r in physical['results']),'source_role_counts':dict(role_counts),'source_role_original_cells':dict(role_cells),'recorded_name_encoding_corrections':len(interpretation['recorded_encoding_corrections']),'supported_physical_class_counts':dict(collections.Counter(original.values())),'held_physical_class_counts':{},'held_reason_counts':{},'exact_original_supported_held_partition':True,'exact_original_patch_diagnostic_constructor_keys_equal':True,'original_source_and_patch_consumed_without_rewrite':True,'owner_counts':ownerrows,'inputs':list(pins.values()),'limits':['All 56626 original keys are conserved with all 70 owners; source-relative authority is not selected/current-owner-zero or emitted delivery acceptance.','Direct original source roles, open Auckland city/local-board and offshore-residual parent questions, all whole-physical issues, original source vintages/terms and GSHHG wording conflict remain.','All earlier historical whole-candidate unknowns and Bounty/Nukunonu source-fitness disagreements remain; exact-centre absence from those complete prior source families does not clear their original subjects.','The separate physical-interpretation companion is outside repair credit. No redundant supported-only copy of unchanged whole source evidence or patch is introduced.']}
body=(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n').encode();assert len(body)<=MAX and total+len(body)<=PHASE;assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
with (O/'original-scope-disposition.json').open('xb') as f:f.write(body)
with (O/'preparation.json').open('x') as f:json.dump({'complete':True,'bytes':len(body),'sha256':sha(body)},f);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['inputs','owner_counts','limits']}))
