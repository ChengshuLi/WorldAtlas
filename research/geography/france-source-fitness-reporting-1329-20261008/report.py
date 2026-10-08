#!/usr/bin/env python3
"""Derive an additive correction from the immutable France #1310 report runs.

Normal use reads only the exact claimed issue snapshot and Git-pinned original
packet/source bytes, admits the whole run before analysis, and writes a fresh
NewVintage. ``check-fixture`` is a no-output negative-control mode; it accepts
only ephemeral fixtures under this owned packet and can never publish evidence.
"""
import argparse
import collections
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types

OWNED = 'research/geography/france-source-fitness-reporting-1329-20261008/'
ORIGINAL = 'research/geography/france-nine-gap-family-source-fitness-20261007/'
SOURCE_ROOT = 'coordination/engineering/original-geography-source-corpus-20261006/'
SOURCE_PATH = SOURCE_ROOT + 'payloads/gb-FRA-ADM3-000.bin.gz'
CATALOGUE_PATH = SOURCE_ROOT + 'catalogue.json'
PROGRESS_PATH = SOURCE_ROOT + 'progress.json'
ATLAS_PART_PATH = 'data/geography/part-8.json'
HELPER_PATH = 'scripts/evidence/immutable.py'
MAX_FILE = 32 * 1024 * 1024
MAX_PHASE = 256 * 1024 * 1024
OUTPUTS = ['erratum.json', 'erratum.md', 'candidate-reconciliation.csv', 'execution.json']


def fail(message):
    raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)


def load_json(raw, label):
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        fail(f'{label} is not valid UTF-8 JSON: {error}')
    if not isinstance(value, dict):
        fail(f'{label} must be a JSON object')
    return value


def read_owned(repo, relative, max_bytes=MAX_FILE):
    if not relative.startswith(OWNED) or '\\' in relative or any(p in ('', '.', '..') for p in relative.split('/')):
        fail('Fixture path escapes the owned evidence prefix')
    target = Path(repo) / relative
    current = Path(repo)
    for component in relative.split('/'):
        current = current / component
        if current.is_symlink():
            fail('Symlink in fixture path')
    if not target.is_file():
        fail('Fixture is not an ordinary file')
    raw = target.read_bytes()
    if len(raw) > max_bytes:
        fail('Fixture exceeds the ordinary-file byte limit')
    return raw


def extract_issue_contract(issue):
    if issue.get('number') != 1489 or issue.get('state') != 'open':
        fail('Captured GitHub issue is not the open #1489 scope')
    body = issue.get('body')
    if not isinstance(body, str):
        fail('Issue body is absent')
    match = re.search(r'<!-- worldatlas-work:v1\s*(.*?)\s*-->', body, re.S)
    if not match:
        fail('Issue machine contract is absent')
    contract = load_json(match.group(1).encode(), 'issue machine contract')
    if contract.get('mode') != 'geography' or contract.get('owned_paths') != [OWNED]:
        fail('Issue mode or owned path changed')
    if contract.get('depends_on') != [1310] or contract.get('max_prs') != 2:
        fail('Issue dependency or PR allowance changed')
    if 'France48candidate/9family/16contact' not in contract.get('scope', ''):
        fail('Issue scope contract changed')
    evidence = contract.get('evidence_quality')
    if not isinstance(evidence, dict) or evidence.get('version') != 1 or evidence.get('review_kind') != 'code':
        fail('Issue evidence contract changed')
    if evidence.get('manifest_path') != OWNED + 'evidence-quality.json':
        fail('Issue manifest path changed')
    subjects = evidence.get('subject_ids')
    if not isinstance(subjects, list) or len(subjects) != 16 or len(set(subjects)) != 16:
        fail('Issue contact scope is not exact and unique')
    if not isinstance(evidence.get('pins'), dict):
        fail('Issue baseline pins are absent')
    return contract, evidence


