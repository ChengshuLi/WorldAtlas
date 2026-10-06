#!/usr/bin/env python3
"""Compare served MDB 2021 and prospective 2026 Eastern Cape footprints.

Diagnostics only: no area threshold authorizes replacement or approval. Both inputs
are ArcGIS REST responses, not MDB original shapefile bytes. Uses the repository's
shared WGS84 straight-source-edge ellipsoidal area helper.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[3]
PACKET=ROOT/'data/regional-review/eastern-cape-source-restoration-435'
SRC=PACKET/'sources'; OUT=PACKET/'findings'/'boundary-vintage-differences.json'
sys.path.insert(0,str(ROOT/'scripts'))
from evidence.geometry import METHOD, VERSION, canonical_land, land_area_m2

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n): return json.loads((SRC/n).read_text())

a21=load('mdb-2021-eastern-cape-attribute-roster.json')['features']
g21=load('mdb-2021-eastern-cape-boundaries.geojson')['features']
a26=load('mdb-2026-eastern-cape-attribute-roster.json')['features']
g26=load('mdb-2026-eastern-cape-boundaries.geojson')['features']
# Crosswalk by official municipal code; geometry uses same stable code property.
attr21={f['attributes']['CAT_B']:f['attributes'] for f in a21}
attr26={f['attributes']['CAT_B']:f['attributes'] for f in a26}
geo21={f['properties']['CAT_B']:f for f in g21}; geo26={f['properties']['CAT_B']:f for f in g26}
assert set(geo21)==set(geo26)==set(attr21)==set(attr26) and len(geo21)==33
prev={}; rows=[]
for code in sorted(attr21):
    old=shape(geo21[code]['geometry']); new=shape(geo26[code]['geometry'])
    oldland=canonical_land(old); newland=canonical_land(new)
    oldarea=land_area_m2(old); newarea=land_area_m2(new)
    xor=oldland.symmetric_difference(newland)
    polys=[]
    if xor.geom_type=='Polygon': polys=[xor]
    elif xor.geom_type=='MultiPolygon': polys=list(xor.geoms)
    elif xor.geom_type=='GeometryCollection': polys=[g for g in xor.geoms if g.geom_type=='Polygon' and not g.is_empty]
    else: raise ValueError(f'Unexpected symmetric-difference type {xor.geom_type}: {code}')
    xorland=unary_union(polys)
    changed=land_area_m2(xorland) if not xorland.is_empty else 0.0
    inter=oldland.intersection(newland)
    union=oldland.union(newland)
    union_area=land_area_m2(union)
    iou=land_area_m2(inter)/union_area
    rows.append({'municipality_code':code,'name_2021':attr21[code]['MUNICNAME'],'name_2026':attr26[code]['MUNICNAME'],
      'category_2021':attr21[code]['CATEGORY'],'district_2021':attr21[code].get('CAT_C'),
      'area_2021_m2':oldarea,'area_2026_m2':newarea,'net_area_change_m2':newarea-oldarea,
      'symmetric_difference_m2':changed,'intersection_over_union':iou,
      'old_polygon_parts':len(list(oldland.geoms)) if oldland.geom_type=='MultiPolygon' else 1,
      'new_polygon_parts':len(list(newland.geoms)) if newland.geom_type=='MultiPolygon' else 1,
      'status':'identical' if changed == 0 else 'different'})
    prev[code]=(old,new)
# method controls: identical geometry gives zero difference and IoU 1; paired
# confirmed gazette feature codes are positive relevance controls, without treating
# their full polygon deltas as exact village area.
ctl_old,ctl_new=prev['EC135']; ctl_old=canonical_land(ctl_old); ctl_new=canonical_land(ctl_new)
neg=ctl_old.symmetric_difference(ctl_old)
assert neg.is_empty and land_area_m2(ctl_old.intersection(ctl_old))/land_area_m2(ctl_old)==1
positive={}
for code in ('EC135','EC138','EC137'):
    r=next(x for x in rows if x['municipality_code']==code)
    positive[code]={'gazette_decision_in_scope':True,'symmetric_difference_m2':r['symmetric_difference_m2'],'interpretation':'Positive relevance control: an official notice confirms a change within this municipality; full-municipality symmetric difference is not the named village or administrative area measurement.'}
result={'method_id':'boundary-vintage-measurement','kind':'measurement','outcome':'passed','version':1,'issue':1137,'baseline_commit':'e8138aef2004b419cb8c458ccc1fb2ce31b639f6','evaluated_at':'2026-10-06',
 'method':dict(METHOD,helper_version=VERSION,comparison='two full official MDB served municipality polygons matched by CAT_B; WGS84 land symmetric difference; intersection-over-union; no snapping or MakeValid'),
 'inputs':[{'path':f'data/regional-review/eastern-cape-source-restoration-435/sources/{n}','sha256':sha(SRC/n)} for n in ('mdb-2021-eastern-cape-boundaries.geojson','mdb-2026-eastern-cape-boundaries.geojson')],
 'metrics_scope':'33 returned Eastern Cape features, including metros. This exact-scope diagnostic compares source versions; it does not establish the legal/current effective-date status, boundary correctness, or detached-territory completeness.',
 'negative_control':{'code':'EC135','comparison':'2021 geometry against itself','symmetric_difference_m2':0.0,'intersection_over_union':1.0,'outcome':'passed'},
 'positive_relevance_controls':positive,'feature_count':len(rows),'different_count':sum(r['status']=='different' for r in rows),'rows':rows}
OUT.write_text(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
print(json.dumps({'output':str(OUT.relative_to(ROOT)),'feature_count':len(rows),'different_count':result['different_count'],'positive_controls':positive},indent=2))
