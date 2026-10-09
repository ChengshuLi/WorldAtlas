#!/usr/bin/env python3
"""Publish one exact-ID outcome ledger for all 363 Melanesia candidates."""
import datetime, hashlib, json, platform, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OWNED='research/geography/melanesia-gap-batch-37ed51b2-20261009/'
RUN='batch-outcomes-363-001'
PIN_META=json.loads((ROOT/OWNED/'batch-outcome-pins.json').read_text())
COMMIT=PIN_META['baseline_commit'];helper='scripts/evidence/immutable.py'
helper_raw=subprocess.check_output(['git','-C',str(ROOT),'show',COMMIT+':'+helper])
ns={'__name__':'pinned_evidence','__file__':str(ROOT/helper)}
exec(compile(helper_raw,str(ROOT/helper),'exec'),ns)
Baseline,NewVintage,canonical_json=ns['Baseline'],ns['NewVintage'],ns['canonical_json']
baseline=Baseline(ROOT,COMMIT,PIN_META['files']);started=time.monotonic()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(baseline.pinned_bytes(path))
def published(path,receipt_path):
 raw=baseline.pinned_bytes(path);receipt=load(receipt_path)
 matches=[x for x in receipt['outputs']if x['path']==path]
 assert receipt['status']=='complete'and len(matches)==1
 assert matches[0]['bytes']==len(raw)and matches[0]['sha256']==sha(raw)
 return json.loads(raw)

scope=load(OWNED+'inputs/assignment-scope.json')['batch']
capture_path=OWNED+'vintages/candidate-capture-001/candidate-capture.json'
capture=published(capture_path,OWNED+'vintages/candidate-capture-001/publication.json')
assert scope['batch_id']==capture['batch_id']and scope['component_count']==363
scope_ids=scope['complete_component_ids'];assert len(scope_ids)==363 and len(set(scope_ids))==363
captured=capture['candidate_records'];candidate_by_id={x['component_id']:x for x in captured}
assert len(candidate_by_id)==363 and set(candidate_by_id)==set(scope_ids)
join=published(OWNED+'vintages/source-comparison-capture-001/batch-source-comparisons.json',
    OWNED+'vintages/source-comparison-capture-001/publication.json')
join_by_id={x['component_id']:x for x in join['cases']};assert len(join_by_id)==363 and set(join_by_id)==set(scope_ids)
ncl=published(OWNED+'vintages/ncl-targeted-source-match-029-001/ncl-source-matches-029.json',
    OWNED+'vintages/ncl-targeted-source-match-029-001/publication.json')
ncl_by_id={x['component_id']:x for x in ncl['cases']};assert len(ncl_by_id)==29
payload=published(OWNED+'vintages/native-payloads-110-001/native-payloads-110.json',
    OWNED+'vintages/native-payloads-110-001/publication.json')
payload_by_id={x['component_id']:x for x in payload['additive_payloads']};assert len(payload_by_id)==110

