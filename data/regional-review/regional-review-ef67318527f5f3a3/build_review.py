#!/usr/bin/env python3
"""Rebuild bounded issue 71 source and geometry screens from retained, pinned bytes."""
import csv, gzip, hashlib, json, pathlib, re, zipfile
from shapely.geometry import shape
from shapely.ops import unary_union, transform
from shapely import make_valid
import shapefile
from pyproj import Transformer
ROOT=pathlib.Path(__file__).parent
SRC=ROOT/'sources'; OUT=ROOT
issue=json.load(open(ROOT/'issue-71-api.json'))
body=issue['body']
scope_text=body[body.index('{"area_scopes"'):body.index('\n```',body.index('{"area_scopes"'))]
scope=json.loads(scope_text)
ids=scope['member_location_ids']
# province_scopes follows the location roster in the same pinned machine contract
province_scopes=scope['province_scopes']
features=[]
for p in pathlib.Path('data/geography').glob('part-*.json'):
    features.extend(json.load(open(p))['features'])
base={f['properties']['id']:f for f in features}
assert len(ids)==226 and all(i in base for i in ids)
def digest(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def readgb(iso,adm):
    p=SRC/f'geoBoundaries-{iso}-{adm}.geojson.gz'
    with gzip.open(p,'rt',encoding='utf-8') as f: d=json.load(f)
    md=json.load(open(SRC/f'geoBoundaries-{iso}-{adm}-metaData.json'))
    return d['features'],md
sources={k:readgb(*v) for k,v in {'CYP':('CYP','ADM1'),'GRC':('GRC','ADM3'),'TUR':('TUR','ADM2')}.items()}
cyprus_dls=json.load(open(SRC/'cyprus-dls-districts.geojson'))['features']
istanbul_roster=json.load(open(SRC/'istanbul-official-district-roster.json'))['districts']
by_shape={}
for code,(fs,md) in sources.items():
    for f in fs:
        by_shape[(code, str(f.get('properties',{}).get('shapeID')))]=f
# Natural Earth 5.1.1's map-unit layer supplies four special cartographic IDs.
nezip=zipfile.ZipFile(SRC/'ne_10m_admin_0_map_units.zip')
ner=shapefile.Reader(shp=nezip.open('ne_10m_admin_0_map_units.shp'),shx=nezip.open('ne_10m_admin_0_map_units.shx'),dbf=nezip.open('ne_10m_admin_0_map_units.dbf'))
nefields=[x[0] for x in ner.fields[1:]]
special={'CYN+00?':'CYN','ESB-5132':'ESB','WSB-5133':'WSB','country-CNM':'CNM'}
ne_matches={}
for ix in range(len(ner)):
    rec=dict(zip(nefields,ner.record(ix)))
    if rec.get('ADM0_A3') in special.values():
        ne_matches[rec['ADM0_A3']]={'type':'Feature','geometry':ner.shape(ix).__geo_interface__,'properties':rec}
# Parent chain labels from the baseline hierarchy. The issue scope is the authority for workload membership.
hierarchy=json.load(open('data/hierarchy.json')); hier={x['id']:x for x in hierarchy}
parents={}
for p in pathlib.Path('data/geography').glob('part-*.json'):
    for f in json.load(open(p))['features']:
        pr=f['properties']; parents[pr['id']]=pr
to_equal_area=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform
rows=[]; parent_groups={}; component_rows=[]
for ident in ids:
    f=base[ident]; p=f['properties']; meta=p.get('metadata',{})
    if ident.startswith('gb:CYP:ADM1:'): code='CYP'; adm='ADM1'; shapekey=ident.rsplit(':',1)[-1]
    elif ident.startswith('gb:GRC:ADM3:'): code='GRC'; adm='ADM3'; shapekey=ident.rsplit(':',1)[-1]
    elif ident.startswith('gb:TUR:ADM2:'): code='TUR'; adm='ADM2'; shapekey=ident.rsplit(':',1)[-1]
    else: code='Natural Earth'; adm='Admin0 Map Units'; shapekey=special.get(ident)
    sf=by_shape.get((code,shapekey)) if code!='Natural Earth' else ne_matches.get(shapekey)
    srcprops=sf.get('properties',{}) if sf else {}
    geom=make_valid(shape(f['geometry'])); metric_geom=make_valid(transform(to_equal_area,geom)); area=metric_geom.area; comps=len(getattr(geom,'geoms',[geom]))
    parts=list(geom.geoms) if hasattr(geom,'geoms') else [geom]
    for ci,part in enumerate(parts,1):
        mp=make_valid(transform(to_equal_area,part)); center=mp.centroid
        component_rows.append({'id':ident,'name':p['name'],'component_index':ci,'component_count':len(parts),'component_area_km2_epsg6933':round(mp.area/1e6,4),'component_centroid_lon':round(Transformer.from_crs('EPSG:6933','EPSG:4326',always_xy=True).transform(center.x,center.y)[0],6),'component_centroid_lat':round(Transformer.from_crs('EPSG:6933','EPSG:4326',always_xy=True).transform(center.x,center.y)[1],6),'interpretation':'Geometry part only; centroid/component is not an island identity or completeness claim.'})
    parent=p.get('parent_id'); pp=parents.get(parent,{})
    parent_chain=[]; cursor=parent
    while cursor and cursor in hier:
        node=hier[cursor]
        parent_chain.append({'id':cursor,'name':node.get('name',''),'level':node.get('level','')})
        cursor=node.get('parent_id')
    source_url=''
    if sf:
        source_url=f'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/{code}/{adm}/geoBoundaries-{code}-{adm}.geojson'
        sg=make_valid(transform(to_equal_area,make_valid(shape(sf['geometry'])))); inter=metric_geom.intersection(sg).area
        iou=inter/metric_geom.union(sg).area if metric_geom.union(sg).area else 0
        cover=inter/sg.area if sg.area else 0
    else: iou=cover=None
    pg=base.get(parent)
    if pg:
        pm=make_valid(transform(to_equal_area,make_valid(shape(pg['geometry']))))
        parent_share=metric_geom.intersection(pm).area/area if area else 0
        child_share=metric_geom.intersection(pm).area/pm.area if pm.area else 0
    else: parent_share=child_share=None
    source_layer_count=len(sources[code][0]) if code in sources else 298
    dls_name=''; dls_iou=''
    if code=='CYP' and sf:
        dls_alias={'Kyrenia':'KERYNEIA','Famagusta':'AMMOCHOSTOS','Larnaca':'LARNAKA','Nicosia':'LEFKOSIA','Limassol':'LEMESOS','Paphos':'PAFOS'}
        candidates=[x for x in cyprus_dls if x.get('properties',{}).get('DIST_NM_E')==dls_alias.get(p['name'])]
        if candidates:
            dls_name=candidates[0]['properties'].get('DIST_NM_E','')
            dg=make_valid(transform(to_equal_area,make_valid(shape(candidates[0]['geometry'])))); u=metric_geom.union(dg)
            dls_iou=round(metric_geom.intersection(dg).area/u.area,6) if u.area else ''
    src_feature_id=srcprops.get('shapeID',srcprops.get('ADM0_A3',''))
    src_name=srcprops.get('shapeName',srcprops.get('NAME_LONG',srcprops.get('NAME_EN',srcprops.get('NAME',''))))
    role=meta.get('source_role','Natural Earth map unit; cartographic/de-facto portrayal')
    if ident=='CYN+00?': role='Natural Earth map-unit portrayal; its “Sovereign country” category is a dataset classification, not a legal or diplomatic determination.'
    elif ident=='country-CNM': role='Natural Earth map-unit portrayal of the United Nations Buffer Zone; dataset marks type Indeterminate. This does not settle sovereignty or establish a province-tier purpose.'
    elif ident in ('ESB-5132','WSB-5133'): role='Natural Earth cartographic depiction of a United Kingdom Sovereign Base Area; type Dependency. This source portrayal is not the legal delimitation authority.'
    if code=='Natural Earth': source_url='https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-details/'
    if code in sources:
        smd=sources[code][1]
        metadata_source=smd.get('boundarySource','')
        boundary_type=smd.get('boundaryType','')
        canonical_role=smd.get('boundaryCanonical','')
        metadata_license=smd.get('boundaryLicense','')
        license_detail=smd.get('licenseDetail','')
        source_update=smd.get('sourceDataUpdateDate','')
        source_build=smd.get('buildDate','')
        source_count_status=f"{len(sources[code][0])} features vs pinned metadata count {smd.get('admUnitCount','unknown')}"
        source_parent_group=srcprops.get('shapeGroup','')
        source_parent_status='Pinned source feature exposes only its ISO country group, not its immediate administrative parent.'
    else:
        metadata_source='Natural Earth 5.1.1'; boundary_type='Admin-0 Map Unit'; canonical_role=srcprops.get('TYPE','')
        metadata_license='Public domain'; license_detail=''; source_update=''; source_build=''
        source_count_status='298 map units in layer'; source_parent_group=srcprops.get('SOVEREIGNT','')
        source_parent_status='Natural Earth SOVEREIGNT field is cartographic context, not a legal parent determination.'
    if code=='TUR' and parent=='framework:province:istanbul:69a618445c3d': reason='This district matches its 2021 ODbL ADM2 feature and is one of seven baseline members of İstanbul. The official provincial roster lists 39 current districts; 32 other roster names match distinct pinned source features absent from the baseline. This exact unit may be present, but full province coverage is unresolved. The whole TUR source also has 973 features vs metadata count 999.'
    elif code=='TUR': reason='Individual Turkey district matches a 2021 ODbL ADM2 feature, but the pinned whole-country file count (973) conflicts with its metadata (999); no immediate province parent is encoded in the ADM2 feature, and lawful authoritative boundaries/completeness are unresolved.'
    elif code=='CYP': reason=f"Baseline district {p['name']} matches its pinned 2017 ADM1 source feature (IoU {iou:.3f}); official DLS comparison IoU is {dls_iou}. Large differences for some districts require a dated, legally and territorially contextualized crosswalk; name/count agreement does not resolve boundary meaning or completeness."
    elif code=='GRC': reason=f"Baseline {p['name']} matches the pinned 2010 ADM3 feature; the source identifies municipalities, but later 2021 census-unit intersections are a statistical crosswalk only, and current legal parent/identity, license lineage and full island coverage remain unresolved. See greece-2021-crosswalk-screen.csv."
    elif ident=='CYN+00?': reason='Natural Earth 5.1.1 supplies a Northern Cyprus map unit and a dataset type label; this does not establish legal status, official administrative parent, current boundary or a province-tier Atlas purpose.'
    elif ident=='country-CNM': reason='Natural Earth describes this map unit as the Cyprus U.N. Buffer Zone and type Indeterminate; primary UN/legal evidence is needed for current geography, neutral label, parent and tier purpose.'
    else: reason='Natural Earth portrays a named UK Sovereign Base Area map unit; that is cartographic evidence, not the legal delimitation source or proof that the one-location province tier is suitable.'
    rows.append({'id':ident,'name':p['name'],'parent_id':parent,'parent_name':pp.get('name',hier.get(parent,{}).get('name','')),'parent_chain_json':json.dumps(parent_chain,ensure_ascii=False,separators=(',',':')),'parent_geometry_status':'not measured: no complete province polygons in this packet baseline','area_km2_epsg6933':round(area/1e6,3),'baseline_components':comps,'source_id':meta.get('source_id','natural-earth'),'source_feature_id':src_feature_id,'source_name':src_name,'source_parent_group':source_parent_group,'source_parent_relationship_status':source_parent_status,'source_layer_feature_count':source_layer_count,'source_completeness_status':source_count_status,'source_metadata_source':metadata_source,'source_boundary_type':boundary_type,'source_canonical_role':canonical_role,'source_role':role,'source_vintage':meta.get('reference_year','Natural Earth 5.1.1; contemporary portrayal (no boundary date field)'),'source_license':meta.get('license','Public domain'),'source_metadata_license':metadata_license,'source_metadata_license_detail':license_detail,'source_update_date':source_update,'source_build_date':source_build,'baseline_to_pinned_source_iou_epsg6933':round(iou,6) if iou is not None else '', 'source_area_coverage_by_baseline':round(cover,6) if cover is not None else '', 'baseline_inside_parent_fraction_epsg6933':round(parent_share,6) if parent_share is not None else '', 'baseline_fraction_of_parent_epsg6933':round(child_share,6) if child_share is not None else '', 'official_Cyprus_DLS_name':dls_name,'baseline_to_DLS_iou_epsg6933':dls_iou,'classification':'insufficient-evidence','reason':reason,'source_url':source_url})
    if parent: parent_groups.setdefault(parent,[]).append(ident)
# Record exact provenance and source-count check
with open(OUT/'assessment.csv','w',newline='') as fp:
    w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator="\n"); w.writeheader(); w.writerows(rows)
