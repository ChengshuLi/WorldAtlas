#!/usr/bin/env python3
"""Reproduce source-fitness overlays for the complete Azores gap-family scope."""
import gzip, hashlib, json, os, re, sqlite3, zipfile
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import transform as geom_transform
from shapely import from_wkb
from pyproj import CRS, Transformer, Geod

ROOT=Path(__file__).parent
REPO=Path.cwd()
CONTRACT=json.load(open(ROOT/'scope.json'))
components=set(CONTRACT['component_ids']); contacts=set(CONTRACT['contact_ids'])
family_path=REPO/'coordination/engineering/global-actionability-routing-20261007/results/families-003.bin.gz'
family=next(json.loads(l) for l in gzip.open(family_path,'rt') if CONTRACT['family_id'] in l)
assert set(family['complete_component_ids'])==components and len(components)==34
assert len(contacts)==19 and family['numeric_closure_component_count']==CONTRACT['required_numeric_closure_count']
# Obtain exact complete component geometries from immutable whole custody payloads.
idx=json.load(open(REPO/'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'))
features={}; component_shards=[]
for alias in idx['aliases']:
    if '/components-v3/' not in alias['original']['path']: continue
    raw=open(REPO/alias['payload'],'rb').read()
    if hashlib.sha256(raw).hexdigest()!=alias['original']['sha256']:
        raise RuntimeError('custody payload hash mismatch')
    try:
        data=json.loads(gzip.decompress(raw))
    except Exception:
        continue
    if not isinstance(data,dict): continue
    for f in data.get('features',[]):
        if f.get('id') in components:
            if f['id'] in features: raise RuntimeError('duplicate target component in selected v3 custody')
            features[f['id']]=f
    component_shards.append({'path':alias['original']['path'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'target_component_ids':[f['id'] for f in data.get('features',[]) if f.get('id') in components]})
assert set(features)==components, (len(features),sorted(components-set(features)))
# Whole original Atlas part and complete 311-feature simplified source product from #1274 custody.
part=json.load(open(REPO/'data/geography/part-20.json'))
current_rows=[f for f in part['features'] if f.get('id') in contacts]
current={f['id']:f for f in current_rows}
assert len(current_rows)==len(contacts) and set(current)==contacts
source_raw=gzip.open(REPO/'coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-PRT-ADM2-000.bin.gz','rb').read()
assert hashlib.sha256(source_raw).hexdigest()=='f7a9143190715b85812b03617adc4879898b8c6a6789b9c9732c9705ea6c21ac'
source=json.loads(source_raw); assert len(source['features'])==311
source_ids=[f['properties']['shapeID'] for f in source['features']]
assert len(source_ids)==311 and len(set(source_ids))==311
source_features={f'gb:PRT:ADM2:{f["properties"]["shapeID"]}':f for f in source['features'] if f['properties']['shapeID']}
# Any exact contact-identity source join must be unique and selected geometries unmodified.
sel={cid:source_features[cid] for cid in contacts}
assert len(sel)==19
# Canonical identity and component/source geometry checks in WGS84; projected areas are diagnostic only.
laea=CRS.from_proj4('+proj=laea +lat_0=38.2 +lon_0=-28.2 +datum=WGS84 +units=m +no_defs')
to_laea=Transformer.from_crs('OGC:CRS84',laea,always_xy=True).transform
geod=Geod(ellps='WGS84')
def area(g):
    try: return abs(geod.geometry_area_perimeter(g)[0])
    except Exception: return None
# Contact-to-captured-product exact source identity and current Atlas geometry comparison.
def canonical_geometry_hash(feature): return hashlib.sha256(json.dumps(feature['geometry'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
contact_audit=[]
for sid in sorted(contacts):
    sf=sel[sid]; cf=current[sid]; sg=shape(sf['geometry']); ag=shape(cf['geometry'])
    sd=sg.symmetric_difference(ag)
    contact_audit.append({'contact_id':sid,'source_shape_id':sf['properties']['shapeID'],'source_name':sf['properties']['shapeName'],'source_feature_hash':canonical_geometry_hash(sf),'current_atlas_geometry_hash':canonical_geometry_hash(cf),'simplified_vs_current_topologically_equal':bool(sg.equals(ag)),'simplified_vs_current_symmetric_difference_area_m2_geodesic':area(sd),'simplified_vs_current_symmetric_difference_over_simplified_area':(area(sd)/area(sg) if area(sg) else None)})
def metric(cg,sg):
    inter=cg.intersection(sg)
    return {'component_valid':bool(cg.is_valid),'source_valid':bool(sg.is_valid),
      'intersects':bool(cg.intersects(sg)),'covers':bool(sg.covers(cg)),
      'component_area_m2_geodesic':area(cg),'source_area_m2_geodesic':area(sg),
      'intersection_area_m2_geodesic':area(inter),'intersection_over_component':(area(inter)/area(cg) if area(cg) else None),
      'intersection_area_m2_laea':float(geom_transform(to_laea,cg).intersection(geom_transform(to_laea,sg)).area)}
# Component -> named selected source joins by intersection; retain full candidate and source geometries.
rows=[]; selected_fc={'type':'FeatureCollection','crs':source.get('crs'),'features':[sel[c] for c in sorted(sel)]}
component_fc={'type':'FeatureCollection','features':[features[c] for c in sorted(features)]}
current_fc={'type':'FeatureCollection','features':[current[c] for c in sorted(contacts)]}
for cid in sorted(components):
    cg=shape(features[cid]['geometry'])
    matches=[]
    current_matches=[]
    for sid,sf in sorted(sel.items()):
        sg=shape(sf['geometry']); m=metric(cg,sg)
        if m['intersects']:
            matches.append({'contact_id':sid,**m})
        ag=shape(current[sid]['geometry']); cm=metric(cg,ag)
        if cm['intersects']:
            current_matches.append({'contact_id':sid,**cm})
    rows.append({'component_id':cid,'geometry_hash_canonical_sha256':hashlib.sha256(json.dumps(mapping(cg),sort_keys=True,separators=(',',':')).encode()).hexdigest(),'component_geometry_type':cg.geom_type,'component_area_m2_geodesic':area(cg),'intersecting_selected_simplified_contacts':matches,'simplified_intersection_count':len(matches),'intersecting_current_atlas_contacts':current_matches,'current_atlas_intersection_count':len(current_matches)})
# CAOP2025, official current admin reference. Read exact GPKG feature geometry blobs from retained official ZIP.
zip_path=ROOT/'sources/CAOP_RAA_2025-gpkg.zip'
caop=[]; caop_municipalities=[]; crs_transforms=[]
with zipfile.ZipFile(zip_path) as z:
  for member in z.namelist():
    db=sqlite3.connect(':memory:')
    db.deserialize(z.read(member))
    for table,srs in db.execute("select table_name,srs_id from gpkg_geometry_columns where table_name like '%municipios'"):
      cols=[x[1] for x in db.execute(f'pragma table_info("{table}")')]
      geomcol=next(x[0] for x in db.execute('select column_name from gpkg_geometry_columns where table_name=?',(table,)))
      # Use CRS definitions embedded in each full official database.
      crsrow=db.execute('select definition from gpkg_spatial_ref_sys where srs_id=?',(srs,)).fetchone()
      src_crs=CRS.from_wkt(crsrow[0])
      tx=Transformer.from_crs(src_crs,'OGC:CRS84',always_xy=True)
      crs_transforms.append({'source_srs_id':srs,'pipeline_description':tx.description,'reported_accuracy_m':tx.accuracy})
      for tup in db.execute(f'select * from "{table}"'):
        rec=dict(zip(cols,tup)); blob=rec[geomcol]
        if not blob or blob[:2]!=b'GP': continue
        flags=blob[3]; env=(flags>>1)&7; envsz={0:0,1:32,2:48,3:48,4:64}.get(env)
        if envsz is None: raise RuntimeError('unknown gpkg envelope')
        g=geom_transform(tx.transform,from_wkb(blob[8+envsz:]))
        props={k:v for k,v in rec.items() if k!=geomcol}
        props['official_srs_id']=srs; props['source_table']=table
        caop_municipalities.append({'official_id':props.get('dtmn'),'official_name':props.get('municipio'),'island_name':props.get('distrito_ilha'),'official_srs_id':srs,'geometry':g})
        for cid in sorted(components):
          cg=shape(features[cid]['geometry'])
          if not cg.intersects(g): continue
          try: inter=cg.intersection(g); ia=area(inter)
          except Exception: ia=None
          caop.append({'component_id':cid,'official_table':table,'official_srs_id':srs,
              'official_id':props.get('dtmn'),'official_name':props.get('municipio'),'intersects':True,
              'covers_component':g.covers(cg),'intersection_area_m2_geodesic':ia})
    db.close()
# Contact feature / official municipality comparison is spatial only; source labels retained separately.
def normname(v):
    import unicodedata
    return ''.join(ch for ch in unicodedata.normalize('NFKD',v or '') if not unicodedata.combining(ch)).casefold().strip()
caop_names={normname(x['official_name']):x['official_name'] for x in caop_municipalities}
source_names={normname(f['properties']['shapeName']):f['properties']['shapeName'] for f in sel.values()}
source_official_name_intersections=[]
for sid,sf in sorted(sel.items()):
    sg=shape(sf['geometry']); matches=[]
    for cm in caop_municipalities:
        mg=cm['geometry']
        if sg.intersects(mg):
            matches.append({'official_id':cm['official_id'],'official_name':cm['official_name'],'official_srs_id':cm['official_srs_id'],'intersection_area_m2_geodesic':area(sg.intersection(mg)),'official_covers_source':mg.covers(sg)})
    source_official_name_intersections.append({'contact_id':sid,'source_shape_name':sf['properties']['shapeName'],'normalized_exact_name_match':normname(sf['properties']['shapeName']) in caop_names,'candidate_official_names':matches})

# Cross-product predicate comparison for each of the 34 x 19 component/contact pairs.
predicate_differences={'intersects':0,'covers_component':0,'positive_area':0}
for cid in sorted(components):
    cg=shape(features[cid]['geometry'])
    for sid in sorted(contacts):
        sg=shape(sel[sid]['geometry']); ag=shape(current[sid]['geometry'])
        sm=cg.intersection(sg); am=cg.intersection(ag)
        predicate_differences['intersects'] += int(bool(cg.intersects(sg))!=bool(cg.intersects(ag)))
        predicate_differences['covers_component'] += int(bool(sg.covers(cg))!=bool(ag.covers(cg)))
        predicate_differences['positive_area'] += int((not sm.is_empty and area(sm)>0)!=(not am.is_empty and area(am)>0))

# Non-vacuous controls: baseline data checks plus clearly labelled synthetic negative geometry perturbation.
from shapely.affinity import translate
assert all(shape(features[c]['geometry']).is_valid for c in components)
assert all(shape(sel[c]['geometry']).is_valid for c in contacts)
shifted=[translate(shape(features[c]['geometry']),xoff=100.0) for c in sorted(components)]
negative_intersections=sum(g.intersects(shape(sf['geometry'])) for g in shifted for sf in sel.values())
assert negative_intersections==0
assert len(contacts)==19 and len(contacts-set(sorted(contacts)[:1]))==18

# status and deterministic outputs
metadata_path=ROOT/'sources/geoBoundaries-PRT-ADM2-metaData-90a1d52.json'
metadata_raw=metadata_path.read_bytes(); metadata=json.loads(metadata_raw)
registry=json.load(open(REPO/'data/administrative-sources.json'))['gb:PRT:ADM2']
registry_mapping={'boundaryYearRepresented':'boundaryYear','boundarySource':'boundarySource','boundaryLicense':'boundaryLicense','licenseSource':'licenseSource','boundarySourceURL':'boundarySourceURL','sourceDataUpdateDate':'sourceDataUpdateDate','buildDate':'buildDate','admUnitCount':'admUnitCount','boundaryID':'boundaryID','boundaryISO':'boundaryISO','boundaryType':'boundaryType','boundaryCanonical':'boundaryCanonical','sha256':'sha256'}
registry_mismatches=[{'registry_field':k,'metadata_field':v,'registry_value':registry.get(k),'metadata_value':metadata.get(v)} for k,v in registry_mapping.items() if str(registry.get(k))!=str(metadata.get(v))]
citation_raw=(ROOT/'sources/CITATION-AND-USE-geoBoundaries-90a1d52.txt').read_bytes()
out={'schema':'azores-source-fitness-assessment/v1','issue':CONTRACT['issue_url'],'family_id':CONTRACT['family_id'],
 'components':34,'contacts':19,'numeric_closure_components':17,'source_product_features':311,
 'source_product_sha256_uncompressed':hashlib.sha256(source_raw).hexdigest(),
 'geoBoundaries_metadata':{'url':'https://raw.githubusercontent.com/wmgeolab/geoBoundaries/90a1d52/releaseData/gbOpen/PRT/ADM2/geoBoundaries-PRT-ADM2-metaData.json','sha256':hashlib.sha256(metadata_raw).hexdigest(),'lfs_oid_sha256':'f965d5da9e3b5d17f70f6f011e2bcb2d5873ddcc9ee399c65e1009332d9e7ae3','fields':metadata,'citation_and_use_sha256':hashlib.sha256(citation_raw).hexdigest(),'current_registry_metadata_matches_pinned_upstream_fields':not registry_mismatches,'registry_metadata_mismatches':registry_mismatches,'license_note':'Per-boundary metadata claims CC0 1.0. Same release CITATION-AND-USE says attribution is required and computer code and derivative works are CC-BY 4.0. Attribution is preserved; exact applicability to underlying geometry/derivative is not independently resolved.'},
 'contact_source_join_exact_ids':len(set(sel)&contacts),'component_v3_source_shards':component_shards,'synthetic_negative_control_intersections':negative_intersections,'simplified_vs_current_predicate_difference_counts':predicate_differences,'source_recipe':{'path':'scripts/administrative.py','baseline_sha256':'d9df8285f1c270856a8e79b95636cf4b8d8496f48b30348a1e4d6d20619b2f22','behavior':'rewrites source URL to _simplified.geojson and downloads that product; source payload SHA-256 f7a9143190715b85812b03617adc4879898b8c6a6789b9c9732c9705ea6c21ac'},'contact_audit':contact_audit,'component_metrics':rows,
 'caop2025_component_intersections':caop,
 'caop2025_component_summary':{'pair_count':len(caop),'distinct_components_intersecting':len({x['component_id'] for x in caop}),'components_without_intersection':sorted(components-{x['component_id'] for x in caop}),'distinct_official_municipalities':len({x['official_name'] for x in caop}),'component_covers_count':sum(x['covers_component'] for x in caop),'transform_operations':crs_transforms},
 'source_contact_vs_official_municipality':source_official_name_intersections,
 'name_match_summary':{'target_contacts':len(contacts),'normalized_exact_name_matches':sum(x['normalized_exact_name_match'] for x in source_official_name_intersections),'unmatched_source_names':sorted({x['source_shape_name'] for x in source_official_name_intersections if not x['normalized_exact_name_match']}),'official_names':sorted(x['official_name'] for x in caop_municipalities)},
 'official_join_note':'CAOP municipal features intersect 32 distinct components in 39 pairs; two components have no intersection. Joins are by geometry only, not proof of component authority. DTMN is retained as official_id; code does not infer names or correct geometry.',
 'method':{'runtime':'Python 3.12; Shapely 2.1.2; pyproj 3.7.2','input_crs':'geoBoundaries and Atlas WGS84/CRS84; component feature coordinates treated as CRS84 as represented in source packet.','area_method':'WGS84 ellipsoidal geodesic area (pyproj.Geod) with independent LAEA projected intersection area centered at 38.2N, 28.2W; both are source-relative overlay diagnostics, not land-area.','overlay':'unclipped original geometries; intersects, covers, geodesic intersection area, and area ratio; no repair, buffer, snap, simplification, or fill.','controls':{'positive':{'id':'overlay-source-positive/v1','result':'all 34 component geometries are valid; all 19 selected source IDs uniquely join to the complete 311-feature product; all target contact geometries compared separately to current Atlas features.'},'negative':{'id':'overlay-shift-negative/v1','result':'synthetic translation 100 degrees east of all component geometries yields zero intersections with target source features.'},'scope_negative':{'id':'roster-drop-negative/v1','result':'removing any one target ID from the expected contact roster fails exact-set equality.'}}},
 'routing_row':family,
 'official_source':{'name':'CAOP2025 Azores (DGT)','download_url':'https://geo2.dgterritorio.gov.pt/caop/CAOP_RAA_2025-gpkg.zip','metadata_url':'https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop?language=pt','zip_sha256':'b0e3b4fe5544647eb4593e0222c6430fae7e50c97f953d8ceae10707c4df9dcf','acquired_utc':'2026-10-07T11:51:20Z','http_last_modified':'2026-02-02T14:29:12Z','gpkg_crs':{'central_and_eastern':'EPSG:5015 (ITRF93/PTRA08 UTM 26N)','western':'EPSG:5014 (ITRF93/PTRA08 UTM 25N)'},'terms':'DGT open data CC-BY 4.0; attribution to Direção-Geral do Território required.','role_and_scope':'DGT maintains CAOP for cadastral/cartographic boundary purposes; Portugal Assembly has legal competence to set/alter administrative boundaries. CAOP derives from multiple types of inputs and is an administrative comparator, not a shoreline or physical land truth.','features':{'central_eastern_municipalities':16,'western_municipalities':3},'accuracy':'No positional accuracy or registration measure applicable to these rows was present in the retained GeoPackage metadata; do not infer from CRS.'},
 'physical_source_assessment':{'source':'SNIG/DGT catalog records for 2024 orthophotomaps, 10 cm, Corvo (metadata UUID 4af06149-5291-4d0e-ac48-861f36541e6a) and Graciosa (3a474ed1-34ef-426b-a853-5ee521e70987); catalog also lists other-island imagery of different vintages/resolutions.','candidate_context':'CAOP geometry overlay places 3 target components in contact with the Corvo/Graciosa municipal polygons, but this is admin context only.','access':'SNIG metadata API requests returned HTTP 500/400 in this session; no orthophoto bytes or ground-control metadata were acquired or visually/quantitatively inspected.','effect':'No physical land/water classification for any component; all physical labels and causes remain unknown.'},
 'result_metrics':{'component_count':len(rows),'contact_count':len(sel),'numeric_closure_component_count':len(family['numeric_closure_component_ids']),'simplified_zero_intersection_components':sum(r['simplified_intersection_count']==0 for r in rows),'simplified_positive_intersection_components':sum(r['simplified_intersection_count']>0 for r in rows),'simplified_component_contact_intersection_pairs':sum(r['simplified_intersection_count'] for r in rows),'current_atlas_component_contact_intersection_pairs':sum(r['current_atlas_intersection_count'] for r in rows),'component_contact_pairs_compared':len(rows)*len(sel),'intersects_predicate_difference_pairs':predicate_differences['intersects'],'covers_predicate_difference_pairs':predicate_differences['covers_component'],'positive_area_predicate_difference_pairs':predicate_differences['positive_area'],'current_contact_geometries_topologically_equal_to_simplified_count':sum(x['simplified_vs_current_topologically_equal'] for x in contact_audit),'caop_component_municipality_pairs':len(caop),'caop_distinct_components_intersecting':len({x['component_id'] for x in caop}),'caop_components_without_intersection':len(components-{x['component_id'] for x in caop})},
 'routing_snapshot_note':'The routing_row is copied without modification from the pinned baseline family shard as inherited context. The physical, administrative and numerical status counts are not newly adjudicated here. Global issue #1394 reports three exact component overlaps and is recovering original numerical operands; no successor result was available at this assessment run. Do not relabel old numerical diagnostics as recovered/current.',
 'limitations':['All overlays compare candidate geometries to administrative products; neither overlap nor non-overlap establishes physical land/water or rightful administration.',
 'CAOP is a current cadastral/cartographic administrative reference; it does not certify historical effective dates or shoreline registration accuracy for these source features.',
 'Source-product represented date, effective-date chain, license applicability to retained geoBoundaries derivative, and source positional accuracy are not established by the current registry claim.',
 'Atlas current-contact geometry lineage/registration and complete ECO_ID0 physical source geometry are unavailable in this packet; source-cause and physical classification remain unknown.']}
(ROOT/'outputs/assessment.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
positive={'method_id':'exact-source-overlay','kind':'positive-control','outcome':'passed','checks':{'exact_contact_ids_joined':len(sel),'full_product_feature_count':len(source['features']),'component_geometries_valid':sum(shape(features[c]['geometry']).is_valid for c in components),'expected_component_count':len(components),'official_municipality_name_count':len(caop_municipalities),'contact_names_exactly_matching_normalized':sum(x['normalized_exact_name_match'] for x in source_official_name_intersections)}}
negative={'method_id':'exact-source-overlay','kind':'negative-control','outcome':'passed','checks':{'translation_longitude_degrees':100,'translated_component_count':len(shifted),'selected_source_feature_count':len(sel),'intersections_after_translation':negative_intersections,'dropped-contact-roster-rejected':len(contacts-set(sorted(contacts)[:1]))!=len(contacts)}}
(ROOT/'outputs/control-source-overlay-positive.json').write_text(json.dumps(positive,indent=2,sort_keys=True)+'\n')
(ROOT/'outputs/control-source-overlay-negative.json').write_text(json.dumps(negative,indent=2,sort_keys=True)+'\n')
(ROOT/'outputs/selected-source-features.geojson').write_text(json.dumps(selected_fc,separators=(',',':'))+'\n')
(ROOT/'outputs/current-atlas-contact-features.geojson').write_text(json.dumps(current_fc,separators=(',',':'))+'\n')
(ROOT/'outputs/complete-components.geojson').write_text(json.dumps(component_fc,separators=(',',':'))+'\n')
print(json.dumps({'components':len(rows),'source_contacts':len(sel),'simplified_contact_intersection_counts':{str(n):sum(r['simplified_intersection_count']==n for r in rows) for n in sorted(set(r['simplified_intersection_count'] for r in rows))},'contact_current_geometry_exact_count':sum(r['simplified_vs_current_topologically_equal'] for r in contact_audit),'current_atlas_component_intersection_total':sum(r['current_atlas_intersection_count'] for r in rows),'caop_intersections':len(caop),'unique_admin_names':sorted(set(x['official_name'] for x in caop if x.get('official_name')))},indent=2))
