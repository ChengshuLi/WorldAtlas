import json
from shapely.geometry import LineString,Point,shape,mapping
from shapely.ops import substring
from geodesic_line import GeodesicLine
src=LineString(json.load(open('caucasus-anapa-abin-combined-candidate.json'))['coordinates']);g=shape(json.load(open('klukhor-jaxa-interface-research.json'))['features'][0]['geometry']);cross=src.intersection(g);points=sorted([p for p in getattr(cross,'geoms',[cross]) if p.geom_type=='Point'],key=src.project);start=points[0];prefix=substring(src,0,src.project(start));interface=substring(g,g.project(start),0)
for weight in (0,1,4):
 bridge=shape(json.load(open('klukhor-north-gap-%d-research.json'%weight)));end=Point(bridge.coords[-1]);suffix=substring(src,src.project(end),src.length);cut=LineString(list(interface.coords)+list(bridge.coords)[1:]);old=substring(src,src.project(start),src.project(end));full=LineString(list(prefix.coords)+list(cut.coords)[1:]+list(suffix.coords)[1:]);print('weight',weight,'old',round(GeodesicLine(list(old.coords)).length),'new',round(GeodesicLine(list(cut.coords)).length),'cut simple',cut.is_simple,'full simple',full.is_simple,'preserved endpoints',full.coords[0]==src.coords[0] and full.coords[-1]==src.coords[-1]);
 if full.is_simple and cut.is_simple:
  for path,g0 in [('klukhor-gap-old-%d-research.json'%weight,old),('klukhor-gap-cut-%d-research.json'%weight,cut),('klukhor-gap-full-%d-research.json'%weight,full)]:json.dump(mapping(g0),open(path,'w'))
