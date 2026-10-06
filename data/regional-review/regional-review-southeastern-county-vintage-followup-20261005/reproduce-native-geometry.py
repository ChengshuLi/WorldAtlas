#!/usr/bin/env python3
"""Read-only native geometry audit for issue #978; outputs stay in this packet."""
import csv, hashlib, json, os
from pathlib import Path
from shapely.geometry import shape
from shapely.validation import explain_validity
from shapely.ops import transform
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
PRIOR=ROOT/'data/regional-review/regional-review-599d6fe712bbbcae'
IDS={
'gb:USA:ADM2:52423323B10934602069357':('Jackson','28059','28'),
'gb:USA:ADM2:52423323B16895111765374':('Moore','47127','47'),
'gb:USA:ADM2:52423323B27952664457255':('Harrison','28047','28'),
'gb:USA:ADM2:52423323B49198903326940':('Hancock','28045','28'),
'gb:USA:ADM2:52423323B60515004813393':('Baldwin','01003','01'),
'gb:USA:ADM2:52423323B65626355292212':('Mobile','01097','01')}

def load(path): return json.loads(path.read_text())['features']
def hashfile(path): return hashlib.sha256(path.read_bytes()).hexdigest()

gb_path=PRIOR/'sources/geoboundaries-2018/geoBoundaries-USA-ADM2.geojson'
rows=[]
for rel in ['sources/census-tigerweb-acs26/counties-state-01.geojson','sources/census-tigerweb-acs26/counties-state-28.geojson','sources/census-tigerweb-acs26/counties-state-47.geojson']:
 for feat in load(PRIOR/rel):
  p=feat['properties']
  if p['GEOID'] in {v[1] for v in IDS.values()}:
   rows.append((p['GEOID'],feat,rel))
cbf={}
for r in csv.DictReader((PRIOR/'findings/usa-county-crosswalk.csv').open()):
 if r['atlas_id'] in IDS: cbf[r['atlas_id']]=r
atlas_records={}
for part in ['25','26','27']:
 for feat in load(ROOT/f'data/geography/part-{part}.json'):
  if feat.get('id') in IDS: atlas_records[feat['id']]=feat
source_features=load(gb_path)
byid={f['properties']['shapeID']:f for f in source_features}
summary=[]
to5070=Transformer.from_crs('EPSG:4326','EPSG:5070',always_xy=True).transform
for ident,(name,geoid,state) in IDS.items():
 src=byid[ident.rsplit(':',1)[1]]
 atlas=atlas_records[ident]
 assert src['properties']['shapeName']==name
 assert atlas['properties']['name']==name and atlas['properties']['parent_id']==cbf[ident]['parent_id']
 census,rel=next((f,r) for g,f,r in rows if g==geoid)
 assert census['properties']['GEOID']==geoid and census['properties']['STATE']==state and census['properties']['NAME']==name+' County' and census['properties']['LSADC']=='06'
 def describe(feat):
  geom=shape(feat['geometry'])
  pieces=list(geom.geoms) if geom.geom_type=='MultiPolygon' else [geom]
  return {'type':geom.geom_type,'valid':geom.is_valid,'validity_reason':explain_validity(geom),'bounds':list(geom.bounds),
          'components':len(pieces),'holes':sum(len(p.interiors) for p in pieces),'vertices':sum(len(p.exterior.coords)+sum(len(h.coords) for h in p.interiors) for p in pieces),
          'area_degrees2':geom.area,'empty':geom.is_empty}
 src_geom=shape(src['geometry']); tiger_geom=shape(census['geometry'])
 projected_src=transform(to5070,src_geom); projected_tiger=transform(to5070,tiger_geom)
 reproduced_tiger_iou=projected_src.intersection(projected_tiger).area/projected_src.union(projected_tiger).area
 summary.append({'id':ident,'name':name,'geoid':geoid,'state':state,'census_source':rel,'state_layer_feature_count':len(load(PRIOR/rel)),
   'atlas_identity':{'name':atlas['properties']['name'],'parent_id':atlas['properties']['parent_id'],'geometry':describe(atlas),'matches_expected_name_parent':atlas['properties']['name']==name and atlas['properties']['parent_id']==cbf[ident]['parent_id']},
   'geoboundaries':describe(src),'tigerweb_2026':describe(census),'prior_diagnostic_iou_2018_cbf':float(cbf[ident]['2018_cb_iou']),
   'prior_diagnostic_iou_2026_tigerweb':float(cbf[ident]['2026_tiger_iou']),'reproduced_2026_tigerweb_iou':round(reproduced_tiger_iou,8),
   'baseline_parent':cbf[ident]['parent_id'],'census_name':census['properties']['NAME'],'lsadc':census['properties']['LSADC']})
output={'version':1,'status':'native geometry integrity and representation triage; not a boundary accuracy determination',
 'inputs':{str(p.relative_to(ROOT)):hashfile(p) for p in [gb_path,PRIOR/'findings/usa-county-crosswalk.csv']+[ROOT/f'data/geography/part-{n}.json' for n in ['25','26','27']]+[PRIOR/f'sources/census-tigerweb-acs26/counties-state-{s}.geojson' for s in ['01','28','47']]},
 'software':{'python':os.sys.version.split()[0]},'geometry_method':'Validity/component audit occurs in native EPSG:4326. For crosswalk reproduction only, transform valid 2D polygons to EPSG:5070 with pyproj always_xy and calculate intersection area / union area; no repair or threshold acceptance.',
 'subjects':summary}
(OUT/'native-geometry-audit.json').write_text(json.dumps(output,sort_keys=True,indent=2)+'\n')
print(json.dumps(output,indent=2))
