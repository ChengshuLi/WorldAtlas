"""Describe seed-labeled interfaces only; not a selected line."""
import sys,json,numpy as np
from affine import Affine
from shapely.geometry import LineString,mapping
from shapely.ops import unary_union,linemerge
from pyproj import Geod
p=np.load('jvari-expanded-north-jaxa-research.npz');labels=p['labels'];aff=Affine(*p['affine'][:6]);h,w=labels.shape;edges=[]
for dr,dc in ((0,1),(1,0)):
 a=labels[:h-dr,:w-dc];b=labels[dr:,dc:];hits=((a==1)&(b==2))|((a==2)&(b==1))
 for r,c in np.argwhere(hits):
  x,y=(aff*(int(c)+1,int(r)),aff*(int(c)+1,int(r)+1)) if dc else (aff*(int(c),int(r)+1),aff*(int(c)+1,int(r)+1))
  edges.append(LineString([x,y]))
if not edges:print('no adjacent opposing labels');sys.exit(0)
g=linemerge(unary_union(edges));components=list(g.geoms) if hasattr(g,'geoms') else [g];geod=Geod(ellps='WGS84')
def dist(g):return sum(geod.inv(*a,*b)[2] for a,b in zip(g.coords,g.coords[1:]))
rank=sorted(components,key=dist,reverse=True);source=LineString(json.load(open('caucasus-line.json'))['coordinates']);print('model',sys.argv[1],'edges',len(edges),'components',len(rank))
for i,g in enumerate(rank[:10]):
 q=g.intersection(source);print('component',i,'length_m',round(dist(g),1),'bounds',tuple(round(v,6) for v in g.bounds),'intersection',q.wkt[:500],'simple',g.is_simple)
json.dump({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'length_m':dist(g)},'geometry':mapping(g)} for g in rank]},open('jvari-expanded-north-interface-research.json','w'))
