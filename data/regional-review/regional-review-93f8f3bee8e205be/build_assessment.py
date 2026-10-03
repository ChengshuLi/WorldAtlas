#!/usr/bin/env python3
"""Build exhaustive #486 row, cohort and derived-footprint evidence."""
import gzip, hashlib, json
from pathlib import Path
from osgeo import ogr, osr
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SRC=HERE/'sources'
ogr.UseExceptions()

def read(path):
    path=Path(path)
    if path.suffix=='.gz':
        with gzip.open(path,'rt',encoding='utf-8') as f:return json.load(f)
    return json.loads(path.read_text(encoding='utf-8'))
def check(v,msg):
    if not v: raise SystemExit('FAIL: '+msg)
def sha(b):return hashlib.sha256(b).hexdigest()
scope=read(HERE/'scope.json'); ids=scope['member_location_ids']; idset=set(ids)
current_data=read(SRC/'current-scope-and-parents.geojson.gz')
current={f['properties']['id']:f for f in current_data['features']}
check(len(ids)==211 and len(current)==211 and set(current)==idset,'exact 211 current scope required')
hierarchy={x['id']:x for x in read(ROOT/'data/hierarchy.json')}
source2_data=read(SRC/'geoboundaries-USA-ADM2.geojson')
source1_data=read(SRC/'geoboundaries-USA-ADM1.geojson')
tiger_data=read(SRC/'tigerline-2024-western-county-neighbors.geojson.gz')
eco_data=read(SRC/'resolve-15-ecoregions.geojson.gz')
gnis_data=read(SRC/'usgs-gnis-populated-places-AK-CO-NM-OR-WY.geojson.gz')
source2={f['properties']['shapeID']:f for f in source2_data['features']}
source1={f['properties']['shapeName'].casefold():f for f in source1_data['features']}
eco={int(f['properties']['ECO_ID']):f for f in eco_data['features']}
expected_eco={int(current[i]['properties']['metadata']['source_id'].split(':')[1]) for i in ids if i.startswith('atlas:physical:')}
check(set(eco)==expected_eco and len(expected_eco)==15,'exact 15 RESOLVE Eco_ID source features required')
tiger_by_state={}
for f in tiger_data['features']:tiger_by_state.setdefault(f['properties']['STATEFP'],[]).append(f)
STATE={
 'framework:province:alaska:4057e2fddbc5':('02','Alaska','EPSG:3338'),
 'framework:province:alaska:d12fadcdd2dd':('02','Alaska','EPSG:3338'),
 'framework:province:colorado:23236001ee65':('08','Colorado','EPSG:5070'),
 'framework:province:new-mexico:af8cd7ad2873':('35','New Mexico','EPSG:5070'),
 'framework:province:oregon:a2a18667bf83':('41','Oregon','EPSG:5070'),
 'framework:province:wyoming:fac4b0784a90':('56','Wyoming','EPSG:5070'),
}
crs_cache={}
def crs(epsg):
    if epsg not in crs_cache:
        s=osr.SpatialReference();s.ImportFromEPSG(int(epsg.split(':')[1]));s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER);crs_cache[epsg]=s
    return crs_cache[epsg]
def makegeom(obj):
    g=ogr.CreateGeometryFromJson(json.dumps(obj,separators=(',',':')))
    if g is None:raise ValueError('invalid GeoJSON geometry')
    g.AssignSpatialReference(crs('EPSG:4326'));return g
def project(g,epsg):
    q=g.Clone();q.TransformTo(crs(epsg));repaired=not bool(q.IsValid())
    if repaired:q=q.MakeValid()
    if q is None or q.IsEmpty() or not q.IsValid():raise ValueError('temporary projected geometry invalid')
    return q,repaired
def get_state(feature):
    parent=feature['properties'].get('parent_id')
    if parent not in STATE:raise ValueError(f'unrecognized assigned province {parent}')
    return STATE[parent]
