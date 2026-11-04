#!/usr/bin/env python3
"""Group differing spans by touching 36-cell grid bins (~0.099 degrees)."""
import argparse,csv,json,hashlib
from pathlib import Path
from collections import defaultdict,Counter
ap=argparse.ArgumentParser();ap.add_argument('--spans',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);v=ap.parse_args();D=36;W=131072;STEP=360/W;src=v.spans;out=v.output;bins={}
if out.exists():raise RuntimeError('output exists')
with src.open() as f:
 for r in csv.DictReader(f,delimiter='\t'):
  y,a,b,old,new,seed=[int(r[k]) for k in ('row','start','end','reference','candidate','mainland_seed')];kind='continent' if old>=17 and new>=17 else 'physical'
  x=a
  while x<b:
   z=min(b,((x//D)+1)*D);k=(kind,y//D,x//D);v=bins.setdefault(k,{'n':0,'oldnew':Counter(),'seed':Counter(),'minx':x,'maxx':z-1,'miny':y,'maxy':y});v['n']+=z-x;v['oldnew'][f'{old}:{new}']+=z-x;v['seed']['mainland' if seed else 'offshore_or_physical']+=z-x;v['minx']=min(v['minx'],x);v['maxx']=max(v['maxx'],z-1);v['miny']=min(v['miny'],y);v['maxy']=max(v['maxy'],y);x=z
seen=set();groups=[];nx=(W+D-1)//D
for key in bins:
 if key in seen:continue
 todo=[key];seen.add(key);cluster=[]
 while todo:
  k=todo.pop();cluster.append(bins[k]);kind,y,x=k
  for dy in (-1,0,1):
   for dx in (-1,0,1):
    q=(kind,y+dy,(x+dx)%nx)
    if q in bins and q not in seen:seen.add(q);todo.append(q)
 n=sum(v['n'] for v in cluster);trans=sum((v['oldnew'] for v in cluster),Counter());seed=sum((v['seed'] for v in cluster),Counter());minx=min(v['minx'] for v in cluster);maxx=max(v['maxx'] for v in cluster);miny=min(v['miny'] for v in cluster);maxy=max(v['maxy'] for v in cluster)
 groups.append({'kind':key[0],'cells':n,'transitions':dict(trans),'seed_status':dict(seed),'extent':{'west':-180+(minx+.5)*STEP,'east':-180+(maxx+.5)*STEP,'north':90-(miny+.5)*STEP,'south':90-(maxy+.5)*STEP},'bins':len(cluster)})
groups.sort(key=lambda x:-x['cells']);result={'schema':'v2-land-difference-clusters-v1','status':'research-validation-only','bin_width_cells':D,'bin_width_degrees':D*STEP,'adjacency':'eight-neighbor occupied bins, longitude wraps; not a formal geographic region','spans_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'clusters':groups}
out.write_text(json.dumps(result,indent=2)+'\n');print('clusters',len(groups));print(json.dumps(groups[:25],indent=2))