rows=[];counts={};native_status_counts={}
for cid in scope_ids:
    candidate=candidate_by_id[cid];joined=join_by_id[cid]
    assert candidate['component_feature_sha256']==joined['candidate_feature_sha256']
    assert candidate['component_geometry_sha256']==joined['candidate_geometry_sha256']
    outcome={'component_id':cid,'candidate_feature_sha256':candidate['component_feature_sha256'],
        'candidate_geometry_sha256':candidate['component_geometry_sha256'],
        'candidate_feature':candidate['feature'],'catalog_prior_physical_support':joined['prior_physical_support'],
        'catalog_prior_pipeline_state':joined['prior_pipeline_state'],
        'catalog_prior_next_prerequisite':joined['original_next_prerequisite'],
        'prior_comparison_status':joined['source_comparison_status'],
        'source_comparison_record_path':OWNED+'vintages/source-comparison-capture-001/batch-source-comparisons.json',
        'source_comparison_record_component_id':cid,
        'native_grid_status':'not-evaluated-for-acceptance',
        'assignment_edit_status':'no-existing-or-candidate-assignment-modified'}
    if cid in payload_by_id:
        proposal=payload_by_id[cid]
        assert proposal['candidate_feature_sha256']==candidate['component_feature_sha256']
        outcome.update({'outcome':'source-supported-additive-payload-prepared',
            'source_supported_fragment_count':len(proposal['source_supported_intersection_fragments']),
            'target_stable_location_id':proposal['target_stable_location_id'],
            'target_current_feature':proposal['target_current_feature'],
            'source_evidence_kind':proposal['source_evidence_kind'],
            'source_supported_intersection_fragments':proposal['source_supported_intersection_fragments'],
            'proposed_payload_path':OWNED+'vintages/native-payloads-110-001/native-payloads-110.json',
            'whole_candidate_coverage_status':('complete-in-retained-comparison' if proposal.get('prior_comparison_source_coverage_complete') is True else
                'partial-in-retained-comparison' if proposal.get('prior_comparison_source_coverage_complete') is False else
                'candidate-source-covered-fraction-recorded; remainder-not-recomputed'),
            'unsupported_candidate_remainder_included':False})
        class_key=outcome['outcome']+':'+outcome['whole_candidate_coverage_status']
    elif joined['disposition']=='targeted-source-match-needed':
        result=ncl_by_id[cid]
        if result['disposition']=='no-positive-area-georep-province-match':
            key='held-no-positive-area-match-in-retained-georep-province-product'
            outcome.update({'outcome':key,'source_match_status':result['disposition'],
                'source_product_id':'NCL-GeoReP-2024','source_query_result':'no positive-area intersection',
                'interpretation_limit':'No match in this retained generalized province source; not evidence of no land or water.'})
        else:raise ValueError('Unexpected unprepared NCL result '+cid)
        class_key=key
    else:
        disposition=joined['disposition']
        if disposition=='ambiguous-multiple-recorded-subjects':
            key='held-multiple-recorded-source-subjects'
            outcome.update({'outcome':key,'source_subject_ids':joined['positive_area_recorded_source_subject_ids'],
                'positive_area_source_feature_intersections':joined['positive_area_source_feature_intersections']})
        elif disposition=='no-positive-area-recorded-source-subject':
            key='held-no-positive-area-recorded-source-subject'
            outcome.update({'outcome':key,'source_comparison_status':joined['source_comparison_status'],
                'source_feature_intersections':joined['positive_area_source_feature_intersections']})
        elif disposition=='retained-routing-only-not-land-supported':
            key='held-no-land-supported-candidate-basis'
            outcome.update({'outcome':key,'source_comparison_status':joined['source_comparison_status'],
                'source_product_codes':joined.get('source_product_codes',[]),
                'physical_support_status':joined['prior_physical_support']})
        elif disposition=='not-in-retained-source-comparison-cohort':
            key='held-not-land-supported-and-outside-retained-comparison-cohort'
            outcome.update({'outcome':key,'source_comparison_status':joined['source_comparison_status'],
                'physical_support_status':joined['prior_physical_support'],
                'interpretation_limit':'Comparison cohort absence is not a negative source overlay.'})
        else:raise ValueError('Unclassified source comparison disposition '+disposition)
        class_key=key
    counts[class_key]=counts.get(class_key,0)+1
    native_status_counts[outcome['native_grid_status']]=native_status_counts.get(outcome['native_grid_status'],0)+1
    rows.append(outcome)
assert len(rows)==363 and len({x['component_id']for x in rows})==363
assert sum(counts.values())==363
assert sum(v for k,v in counts.items() if k.startswith('source-supported-additive-payload-prepared'))==110
assert sum(v for k,v in counts.items() if k.startswith('held-'))==253

result={'schema':'melanesia-complete-batch-outcomes/v1','batch_id':capture['batch_id'],
    'scope_source_path':OWNED+'inputs/assignment-scope.json','candidate_count':len(rows),
    'outcome_counts':counts,'native_grid_status_counts':native_status_counts,
    'source_supported_payload_count':110,'held_or_not-currently-source-supported_count':253,
    'source_supported_candidate_payload_path':OWNED+'vintages/native-payloads-110-001/native-payloads-110.json',
    'source_comparison_capture_path':OWNED+'vintages/source-comparison-capture-001/batch-source-comparisons.json',
    'candidate_capture_path':capture_path,'cases':rows,
    'limits':['This ledger accounts for all 363 IDs using the pinned prior catalog/comparison capture plus targeted retained New Caledonia source evidence.',
        'The 91 geoBoundaries source comparisons are reused; no source overlay or union was repeated.',
        'The 19 New Caledonia matches are source-relative to the retained generalized GeoReP-2024 province layer.',
        'Source-supported fragments are not accepted repairs. Native-grid evaluation, unowned-cell proof, full assignment conservation, and source-supported remainder resolution remain open.',
        'No historical physical cause, water status, current legal boundary, or boundary authority is inferred.']}
script=Path(__file__).read_bytes()
execution={'status':'completed','completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'baseline_commit':COMMIT,'script_path':str(Path(__file__).relative_to(ROOT)),
    'script_bytes':len(script),'script_sha256':sha(script),'python':platform.python_version(),
    'custody':'pinned Baseline + exclusive NewVintage','admitted_input_bytes':sum(baseline.consumed.values()),
    'elapsed_seconds':time.monotonic()-started}
values={'batch-outcomes-363.json':canonical_json(result),'execution.json':canonical_json(execution),
    'prepare-batch-outcomes-363.py':script,
    'input-pins.json':canonical_json({'schema':'melanesia-batch-outcomes-363-run-inputs/v1','baseline_commit':COMMIT,'files':PIN_META['files']})}
NewVintage(baseline,OWNED,RUN,list(values)).publish_bytes(values)
print(json.dumps({'status':'published','cases':len(rows),'outcomes':counts,
    'admitted_input_bytes':sum(baseline.consumed.values())},sort_keys=True))
