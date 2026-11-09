"""Measure administrative coverage of freshly source-selected component roots.

The caller must authenticate the revision-bound mappings, extract raw provider
features, re-resolve the selecting polygon claim, pin/recheck code and streams,
protect mainland roots, check conflicts and validate input provenance. This
module reports corroboration for the selected components.
Source-hit roots outside the selected claim are ignored, not adjudicated here.
"""
import math
from fractions import Fraction
from pathlib import Path
import polygon_intersection as pi

def need(x,m):
 if not x:raise ValueError(m)
def evaluate(claim,associations,admin_features,grid,inputs):
 from osgeo import ogr
 need(isinstance(claim,dict) and isinstance(claim.get('affiliation_id'),str) and claim['affiliation_id'] and claim.get('method')=='component_intersection_v1','invalid source claim')
 roots=claim.get('component_ids');features=claim.get('source_features');intersection=claim.get('intersection',{});hits=intersection.get('per_feature_root_inside_cells');need(isinstance(roots,list) and len(roots)>0 and all(type(x) is int and 0<=x<0xffffffff for x in roots) and len(set(roots))==len(roots) and isinstance(features,list) and 0<len(features)<=1000 and isinstance(hits,list) and len(hits)==len(features),'invalid claim roots or feature trace');rootset=set(roots);fids=[x.get('feature_id') if isinstance(x,dict) else None for x in features];need(all(isinstance(x,str) and x for x in fids) and len(set(fids))==len(fids),'invalid source feature IDs')
 need(isinstance(associations,list) and len(associations)==len(features) and isinstance(admin_features,dict) and 0<len(admin_features)<=1000,'invalid association set');by_feature={}
 for a in associations:
  need(isinstance(a,dict) and set(a)=={'selected_feature_id','administrative_feature_ids'} and a['selected_feature_id'] in fids and a['selected_feature_id'] not in by_feature and isinstance(a['administrative_feature_ids'],list) and 0<len(a['administrative_feature_ids'])<=1000 and all(isinstance(x,str) and x for x in a['administrative_feature_ids']) and len(set(a['administrative_feature_ids']))==len(a['administrative_feature_ids']),'invalid or duplicate association');by_feature[a['selected_feature_id']]=a['administrative_feature_ids']
 need(set(by_feature)==set(fids) and isinstance(admin_features,dict) and set(admin_features)=={x for v in by_feature.values() for x in v},'missing or unused administrative feature');admin={}
 for k,v in admin_features.items():
  need(isinstance(k,str) and k and isinstance(v,dict) and v.get('feature_id')==k and isinstance(v.get('geometry'),dict),'bad administrative feature');g=ogr.CreateGeometryFromJson(__import__('json').dumps(v['geometry'],allow_nan=False));need(g is not None and not g.IsEmpty() and g.IsValid(),'invalid administrative geometry');admin[k]=g
 perroot={r:set() for r in roots};observed_hits={r:[] for r in roots}
 for fid,h in zip(fids,hits):
  need(isinstance(h,dict),'invalid source hit map')
  for key,n in h.items():
   need(isinstance(key,str) and key.isascii() and key.isdigit() and (key=='0' or not key.startswith('0')) and type(n) is int and n>0,'invalid source hit');r=int(key);need(0<=r<0xffffffff,'invalid source root')
   if r in rootset:perroot[r].update(by_feature[fid]);observed_hits[r].append(n)
 need(all(perroot.values()),'selected root lacks source association')
 need(isinstance(grid,dict) and set(grid)=={'width','height','west','north','step'},'bad grid');w=grid['width'];h=grid['height'];s=grid['step'];need(type(w) is int and 1<w<=1000000 and type(h) is int and 0<h<=1000000 and type(s) in (int,float) and math.isfinite(s) and grid['west']==-180 and grid['north']==90 and Fraction(s)==Fraction(360,w) and h*Fraction(s)<=180,'unsupported global grid');names=('physical_rows','physical_runs','component_rows','component_runs');need(isinstance(inputs,dict) and set(inputs)==set(names) and all(isinstance(inputs[k],str) and Path(inputs[k]).is_file() for k in names),'invalid streams')
 stats={r:{'component_id_current_generation_only':r,'administrative_feature_ids':sorted(perroot[r]),'total_cells':0,'covered_centers':0,'outside_centers':0} for r in roots};total=0
 with open(inputs['physical_rows'],'rb') as pr,open(inputs['physical_runs'],'rb') as pv,open(inputs['component_rows'],'rb') as cr,open(inputs['component_runs'],'rb') as cv:
  for y in range(h):
   physical=pi.readrow(pr,pv,y,w,'physical');components=pi.readrow(cr,cv,y,w,'component');pi.equal_coverage(physical,components,w)
   for i,(a,b,root) in enumerate(components):
    if root not in stats:continue
    total+=b-a;row=stats[root]
    for x in range(a,b):
     point=ogr.Geometry(ogr.wkbPoint);point.AddPoint_2D(grid['west']+(x+.5)*s,grid['north']-(y+.5)*s);inside=any(admin[k].Intersects(point) for k in perroot[root]);row['total_cells']+=1;row['covered_centers']+=int(inside);row['outside_centers']+=int(not inside)
 need(all(v['total_cells']>0 and v['covered_centers']+v['outside_centers']==v['total_cells'] and all(n<=v['total_cells'] for n in observed_hits[r]) for r,v in stats.items()),'selected component missing or invalid source hits')
 return {'schema':'administrative-corroboration-report-v1','status':'research-only-not-a-decision','affiliation_id':claim['affiliation_id'],'rows':[stats[r] for r in sorted(stats)],'limitations':['Boundary-touching centers are counted as covered.','Administrative coverage is corroboration, not proof of island identity or a selection threshold.','Source-hit roots outside the selected claim are ignored, not independently adjudicated.','Source-custody, coordinate-order interpretation and source-association assertions require independent review.','The current source polygons provide the corroboration.']}
