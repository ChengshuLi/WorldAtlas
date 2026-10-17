import json,pathlib,collections,gzip,subprocess,hashlib
D=pathlib.Path(__file__).resolve().parent;B='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';R=D.parent/'worldatlas-primary'
a=json.loads((D/'identity-obligations-review.json').read_text());f=json.loads((D/'original-foreign-contact-keys.json').read_text());u=json.loads((D/'exact-USA31-component-keys.json').read_text());reasons=collections.defaultdict(set)
for x in f['keys']:reasons[(x['y'],x['x'],x['owner_index'])].add('complete-foreign-original-contact')
for x in u['keys']:reasons[(x['y'],x['x'],x['owner_index'])].add('USA31-existing-source-history-defer')
for y,a0,z,o,s,k in a['Fairfax']['hold_keys']:
 for x in range(a0,z):reasons[(y,x,o[0])].add('Fairfax-distinct-city-county-identity-976')
rows=json.loads(gzip.decompress((D.parent/'screen-next-repair-package-20261017/gb-USA-ADM2--repair-evaluation.json.gz').read_bytes()));held=[];complement=[];keys=[]
for idx,(y,a0,z,o,s,kind)in enumerate(rows):
 groups=[];prev=None
 for x in range(a0,z):
  why=sorted(reasons.get((y,x,o[0]),[]))
  if why:keys.append({'y':y,'x':x,'owner_index':o[0],'physical_class':kind,'reasons':why})
  if groups and why==prev:groups[-1][1]=x+1
  else:groups.append([x,x+1,why]);prev=why
 for lo,hi,why in groups:
  record={'original_row_index':idx,'row':[y,lo,hi,o,s,kind]}
  if why:record['reasons']=why;held.append(record)
  else:complement.append(record)
counts=collections.Counter(x['physical_class']for x in keys);seen={(x['y'],x['x'],x['owner_index'])for x in keys};assert seen==set(reasons) and len(seen)==600 and len(keys)==600;assert sum(x['row'][2]-x['row'][1]for x in held)==600;assert sum(x['row'][2]-x['row'][1]for x in complement)==106531
p='research/geography/usa31-gap-family-source-fitness-20261007/per-component-source-screen.json';raw=subprocess.check_output(['git','-C',str(R),'show',B+':'+p]);source=json.loads(raw);component_scope={r['component_id']for r in u['components']};assert component_scope=={r['component']for r in source['components']}and len(component_scope)==31;defer=[{k:r[k]for k in ['component','classification','physical_authority','physical_status','physical_source_vintage','current_geometry_sha256','current_feature_sha256']}for r in source['components']];assert {r['classification']for r in defer}=={'source-history-unresolved; retain original candidate and defer processing/repair'}
out={'kind':'independent-exact-original-hold-key-union','baseline':B,'original_keys':107131,'original_owners':351,'original_intervals':46575,'hold_counts':{'foreign':63,'USA31':536,'Fairfax':1,'distinct_union':600,'pairwise_intersections':{'foreign_USA31':0,'foreign_Fairfax':0,'USA31_Fairfax':0}},'held_physical_classes':dict(counts),'potential_complement_before_qualification':{'keys':106531,'owners':len({r['row'][3][0]for r in complement}),'land':95729-counts['land'],'inland_water':11402-counts['inland-water'],'interval_segments':len(complement)},'held_intervals':held,'held_keys':keys,'USA31_exact_source_dispositions':defer,'disposition_pin':{'commit':B,'path':p,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'later_resolution_check':{'issue1377':'Closed source-only; all31 remain source-history unresolved per acceptance comment6037327763. All6 issue comments fetched 2026-10-17.','issue1534':'Open preservation/reproduction/metric-integrity successor. No comments. No source-fitness resolution.','issue1630':'Open later campaign explicitly retains USA31 source-history-unresolved. Later4 AleutiansWest source checks are expressly disjoint from USA31. All comments fetched.','search':'GitHub repository issue queries1377 and USA31 return1377,1534,1630. No later applicable source-fitness resolution found.'},'limits':['These holds preserve present contrary evidence and explicit source-history uncertainty; they are not findings that600 cells belong elsewhere.','The106531 complement has not passed source/physical/native qualification or selected-owner-zero/conservation/delivery gates.','No all-county hold is inferred from broad historical/semantic research scope alone.']};(D/'hold-key-union.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['hold_counts','held_physical_classes','potential_complement_before_qualification']},indent=2))
