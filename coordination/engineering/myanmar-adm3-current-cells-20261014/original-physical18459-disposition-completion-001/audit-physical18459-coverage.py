from pathlib import Path
import json,gzip,hashlib,collections
w=Path.cwd();d=w/'.takeover/original-package-completion-audit';p=w/'.takeover/public';key=lambda r:tuple(r['original_key'][k]for k in ['owner','y','x'])
def load(path):
 raw=Path(path).read_bytes();raw=gzip.decompress(raw)if str(path).endswith('.gz')else raw
 try:return json.loads(raw)
 except json.JSONDecodeError:return[json.loads(l)for l in raw.splitlines()]
def fact(path):
 b=Path(path).read_bytes();return {'local_retained_path':str(Path(path).relative_to(w)),'bytes':len(b),'git_blob_oid':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest(),'sha256':hashlib.sha256(b).hexdigest()}
original=load(p/'original-remaining-intervals.json.gz');scope=next(x for x in original['packages']if x['package_id']=='gb-MMR-ADM3--physical-interpretation')['rows'];assert len(scope)==9162
bykey={}
for ordinal,row in enumerate(scope):
 y,start,end,owners,sids,kind=row;assert len(owners)==1 and kind=='source-relative'
 for x in range(start,end):
  k=(owners[0],y,x);assert k not in bykey;bykey[k]={'original_interval_ordinal':ordinal,'original_interval':row}
assert len(bykey)==18459
answers={};sources=[]
def add(name,rows,path,extract=key):
 keys=[extract(r)for r in rows];assert len(keys)==len(set(keys));assert set(keys)<=bykey.keys();assert not set(keys)&answers.keys(),name
 for k in keys:answers[k]=name
 sources.append({'group':name,'keys':len(keys),'body':fact(path)})
add('known2237',load(p/'reused-known2237.jsonl.gz'),p/'reused-known2237.jsonl.gz')
for name in ['2-adopted-annual-body-location-answers.jsonl.gz','5-adopted-annual-wetland-body-location-answers.jsonl.gz','7-adopted-mixed-wetland-body-margin-answers185.jsonl.gz','8-adopted-annual-wetland-edge63.jsonl.gz','9-proposed-dated-surface-answers.jsonl.gz','pmn-answers.jsonl.gz','pln-answers.jsonl.gz','pmq-answers.jsonl.gz']:
 add(name,load(p/name),p/name)
x=load(p/'6-adopted-dated-canopy12.json');add('dated12',x['proposals'],p/'6-adopted-dated-canopy12.json',lambda r:key(r['original_open_row']))
x=load(p/'4-main-four-edge-adoption.json');add('edge4',x['adopted_answers'],p/'4-main-four-edge-adoption.json')
pmp=(30271,121814,202666);assert 'exact original key8082 at (30271,121814,202666)'in load(p/'pmp-adoption.json')['judgment'];add('retainedPMP1',[{'original_key':dict(zip(['owner','y','x'],pmp))}],p/'pmp-adoption.json')
assert len(answers)==17384
old=load(p/'physical-disposition-inventory-private.json');oldkeys={}
for interval in old['intervals']:
 row=interval['original_interval'];assert row==scope[interval['original_interval_ordinal']]
 for s in interval['dispositions']:
  if s['status']=='bounded-adopted-source-interpretation':
   for x in range(s['start'],s['end']):oldkeys[(row[3][0],row[0],x)]=s['source_group']
