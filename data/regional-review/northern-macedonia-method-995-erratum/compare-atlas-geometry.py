#!/usr/bin/env python3
"""Compare stored Atlas geometry objects to the retained 2016 source objects."""
import hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[3]; BASE='b6cfaada43a1e0472cd833d16733d1fd6065eaec'
def blob(path):
 row=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-z',BASE,'--',path]).decode().rstrip('\0')
 if not row.startswith('100644 ') or row.split('\t',1)[-1]!=path: raise ValueError('nonordinary/missing baseline input')
 return subprocess.check_output(['git','-C',str(ROOT),'show',f'{BASE}:{path}'])
def nvertices(g):
 def walk(x):
  if isinstance(x,list):
   if len(x)>=2 and all(isinstance(v,(int,float)) for v in x[:2]): return 1
   return sum(walk(y) for y in x)
  return 0
 return walk(g['coordinates'])
geo_raw=blob('data/regional-review/regional-review-3c4fe25a21fa428d/source/gb/gb-MKD-ADM2.geojson')
atlas_raw=blob('data/geography/part-15.json')
geo=json.loads(geo_raw); part=json.loads(atlas_raw)
source={'gb:MKD:ADM2:'+f['properties']['shapeID']:f for f in geo['features']}
atlas={f.get('id') or f.get('properties',{}).get('id'):f for f in part['features']}
if len(source)!=84 or not source.keys()<=atlas.keys(): raise ValueError('subject roster mismatch')
rows=[]
for sid,f in sorted(source.items()):
 a=atlas[sid]; sg=f['geometry']; ag=a['geometry']
 rows.append({'location_id':sid,'exact_geometry_object_equal':sg==ag,'source_coordinate_vertices':nvertices(sg),'atlas_coordinate_vertices':nvertices(ag),'atlas_has_fewer_vertices':nvertices(ag)<nvertices(sg)})
report={'version':1,'baseline_commit':BASE,'source_path':'data/regional-review/regional-review-3c4fe25a21fa428d/source/gb/gb-MKD-ADM2.geojson','source_sha256':hashlib.sha256(geo_raw).hexdigest(),'atlas_path':'data/geography/part-15.json','atlas_sha256':hashlib.sha256(atlas_raw).hexdigest(),'comparison':'exact parsed GeoJSON geometry-object equality and coordinate-vertex counts; no spatial-distance claim','subjects':len(rows),'exact_equal_count':sum(x['exact_geometry_object_equal'] for x in rows),'atlas_fewer_vertex_count':sum(x['atlas_has_fewer_vertices'] for x in rows),'rows':rows,'limits':['This is representation comparison only, not geographic equivalence, boundary validity, or a distance measurement.']}
out=ROOT/'data/regional-review/northern-macedonia-method-995-erratum/v1/atlas-geometry-check.json'
with out.open('x',encoding='utf-8') as stream: stream.write(json.dumps(report,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps({'subjects':len(rows),'exact_equal':report['exact_equal_count'],'atlas_fewer_vertices':report['atlas_fewer_vertex_count']}))
