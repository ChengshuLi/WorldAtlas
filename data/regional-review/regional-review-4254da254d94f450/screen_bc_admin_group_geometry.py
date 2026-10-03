#!/usr/bin/env /usr/bin/python3
"""Compare all 19 current BC administrative group polygons to their 376 2016 ADM3 members."""
import gzip,json,hashlib
from pathlib import Path
from osgeo import ogr,osr
P=Path(__file__).resolve().parent;S=P/'sources';ogr.UseExceptions()
def read(p):
 with gzip.open(p,'rt',encoding='utf-8') if p.suffix=='.gz' else p.open(encoding='utf-8') as f:return json.load(f)
srs=osr.SpatialReference();srs.ImportFromEPSG(3347);srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
def geom(obj):
 g=ogr.CreateGeometryFromJson(json.dumps(obj,separators=(',',':')));w=osr.SpatialReference();w.ImportFromEPSG(4326);w.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);g.AssignSpatialReference(w);g.TransformTo(srs)
 fixed=not bool(g.IsValid())
 if fixed:g=g.MakeValid()
 def collect(x,o):
  if x.GetGeometryName()=='POLYGON':o.AddGeometry(x)
  elif x.GetGeometryName() in ('MULTIPOLYGON','GEOMETRYCOLLECTION'):
   for i in range(x.GetGeometryCount()):collect(x.GetGeometryRef(i),o)
 out=ogr.Geometry(ogr.wkbMultiPolygon);collect(g,out)
 if out.IsEmpty() or not out.IsValid():raise ValueError('unusable source geometry after temporary repair')
 return out,fixed
def union(xs):
 out=None
 for g in xs:out=g.Clone() if out is None else out.Union(g)
 return out
def pct(a,b):return round(a.Intersection(b).GetArea()/max(b.GetArea(),1)*100,6)
def km2(g):return round(g.GetArea()/1e6,6)
sc=read(P/'scope.json');ids=set(sc['member_location_ids']);fc=read(S/'current-scope-and-parents.geojson.gz');current={f['properties']['id']:f for f in fc['features']};allsource=read(S/'geoboundaries-CAN-ADM3-2016.geojson');byid={f['properties']['shapeID']:f for f in allsource['features']}
rows=[];used=[]
for lid in sorted(i for i in ids if i.startswith('atlas:district:CAN-')):
 p=current[lid]['properties'];members=p['metadata']['source_member_ids'];ids0=[x.rsplit(':',1)[1] for x in members]
 assert len(ids0)==len(set(ids0));used.extend(ids0);assert all(x in byid for x in ids0)
 src=[geom(byid[x]['geometry']) for x in ids0];sg=union([x[0] for x in src]);cg,_=geom(current[lid]['geometry'])
 rows.append({'location_id':lid,'name':p['name'],'member_count':len(ids0),'member_ids':sorted(ids0),'members_all_in_retained_national_2016_file':True,'source_union_area_km2':km2(sg),'current_location_area_km2':km2(cg),'source_overlap_over_current_pct':pct(sg,cg),'current_overlap_over_source_pct':pct(cg,sg),'symmetric_difference_km2':km2(sg.SymDifference(cg)),'temporary_source_members_repaired':sum(x[1] for x in src),'decision':'geometry-vintage comparison only; differences require source-member successor reconciliation; no boundary correction inferred'})
assert len(rows)==19 and len(used)==376 and len(set(used))==376
r={'scope_location_count':len(rows),'source_member_count':len(used),'source_ids_sha256':hashlib.sha256(('\n'.join(sorted(used))+'\n').encode()).hexdigest(),'projection':'EPSG:3347 from EPSG:4326; input source geometries are not modified; invalid transformed polygons are temporarily MakeValid-repaired and repair counts are retained.','method':'For every one of the 19 current BC administrative group locations, form a union of all exact source_member_ids from the retained national 2016 geoBoundaries Canada ADM3 file, overlay it with that current group geometry, and report both-direction area ratios, symmetric difference, member roster and temporary repair count.','limitations':['2016 local-unit source vintage differs from the current grouped locations. Differences are triage signals, not legal successor decisions.','The comparison does not determine political ownership or a corrected footprint; named CSD transitions and exact successor evidence are addressed by bounded follow-up #607.'],'locations':rows}
(P/'bc-admin-group-geometry-screen.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'locations':len(rows),'members':len(used),'minimum_source_in_current_pct':min(x['source_overlap_over_current_pct'] for x in rows),'minimum_current_in_source_pct':min(x['current_overlap_over_source_pct'] for x in rows),'max_symdiff_km2':max(x['symmetric_difference_km2'] for x in rows)},indent=2))
