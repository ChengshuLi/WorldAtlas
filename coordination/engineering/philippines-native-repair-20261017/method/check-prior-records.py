"""Preserve actual Philippine prior record scopes and native applicability without replaying their operators.
Usage: python check-prior-records.py READ_ONLY_REPO FRESH_OUTPUT
"""
import collections,gzip,hashlib,io,json,os,pathlib,resource,subprocess,sys,time
import numpy as np,shapely
from shapely.geometry import shape
W,O=map(lambda v:pathlib.Path(v).absolute(),sys.argv[1:]);H='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';F='3545c11a0ad2d177672967e14dd2111b6df3883f';P='coordination/engineering/philippines-native-repair-20261017/'
assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents))
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

SEA='research/geography/southeast-asia-gap-batch-0393f64c-20261009/vintages/source-rule-fit-005/'
OLD='research/geography/philippines-ten-gap-family-source-fitness-20261007/'
NINE='coordination/engineering/shared-country-delivery-phl-20261010/vintages/phl-source-handoff-003/source-handoff.json'
fit=js(SEA+'administrative-source-rule-fit.json');states=js(SEA+'component-state-318.json');families=js(SEA+'family-roster-122.json');nine=js(NINE);candidates=js(OLD+'records/candidate-pointsets-22.json');assessments=js(OLD+'records/component-assessments.json');physical=js(OLD+'records/physical-comparison-rows-22.json');contacts=js(OLD+'records/contact-assessments.json');ten=js(OLD+'records/family-reconciliation.json');register=js(OLD+'inputs/source-register.json')
ids=[r['component_id'] for r in states['rows']];assert len(ids)==len(set(ids))==states['component_count'];familyids=[r['family_id'] for r in families['families']];assert len(familyids)==len(set(familyids))==families['family_count'];assert states['family_rows']==families['families'];assert set(ids)=={x for r in families['families'] for x in r['component_ids']}
caseids=[r['component_id'] for r in fit['cases']];assert len(caseids)==len(set(caseids))==states['priority_component_count'] and set(caseids)<=set(ids)
assert set(nine['scopeIds'])=={r['component_id'] for r in nine['candidate_source_native_bindings']}<=set(caseids) and len(nine['scopeIds'])==9
for p in nine['accepted_ledger_bindings']:
 b=read(p['path'],p['commit']);assert len(b)==p['bytes'] and sha(b)==p['sha256']
canon=lambda j:(json.dumps(j,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
for r in candidates['features']:
 assert sha(canon(r['feature']))==r['canonical_feature_sha256'] and sha(canon(r['feature']['geometry']))==r['canonical_geometry_sha256']
oldids={r['component_id'] for r in candidates['features']};assert len(oldids)==candidates['count']==22 and oldids=={r['component_id'] for r in assessments['components']}=={r['component'] for r in physical['records']}=={c for r in ten['families'] for c in r['component_ids']}
segments=[]
for b in range(28,32):segments+=js(P+f'frozen-queue/block-{b:03}.json.gz',F)
cells=[(x,y,o[0]) for y,a,z,o,ss,k in segments for x in range(a,z)];binding=js('coordination/engineering/global-current-cell-work-queue-20261014/ownership-binding.json');lp=binding['native_latitudes'];lat=np.frombuffer(read(lp['path'],lp['commit'],lp),dtype='<f8');points=shapely.points([[(x+.5)/262166*360-180,lat[y]] for x,y,o in cells]);tree=shapely.STRtree(points)
def overlap(f):
 g=shape(f['geometry']);assert g.is_valid;possible=tree.query(g);ix=possible[shapely.covers(g,points[possible])];return [[*cells[int(i)]] for i in sorted(ix)]
oldhits=[{'component_id':r['component_id'],'original_feature_sha256':r['canonical_feature_sha256'],'native_cells':overlap(r['feature'])} for r in candidates['features']]
ninehits=[{'component_id':r['component_id'],'native_cells':overlap(r['original_candidate_feature'])} for r in nine['candidate_source_native_bindings']]
result={'version':1,'original_repair_cells':len(cells),'complete_sea_components':len(ids),'complete_sea_families':len(familyids),'complete_sea_priority_cases':len(caseids),'complete_sea_other_cases':len(ids)-len(caseids),'all_prior_states_preserved':True,'nine_gap_scope_ids':nine['scopeIds'],'nine_gap_original_native_contacts':ninehits,'nine_gap_native_contact_cells':len({tuple(c) for r in ninehits for c in r['native_cells']}),'prior_ten_family_count':len(ten['families']),'prior_22_component_ids':sorted(oldids),'prior_22_native_contacts':oldhits,'prior_22_native_contact_cells':len({tuple(c) for r in oldhits for c in r['native_cells']}),'complete_prior_component_assessments':assessments,'complete_prior_contact_role_assessments':contacts,'complete_prior_family_reconciliation':ten,'complete_prior_source_register':register,'nine_handoff_unknowns':nine['unknowns'],'nine_constructor_disposition':nine['constructor_disposition'],'source_rule_fit_limits':fit['limitations'],'physical_status_counts':dict(collections.Counter(r['physical_status'] for r in assessments['components'])),'inputs':list(pins.values()),'processing_bytes':total,'elapsed_seconds':time.monotonic()-started,'limits':['This consumes complete retained products and source/physical rows as original evidence; it does not execute legacy extractors or validate their historical unsafe helper/runtime path.','Issue 1500 remains open for its recorded writer/admission/custody defects. Its older source fitness and unit-role limitations remain; a shared stock native rule does not close that issue.','All 318 states, 122 families and 30 prior source-fit cases remain unchanged; nine-gap and ten-family whole-component completion is separate from this exact native-centre repair.','A zero native contact is not water or a whole-gap completion. Original 2020 represented year, 2023 build/update dates, unknown observation/registration and unapproved current physical/legal authority remain separate.']}
body=(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n').encode();assert len(body)<=MAX and total+len(body)<=PHASE;assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
with (O/'prior-record-applicability.json').open('xb') as f:f.write(body)
with (O/'preparation.json').open('x') as f:json.dump({'complete':True,'bytes':len(body),'sha256':sha(body)},f);f.write('\n')
print(json.dumps({k:result[k] for k in ['complete_sea_components','complete_sea_families','complete_sea_priority_cases','complete_sea_other_cases','nine_gap_native_contact_cells','prior_22_native_contact_cells','processing_bytes','elapsed_seconds']}))