def context(repo, request_path=OWNED + 'request.json'):
    repo = Path(repo).resolve()
    owned = repo / OWNED
    request_raw = read_owned(repo, request_path)
    request = load_json(request_raw, 'request.json')
    if request.get('version') != 1 or request.get('issue') != 1489 or request.get('owned_path') != OWNED:
        fail('Request scope does not match #1489')
    issue_raw = read_owned(repo, request['issue_snapshot']['path'])
    issue_desc = request['issue_snapshot']
    if len(issue_raw) != issue_desc.get('bytes') or sha(issue_raw) != issue_desc.get('sha256'):
        fail('Captured issue snapshot changed')
    issue = load_json(issue_raw, 'issue snapshot')
    contract, evidence = extract_issue_contract(issue)
    claim = load_json(read_owned(repo, OWNED + 'claim-receipt.json'), 'claim receipt')
    if claim.get('accepted') is not True or claim.get('issue_number') != 1489:
        fail('Claim receipt is not accepted for #1489')
    if claim.get('claim', {}).get('worker_id') != request.get('worker_id') or claim.get('claim', {}).get('claim_id') != request.get('claim_id'):
        fail('Claim receipt and request identity differ')
    if claim.get('claim', {}).get('branch') != request.get('branch'):
        fail('Claim receipt branch differs from request')
    commit = request.get('baseline_commit')
    if not re.fullmatch(r'[a-f0-9]{40}', commit or '') or git(repo, 'rev-parse', '--verify', commit + '^{commit}').decode().strip() != commit:
        fail('Baseline commit is not exact and available')
    files = request.get('baseline_files')
    if not isinstance(files, list) or not files:
        fail('Immutable baseline inventory is missing')
    by_path = {row.get('path'): row for row in files}
    if len(by_path) != len(files):
        fail('Duplicate baseline path')
    if not all(path in by_path and by_path[path].get('sha256') == expected
               for path, expected in evidence['pins'].items()):
        fail('Issue pins do not match authenticated baseline descriptors')
    helper_pin = by_path.get(HELPER_PATH)
    if not helper_pin:
        fail('Shared immutable-evidence helper is not inventoried')
    row = git(repo, 'ls-tree', '-z', commit, '--', HELPER_PATH).rstrip(b'\0')
    meta, name = row.split(b'\t', 1)
    mode, kind, oid = meta.decode().split()
    if mode not in ('100644', '100755') or kind != 'blob' or name.decode() != HELPER_PATH:
        fail('Pinned helper is not an ordinary committed blob')
    helper_bytes = git(repo, 'cat-file', 'blob', oid)
    if len(helper_bytes) != helper_pin.get('bytes') or sha(helper_bytes) != helper_pin.get('sha256'):
        fail('Pinned helper bytes differ from the declared descriptor')
    trusted = types.ModuleType('worldatlas_pinned_immutable')
    exec(compile(helper_bytes, f'{commit}:{HELPER_PATH}', 'exec'), trusted.__dict__)
    baseline = trusted.Baseline(repo, commit, files)
    loaded = baseline.load_modules({'scripts.evidence.immutable': HELPER_PATH})
    shared = loaded['scripts.evidence.immutable']
    if shared.sha256(helper_bytes) != helper_pin['sha256']:
        fail('Executed shared helper does not match its immutable pin')
    # The issue snapshot, request, claim and actual producer bytes are consumed
    # candidate inputs; account for them in the same complete phase.
    baseline.admit('candidate:' + request['issue_snapshot']['path'], len(issue_raw))
    baseline.admit('candidate:' + request_path, len(request_raw))
    claim_raw = (owned / 'claim-receipt.json').read_bytes()
    baseline.admit('candidate:' + OWNED + 'claim-receipt.json', len(claim_raw))
    producer_path = Path(__file__).resolve()
    producer_raw = producer_path.read_bytes()
    baseline.admit('candidate:' + OWNED + 'report.py', len(producer_raw))
    return {'repo': repo, 'owned': owned, 'request': request, 'issue': issue,
            'issue_contract': contract, 'evidence_contract': evidence, 'baseline': baseline,
            'shared': shared, 'producer_raw': producer_raw, 'producer_sha256': sha(producer_raw),
            'by_path': by_path}


def pinned(ctx, path):
    row = ctx['by_path'].get(path)
    if not row:
        fail('Consumed file lacks a declared baseline pin: ' + path)
    raw = ctx['baseline'].pinned_bytes(path)
    if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
        fail('Pinned input changed: ' + path)
    return raw


def exact_rows(rows, expected, key, label):
    if not isinstance(rows, list) or not rows:
        fail(label + ' must be a complete nonempty list')
    identities = [row.get(key) if isinstance(row, dict) else None for row in rows]
    if any(not isinstance(value, str) or not value for value in identities):
        fail(label + ' contains a missing identity')
    if len(identities) != len(set(identities)):
        fail(label + ' contains duplicate identities')
    if len(expected) != len(set(expected)) or set(identities) != set(expected):
        fail(label + ' contains an omitted or foreign identity')
    return {identity: row for identity, row in zip(identities, rows)}