def poly_count(g):
    return g.GetGeometryCount() if g.GetGeometryName()=='MULTIPOLYGON' else (1 if g.GetGeometryName()=='POLYGON' else sum(poly_count(g.GetGeometryRef(i)) for i in range(g.GetGeometryCount())))
def area_km(g):return round(g.GetArea()/1e6,6)
# Resolve every original county predecessor from stable source IDs and group all direct/derived locations.
admin_groups={}; current_geom={}; repaired={}; ref_state={}
for i,f in current.items():
    p=f['properties'];st,name,epsg=get_state(f);md=p.get('metadata',{})
    pred=i.rsplit(':',1)[-1] if i.startswith('gb:USA:ADM2:') else md.get('original_id')
    check(pred in source2,f'missing 2018 source shape {pred} for {i}')
    g,fix=project(makegeom(f['geometry']),epsg);current_geom[i]=g;repaired[i]=fix
    admin_groups.setdefault(pred,[]).append(i);ref_state[pred]=(st,name,epsg)
check(len(admin_groups)==185,'all 178 direct county IDs plus seven physical predecessors must yield 185 source units')
check(sum(i.startswith('gb:USA:ADM2:') for i in ids)==178 and sum(i.startswith('atlas:physical:') for i in ids)==33,'scope subject role totals mismatch')
admin_current={}
for pred,group in admin_groups.items():
    gs=[current_geom[i] for i in group];u=gs[0].Clone()
    for g in gs[1:]:u=u.Union(g)
    admin_current[pred]=u
# Match each 2018 county predecessor against the complete 2024 state county layer using exact name first, then area overlay.
source_geom_cache={}
def sg(feature,epsg):
    key=(id(feature),epsg)
    if key not in source_geom_cache:source_geom_cache[key]=project(makegeom(feature['geometry']),epsg)[0]
    return source_geom_cache[key]
county_crosswalk={};county_metrics={}
for pred,group in admin_groups.items():
    old=source2[pred]; oldp=old['properties'];st,state,epsg=ref_state[pred]
    census=tiger_by_state.get(st,[]); exact=[f for f in census if f['properties']['NAME'].casefold()==oldp['shapeName'].casefold()]
    oldg=sg(old,epsg);ranked=[]
    if exact:
        selected=exact
    else:
        for tf in census:
            g=sg(tf,epsg); inter=oldg.Intersection(g).GetArea()
            if inter>1:ranked.append((inter,tf))
        selected=[tf for inter,tf in ranked if inter>max(oldg.GetArea()*0.00001,1)]
    check(selected,f'no 2024 Census counterpart or spatial crosswalk for {state}/{oldp["shapeName"]}')
    target=None
    for tf in selected:
        g=sg(tf,epsg);target=g.Clone() if target is None else target.Union(g)
    now=admin_current[pred];intersection=oldg.Intersection(now).GetArea();ov=oldg.Intersection(target).GetArea();nowov=now.Intersection(target).GetArea()
    rows=[]
    for tf in selected:
        g=sg(tf,epsg);inter=oldg.Intersection(g).GetArea()
        rows.append({'geoid':tf['properties']['GEOID'],'name':tf['properties']['NAME'],'namelsad':tf['properties'].get('NAMELSAD'),'classfp':tf['properties'].get('CLASSFP'),'aland_m2':int(tf['properties']['ALAND']),'awater_m2':int(tf['properties']['AWATER']),'source_intersection_pct':round(inter/max(oldg.GetArea(),1)*100,6)})
    county_crosswalk[pred]=rows
    county_metrics[pred]={'predecessor_shape_id':pred,'2018_name':oldp['shapeName'],'2018_state':state,'assigned_location_ids':sorted(group),'assigned_piece_count':len(group),'2024_counterparts':rows,'match_rule':'exact 2024 name' if exact else 'temporary equal-area polygon intersection; all material descendant matches retained','2018_area_km2':area_km(oldg),'current_area_km2':area_km(now),'2024_counterpart_union_area_km2':area_km(target),'current_intersection_over_2018_pct':round(intersection/max(oldg.GetArea(),1)*100,6),'current_intersection_over_2024_union_pct':round(nowov/max(target.GetArea(),1)*100,6),'2018_2024_union_iou_pct':round(ov/max(oldg.Union(target).GetArea(),1)*100,6),'current_2018_symdiff_km2':area_km(oldg.SymDifference(now)),'current_2024_symdiff_km2':area_km(now.SymDifference(target)),'current_projected_repair':any(repaired[i] for i in group),'interpretation':'Equal-area footprint screen; it does not establish legal ownership, a water boundary convention, or a line-change authorization.'}
