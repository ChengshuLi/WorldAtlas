import json,numpy as np
from shapely.geometry import LineString,Point
from shapely.ops import unary_union,linemerge
from affine import Affine
from geodesic_line import GeodesicLine
p=np.load('west-stream-seeded-jaxa-product-filled-abin-output.npz');aff=Affine(*p['affine'][:6]);edges=[]
for r,c,dr,dc in p['boundary']:
 a,b=((aff*(c+1,r),aff*(c+1,r+1)) if dc else (aff*(c,r+1),aff*(c+1,r+1)));edges.append(LineString([a,b]))
merged=linemerge(unary_union(edges));lines=list(merged.geoms) if hasattr(merged,'geoms') else [merged];line=GeodesicLine(json.load(open('west-abin-jaxa-local-alternative-research.json'))['coordinates']);rank=sorted(lines,key=lambda g:GeodesicLine(list(g.coords)).length,reverse=True)
for i,g in enumerate(rank[:15]):
 a,b=g.coords[0],g.coords[-1]; print(i,'length_m',round(GeodesicLine(list(g.coords)).length),'endpoints',tuple(round(x,5) for x in a),tuple(round(x,5) for x in b),'dist_to_candidate_m',round(line.closest(a)['distance_m']),round(line.closest(b)['distance_m']))
json.dump({'type':'FeatureCollection','features':[{'type':'Feature','properties':{'rank':i},'geometry':g.__geo_interface__} for i,g in enumerate(rank)]},open('west-seeded-divide-jaxa-filled-abin-research.json','w'))
