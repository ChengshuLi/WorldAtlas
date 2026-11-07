import sys,json,numpy as np
from affine import Affine
from shapely.geometry import LineString,mapping,shape
from shapely.ops import unary_union,linemerge
from pyproj import Geod
from geodesic_line import GeodesicLine
f=sys.argv[1];out=sys.argv[2];p=np.load(f);labels=p['labels'];aff=Affine(*p['affine'][:6]);h,w=labels.shape;edges=[]
for dr,dc in ((0,1),(1,0)):
 a=labels[:h-dr,:w-dc];b=labels[dr:,dc:];hits=((a==1)&(b==2))|((a==2)&(b==1))
 for r,c in np.argwhere(hits):
  x,y=(aff*(int(c)+1,int(r)),aff*(int(c)+1,int(r)+1)) if dc else (aff*(int(c),int(r)+1),aff*(int(c)+1,int(r)+1));edges.append(LineString([x,y]))
if not edges:raise ValueError('no interface')
g=linemerge(unary_union(edges));components=list(g.geoms) if hasattr(g,'geoms') else [g];source=LineString(json.load(open('caucasus-anapa-abin-combined-candidate.json'))['coordinates']);rank=sorted(components,key=lambda x:GeodesicLine(list(x.coords)).length,reverse=True)
print('edges',len(edges),'components',len(rank))
for i,g in enumerate(rank[:10]):
 cross=g.intersection(source);print('rank',i,'length_m',round(GeodesicLine(list(g.coords)).length),'bounds',tuple(round(x,6) for x in g.bounds),'source_intersection',str(cross)[:400], 'simple',g.is_simple)
json.dump({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'rank':i},'geometry':mapping(g)} for i,g in enumerate(rank)]},open(out,'w'))
