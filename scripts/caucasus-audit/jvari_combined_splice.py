import json
from shapely.geometry import LineString,Point,shape,mapping
from shapely.ops import substring
from geodesic_line import GeodesicLine
src=LineString(json.load(open('caucasus-anapa-abin-combined-candidate.json'))['coordinates']);model=shape(json.load(open('jvari-expanded-north-interface-research.json'))['features'][0]['geometry']);line=GeodesicLine(list(src.coords));t0=line.closest((44.382281,42.551041))['station_m'];t1=line.closest((44.45511099459589,42.50809094740639))['station_m'];a,b=min(t0,t1),max(t0,t1);x=src.intersection(model);points=[p for p in getattr(x,'geoms',[x]) if p.geom_type=='Point'];ordered=sorted([(line.closest((p.x,p.y))['station_m'],p) for p in points],key=lambda p:p[0]);lo=[q for q in ordered if q[0]<a-20];hi=[q for q in ordered if q[0]>b+20];
if not lo or not hi:raise ValueError('no bracket joins')
(s0,p0),(s1,p1)=lo[-1],hi[0];i,j=src.project(p0),src.project(p1);u,v=model.project(p0),model.project(p1);pre=substring(src,0,i);old=substring(src,i,j);cut=substring(model,u,v);post=substring(src,j,src.length);full=LineString(list(pre.coords)+list(cut.coords)[1:]+list(post.coords)[1:]);print('joins',round(s0-a),round(s1-b),'old_m',round(GeodesicLine(list(old.coords)).length),'new_m',round(GeodesicLine(list(cut.coords)).length),'cut_simple',cut.is_simple,'full_simple',full.is_simple,'endpoint_preserved',full.coords[0]==src.coords[0] and full.coords[-1]==src.coords[-1]);
if not cut.is_simple or not full.is_simple:raise ValueError('invalid geometry')
for f,g in [('jvari-combined-current-cut-research.json',old),('jvari-combined-jaxa-cut-research.json',cut),('jvari-combined-jaxa-full-research.json',full)]:json.dump(mapping(g),open(f,'w'))
