import sys,json,hashlib,shapefile,collections,math
from shapely.geometry import LineString,shape
from shapely.strtree import STRtree
from shapely.ops import unary_union
from shapely import set_precision
from pyproj import Geod
sys.path.insert(0,'landed-1b494125')
from terrain_basin_screen import checked_shapes,digest_file
p='/tmp/ural-raw-chord-template.json';expected='87c92c1490692fd79a33c48fe365c9f44ffcc4c9705c243fae343f5185939705'
with open(p,'rb') as f:
 if digest_file(f)!=expected:raise ValueError('selected line hash mismatch')
source=json.load(open(p));bbox=(58.95,54.71,67.17,68.74);archive='/tmp/ural-hydro-eu.zip';digest='21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03';shp='/tmp/ural-hydro-eu/hybas_eu_lev12_v1c.shp';features=checked_shapes(archive,digest,shp,bbox);edges=[]
for geom,_ in features:
 for poly in getattr(geom,'geoms',[geom]):
  for ring in [poly.exterior,*poly.interiors]:
   xy=list(ring.coords)
   for a,b in zip(xy,xy[1:]):
    line=set_precision(LineString([a,b]),1e-12)
    if not line.is_empty:edges.append(line)
tree=STRtree(edges);geod=Geod(ellps='WGS84');ranges={'north':(4,1626),'middle':(1895,2319),'south':(3548,4939)};out={};bad=[]
for label,(start,end) in ranges.items():
 stats=collections.Counter();worst=[]
 for i in range(start,end):
  segment=set_precision(LineString(source[i:i+2]),1e-12)
  if segment.is_empty:stats['collapsed']+=1;continue
  candidates=[edges[j] for j in tree.query(segment)];remaining=segment.difference(unary_union(candidates)) if candidates else segment
  def line_lengths(g):
   if g.is_empty:return 0.
   if g.geom_type in ('LineString','LinearRing'):return abs(geod.geometry_length(g))
   if g.geom_type in ('MultiLineString','GeometryCollection'):return sum(line_lengths(x) for x in g.geoms)
   if g.geom_type in ('Point','MultiPoint'):return 0.
   raise ValueError('unexpected geometry '+g.geom_type)
  m=line_lengths(remaining);stats['segments']+=1
  if m<=0.001:stats['covered_to_1mm']+=1
  else:
   stats['uncovered_over_1mm']+=1;bad.append({'ordinal_zero_based':i,'remaining_wgs84_chord_sum_m':m});worst.append(m)
 out[label]={'counts':dict(stats),'largest_uncovered_wgs84_m':max(worst,default=0.)}
print(json.dumps({'source_line_sha256':expected,'eu_archive_sha256':digest,'rounding_degrees':1e-12,'ranges':out,'uncovered':bad,'method':'source polyline segment minus local union of rounded EU HydroBASINS polygon edge segments; WGS84 residual vertex-geodesic sum, no global search','limitations':['Matching polygon edges is source fidelity, not proof of correct basin convention or historical construction.','Rounding is angular topology precision, not geographic distance; exact paths may differ by sub-millimetre.','Residual WGS84 vertex chord sums approximate coordinate-linear edges without formal error bound.','The four northern connector vertices and the two terrain gaps are excluded.','No map build or selected boundary change.']},sort_keys=True))
