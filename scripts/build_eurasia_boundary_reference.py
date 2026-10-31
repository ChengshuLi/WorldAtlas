"""Build the reference divide from a CC-BY BasinATLAS subset and OSM river.

Inputs are retained as immutable evidence alongside each review release.
Coastal endpoints are snapped to the accepted native mask in a separate step.
"""
import json,gzip,argparse,numpy as np
from shapely.geometry import shape,box,Point,LineString,mapping
from shapely.ops import unary_union,nearest_points,substring
from pathlib import Path

parser=argparse.ArgumentParser();parser.add_argument('basins',type=Path);parser.add_argument('river',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
basins=json.loads(gzip.decompress(args.basins.read_bytes()))
def load(level):
 return [(f['properties'],shape(f['geometry'])) for f in basins['features'] if f['properties']['level']==level]
def biggest(g):return max(g.geoms,key=lambda p:p.area) if g.geom_type=='MultiPolygon' else g

def arc(ring,a,b,guide=None):
 line=LineString(ring.coords);x=line.project(Point(a));y=line.project(Point(b));lo,hi=sorted([x,y]);one=substring(line,lo,hi);two=LineString(list(substring(line,hi,line.length).coords)+list(substring(line,0,lo).coords)[1:]);choices=[one,two]
 if guide:best=min(choices,key=lambda z:sum(z.distance(Point(q)) for q in guide))
 else:best=min(choices,key=lambda z:z.length)
 coords=list(best.coords)
 if Point(coords[0]).distance(Point(a))>Point(coords[-1]).distance(Point(a)):coords.reverse()
 return coords
rs=load(6);eu=biggest(unary_union([g.intersection(box(50,53,75,72)) for d,g in load(4) if g.intersects(box(50,53,75,72))]));kara=next(g for d,g in rs if d['HYBAS_ID']==2060044660);konst=Point(66.23528,68.48528)
join=nearest_points(konst,kara.boundary.intersection(eu.boundary))[1];north=nearest_points(konst,kara.boundary)[1]
river=shape(json.loads(args.river.read_text())['geometry']);rcoords=list(river.coords)
if rcoords[0][1]<rcoords[-1][1]:rcoords.reverse()
source=rcoords[0];south=nearest_points(Point(source),eu.boundary)[1]
coast=[67.19512939453125,68.70849609375]
u=[coast]+arc(kara.exterior,(north.x,north.y),(join.x,join.y))+arc(eu.exterior,(join.x,join.y),(south.x,south.y),[(64.392,66.72),(60.115,65.033),(59.5,62),(60.1,57)])[1:]+[source]
roots={2060006110,2060069150,2060069200,2060069480,2060069490,2060069160,2060069210}
anapka=next(g for d,g in load(8) if d['HYBAS_ID']==2080005990)
c=biggest(unary_union([g for d,g in rs if d['MAIN_BAS'] in roots]+[anapka]));print('north caucasus',c.geom_type,c.bounds)
# Western/southeastern ends of the actual watershed footprint. Coast connectors
# will be snapped separately to the accepted Black/Caspian water masks.
western_crest=min(list(anapka.exterior.coords),key=lambda q:q[1]);w=nearest_points(Point(western_crest),c.boundary)[1];e=nearest_points(Point(49.6125,40.6166667),c.boundary)[1]
ca=arc(c.exterior,(w.x,w.y),(e.x,e.y),[(42,43.2),(44.45,42.5),(47.79,41.27)])
features=[{'type':'Feature','properties':{'name':'Urals watershed','source':'BasinATLAS v1.0 EU/Siberia and Kara watershed; northern coastal connector to accepted shore','note':'Reference resolution coarser north60N; coastal lowland connector is editorial.'},'geometry':mapping(LineString(u))},{'type':'Feature','properties':{'name':'Ural River','source':'https://www.openstreetmap.org/relation/214415','license':'ODbL; © OpenStreetMap contributors'},'geometry':mapping(LineString(rcoords))},{'type':'Feature','properties':{'name':'Greater Caucasus watershed','source':'BasinATLAS v1.0; north-facing Kuban/Terek/Sulak/Samur and northeastern Caspian catchments','basin_roots':sorted(roots),'additional_basin':2080005990},'geometry':mapping(LineString(ca))}]
features[0]['properties']['northern_lowland_connector']={'from':coast,'to':[north.x,north.y],'note':'Editorial continuation from the northern Ural ridge near Konstantinov Kamen to the accepted Baydaratskaya shoreline, approximately 46 km.'}
for i in [0,2]:features[i]['properties'].update(license='CC BY 4.0',source_url='https://doi.org/10.6084/m9.figshare.9890531',attribution='Linke et al. (2019), HydroATLAS/BasinATLAS v1.0')
json.dump({'type':'FeatureCollection','features':features},args.output.open('w'));print('Urals',len(u),u[0],u[-1]);print('Caucasus',len(ca),ca[0],ca[-1]);print('Kara join',join,'north ridge point',north)
for p in [(44.51194,42.55944),(48.5125,41.3597),(43.17,43.01),(44.45,42.5)]:print('Caucasus landmark',p,'distance to ridge degrees',LineString(ca).distance(Point(p)))
