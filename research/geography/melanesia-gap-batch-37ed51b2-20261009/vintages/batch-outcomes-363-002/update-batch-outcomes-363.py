#!/usr/bin/env python3
"""Bind exact retained-source remainders into the full 363-ID ledger."""
import datetime, hashlib, json, platform, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OWNED='research/geography/melanesia-gap-batch-37ed51b2-20261009/'
RUN='batch-outcomes-363-002'
PIN_META=json.loads((ROOT/OWNED/'batch-outcome-update-pins.json').read_text())
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
v1=published(OWNED+'vintages/batch-outcomes-363-001/batch-outcomes-363.json',OWNED+'vintages/batch-outcomes-363-001/publication.json')
remainders=published(OWNED+'vintages/source-remainders-084-001/source-remainders-084.json',OWNED+'vintages/source-remainders-084-001/publication.json')
join=published(OWNED+'vintages/source-comparison-capture-001/batch-source-comparisons.json',OWNED+'vintages/source-comparison-capture-001/publication.json')
join_by_id={x['component_id']:x for x in join['cases']}
ncl=published(OWNED+'vintages/ncl-targeted-source-match-029-001/ncl-source-matches-029.json',OWNED+'vintages/ncl-targeted-source-match-029-001/publication.json')
assert v1['candidate_count']==363 and len(v1['cases'])==363
geo_partial={x['component_id']:x for x in remainders['geoBoundaries_partial_remainders']}
geo_complete={x['component_id']:x for x in join['cases'] if x['disposition']=='native-grid-source-payload' and x['source_coverage_complete_in_prior_comparison'] is True}
ncl_partial={x['component_id']:x for x in remainders['NCL_partial_remainders']}
ncl_complete={x['component_id']:x for x in remainders['NCL_full_candidate_coverage']}
ncl_nohit={x['component_id'] for x in ncl['cases'] if x['disposition']=='no-positive-area-georep-province-match'}
assert len(geo_partial)==65 and len(geo_complete)==26 and len(ncl_partial)==4 and len(ncl_complete)==15 and len(ncl_nohit)==10
rows=[];counts={'complete-retained-source-coverage':0,'partial-retained-source-coverage-with-geometry-remainder':0,
    'no-positive-area-NCL-match':0,'other-held-source-or-land-support-status':0}
for old in v1['cases']:
    row=dict(old);cid=row['component_id']
    if cid in geo_complete:
        row['whole_candidate_source_coverage']={'status':'complete-exact-in-prior-admitted-geoBoundaries-comparison',
            'comparison_record_path':OWNED+'vintages/source-comparison-capture-001/batch-source-comparisons.json'}
        counts['complete-retained-source-coverage']+=1
    elif cid in geo_partial:
        evidence=geo_partial[cid]
        row['whole_candidate_source_coverage']={'status':'partial-in-prior-admitted-geoBoundaries-comparison',
            'remainder':evidence['candidate_minus_retained_source_union'],
            'source_comparison_status':join_by_id[cid]['source_comparison_status'],
            'remainder_interpretation':evidence['remainder_interpretation']}
        row['whole_candidate_coverage_status']='partial-in-retained-comparison; exact remainder attached'
        counts['partial-retained-source-coverage-with-geometry-remainder']+=1
    elif cid in ncl_complete:
        evidence=ncl_complete[cid]
        row['whole_candidate_source_coverage']={'status':'complete-exact-candidate-minus-source-empty',
            'source_id':'NCL-GeoReP-2024','target_stable_location_id':evidence['target_stable_location_id'],
            'candidate_area_degree2':evidence['candidate_area_degree2'],
            'source_intersection_area_degree2':evidence['source_intersection_area_degree2'],
            'candidate_area_covered_fraction':evidence['candidate_area_covered_fraction'],
            'candidate_minus_retained_source_feature':evidence['candidate_minus_retained_source_feature']}
        row['whole_candidate_coverage_status']='complete-exact-in-retained-generalized-NCL-province-source'
        counts['complete-retained-source-coverage']+=1
    elif cid in ncl_partial:
        evidence=ncl_partial[cid]
        row['whole_candidate_source_coverage']={'status':'partial-exact-candidate-minus-source-nonempty',
            'source_id':'NCL-GeoReP-2024','target_stable_location_id':evidence['target_stable_location_id'],
            'candidate_area_degree2':evidence['candidate_area_degree2'],
            'source_intersection_area_degree2':evidence['source_intersection_area_degree2'],
            'candidate_area_covered_fraction':evidence['candidate_area_covered_fraction'],
            'remainder':evidence['candidate_minus_retained_source_feature'],
            'remainder_interpretation':evidence['remainder_interpretation']}
        row['whole_candidate_coverage_status']='partial-exact-in-retained-generalized-NCL-province-source; exact remainder attached'
        counts['partial-retained-source-coverage-with-geometry-remainder']+=1
    elif cid in ncl_nohit:
        row['whole_candidate_source_coverage']={'status':'no-positive-area-match-in-retained-generalized-NCL-province-source',
            'interpretation_limit':'No match in this retained source; not evidence of no land or water.'}
        row['whole_candidate_coverage_status']='no-positive-area-NCL-source-match'
        counts['no-positive-area-NCL-match']+=1
    else:
        row['whole_candidate_source_coverage']={'status':'no-new-source-coverage-change-from-batch-outcomes-363-001'}
        counts['other-held-source-or-land-support-status']+=1
    rows.append(row)
assert len(rows)==363 and sum(counts.values())==363
assert counts['complete-retained-source-coverage']==41
assert counts['partial-retained-source-coverage-with-geometry-remainder']==69
assert counts['no-positive-area-NCL-match']==10
assert counts['other-held-source-or-land-support-status']==243
result={'schema':'melanesia-complete-batch-outcomes/v2','batch_id':v1['batch_id'],'candidate_count':363,
    'coverage_counts':counts,'source_supported_payload_count':110,
    'assignment_status':'no assignment edits; native evaluation and acceptance remain pending',
    'supersedes_coverage_fields_in':OWNED+'vintages/batch-outcomes-363-001/batch-outcomes-363.json',
    'cases':rows,'limits':['The 69 partial outcomes carry exact retained-source remainder geometries; the remainder is not labeled water or cause.',
        'The 41 complete outcomes mean source-geometry coverage only, not native-grid eligibility or accepted repair.',
        'The 10 NCL no-hit cases remain source-unmatched, not land/water classified.',
        'The other 243 outcomes retain their source/land-support hold reason from v1.',
        'No source comparison overlay is repeated for the 91 geoBoundaries cases.']}
script=Path(__file__).read_bytes()
execution={'status':'completed','completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'baseline_commit':COMMIT,'script_path':str(Path(__file__).relative_to(ROOT)),'script_bytes':len(script),
    'script_sha256':sha(script),'python':platform.python_version(),'custody':'pinned Baseline + exclusive NewVintage',
    'admitted_input_bytes':sum(baseline.consumed.values()),'elapsed_seconds':time.monotonic()-started}
values={'batch-outcomes-363-v2.json':canonical_json(result),'execution.json':canonical_json(execution),
    'update-batch-outcomes-363.py':script,
    'input-pins.json':canonical_json({'schema':'melanesia-batch-outcomes-363-v2-inputs/v1','baseline_commit':COMMIT,'files':PIN_META['files']})}
NewVintage(baseline,OWNED,RUN,list(values)).publish_bytes(values)
print(json.dumps({'status':'published','coverage_counts':counts,'admitted_input_bytes':sum(baseline.consumed.values())},sort_keys=True))