def analyze(ctx, run1_raw, run2_raw):
    baseline = ctx['baseline']
    if len(run1_raw) > MAX_FILE or len(run2_raw) > MAX_FILE:
        fail('Full run input exceeds 32 MiB')
    if run1_raw != run2_raw:
        fail('Two full original run inputs differ byte-for-byte')
    run = load_json(run1_raw, 'complete run')
    contract_raw = pinned(ctx, ORIGINAL + 'run-contract.json')
    old_contract = load_json(contract_raw, 'original run contract')
    frozen = old_contract.get('scope')
    if not isinstance(frozen, dict):
        fail('Original frozen scope is absent')
    expected_components = frozen.get('component_ids', [])
    expected_families = frozen.get('family_ids', [])
    expected_contacts = ctx['evidence_contract']['subject_ids']
    if len(expected_components) != 48 or len(expected_families) != 9 or len(expected_contacts) != 16:
        fail('Bound complete scope counts changed')
    if frozen.get('contact_ids') != expected_contacts:
        fail('Issue contacts differ from original frozen roster')
    run_components = exact_rows(run.get('candidates'), expected_components, 'component_id', 'candidate records')
    run_families = exact_rows(run.get('families'), expected_families, 'id', 'family records')
    run_contacts = exact_rows(run.get('contacts'), expected_contacts, 'subject_id', 'contact records')
    if run.get('issue') != 1310 or run.get('frozen_scope') != frozen:
        fail('Run issue or exact frozen scope differs from its original contract')
    if run.get('candidate_count') != len(expected_components) or run.get('contact_count') != len(expected_contacts):
        fail('Run metric counts differ from complete raw record counts')
    if run.get('official_layer_roster', {}).get('features') != 333:
        fail('Recorded full IGN feature roster is not 333')
    if run.get('official_layer_roster', {}).get('numberMatched') != 333 or run.get('official_layer_roster', {}).get('numberReturned') != 333:
        fail('Recorded IGN response is incomplete')
    controls = run.get('controls', {})
    scope_controls = controls.get('scope_roster', {})
    if not scope_controls or any(value is not True for value in scope_controls.values()):
        fail('A required omission/duplicate/foreign scope control did not pass')
    source_controls = controls.get('source_and_geometry', {})
    source_bools = [value for key, value in source_controls.items() if key.startswith('negative_') or key.startswith('positive_')]
    if not source_bools or any(value is not True for value in source_bools):
        fail('A required source/geometry control did not pass')
    axis_controls = controls.get('axis_order', {})
    if axis_controls.get('negative_swapped_candidate_envelope_hits') != 0 or not axis_controls.get('positive_full_geometry_candidate_count_with_source_intersection'):
        fail('Required full-layer axis/order controls are incomplete')
    if source_controls.get('raster_affine_nodata') != 'not-applicable: no raster input or raster transform was queried; coverage/NoData remain unresolved':
        fail('Raster applicability limit changed or was removed')

    source_path = SOURCE_PATH
    source_encoded = pinned(ctx, source_path)
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(source_encoded)) as stream:
            source_raw = stream.read(MAX_FILE + 1)
    except (OSError, EOFError) as error:
        fail('Pinned France source gzip is corrupt: ' + str(error))
    if len(source_raw) > MAX_FILE:
        fail('Decoded original France source exceeds 32 MiB')
    baseline.admit(source_path + ':decoded', len(source_raw))
    source_hash = sha(source_raw)
    catalogue = load_json(pinned(ctx, CATALOGUE_PATH), 'original source catalogue')
    source_product = next((row for row in catalogue.get('products', []) if row.get('key') == 'gb:FRA:ADM3'), None)
    if not source_product or source_product.get('original_bytes') != len(source_raw) or source_product.get('original_sha256') != source_hash:
        fail('Reconstructed source differs from the original whole-source catalogue record')
    source_geojson = load_json(source_raw, 'complete original France source')
    source_features = source_geojson.get('features')
    if not isinstance(source_features, list) or len(source_features) != source_product.get('feature_count'):
        fail('Original France source feature count differs from the complete catalogue')
    source_by_id = {}
    for feature in source_features:
        props = feature.get('properties', {}) if isinstance(feature, dict) else {}
        identity = props.get('shapeID')
        if not isinstance(identity, str) or identity in source_by_id:
            fail('Missing or duplicate original France shapeID')
        source_by_id[identity] = feature
    if len(source_by_id) != 320:
        fail('Original France ADM3 source is not the complete 320-feature product')
    atlas_part = load_json(pinned(ctx, ATLAS_PART_PATH), 'pinned current Atlas geography part')
    atlas_features = atlas_part.get('features')
    if not isinstance(atlas_features, list):
        fail('Pinned Atlas geography part has no complete feature list')
    expected_atlas_subjects = set(ctx['evidence_contract']['subject_ids'])
    atlas_by_id = {feature.get('id'): feature for feature in atlas_features if isinstance(feature, dict)}
    if len(atlas_by_id) != len(atlas_features) or not expected_atlas_subjects.issubset(atlas_by_id):
        fail('Pinned Atlas geography part omits or duplicates an issue contact subject')
    if any(atlas_by_id[identity].get('properties', {}).get('id') != identity for identity in expected_atlas_subjects):
        fail('Pinned Atlas geography part has a mismatched feature/property identity')

    # Bind the source's original retrieval observation from the pinned corpus
    # progress receipt, rather than presenting a file hash as a retrieval date.
    progress = load_json(pinned(ctx, PROGRESS_PATH), 'source corpus progress receipt')
    transport_desc = progress.get('archived_auxiliary_receipts', {}).get('transport-provenance.json', {})
    transport_raw = transport_desc.get('raw_utf8')
    if (not isinstance(transport_raw, str) or transport_desc.get('original_bytes') != len(transport_raw.encode('utf-8'))
            or transport_desc.get('original_sha256') != sha(transport_raw.encode('utf-8'))):
        fail('Original transport-provenance receipt bytes or hash are inconsistent')
    transport = load_json(transport_raw.encode('utf-8'), 'original transport provenance')
    france_rows = [row for row in transport.get('rows', []) if row.get('registry_key') == 'gb:FRA:ADM3']
    if len(france_rows) != 1:
        fail('Original transport provenance does not contain exactly one France ADM3 source row')
    france = france_rows[0]
    attempts = france.get('attempts', [])
    if (france.get('status') != 'successful-new' or france.get('sha256') != source_hash
            or france.get('bytes') != len(source_raw) or france.get('feature_count') != 320
            or len(attempts) != 1 or attempts[0].get('sha256') != source_hash
            or attempts[0].get('bytes') != len(source_raw)
            or attempts[0].get('status') != 'expected-whole-sha-match'):
        fail('Original France retrieval observation does not bind to the complete source bytes')

    source_counts = collections.Counter(row.get('source_fitness_disposition') for row in run_components.values())
    if dict(sorted(source_counts.items())) != dict(sorted(run.get('source_fitness_disposition_counts', {}).items())):
        fail('Recorded source-fitness summary differs from all complete candidate records')
    relation_rows = []
    intersects = covers = 0
    for identity in expected_components:
        row = run_components[identity]
        relations = row.get('official_2026_whole_layer_relations', {}).get('exact_whole_feature_intersections')
        if not isinstance(relations, list):
            fail('Candidate is missing its complete retained whole-layer relation list')
        hit = bool(relations)
        whole_cover = any(item.get('whole_feature_covers_full_subject') is True for item in relations)
        intersects += int(hit)
        covers += int(whole_cover)
        relation_rows.append({'component_id': identity, 'family_id': row.get('family_id'),
            'source_fitness_disposition': row.get('source_fitness_disposition'),
            'ign_2026_intersection_count': len(relations), 'ign_2026_whole_feature_cover': whole_cover,
            'inherited_physical_status': row.get('physical_status_record', {}).get('physical_status'),
            'surface_status': row.get('physical_status_record', {}).get('water_surface_status')})
    no_intersection = len(expected_components) - intersects

    contact_rows = []
    named = 0
    source_intersect = source_cover = atlas_intersect = atlas_cover = 0
    for identity in expected_contacts:
        row = run_contacts[identity]
        original_feature = row.get('complete_original_2022_source_feature')
        current_feature = row.get('complete_current_atlas_feature')
        if not isinstance(original_feature, dict) or not isinstance(current_feature, dict):
            fail('A full original/current contact feature is missing')
        props = original_feature.get('properties', {})
        shape_id = props.get('shapeID')
        expected_shape_id = identity.split(':')[-1]
        if shape_id != expected_shape_id or source_by_id.get(shape_id) != original_feature:
            fail('Contact identity/geometry does not match the complete retained 2022 source')
        if props.get('shapeType') != 'ADM3' or props.get('shapeGroup') != 'FRA':
            fail('Contact source role differs from the retained French ADM3 source')
        current_props = current_feature.get('properties', {})
        if current_feature.get('id') != identity or current_props.get('id') != identity:
            fail('Current Atlas contact feature identity differs from issue scope')
        names = row.get('official_2026_exact_name_identity_candidates')
        if not isinstance(names, list):
            fail('Contact exact-name leads are missing')
        named += int(bool(names))
        source_rel = row.get('official_2026_original_source_whole_layer_relations', {}).get('exact_whole_feature_intersections')
        atlas_rel = row.get('official_2026_current_atlas_whole_layer_relations', {}).get('exact_whole_feature_intersections')
        if not isinstance(source_rel, list) or not isinstance(atlas_rel, list):
            fail('Contact relation lists are missing')
        for relation in (row['official_2026_original_source_whole_layer_relations'],
                         row['official_2026_current_atlas_whole_layer_relations']):
            if relation.get('whole_source_features_scanned') != 333:
                fail('Contact comparison did not record all 333 whole IGN features')
        source_hit = bool(source_rel); atlas_hit = bool(atlas_rel)
        source_whole = any(x.get('whole_feature_covers_full_subject') is True for x in source_rel)
        atlas_whole = any(x.get('whole_feature_covers_full_subject') is True for x in atlas_rel)
        source_intersect += int(source_hit); source_cover += int(source_whole)
        atlas_intersect += int(atlas_hit); atlas_cover += int(atlas_whole)
        metadata = current_props.get('metadata', {})
        contact_rows.append({'subject_id': identity, 'source_shape_name': props.get('shapeName'),
            'source_shape_type': props.get('shapeType'), 'source_group': props.get('shapeGroup'),
            'source_parent_identity': 'not present in retained geoBoundaries feature properties',
            'atlas_name': current_props.get('name'), 'atlas_parent_id': current_props.get('parent_id'),
            'atlas_parent_source_level': metadata.get('parent_source_level'),
            'exact_2026_name_candidates': sorted({x.get('name') for x in names if isinstance(x, dict)}),
            'original_source_2026_intersection_names': sorted({x.get('name') for x in source_rel if isinstance(x, dict)}),
            'original_source_2026_whole_covers': int(source_whole),
            'current_atlas_2026_intersection_names': sorted({x.get('name') for x in atlas_rel if isinstance(x, dict)}),
            'current_atlas_2026_whole_covers': int(atlas_whole),
            'identity_limit': row.get('identity_limit')})

    metrics = {
        'family_count': len(run_families), 'candidate_count': len(run_components),
        'contact_count': len(run_contacts), 'original_source_record_count': len(source_by_id),
        'official_2026_feature_count': run['official_layer_roster']['features'],
        'compatible_recorded_subjects': source_counts.get('compatible-original-subject-recorded', 0),
        'partial_or_unbound_original_source': source_counts.get('partial-or-unbound-original-source-unknown', 0),
        'no_compatible_original_intersection': source_counts.get('no-compatible-original-source-intersection-unknown', 0),
        'outside_original_source_domain': source_counts.get('outside-original-source-domain-unknown', 0),
        'official_2026_intersect': intersects, 'official_2026_whole_feature_cover': covers,
        'official_2026_intersect_without_cover': intersects - covers, 'official_2026_no_intersection': no_intersection,
        'exact_current_contact_name_match': named,
        'inherited_mapped_land_support': sum(x.get('physical_status_record', {}).get('physical_status') == 'mapped-land-support' for x in run_components.values()),
        'inherited_outside_l1_context': sum(x.get('physical_status_record', {}).get('physical_status') == 'outside-mapped-L1-context' for x in run_components.values()),
        'unverified_surface': sum(x.get('physical_status_record', {}).get('water_surface_status') == 'unverified' for x in run_components.values()),
        'contacts_with_2022_geometry_intersection_2026': source_intersect,
        'contacts_with_2022_geometry_whole_cover_2026': source_cover,
        'contacts_with_current_atlas_geometry_intersection_2026': atlas_intersect,
        'contacts_with_current_atlas_geometry_whole_cover_2026': atlas_cover}
    old_metrics = load_json(pinned(ctx, ORIGINAL + 'summary-metrics.json'), 'frozen original summary')
    old_values = old_metrics.get('values')
    if not isinstance(old_values, dict) or old_values != metrics:
        fail('Fresh derivation differs from the frozen summary metrics; preserve and investigate the discrepancy')
    stale_phrases = [phrase for phrase in run.get('methods', {}).get('limits', [])
                     if isinstance(phrase, str) and 'Four candidate pointsets have no intersection' in phrase]
    if len(stale_phrases) != 1:
        fail('The exact stale four-no-intersection narrative was not found once')
    return {'metrics': metrics, 'candidates': relation_rows, 'contacts': contact_rows,
            'run_sha256': sha(run1_raw), 'run_bytes': len(run1_raw),
            'source_sha256': source_hash, 'source_bytes': len(source_raw),
            'source_encoded_sha256': sha(source_encoded), 'source_encoded_bytes': len(source_encoded),
            'source_retrieval_started_utc': attempts[0]['started_utc'],
            'source_retrieval_finished_utc': attempts[0]['finished_utc'],
            'source_retrieval_url': attempts[0]['resolved_url'],
            'source_product': source_product, 'old_limit': stale_phrases[0],
            'current_atlas_subject_count': len(expected_atlas_subjects),
            'run_contract': old_contract}


