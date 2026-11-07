import json
from shapely.geometry import LineString,Point
from shapely.ops import substring
from west_abin_both_joins import src,alt,pair
s=LineString(json.load(open('caucasus-line.json'))['coordinates']);a=LineString(json.load(open('west-abin-splice-cut-research.json'))['coordinates']); xs=s.intersection(a);pts=[x for x in getattr(xs,'geoms',[xs]) if x.geom_type=='Point'];pts.sort(key=s.project);west=pts[0]; pre=substring(s,0,s.project(west));print('opts')
for p in list(reversed(pts))[:15]:
 si=s.project(p); ai=a.project(p)
 if not ai:continue
 ac=substring(a,0,ai);post=substring(s,si,s.length);full=LineString(list(pre.coords)+list(ac.coords)[1:]+list(post.coords)[1:]);ss=src.closest((p.x,p.y))['station_m']; aa=alt.closest((p.x,p.y))['station_m'];print(round(ss),round(aa),round(p.x,6),round(p.y,6),'simple',full.is_simple,'source',pair(src,ss+300),'candidate',pair(alt,aa-300))
