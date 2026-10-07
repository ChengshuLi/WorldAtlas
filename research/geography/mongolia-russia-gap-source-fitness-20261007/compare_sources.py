#!/usr/bin/env python3
"""Deterministically compare the complete physical family with preserved ADM2 sources.
No input geometry is changed. Intersection areas are descriptive overlays only.
"""
from __future__ import annotations
import gzip, hashlib, json, math, sys
from pathlib import Path
from shapely.geometry import shape
from shapely.strtree import STRtree

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
sys.path.insert(0, str(REPO/'scripts'))
sys.path.insert(0, str(REPO/'scripts/evidence'))
from geometry import VERSION as GEOMETRY_VERSION
from ellipsoidal_area import area as geod_area
SOURCES=ROOT/'sources'
INPUTS=ROOT/'inputs'
CORPUS=REPO/'coordination/engineering/original-geography-source-corpus-20261006'
CAT=json.loads((CORPUS/'catalogue.json').read_text())
FAM=json.loads((INPUTS/'complete-family.json').read_text())
PHYS=json.loads((INPUTS/'physical-component-features.geojson').read_text())
FAM_ROWS=[json.loads(line) for line in (INPUTS/'route-component-rows.jsonl').read_text().splitlines() if line.strip()]
# Match retained source features to complete route component rows using original canonical IDs.
byid={str(r.get('component',r.get('component_id',r.get('id')))):r for r in FAM_ROWS}
features={}
for f in PHYS['features']:
    p=f['properties']; cid=str(f.get('id',p.get('component_id',p.get('id'))))
    features[cid]=f
if set(byid)!=set(features) or len(byid)!=48: raise SystemExit('family/physical feature join is not 48/48')

def product(country):
    entry=next(x for x in CAT['products'] if x['key']==f'gb:{country}:ADM2')
    compressed=REPO/entry['parts'][0]['path']
    raw=gzip.decompress(compressed.read_bytes())
    if hashlib.sha256(raw).hexdigest()!=entry['original_sha256']:
        raise SystemExit(f'{country} whole source raw hash mismatch')
    data=json.loads(raw)
    if len(data['features'])!=entry['feature_count']: raise SystemExit(f'{country} feature count mismatch')
    geoms=[shape(f['geometry']) for f in data['features']]
    tree=STRtree(geoms)
    out=[]
    for cid in sorted(byid):
        tg=shape(features[cid]['geometry'])
        ta=geod_area(tg)
        hits=[]
        for idx in tree.query(tg):
            idx=int(idx); sg=geoms[idx]
            # preserve literal intersects relation, and fail closed on GEOS topology errors
            if not tg.intersects(sg): continue
            inter=tg.intersection(sg)
            ia=geod_area(inter)
            if ia<=0: continue
            p=data['features'][idx]['properties']
            hits.append({'source_feature_index':idx,'source_properties':p,'intersection_area_m2_wgs84':ia,'component_area_m2_wgs84':ta,'component_overlap_fraction':ia/ta if ta else None})
        hits.sort(key=lambda x:(-x['intersection_area_m2_wgs84'],x['source_feature_index']))
        out.append({'component_id':cid,'component_geometry_sha256':byid[cid].get('current_geometry_sha256'),'component_area_m2_wgs84':ta,'intersecting_feature_count':len(hits),'overlaps':hits})
    return {'product':entry,'raw_sha256':hashlib.sha256(raw).hexdigest(),'raw_bytes':len(raw),'feature_count':len(data['features']),'family_component_count':len(out),'relations':out}

# MRIS is an official source candidate for Mongolia; exact response bytes remain in sources/.
mris_path=SOURCES/'mongolia-mris/mng-adm2-nso-featurelayer-full.geojson'
mris=json.loads(mris_path.read_text())
mris_geoms=[shape(f['geometry']) for f in mris['features']]
tree=STRtree(mris_geoms)
mris_rel=[]
for cid in sorted(byid):
    tg=shape(features[cid]['geometry']); ta=geod_area(tg); hits=[]
    for ix in tree.query(tg):
        ix=int(ix); sg=mris_geoms[ix]
        if not tg.intersects(sg): continue
        ia=geod_area(tg.intersection(sg))
        if ia<=0: continue
        hits.append({'feature_index':ix,'properties':mris['features'][ix]['properties'],'intersection_area_m2_wgs84':ia,'component_overlap_fraction':ia/ta if ta else None})
    hits.sort(key=lambda x:(-x['intersection_area_m2_wgs84'],x['feature_index']))
    mris_rel.append({'component_id':cid,'component_area_m2_wgs84':ta,'intersecting_feature_count':len(hits),'overlaps':hits})

products={'geoBoundaries_MNG_ADM2':product('MNG'),'geoBoundaries_RUS_ADM2':product('RUS')}
contacts=json.loads((INPUTS/'current-contact-features.geojson').read_text())
mris_result={'response_sha256':hashlib.sha256(mris_path.read_bytes()).hexdigest(),'feature_count':len(mris['features']),'family_component_count':len(mris_rel),'positive_area_component_count':sum(bool(r['intersecting_feature_count']) for r in mris_rel),'relations':mris_rel}
out={'method':{'source_geometry_policy':'Preserve source and target geometries as decoded; no repair, clipping, simplification or assignment. Shapely intersects predicates and topology intersections use decoded EPSG:4326 longitude-latitude coordinates; intersection area is measured with the pinned WGS84 straight-source-edge ellipsoidal integral helper. Only positive ellipsoidal polygon area is counted; line-only touch is excluded. These comparisons do not establish precision, authority, or physical land status.','axis_order':'longitude-latitude','crs':'EPSG:4326','area_method':'WGS84 straight-source-edge ellipsoidal integral','distance_method':'WGS84 inverse geodesic; no distances calculated','helper_version':GEOMETRY_VERSION,'scope':'All 48 components in complete family; full retained source feature rosters.'},'products':products,'mris_mongolia_nso_adm2':mris_result,'result_counts':{'complete_family_components':FAM['component_count'],'positive_length_contacts':len(contacts['features']),'geoboundaries_mng_source_features':products['geoBoundaries_MNG_ADM2']['feature_count'],'geoboundaries_mng_positive_area_components':sum(bool(r['intersecting_feature_count']) for r in products['geoBoundaries_MNG_ADM2']['relations']),'geoboundaries_rus_source_features':products['geoBoundaries_RUS_ADM2']['feature_count'],'geoboundaries_rus_advertised_source_features':products['geoBoundaries_RUS_ADM2']['product']['advertised_feature_count'],'geoboundaries_rus_positive_area_components':sum(bool(r['intersecting_feature_count']) for r in products['geoBoundaries_RUS_ADM2']['relations']),'mris_nso_source_features':mris_result['feature_count'],'mris_nso_positive_area_components':mris_result['positive_area_component_count']}}
path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'inputs/source-overlay-comparison.json'
path.write_text(json.dumps(out,sort_keys=True,separators=(',',':'))+'\n')
print(json.dumps({'output':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'product_feature_counts':{k:v['feature_count'] for k,v in out['products'].items()},'mris_features':out['mris_mongolia_nso_adm2']['feature_count'],'family':48},indent=2))
