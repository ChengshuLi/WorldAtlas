#!/usr/bin/env python3
"""Assemble unique, source-supported additive payloads for one Melanesia batch."""
import datetime, hashlib, json, platform, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = 'research/geography/melanesia-gap-batch-37ed51b2-20261009/'
RUN = 'native-payloads-110-001'
PIN_META = json.loads((ROOT / OWNED / 'native-payload-pins.json').read_text())
COMMIT = PIN_META['baseline_commit']
helper = 'scripts/evidence/immutable.py'
helper_raw = subprocess.check_output(['git','-C',str(ROOT),'show',COMMIT+':'+helper])
ns={'__name__':'pinned_evidence','__file__':str(ROOT/helper)}
exec(compile(helper_raw,str(ROOT/helper),'exec'),ns)
Baseline,NewVintage,canonical_json=ns['Baseline'],ns['NewVintage'],ns['canonical_json']
baseline=Baseline(ROOT,COMMIT,PIN_META['files'])
started=time.monotonic()

def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(baseline.pinned_bytes(path))
def published_payload(path,receipt_path):
    raw=baseline.pinned_bytes(path); receipt=load(receipt_path)
    matches=[x for x in receipt['outputs'] if x['path']==path]
    assert receipt['status']=='complete' and len(matches)==1
    assert matches[0]['bytes']==len(raw) and matches[0]['sha256']==sha(raw)
    return json.loads(raw)

capture_path='research/geography/melanesia-gap-batch-37ed51b2-20261009/vintages/candidate-capture-001/candidate-capture.json'
capture=published_payload(capture_path,'research/geography/melanesia-gap-batch-37ed51b2-20261009/vintages/candidate-capture-001/publication.json')
candidate_by_id={x['component_id']:x for x in capture['candidate_records']}
assert len(candidate_by_id)==363
join_path='research/geography/melanesia-gap-batch-37ed51b2-20261009/vintages/source-comparison-capture-001/batch-source-comparisons.json'
join=published_payload(join_path,'research/geography/melanesia-gap-batch-37ed51b2-20261009/vintages/source-comparison-capture-001/publication.json')
assert join['candidate_count']==363
source_map={x['component_id']:x for x in join['cases']}
assert len(source_map)==363

# Reuse the previous admitted comparison output as-is. This script deliberately
# does not re-run any source overlay or source union operation.
source_cases=[x for x in join['cases'] if x['disposition']=='native-grid-source-payload']
assert len(source_cases)==91
parts={}
for path in [x['path'] for x in PIN_META['files'] if x['path'].startswith('data/geography/part-')]:
    parts[path]={}
    for feat in load(path)['features']:
        parts[path].setdefault(feat['id'],[]).append(feat)
target_rows={}
payloads=[]
for row in source_cases:
    cid=row['component_id']; captured=candidate_by_id[cid]
    assert row['candidate_feature_sha256']==captured['component_feature_sha256']
    assert row['candidate_geometry_sha256']==captured['component_geometry_sha256']
    assert captured['feature']['properties']['administrative_assignment'] is None
    ids=row['positive_area_recorded_source_subject_ids']
    assert len(ids)==1
    target_id=ids[0]
    matches=[(path,fs[target_id][0]) for path,fs in parts.items() if target_id in fs and len(fs[target_id])==1]
    match_count=sum(len(fs.get(target_id,[])) for fs in parts.values())
    assert len(matches)==1 and match_count==1, (cid,target_id,match_count)
    path,target=matches[0]
    assert target.get('id')==target_id
    meta=target.get('properties',{}).get('metadata',{})
    assert not meta.get('source_id') or target_id.startswith(meta['source_id']+':')
    assert not meta.get('original_id') or target_id.split(':')[-1]==meta['original_id']
    target_rows[target_id]={'path':path,'feature_sha256':sha(canonical_json(target)),
        'geometry_sha256':sha(canonical_json(target['geometry'])),'name':target.get('properties',{}).get('name'),
        'parent_id':target.get('properties',{}).get('parent_id'),
        'recorded_source_id':meta.get('source_id'),'recorded_original_id':meta.get('original_id')}
    fragments=[]
    observed=set()
    for hit in row['positive_area_source_feature_intersections']:
        if hit['positive_area_deg2']<=0:continue
        recorded=hit['recorded_stable_subjects']
        assert recorded and {x['id'] for x in recorded}=={target_id}
        observed.add(hit['source_id'])
        fragments.append({'source_id':hit['source_id'],'source_feature_index':hit['feature_index'],
            'shapeID':hit['shapeID'],'source_feature_sha256':hit['feature_sha256'],
            'source_geometry_sha256':hit['geometry_sha256'],'positive_area_degree2':hit['positive_area_deg2'],
            'intersection_geometry':hit['intersection_geometry'],'recorded_stable_subjects':recorded})
    assert fragments
    payloads.append({'component_id':cid,'candidate_feature_sha256':captured['component_feature_sha256'],
        'candidate_geometry_sha256':captured['component_geometry_sha256'],
        'candidate_feature':captured['feature'],'source_evidence_kind':'retained-exact-consumed-simplified-product-comparison',
        'source_comparison_status':row['source_comparison_status'],
        'prior_comparison_source_coverage_complete':row['source_coverage_complete_in_prior_comparison'],
        'source_product_codes':sorted(observed),'target_stable_location_id':target_id,
        'target_current_feature':target_rows[target_id],
        'source_supported_intersection_fragments':fragments,
        'unsupported_candidate_remainder_included':False,
        'proposed_change':{'operation':'add-source-supported-fragment-to-existing-stable-location',
            'administrative_assignment_before':None,'administrative_assignment_proposed':target_id,
            'existing_assignments_modified':False}})

