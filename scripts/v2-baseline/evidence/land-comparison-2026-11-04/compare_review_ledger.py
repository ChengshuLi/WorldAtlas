#!/usr/bin/env /usr/bin/python3
"""Compare candidate/V2 land changes to independently verified V2->V7 ledger."""
from pathlib import Path
import argparse,csv,gzip,json,hashlib
from collections import defaultdict,Counter
ap=argparse.ArgumentParser();ap.add_argument('--spans',required=True,type=Path);ap.add_argument('--ledger',required=True,type=Path);ap.add_argument('--member-index',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);v=ap.parse_args();SP=v.spans;LED=v.ledger;IDX=v.member_index;OUT=v.output;rows=defaultdict(list)
if OUT.exists():raise RuntimeError('output exists')
with SP.open() as f:
 for r in csv.DictReader(f,delimiter='\t'):
  y,a,b,o,n=map(int,(r['row'],r['start'],r['end'],r['reference'],r['candidate']))
  if 17<=o<=22 and 17<=n<=22:rows[y].append((a,b,o,n))
summary=Counter();members=Counter();by_transition=defaultdict(Counter)
with gzip.open(LED,'rt') as f:
 for line in f:
  rec=json.loads(line);y=rec['row']
  if y not in rows:continue
  for a,b,o,n in rows[y]:
   covered=0
   for s in rec['spans']:
    if s['end']<=a:continue
    if s['start']>=b:break
    length=min(b,s['end'])-max(a,s['start'])
    if length<=0:continue
    if s['from_code']!=o:raise ValueError('ledger V2 mismatch')
    covered+=length;category='v7_equals_candidate' if s['to_code']==n else 'v7_differs_from_both';summary[category]+=length;by_transition[f'{o}:{n}'][category]+=length;members[s['member_id']]+=length
   summary['v7_equals_v2']+=b-a-covered;by_transition[f'{o}:{n}']['v7_equals_v2']+=b-a-covered
meta={x['member_id']:x for x in json.loads(IDX.read_bytes())['members']};items=[]
for member,count in members.most_common():
 m=meta[member];items.append({'member_id':member,'overlap_cells':count,'source_group_title':m['source_group_title'],'source_group_reason':m['source_group_reason']})
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r={'schema':'candidate-v2-v7-land-ledger-overlap-v1','status':'research-validation-only','summary':dict(summary),'by_transition':{k:dict(v) for k,v in by_transition.items()},'members':items,'inputs':{'spans_sha256':sha(SP),'ledger_sha256':sha(LED),'member_index_sha256':sha(IDX)},'limitation':'Ledger was independently checked against preserved V2/V7 grids; overlap identifies later reviewed changes, not proof of V2 source inputs or cause. Candidate physical differences excluded.'}
OUT.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