# Complete state-cohort and ADM1 parent coverage from the exact assigned 2018 source roster and full Census 2024 state rosters.
state_audit={};state_names=['Alaska','Colorado','New Mexico','Oregon','Wyoming']
for state in state_names:
    source_state=source1[state.casefold()];epsg='EPSG:3338' if state=='Alaska' else 'EPSG:5070';stateg=sg(source_state,epsg)
    st={'Alaska':'02','Colorado':'08','New Mexico':'35','Oregon':'41','Wyoming':'56'}[state]
    assigned_preds=sorted(p for p,(fips,n,proj) in ref_state.items() if n==state)
    source_candidates=[source2[p] for p in assigned_preds];src_union=None
    for f in source_candidates:
        g=sg(f,epsg);src_union=g.Clone() if src_union is None else src_union.Union(g)
    cur_union=None
    for pred in assigned_preds:
        g=admin_current[pred];cur_union=g.Clone() if cur_union is None else cur_union.Union(g)
    source_to_tiger={p:county_crosswalk[p] for p in assigned_preds}
    linked_geoids={row['geoid'] for p in assigned_preds for row in source_to_tiger[p]}
    unlinked_tiger=[{'geoid':tf['properties']['GEOID'],'name':tf['properties']['NAME']} for tf in tiger_by_state[st] if tf['properties']['GEOID'] not in linked_geoids]
    unlinked_source=[p for p,links in source_to_tiger.items() if not links]
    current_parent_ids={f['properties']['parent_id'] for f in current.values() if get_state(f)[1]==state}
    state_audit[state]={'state_fips':st,'adm1_source_shape_id':source_state['properties']['shapeID'],'adm1_source_name':source_state['properties']['shapeName'],'assigned_2018_adm2_predecessor_count':len(assigned_preds),'tiger_2024_county_feature_count':len(tiger_by_state[st]),'assigned_location_count':sum(1 for f in current.values() if get_state(f)[1]==state),'current_parent_node_ids':sorted(current_parent_ids),'all_2024_tiger_counties_crosswalked_to_assigned_2018_sources':not unlinked_tiger,'unlinked_2024_tiger_counties':unlinked_tiger,'unlinked_2018_predecessors':unlinked_source,'2018_source_to_2024_tiger_crosswalk':source_to_tiger,'source_adm2_union_area_km2':area_km(src_union),'source_adm1_area_km2':area_km(stateg),'source_adm2_union_intersection_over_adm1_pct':round(src_union.Intersection(stateg).GetArea()/max(stateg.GetArea(),1)*100,6),'source_adm2_union_symdiff_km2':area_km(src_union.SymDifference(stateg)),'current_parent_cohort_union_area_km2':area_km(cur_union),'current_parent_union_intersection_over_adm1_pct':round(cur_union.Intersection(stateg).GetArea()/max(stateg.GetArea(),1)*100,6),'current_parent_union_symdiff_km2':area_km(cur_union.SymDifference(stateg)),'2018_source_shape_ids':sorted(assigned_preds),'interpretation':'The assigned 2018 predecessor roster is crosswalked against the full official 2024 Census state county roster. A 2018 unit can map to multiple present-day units, so no one-to-one identity is forced.'}