ncl_path='research/geography/melanesia-gap-batch-37ed51b2-20261009/vintages/ncl-targeted-source-match-029-001/ncl-source-matches-029.json'
ncl=published_payload(ncl_path,'research/geography/melanesia-gap-batch-37ed51b2-20261009/vintages/ncl-targeted-source-match-029-001/publication.json')
assert ncl['target_count']==29
ncl_supported=[]
for row in ncl['cases']:
    if row['disposition']!='unique-positive-area-georep-province-match':continue
    cid=row['component_id'];captured=candidate_by_id[cid]
    assert row['candidate_feature_sha256']==captured['component_feature_sha256']
    assert row['candidate_geometry_sha256']==captured['component_geometry_sha256']
    assert captured['feature']['properties']['administrative_assignment'] is None
    hits=[x for x in row['province_intersections'] if x['intersection_dimension']=='area']
    ids=sorted({x['target_stable_location_id'] for x in hits})
    assert len(ids)==1 and set(ids)==set(row['positive_area_target_stable_location_ids'])
    target_id=ids[0]
    matches=[fs[target_id][0] for fs in parts.values() if target_id in fs and len(fs[target_id])==1]
    match_count=sum(len(fs.get(target_id,[])) for fs in parts.values())
    assert len(matches)==1 and match_count==1
    target=matches[0]
    current_info=hits[0]
    assert current_info['current_location_feature_sha256']==sha(canonical_json(target))
    assert current_info['current_location_geometry_sha256']==sha(canonical_json(target['geometry']))
    target_rows[target_id]={'path':'data/geography/part-28.json',
        'feature_sha256':sha(canonical_json(target)),'geometry_sha256':sha(canonical_json(target['geometry'])),
        'name':target.get('properties',{}).get('name'),'parent_id':target.get('properties',{}).get('parent_id'),
        'recorded_source_id':None,'recorded_original_id':None}
    fragments=[{'source_id':'NCL-GeoReP-2024','source_path':x['source_path'],
        'source_file_sha256':x['source_file_sha256'],'source_feature_id':x['source_feature_id'],
        'source_feature_sha256':x['source_feature_sha256'],'source_geometry_sha256':x['source_geometry_sha256'],
        'positive_area_degree2':x['intersection_area_degree2'],'intersection_geometry':x['intersection_geometry'],
        'candidate_area_covered_fraction':x['candidate_area_covered_fraction']} for x in hits]
    ncl_supported.append({'component_id':cid,'candidate_feature_sha256':captured['component_feature_sha256'],
        'candidate_geometry_sha256':captured['component_geometry_sha256'],'candidate_feature':captured['feature'],
        'source_evidence_kind':'retained-generalized-New-Caledonia-GeoReP-2024-province-layer',
        'source_product_codes':['NCL-GeoReP-2024'],'target_stable_location_id':target_id,
        'target_current_feature':target_rows[target_id],'source_supported_intersection_fragments':fragments,
        'unsupported_candidate_remainder_included':False,
        'proposed_change':{'operation':'add-source-supported-fragment-to-existing-stable-location',
            'administrative_assignment_before':None,'administrative_assignment_proposed':target_id,
            'existing_assignments_modified':False}})

