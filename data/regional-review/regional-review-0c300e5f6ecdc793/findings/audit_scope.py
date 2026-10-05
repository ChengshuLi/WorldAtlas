#!/usr/bin/env python3
"""Reproduce exact issue-424 scope against checked-in Atlas and retained sources."""
from __future__ import annotations
import csv, glob, gzip, hashlib, json, pathlib, sys
import shapefile
from shapely.geometry import shape
from shapely.validation import explain_validity

ROOT = pathlib.Path(__file__).resolve().parents[4]
PACKET = pathlib.Path(__file__).resolve().parents[1]
SCOPE = json.loads((PACKET/'issue-scope.json').read_text())

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

atlas=[]
for p in glob.glob(str(ROOT/'data/geography/part-*.json')):
    atlas.extend(json.load(open(p))['features'])
byid={f['properties']['id']:f for f in atlas}
errors=[]
raw_t=json.load(open(PACKET/'sources/geoboundaries-9469f09/geoBoundaries-TUR-ADM2.geojson'))['features']
raw_s=json.load(open(PACKET/'sources/geoboundaries-9469f09/geoBoundaries-SVN-ADM2.geojson'))['features']
raw={('TUR',f['properties']['shapeID']):f for f in raw_t}
raw.update({('SVN',f['properties']['shapeID']):f for f in raw_s})
ne_path=PACKET/'sources/natural-earth-ca96624/ne_10m_admin_1_states_provinces.geojson.gz'
ne=json.loads(gzip.decompress(ne_path.read_bytes()))['features']
ne_istanbul=[f for f in ne if f.get('properties',{}).get('adm1_code')=='TUR-2265']
if len(ne_istanbul)!=1 or ne_istanbul[0]['properties'].get('type_en')!='Province' or ne_istanbul[0]['properties'].get('admin')!='Turkey' or ne_istanbul[0]['properties'].get('name')!='Istanbul': errors.append('Natural Earth Istanbul province record is missing or mismatched')
hgm_reader=shapefile.Reader(str(PACKET/'sources/hgm-2026/hgm-2026-district-boundary-lines.shp'))
hgm_fields=[f[0] for f in hgm_reader.fields[1:]]
hgm_records=[list(r) for r in hgm_reader.records()]
if len(hgm_records)!=2499 or 'shapeID' in [x.lower() for x in hgm_fields]: errors.append('HGM screen layer count or non-identifying-attribute check changed')
semantic=json.load(open(ROOT/'data/semantic-report.json'))
city_changes=[c for c in semantic.get('changes',[]) if c.get('id')=='atlas:city:TUR-2265']
if len(city_changes)!=1 or len(city_changes[0].get('replaces',[]))!=32: errors.append('Istanbul aggregation source report is missing or not a 32-feature replacement')
restoration=json.load(open(PACKET/'findings/source-restoration.json'))
hierarchy=json.load(open(ROOT/'data/hierarchy.json'))
def parent_name(pid):
    return next((x.get('name','') for x in hierarchy if x.get('id')==pid),'')
