#!/usr/bin/env python3
"""Read-only, pinned Temotu scope reproduction for issue #913."""
import argparse
import gzip
import json
from pathlib import Path
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]
sys.path.insert(0, str(REPO / 'scripts'))
from evidence.immutable import Baseline, NewVintage, canonical_json

SUBJECT = 'gb:SLB:ADM1:17018030B19935783635883'
AREA = 'framework:area:santa-cruz-is:a2bb7bce4e86'
PROVINCE = 'framework:province:temotu:c9f46b66cd8a'
OWNED = 'data/regional-review/temotu-santa-cruz-parent-scope-20261005/'
ISSUE_PINS = {
    'world_index': 'a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03',
    'source_registry': 'ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633',
    'geography_part_22': 'f7ac47c8a9012651773264a31bfd6b360394ad029dd1f9cf88d63150953070d3',
    'macro_publication_v5': 'aae3967fde4f5bf92b3cb0b42c490c6c6a5921c7421dcdc9533f242afbd6a674',
}


def relationship_disposition(*, area_extent_defined, direct_membership_demonstrated, historical_alias_only):
    """An admin name or province extent cannot supply an undefined Atlas-area membership."""
    if historical_alias_only or not area_extent_defined or not direct_membership_demonstrated:
        return 'unresolved'
    return 'candidate-for-independent-review'


