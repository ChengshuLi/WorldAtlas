#!/usr/bin/env python3
"""Inventory all scoped 2020 polygon components and their current Georef intersections."""
import csv,json,pathlib
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer
ROOT=pathlib.Path(__file__).resolve().parents[3]
OWN=ROOT/'data/regional-review/argentina-adm2-source-revalidation-443'
PARENT=ROOT/'data/regional-review/regional-review-7cf674a63057d43f'
old=json.load(open(OWN/'source/geoBoundaries-2020-scoped-214.geojson'))['features']
current=json.load(open(OWN/'source/Georef-current/departamentos.geojson'))['features']
with (PARENT/'findings/scoped-location-review.csv').open(encoding='utf-8',newline='') as f: atlas={r['original_id']:r for r in csv.DictReader(f) if r['location_id'].startswith('gb:ARG:ADM2:')}
project=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform
geoms=[(ft,transform(project,shape(ft['geometry']))) for ft in current]
rows=[]
for ft in old:
    g=transform(project,shape(ft['geometry']))
    components=list(g.geoms) if g.geom_type=='MultiPolygon' else [g]
    if len(components)==1 and not sum(len(p.interiors) for p in components): continue
    p=ft['properties']; ar=atlas[p['shapeID']]
    for i,c in enumerate(components,1):
        hits=[]
        for cft,cg in geoms:
            a=c.intersection(cg).area
            if a>1: hits.append((a,cft))
        hits.sort(key=lambda q:q[0],reverse=True)
        rows.append({'atlas_id':ar['location_id'],'atlas_name':ar['atlas_name'],'source_shape_id':p['shapeID'],
          'component_number':i,'component_count':len(components),'component_area_km2':round(c.area/1e6,6),
          'interior_ring_count':len(c.interiors),
          'current_positive_area_intersections':json.dumps([{'id':q[1]['properties']['id'],'name':q[1]['properties']['nombre'],'province':q[1]['properties']['provincia']['nombre'],'category':q[1]['properties']['categoria']} for q in hits],ensure_ascii=False,separators=(',',':')),
          'interpretation':'Recorded source component and current statistical-layer overlays; component existence does not establish island/exclave identity or completeness.'})
out=OWN/'findings/scoped-multipart-components.csv'
with out.open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary={'features':len({r['source_shape_id'] for r in rows}),'component_rows':len(rows),'interior_rings':sum(r['interior_ring_count'] for r in rows),
 'components_by_shape_id':{r['source_shape_id']:r['component_count'] for r in rows if r['component_number']==1},
 'interior_rings_by_shape_id':{r['source_shape_id']:sum(x['interior_ring_count'] for x in rows if x['source_shape_id']==r['source_shape_id']) for r in rows if r['component_number']==1}}
(OWN/'findings/component-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
