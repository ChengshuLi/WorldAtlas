"""Literal original comparison loops; only authenticated captured readers are adapted."""
import hashlib,json

def compare(captured, decoded, geometry, ellipsoidal):
    from shapely.geometry import shape
    from shapely.strtree import STRtree
    geod_area=ellipsoidal.area
    GEOMETRY_VERSION=geometry.VERSION
    packet='research/geography/mongolia-russia-gap-source-fitness-20261007/'
    MRIS=packet+'sources/mongolia-mris/mng-adm2-nso-featurelayer-full.geojson'
    CAT=json.loads(captured['coordination/engineering/original-geography-source-corpus-20261006/catalogue.json'])
    FAM=json.loads(captured[packet+'inputs/complete-family.json'])
    PHYS=json.loads(captured[packet+'inputs/physical-component-features.geojson'])
    FAM_ROWS=[json.loads(line) for line in captured[packet+'inputs/route-component-rows.jsonl'].splitlines() if line.strip()]
    byid={str(r.get('component',r.get('component_id',r.get('id')))):r for r in FAM_ROWS}
    features={}
    for f in PHYS['features']:
        p=f['properties'];cid=str(f.get('id',p.get('component_id',p.get('id'))));features[cid]=f
    def product(country):
        entry=next(x for x in CAT['products'] if x['key']==f'gb:{country}:ADM2')
        raw=decoded[entry['parts'][0]['path']]
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
    mris_raw=captured[MRIS]
    mris=json.loads(mris_raw)
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
    contacts=json.loads(captured[packet+'inputs/current-contact-features.geojson'])
    mris_result={'response_sha256':hashlib.sha256(mris_raw).hexdigest(),'feature_count':len(mris['features']),'family_component_count':len(mris_rel),'positive_area_component_count':sum(bool(r['intersecting_feature_count']) for r in mris_rel),'relations':mris_rel}
    out={'method':{'source_geometry_policy':'Preserve source and target geometries as decoded; no repair, clipping, simplification or assignment. Shapely intersects predicates and topology intersections use decoded EPSG:4326 longitude-latitude coordinates; intersection area is measured with the pinned WGS84 straight-source-edge ellipsoidal integral helper. Only positive ellipsoidal polygon area is counted; line-only touch is excluded. These comparisons do not establish precision, authority, or physical land status.','axis_order':'longitude-latitude','crs':'EPSG:4326','area_method':'WGS84 straight-source-edge ellipsoidal integral','distance_method':'WGS84 inverse geodesic; no distances calculated','helper_version':GEOMETRY_VERSION,'scope':'All 48 components in complete family; full retained source feature rosters.'},'products':products,'mris_mongolia_nso_adm2':mris_result,'result_counts':{'complete_family_components':FAM['component_count'],'positive_length_contacts':len(contacts['features']),'geoboundaries_mng_source_features':products['geoBoundaries_MNG_ADM2']['feature_count'],'geoboundaries_mng_positive_area_components':sum(bool(r['intersecting_feature_count']) for r in products['geoBoundaries_MNG_ADM2']['relations']),'geoboundaries_rus_source_features':products['geoBoundaries_RUS_ADM2']['feature_count'],'geoboundaries_rus_advertised_source_features':products['geoBoundaries_RUS_ADM2']['product']['advertised_feature_count'],'geoboundaries_rus_positive_area_components':sum(bool(r['intersecting_feature_count']) for r in products['geoBoundaries_RUS_ADM2']['relations']),'mris_nso_source_features':mris_result['feature_count'],'mris_nso_positive_area_components':mris_result['positive_area_component_count']}}
    return out