assert answers.keys()==oldkeys.keys()
extra=load(p/'exact-private17503-and-proposed576.json');p98=w/'.takeover/local-recovery/.cache/worker1-mmr-bulk-physical-20261015-001/pmm138-publication-preparation-010/payload/proposed-retained-dated-surface98.jsonl.gz';r98=load(p98);assert set(map(key,r98))==set(map(tuple,extra['pmm98_keys']));add('publicPMM98',r98,p98)
p576=w/'.takeover/annual576-publication/payload/proposed-retained-annual-body-margin576.jsonl.gz';r576=load(p576);assert set(map(key,r576))==set(map(tuple,extra['proposed576_keys']));add('publicAnnual576',r576,p576)
a107=load(w/'.takeover/dated107-publication/payload/exact107-union-and294-remainder.json');k107=a107['new_Jan25_prior_adopted21_keys']+a107['new_cloud_adopted_Bokpyin86_keys'];add('publicDated107',[{'original_key':dict(zip(['owner','y','x'],r))}for r in k107],w/'.takeover/dated107-publication/payload/exact107-union-and294-remainder.json');assert len(answers)==18165
heldpath=w/'.takeover/dated107-publication/payload/remaining-original294-specific-questions.jsonl.gz';held=load(heldpath);assert len(held)==294 and len(set(map(key,held)))==294;assert set(map(key,held))==bykey.keys()-answers.keys()
oldopen=load(p/'3-open-physical-questions.jsonl.gz');oldopenmap={key(r):(i,r)for i,r in enumerate(oldopen)};rows=[]
for r in held:
 k=key(r);i,source=oldopenmap[k];saved=r['unchanged_original_question_record'];assert key(saved)==k
 assert saved['original_record_unchanged']==source['original_record_unchanged']
 
 def projected_observation(value):
  value=dict(value)
  if 'centre_array'in value:
   path=value['centre_array']
   for prefix in ['/Users/chengshuli/Documents/Codex/2026-10-14/task-2/','retained-private:']:
    if path.startswith(prefix):path=path[len(prefix):];break
   assert path.startswith('.cache/worker1-mmr-bulk-physical-20261015-001/worldcover-native-001/')
   value['centre_array']=path
  return value
 assert projected_observation(saved['source_observation'])==projected_observation(source['source_observation'])
 assert saved['positive_original_source_body_association']==source['positive_original_source_body_association']
 assert saved['original_record_unchanged']['original_interval']==bykey[k]['original_interval']
 assert source['original_record_unchanged']['original_owners']==[k[0]]and source['original_record_unchanged']['original_SIDs']==bykey[k]['original_interval'][4]
 question=source['remaining_physical_question'];assert isinstance(question,str)and question.strip()
 precise=r['remaining_specific_question']if isinstance(r['remaining_specific_question'],str)else None
 rows.append({'original_key':r['original_key'],**bykey[k],'original_open3455_line_zero_based':i,'original_source_question':question,'current_precise_annual_question':precise,'historical_reservation_label':r['remaining_specific_question']if precise is None else None,'source_observation':source['source_observation'],'positive_original_body_association':source['positive_original_source_body_association'],'source_year':source['source_year'],'body_source_year':2019,'disposition':'evidence-backed-unresolved-physical-question','adopted_new_positive_facet':False})
intervals=[]
for ordinal,row in enumerate(scope):
 y,start,end,owners,sids,kind=row;segments=[]
 for x in range(start,end):
  k=(owners[0],y,x);status='bounded-adopted-source-interpretation'if k in answers else'evidence-backed-unresolved-physical-question';group=answers.get(k,'held294')
  if segments and segments[-1]['end']==x and segments[-1]['status']==status and segments[-1]['source_group']==group:segments[-1]['end']=x+1
  else:segments.append({'start':x,'end':x+1,'status':status,'source_group':group})
 assert segments[0]['start']==start and segments[-1]['end']==end and all(a['end']==b['start']for a,b in zip(segments,segments[1:]));intervals.append({'original_interval_ordinal':ordinal,'original_interval':row,'dispositions':segments})
result={'kind':'original-MMR-physical18459-complete-disposition-coverage-audit','original_scientific_vintage':original['scientific_vintage'],'original_package':'gb-MMR-ADM3--physical-interpretation','original_cells':18459,'original_intervals':9162,'positive_interpretation_keys':18165,'explicit_unresolved_keys':294,'exact_source_body_joins':294,'exact_original_owner_interval_SID_joins':294,'literal_original_completion':'Classify each interval with a reusable source interpretation or an explicit unresolved question. Physical-mask disagreement alone does not reject a source-backed river/location assignment.','source_groups':sources,'original_scope_body':fact(p/'original-remaining-intervals.json.gz'),'current_held_body':fact(heldpath),'original_questions_body':fact(p/'3-open-physical-questions.jsonl.gz'),'held_question_categories':dict(collections.Counter(r['original_source_question']for r in rows)),'public_projection_note':'Machine-local original centre_array prefix and disclosed retained-private prefix compare through their exact unchanged .cache suffix only. All other source-observation fields are literal.', 'top_level_precise_annual_questions':sum(r['current_precise_annual_question']is not None for r in rows),'top_level_reservation_labels_resolved_to_nested_actual_questions':sum(r['current_precise_annual_question']is None for r in rows),'intervals':intervals,'scientific_adoption_or_package_closure':False,'remaining_review_requirements':['Independent final exact coverage review against immutable original package and public source/result bodies','Bind genuine original independent reviews for interpreted facets and retained unresolved questions; fresh source/imagery acquisition is not implied','Root adoption/publication of completion disposition while18165 interpreted and294 unresolved remain distinct'],'limits':['No new positive physical facet, repair, native ownership, source priority or geography hold clearance.','This is metadata/key/body binding, not a new interpretation of imagery.','The263 top-level reservation labels are not themselves scientific conclusions; the exact nested original questions and source evidence remain the operative unresolved dispositions.']}
(d/'physical18459-complete-disposition-coverage.json').write_text(json.dumps(result,indent=2)+'\n');(d/'physical294-evidence-backed-unresolved-dispositions.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in['intervals','source_groups','held_question_categories']},indent=2))
