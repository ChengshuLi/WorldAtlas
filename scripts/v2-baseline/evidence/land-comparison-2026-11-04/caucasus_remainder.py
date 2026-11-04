#!/usr/bin/env /usr/bin/python3
import argparse,csv,gzip,json,math
from pathlib import Path
from collections import Counter,defaultdict
ap=argparse.ArgumentParser();ap.add_argument('--spans',required=True,type=Path);ap.add_argument('--ledger',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);v=ap.parse_args();SP=v.spans;LED=v.ledger;OUT=v.output;step=360/131072;bounds=(37.31,49.33,40.8,44.91);west,east,south,north=bounds;x0=math.ceil((west+180)/step-.5);x1=math.floor((east+180)/step-.5)+1;rows=defaultdict(list)
with SP.open() as f:
 for r in csv.DictReader(f,delimiter='\t'):
  y,a,b,o,n,seed=map(int,(r['row'],r['start'],r['end'],r['reference'],r['candidate'],r['mainland_seed']));lat=90-(y+.5)*step
  if o==18 and n==19 and seed and south<=lat<=north and max(a,x0)<min(b,x1):rows[y].append((max(a,x0),min(b,x1)))
with OUT.open('x') as out:
 out.write('row\tstart\tend\treference\tcandidate\tmainland_seed\n')
 with gzip.open(LED,'rt') as f:
  for line in f:
   rec=json.loads(line);y=rec['row']
   for a,b in rows.get(y,()):
    cursor=a
    for s in rec['spans']:
     if s['end']<=a:continue
     if s['start']>=b:break
     if s['from_code']!=18 or s['to_code']!=19:raise ValueError('unexpected ledger transition')
     lo=max(a,s['start']);hi=min(b,s['end'])
     if cursor<lo:out.write(f'{y}\t{cursor}\t{lo}\t18\t19\t19\n')
     cursor=max(cursor,hi)
    if cursor<b:out.write(f'{y}\t{cursor}\t{b}\t18\t19\t19\n')
print('wrote',OUT)
