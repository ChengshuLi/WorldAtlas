#!/usr/bin/env python3
"""Build the #1018 evidence receipt from immutable baseline inputs and outputs."""
import gzip, hashlib, json, pathlib, subprocess
R=pathlib.Path(__file__).resolve().parents[3]
D=pathlib.Path(__file__).resolve().parent
REL=D.relative_to(R).as_posix()
BASE='7646e0962afab6cc4f566439bb2f96890ae4b91e'
def h(b): return hashlib.sha256(b).hexdigest()
def git(path): return subprocess.check_output(['git','show',f'{BASE}:{path}'],cwd=R)
def fd(path,baseline=False,compressed=False,role=None):
    b=git(path) if baseline else (R/path).read_bytes()
    x={'path':path,'bytes':len(b),'sha256':h(b),'hash_kind':'file-bytes'}
    if compressed:
        q=gzip.decompress(b); x.update(uncompressed_bytes=len(q),uncompressed_sha256=h(q))
    if role:x['role']=role
    return x
scope_path='data/regional-review/regional-review-d282e62cf0209796/scope.json'
unit_path='data/regional-review/regional-review-d282e62cf0209796/unit-assessments.json'
prov_path='data/regional-review/regional-review-d282e62cf0209796/province-assessments.json'
SRC='data/regional-review/regional-review-d282e62cf0209796/source'
paths=['data/world-index.json','data/geography/part-22.json','data/hierarchy.json','data/administrative-sources.json','data/geographic-releases/current-manifest.json',
'data/macro-foundation/regional-handoffs.json.gz','data/macro-foundation/macro-certificate.json','data/macro-foundation/approved-boundary-decisions.json',
 scope_path,unit_path,prov_path,f'{SRC}/source-provenance.json',f'{SRC}/issue-423-api-snapshot.json',f'{SRC}/issue-423-comments-snapshot.json',f'{SRC}/gurs-wfs-collections.json']
for country,level in [('SRB','ADM1'),('SRB','ADM2'),('SVN','ADM1'),('SVN','ADM2')]:
    paths += [f'{SRC}/geoboundaries-9469f09/geoBoundaries-{country}-{level}.geojson',f'{SRC}/geoboundaries-9469f09/geoBoundaries-{country}-{level}-metaData.json']
