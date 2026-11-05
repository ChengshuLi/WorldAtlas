"""Construct an unselected coordinate-linear research splice at actual intersections."""
import json
from shapely.geometry import LineString,Point,shape,mapping
from shapely.ops import substring
from geodesic_line import GeodesicLine
raw=json.load(open('caucasus-line.json'))['coordinates']; src=LineString(raw); features=json.load(open('west-seeded-divide-srtm-abin-research.json'))['features'];a=shape(features[0]['geometry']);b=shape(features[1]['geometry']);alt=LineString(list(a.coords)+list(b.coords)[1:]); intersections=src.intersection(alt);points=[p for p in getattr(intersections,'geoms',[intersections]) if p.geom_type=='Point'];points.sort(key=src.project);start,end=points[0],points[-2];s0,s1=src.project(start),src.project(end);a0,a1=alt.project(start),alt.project(end)
if not 0<a0<a1<alt.length:raise ValueError('intersection order disagrees')
cut=substring(alt,a0,a1);pre=substring(src,0,s0);post=substring(src,s1,src.length);proposed=LineString(list(pre.coords)+list(cut.coords)[1:]+list(post.coords)[1:]);clip=substring(src,s0,s1)
print('intersections',len(points),'splice-simple',proposed.is_simple,'candidate-cut-simple',cut.is_simple,'source-replaced-length-m',GeodesicLine(list(clip.coords)).length,'candidate-cut-length-m',GeodesicLine(list(cut.coords)).length,'cut_vertices',len(cut.coords),'joins',list(start.coords)[0],list(end.coords)[0]);
json.dump(mapping(cut),open('west-abin-splice-second-cut-research.json','w'));json.dump(mapping(proposed),open('west-abin-splice-second-complete-research.json','w'))
