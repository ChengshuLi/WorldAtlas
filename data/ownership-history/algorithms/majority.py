"""Ellipsoidal land area and strict majority decisions, independent of rendering."""
import math
from shapely import make_valid,union_all,segmentize
from shapely.geometry import Polygon,box
from shapely.affinity import translate
from shapely.geometry.polygon import orient
from pyproj import Geod
GEOD=Geod(ellps='WGS84')
def polygons(g):
 if g.geom_type=='Polygon':return [g]
 return [p for x in getattr(g,'geoms',[]) for p in polygons(x)]
def canonical(g):
 result=[]
 for p in polygons(make_valid(g)):
  def unwrap(r):
   out=[]
   for x,y in r.coords:
    if out:x+=360*round((out[-1][0]-x)/360)
    out.append((x,y))
   return out
  outer=unwrap(p.exterior);center=sum(x for x,y in outer)/len(outer);holes=[]
  for h in p.interiors:
   ring=unwrap(h);shift=360*round((center-sum(x for x,y in ring)/len(ring))/360);holes.append([(x+shift,y) for x,y in ring])
  q=make_valid(Polygon(outer,holes));lo,_,hi,_=q.bounds
  for n in range(math.floor((lo+180)/360),math.floor((hi+180)/360)+1):
   cut=q.intersection(box(-180+360*n,-90,180+360*n,90))
   if not cut.is_empty:result.append(translate(cut,xoff=-360*n))
 return union_all(result)
def area(g):return sum(abs(GEOD.geometry_area_perimeter(orient(p,sign=1))[0]) for p in polygons(segmentize(g,.1)))
def decide(location,claims,total=None,preclipped=False,cache=None):
 total=total or area(location);groups={};cache=cache if cache is not None else {}
 sizes=cache.setdefault('areas',{});unions=cache.setdefault('unions',{});intersections=cache.setdefault('intersections',{})
 def measured_area(g):
  if g is location:return total
  key=id(g)
  if key not in sizes:sizes[key]=area(g)
  return sizes[key]
 def combined(geoms):
  gs={id(g):g for g in geoms}
  if id(location) in gs:return location
  if len(gs)==1:return next(iter(gs.values()))
  key=tuple(sorted(gs))
  if key not in unions:unions[key]=union_all(list(gs.values()))
  return unions[key]
 for owner,geoms in claims.items():
  local=geoms if preclipped else [location if g.covers(location) else g.intersection(location) for g in geoms]
  groups[owner]=location if any(g is location or g.equals(location) for g in local) else combined(local)
 measured={owner:measured_area(g) for owner,g in groups.items()}
 shares={owner:min(1,size/total) for owner,size in measured.items() if size>total*1e-8}
 ordered=sorted(shares,key=lambda k:(-shares[k],k));coverage=1 if any(g is location for g in groups.values()) else min(1,measured_area(combined(groups.values()))/total) if groups else 0
 def overlap(a,b):
  if groups[a] is location:return measured[b]
  if groups[b] is location:return measured[a]
  key=tuple(sorted((id(groups[a]),id(groups[b]))))
  if key not in intersections:intersections[key]=area(groups[a].intersection(groups[b]))
  return intersections[key]
 conflict=any(overlap(a,b)>total*1e-6 for i,a in enumerate(ordered) for b in ordered[i+1:])
 status='disputed' if conflict else 'derived' if ordered and shares[ordered[0]]>.50000001 else 'no-majority' if ordered else 'unknown'
 return {'owner':ordered[0] if status=='derived' else None,'status':status,'share':round(shares[ordered[0]],12) if ordered else 0,'coverage':round(coverage,12),'candidates':[[o,round(shares[o],12)] for o in ordered]}