paths += [f'{SRC}/gurs-municipal-boundaries.geojson',f'{SRC}/gurs-statistical-regions.geojson']
paths += ['data/regional-review/followup-yugoslavia-423-slovenia-names-20261005/2017-name-assessment.csv','data/regional-review/followup-yugoslavia-423-slovenia-names-20261005/source/gurs-obcine-h-53-codes-2017.json','data/regional-review/followup-yugoslavia-423-slovenia-names-20261005/source/gurs-obcine-h-request.json','data/regional-review/followup-yugoslavia-423-slovenia-names-20261005/source-provenance.json','data/regional-review/followup-yugoslavia-423-slovenia-names-20261005/reproduction-summary.json']
paths=list(dict.fromkeys(paths)); baseline_files=[fd(p,True,p.endswith('.gz'),'original-source' if '/source/' in p else None) for p in paths]
B={x['path']:x for x in baseline_files}
scope=json.loads(git(scope_path)); ids=scope['member_location_ids']; subject_hash=h(json.dumps(sorted(ids),separators=(',',':')).encode())
assert len(ids)==278 and len(set(ids))==278
world=json.loads(git('data/world-index.json'))
assert 'geography/part-22.json' in world['parts']
feature_ids={x.get('id',x.get('properties',{}).get('id')) for x in json.loads(git('data/geography/part-22.json'))['features']}
assert set(ids)<=feature_ids
pins={'issue_423_scope':B[scope_path]['sha256'],'issue_423_unit_assessments':B[unit_path]['sha256'],'issue_423_parent_assessments':B[prov_path]['sha256'],
'world_index':B['data/world-index.json']['sha256'],'hierarchy':B['data/hierarchy.json']['sha256'],'source_registry':B['data/administrative-sources.json']['sha256'],
'current_geographic_release_manifest':B['data/geographic-releases/current-manifest.json']['sha256'],'macro_certificate':B['data/macro-foundation/macro-certificate.json']['sha256'],
'approved_boundary_decisions':B['data/macro-foundation/approved-boundary-decisions.json']['sha256'],'regional_handoffs_gzip':B['data/macro-foundation/regional-handoffs.json.gz']['sha256']}
pin_files={k:v for k,v in zip(pins,['', '', '', '', '', '', '', '', '', ''])}
pin_files={'issue_423_scope':scope_path,'issue_423_unit_assessments':unit_path,'issue_423_parent_assessments':prov_path,
'world_index':'data/world-index.json','hierarchy':'data/hierarchy.json','source_registry':'data/administrative-sources.json',
'current_geographic_release_manifest':'data/geographic-releases/current-manifest.json','macro_certificate':'data/macro-foundation/macro-certificate.json',
'approved_boundary_decisions':'data/macro-foundation/approved-boundary-decisions.json','regional_handoffs_gzip':'data/macro-foundation/regional-handoffs.json.gz'}
output_names=['findings.md','parent-study.json','geometry-comparison.json','source-provenance.json','issue-1018-api-snapshot.json','issue-1018-comments-snapshot.json','reproduce-parent-study.py','reproduce-geometry-overlay.py','build-evidence-manifest.py','issue-1016-overlap.csv','validation/positive-control.json','validation/negative-control.json','validation/reproducibility.json']
outputs=[fd(f'{REL}/{n}') for n in output_names]
P=json.loads((D/'parent-study.json').read_text()); G=json.loads((D/'geometry-comparison.json').read_text())
def out_hash(name):return next(x['sha256'] for x in outputs if x['path']==f'{REL}/{name}')
S=[]
def source(i,url,role,vintage,license_status,terms,verification,limit,restore):
    S.append({'id':i,'url':url,'role':role,'vintage':vintage,'retrieved_at':'2026-10-05','license':{'status':license_status,'terms':terms},
    'retention':'restoration-only','verification':verification,'restoration':restore,'limit':limit,'temporal_status':'reference'})
