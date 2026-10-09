#!/usr/bin/env python3
"""Expose source-coverage remainders for partial Melanesia candidate matches."""
import datetime, gzip, hashlib, json, platform, subprocess, sys, time
from pathlib import Path
from shapely.geometry import shape, mapping

ROOT=Path(__file__).resolve().parents[3]
OWNED='research/geography/melanesia-gap-batch-37ed51b2-20261009/'
RUN='source-remainders-084-001'
PIN_META=json.loads((ROOT/OWNED/'source-remainder-pins.json').read_text())
COMMIT=PIN_META['baseline_commit'];helper='scripts/evidence/immutable.py'
helper_raw=subprocess.check_output(['git','-C',str(ROOT),'show',COMMIT+':'+helper])
ns={'__name__':'pinned_evidence','__file__':str(ROOT/helper)}
exec(compile(helper_raw,str(ROOT/helper),'exec'),ns)
Baseline,NewVintage,canonical_json=ns['Baseline'],ns['NewVintage'],ns['canonical_json']
baseline=Baseline(ROOT,COMMIT,PIN_META['files']);started=time.monotonic()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(baseline.pinned_bytes(path))
def published(path,receipt_path):
 raw=baseline.pinned_bytes(path);rec=load(receipt_path);rows=[x for x in rec['outputs']if x['path']==path]
 assert rec['status']=='complete'and len(rows)==1 and rows[0]['bytes']==len(raw)and rows[0]['sha256']==sha(raw)
 return json.loads(raw)

capture_path=OWNED+'vintages/candidate-capture-001/candidate-capture.json'
capture=published(capture_path,OWNED+'vintages/candidate-capture-001/publication.json')
candidates={x['component_id']:x for x in capture['candidate_records']}
join=published(OWNED+'vintages/source-comparison-capture-001/batch-source-comparisons.json',
    OWNED+'vintages/source-comparison-capture-001/publication.json')
by_id={x['component_id']:x for x in join['cases']}
geo_partial=[x for x in join['cases'] if x['disposition']=='native-grid-source-payload' and x['source_coverage_complete_in_prior_comparison'] is False]
geo_complete=[x for x in join['cases'] if x['disposition']=='native-grid-source-payload' and x['source_coverage_complete_in_prior_comparison'] is True]
assert len(geo_partial)==65 and len(geo_complete)==26
rows=[]
for row in geo_partial:
    rem=row['source_comparison_record']['component_minus_source_union']
    assert rem['is_empty'] is False and rem['geometry']
    rows.append({'component_id':row['component_id'],'candidate_feature_sha256':row['candidate_feature_sha256'],
        'candidate_geometry_sha256':row['candidate_geometry_sha256'],'source_basis':'retained-exact-consumed-simplified-product-source-comparison',
        'source_coverage_complete_in_prior_comparison':False,
        'candidate_minus_retained_source_union':rem,'source_subject_ids':row['positive_area_recorded_source_subject_ids'],
        'source_product_codes':row.get('source_product_codes'),
        'remainder_interpretation':'Geometry outside the retained source feature union in the prior admitted comparison. This does not identify water, processing cause, or boundary authority.'})

source_review_path='data/regional-review/new-caledonia-valid-province-source-20261005/'
review=load(source_review_path+'sources.json');readme=baseline.pinned_bytes(source_review_path+'README.md').decode()
assert all(x in readme for x in ('NCL-559','NCL-1259','NCL-1258'))
georep=next(x for x in review['sources']if x['id']=='NCL-GeoReP-2024')
file_by_path={x['path']:x for x in georep['source_files']}
source_root='data/regional-review/regional-review-1aa97b490604ea4e/sources/new-caledonia-province-parts/'
sources={}
for name,filename,target in [('PROVINCE NORD','province-nord.geojson','NCL-559'),('PROVINCE SUD','province-sud.geojson','NCL-1259'),('PROVINCE DES ILES','province-des-iles.geojson','NCL-1258')]:
    path=source_root+filename;raw=baseline.pinned_bytes(path);assert path in file_by_path
    assert len(raw)==file_by_path[path]['bytes'] and sha(raw)==file_by_path[path]['sha256']
    feature=json.loads(raw)['features'][0];assert feature['properties']['nom']==name
    sources[target]={'path':path,'file_sha256':sha(raw),'feature_sha256':sha(canonical_json(feature)),
        'geometry_sha256':sha(canonical_json(feature['geometry'])),'geometry':shape(feature['geometry']),
        'province_name':name}
