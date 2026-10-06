"""Exploratory exact source-segment arrangement. Never changes original bytes."""
from fractions import Fraction as F
from functools import cmp_to_key
from collections import defaultdict
from shapely.geometry import LineString
from shapely.strtree import STRtree

def point(p):return tuple(F(x)for x in p)
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def minus(a,b):return(a[0]-b[0],a[1]-b[1])
def on(a,b,p):return cross(minus(b,a),minus(p,a))==0 and all(min(a[i],b[i])<=p[i]<=max(a[i],b[i])for i in [0,1])
def crossings(a,b,c,d):
 r,s=minus(b,a),minus(d,c);v=minus(c,a);det=cross(r,s)
 if det:
  t,u=cross(v,s)/det,cross(v,r)/det
  return[(a[0]+t*r[0],a[1]+t*r[1])]if 0<=t<=1 and 0<=u<=1 else[]
 if cross(v,r):return[]
 return list({p for p in [a,b,c,d]if on(a,b,p)and on(c,d,p)})
def signed_area(ring):return sum(cross(a,b)for a,b in zip(ring,ring[1:]+ring[:1]))/2

def inside_ring(p,ring):
 inside=False
 for a,b in zip(ring,ring[1:]+ring[:1]):
  if on(a,b,p):return None
  if(a[1]<=p[1]<b[1])or(b[1]<=p[1]<a[1]):
   x=a[0]+(p[1]-a[1])*(b[0]-a[0])/(b[1]-a[1])
   if x>p[0]:inside=not inside
 return inside

def interior(ring):
 # Exact mid-scanline avoids rounded GEOS representative points on narrow faces.
 ys=sorted({p[1]for p in ring});intervals=sorted(zip(ys,ys[1:]),key=lambda q:q[1]-q[0],reverse=True)
 for lo,hi in intervals:
  y=(lo+hi)/2;xs=[]
  for a,b in zip(ring,ring[1:]+ring[:1]):
   if(a[1]<=y<b[1])or(b[1]<=y<a[1]):xs.append(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
  xs.sort()
  for a,b in zip(xs[::2],xs[1::2]):
   if a<b:
    p=((a+b)/2,y)
    if inside_ring(p,ring) is True:return p
 raise ValueError('No exact positive-area face interior')

def arrange(raw_segments):
 original=[]
 for a,b in raw_segments:
  a,b=point(a),point(b)
  if a!=b:original.append((a,b))
 nodes=[{a,b}for a,b in original]
 tree=STRtree([LineString([[float(v)for v in a],[float(v)for v in b]])for a,b in original])
 intersections=0
 for n,(a,b)in enumerate(original):
  for k in tree.query(LineString([[float(v)for v in a],[float(v)for v in b]])):
   k=int(k)
   if k<=n:continue
   values=crossings(a,b,*original[k]);intersections+=len(values)
   nodes[n].update(values);nodes[k].update(values)
 edges=set()
 for(a,b),values in zip(original,nodes):
  axis=0 if a[0]!=b[0]else 1;ordered=sorted(values,key=lambda p:p[axis])
  for u,v in zip(ordered,ordered[1:]):edges.add(tuple(sorted([u,v])))
 graph=defaultdict(set)
 for a,b in edges:graph[a].add(b);graph[b].add(a)
 def compare(origin,a,b):
  u,v=minus(a,origin),minus(b,origin)
  upper=lambda w:w[1]>0 or(w[1]==0 and w[0]>0)
  if upper(u)!=upper(v):return -1 if upper(u)else 1
  c=cross(u,v)
  if c:return -1 if c>0 else 1
  raise ValueError('Unnoded coincident half-edge direction')
 ordered={p:sorted(adj,key=cmp_to_key(lambda a,b:compare(p,a,b)))for p,adj in graph.items()}
 done=set();faces=[];negative=[];zero=[]
 for a in sorted(ordered):
  for b in ordered[a]:
   if(a,b)in done:continue
   ring=[];edge=(a,b)
   while edge not in done:
    done.add(edge);u,v=edge;ring.append(u);neighbors=ordered[v];edge=(v,neighbors[(neighbors.index(u)-1)%len(neighbors)])
   if edge!=(a,b):raise ValueError('Face walk joined previously consumed edge')
   area=signed_area(ring)
   if area>0:faces.append((ring,area,interior(ring)))
   elif area<0:negative.append((ring,area))
   else:zero.append(ring)
 return {'original_segments':original,'edges':edges,'faces':faces,'negative':negative,'zero':zero,'intersections':intersections}

def boundaries(faces,labels,owner):
 # Cancel identical internal half-edges; no new overlay/noding or coordinate edit.
 boundary=set()
 for(ring,area,p),membership in zip(faces,labels):
  if owner not in membership:continue
  for edge in zip(ring,ring[1:]+ring[:1]):
   if(edge[1],edge[0])in boundary:boundary.remove((edge[1],edge[0]))
   else:
    if edge in boundary:raise ValueError('Duplicate same-direction ownership edge')
    boundary.add(edge)
 outgoing=defaultdict(list)
 for a,b in boundary:outgoing[a].append(b)
 def compare(origin,a,b):
  u,v=minus(a,origin),minus(b,origin);upper=lambda w:w[1]>0 or(w[1]==0 and w[0]>0)
  if upper(u)!=upper(v):return -1 if upper(u)else 1
  c=cross(u,v)
  return -1 if c>0 else 1 if c<0 else 0
 ordered={p:sorted(adj,key=cmp_to_key(lambda a,b:compare(p,a,b)))for p,adj in outgoing.items()}
 done=set();rings=[]
 for start in sorted(boundary):
  if start in done:continue
  edge=start;ring=[]
  while edge not in done:
   done.add(edge);a,b=edge;ring.append(a)
   if b not in ordered:raise ValueError('Open owned boundary')
   # Choose the outgoing direction just clockwise from incoming reverse.
   choices=ordered[b];all_choices=sorted([*choices,a],key=cmp_to_key(lambda u,v:compare(b,u,v)))
   k=all_choices.index(a);next_point=all_choices[(k-1)%len(all_choices)]
   if next_point==a:raise ValueError('Owned edge reverses onto its excluded twin')
   edge=(b,next_point)
  if edge!=start:raise ValueError('Owned cycle joined another cycle')
  if signed_area(ring)==0:raise ValueError('Zero-area ownership cycle requires explicit investigation')
  rings.append(ring)
 if len(done)!=len(boundary):raise ValueError('Incomplete boundary traversal')
 return rings

def export_rings(rings):
 outer=[r for r in rings if signed_area(r)>0];holes=[r for r in rings if signed_area(r)<0]
 grouped=[[]for r in outer]
 for r in holes:
  p=interior(r);containers=[(signed_area(parent),n)for n,parent in enumerate(outer)if inside_ring(p,parent)is True]
  if not containers:raise ValueError('No exact enclosing outer cycle')
  grouped[min(containers)[1]].append(r)
 convert=lambda r:[[float(x),float(y)]for x,y in r+[r[0]]]
 polygons=[[convert(r),*[convert(h)for h in hs]]for r,hs in zip(outer,grouped)]
 if not polygons:raise ValueError('Empty target footprint')
 return {'type':'Polygon','coordinates':polygons[0]}if len(polygons)==1 else{'type':'MultiPolygon','coordinates':polygons}