source('geoboundaries-srb','https://github.com/wmgeolab/geoBoundaries/tree/9469f09592ced973a3448cf66b6100b741b64c0d','2017 Serbian ADM1 district and ADM2 local-unit geometry','boundaryYear 2017; source update 2023-01-19; build 2023-12-12','redistributable','ODbL 1.0; attribute geoBoundaries and underlying OpenStreetMap/Wambacher source.','verified','Not current official RZS boundaries; national aggregate count cannot verify each of the 12 memberships.','Complete raw features and metadata are pinned at exact baseline paths in baseline.files and source-provenance.json; restore from the same upstream commit and collection paths.')
source('geoboundaries-svn-adm2','https://github.com/wmgeolab/geoBoundaries/tree/9469f09592ced973a3448cf66b6100b741b64c0d','2017 Slovenian ADM2 municipality-like source polygons','boundaryYear 2017; source update 2023-01-19; build 2023-12-12','redistributable','ODbL 1.0; attribute geoBoundaries and underlying OpenStreetMap/Wambacher source.','verified','2017 source polygons do not establish current identity/boundaries; one out-of-scope duplicate-name Maribor sliver exists.','Complete raw feature layer and metadata are pinned at exact baseline paths in baseline.files and source-provenance.json; restore same upstream commit.')
source('gisco-svn-nuts2','https://ec.europa.eu/eurostat/web/gisco/geodata/reference-data/administrative-units-statistical-units/nuts','2021 Slovenia NUTS2 cohesion parent polygons','NUTS boundary year 2021; geoBoundaries build 2023-12-12','redistributable','CC BY 4.0; attribute Eurostat/GISCO.','verified','NUTS2 statistical cohesion regions, not administrative provinces; vintage differs from ADM2 and current GURS.','Complete raw features and metadata are pinned at baseline source paths; restore same geoBoundaries commit/GISCO layer.')
source('gurs-current','https://www.e-prostor.gov.si/en/access-to-geodetic-data/','Current GURS municipalities and NUTS3 statistical region geometries; official reuse terms','Live OGC WFS retrieved 2026-10-05; retained feature DATUM_SYS dates','redistributable','CC BY 4.0; cite Surveying and Mapping Authority of the Republic of Slovenia, dataset type and retrieval date.','verified','Current polygons are not historical equivalence; GURS notes service/data quality and availability limits.','Original full licensed WFS files and collection catalog are pinned in baseline.files and listed with exact URLs/hashes in source-provenance.json.')
source('rzs-current-classification','https://www.stat.gov.rs/sr-latn/oblasti/registar-prostornih-jedinica-i-gis/administrativno-teritorijalna-podela-i-nstj-nivoi-1-2-3/','Current official Serbian administrative tier and local-unit aggregate counts','Page accessed 2026-10-05; page has no separate as-of date','redistributable','RZS reuse terms allow reuse of statistical data/files with attribution and clear marking of changes; https://www.stat.gov.rs/sr-latn/copyright/.','verified','Current national counts only; no exact per-district roster/boundary crosswalk.','Restore the official page directly and inspect current RZS table; findings and URL are in source-provenance.json.')
source('rzs-unit-register','https://www.stat.gov.rs/media/412350/sifarnikgradovi-opstine-tekucestanje.xlsx','Current status Serbian municipality/city municipality/city official-code roster','Linked by RZS in page accessed 2026-10-05; workbook revision not retrieved','redistributable','RZS reuse terms require attribution and a clear note of changes; https://www.stat.gov.rs/sr-latn/copyright/.','unverified','XLSX bytes/hash and per-district current roster not retrieved; Serbia full-parent completeness is unresolved.','Restore this exact official linked XLSX. Direct shell API failed local TLS chain validation; web content service does not parse XLSX. Retain bytes, response metadata, date and SHA-256, then crosswalk all 12 districts by official code.')
source('surs-cohesion-membership','https://www.stat.si/StatWeb/en/news/Index/7910','SURS official eight eastern/four western NUTS3 statistical-region cohesion membership','2019 territorial-unit registry context; accessed 2026-10-05','unknown','Only factual notes and URL retained; full-page reproduction terms not established.','verified','2019 grouping supports statistical-tier semantics, not current legal geometry.','Restore exact SURS page and inspect its 8/4 named NUTS3 lists.')
source('surs-current-totals','https://www.stat.si/statweb/en/News/Index/14129','Current SURS totals for 12 statistical regions and 212 municipalities','Published 2026-02-17; updated data through 2024','unknown','Only factual notes and URL retained; full-page reproduction terms not established.','verified','Counts do not establish child identity or boundaries.','Restore exact SURS article.')
source('surs-skte','https://www.stat.si/dokument/12673/SKTE_2024_angl.pdf','Official SKTE/NUTS classification context','2024-01-01 classification; accessed 2026-10-05','unknown','PDF not retained; document reuse terms not established.','verified','Classification does not establish individual boundary membership.','Restore exact official PDF and inspect level definitions.')
source('govsi-municipality-role','https://www.gov.si/en/topics/municipalities-in-numbers/','Government of Slovenia municipality definition and Ankaran establishment context','Page modified 2026-06-04; accessed 2026-10-05','unknown','Only factual notes and URL retained; reuse terms not established.','verified','Does not establish the historic boundary of the 2017 polygons.','Restore exact official page and inspect municipality definition/history.')
source('gurs-historical-names-1016','https://ipi.eprostor.gov.si/wfs-si-gurs-rpe/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=SI.GURS.RPE%3AOBCINE_H','Dated official 2017 Slovenian municipality names for 53 issue-overlapping IDs','OBCINE_H exact-code history queried 2026-10-05; intervals evaluated at 2017-01-01 and 2017-07-01','redistributable','GURS public data CC BY 4.0 under GURS access terms; attribute GURS and identify derived assessment.','verified','Historical WFS response has no geometry; cannot establish historic boundaries, parent semantics or region approval.','Original response, exact request, provenance, assessment and summary are pinned at fresh-main baseline paths and exact hashes in baseline.files; overlap rows are generated in issue-1016-overlap.csv.')
source('gurs-terms','https://www.e-prostor.gov.si/en/access-to-geodetic-data/','Official GURS reuse terms and quality caveats','Accessed 2026-10-05','redistributable','CC BY 4.0 with source/type/date attribution.','verified','License is not positional accuracy certification.','Restore official terms page; raw datasets remain pinned under source gurs-current.')
# Ledger helper: numeric metrics must cite an exact immutable input/output hash.
M=[]
def m(i,v,u,sha_,n=None,d=None):
 x={'id':i,'value':v,'unit':u,'vintage':'baseline','input_sha256':sha_,'evaluation_commit':BASE}
 if n is not None:x.update(numerator=n,denominator=d)
 M.append(x)