rows=[]
for id in SCOPE['member_location_ids']:
    f=byid.get(id)
    if not f: errors.append(f'missing Atlas feature: {id}'); continue
    p=f['properties']; m=p.get('metadata',{}); g=shape(f['geometry'])
    if id.startswith('gb:TUR:ADM2:'):
        sid=id.rsplit(':',1)[1]; src=raw.get(('TUR',sid)); jurisdiction='Turkey'; vintage='2021'; role='Districts'; lic='ODbL 1.0'; sourceid='geoBoundaries TUR-ADM2-54988432'; sn=src['properties']['shapeName'] if src else ''; source_geom=src['geometry']['type'] if src else ''; topology_reconciled=m.get('topology_reconciled',''); topology_note=m.get('topology_note',''); original_geom_sha256=m.get('original_geometry_sha256','')
        if not src: errors.append(f'missing raw Turkish feature: {id}')
        if p['name'] != sn: errors.append(f'name mismatch {id}: Atlas={p["name"]!r}; source={sn!r}')
        semantic='identity-and-tier-supported; exact Europe-side boundary membership unresolved'
        evidence_paths='sources/geoboundaries-9469f09/geoBoundaries-TUR-ADM2.geojson; sources/geoboundaries-9469f09/geoBoundaries-TUR-ADM2-metaData.json; sources/interior-ministry-district-foundation-2018.pdf (province pages 24, 30, 53, 78); sources/interior-ministry-valilikler.html; sources/tourism-ministry-regions.html; sources/goturkiye-thrace.html'
        citation_urls='https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/TUR/ADM2/geoBoundaries-TUR-ADM2.geojson; https://icisleri.gov.tr/kurumlar/icisleri.gov.tr/IcSite/illeridaresi/Bilgiler2/%C4%B0l%20ve%20%C4%B0l%C3%A7e%20Kurulu%C5%9F%20Tarihleri%202018.pdf; https://www.icisleri.gov.tr/valilikler; https://www.ktb.gov.tr/EN-99760/regions.html; https://goturkiye.com/thrace/thrace-goturkiye'
        handoff='Assess Europe-side membership against a declared boundary convention; Çanakkale contains transcontinental/strait geography and Tourism Thrace is a narrower administrative convention.'
        if p['name']=='Meriç': handoff+=' Its raw 2021 source geometry is Polygon but the Atlas display geometry is a topology-reconciled two-part MultiPolygon, including one near-zero sliver; engineering should inspect both without replacing the source.'
        if p['name']=='Marmaraereğlisi': handoff+=' Its raw 2021 source geometry is a two-part MultiPolygon, while Atlas is Polygon; the source has a second tiny component not separately present in the current geometry. Check island/source lineage before changing any boundary.'
    elif id.startswith('gb:SVN:ADM2:'):
        sid=id.rsplit(':',1)[1]; src=raw.get(('SVN',sid)); jurisdiction='Slovenia'; vintage='2017'; role='Municipality (geoBoundaries ADM2)'; lic='ODbL 1.0'; sourceid='geoBoundaries SVN-ADM2'; sn=src['properties']['shapeName'] if src else ''; source_geom=src['geometry']['type'] if src else ''; topology_reconciled=m.get('topology_reconciled',''); topology_note=m.get('topology_note',''); original_geom_sha256=m.get('original_geometry_sha256','')
        if not src: errors.append(f'missing raw Slovenian feature: {id}')
        semantic='current municipality identity supported by GOV.SI; Atlas source spelling Hodoj conflicts with official Hodoš/Hodos'
        evidence_paths='sources/geoboundaries-9469f09/geoBoundaries-SVN-ADM2.geojson; sources/geoboundaries-9469f09/geoBoundaries-SVN-ADM2-metaData.json; sources/govsi-hodos.html; sources/surs-pomurska-region.html; sources/govsi-history-slovenia.html'
        citation_urls='https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SVN/ADM2/geoBoundaries-SVN-ADM2.geojson; https://www.gov.si/drzavni-organi/upravne-enote/murska-sobota/o-upravni-enoti-murska-sobota/obcine-in-naselja-upravne-enote-murska-sobota/; https://www.stat.si/obcine/sl/Region/Index/1; https://www.gov.si/en/topics/history-of-slovenia/'
        handoff='Correct source-name rendering and review the historical Yugoslavia grouping; Slovenia has been independent since 1991, so this is not a current-state national parent.'
    else:
        sid='TUR-2265'; sn='Istanbul'; jurisdiction='Turkey'; vintage='Natural Earth 10m Admin 1 retained Atlas reference (undated modern reference)'; role='province-wide Atlas city aggregate'; lic='Public domain (Natural Earth)'; sourceid='Natural Earth Admin 1 / Atlas city aggregation'; source_geom=ne_istanbul[0]['geometry']['type'] if ne_istanbul else ''; topology_reconciled=m.get('topology_reconciled',''); topology_note=m.get('topology_note',''); original_geom_sha256=m.get('original_geometry_sha256',''); semantic='whole Istanbul aggregation is supported as Istanbul identity but crosses Europe and Asia'; evidence_paths='data/semantic-report.json (change index 38); sources/natural-earth-ca96624/ne_10m_admin_1_states_provinces.geojson.gz; sources/goturkiye-istanbul.html; sources/ibb-istanbul-air-quality-strategy.pdf'; citation_urls='https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/; https://goturkiye.com/bluevoyage/istanbul; https://cevre.ibb.istanbul/wp-content/uploads/2021/12/actionplan.pdf'; handoff='Do not treat the full Istanbul province aggregate as Europe-only. Determine a named area boundary or a sub-provincial split before asserting membership.'
    tier_class='justified' if id.startswith('gb:TUR:ADM2:') or id.startswith('gb:SVN:ADM2:') else 'justified'
    membership_class='insufficient-evidence' if id.startswith('gb:TUR:ADM2:') else ('correction-needed' if id.startswith('atlas:city:TUR-2265') or id.startswith('gb:SVN:ADM2:') else 'insufficient-evidence')
    source_feature=src if id.startswith('gb:') else (ne_istanbul[0] if ne_istanbul else None)
    source_shape=shape(source_feature['geometry']) if source_feature else None
    source_parts=list(source_shape.geoms) if source_shape is not None and hasattr(source_shape,'geoms') else ([source_shape] if source_shape is not None else [])
    source_component_summary=json.dumps([{'bounds':[round(x,8) for x in part.bounds],'exterior_vertices':len(part.exterior.coords) if hasattr(part,'exterior') else None} for part in source_parts],separators=(',',':'))
    rows.append({'location_id':id,'name':p['name'],'parent_id':p.get('parent_id',''),'parent_name':parent_name(p.get('parent_id','')),'individual_classification':membership_class,'source_tier_classification':tier_class,'area_membership_classification':membership_class,'geometry_type':f['geometry']['type'],'geometry_valid':g.is_valid,'geometry_validity_detail':explain_validity(g),'geometry_parts':len(g.geoms) if hasattr(g,'geoms') else 1,'geometry_component_summary':json.dumps([{'bounds':[round(x,8) for x in part.bounds],'exterior_vertices':len(part.exterior.coords) if hasattr(part,'exterior') else None} for part in (g.geoms if hasattr(g,'geoms') else [g])],separators=(',',':')),'source_dataset':sourceid,'source_feature_id':sid,'source_feature_name':sn,'source_tier_or_role':role,'source_geometry_type':source_geom,'source_geometry_parts':len(source_parts),'source_geometry_component_summary':source_component_summary,'atlas_topology_reconciled':topology_reconciled,'atlas_topology_note':topology_note,'atlas_original_geometry_sha256':original_geom_sha256,'source_vintage':vintage,'source_license':lic,'evidence_assessment':semantic,'evidence_paths':evidence_paths,'citation_urls':citation_urls,'engineering_handoff':handoff})