# Place screen from the complete 2024 Census place archive in each assigned state.
place_records=[];place_counts={}
for st,fn in [('02','tl_2024_02_place.zip'),('08','tl_2024_08_place.zip'),('35','tl_2024_35_place.zip'),('41','tl_2024_41_place.zip'),('56','tl_2024_56_place.zip')]:
    ds=ogr.Open('/vsizip/'+str((SRC/fn).resolve()));check(ds is not None,f'cannot open {fn}');layer=ds.GetLayer(0);place_counts[st]=layer.GetFeatureCount()
    epsg='EPSG:3338' if st=='02' else 'EPSG:5070'
    for feat in layer:
        g=feat.GetGeometryRef().Clone();g.AssignSpatialReference(crs('EPSG:4269'));g.TransformTo(crs(epsg));
        if not g.IsValid():g=g.MakeValid()
        defn=layer.GetLayerDefn();fields={defn.GetFieldDefn(j).GetName():feat.GetField(j) for j in range(defn.GetFieldCount())}
        place_records.append({'state_fips':st,'geoid':fields['GEOID'],'name':fields['NAME'],'classfp':fields.get('CLASSFP'),'lsad':fields.get('LSAD'),'geometry':g})
    ds=None
places={}
for i,f in current.items():
    st,state,epsg=get_state(f);g=current_geom[i];matches=[];env=g.GetEnvelope()
    for p in place_records:
        if p['state_fips']!=st:continue
        pe=p['geometry'].GetEnvelope()
        if env[1]<pe[0] or pe[1]<env[0] or env[3]<pe[2] or pe[3]<env[2]:continue
        if g.Intersects(p['geometry']):matches.append({k:p[k] for k in ('geoid','name','classfp','lsad')})
    places[i]=sorted(matches,key=lambda x:(x['name'].casefold(),x['geoid']))
# Match official GNIS Populated Place names to current assigned feature footprints.
GNIS_STATE={'AK':'02','CO':'08','NM':'35','OR':'41','WY':'56'}
gnis_records=[];gnis_unknown_count=0
for f in gnis_data['features']:
    p=f.get('properties',{}); st=GNIS_STATE.get(p.get('state_alpha'))
    if not st:continue
    # The service's IsUnknownCoords value is not a truthy boolean: observed
    # records use 2 while carrying valid coordinates. Treat only absent or
    # explicit (0,0) point coordinates as unlocated; retain the source flag.
    raw_geom=f.get('geometry') or {}; coords=raw_geom.get('coordinates') or []
    valid_coords=[xy for xy in coords if isinstance(xy,(list,tuple)) and len(xy)>=2 and not (float(xy[0])==0 and float(xy[1])==0)]
    if not valid_coords:gnis_unknown_count+=1;continue
    g=makegeom(raw_geom);epsg='EPSG:3338' if st=='02' else 'EPSG:5070';g.TransformTo(crs(epsg))
    gnis_records.append({'state_fips':st,'gaz_id':p.get('gaz_id'),'name':p.get('gaz_name'),'feature_class':p.get('gaz_featureclass'),'county_name':p.get('county_name'),'fcode':p.get('fcode'),'isunknowncoords_source_value':p.get('isunknowncoords'),'geometry':g})
gnis_by_location={}
for i,f in current.items():
    st,state,epsg=get_state(f);g=current_geom[i];env=g.GetEnvelope();hits=[]
    for item in gnis_records:
        if item['state_fips']!=st:continue
        e=item['geometry'].GetEnvelope()
        if env[1]<e[0] or e[1]<env[0] or env[3]<e[2] or e[3]<env[2]:continue
        if g.Intersects(item['geometry']):hits.append({k:item[k] for k in ('gaz_id','name','feature_class','county_name','fcode','isunknowncoords_source_value')})
    gnis_by_location[i]=sorted(hits,key=lambda x:(x['name'] or '',x['gaz_id'] or 0))
