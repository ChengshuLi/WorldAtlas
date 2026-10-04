#!/usr/bin/env python3
"""Rebuild issue #601's exact source-role crosswalk from pinned project blobs."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = Path('data/regional-review/alaska-ecoregion-role-followup-2026')
SCOPE = OWNED / 'scope.json'
OUTPUT = OWNED / 'assessment.json'
SNAPSHOT = '276d72e1f316ad58d52c8fea7974a873c2ec9387'
EVALUATION = '0ea5b92969a37e404daded7a5c1d8931bd74b19c'
PARENT = Path('data/regional-review/regional-review-93f8f3bee8e205be')
QUERY_FILE = OWNED / 'sources/resolve-alaska-eco-attributes-20261004.json'
CENSUS_FILE = OWNED / 'sources/census-tiger-2018-seven-alaska-counties.json'
REMOTE_FIELDS = ('ECO_NAME', 'BIOME_NUM', 'BIOME_NAME', 'REALM', 'LICENSE')


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob(commit: str, path: str | Path) -> bytes:
    path = str(path)
    mode = subprocess.check_output(['git', 'ls-tree', commit, '--', path], cwd=ROOT, text=True)
    if not mode.startswith(('100644 ', '100755 ')):
        raise ValueError(f'Pinned input is not an ordinary file: {commit}:{path}')
    return subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=ROOT)


def parsed(blob: bytes, path: str | Path):
    path = str(path)
    return json.loads(gzip.decompress(blob) if path.endswith('.gz') else blob)


def canon(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()


def build_report(scope: dict | None = None) -> dict:
    scope = scope or json.loads((ROOT / SCOPE).read_bytes())
    if scope['issue'] != 601 or len(scope['subject_ids']) != 33 or len(set(scope['subject_ids'])) != 33:
        raise ValueError('Wrong issue or incomplete/duplicate assigned subject roster')
    if scope['parent_source_snapshot_commit'] != SNAPSHOT or scope['parent_evaluation_baseline_commit'] != EVALUATION:
        raise ValueError('Parent snapshot/evaluation commits differ from the audited handoff')
    if sha(scope['issue_body'].encode()) != scope['issue_body_sha256']:
        raise ValueError('Captured #601 issue body differs from its whole-text pin')
    subjects = set(scope['subject_ids'])
    prefix = str(PARENT) + '/'
    source = lambda rel: git_blob(SNAPSHOT, prefix + rel)

    # Confirm the later packet commit contains the same exact project geography as the original evaluation baseline.
    index_raw = git_blob(EVALUATION, 'data/world-index.json')
    hierarchy_raw = git_blob(EVALUATION, 'data/hierarchy.json')
    snapshot_index = git_blob(SNAPSHOT, 'data/world-index.json')
    snapshot_hierarchy = git_blob(SNAPSHOT, 'data/hierarchy.json')
    if sha(index_raw) != sha(snapshot_index) or sha(hierarchy_raw) != sha(snapshot_hierarchy):
        raise ValueError('Project world index or hierarchy changed after the #486 evaluation baseline')
    world = json.loads(index_raw)
    parts = world['parts']
    if len(parts) != 36:
        raise ValueError('Unexpected original world-index partition count')
    occurrences: dict[str, list[str]] = {subject: [] for subject in subjects}
    subject_features: dict[str, dict] = {}
    indexed_part_descriptors = []
    for part in parts:
        path = 'data/' + part
        raw = git_blob(EVALUATION, path)
        if raw != git_blob(SNAPSHOT, path):
            raise ValueError(f'Indexed geography part differs from source snapshot: {path}')
        indexed_part_descriptors.append({'path': path, 'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'file-bytes'})
        data = json.loads(raw)
        for feature in data.get('features', []):
            props = feature.get('properties') or {}
            sid = feature.get('id') or props.get('id')
            if sid in subjects:
                occurrences[sid].append(path)
                subject_features[sid] = feature
    bad = {sid: paths for sid, paths in occurrences.items() if len(paths) != 1}
    if bad:
        raise ValueError(f'Assigned subjects are not unique across all 36 indexed parts: {bad}')

    audit = parsed(source('derived-portion-audit.json'), 'derived-portion-audit.json')
    assessment = parsed(source('assessment.json'), 'assessment.json')
    chains = parsed(source('sources/current-parent-chains.json.gz'), 'sources/current-parent-chains.json.gz')
    resolve_archive = parsed(source('sources/resolve-15-ecoregions.geojson.gz'), 'resolve-15-ecoregions.geojson.gz')
    geoboundaries = parsed(source('sources/geoboundaries-USA-ADM2.geojson'), 'sources/geoboundaries-USA-ADM2.geojson')
    gb_meta = parsed(source('sources/geoboundaries-USA-ADM2-metadata.json'), 'sources/geoboundaries-USA-ADM2-metadata.json')
    resolve_item = parsed(source('sources/resolve-item-metadata.json'), 'sources/resolve-item-metadata.json')
    resolve_layer = parsed(source('sources/resolve-layer-metadata.json'), 'sources/resolve-layer-metadata.json')
    registry = parsed(source('sources.json'), 'sources.json')
    archived_scope = parsed(source('scope.json'), 'scope.json')

    audit_rows = audit['fragments']
    if len(audit_rows) != 33 or {r['location_id'] for r in audit_rows} != subjects:
        raise ValueError('Original derived audit does not exactly cover the 33 issue subjects')
    assessment_rows = {r['location_id']: r for r in assessment['locations']}
    chain_rows = {r['id']: r['parent_chain'] for r in chains}
    if len(chain_rows) != len(chains) or not subjects.issubset(assessment_rows) or not subjects.issubset(chain_rows):
        raise ValueError('Original assessment or full parent-chain snapshot misses assigned subjects')

    local_resolve = {int(f['properties']['ECO_ID']): f['properties'] for f in resolve_archive['features']}
    remote_bytes = (ROOT / QUERY_FILE).read_bytes()
    scope_query_sha = scope.get('official_query_sha256')
    if scope_query_sha and sha(remote_bytes) != scope_query_sha:
        raise ValueError('Official ArcGIS query bytes differ from the recorded retrieval hash')
    for capture_name, capture in scope.get('new_source_capture', {}).items():
        captured = (ROOT / OWNED / 'sources' / capture_name).read_bytes()
        if len(captured) != capture['bytes'] or sha(captured) != capture['sha256']:
            raise ValueError(f'Captured primary-source bytes differ from the scope pin: {capture_name}')
    remote_query = json.loads(remote_bytes)
    if remote_query.get('error') or len(remote_query.get('features', [])) != 15:
        raise ValueError('Official ArcGIS attribute query did not return all 15 expected Eco_ID rows')
    remote_resolve = {int(f['attributes']['ECO_ID']): f['attributes'] for f in remote_query['features']}
    if set(local_resolve) != set(remote_resolve) or len(local_resolve) != 15:
        raise ValueError('Retained and current official RESOLVE feature rosters differ')
    for eco_id in local_resolve:
        for field in REMOTE_FIELDS:
            if local_resolve[eco_id].get(field) != remote_resolve[eco_id].get(field):
                raise ValueError(f'ReSOLVE retained/current source mismatch: Eco_ID {eco_id}, {field}')

    adm2_props = {f['properties']['shapeID']: f['properties'] for f in geoboundaries['features']}
    census_evidence = json.loads((ROOT / CENSUS_FILE).read_bytes())
    census_by_name = {r['NAME']: r for r in census_evidence['rows']}
    if len(census_by_name) != 7 or census_evidence['selection']['feature_count'] != 7:
        raise ValueError('Official Census 2018 Alaska county predecessor table is not exactly seven rows')
    census_archive = census_evidence['source_archive']
    if census_archive != scope.get('census_source_archive'):
        raise ValueError('Official Census archive URL/date/hash differs from the captured issue scope')
    location_rows = []
    for inherited in sorted(audit_rows, key=lambda row: row['location_id']):
        sid = inherited['location_id']
        row = assessment_rows[sid]
        chain = chain_rows[sid]
        feature = subject_features[sid]
        metadata = chain[0]['metadata']
        eco_id = int(inherited['eco_id'])
        admin_shape = inherited['predecessor_shape_id']
        admin = adm2_props.get(admin_shape)
        if not admin or admin.get('shapeGroup') != 'USA' or admin.get('shapeType') != 'ADM2':
            raise ValueError(f'2018 source predecessor missing or wrong tier: {sid}')
        if admin.get('shapeName') != inherited['predecessor_name']:
            raise ValueError(f'2018 source predecessor name mismatch: {sid}')
        census_admin = census_by_name.get(admin['shapeName'])
        if not census_admin or census_admin.get('STATEFP') != '02' or census_admin.get('GEOID') != f"02{census_admin.get('COUNTYFP')}":
            raise ValueError(f'Official Census 2018 predecessor name/FIPS mismatch: {sid}')
        normalized_tiger_name = census_admin['NAMELSAD'].removesuffix(' Census Area').removesuffix(' Borough')
        if normalized_tiger_name != admin['shapeName']:
            raise ValueError(f'GeoBoundaries county predecessor does not map to official Census NAMELSAD: {sid}')
        eco = local_resolve.get(eco_id)
        if not eco or eco.get('ECO_NAME') != inherited['eco_name']:
            raise ValueError(f'RESOLVE Eco_ID/name mismatch: {sid}')
        if row.get('name') != inherited['name'] or chain[0].get('name') != inherited['name']:
            raise ValueError("Location name differs across the issue's inherited ledgers: " + sid)
        if metadata.get('source_id') != f'resolve:{eco_id}' or metadata.get('original_id') != admin_shape:
            raise ValueError(f'Location metadata source lineage mismatches the inherited crosswalk: {sid}')
        if metadata.get('source_member_ids') != [f'gb:USA:ADM2:{admin_shape}']:
            raise ValueError(f'Current source-member identity does not preserve the 2018 admin predecessor: {sid}')
        if metadata.get('source_role') != 'Counties' or 'Counties' not in metadata.get('selection_reason', ''):
            raise ValueError(f'Expected inherited county-role misclassification not reproduced: {sid}')
        if metadata.get('administrative_level') != 'Named physical region portion' or metadata.get('parent_source_level') != 'ADM1':
            raise ValueError(f'Unexpected inherited role/tier metadata: {sid}')
        if len(chain) != 6 or [p.get('id') for p in chain] != [
            sid,
            'framework:province:alaska:4057e2fddbc5',
            'framework:area:pacific:31aced66907e',
            'framework:region:western-north-america:d2a1c2775a57',
            'framework:subcontinent:northern-america:477e054b32f2',
            'framework:continent:north-america:1ca27616f338',
        ]:
            raise ValueError(f'Frozen current parent chain is incomplete or changed: {sid}')
        if feature.get('id', feature.get('properties', {}).get('id')) != sid:
            raise ValueError(f'Containing geography feature ID mismatch: {sid}')
        parent_id = (feature.get('properties') or {}).get('parent_id')
        if parent_id != chain[0].get('parent_id'):
            raise ValueError(f'Containing geography feature and parent-chain snapshot disagree: {sid}')
        location_rows.append({
            'id': sid,
            'name': inherited['name'],
            'source_lineage': {
                'resolve_source_id': f'resolve:{eco_id}',
                'resolve_eco_id': eco_id,
                'resolve_eco_name': inherited['eco_name'],
                'resolve_biome': eco.get('BIOME_NAME'),
                'resolve_realm': eco.get('REALM'),
                'resolve_license_attribute': eco.get('LICENSE'),
                'resolve_source_vintage': '2017',
                'administrative_predecessor_source_id': f'gb:USA:ADM2:{admin_shape}',
                'administrative_predecessor_shape_id': admin_shape,
                'administrative_predecessor_name': admin.get('shapeName'),
                'administrative_predecessor_tier': 'USA ADM2; geoBoundaries source metadata says Counties',
                'administrative_predecessor_vintage': '2018',
                'census_tiger_geoid': census_admin['GEOID'],
                'census_tiger_namelsad': census_admin['NAMELSAD'],
                'census_tiger_lsad': census_admin['LSAD'],
                'census_tiger_classfp': census_admin['CLASSFP'],
                'census_tiger_funcstat': census_admin['FUNCSTAT'],
            },
            'inherited_metadata': {
                'source_id': metadata.get('source_id'),
                'source_name': metadata.get('source_name'),
                'source_role': metadata.get('source_role'),
                'selection_reason': metadata.get('selection_reason'),
                'administrative_level': metadata.get('administrative_level'),
                'parent_source_level': metadata.get('parent_source_level'),
                'reference_year': metadata.get('reference_year'),
                'original_id': metadata.get('original_id'),
                'source_member_ids': metadata.get('source_member_ids'),
                'location_basis': metadata.get('location_basis'),
                'parent_match': metadata.get('parent_match'),
            },
            'current_parent_chain': [
                {'id': p['id'], 'name': p['name'], **({'parent_id': p['parent_id']} if p.get('parent_id') else {})}
                for p in chain
            ],
            'proposed_recommendation': {
                'remove_unsupported_role': 'Counties',
                'proposed_non_administrative_role': 'Named physical region / ecoregion-derived portion',
                'selection_basis': 'The named 2017 RESOLVE ecoregion portion derives from the intersection with the recorded 2018 county predecessor; the ecological layer supplies the physical partition, while the county polygon is preserved as source lineage.',
                'preserve': ['stable subject ID', 'RESOLVE source ID/Eco_ID', '2018 county source-member ID', 'current geometry', 'current complete parent chain', 'United States reference owner'],
                'tier_note': 'Do not recast the ecoregion as an administrative tier. Keep the 2018 county predecessor and current Alaska ADM1 parent as distinct source-lineage facts. Exact normalized role vocabulary is for engineering/model integration.',
            },
        })

    role_counts = Counter(r['inherited_metadata']['source_role'] for r in location_rows)
    predecessor_counts = Counter(r['source_lineage']['administrative_predecessor_name'] for r in location_rows)
    eco_counts = Counter(r['source_lineage']['resolve_eco_id'] for r in location_rows)
    chain_counts = Counter(tuple(p['id'] for p in r['current_parent_chain'][1:]) for r in location_rows)
    if role_counts != {'Counties': 33} or len(predecessor_counts) != 7 or len(eco_counts) != 15 or len(chain_counts) != 1:
        raise ValueError(f'Whole-scope totals differ: roles={dict(role_counts)}, predecessors={dict(predecessor_counts)}, ecoregions={dict(eco_counts)}, chains={len(chain_counts)}')

    def source_desc(path: str) -> dict:
        raw = git_blob(SNAPSHOT, path)
        return {'path': path, 'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'file-bytes'}

    selected_parent_files = [
        str(PARENT / 'scope.json'), str(PARENT / 'assessment.json'), str(PARENT / 'derived-portion-audit.json'),
        str(PARENT / 'sources.json'), str(PARENT / 'sources/current-parent-chains.json.gz'),
        str(PARENT / 'sources/current-scope-and-parents.geojson.gz'),
        str(PARENT / 'sources/geoboundaries-USA-ADM1-metadata.json'), str(PARENT / 'sources/geoboundaries-USA-ADM1.geojson'),
        str(PARENT / 'sources/geoboundaries-USA-ADM2-metadata.json'), str(PARENT / 'sources/geoboundaries-USA-ADM2.geojson'),
        str(PARENT / 'sources/resolve-item-metadata.json'), str(PARENT / 'sources/resolve-layer-metadata.json'),
        str(PARENT / 'sources/resolve-15-ecoregions.geojson.gz'),
    ]
    parent_file_descriptors = [source_desc(path) for path in selected_parent_files]
    parent_file_descriptors.extend(indexed_part_descriptors)
    parent_file_descriptors.extend([
        {'path': 'data/world-index.json', 'bytes': len(index_raw), 'sha256': sha(index_raw), 'hash_kind': 'file-bytes'},
        {'path': 'data/hierarchy.json', 'bytes': len(hierarchy_raw), 'sha256': sha(hierarchy_raw), 'hash_kind': 'file-bytes'},
    ])
    parent_file_descriptors.sort(key=lambda x: x['path'])
    registry_row = {row['path']: row for row in registry['sources']}
    old_archives = []
    for local_path in [
        'sources/geoboundaries-USA-ADM2.geojson', 'sources/geoboundaries-USA-ADM2-metadata.json',
        'sources/resolve-15-ecoregions.geojson.gz', 'sources/resolve-item-metadata.json', 'sources/resolve-layer-metadata.json',
    ]:
        descriptor = registry_row[local_path.removeprefix('sources/')]
        old_archives.append({'path': str(PARENT / local_path), 'bytes': descriptor['bytes'], 'sha256': descriptor['sha256'], 'hash_kind': 'file-bytes'})

    return {
        'version': 1,
        'issue': 601,
        'baseline': {
            'source_snapshot_commit': SNAPSHOT,
            'original_geographic_evaluation_commit': EVALUATION,
            'evaluation_and_source_snapshot_core_files_byte_equal': True,
            'world_index_part_count': len(parts),
            'assigned_subject_count': len(location_rows),
            'all_assigned_ids_occur_exactly_once_across_all_indexed_parts': True,
            'source_snapshot_relevant_input_file_count': len(parent_file_descriptors),
            'inputs': parent_file_descriptors,
            'subject_files': {sid: occurrences[sid][0] for sid in sorted(subjects)},
            'original_parent_scope_sha256': sha(source('scope.json')),
            'original_parent_assessment_sha256': sha(source('assessment.json')),
            'original_parent_derived_audit_sha256': sha(source('derived-portion-audit.json')),
            'original_parent_source_registry_sha256': sha(source('sources.json')),
            'original_preserved_source_descriptors': old_archives,
        },
        'whole_scope_summary': {
            'assigned_subjects': 33,
            'subjects_with_exactly_one_current_containing_part': 33,
            'subjects_with_complete_six_node_parent_chain': 33,
            'subjects_with_inherited_source_role_counties': 33,
            'distinct_2018_adm2_predecessors': len(predecessor_counts),
            'distinct_resolve_2017_ecoregion_features': len(eco_counts),
            'official_tiger_2018_county_equivalent_predecessors': len(census_by_name),
            'official_tiger_2018_archive_sha256': census_archive['sha256'],
            'direct_current_arcgis_feature_service_records': len(remote_resolve),
            'retained_vs_current_resolve_attribute_mismatches': 0,
            'current_parent_chain': [dict(p) for p in location_rows[0]['current_parent_chain']],
            'predecessor_fragment_counts': dict(sorted(predecessor_counts.items())),
            'ecoregion_fragment_counts': {str(k): eco_counts[k] for k in sorted(eco_counts)},
            'current_role_counts': dict(role_counts),
        },
        'source_role_assessment': location_rows,
        'interpretation': {
            'finding': 'For every assigned subject, RESOLVE supplies the named ecological feature used for the physical portion, but the retained source_role and selection rationale identify it as a county. The exact 2018 county predecessor is separately and consistently retained through original_id/source_member_ids. These administrative and physical source roles are conflated in the current metadata.',
            'recommendation': 'Replace the false administrative Counties role and county-tier selection rationale with a schema-approved non-administrative physical/ecoregion role and an accurate intersection/source-lineage explanation. If the role vocabulary only permits administrative roles, leave the unsupported role unset pending the integration decision. Preserve all current IDs, geometries, parent membership and ownership references.',
            'source_vintage_handling': 'Record the RESOLVE layer vintage as 2017 and the predecessor county source vintage as 2018 in distinct fields/notes; the inherited reference_year=2018 must not be used to imply the RESOLVE classification itself is 2018.',
            'unresolved': [
                'Whether this physical partition is an appropriate published location granularity is an engineering/integration model decision outside the source-role recommendation.',
                'No geometric union or boundary calculation was repeated in this packet; predecessor-union results are inherited from the pinned #486 audit.',
                'RESOLVE ecology does not establish political ownership, county membership, settlement completeness or legal boundaries.',
                'The original geoBoundaries 2018 county source is a generalized source representation; no new direct Census row-level legal-boundary validation was performed.',
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--create', action='store_true', help='Create a new assessment.json; refuses overwrite')
    parser.add_argument('--check', action='store_true', help='Compare a deterministic rebuild to assessment.json (default)')
    args = parser.parse_args()
    expected = canon(build_report())
    if args.create:
        with (ROOT / OUTPUT).open('xb') as handle:
            handle.write(expected)
        print(json.dumps({'mode': 'create', 'subjects': 33, 'result': 'PASS', 'sha256': sha(expected)}))
    else:
        saved = (ROOT / OUTPUT).read_bytes()
        if saved != expected:
            raise SystemExit('Saved assessment differs from immutable source rebuild')
        print(json.dumps({'mode': 'read-only-check', 'subjects': 33, 'result': 'PASS', 'sha256': sha(expected)}))

if __name__ == '__main__':
    main()