all_proposals=payloads+ncl_supported
assert len(payloads)==91 and len(ncl_supported)==19 and len(all_proposals)==110
proposal_ids=[x['component_id'] for x in all_proposals]
assert len(proposal_ids)==len(set(proposal_ids))
assert set(proposal_ids).isdisjoint({x['component_id'] for x in source_cases if x['component_id'] in {r['component_id'] for r in ncl_supported}})
excluded_counts={}
for row in join['cases']:
    cid=row['component_id']
    if cid in set(proposal_ids):continue
    outcome=row['disposition']
    if outcome=='targeted-source-match-needed':
        ncl_row=next(x for x in ncl['cases'] if x['component_id']==cid)
        outcome='NCL-no-positive-area-match' if ncl_row['disposition']=='no-positive-area-georep-province-match' else ncl_row['disposition']
    excluded_counts[outcome]=excluded_counts.get(outcome,0)+1
assert sum(excluded_counts.values())==253

output={'schema':'melanesia-whole-batch-native-payloads/v1','batch_id':capture['batch_id'],
    'batch_candidate_count':363,'source_supported_candidate_payload_count':len(all_proposals),
    'source_payload_counts':{'retained-geoBoundaries-consumed-simplified-products':len(payloads),
        'retained-generalized-New-Caledonia-GeoReP-2024':len(ncl_supported)},
    'excluded_candidate_counts':excluded_counts,'unique_existing_target_count':len(target_rows),
    'existing_target_locations':[{'id':identity,**target_rows[identity]} for identity in sorted(target_rows)],
    'additive_payloads':all_proposals,
    'conservation':{'all_363_original_candidate_features_retained_in_candidate-capture-001':True,
        'all_110_candidate_administrative_assignment_values_before_are_null':True,
        'all_proposed_geometries_are_source-intersection-fragments-only':True,
        'unsupported_candidate_remainders_added':False,'existing_location_assignments_changed':False,
        'native_grid_unowned_cell_check':'required before acceptance; not performed in this evidence preparation',
        'preexisting_native_grid_assignments':'must remain byte-for-byte/owner-for-owner unchanged when accepted payload is applied'},
    'source_coverage':{'91_existing-comparison-cases':{'complete':sum(x['source_coverage_complete_in_prior_comparison'] is True for x in source_cases),
        'partial':sum(x['source_coverage_complete_in_prior_comparison'] is False for x in source_cases)},
        '19_NCL_matches':'positive-area unique source-relative province match; source coverage fraction and current target relation preserved in fragments'},
    'method':'Reuse admitted source-comparison intersection geometry for the 91 geoBoundaries cases; do not rerun source overlays. Reuse the admitted targeted GeoReP-2024 candidate intersections for the 19 New Caledonia cases. Resolve every target against a unique exact current geography feature ID and pin the current feature file/hash. Propose only additive assignment of source-supported fragments.',
    'limits':['The 65 partial geoBoundaries cases include only positive-area source intersections; unsupported original candidate remainder is excluded.',
        'GeoReP New Caledonia source is generalized at maxAllowableOffset=0.00005 degrees and geometryPrecision=6, not the full-resolution database.',
        'Source-relative matches establish no present legal boundary, effective date, historical process cause, or boundary authority.',
        'This packet prepares geometry/target payloads; it does not execute assignment edits or native-grid ownership checks.',
        'Unmatched, multi-subject and non-land-supported cases remain explicitly excluded rather than forced into a target.']}
script=Path(__file__).read_bytes()
execution={'status':'completed','completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'baseline_commit':COMMIT,'script_path':str(Path(__file__).relative_to(ROOT)),
    'script_bytes':len(script),'script_sha256':sha(script),'python':platform.python_version(),
    'custody':'pinned Baseline + exclusive NewVintage','admitted_input_bytes':sum(baseline.consumed.values()),
    'elapsed_seconds':time.monotonic()-started}
values={'native-payloads-110.json':canonical_json(output),'execution.json':canonical_json(execution),
    'prepare-native-payload-110.py':script,
    'input-pins.json':canonical_json({'schema':'melanesia-native-payload-110-run-inputs/v1','baseline_commit':COMMIT,'files':PIN_META['files']})}
NewVintage(baseline,OWNED,RUN,list(values)).publish_bytes(values)
print(json.dumps({'status':'published','proposals':len(all_proposals),'excluded':excluded_counts,
    'target_locations':len(target_rows),'admitted_input_bytes':sum(baseline.consumed.values())},sort_keys=True))
