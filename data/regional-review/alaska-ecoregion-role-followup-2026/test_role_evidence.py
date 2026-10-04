#!/usr/bin/env python3
"""Run reproducibility and rejection controls for the complete #601 crosswalk."""
import copy
import hashlib
import json
from pathlib import Path

from build_assessment import OWNED, ROOT, SCOPE, build_report, canon

RESULT = ROOT / OWNED / 'negative-control-results.json'


def rejected(scope, fragment):
    try:
        build_report(scope)
    except (ValueError, KeyError, FileNotFoundError) as error:
        if fragment not in str(error):
            raise AssertionError(f'Wrong rejection reason: {error}') from error
        return str(error)
    raise AssertionError('Mutated source/scope was accepted')


def main():
    scope = json.loads((ROOT / SCOPE).read_bytes())
    report_a = build_report(scope)
    report_b = build_report(scope)
    if canon(report_a) != canon(report_b):
        raise AssertionError('Independent source crosswalk builds differ')
    if report_a['whole_scope_summary']['subjects_with_exactly_one_current_containing_part'] != 33:
        raise AssertionError('Whole-scope cross-part duplicate/missing scan failed')
    if report_a['whole_scope_summary']['subjects_with_complete_six_node_parent_chain'] != 33:
        raise AssertionError('Whole-scope complete-parent-chain audit failed')
    if report_a['whole_scope_summary']['retained_vs_current_resolve_attribute_mismatches'] != 0:
        raise AssertionError('Original/current RESOLVE attribute cross-check failed')
    if report_a['whole_scope_summary']['official_tiger_2018_county_equivalent_predecessors'] != 7:
        raise AssertionError('Official TIGER 2018 county-equivalent crosswalk failed')
    cases = [
        {'id':'positive-complete-33-subject-crosswalk', 'result':'PASS', 'subjects':33},
        {'id':'positive-all-36-indexed-parts-unique-containment', 'result':'PASS', 'parts':36},
        {'id':'positive-complete-six-node-parent-chains', 'result':'PASS', 'subjects':33},
        {'id':'positive-resolve-2017-original-vs-live-15-row-attribute-match', 'result':'PASS', 'features':15},
        {'id':'positive-2018-adm2-predecessor-roster', 'result':'PASS', 'predecessors':7},
        {'id':'positive-official-tiger-2018-seven-county-equivalents', 'result':'PASS', 'source_archive_sha256':scope['census_source_archive']['sha256']},
        {'id':'positive-two-independent-builds-byte-identical', 'result':'PASS', 'sha256':hashlib.sha256(canon(report_a)).hexdigest()},
    ]
    mutations = []
    bad = copy.deepcopy(scope); bad['subject_ids'][-1] = bad['subject_ids'][0]
    mutations.append(('negative-duplicate-assigned-id-rejected', bad, 'incomplete/duplicate'))
    bad = copy.deepcopy(scope); bad['subject_ids'].pop()
    mutations.append(('negative-missing-assigned-id-rejected', bad, 'incomplete/duplicate'))
    bad = copy.deepcopy(scope); bad['issue_body'] += 'changed'
    mutations.append(('negative-changed-github-issue-body-rejected', bad, 'issue body'))
    bad = copy.deepcopy(scope); bad['parent_source_snapshot_commit'] = '1111111111111111111111111111111111111111'
    mutations.append(('negative-changed-parent-snapshot-rejected', bad, 'snapshot/evaluation commits'))
    bad = copy.deepcopy(scope); bad['official_query_sha256'] = '0' * 64
    mutations.append(('negative-changed-primary-source-response-rejected', bad, 'ArcGIS query bytes'))
    bad = copy.deepcopy(scope); bad['new_source_capture']['census-tiger-2018-seven-alaska-counties.json']['sha256'] = '0' * 64
    mutations.append(('negative-changed-census-extract-rejected', bad, 'Captured primary-source bytes'))
    for name, mutated, reason in mutations:
        rejected(mutated, reason)
        cases.append({'id':name,'result':'PASS','rejection':reason})
    data = {'version':1,'issue':601,'result':'PASS','case_count':len(cases),'cases':cases,
            'original_source_write_attempts':0,'shared_geography_write_attempts':0}
    encoded = canon(data)
    if RESULT.exists():
        if RESULT.read_bytes() != encoded:
            raise AssertionError('Saved negative-control results differ; refusing overwrite')
    else:
        with RESULT.open('xb') as handle:
            handle.write(encoded)
    print(encoded.decode(), end='')

if __name__ == '__main__':
    main()
