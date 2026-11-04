#!/usr/bin/env /usr/bin/python3
import argparse,csv,gzip,json,math,hashlib
from pathlib import Path
from collections import Counter,defaultdict
ap=argparse.ArgumentParser();ap.add_argument('--spans',required=True,type=Path);ap.add_argument('--ledger',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);v=ap.parse_args();sp=v.spans;ledger=v.ledger;out=v.output;step=360/131072;rows=defaultdict(list)
if out.exists():raise RuntimeError('output exists')
west,east,south,north=37.31,49.33,40.8,44.91
x0=math.ceil((west+180)/step-.5);x1=math.floor((east+180)/step-.5)+1
with sp.open() as f:
 for r in csv.DictReader(f,delimiter='\t'):
  y,a,b,old,new,seed=map(int,(r['row'],r['start'],r['end'],r['reference'],r['candidate'],r['mainland_seed']));lat=90-(y+.5)*step
  if old==18 and new==19 and seed and south<=lat<=north and max(a,x0)<min(b,x1):rows[y].append((max(a,x0),min(b,x1)))
counts=Counter();members=Counter()
with gzip.open(ledger,'rt') as f:
 for line in f:
  rec=json.loads(line)
  for a,b in rows.get(rec['row'],()):
   covered=0
   for s in rec['spans']:
    if s['end']<=a:continue
    if s['start']>=b:break
    length=min(b,s['end'])-max(a,s['start'])
    if length<=0:continue
    if s['from_code']!=18:raise ValueError('ledger reference mismatch')
    covered+=length;counts['v7_equals_candidate' if s['to_code']==19 else 'v7_differs_from_both']+=length;members[s['member_id']]+=length
   counts['v7_equals_v2']+=b-a-covered
r={'schema':'caucasus-v2-v7-ledger-overlap-v1','status':'research-validation-only','selection':'candidate seeded mainland Asia→Europe changes inside diagnostic box 37.31–49.33E, 40.8–44.91N','counts':dict(counts),'members':dict(members),'spans_sha256':hashlib.sha256(sp.read_bytes()).hexdigest(),'ledger_sha256':hashlib.sha256(ledger.read_bytes()).hexdigest(),'limitation':'The later V7 ledger is a verified comparison source, not evidence of the unrecovered V2 source route or of a bug.'};out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