# Row-level complete ancestry comes from exact current location plus inventory parent records.
chains={r['id']:r['parent_chain'] for r in read(SRC/'current-parent-chains.json.gz')}
land=read(HERE/'gshhg-scope-screen.json');check(set(land['per_location'])==idset,'complete GSHHG screen required')
rows=[];physical_ids=[i for i in ids if i.startswith('atlas:physical:')]
for i in ids:
    f=current[i];p=f['properties'];md=p.get('metadata',{});st,state,epsg=get_state(f)
    pred=i.rsplit(':',1)[-1] if i.startswith('gb:USA:ADM2:') else md['original_id'];src=source2[pred];meta_src=src['properties'];eco_id=int(md['source_id'].split(':')[1]) if md.get('source_id','').startswith('resolve:') else None
    coords=f['geometry']['coordinates'];polys=coords if f['geometry']['type']=='MultiPolygon' else [coords];rings=sum(len(poly) for poly in polys);holes=sum(len(poly)-1 for poly in polys);verts=sum(len(ring) for poly in polys for ring in poly)
    current_area=current_geom[i].GetArea(); county=county_metrics[pred]; links=county_crosswalk[pred]; role_ok=eco_id is None and md.get('source_role')=='Counties'
    eco_record=None
    if eco_id is not None:
        ep=eco[eco_id]['properties'];eco_record={'eco_id':eco_id,'eco_name':ep['ECO_NAME'],'biome':ep['BIOME_NAME'],'realm':ep['REALM'],'license':ep['LICENSE'],'source_role':'Natural ecological unit; does not define administrative county membership or political ownership.'}
    role_finding='The current `Counties` source_role matches the 2018 Census-sourced county-equivalent identity. This finding is limited to that named source role; current status and footprint vintage remain separately described.' if role_ok else 'Current source_role and selection rationale identify this location as a County, while its retained source is a RESOLVE ecological feature. The intersection with a named 2018 county predecessor does not make that ecological portion an administrative county.'
    if eco_id is not None:decision='correction_needed'; basis='The 33 Alaska physical pieces are ecoregion/ecology features clipped to seven source county predecessors; metadata role must reflect ecological derivation. The current geometry is not changed by this finding.'
    else:decision='justified';basis='The exact 2018 geoBoundaries ADM2 shapeID and named unit are traced for this row; 2024 Census crosswalk, complete source/state cohort, parent chain and row-level settlement/physical screens are recorded. This does not certify a complete contemporary legal boundary or all local settlements.'
    row={'location_id':i,'name':p['name'],'area':next((x['name'] for x in chains[i] if x.get('level')=='area'),'unknown'),'parent_state':state,'state_fips':st,'full_parent_chain':chains[i],
    'current_geometry_screen':{'type':f['geometry']['type'],'components':poly_count(makegeom(f['geometry'])),'rings':rings,'interior_rings':holes,'vertices':verts,'area_km2_equal_area_screen':round(current_area/1e6,6),'temporary_projected_geometry_repair':repaired[i],'equal_area_crs':epsg},
    'administrative_identity':{'2018_source':'geoBoundaries gbOpen USA ADM2; source-declared U.S. Census MAF/TIGER origin; Public Domain; boundary vintage 2018','source_shape_id':pred,'source_name_2018':meta_src['shapeName'],'source_type':meta_src['shapeType'],'match_kind':'direct stable ADM2 shape ID' if i.startswith('gb:USA:ADM2:') else '2018 county predecessor represented by physical fragments','current_display_name':p['name'],'census_2024_counterparts':links,'2018_2024_current_footprint_audit':county,'vintage_note':'A 2018 geographic reference is not asserted to be the present legal/administrative status. For changed or renamed county equivalents, the 2024 Census source overlay crosswalk is explicit.'},
    'source_role_metadata_review':{'current_source_id':md.get('source_id'),'current_source_role':md.get('source_role'),'current_administrative_level':md.get('administrative_level'),'current_selection_reason':md.get('selection_reason'),'source_role_agrees':role_ok,'finding':role_finding},
    'physical_source_identity':eco_record,
    'settlement_screen':{'polygon_source':'U.S. Census Bureau TIGER/Line Places 2024; incorporated places and Census Designated Places','intersecting_place_count':len(places[i]),'places':places[i],'named_place_source':'USGS The National Map Gazetteer (GNIS), five-state 2026-10-03 query for gaz_featureclass=Populated Place; public-domain federal names data','gnis_populated_place_hit_count':len(gnis_by_location[i]),'gnis_populated_place_hits':gnis_by_location[i],'interpretation':'Census Places supplies 2024 incorporated-place/CDP polygons. USGS GNIS adds federally maintained named Populated Place point records with Feature IDs. GNIS is a flat names database, not a hierarchy, current settlement census, or complete inventory. A no-hit in either screen does not prove no settlement; location edge and accuracy remain subject-specific.'},
    'physical_land_screen':land['per_location'][i],
    'political_historical_distinction':'A county-equivalent feature is a U.S. administrative geography source; the 2018 vintage and Census 2024 status crosswalk do not settle political ownership historically. RESOLVE eco-regions are physical geography, not political units.',
    'remainders_islands_disconnected_review':'Geometry component/ring counts and full-resolution GSHHG land screens are recorded. Census water area, detached or insular source matches, GSHHG centroid screens, and Census Places do not certify complete shorelines, every island, every inhabited site, Indigenous/federal administrative remainder, or full legal water boundaries.',
    'decision':decision,'decision_basis':basis,'unresolved':['County names and administrative-status changes between the 2018 geoBoundaries source and 2024 Census vintage require explicit source-era crosswalk; 2024 polygon overlays are not legal rulings.','Census Places does not enumerate every named settlement; review named inhabited communities where a row has a sparse/zero place-polygon screen.','GSHHG only screens land component relationships; complete coastline/island/hydrographic coverage is unproven.','Large land/water shared-edge differences are source-vintage comparison leads and need fit-for-purpose authority, not unilateral line edits.']}
    rows.append(row)