ncl=published(OWNED+'vintages/ncl-targeted-source-match-029-001/ncl-source-matches-029.json',
    OWNED+'vintages/ncl-targeted-source-match-029-001/publication.json')
ncl_partial=[];ncl_complete=[]
for row in ncl['cases']:
    if row['disposition']!='unique-positive-area-georep-province-match':continue
    candidate=candidates[row['component_id']]
    assert candidate['component_feature_sha256']==row['candidate_feature_sha256']
    geom=shape(candidate['feature']['geometry'])
    ids=row['positive_area_target_stable_location_ids'];assert len(ids)==1
    target=ids[0];source=sources[target]
    remainder=geom.difference(source['geometry'])
    supported=geom.intersection(source['geometry'])
    # Exact operation equality is required; no threshold or snapping is used.
    assert remainder.is_empty == (supported.equals(geom))
    rec={'component_id':row['component_id'],'candidate_feature_sha256':row['candidate_feature_sha256'],
        'candidate_geometry_sha256':row['candidate_geometry_sha256'],'source_basis':'retained-generalized-NCL-GeoReP-2024',
        'target_stable_location_id':target,'source_path':source['path'],'source_file_sha256':source['file_sha256'],
        'source_feature_sha256':source['feature_sha256'],'source_geometry_sha256':source['geometry_sha256'],
        'candidate_area_degree2':geom.area,'source_intersection_area_degree2':supported.area,
        'candidate_area_covered_fraction':supported.area/geom.area if geom.area else None,
        'candidate_minus_retained_source_feature':{'is_empty':remainder.is_empty,'geometry_type':remainder.geom_type,
            'area_degree2':remainder.area,'geometry':None if remainder.is_empty else mapping(remainder)},
        'remainder_interpretation':'Geometry outside the single matching retained generalized province feature. This does not identify water, processing cause, or boundary authority.'}
    (ncl_complete if remainder.is_empty else ncl_partial).append(rec)

output={'schema':'melanesia-source-remainders-084/v1','batch_id':capture['batch_id'],
    'scope_count':363,'partial_candidate_count':len(geo_partial)+len(ncl_partial),
    'counts':{'geoBoundaries_prior-comparison_partial':len(geo_partial),
        'geoBoundaries_prior-comparison_complete':len(geo_complete),
        'NCL_positive_match_full_candidate_covered_exactly':len(ncl_complete),
        'NCL_positive_match_with_retained_source_remainder':len(ncl_partial),
        'NCL_no_positive_area_match':sum(x['disposition']=='no-positive-area-georep-province-match' for x in ncl['cases'])},
    'geoBoundaries_partial_remainders':rows,'NCL_partial_remainders':ncl_partial,
    'NCL_full_candidate_coverage':ncl_complete,
    'method':'For the 65 geoBoundaries cases, reused the exact candidate-minus-source-union geometry already retained in the admitted source-comparison row. For the 19 New Caledonia positive matches, computed candidate minus the uniquely bound retained province feature without snapping or tolerance, then preserved the exact resulting geometry.',
    'limits':['Remainder geometry records source-layer noncoverage only; it is not a water or physical-cause classification.',
        'The New Caledonia GeoReP source is generalized at maximum allowable offset 0.00005 degrees and geometry precision 6.',
        'The 26 complete geoBoundaries cases are recorded as prior exact source coverage; their geometries are not recomputed.',
        'This is source coverage evidence, not native-grid acceptance or an accepted repair.']}
script=Path(__file__).read_bytes()
execution={'status':'completed','completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'baseline_commit':COMMIT,'script_path':str(Path(__file__).relative_to(ROOT)),'script_bytes':len(script),
    'script_sha256':sha(script),'python':platform.python_version(),'shapely':__import__('shapely').__version__,
    'custody':'pinned Baseline + exclusive NewVintage','admitted_input_bytes':sum(baseline.consumed.values()),
    'elapsed_seconds':time.monotonic()-started}
values={'source-remainders-084.json':canonical_json(output),'execution.json':canonical_json(execution),
    'measure-source-remainders.py':script,
    'input-pins.json':canonical_json({'schema':'melanesia-source-remainders-run-inputs/v1','baseline_commit':COMMIT,'files':PIN_META['files']})}
NewVintage(baseline,OWNED,RUN,list(values)).publish_bytes(values)
print(json.dumps({'status':'published','counts':output['counts'],
    'partial_candidates':output['partial_candidate_count'],'admitted_input_bytes':sum(baseline.consumed.values())},sort_keys=True))