m('scope-locations',278,'location IDs',pins['issue_423_scope'])
m('scope-parents',17,'parent IDs',pins['issue_423_parent_assessments'])
m('scoped-serbian-children',67,'location IDs',pins['issue_423_unit_assessments'])
m('scoped-slovenian-children',211,'location IDs',pins['issue_423_unit_assessments'])
for k,v in P['source_collection_counts'].items():
 layer=k.split('-'); path=f'{SRC}/geoboundaries-9469f09/geoBoundaries-{layer[0]}-{layer[1]}.geojson';m('features-'+k,v['feature_count'],'features',B[path]['sha256'])
GURS=G['current_GURS_region_municipality_geometry'];m('GURS-current-municipalities',212,'features',B[f'{SRC}/gurs-municipal-boundaries.geojson']['sha256'])
m('GURS-current-NUTS3-regions',12,'features',B[f'{SRC}/gurs-statistical-regions.geojson']['sha256'])
m('GURS-municipalities-dominant-overlap-99.9pct',212,'municipalities',B[f'{SRC}/gurs-municipal-boundaries.geojson']['sha256'])
m('GURS-municipalities-crossing-more-than-one-region',60,'municipalities',B[f'{SRC}/gurs-municipal-boundaries.geojson']['sha256'])
for x in GURS['cohesion_region_geometry_comparison']:
    m('current-'+('east' if x['cohesion_region'].startswith('V') else 'west')+'-municipalities',x['municipality_count_by_maximum_GURS_region_overlap'],'municipalities',B[f'{SRC}/gurs-municipal-boundaries.geojson']['sha256'])
for x in G['parent_comparisons']:
    if x.get('parent_child_comparison'):
        m('parent-symdiff-'+x['parent_id'],x['parent_child_comparison']['symmetric_difference_share_of_parent'],'fraction of parent area',out_hash('geometry-comparison.json'))
for x in GURS['coastal_singleton_polygon_crosswalks']:
    m('coastal-IoU-'+x['location_id'],x['intersection_over_union'],'intersection/union area fraction',out_hash('geometry-comparison.json'))