rows.sort(key=lambda r:r['location_id']);counts={d:sum(r['decision']==d for r in rows) for d in ['justified','correction_needed','insufficient_evidence']}
# Overlay every physical fragment as exact predecessor ADM2 × named RESOLVE ecoregion.
derived=[]
for i in physical_ids:
    f=current[i];md=f['properties']['metadata'];pred=md['original_id'];eco_id=int(md['source_id'].split(':')[1]);st,state,epsg=get_state(f)
    county=sg(source2[pred],epsg);ecog=sg(eco[eco_id],epsg);expected=county.Intersection(ecog);observed=current_geom[i];a=expected.GetArea()
    derived.append({'location_id':i,'name':f['properties']['name'],'predecessor_shape_id':pred,'predecessor_name':source2[pred]['properties']['shapeName'],'eco_id':eco_id,'eco_name':eco[eco_id]['properties']['ECO_NAME'],'crs':epsg,'expected_area_km2':area_km(expected),'current_area_km2':area_km(observed),'current_intersection_over_expected_pct':round(expected.Intersection(observed).GetArea()/max(a,1)*100,6),'symmetric_difference_km2':area_km(expected.SymDifference(observed)),'temporary_projected_repair':repaired[i],'raw_source_bytes_preserved':True})
# Reconcile seven source county predecessors as whole administrative units.
physical_parent=[]
for pred,group in sorted(admin_groups.items()):
    if not any(i.startswith('atlas:physical:') for i in group):continue
    old=sg(source2[pred],ref_state[pred][2]);now=admin_current[pred]
    physical_parent.append({'predecessor_shape_id':pred,'predecessor_name':source2[pred]['properties']['shapeName'],'location_ids':sorted(group),'piece_count':len(group),'predecessor_area_km2':area_km(old),'current_piece_union_area_km2':area_km(now),'current_union_intersection_over_predecessor_pct':round(old.Intersection(now).GetArea()/max(old.GetArea(),1)*100,6),'symdiff_km2':area_km(old.SymDifference(now))})