with open(OUT/'geometry-components.csv','w',newline='') as fp:
    w=csv.DictWriter(fp,fieldnames=list(component_rows[0]),lineterminator="\n");w.writeheader();w.writerows(component_rows)
# Per-province and area outcome ledger: no inherited approval from packet partition.
import unicodedata
def normalize_name(value): return ''.join(c for c in unicodedata.normalize('NFKD',value).casefold() if not unicodedata.combining(c) and c.isalnum())
tur_name_index={}
for source_feature in sources['TUR'][0]: tur_name_index.setdefault(normalize_name(source_feature['properties']['shapeName']),[]).append(source_feature)
istanbul_alias={'adalar':'princeislands'}; istanbul_rows=[]
for roster_unit in istanbul_roster:
    key=istanbul_alias.get(normalize_name(roster_unit['name']),normalize_name(roster_unit['name']))
    candidates=tur_name_index.get(key,[])
    if len(candidates)!=1: raise ValueError(f"Official Istanbul district {roster_unit['name']} matches {len(candidates)} pinned source features")
    source_feature=candidates[0]; source_props=source_feature['properties']; location_id='gb:TUR:ADM2:'+str(source_props['shapeID']); atlas_props=parents.get(location_id)
    istanbul_rows.append({'official_district_name':roster_unit['name'],'official_source_url':roster_unit['url'],'geoBoundaries_shapeName':source_props['shapeName'],'geoBoundaries_shapeID':source_props['shapeID'],'exact_atlas_location_id_candidate':location_id,'atlas_baseline_present':bool(atlas_props),'atlas_baseline_name':atlas_props.get('name','') if atlas_props else '', 'atlas_parent_id':atlas_props.get('parent_id','') if atlas_props else '', 'atlas_parent_matches_istanbul_province':bool(atlas_props and atlas_props.get('parent_id')=='framework:province:istanbul:69a618445c3d'),'review_status':'present baseline ID' if atlas_props else 'officially-listed current district not represented by this exact geoBoundaries ID in baseline','interpretation':'Official province-specific district list joined by normalized name to a unique pinned source feature and exact shapeID. geoBoundaries ADM2 encodes only shapeGroup=TUR, not an immediate province parent. Absence flags a source/Atlas crosswalk gap, not automatic authority to add or transfer IDs.'})
