"""Rebuild approved Anapa opening from a source-replayed baseline and pinned OSM coast."""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
from shapely.geometry import LineString
from shapely.ops import substring
from geodesic_line import GeodesicLine
p=argparse.ArgumentParser()
for key in ('baseline','author','coast','recipe','output'):p.add_argument('--'+key,required=True)
a=p.parse_args();recipe=json.loads(Path(a.recipe).read_bytes());decision=recipe['anapa'];baseline=LineString(json.loads(Path(a.baseline).read_bytes())['geometry']['coordinates']);author=LineString(json.loads(Path(a.author).read_bytes())['features'][decision['author_feature_index']]['geometry']['coordinates'])
r=ET.parse(a.coast).getroot();nodes={n.get('id'):(float(n.get('lon')),float(n.get('lat'))) for n in r.findall('node')};w=[v for v in r.findall('way') if v.get('id')==decision['coast_way_id'] and v.get('version')==decision['coast_way_version']];assert len(w)==1
coastline=LineString([nodes[v.get('ref')] for v in w[0].findall('nd')]);coast=author.intersection(coastline)
if coast.geom_type!='Point':raise ValueError('coastal intersection is not unique')
hits=baseline.intersection(author);points=[hits] if hits.geom_type=='Point' else [x for x in hits.geoms if x.geom_type=='Point'];gbase=GeodesicLine(list(baseline.coords));gauthor=GeodesicLine(list(author.coords));coast_s=gauthor.closest((coast.x,coast.y))['station_m'];selected=[]
for x in points:
 if gauthor.closest((x.x,x.y))['station_m']<coast_s:selected.append((gbase.closest((x.x,x.y))['station_m'],x))
selected.sort(key=lambda v:v[0]);join=selected[decision['intersection_index']][1]
# project/substring locate already coincident points on coordinate-linear source edges.
opening=list(substring(author,author.project(join),author.project(coast)).coords)[::-1];retained=list(substring(baseline,baseline.project(join),baseline.length).coords);opening[-1]=(join.x,join.y);retained[0]=(join.x,join.y);out=LineString(opening+retained[1:]);assert out.is_simple and out.coords[0]==(coast.x,coast.y)
geo={'type':'LineString','coordinates':[[float(x),float(y)] for x,y in out.coords]};raw=json.dumps(geo,sort_keys=True,separators=(',',':'),allow_nan=False).encode();Path(a.output).write_bytes(raw);print(json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),'vertices':len(out.coords),'join':[join.x,join.y],'coast':[coast.x,coast.y],'candidate_intersections':len(selected)}))

