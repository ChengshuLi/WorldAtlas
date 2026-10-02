"""Prepare exact-guard metadata patches; do not mutate any atlas product."""
import argparse
import gzip
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(path):
    with gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path) as stream:
        return json.load(stream)


def geometry_hash(geometry):
    return hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_against_current(plan, features, units):
    """Preflight the entire plan before a caller performs metadata mutations."""
    current = {f['properties']['id']: f for f in features if f['properties']['reference_owner'] == 'Namibia'}
    patches = {r['id']: r for r in plan['feature_annotations']}
    assert len(patches) == len(plan['feature_annotations']) == len(current) == 111
    assert set(patches) == set(current), 'Incomplete country annotation set'
    groups = {u['id']: u for u in units}
    descendants = {}
    for identifier, row in patches.items():
        f, expected = current[identifier], row['expected']
        p = f['properties']
        actual = {'name': p['name'], 'parent_id': p['parent_id'],
                  'source_id': p['metadata']['source_id'], 'reference_year': str(p['metadata']['reference_year']),
                  'source_member_ids': p['metadata'].get('source_member_ids', []),
                  'geometry_sha256': geometry_hash(f['geometry'])}
        assert actual == expected, f'Location annotation guard mismatch: {identifier}'
        assert set(row['metadata_patch']) == {'source_quality_review'}, 'Unapproved mutation field'
        parent, seen = p['parent_id'], set()
        while parent:
            assert parent not in seen and parent in groups, 'Broken parent chain'
            seen.add(parent)
            descendants.setdefault(parent, []).append(identifier)
            parent = groups[parent]['parent_id']
    group_patches = {r['id']: r for r in plan['group_annotations']}
    assert len(group_patches) == len(plan['group_annotations'])
    assert set(group_patches) == set(descendants), 'Incomplete parent annotation set'
    for identifier, row in group_patches.items():
        u = groups[identifier]
        actual = {'name': u['name'], 'level': u['level'], 'parent_id': u['parent_id'],
                  'affected_namibia_location_ids': sorted(descendants[identifier])}
        assert row['expected'] == actual, f'Parent annotation guard mismatch: {identifier}'
        assert set(row['metadata_patch']) == {'source_quality_review'}, 'Unapproved mutation field'
    return True