# Bind every numeric ledger result to the exact generated JSON value inspected by reviewers.
bindings=[]
for x in M:
    i=x['id']; path=f'{REL}/parent-study.json'; ptr=None
    if i=='scope-locations':ptr='/scope/location_count'
    elif i=='scope-parents':ptr='/scope/parent_count'
    elif i=='scoped-serbian-children':ptr='/scope/children_by_country/SRB'
    elif i=='scoped-slovenian-children':ptr='/scope/children_by_country/SVN'
    elif i.startswith('features-'):
        key=i[len('features-'):];ptr='/source_collection_counts/'+key.replace('~','~0').replace('/','~1')+'/feature_count'
    elif i=='GURS-current-municipalities':path=f'{REL}/geometry-comparison.json';ptr='/current_GURS_region_municipality_geometry/municipality_features'
    elif i=='GURS-current-NUTS3-regions':path=f'{REL}/geometry-comparison.json';ptr='/current_GURS_region_municipality_geometry/statistical_region_features'
    elif i=='GURS-municipalities-dominant-overlap-99.9pct':path=f'{REL}/geometry-comparison.json';ptr='/current_GURS_region_municipality_geometry/crosswalk_summary/municipalities_with_maximum_overlap_share_at_least_0_999'
    elif i=='GURS-municipalities-crossing-more-than-one-region':path=f'{REL}/geometry-comparison.json';ptr='/current_GURS_region_municipality_geometry/crosswalk_summary/municipalities_touching_multiple_region_polygons'
    elif i in ('current-east-municipalities','current-west-municipalities'):
        path=f'{REL}/geometry-comparison.json';idx=0 if i=='current-east-municipalities' else 1;ptr=f'/current_GURS_region_municipality_geometry/cohesion_region_geometry_comparison/{idx}/municipality_count_by_maximum_GURS_region_overlap'
    elif i.startswith('parent-symdiff-'):
        path=f'{REL}/geometry-comparison.json';pid=i[len('parent-symdiff-'):];idx=next(j for j,z in enumerate(G['parent_comparisons']) if z['parent_id']==pid);ptr=f'/parent_comparisons/{idx}/parent_child_comparison/symmetric_difference_share_of_parent'
    elif i.startswith('coastal-IoU-'):
        path=f'{REL}/geometry-comparison.json';loc=i[len('coastal-IoU-'):];idx=next(j for j,z in enumerate(GURS['coastal_singleton_polygon_crosswalks']) if z['location_id']==loc);ptr=f'/current_GURS_region_municipality_geometry/coastal_singleton_polygon_crosswalks/{idx}/intersection_over_union'
    assert ptr, i
    bindings.append({'metric_id':i,'path':path,'json_pointer':ptr})
validation=[{'method_id':'full-polygon-comparison','kind':'positive-control','outcome':'passed','evidence_path':f'{REL}/validation/positive-control.json'},
 {'method_id':'full-polygon-comparison','kind':'negative-control','outcome':'passed','evidence_path':f'{REL}/validation/negative-control.json'},
 {'method_id':'identity-scope-join','kind':'reproducibility','outcome':'passed','evidence_path':f'{REL}/validation/reproducibility.json'}]
