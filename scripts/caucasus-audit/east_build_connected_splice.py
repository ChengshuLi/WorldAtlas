"""Build a hypothetical coordinate-linear splice between observed intersections."""
import json
from shapely.geometry import LineString,mapping
from shapely.ops import substring
from geodesic_line import GeodesicLine
src=LineString(json.load(open('caucasus-line.json'))['coordinates']);cand=LineString(json.load(open('east-connected-exploratory.json'))['coordinates']); intersections=src.intersection(cand);p=[g for g in getattr(intersections,'geoms',[intersections]) if g.geom_type=='Point'];p.sort(key=src.project);a,b=p[0],p[-1];s0,s1=src.project(a),src.project(b);c0,c1=cand.project(a),cand.project(b);print('intersection_count',len(p),'cand_simple',cand.is_simple,'candidate_order',c0<c1)
if not c0<c1:raise ValueError('reverse orientation, review manually')
pre=substring(src,0,s0);cut=substring(cand,c0,c1);post=substring(src,s1,src.length);spliced=LineString(list(pre.coords)+list(cut.coords)[1:]+list(post.coords)[1:]);original=substring(src,s0,s1)
print('full_splice_simple',spliced.is_simple,'cut_simple',cut.is_simple,'joins',tuple(a.coords)[0],tuple(b.coords)[0],'source_m',GeodesicLine(list(original.coords)).length,'candidate_m',GeodesicLine(list(cut.coords)).length,'vertices',len(cut.coords));json.dump(mapping(cut),open('east-connected-splice-cut-research.json','w'));json.dump(mapping(spliced),open('east-connected-splice-full-research.json','w'))