with open(PACKET/'findings/individual-assessments.csv','w',newline='') as out:
    w=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n'); w.writeheader(); w.writerows(rows)

# Scope integrity and shape/identity requirements.
if hashlib.sha256('\n'.join(sorted(SCOPE['member_location_ids'])).encode()).hexdigest()!=SCOPE['member_location_ids_sha256']: errors.append('frozen issue member ID roster hash does not reproduce')
if len(rows)!=33: errors.append(f'expected 33 assessment rows, found {len(rows)}')
if len(set(r['location_id'] for r in rows))!=33: errors.append('duplicate assessment IDs')
if sum(r['location_id'].startswith('gb:TUR:ADM2:') for r in rows)!=31: errors.append('expected 31 Turkey ADM2s')
if len(raw_t)!=973: errors.append(f'expected retained TUR source count 973, got {len(raw_t)}')
if len(raw_s)!=213: errors.append(f'expected retained SVN source count 213, got {len(raw_s)}')
# Area semantics summary, counts derive solely from scope and parent IDs.
parents={}
for r in rows: parents[r['parent_name']]=parents.get(r['parent_name'],0)+1
summary={'issue':424,'expected_scope_locations':SCOPE['location_count'],'assessed_locations':len(rows),'scope_member_ids_sha256_pinned':SCOPE['member_location_ids_sha256'],'scope_member_ids_sorted_newline_sha256':hashlib.sha256('\n'.join(sorted(SCOPE['member_location_ids'])).encode()).hexdigest(),'scope_ids_unique':len(set(SCOPE['member_location_ids']))==SCOPE['location_count'],'current_parent_counts':parents,'source_feature_counts':{'TUR_ADM2':len(raw_t),'SVN_ADM2':len(raw_s),'HGM_2026_unlabelled_lines':len(hgm_records)},'hgm_2026_dbf_fields':hgm_fields,'hgm_2026_detail_labels':sorted({r[hgm_fields.index('Detay_Adi')] for r in hgm_records}),'source_matching':{'Turkey_scoped_features':sum(bool(raw.get(('TUR',r['source_feature_id']))) for r in rows if r['source_dataset']=='geoBoundaries TUR-ADM2-54988432'),'Slovenia_scoped_features':sum(bool(raw.get(('SVN',r['source_feature_id']))) for r in rows if r['source_dataset']=='geoBoundaries SVN-ADM2'),'natural_earth_istanbul_province_record':len(ne_istanbul),'atlas_istanbul_replaced_features':len(city_changes[0].get('replaces',[])) if city_changes else 0},'geometry_component_counts':{str(n):sum(int(r['geometry_parts'])==n for r in rows) for n in sorted({int(r['geometry_parts']) for r in rows})},'source_vs_atlas_geometry_type_pairs':{a+' -> '+b:sum(r['source_geometry_type']==a and r['geometry_type']==b for r in rows) for a,b in sorted({(r['source_geometry_type'],r['geometry_type']) for r in rows})},'source_vs_atlas_component_discrepancies':[{'location_id':r['location_id'],'name':r['name'],'source_geometry_parts':r['source_geometry_parts'],'atlas_geometry_parts':r['geometry_parts'],'source_components':r['source_geometry_component_summary'],'atlas_components':r['geometry_component_summary']} for r in rows if r['source_geometry_parts']!=r['geometry_parts']],'invalid_geometry_count':sum(not r['geometry_valid'] for r in rows),'source_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted((PACKET/'sources').rglob('*')) if p.is_file()},'source_restoration_observed_sha256':{row['source_url']:row['observed_sha256'] for row in restoration['sources']},'reference_input_hashes':{str(p):sha(ROOT/p) for p in ['data/hierarchy.json','data/semantic-report.json','data/macro-foundation/europe-asia-boundary-decisions.json']},'audit_errors':errors}
(PACKET/'findings/audit-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
sys.exit(bool(errors))
