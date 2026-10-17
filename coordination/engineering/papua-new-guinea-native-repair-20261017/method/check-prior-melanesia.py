"""Authenticate complete prior 363-component Melanesia outcomes and exact PNG applicability.
Usage: python check-prior-melanesia.py READ_ONLY_REPO FRESH_OUTPUT
Preserve all whole candidates, supported source fragments, literal remainders and held cases.
"""
import collections,gzip,hashlib,io,json,os,pathlib,resource,subprocess,sys,time
import numpy as np,shapely
from shapely.geometry import shape
W,O=map(lambda v:pathlib.Path(v).absolute(),sys.argv[1:]);H='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';F='1a6a08cb722ab344a71640f47af38490f7df4577';P='coordination/engineering/papua-new-guinea-native-repair-20261017/'
assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents))
pins={};total=0;started=time.monotonic();sha=lambda b:hashlib.sha256(b).hexdigest();env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
def read(path,commit=H,expected=None):
 global total
 assert time.monotonic()-started<180 and path and not path.startswith('/') and all(x not in ['', '.', '..'] for x in path.split('/'))
 cmd=['git','-c','protocol.allow=never','-C',str(W)];meta,name=subprocess.check_output(cmd+['ls-tree','-z',commit,'--',path],env=env).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and name.decode()==path
 size=int(subprocess.check_output(cmd+['cat-file','-s',oid],env=env));assert size>0
 b=subprocess.check_output(cmd+['cat-file','blob',oid],env=env);assert len(b)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 pin={'path':path,'commit':commit,'mode':mode,'git_blob_oid':oid,'bytes':size,'sha256':sha(b)}
 if expected:assert size==expected['bytes'] and sha(b)==expected['sha256']
 if path.endswith('.gz'):
  with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:d=f.read()
  pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
  if expected:assert len(b)==expected['decoded_bytes'] and sha(b)==expected['decoded_sha256']
 if (commit,path) not in pins:total+=size+pin.get('decoded_bytes',0)
 pins[(commit,path)]=pin;return b
js=lambda p,h=H:json.loads(read(p,h))

R='research/geography/melanesia-gap-batch-37ed51b2-20261009/';original='2bbc1ce28a5c6995be10a70e79b4f872b94e69e5';documents={};identity=[]
for role,path in [('scope','inputs/assignment-scope.json'),('outcomes','vintages/batch-outcomes-363-002/batch-outcomes-363-v2.json'),('comparisons','vintages/source-comparison-capture-001/batch-source-comparisons.json'),('remainders','vintages/source-remainders-084-001/source-remainders-084.json'),('payloads','vintages/native-payloads-110-001/native-payloads-110.json')]:
 old=read(R+path,original);current=read(R+path);assert old==current;documents[role]=json.loads(old);identity.append({'path':R+path,'original_source_commit':original,'current_commit':H,'whole_body_equal':True})