def build(features, units, review, migration, evidence_hashes):
    current = [f for f in features if f['properties']['reference_owner'] == 'Namibia']
    records = {r['id']: r for r in review['current_locations']}
    assert len(current) == len(records) == 111
    assert {f['properties']['id'] for f in current} == set(records)
    assert migration['status'] == 'blocked'
    source = review['source']
    profile = {
        'code': 'namibia-2007-source-label-geometry', 'country': 'Namibia',
        'status': 'pending-source-replacement', 'semantic_complete': False,
        'summary': 'The Namibia reference layer comes from a defective 2007 source whose names and footprints frequently disagree. A complete licensed replacement has been reviewed but is blocked by unresolved boundary differences.',
        'current_location_count': 111, 'current_original_feature_count': 109,
        'candidate_location_count': 107, 'candidate_province_count': 14,
        'current_source': {'id': 'gb:NAM:ADM2', 'vintage': '2007',
                           'license': 'Public Domain',
                           'url': 'https://purl.stanford.edu/cs051py0596'},
        'candidate_source': {'url': source['url'], 'vintage': '2011 source / later regional labels',
                             'license': source['license'], 'status': 'blocked',
                             'modern_121_constituency_coverage': 'Not established by this source'},
        'source_profile_problem': 'Upstream SHP/DBF name/footprint joins were checked against all 109 original records. Even an individually plausible name remains subject to this countrywide source review.',
        'migration_blocks': migration['blocks'],
        'safe_coast_restoration_m2': migration['coastal_concordance']['safe_restoration_m2'],
        'remaining_unresolved_old_land_m2': migration['coastal_concordance']['remaining_unresolved_old_land_m2'],
        'historical_records': 'Preserved on existing identities; no automatic transfer approved',
        'evidence': [
            {'url': 'https://purl.stanford.edu/cs051py0596', 'title': 'Original Namibia constituencies, 2007',
             'inspected_fact': 'All 109 original binary SHP/DBF row joins checked. Large label/coordinate errors occur in the upstream source, not only in the atlas conversion.'},
            {'url': source['url'], 'title': 'NSA / OCHA COD-AB Namibia reference boundaries',
             'inspected_fact': 'Licensed former 107-constituency framework with14 regional clusters, complete internal coverage and explicit obsolete-vintage caveat; modern 121coverage remains open.'},
        ],
        'public_evidence_files': [
            {'path': 'namibia-source-review.json.gz', 'title': 'Every current and candidate source unit',
             'sha256': evidence_hashes['review']},
            {'path': 'retained-geographic-sources/namibia/migration-receipt.json.gz',
             'title': 'Blocked complete-country replacement and neighbor conflicts',
             'sha256': evidence_hashes['migration']},
            {'path': 'retained-geographic-sources/namibia/coastal-concordance-receipt.json.gz',
             'title': 'Source-supported coastal restoration and remaining gaps',
             'sha256': evidence_hashes['coast']},
            {'path': 'retained-geographic-sources/namibia/manifest.json',
             'title': 'Retained source licenses, hashes and original geometry',
             'sha256': evidence_hashes['manifest']},
        ],
    }
    by_id = {u['id']: u for u in units}
    descendant_ids = {}
    feature_annotations = []
    for f in sorted(current, key=lambda f: f['properties']['id']):
        p = f['properties']
        r = records[p['id']]
        assert p['name'] == r['name'] and p['parent_id'] == r['parent_id']
        assert (p['metadata']['source_id'] == 'gb:NAM:ADM2' or
                any(member.startswith('gb:NAM:ADM2:') for member in p['metadata'].get('source_member_ids', [])))
        assert str(p['metadata']['reference_year']) == '2007'
        matches = r['top_spatial_matches']
        annotation = {
            'status': profile['status'], 'profile_code': profile['code'],
            'summary': 'Namibia 2007 reference source requires correction; current territory and historical records have been preserved.',
            'source_profile_problem': profile['source_profile_problem'],
            'individual_correspondence': 'No overlap with independent COD country footprint' if not matches else
            'Normalized label matches spatial winner; source-profile review remains open' if r['name_matches_spatial_winner'] else
            'Label differs from spatial winner; spelling, source-join error or succession requires review',
            'independent_spatial_matches': matches,
            'replacement_status': 'Blocked; candidate source is former 107framework, not certified modern 121framework',
            'evidence': profile['evidence'], 'public_evidence_files': profile['public_evidence_files'],
        }
        feature_annotations.append({'id': p['id'], 'expected': {
            'name': p['name'], 'parent_id': p['parent_id'], 'source_id': p['metadata']['source_id'],
            'reference_year': str(p['metadata']['reference_year']),
            'source_member_ids': p['metadata'].get('source_member_ids', []),
            'geometry_sha256': geometry_hash(f['geometry']),
        }, 'metadata_patch': {'source_quality_review': annotation}})
        parent = p['parent_id']
        while parent:
            assert parent in by_id
            descendant_ids.setdefault(parent, []).append(p['id'])
            parent = by_id[parent]['parent_id']
    groups = []
    for identifier in sorted(descendant_ids):
        u = by_id[identifier]
        affected = sorted(descendant_ids[identifier])
        groups.append({'id': identifier, 'expected': {'name': u['name'], 'level': u['level'],
                                                      'parent_id': u['parent_id'],
                                                      'affected_namibia_location_ids': affected},
                       'metadata_patch': {'source_quality_review': {
                           'status': 'contains-pending-source-review', 'profile_code': profile['code'],
                           'scope': 'Namibia descendant locations only; no claim that all other members of this group are defective.',
                           'affected_locations': len(affected),
                           'summary': f'Contains {len(affected)} Namibia locations from the defective 2007 reference source; a full replacement remains blocked.',
                           'evidence': profile['evidence'], 'public_evidence_files': profile['public_evidence_files'],
                       }}})
    return {'schema_version': 1, 'kind': 'metadata-only-source-quality-plan',
            'status': 'pending-root-integration', 'reference_date': '2026-10-01',
            'mutation_contract': 'Only metadata.source_quality_review may change. Geometry, names, IDs, parent memberships, ownership and dated records must remain identical.',
            'guard_policy': 'Verify every expected field and complete country/ancestor crosswalk before applying any patch. Never apply a partial country annotation set.',
            'profile_review': profile, 'feature_annotations': feature_annotations,
            'group_annotations': groups,
            'counts': {'locations': len(feature_annotations), 'parent_groups': len(groups),
                       'candidate_locations': 107, 'candidate_provinces': 14}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='data/namibia-source-quality-annotations.json')
    args = parser.parse_args()
    index = read(ROOT/'data/world-index.json')
    features = [f for part in index['parts'] for f in read(ROOT/'data'/part)['features']]
    base = ROOT/'data/retained-geographic-sources/namibia'
    review_path = ROOT/'data/namibia-source-review.json.gz'
    migration_path = base/'migration-receipt.json.gz'
    result = build(features, read(ROOT/'data/hierarchy.json'), read(review_path), read(migration_path),
                   {'review': file_hash(review_path), 'migration': file_hash(migration_path),
                    'coast': file_hash(base/'coastal-concordance-receipt.json.gz'),
                    'manifest': file_hash(base/'manifest.json')})
    validate_against_current(result, features, read(ROOT/'data/hierarchy.json'))
    output = ROOT/args.output
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
    print(json.dumps({'output': str(output), 'counts': result['counts'], 'sha256': file_hash(output)}))


if __name__ == '__main__':
    main()