(HERE/'assessment.json').write_text(json.dumps({'issue':486,'date_utc':'2026-10-03','scope':{'count':len(ids),'ids_sha256':sha(('\n'.join(sorted(ids))+'\n').encode()),'region_id':scope['region_id'],'release':scope['release'],'area_scopes':scope['area_scopes'],'province_scopes':scope['province_scopes']},'source_accounting':{'direct_2018_adm2_rows':178,'physical_derived_rows':33,'distinct_2018_adm2_predecessors':len(admin_groups),'physical_predecessor_count':len(physical_parent),'tiger_2024_selected_neighbor_counties':len(tiger_data['features']),'census_2024_place_feature_count_by_state':place_counts,'census_2024_place_feature_total':sum(place_counts.values()),'usgs_gnis_populated_place_source_feature_count':len(gnis_data['features']),'usgs_gnis_rows_skipped_unknown_coordinate':gnis_unknown_count,'usgs_gnis_rows_located_and_screened':len(gnis_records),'resolve_full_source_feature_count':len(eco_data['features'])},'complete_state_parent_cohorts':state_audit,'complete_province_parent_groups':{x['id']:{'name':x['name'],'assigned_member_count':len([i for i in ids if current[i]['properties']['parent_id']==x['id']]),'scope_full_member_count':x['full_province_locations'],'partial':x['partial'],'current_definition':hierarchy.get(x['id'],{})} for x in scope['province_scopes']},'decision_counts':counts,'physical_summary':{'fragments':len(physical_ids),'unique_ecoregion_features':len(expected_eco),'physical_fragments_overlay':len(derived),'gshhg_points_on_land':sum(bool(x['representative_point_in_level1_land']) for x in land['per_location'].values()),'gshhg_locations_with_land_centroid_hit':sum(bool(x['level1_centroid_hits']) for x in land['per_location'].values()),'gshhg_locations_with_no_point_hit':sum(not x['representative_point_in_level1_land'] for x in land['per_location'].values())},'physical_predecessor_reconciliation':physical_parent,'limitations':['Initial packet is 211 of 533 region locations and partial ownership of both Mountain and Pacific areas; no integrated parent decision follows.','County name/role findings are tied to 2018 source vintage and independently screened against 2024 Census data.','Physical ecoregions support natural geography only; they do not determine administrative membership or ownership.','Census Places, GSHHG and county area fields are evidence screens, not complete settlement, island, land/water, sovereignty or boundary certification.','No shared boundary, hierarchy, certificate, source index, application, schema or live record was changed.'],'locations':rows},ensure_ascii=False,indent=2)+'\n')
(HERE/'derived-portion-audit.json').write_text(json.dumps({'method':'For each exact current physical location, intersect the pinned 2018 geoBoundaries county predecessor with its exact RESOLVE eco_id feature in a temporary state-appropriate equal-area projection (EPSG:3338 Alaska Albers; EPSG:5070 lower-48). Compare expected intersection with current polygon and preserve original inputs.','fragment_count':len(derived),'fragments':derived,'predecessor_union_reconciliation':physical_parent,'interpretation':'The ecoregion crosswalk audits derivation and source role. Overlay residuals are scale, source-vintage, coast/water and precision leads; they do not establish county status or authorize a unilateral line move.'},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'locations':len(rows),'decisions':counts,'place_features':len(place_records),'county_predecessors':len(admin_groups),'physical_fragments':len(derived),'states':state_audit},indent=2))
