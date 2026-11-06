import json
from shapely.geometry import LineString,Point,mapping,shape
from shapely.ops import substring
from geodesic_line import GeodesicLine
from pyproj import Geod
G=Geod(ellps='WGS84')
src=LineString(json.load(open('caucasus-line.json'))['coordinates']);prior_endpoints=((38.31791666666666,44.59583333333336),(38.65436563496357,44.50458333333333));jaxa=shape(json.load(open('west-seeded-divide-jaxa-filled-abin-research.json'))['features'][0]['geometry']);cross=src.intersection(jaxa);points=[p for p in getattr(cross,'geoms',[cross]) if p.geom_type=='Point'];points.sort(key=src.project)
for p in points:
 print('intersection',round(p.x,6),round(p.y,6),'near prior endpoints m',round(G.inv(prior_endpoints[0][0],prior_endpoints[0][1],p.x,p.y)[2]), 'source_station',round(src.project(p),6))
print('total',len(points))
from pyproj import Geod
G=Geod(ellps='WGS84');closest=lambda pt: min(points,key=lambda x:G.inv(pt[0],pt[1],x.x,x.y)[2]);start=closest(prior_endpoints[0]);end=closest(prior_endpoints[-1]);s0,s1=src.project(start),src.project(end);j0,j1=jaxa.project(start),jaxa.project(end)
print('chosen joins',list(start.coords),list(end.coords),'stations order',s0<s1,'jaxa order',j0<j1)
cut=substring(jaxa,j0,j1);pre=substring(src,0,s0);post=substring(src,s1,src.length);full=LineString(list(pre.coords)+list(cut.coords)[1:]+list(post.coords)[1:]);print('cut length',round(GeodesicLine(list(cut.coords)).length),'cut simple',cut.is_simple,'full simple',full.is_simple,'full endpoints retained',full.coords[0]==src.coords[0] and full.coords[-1]==src.coords[-1]);
if not full.is_simple or not cut.is_simple or s0>=s1:raise ValueError('invalid topology')
json.dump(mapping(cut),open('west-abin-jaxa-product-cut-research.json','w'));json.dump(mapping(full),open('west-abin-jaxa-product-full-research.json','w'))