assert len(istanbul_rows)==39 and sum(bool(x['atlas_baseline_present']) for x in istanbul_rows)==7
with open(OUT/'istanbul-completeness.csv','w',newline='') as fp:
    w=csv.DictWriter(fp,fieldnames=list(istanbul_rows[0]),lineterminator="\n");w.writeheader();w.writerows(istanbul_rows)
with open(OUT/'scope-assessment.csv','w',newline='') as fp:
    fields=['scope_type','id','name','full_scope_count','owned_count','classification','reason']
    w=csv.DictWriter(fp,fieldnames=fields,lineterminator="\n"); w.writeheader()
    for a in scope['area_scopes']:
        w.writerow(dict(scope_type='area',id=a['id'],name=a['name'],full_scope_count=a['full_area_location_count'],owned_count=a['owned_member_location_count'],classification='insufficient-evidence',reason='Area completeness and overall tier purpose require combined regional evidence; Turkey is only a 198/911 workload subset.'))
    for q in province_scopes:
        istanbul=q['name']=='İstanbul'
        w.writerow(dict(scope_type='province',id=q['id'],name=q['name'],full_scope_count=q['full_province_locations'],owned_count=len(q['owned_location_ids']),classification='correction-needed' if istanbul else 'insufficient-evidence',reason='Official İstanbul district roster lists 39 current districts; this baseline province has 7 exact source-matched locations. 32 roster units match pinned 2021 source features but are absent from the baseline. Follow-up #821 owns the identity/parent/source reconciliation; no automatic additions.' if istanbul else 'Province cluster purpose, neighboring tier consistency and omitted settlement/physical coverage not established by the lower-tier source roster.'))
