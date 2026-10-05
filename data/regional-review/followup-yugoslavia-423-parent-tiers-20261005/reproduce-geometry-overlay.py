#!/usr/bin/env python3
"""Compare full retained source parent and scoped-child polygons (diagnostic only)."""
import hashlib, json, pathlib, unicodedata
from collections import defaultdict
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from shapely.validation import explain_validity
ROOT=pathlib.Path(__file__).resolve().parents[3]
OLD=ROOT/'data/regional-review/regional-review-d282e62cf0209796'
OUT=pathlib.Path(__file__).resolve().parent/'geometry-comparison.json'
def read(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def norm(s):
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().casefold()
    return ''.join(c for c in s if c.isalnum())
def digest(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
# European equal-area projection; always_xy is independently round-tripped below.
t=Transformer.from_crs('EPSG:4326','EPSG:3035',always_xy=True)
x,y=t.transform(10.0,45.0); lon,lat=Transformer.from_crs('EPSG:3035','EPSG:4326',always_xy=True).transform(x,y)
assert abs(lon-10)<1e-8 and abs(lat-45)<1e-8
src=OLD/'source/geoboundaries-9469f09'
units=read(OLD/'unit-assessments.json')['rows']; parents=read(OLD/'province-assessments.json')['assessments']
shape_features={}; layers={}; metadata={}
for cc,lev in [('SRB','ADM1'),('SRB','ADM2'),('SVN','ADM1'),('SVN','ADM2')]:
    fc=read(src/f'geoBoundaries-{cc}-{lev}.geojson'); layers[f'{cc}-{lev}']=fc
    metadata[f'{cc}-{lev}']=read(src/f'geoBoundaries-{cc}-{lev}-metaData.json')
    for f in fc['features']:
        key=f['properties']['shapeID']; assert key not in shape_features; shape_features[key]=f
projected={k: transform(t.transform,shape(v['geometry'])) for k,v in shape_features.items()}
invalid=[{'shapeID':k,'validity':explain_validity(g)} for k,g in projected.items() if not g.is_valid]
assert not invalid, f'Invalid unmodified source geometries: {invalid[:3]}'
def area(g): return g.area
assess=[]
for p in sorted(parents,key=lambda x:x['province_id']):
    name=p['name']; pid=p['province_id']; cohort=pid in {'framework:province:vzhodna:d0d1788c155c','framework:province:zahodna-slovenija:52f5c9765039'}
    country='SRB' if pid in {r['parent_id'] for r in units if r['location_id'].startswith('gb:SRB:')} else 'SVN'
    parent_candidates=[f for f in layers[f'{country}-ADM1']['features'] if norm(f['properties']['shapeName'])==norm(name)]
    scoped=[r for r in units if r['parent_id']==pid]
    child_geoms=[projected[r['source_shape_id']] for r in scoped]
    scoped_union=unary_union(child_geoms)
    rec={'parent_id':pid,'name':name,'scoped_child_count':len(scoped),'source_parent_match_count':len(parent_candidates),
         'scoped_child_union_area_m2':area(scoped_union),'geometry_validity':'all original features valid; no repair applied',
         'measure':'2D area after EPSG:4326 longitude/latitude to EPSG:3035 (ETRS89 / LAEA Europe), pyproj always_xy=True; diagnostic only',
         'parent_child_comparison':None}
    if len(parent_candidates)==1:
        pg=projected[parent_candidates[0]['properties']['shapeID']]
        diff=pg.symmetric_difference(scoped_union)
        missing=pg.difference(scoped_union); excess=scoped_union.difference(pg)
        rec['parent_shape_id']=parent_candidates[0]['properties']['shapeID']
        rec['parent_source_vintage']=layers[f'{country}-ADM1']['features'][0]['properties'].get('shapeType')
        rec['parent_area_m2']=area(pg)
        rec['parent_child_comparison']={'symmetric_difference_area_m2':area(diff),
            'symmetric_difference_share_of_parent':area(diff)/area(pg),
            'parent_area_not_covered_by_scoped_children_m2':area(missing),
            'parent_area_not_covered_share':area(missing)/area(pg),
            'scoped_child_area_outside_parent_m2':area(excess),
            'scoped_child_area_outside_share':area(excess)/area(scoped_union) if area(scoped_union) else None,
            'interpretation':'Source-polygon compatibility only. Does not establish current/legal membership, equal vintage, or truth.'}
    else:
        # For the three synthetic same-municipality province parents, report their
        # actual municipality child polygon against both official Slovenian NUTS2
        # parent polygons. This shows which source parent geometry exists, without
        # inventing a geometry for the synthetic Atlas province ID.
        ranked=[]
        for cand in layers['SVN-ADM1']['features']:
            pg=projected[cand['properties']['shapeID']]
            overlap=area(scoped_union.intersection(pg))
            ranked.append({'source_parent_id':cand['properties']['shapeID'],'source_parent_name':cand['properties']['shapeName'],
                'overlap_area_m2':overlap,'share_of_scoped_child':overlap/area(scoped_union) if area(scoped_union) else None,
                'source_parent_area_m2':area(pg),'child_outside_parent_share':area(scoped_union.difference(pg))/area(scoped_union) if area(scoped_union) else None})
        rec['synthetic_parent_geometry_status']='No same-named ADM1 parent polygon exists; Atlas one-child parent has no independent source parent geometry.'
        rec['actual_NUTS2_parent_overlap_candidates']=sorted(ranked,key=lambda z:z['overlap_area_m2'],reverse=True)
    assess.append(rec)
# National parent overlays for the two Slovenia cohesion polygons: all 213 historical ADM2
# source units assigned by maximum positive-area overlap, kept distinct from #1018 scope.
slovene_all=layers['SVN-ADM2']['features']; cohesion=[]
for pf in layers['SVN-ADM1']['features']:
    pg=projected[pf['properties']['shapeID']]; assigned=[]; no_positive=[]
    for cf in slovene_all:
        cg=projected[cf['properties']['shapeID']]
        scores=[area(cg.intersection(projected[q['properties']['shapeID']])) for q in layers['SVN-ADM1']['features']]
        best=max(range(len(scores)),key=lambda i:scores[i])
        if scores[best]>0 and layers['SVN-ADM1']['features'][best]['properties']['shapeID']==pf['properties']['shapeID']:
            assigned.append(cf['properties']['shapeID'])
        if max(scores)==0: no_positive.append(cf['properties']['shapeID'])
    u=unary_union([projected[sid] for sid in assigned])
    cohesion.append({'source_parent_id':pf['properties']['shapeID'],'source_parent_name':pf['properties']['shapeName'],
        'source_parent_vintage':'2021 NUTS2 (GISCO)','source_child_layer':'2017 OSM/Wambacher ADM2',
        'all_213_ADM2_max_overlap_assignment_count':len(assigned),'all_historical_children_with_no_positive_overlap':no_positive,
        'union_vs_parent_symmetric_difference_area_m2':area(u.symmetric_difference(pg)),
        'union_vs_parent_symmetric_difference_share':area(u.symmetric_difference(pg))/area(pg),
        'assigned_shape_ids':sorted(assigned),
        'interpretation':'Maximum-overlap assignment across different vintages is only a diagnostic. It is not official child membership and does not establish current boundary completeness.'})
# Current official GURS collection geometry: check complete 212-municipality and
# 12-statistical-region layers against the 2021 NUTS2 parent tier and coastal aliases.
gurs_m=read(OLD/'source/gurs-municipal-boundaries.geojson')['features']
gurs_r=read(OLD/'source/gurs-statistical-regions.geojson')['features']
gurs_m_g={f['properties']['EID_OBCINA']:transform(t.transform,shape(f['geometry'])) for f in gurs_m}
gurs_r_g={str(f['properties']['EID_STATISTICNA_REGIJA']):transform(t.transform,shape(f['geometry'])) for f in gurs_r}
assert len(gurs_m)==212 and len(gurs_r)==12
assert all(shape(f['geometry']).is_valid for f in gurs_m+gurs_r), 'Invalid original GURS geometry; no repair applied'
region_controls=[]
municipal_region_crosswalk=[]
for mf in gurs_m:
    mg=gurs_m_g[str(mf['properties']['EID_OBCINA'])]
    scores=[area(mg.intersection(gurs_r_g[str(r['properties']['EID_STATISTICNA_REGIJA'])])) for r in gurs_r]
    order=sorted(range(len(scores)),key=lambda i:scores[i],reverse=True); best=order[0]
    municipal_region_crosswalk.append({'municipality':mf['properties']['NAZIV'],'municipality_code':mf['properties']['SIFRA'],
       'max_overlap_region':gurs_r[best]['properties']['NAZIV'],'largest_region_share':scores[best]/area(mg),
       'positive_intersection_regions':sum(v>0.01 for v in scores)})
for f in gurs_r:
    reggeom=gurs_r_g[str(f['properties']['EID_STATISTICNA_REGIJA'])]
    areas=[area(reggeom.intersection(gurs_m_g[c])) for c in gurs_m_g]
    positive=sum(a>0.01 for a in areas)
    region_controls.append({'region_name':f['properties']['NAZIV'],'region_id':str(f['properties']['EID_STATISTICNA_REGIJA']),
        'municipality_features_with_positive_area_intersection':positive,
        'statistical_region_geometry_valid':reggeom.is_valid,
        'region_system_date':f['properties'].get('DATUM_SYS')})
# Official SURS 2019 list, verified on 2026-10-05: 8 eastern + 4 western NUTS3 regions.
east={'Pomurska','Podravska','Koroška','Savinjska','Zasavska','Posavska','Jugovzhodna Slovenija','Primorsko-notranjska'}
west={'Osrednjeslovenska','Gorenjska','Goriška','Obalno-kraška'}
assert {f['properties']['NAZIV'] for f in gurs_r}==east|west
cohesion_gurs=[]
for name, members, sid in [('Vzhodna Slovenija',east,'3739544B32704473481330'),('Zahodna Slovenija',west,'3739544B2739881953900')]:
    candidates=[f for f in layers['SVN-ADM1']['features'] if f['properties']['shapeID']==sid]
    assert len(candidates)==1
    region_union=unary_union([gurs_r_g[str(f['properties']['EID_STATISTICNA_REGIJA'])] for f in gurs_r if f['properties']['NAZIV'] in members])
    nuts2=projected[sid]; diff=region_union.symmetric_difference(nuts2)
    assigned_municipalities=[]
    for m in gurs_m:
        mg=gurs_m_g[m['properties']['EID_OBCINA']]
        scores=[area(mg.intersection(gurs_r_g[str(r['properties']['EID_STATISTICNA_REGIJA'])])) for r in gurs_r]
        idx=max(range(len(scores)),key=lambda i:scores[i])
        rr=gurs_r[idx]
        # record membership based on current official GURS statistical-region overlay
        if rr['properties']['NAZIV'] in members: assigned_municipalities.append(m['properties']['NAZIV'])
    cohesion_gurs.append({'cohesion_region':name,'official_12_region_members':sorted(members),
        'gurs_statistical_region_polygon_union_area_m2':area(region_union),'nuts2_geoBoundaries_shapeID':sid,
        'nuts2_geoBoundaries_boundary_year':'2021','gurs_region_system_dates':sorted(set(f['properties'].get('DATUM_SYS') for f in gurs_r if f['properties']['NAZIV'] in members)),
        'gurs_union_vs_nuts2_symmetric_difference_m2':area(diff),
        'gurs_union_vs_nuts2_difference_share_of_nuts2':area(diff)/area(nuts2),
        'municipality_count_by_maximum_GURS_region_overlap':len(assigned_municipalities),
        'interpretation':'Current GURS official NUTS3 polygons dissolved using SURS-published NUTS2 membership, compared with separate 2021 GISCO NUTS2 source shape; vintage/source differences are expected and any mismatch is diagnostic.'})
coastal=[]
for r in units:
    if r['parent_id'] not in {'framework:province:ankaran-ancarano:3995388bc628','framework:province:izola-isola:bc2149bec285','framework:province:piran-pirano:1d929956088b'}: continue
    cid=str(r['current_official_code']); gf=next(f for f in gurs_m if str(f['properties']['SIFRA'])==cid)
    oldg=projected[r['source_shape_id']]; newg=gurs_m_g[str(gf['properties']['EID_OBCINA'])]; inter=oldg.intersection(newg); uni=oldg.union(newg)
    coastal.append({'atlas_parent_id':r['parent_id'],'location_id':r['location_id'],'source_shape_id':r['source_shape_id'],
       'source_name':r['source_shape_name'],'gurs_official_municipality_name':gf['properties']['NAZIV'],'gurs_id':cid,
       'gurs_system_date':gf['properties'].get('DATUM_SYS'),'geoBoundaries_year':'2017',
       'intersection_over_union':area(inter)/area(uni),'old_2017_share_intersecting_current':area(inter)/area(oldg),
       'current_share_intersecting_2017':area(inter)/area(newg),
       'interpretation':'Polygon crosswalk diagnostic for the current municipality identity; does not prove same-date boundary equivalence or give the Atlas synthetic parent an independent boundary.'})
# Compare the second same-name Maribor ADM2 source feature against its current GURS feature.
maribor=next(f for f in layers['SVN-ADM2']['features'] if f['properties']['shapeID']=='79292919B38849654156102')
maribor_current=next(f for f in gurs_m if f['properties']['NAZIV']=='Maribor')
maribor_oldg=projected[maribor['properties']['shapeID']]; maribor_newg=gurs_m_g[str(maribor_current['properties']['EID_OBCINA'])]
maribor_inter=maribor_oldg.intersection(maribor_newg)
output={'version':1,'issue':1018,'baseline_commit':'7646e0962afab6cc4f566439bb2f96890ae4b91e',
 'geometry_controls':{'all_geoBoundaries_original_features_valid':True,'all_GURS_original_features_valid':True,
    'identity_overlay_symmetric_difference_area_m2':area(projected[layers['SRB-ADM1']['features'][0]['properties']['shapeID']].symmetric_difference(projected[layers['SRB-ADM1']['features'][0]['properties']['shapeID']])),
    'out_of_scope_discordant_Maribor_sliver_IoU':area(maribor_inter)/area(maribor_oldg.union(maribor_newg)),
    'warning':'Positive identity and low-overlap discordant controls exercise area calculation; neither validates the source geometry.'},
 'projection_control':{'input_lon_lat':[10,45],'projected_epsg3035_m':[x,y],'round_trip_lon_lat':[lon,lat],'max_abs_error_degrees':max(abs(lon-10),abs(lat-45))},
 'source_layer_sha256':{f'geoBoundaries-{c}-{l}.geojson':digest(src/f'geoBoundaries-{c}-{l}.geojson') for c,l in [('SRB','ADM1'),('SRB','ADM2'),('SVN','ADM1'),('SVN','ADM2')]},
 'parent_comparisons':assess,'Slovenia_full_historical_ADM2_vs_NUTS2':cohesion,
 'current_GURS_region_municipality_geometry':{'municipality_features':len(gurs_m),'statistical_region_features':len(gurs_r),
   'region_municipality_intersection_controls':region_controls,
   'municipality_to_region_crosswalk':municipal_region_crosswalk,
   'crosswalk_summary':{'municipalities':len(municipal_region_crosswalk),
      'municipalities_with_maximum_overlap_share_at_least_0_999':sum(x['largest_region_share']>=0.999 for x in municipal_region_crosswalk),
      'municipalities_touching_multiple_region_polygons':sum(x['positive_intersection_regions']>1 for x in municipal_region_crosswalk),
      'minimum_maximum_overlap_share':min(x['largest_region_share'] for x in municipal_region_crosswalk)},
   'cohesion_region_geometry_comparison':cohesion_gurs,'coastal_singleton_polygon_crosswalks':coastal,
   'out_of_scope_duplicate_Maribor_feature':{'shapeID':maribor['properties']['shapeID'],'shapeName':maribor['properties']['shapeName'],
       'area_m2':area(maribor_oldg),'current_GURS_Maribor_overlap_share_of_sliver':area(maribor_inter)/area(maribor_oldg),
       'overlap_share_of_current_Maribor':area(maribor_inter)/area(maribor_newg),
       'scope_status':'This distinct 2017 ADM2 feature is not one of the pinned 278 subjects.'},
   'input_sha256':{'gurs-municipal-boundaries.geojson':digest(OLD/'source/gurs-municipal-boundaries.geojson'),
                   'gurs-statistical-regions.geojson':digest(OLD/'source/gurs-statistical-regions.geojson')}},
 'limitations':['No polygon was repaired or snapped.','Geometric equality is not an authoritative claim and can be affected by vintage and source lineage.',
 'SRB ADM1/ADM2 both use 2017 OSM-derived boundaries; per-unit current RZS roster/boundaries are not retained in this packet.',
 'SVN ADM1 is 2021 NUTS2/GISCO; SVN ADM2 is 2017 OSM-derived, so differences combine tier assignment and vintage.',
 'Synthetic coastal one-child Atlas parent records have no independent same-named source parent polygon.',
 'GURS current municipal/statistical polygons are retained in the prior issue packet and are overlaid here; current statutory membership is still best supported by the SURS-published official 8/4 NUTS3 lists.'],
 'software':{'python':'3.12','shapely':'2.1.2','pyproj':'3.7.2','crs':'EPSG:3035','area_units':'square metres'}}
enc=json.dumps(output,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'; OUT.write_text(enc,encoding='utf-8')
print(f'wrote {OUT.relative_to(ROOT)} sha256={hashlib.sha256(enc.encode()).hexdigest()} parents={len(assess)}; invalid={len(invalid)}')