conclusions=[
 {'text':'The exact 17 parent IDs and 278 subject IDs reproduce against pinned packet inputs and current baseline hierarchy/containing geometry file; all 278 join one retained ADM2 feature by exact shapeID. This is scope/source identity only.','status':'supported','source_ids':['geoboundaries-srb','geoboundaries-svn-adm2','gisco-svn-nuts2']},
 {'text':'RZS distinguishes Serbia administrative-district tier from municipality/city local tiers; these 12 names match the 2017 ADM1 district source layer. Current per-district roster and boundary completeness remain unresolved without the current-status RZS workbook.','status':'unresolved','source_ids':['rzs-current-classification','rzs-unit-register','geoboundaries-srb']},
 {'text':'SURS defines two NUTS2 cohesion/statistical groupings over 8 eastern and 4 western NUTS3 statistical regions; current GURS maximum-area overlay assigns 148 municipalities east and 64 west. These are unlike Serbian administrative-district roles.','status':'supported','source_ids':['surs-cohesion-membership','surs-current-totals','gurs-current','gisco-svn-nuts2']},
 {'text':'Ankaran, Izola and Piran are current GURS municipality identities; each synthetic Atlas province parent has one same-name location and no same-name source ADM1 polygon. Dated polygon intersection-over-union with current GURS is low, so current legal identity is resolved but historical boundary equivalence is not.','status':'supported','source_ids':['govsi-municipality-role','gurs-current','geoboundaries-svn-adm2','gurs-terms']},
 {'text':'Current GURS statistical-region dissolved cohort polygons materially differ from the older 2021 GISCO NUTS2 shapes; no current geometry replacement is proposed.','status':'unresolved','source_ids':['gurs-current','gisco-svn-nuts2','surs-cohesion-membership']},
 {'text':'GURS historical-name evidence from merged issue #1016 resolves official names for 53 exact overlapping Slovenian IDs at 2017-01-01 and 2017-07-01; names are stable, but response geometry is absent and no boundary or parent finding follows.','status':'supported','source_ids':['gurs-historical-names-1016']},
 {'text':'The full retained 2017 SVN ADM2 collection contains a distinct 739.7 m2 second Maribor feature outside the 278 issue subjects with negligible overlap of the current GURS Maribor municipality; national source completeness needs a separate identity handoff.','status':'supported','source_ids':['geoboundaries-svn-adm2','gurs-current']}
]
subfiles={i:'data/geography/part-22.json' for i in ids}
receipts=[{'path':x['path'],'status':'added'} for x in outputs]+[{'path':f'{REL}/evidence-quality.json','status':'added'}]
obj={'version':1,'issue':1018,'lane':'geography','worker_id':'worldatlas-geography-1018-20261005-7fca','subject_ids':ids,'subject_ids_sha256':subject_hash,
'baseline':{'commit':BASE,'files':baseline_files,'pins':pins,'pin_files':pin_files,'subject_files':subfiles},'sources':S,'outputs':outputs,
'methods':[{'id':'identity-scope-join','kind':'source','description':'Join all #423 scope IDs through pinned scope/unit/parent ledgers, the actual world-index selected geography part and exact source shapeIDs; compare all source feature counts to metadata and preserve full scoped child ID sets.','software':'Python 3.12 standard library JSON/SHA-256','units':'counts and identifiers'},
{'id':'full-polygon-comparison','kind':'measurement','description':'Transform full unmodified complete source polygons, form child unions, and calculate intersections/unions/symmetric differences and area shares. Reject invalid polygons; no snapping or repair. Current GURS municipality polygons are assigned to the NUTS3 feature with the maximum positive-area intersection, and current NUTS3 regions are grouped using official SURS 8/4 membership. Diagnostic only.','software':'Python 3.12; Shapely 2.1.2; PyProj 3.7.2','units':'square metres and area fractions','axis_order':'longitude-latitude','crs':'Input GeoJSON EPSG:4326; analysis EPSG:3035 (ETRS89 / LAEA Europe).','area_method':'Planar area of transformed polygons in equal-area CRS; union/intersection/symmetric-difference; no repair/snap/rounding.','distance_method':'Not used'}],
'metrics':M,'metric_bindings':bindings,'validation':validation,'summaries':[{'id':x['id'],'metric_id':x['id'],'value':x['value'],'unit':x['unit']} for x in M],
'conclusions':conclusions,'stages':{'research':'complete','implementation':'proposed','geographic_approval':'unapproved'},
'commands':[f'python3 {REL}/reproduce-parent-study.py','python3 -m pip install -r requirements.txt after scripts/local-workspace.mjs check admits storage',f'python3 {REL}/reproduce-geometry-overlay.py',f'node scripts/evidence-quality.mjs {REL}/evidence-quality.json',f'node scripts/check-handoff-scope.mjs --branch geography/yugoslavia-parent-tiers-1018-20261005-r1 --base origin/main --pr-body-file /tmp/pr-body-1018.txt --issue-file {REL}/issue-1018-api-snapshot.json'],
'change_receipts':receipts}
(D/'evidence-quality.json').write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
print('evidence manifest built; baseline bytes',sum(x['bytes'] for x in baseline_files),'baseline files',len(baseline_files),'sources',len(S),'metrics',len(M),'outputs',len(outputs))
