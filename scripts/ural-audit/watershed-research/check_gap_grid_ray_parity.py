import json,math
from shapely.geometry import LineString,Point
from shapely.ops import unary_union,polygonize
step=0.00274658203125
for n in ('00','02'):
 for kind,bn in [('30m-arctic','d8-interface-research'),('30m-cop','cop-d8-interface-research'),('30m-smaller-domain','d8-smaller-domain-research')]:
  a=LineString(json.load(open('/tmp/ural-gap'+n+'-d8-15m-research.json'))['coordinates']);b=LineString(json.load(open('/tmp/ural-gap'+n+'-'+bn+'.json'))['coordinates']);shape=unary_union(list(polygonize(unary_union([a,b]))));w,s,e,top=shape.bounds;witness=(w-.034963219,s-.041231234);checks=0;diff=[]
  def parity(g):
   if g.is_empty:return 0
   if g.geom_type=='Point':return 1
   if g.geom_type=='MultiPoint':return len(g.geoms)%2
   raise ValueError('ambiguous intersection '+g.geom_type)
  for y in range(math.ceil((90-top)/step-.5),math.floor((90-s)/step-.5)+1):
   for x in range(math.ceil((w+180)/step-.5),math.floor((e+180)/step-.5)+1):
    pt=Point(-180+(x+.5)*step,90-(y+.5)*step); ray=LineString([witness,(pt.x,pt.y)])
    if shape.boundary.intersects(pt):raise ValueError('center on boundary')
    actual=shape.contains(pt);expected=bool(parity(a.intersection(ray))^parity(b.intersection(ray)));checks+=1
    if actual!=expected:diff.append((x,y))
  print(n,kind,'grid_centers',checks,'mismatches',len(diff),diff[:5])