by_id={r['id']:r for r in rows}
with open(OUT/'province-scale-screen.csv','w',newline='') as fp:
    fields=['province_id','province_name','full_location_count','owned_location_count','current_official_district_roster_count','official_districts_unrepresented_by_current_baseline','largest_owned_location_id','largest_owned_location_name','largest_owned_location_area_km2_epsg6933','median_owned_location_area_km2_epsg6933','largest_to_median_area_ratio','purpose_review']
    w=csv.DictWriter(fp,fieldnames=fields,lineterminator="\n");w.writeheader()
    for q in province_scopes:
        items=[by_id[x] for x in q['owned_location_ids'] if x in by_id]
        sizes=sorted(float(x['area_km2_epsg6933']) for x in items)
        if sizes:
            mid=len(sizes)//2; median=sizes[mid] if len(sizes)%2 else (sizes[mid-1]+sizes[mid])/2
            largest=max(items,key=lambda x:float(x['area_km2_epsg6933']))
        else: median=0;largest={'id':'','name':'','area_km2_epsg6933':0}
        is_istanbul=q['name']=='İstanbul'
        w.writerow({'province_id':q['id'],'province_name':q['name'],'full_location_count':q['full_province_locations'],'owned_location_count':len(items),'current_official_district_roster_count':len(istanbul_rows) if is_istanbul else '', 'official_districts_unrepresented_by_current_baseline':'; '.join(x['official_district_name'] for x in istanbul_rows if not x['atlas_baseline_present']) if is_istanbul else '', 'largest_owned_location_id':largest['id'],'largest_owned_location_name':largest['name'],'largest_owned_location_area_km2_epsg6933':largest['area_km2_epsg6933'],'median_owned_location_area_km2_epsg6933':round(median,3),'largest_to_median_area_ratio':round(float(largest['area_km2_epsg6933'])/median,3) if median else '', 'purpose_review':'Official İstanbul list has 39 districts, with 7 current baseline members and 32 exact source candidates absent; parent/identity/geographic crosswalk required.' if is_istanbul else 'Scale screen only; ratio does not establish an outlier, administrative error, or parent-area share. No complete parent province polygon was available for this screen.'})
