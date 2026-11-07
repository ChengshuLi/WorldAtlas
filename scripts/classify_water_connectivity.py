"""Identify open-ocean row runs without allocating a dense world raster."""
import gzip,numpy as np,json
from pathlib import Path
import argparse
parser=argparse.ArgumentParser();parser.add_argument('parent',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
p=args.parent;m=json.loads((p/'proposal.json').read_text());r=np.frombuffer(gzip.open(p/'rows.u32.gz','rb').read(),'<u4');v=np.frombuffer(gzip.open(p/'runs.u32.gz','rb').read(),'<u4').reshape(-1,2);n=len(v);parent=np.arange(n,dtype='int32');rank=np.zeros(n,dtype='uint8');g=(v[:,1]<16).astype("uint8")

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
print('open ocean cells',int(counts[main]),'closed water runs',int(np.count_nonzero((g==1)&~opened)),flush=True)