def reproduce():
    baseline_path = PACKET / 'baseline-inputs.json'
    request = json.loads(baseline_path.read_text())
    baseline_data = request['baseline']
    baseline = Baseline(REPO, baseline_data['commit'], baseline_data['files'])
    if request['subject_ids'] != [SUBJECT]:
        raise ValueError('Candidate scope differs from issue 913 exact subject')
    for key, digest in ISSUE_PINS.items():
        if baseline_data['pins'].get(key) != digest:
            raise ValueError('Issue-declared pin mismatch: ' + key)
    for key, path in baseline_data['pin_files'].items():
        if baseline.pins[path]['sha256'] != baseline_data['pins'][key]:
            raise ValueError('Baseline pin/file binding mismatch: ' + key)

    # Authenticate the helper and validator bytes that are actually materialized and run.
    for name in ('scripts/evidence/immutable.py', 'scripts/evidence-quality.mjs'):
        baseline.materialized_bytes(name)

    features, containing = baseline.subjects([SUBJECT])
    subject = features[SUBJECT]
    if (subject.get('id') or subject.get('properties', {}).get('id')) != SUBJECT:
        raise ValueError('Issue subject does not resolve to its native ID')
    props = subject['properties']
    if props.get('name') != 'Temotu' or props.get('parent_id') != PROVINCE:
        raise ValueError('Current feature identity/administrative parent changed')
    metadata = props.get('metadata', {})
    if metadata.get('source_id') != 'gb:SLB:ADM1' or metadata.get('source_role') != 'Province':
        raise ValueError('Current feature no longer declares the reviewed ADM1/Province role')
    if metadata.get('geographic_area_code') != 'SCZ':
        raise ValueError('Current area code differs from the reviewed subject')

    # Negative exact-scope control: a non-existent extra subject must fail closed.
    decoy = SUBJECT + '-outside-reviewed-scope'
    try:
        baseline.subjects([SUBJECT, decoy])
    except ValueError as error:
        if 'absent from immutable index' not in str(error):
            raise
        negative_scope = {'id': 'out-of-scope-decoy', 'status': 'pass', 'rejected_id': decoy,
                          'observed': str(error)}
    else:
        raise AssertionError('Negative scope control unexpectedly accepted an absent ID')

    source_name = 'data/regional-review/regional-review-1aa97b490604ea4e/sources/solomon-islands-natural-earth-adm1.geojson'
    source_bytes = baseline.pinned_bytes(source_name)
    source = json.loads(source_bytes)
    source_features = source.get('features', [])
    source_ids = []
    target_source = []
    for row in source_features:
        p = row.get('properties', {})
        native_id = 'gb:' + p.get('shapeGroup', '') + ':' + p.get('shapeType', '') + ':' + p.get('shapeID', '')
        source_ids.append(native_id)
        if native_id == SUBJECT:
            target_source.append(row)
    if len(source_features) != 10 or len(set(source_ids)) != 10 or len(target_source) != 1:
        raise ValueError('Retained natural-earth reference roster/identity is incomplete or duplicated')
    if target_source[0].get('properties', {}).get('shapeName') != 'Temotu':
        raise ValueError('Retained source native identity no longer maps to Temotu')
    names = sorted(row.get('properties', {}).get('shapeName', '') for row in source_features)
    if 'Capital Territory (Honiara)' not in names:
        raise ValueError('Neighbor-scale control no longer finds Honiara capital territory')

    registry = json.loads(baseline.pinned_bytes('data/administrative-sources.json'))
    admin_row = registry['gb:SLB:ADM1']
    if (admin_row.get('boundaryYearRepresented') != '2021' or
            admin_row.get('boundarySource') != 'Natural Earth' or
            admin_row.get('boundaryLicense') != 'Public Domain' or
            admin_row.get('admUnitCount') != '10'):
        raise ValueError('Administrative source vintage/license/count differs from reviewed baseline')

    membership_bytes = baseline.pinned_bytes('data/macro-foundation/current-membership-inventory.json.gz')
    membership = json.loads(gzip.decompress(membership_bytes))
    area_rows = [row for row in membership if row.get('id') == AREA]
    province_rows = [row for row in membership if row.get('id') == PROVINCE]
    if len(area_rows) != 1 or len(province_rows) != 1:
        raise ValueError('Current area/province membership rows are missing or duplicated')
    area, province = area_rows[0], province_rows[0]
    if (area.get('level') != 'area' or province.get('level') != 'province' or
            province.get('parent_id') != AREA or province.get('member_location_ids') != [SUBJECT] or
            area.get('member_location_ids') != [SUBJECT]):
        raise ValueError('Current membership ledger differs from exact reviewed scope')

    # Source-based non-inference controls: neither a historical alias alone nor
    # a province-boundary source without an Atlas-area perimeter resolves the edge.
    alias_control = relationship_disposition(area_extent_defined=False,
        direct_membership_demonstrated=False, historical_alias_only=True)
    admin_extent_control = relationship_disposition(area_extent_defined=False,
        direct_membership_demonstrated=False, historical_alias_only=False)
    if alias_control != 'unresolved' or admin_extent_control != 'unresolved':
        raise AssertionError('Historical-name/admin-boundary control inferred an Atlas area relationship')

    actual_feature_file = containing[SUBJECT]
    expected_part = 'data/geography/part-22.json'
    if actual_feature_file['path'] != expected_part or actual_feature_file['sha256'] != ISSUE_PINS['geography_part_22']:
        raise ValueError('World-index scan found a different containing file or part-22 pin')
    return {
        'version': 1,
        'issue': 913,
        'baseline_commit': baseline.commit,
        'subject': {'id': SUBJECT, 'name': props['name'], 'source_id': metadata['source_id'],
                    'source_role': metadata['source_role'], 'geometry_type': subject.get('geometry', {}).get('type'),
                    'containing_file': actual_feature_file},
        'issue_pins': ISSUE_PINS,
        'area_membership': {'area_id': AREA, 'province_id': PROVINCE,
                            'area_members': area['member_location_ids'],
                            'province_members': province['member_location_ids'],
                            'current_area_code': metadata.get('geographic_area_code'),
                            'recorded_area_overlap': metadata.get('geographic_overlap'),
                            'recorded_admin_hierarchy_overlap': metadata.get('hierarchy_overlap'),
                            'interpretation': 'Current assignment and screen values only; neither is semantic or legal proof.'},
        'administrative_source': {'source_id': 'gb:SLB:ADM1', 'vintage': admin_row['boundaryYearRepresented'],
                                  'source': admin_row['boundarySource'], 'license': admin_row['boundaryLicense'],
                                  'feature_count': int(admin_row['admUnitCount']),
                                  'feature_names': names,
                                  'neighbor_control': 'Ten Natural Earth-derived ADM1 features include nine province-named units and Capital Territory (Honiara).'},
        'positive_controls': [
            {'id': 'exact-subject-and-source-identity', 'status': 'pass',
             'observed': 'Exact Atlas subject and retained source native shapeID both resolve to Temotu.'},
            {'id': 'exact-current-membership-chain', 'status': 'pass',
             'observed': 'The current release ledger contains one Temotu province row and one Santa Cruz area row, both listing the exact issue location.'}
        ],
        'negative_controls': [negative_scope,
            {'id': 'historical-name-only', 'status': 'pass', 'disposition': alias_control,
             'observed': 'A former provincial name alone leaves the Atlas parent relation unresolved.'},
            {'id': 'province-boundary-without-area-scope', 'status': 'pass', 'disposition': admin_extent_control,
             'observed': 'An administrative province boundary without a sourced Atlas-area extent leaves the parent relation unresolved.'}
        ],
        'classification': 'unresolved; insufficient evidence for whole-province reparent',
        'limits': ['No legal province polygon or complete island-level administrative roster was validated.',
                   'No authoritative source defines the Atlas Santa Cruz Islands area perimeter.',
                   'Identity, ledger, source-count and negative-scope checks do not prove geographic correctness.']
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write', action='store_true', help='publish one fresh result through NewVintage')
    group.add_argument('--check', action='store_true', help='recompute and compare an existing result')
    parser.add_argument('--vintage', required=True)
    args = parser.parse_args()
    result = reproduce()
    if args.write:
        request = json.loads((PACKET / 'baseline-inputs.json').read_text())
        baseline = Baseline(REPO, request['baseline']['commit'], request['baseline']['files'])
        destination = NewVintage(baseline, OWNED, args.vintage, ['reproduction.json'])
        record = destination.publish({'reproduction.json': result})[0]
        print(json.dumps({'status': 'written', **record}, sort_keys=True))
        return
    path = PACKET / 'vintages' / args.vintage / 'reproduction.json'
    if not path.is_file() or path.is_symlink() or path.read_bytes() != canonical_json(result):
        raise SystemExit('Reproduced result differs from immutable saved vintage')
    print(json.dumps({'status': 'reproduced-exactly', 'path': str(path.relative_to(REPO)),
                      'sha256': __import__('hashlib').sha256(path.read_bytes()).hexdigest()}, sort_keys=True))


if __name__ == '__main__':
    main()
