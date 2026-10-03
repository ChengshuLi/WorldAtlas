#!/usr/bin/env python3
"""Reproduce source/current geometry diagnostics; requires GDAL/OGR Python bindings."""
import gzip, json, pathlib
from osgeo import ogr, osr
P=pathlib.Path(__file__).resolve().parent; ROOT=P.parents[2]; S=P/'sources'
scope=json.loads((P/'issue-scope.json').read_text()); ids=set(scope['member_location_ids']); audit={'subjects':[json.loads(line) for line in (P/'audit.jsonl').read_text().splitlines() if line.strip()]};
index=json.loads((ROOT/'data/world-index.json').read_text()); current={}
for rel in index['parts']:
 for f in json.loads((ROOT/'data'/rel).read_text()).get('features',[]):
  if f['id'] in ids: current[f['id']]=f
source_data=json.loads(gzip.decompress((S/'geoboundaries-COL-ADM2-geojson.json.gz').read_bytes()))
source={f['properties']['shapeID']:f for f in source_data['features']}
srs=osr.SpatialReference(); srs.ImportFromEPSG(4326); target=osr.SpatialReference(); target.ImportFromEPSG(6933); transform=osr.CoordinateTransformation(srs,target)
def geom(f):
 g=ogr.CreateGeometryFromJson(json.dumps(f['geometry'])); g.Transform(transform); return g
def add_polygons(out,g):
 if g.GetGeometryName()=='POLYGON': out.AddGeometry(g)
 elif g.GetGeometryName()=='MULTIPOLYGON':
  for i in range(g.GetGeometryCount()): out.AddGeometry(g.GetGeometryRef(i))
 elif g.GetGeometryName()=='GEOMETRYCOLLECTION':
  for i in range(g.GetGeometryCount()): add_polygons(out,g.GetGeometryRef(i))
rows=[]; failures=[]; grouped={}; audit_by_id={r['location_id']:r for r in audit['subjects']}
for row in audit['subjects']:
 id=row['location_id']; a=geom(current[id]); b=geom(source[row['geoBoundaries_shape_id']]); invalid_current=not a.IsValid(); invalid_source=not b.IsValid()
 grouped.setdefault(row['department'],{'current':[],'source':[],'invalid_current':0,'invalid_source':0,'locations':0})
 group=grouped[row['department']]; group['locations']+=1; group['invalid_current']+=invalid_current; group['invalid_source']+=invalid_source
 group['current'].append(a.Clone()); group['source'].append(b.Clone())
 area_delta=abs(a.GetArea()-b.GetArea())/b.GetArea() if b.GetArea() else None
 if invalid_current or invalid_source:
  failures.append({'id':id,'name':row['name'],'department':row['department'],'invalid_current':invalid_current,'invalid_source':invalid_source,'relative_area_difference':area_delta}); assert audit_by_id[id]['geometry_comparison']['status']=='invalid overlay'; continue
 diff=a.SymDifference(b); share=diff.GetArea()/b.GetArea(); rows.append({'id':id,'relative_area_difference':area_delta,'symmetric_difference_fraction':share}); expected=audit_by_id[id]['geometry_comparison']; assert abs(expected['area_fraction_difference']-area_delta)<1e-10 and abs(expected['symmetric_difference_fraction']-share)<1e-10
print('Individual source/current overlays:',len(rows),'successful,',len(failures),'invalid input pairs')
print('Maximum absolute individual area difference:',max(x['relative_area_difference'] for x in rows+failures))
print('Maximum symmetric-difference share:',max(x['symmetric_difference_fraction'] for x in rows))
def valid_polygon_union(items):
 multi=ogr.Geometry(ogr.wkbMultiPolygon)
 for g in items:
  candidate=g if g.IsValid() else g.MakeValid()
  if candidate is None: raise RuntimeError('MakeValid failed during diagnostic union')
  add_polygons(multi,candidate)
 return multi.UnionCascaded()
summary=[]
for department,g in grouped.items():
 current_union=valid_polygon_union(g['current']); source_union=valid_polygon_union(g['source']); sd=current_union.SymDifference(source_union); sa=source_union.GetArea(); ca=current_union.GetArea()
 summary.append({'department':department,'locations':g['locations'],'current_union_area_km2':ca/1e6,'source_union_area_km2':sa/1e6,'relative_area_delta':(ca-sa)/sa,'union_symmetric_difference_fraction':sd.GetArea()/sa,'invalid_current_inputs_made_valid_for_union':g['invalid_current'],'invalid_source_inputs_made_valid_for_union':g['invalid_source']})
for r in summary: print(r['department'],r['locations'],'units; union symmetric difference',f"{100*r['union_symmetric_difference_fraction']:.3f}%",'invalid inputs normalized',r['invalid_current_inputs_made_valid_for_union'],r['invalid_source_inputs_made_valid_for_union'])
json.dump({'method':'OGR EPSG:6933. For aggregate-only diagnostics, invalid clones were normalized with MakeValid before union; no published geometry was changed. Each union contains only the 2020 source or current features for the assigned municipalities. It does not prove external department-envelope coverage or lack of omitted physical land.','departments':summary},open(P/'department-union-comparison.json','w'),indent=2)