def make_markdown(result):
    m = result['metrics']
    rows = [
        '# Additive reporting erratum: France source-fitness packet', '',
        'This correction applies only to reporting derived from the immutable complete runs in original issue #1310. It does not alter those runs or certify French boundaries.', '',
        '## Corrections', '',
        f'- The full retained candidate relation records yield **{m["official_2026_no_intersection"]}** candidate pointsets with no 2026 IGN whole-layer intersection, not four. The remaining candidates yield {m["official_2026_intersect"]} intersections: {m["official_2026_whole_feature_cover"]} whole-feature covers and {m["official_2026_intersect_without_cover"]} intersections without whole-feature cover.',
        '- The exact counts above are recalculated from all 48 complete retained candidate relation records and reconciled to the original frozen summary. The original `run-contract.json` limit phrase is stale; it is preserved unchanged.',
        f'- For all {m["contact_count"]} complete original 2022 source contact geometries and all {m["contact_count"]} complete current Atlas contact geometries, the retained run records comparison against the complete 333-feature 2026 IGN layer: {m["contacts_with_2022_geometry_intersection_2026"]}/{m["contact_count"]} and {m["contacts_with_current_atlas_geometry_intersection_2026"]}/{m["contact_count"]} intersect; whole-feature covers are {m["contacts_with_2022_geometry_whole_cover_2026"]} and {m["contacts_with_current_atlas_geometry_whole_cover_2026"]}. The previous methods sentence understated this by describing only exact-name identity leads.',
        f'- Exact-name identity candidates are present for {m["exact_current_contact_name_match"]}/{m["contact_count"]} contacts. Names remain leads; no one-to-one identity or boundary crosswalk is inferred.',
        '', '## Preserved source meaning and limits', '',
        f'- The complete retained geoBoundaries source body is {result["source_bytes"]} decoded bytes, SHA-256 `{result["source_sha256"]}`, and contains {m["original_source_record_count"]} unique French `ADM3` records. The pinned original transport receipt records retrieval {result["source_retrieval_started_utc"]} through {result["source_retrieval_finished_utc"]} from {result["source_retrieval_url"]}. Its corpus catalogue records represented year 2022 and Etalab Open Licence 2.0 metadata; geoBoundaries separately states CC-BY 4.0 for derivative products. The source record itself does not provide a parent ID in its feature properties. These recorded terms do not resolve the underlying-source rights chain or establish legal boundary authority.',
        f'- The comparison layer is `ADMINEXPRESS-COG.2026`, edition 2026-01-01, retrieved 2026-10-07. Its exact 156,850,437-byte source is restoration-only because it exceeds the repository 32 MiB file limit; this erratum reuses the complete retained run relations and does not substitute a clipped or filtered layer.',
        f'- The retained source-fitness dispositions remain {m["compatible_recorded_subjects"]} compatible recorded subjects, {m["partial_or_unbound_original_source"]} partial/unbound cases, {m["no_compatible_original_intersection"]} no-compatible-intersection cases, and {m["outside_original_source_domain"]} outside-domain cases. These remain source-fit dispositions, not factual boundary conclusions.',
        f'- The inherited physical summary remains {m["inherited_mapped_land_support"]} mapped-land-support records, {m["inherited_outside_l1_context"]} outside-L1 records and {m["unverified_surface"]} unverified surface statuses. Physical-source license, coverage, observation dates and physical authority remain unresolved.',
        '- This work independently verifies the arithmetic and identity correspondence of the retained complete run records and checks all 16 original contact features against the authenticated complete 2022 source bytes. It does not rerun the 156 MB 2026 spatial overlay, independently establish its intersections, certify France, change any parent/boundary, approve source rights, or complete original issue #1329.',
        '', '## Reproduction and exact inputs', '',
        f'- Both frozen full result files are byte-identical, SHA-256 `{result["run_sha256"]}` ({result["run_bytes"]} bytes each). The new CLI binds this whole hash, the issue-declared pins, the complete original source, its own code hash and the shared pinned writer helper in each fresh publication receipt.',
        '- Run the documented `report.py run --repo <checkout> --vintage <fresh-name>` command twice with distinct fresh names. The control CLI records adverse cases separately; all failed and partial attempts remain failed.',
        '', 'Sources retained by original issue #1310:', '',
        '- geoBoundaries France ADM3 simplified source, pinned upstream revision `9469f09`: https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/FRA/ADM3/geoBoundaries-FRA-ADM3_simplified.geojson',
        '- geoBoundaries derivative citation and attribution terms: https://www.geoboundaries.org',
        '- IGN ADMINEXPRESS-COG.2026 product context and French Open Licence catalogue references are preserved in the original packet README; see https://geoservices.ign.fr/ and https://www.data.gouv.fr/datasets/admin-express-admin-express-cog-admin-express-cog-carto-admin-express-cog-carto-pe-admin-express-cog-carto-plus-pe',
        '- Source retrieval and file hashes are historical observations recorded in the original packet; no new source download occurred for this report correction.',
    ]
    return ('\n'.join(rows) + '\n').encode('utf-8')