scope=documents['scope']['batch'];outcomes=documents['outcomes'];comparisons=documents['comparisons'];remainders=documents['remainders'];payloads=documents['payloads'];ids=set(scope['complete_component_ids']);cases={r['component_id']:r for r in outcomes['cases']};comp={r['component_id']:r for r in comparisons['cases']};pay={r['component_id']:r for r in payloads['additive_payloads']}
assert len(ids)==scope['component_count']==len(cases)==len(outcomes['cases'])==len(comp)==len(comparisons['cases'])==363 and set(cases)==set(comp)==ids
assert len(pay)==len(payloads['additive_payloads'])==outcomes['source_supported_payload_count']==110 and set(pay)<=ids
full={k for k,r in cases.items() if r['whole_candidate_source_coverage']['status'].startswith('complete-exact')};partial={k for k,r in cases.items() if r['whole_candidate_source_coverage']['status'].startswith('partial-')};held=ids-set(pay);assert full|partial==set(pay) and not(full&partial) and len(full)==41 and len(partial)==69 and len(held)==253
rem={r['component_id']:r for key in ['geoBoundaries_partial_remainders','NCL_partial_remainders'] for r in remainders[key]};assert set(rem)==partial and len(rem)==69
canonical=lambda v:sha((json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode())
segments=[]
for b in range(32,35):segments+=js(P+f'frozen-queue/block-{b:03}.json.gz',F)
cells=[(x,y,o[0]) for y,a,z,o,s,k in segments for x in range(a,z)];assert len(cells)==56552
binding=js('coordination/engineering/global-current-cell-work-queue-20261014/ownership-binding.json');lp=binding['native_latitudes'];lat=np.frombuffer(read(lp['path'],lp['commit']),dtype='<f8');assert pins[(lp['commit'],lp['path'])]['decoded_sha256']==lp['decoded_sha256'];points=shapely.points([[(x+.5)/262166*360-180,lat[y]] for x,y,o in cells]);tree=shapely.STRtree(points);invalid=[]
def contacts(geometry,label):
 if geometry is None:return set()
 g=shape(geometry);ix=tree.query(g)
 if not g.is_valid:
  invalid.append({'operand':label,'geometry_sha256':canonical(geometry),'candidate_bound_contacts':[list(cells[int(i)]) for i in ix]});assert not len(ix),'Invalid prior geometry reaches exact original support bounds';return set()
 return {cells[int(i)] for i in ix[shapely.covers(g,points[ix])]}
rows=[];sets={k:set() for k in ['whole','full','partial','held','supported_fragments','remainders','source_fitness_holds']}
for ident in scope['complete_component_ids']:
 r=cases[ident];candidate=r['candidate_feature'];assert candidate['id']==ident and canonical(candidate)==r['candidate_feature_sha256'] and canonical(candidate['geometry'])==r['candidate_geometry_sha256'];assert comp[ident]['candidate_geometry_sha256']==r['candidate_geometry_sha256'];whole=contacts(candidate['geometry'],ident+':whole');kind='full' if ident in full else 'partial' if ident in partial else 'held';sets['whole']|=whole;sets[kind]|=whole;supported=set();unresolved=set();fragment_rows=[]
 if ident in pay:
  p=pay[ident];assert p['candidate_geometry_sha256']==r['candidate_geometry_sha256'] and p['candidate_feature']==candidate and p['unsupported_candidate_remainder_included'] is False
  for i,fragment in enumerate(p['source_supported_intersection_fragments']):
   contact=contacts(fragment['intersection_geometry'],ident+':supported-fragment:'+str(i));assert contact<=whole;supported|=contact;fragment_rows.append({'ordinal':i,'geometry_sha256':canonical(fragment['intersection_geometry']),'native_cells':[list(k) for k in sorted(contact)],'original_fragment':fragment})
  sets['supported_fragments']|=supported
 if ident in partial:
  rr=rem[ident];assert rr['candidate_geometry_sha256']==r['candidate_geometry_sha256'];operand=rr.get('candidate_minus_retained_source_union',rr.get('candidate_minus_retained_source_feature'));assert operand['is_empty'] is False and operand['geometry'] is not None
  if 'geometry_sha256' in operand:assert canonical(operand['geometry'])==operand['geometry_sha256']
  unresolved=contacts(operand['geometry'],ident+':literal-remainder');assert unresolved<=whole;sets['remainders']|=unresolved;assert whole<=supported|unresolved
 holds=whole if ident in held else unresolved;sets['source_fitness_holds']|=holds
 rows.append({'component_id':ident,'prior_class':kind,'prior_outcome':r['outcome'],'whole_native_cells':[list(k) for k in sorted(whole)],'supported_fragment_native_cells':[list(k) for k in sorted(supported)],'literal_remainder_native_cells':[list(k) for k in sorted(unresolved)],'provisional_source_fitness_hold_keys':[list(k) for k in sorted(holds)],'complete_original_outcome':r,'complete_original_comparison':comp[ident],'complete_original_payload':pay.get(ident),'complete_original_remainder':rem.get(ident),'fragment_contacts':fragment_rows})
result={'version':1,'original_cells':len(cells),'complete_prior_components':len(ids),'complete_prior_full_cases':len(full),'complete_prior_partial_cases':len(partial),'complete_prior_held_cases':len(held),'complete_prior_payloads':len(pay),'complete_prior_literal_nonempty_remainders':len(rem),'original_current_body_identity':identity,'original_scope':documents['scope'],'original_outcome_counts':outcomes['coverage_counts'],'original_source_and_method_limits':{role:doc.get('limits',[]) for role,doc in documents.items()},'whole_contact_components':sum(bool(r['whole_native_cells']) for r in rows),'contact_counts':{k:len(v) for k,v in sets.items()},'source_fitness_hold_keys':[list(k) for k in sorted(sets['source_fitness_holds'])],'source_fitness_hold_cells':len(sets['source_fitness_holds']),'component_rows':rows,'invalid_prior_operands':invalid,'inputs':list(pins.values()),'limits':['The complete 363-component research packet is source-relative and does not approve whole-current-source fitness, current jurisdiction, dry land or contemporary boundaries.','All 41 full-source cases, 69 partial cases and literal remainders, 253 holds and 110 supported payloads remain distinct. Specific held or unsupported remainder contacts are conservatively retained as provisional exact-key source-fitness holds.','Generic unknown effective dates/current truth and separate invalid generalized New Caledonia geometry do not create a whole-PNG veto. No new original source overlay or old native producer is executed.','Issue 1647 closure superseded the fixed polygon delivery workflow and directed current-cell family sessions; it did not erase original 363/327 holds or remainders. The separately denominated 327 scope remains separate, and no new disposition or repair credit is claimed for it.','Original PNG full cases 011/034/035 and historical native diagnostics remain historical evidence, not present selected gain.']}
body=(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n').encode();assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
with (O/'prior-melanesia-applicability.json').open('xb') as f:f.write(body)
with (O/'preparation.json').open('x') as f:json.dump({'complete':True,'bytes':len(body),'sha256':sha(body)},f);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k in ['original_cells','complete_prior_components','complete_prior_full_cases','complete_prior_partial_cases','complete_prior_held_cases','complete_prior_literal_nonempty_remainders','whole_contact_components','contact_counts','source_fitness_hold_keys','source_fitness_hold_cells']}))
