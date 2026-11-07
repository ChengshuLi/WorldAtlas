import json,numpy as np
from affine import Affine
from shapely.geometry import LineString,mapping
from shapely.ops import unary_union,linemerge
from pyproj import Geod
p=np.load('west-stream-seeded-srtm-abin-output.npz');aff=Affine(*p['affine'][:6]);edges=[]
for r,c,dr,dc in p['boundary']:
 if dc:a=aff*(c+1,r);b=aff*(c+1,r+1)
 else:a=aff*(c,r+1);b=aff*(c+1,r+1)
 edges.append(LineString([a,b]))
merged=linemerge(unary_union(edges));lines=list(merged.geoms) if hasattr(merged,'geoms') else [merged];G=Geod(ellps='WGS84')
def length(g):return sum(G.inv(*a,*b)[2] for a,b in zip(g.coords,g.coords[1:]))
source=LineString([x for x in json.load(open('caucasus-line.json'))['coordinates'] if 38.25<x[0]<38.71 and 44.45<x[1]<44.81]);rank=sorted(lines,key=length,reverse=True)
print('components',len(rank),'lengths_m',[round(length(x)) for x in rank[:10]])
for x in rank[:10]:
 print('length_m',round(length(x)),'bounds',tuple(round(v,5) for v in x.bounds),'endpoints',x.coords[0],x.coords[-1],'intersects_source',not x.intersection(source).is_empty)
json.dump({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'length_m':length(g)},'geometry':mapping(g)} for g in rank]},open('west-seeded-divide-srtm-abin-research.json','w'))