# Source profile table and hash manifest, preserving source distinctions.
profiles=[]
for code,(fs,md) in sources.items():
    adm_level={'CYP':'ADM1','GRC':'ADM3','TUR':'ADM2'}[code]
    meta_path=SRC/f'geoBoundaries-{code}-{adm_level}-metaData.json'
    raw=SRC/f'geoBoundaries-{code}-{adm_level}.geojson.gz'
    count=int(md.get('admUnitCount',-1))
    profiles.append({'source_id':'gb:'+code+':'+adm_level, 'feature_count':len(fs),'pinned_metadata_count':count, 'count_matches':count==len(fs),'year':md.get('boundaryYear'),'canonical_role':md.get('boundaryCanonical'),'source':md.get('boundarySource'),'license':md.get('boundaryLicense'),'license_detail':md.get('licenseDetail'),'license_source':md.get('licenseSource'),'build_date':md.get('buildDate'),'data_update':md.get('sourceDataUpdateDate'),'retrieval_utc':'2026-10-04','release_commit':'9469f09592ced973a3448cf66b6100b741b64c0d','geojson_gzip_sha256':digest(raw),'metadata_sha256':digest(meta_path),'metadata_url':f'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/{code}/{adm_level}/geoBoundaries-{code}-{adm_level}.metaData.json'})
json.dump({'generated_by':'build_review.py','scope_count':len(rows),'pinned_issue_member_location_ids_sha256':scope['member_location_ids_sha256'],'local_ordered_id_json_sha256':hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest(),'macro_release':scope['release'],'frozen_region_geometry_sha256':scope['frozen_region_geometry_sha256'],'frozen_region_member_ids_sha256':scope['frozen_region_member_ids_sha256'],'macro_certificate_sha256':scope['macro_certificate_sha256'],'source_profiles':profiles,'classification_summary':{x:sum(r['classification']==x for r in rows) for x in ['justified','correction-needed','insufficient-evidence']},'limits':['Area uses EPSG:6933 equal-area projection; area screens are not tier approval.','No settlement census or complete island inventory is supplied by these administrative layers.','geoBoundaries Turkey ADM2 pinned GeoJSON count differs from its own pinned metadata.','Greek source role/vintage/license do not establish current island municipality identities.','For special Natural Earth entries, classification and label are map-unit portrayals rather than legal determinations.']},open(OUT/'source-inventory.json','w'),indent=2)
print('rows',len(rows),'province scopes',len(province_scopes),'area scopes',len(scope['area_scopes']))
print('source profiles',[(x['source_id'],x['feature_count'],x['pinned_metadata_count'],x['count_matches']) for x in profiles])