def build_payloads(ctx, result):
    shared = ctx['shared']
    erratum = {'version': 1, 'issue': 1489, 'original_issue': 1310,
        'baseline_commit': ctx['baseline'].commit, 'original_run_sha256': result['run_sha256'],
        'original_run_bytes_each': result['run_bytes'],
        'scope': {'components': len(result['candidates']), 'families': len(result['run_contract']['scope']['family_ids']),
                  'contacts': len(result['contacts']), 'contact_ids_sha256': shared.sha256(json.dumps(sorted(ctx['evidence_contract']['subject_ids']), separators=(',', ':')).encode())},
        'metrics': result['metrics'], 'candidate_records': result['candidates'], 'contact_records': result['contacts'],
        'corrections': {'stale_run_contract_phrase': result['old_limit'],
            'correct_no_intersection_count': result['metrics']['official_2026_no_intersection'],
            'contact_method_correction': 'The original retained runs compare all 16 full 2022 source contact geometries and all 16 current Atlas contact geometries to the complete 333-feature 2026 IGN layer. Exact-name matches remain identity leads only; no boundary crosswalk is inferred.'},
        'source_context': {'source_path': SOURCE_PATH, 'source_sha256': result['source_sha256'],
            'source_decoded_bytes': result['source_bytes'], 'source_encoded_sha256': result['source_encoded_sha256'],
            'source_encoded_bytes': result['source_encoded_bytes'],
            'retrieval_started_utc': result['source_retrieval_started_utc'],
            'retrieval_finished_utc': result['source_retrieval_finished_utc'],
            'retrieval_url': result['source_retrieval_url'], 'represented_year_claim': '2022',
            'boundary_type': 'ADM3', 'recorded_metadata_license': 'Etalab Open Licence 2.0',
            'geoBoundaries_derivative_terms': 'CC-BY 4.0, attribution required',
            'source_parent_ids': 'not present in original source feature properties',
            'current_atlas_contact_subjects_verified': result['current_atlas_subject_count'],
            'territorial_and_underlying_rights_status': 'unresolved'},
        'limits': ['Retained run relations are arithmetically reconciled; the >32 MiB IGN layer was not restored or rerun.',
            'No source/legal/current-boundary authority or neighbor granularity approval is made.',
            'The original #1310 physical-source and 2022/2026 temporal-identity unknowns remain.',
            'Original #1329 remains Incomplete; this packet is not regional certification, import permission or publication.']}
    csvbuf = io.StringIO(newline='')
    writer = csv.writer(csvbuf, lineterminator='\n')
    writer.writerow(['component_id', 'family_id', 'original_source_fitness', 'ign_2026_intersection_count',
                     'ign_2026_whole_feature_cover', 'inherited_physical_status', 'surface_status'])
    for row in result['candidates']:
        writer.writerow([row['component_id'], row['family_id'], row['source_fitness_disposition'],
                         row['ign_2026_intersection_count'], str(row['ign_2026_whole_feature_cover']).lower(),
                         row['inherited_physical_status'], row['surface_status']])
    executed = {'version': 1, 'status': 'passed', 'issue': 1489, 'baseline_commit': ctx['baseline'].commit,
        'producer_path': OWNED + 'report.py', 'producer_sha256': ctx['producer_sha256'],
        'helper_path': HELPER_PATH, 'helper_sha256': ctx['by_path'][HELPER_PATH]['sha256'],
        'python_runtime': sys.version.split()[0], 'inputs': [ctx['by_path'][path] for path in sorted(ctx['by_path'])
            if path.startswith(ORIGINAL) or path in (SOURCE_PATH, CATALOGUE_PATH, PROGRESS_PATH, ATLAS_PART_PATH, HELPER_PATH)],
        'issue_snapshot_sha256': ctx['request']['issue_snapshot']['sha256'],
        'complete_phase_bytes_before_outputs': sum(ctx['baseline'].consumed.values()),
        'operation_limits': {'ordinary_or_decoded_bytes': MAX_FILE, 'whole_phase_bytes': MAX_PHASE},
        'derived_run_sha256': result['run_sha256'], 'source_decoded_sha256': result['source_sha256'],
        'geographic_result': 'No overlay recomputed; report arithmetic and contact-source identity reconciliation only.'}
    return {'erratum.json': shared.canonical_json(erratum), 'erratum.md': make_markdown(result),
            'candidate-reconciliation.csv': csvbuf.getvalue().encode('utf-8'),
            'execution.json': shared.canonical_json(executed)}


