"""Identify open-ocean row runs without allocating a dense world raster."""
import gzip,numpy as np,json
from pathlib import Path
import argparse
parser=argparse.ArgumentParser();parser.add_argument('parent',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--ocean-code',type=int,choices=[7,8,9,10]);args=parser.parse_args()
p=args.parent;m=json.loads((p/'proposal.json').read_text());r=np.frombuffer(gzip.open(p/'rows.u32.gz','rb').read(),'<u4');v=np.frombuffer(gzip.open(p/'runs.u32.gz','rb').read(),'<u4').reshape(-1,2);n=len(v);parent=np.arange(n,dtype='int32');rank=np.zeros(n,dtype='uint8');g=((v[:,1]==args.ocean_code) if args.ocean_code else ((v[:,1]>=7)&(v[:,1]<=10))).astype('uint8')

def find(x):
 while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
 return x

def union(a,b):
 a=find(a);b=find(b)
 if a==b:return
 if rank[a]<rank[b]:a,b=b,a
 parent[b]=a
 if rank[a]==rank[b]:rank[a]+=1
for y in range(m['height']):
 a,b=map(int,r[y:y+2]);
 for i in range(a+1,b):
  if g[i]==1 and g[i]==g[i-1]:union(i,i-1)
 if g[a]==1 and g[a]==g[b-1]:union(a,b-1)
 if not y:continue
 pa,pb=map(int,r[y-1:y+1]);i,j=a,pa;si=sj=0
 while i<b and j<pb:
  ei,ej=int(v[i,0]),int(v[j,0])
  if max(si,sj)<min(ei,ej) and g[i]==1 and g[i]==g[j]:union(i,j)
  if ei<=ej:si=ei;i+=1
  if ej<=ei:sj=ej;j+=1
roots=np.array([find(i) for i in range(n)],dtype='int32');counts=np.zeros(n,dtype="int64")
for y in range(m['height']):
 a,b=map(int,r[y:y+2]);lengths=np.diff(np.r_[0,v[a:b,0]]).astype('int64');water=g[a:b]==1;np.add.at(counts,roots[a:b][water],lengths[water])
main=int(counts.argmax());opened=(roots==main)&(g==1)
np.save(args.output,opened)
json.dump({'proposal_id':m['proposal_id'],'runs_sha256':m['local_grid']['runs_sha256'],'ocean_code':args.ocean_code},open(str(args.output)+'.meta.json','w'))
closed=(g==1)&~opened
records={int(k):{'cells':int(counts[k]),'groups':set(),'first':None} for k in np.unique(roots[closed])}
for y in range(m['height']):
 a,b=map(int,r[y:y+2])
 for i in range(a,b):
  if not closed[i]:continue
  rec=records[int(roots[i])];start=int(v[i-1,0]) if i>a else 0;end=int(v[i,0])
  if rec['first'] is None:rec['first']=[start,y]
  for neighbor in [i-1 if i>a else b-1,i+1 if i+1<b else a]:
   val=int(v[neighbor,1]);group=val&15
   if 1<=group<=10 and group!=args.ocean_code:rec['groups'].add(group)
  for yy in [y-1,y+1]:
   if yy<0 or yy>=m['height']:continue
   aa,bb=map(int,r[yy:yy+2]);j=aa+int(np.searchsorted(v[aa:bb,0],start,side='right'))
   while j<bb and (int(v[j-1,0]) if j>aa else 0)<end:
    group=int(v[j,1])&15
    if 1<=group<=10 and group!=args.ocean_code:rec['groups'].add(group)
    j+=1
for rec in records.values():rec['groups']=sorted(rec['groups'])
json.dump(sorted(records.values(),key=lambda z:-z['cells']),open(str(args.output)+'.json','w'),indent=2)
print('disconnected ocean components',len(records),'cells',int(counts[list(records)].sum()),flush=True)
print('open ocean cells',int(counts[main]),'closed water runs',int(np.count_nonzero((g==1)&~opened)),flush=True)