def fixture_path(ctx, path):
    if not path.startswith(OWNED + '.scratch/'):
        fail('Fixture input is permitted only inside the private owned .scratch directory')
    raw = read_owned(ctx['repo'], path)
    ctx['baseline'].admit('candidate:' + path, len(raw))
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default=str(Path(__file__).resolve().parents[3]))
    parser.add_argument('--request', default=OWNED + 'request.json')
    subs = parser.add_subparsers(dest='action', required=True)
    normal = subs.add_parser('run')
    normal.add_argument('--vintage', required=True)
    normal.add_argument('--expected-code-sha256')
    normal.add_argument('--test-fail-publication-receipt', action='store_true')
    fixture = subs.add_parser('check-fixture')
    fixture.add_argument('--run-one', required=True)
    fixture.add_argument('--run-two', required=True)
    args = parser.parse_args()
    if not args.request.startswith(OWNED):
        fail('Request snapshot must remain in the declared owned prefix')
    ctx = context(args.repo, args.request)
    if args.action == 'check-fixture':
        one = fixture_path(ctx, args.run_one)
        two = fixture_path(ctx, args.run_two)
        analyze(ctx, one, two)
        print(json.dumps({'status': 'accepted-control-inputs', 'publication': 'disabled'}))
        return 0
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', args.vintage):
        fail('Use a safe fresh vintage name')
    if args.expected_code_sha256 and args.expected_code_sha256 != ctx['producer_sha256']:
        fail('Producer code drifted from the separately captured expected SHA-256')
    if args.test_fail_publication_receipt and os.environ.get('WORLDATLAS_CONTROL_MODE') != '1':
        fail('Publication fault injection is restricted to the explicit control harness')
    # Reserve the entire output set before parsing/calculating the report.
    destination = ctx['shared'].NewVintage(ctx['baseline'], OWNED, args.vintage, OUTPUTS)
    run1 = pinned(ctx, ORIGINAL + 'verification/run-1.json')
    run2 = pinned(ctx, ORIGINAL + 'verification/run-2.json')
    result = analyze(ctx, run1, run2)
    payloads = build_payloads(ctx, result)
    if args.test_fail_publication_receipt:
        original_link = ctx['shared'].os.link
        def injected_link(source, target, *rest, **kwargs):
            if Path(target).name == 'publication.json':
                raise OSError('controlled failure before final publication receipt')
            return original_link(source, target, *rest, **kwargs)
        ctx['shared'].os.link = injected_link
    destination.publish_bytes(payloads)
    print(json.dumps({'status': 'complete', 'vintage': args.vintage,
                      'run_sha256': result['run_sha256'], 'producer_sha256': ctx['producer_sha256']}))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        raise SystemExit(1)
