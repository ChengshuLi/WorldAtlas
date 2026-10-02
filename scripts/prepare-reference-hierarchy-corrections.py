#!/usr/bin/env python3
"""Prepare three reviewed reference-only corrections; never install geography."""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
OUT = DATA / 'reference-hierarchy-corrections'
CONTINENTS = ('africa', 'asia', 'europe', 'north-america', 'oceania', 'south-america')
TIERS = ('location', 'province', 'area', 'region', 'subcontinent', 'continent')
MONACO = 'framework:area:france:a85924a668ef'
LUXEMBOURG = 'framework:area:belgium:3a14f80912de'
RETAIN = 'framework:province:west-virginia:4c9dc6438fb1'
RETIRE = 'framework:province:west-virginia:8d71dccb3165'
HANCOCK = 'gb:USA:ADM2:52423323B20661288428578'
FOOTPRINT_PIN = '5d7236fe7e9d2f83c07c0b5cc1d5e703bf685f860fd49c850edd18eea27c61a8'


def raw_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def chain(location, units):
    result = [{'id': location['id'], 'name': location['properties']['name'], 'level': 'location'}]
    parent = location['properties']['parent_id']
    while parent is not None:
        unit = units[parent]
        require(unit['level'] == TIERS[len(result)], f'Non-adjacent chain: {location["id"]}')
        result.append({k: unit[k] for k in ('id', 'name', 'level')})
        parent = unit['parent_id']
    require(len(result) == 6, f'Incomplete chain: {location["id"]}')
    return result


def inventories(features, units):
    members = {key: [] for key in units}
    chains = {}
    for location in features:
        chains[location['id']] = chain(location, units)
        for row in chains[location['id']][1:]:
            members[row['id']].append(location['id'])
    for key, ids in members.items():
        ids.sort()
        require(ids, f'Empty active group: {key}')
    return members, chains


def member_proof(ids, geometries):
    pairs = [[key, geometries[key]] for key in ids]
    # Existing follow-up ledgers use Python's ASCII-escaped compact JSON here.
    return {'member_location_ids': ids,
            'membership_sha256': sha(json.dumps(ids, separators=(',', ':')).encode()),
            'footprint_sha256': sha(json.dumps(pairs, separators=(',', ':')).encode())}


def footprint_hash(directory):
    code = """import fs from 'node:fs';
import {footprintHash} from './scripts/check-prepared.mjs';
const base=process.argv[1],index=JSON.parse(fs.readFileSync(base+'/world-index.json'));
console.log(footprintHash(index.parts.flatMap(p=>JSON.parse(fs.readFileSync(base+'/'+p)).features)));
"""
    return subprocess.check_output(['node', '--input-type=module', '-e', code, str(directory)],
                                   cwd=ROOT, text=True).strip()


def write_gzip(name, value, check):
    target = OUT / name
    raw = gzip.compress(raw_json(value), compresslevel=9, mtime=0)
    require(len(raw) < 16 * 1024 * 1024, f'Archive exceeds repository mirror limit: {name}')
    if check:
        require(target.exists() and target.read_bytes() == raw, f'Non-reproducible archive: {name}')
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return {'path': str(target.relative_to(ROOT)), 'sha256': sha(raw), 'bytes': len(raw),
            'uncompressed_sha256': sha(raw_json(value))}


def prepare(check=False):
    pins = {}

    def pinned(path):
        relative = str(path.relative_to(ROOT))
        raw = path.read_bytes()
        pins[relative] = sha(raw)
        return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)

    index = pinned(DATA / 'world-index.json')
    hierarchy = pinned(DATA / 'hierarchy.json')
    before = {row['id']: row for row in hierarchy}
    require(len(before) == len(hierarchy) == 5705, 'Current hierarchy identity inventory changed')
    reports = {name: pinned(DATA / f'geographic-semantic-followup/{name}.json.gz') for name in CONTINENTS}
    closure = pinned(DATA / 'global-semantic-closure.json.gz')
    gate = pinned(DATA / 'validation/geographic-semantic-followup.json')
    for name, report in reports.items():
        continent = report['continent']
        require(gate['report_sha256'][continent] == pins[f'data/geographic-semantic-followup/{name}.json.gz'],
                f'Follow-up report no longer matches the exhaustive global gate: {continent}')
    # Historical payloads are neither read for reassignment nor copied into the candidate.
    for path in [DATA / 'hosted-catalog/index.json', DATA / 'ownership-history/index.json',
                 DATA / 'ownership-runtime/index.json', DATA / 'reference-attributes/index.json',
                 DATA / 'geographic-decision-migration.json.gz', DATA / 'macro-boundary-migration.json.gz',
                 DATA / 'geographic-repair-evidence/migration-receipt.json.gz']:
        pinned(path)
    features, parts = [], {}
    for filename in index['parts']:
        part = pinned(DATA / filename)
        parts[filename] = part
        features.extend(part['features'])
    by_id = {row['id']: row for row in features}
    require(len(by_id) == len(features) == 49589, 'Current location identity inventory changed')
    geometry_hashes = {row['id']: sha(json.dumps(row['geometry'], sort_keys=True,
                      separators=(',', ':')).encode()) for row in features}
    closed_hashes = {row['id']: row['footprint_sha256'] for row in closure['locations']}
    require(geometry_hashes == closed_hashes, 'Original geometry differs from exhaustive closure evidence')
    old_members, old_chains = inventories(features, before)
    europe, america = reports['europe'], reports['north-america']
    proposals = {row['id']: row for row in europe['proposals']}
    monaco = proposals['europe:area-label:monaco']
    lux = proposals['europe:area-label:luxembourg']
    wv = next(row for row in america['proposals'] if row['id'] == 'americas:province-family:dff0938a999e70a4')
    correction = wv['specific_supported_correction']
    require(correction['retain_group_id'] == RETAIN and correction['retire_group_id'] == RETIRE
            and correction['reparent_location_ids'] == [HANCOCK], 'West Virginia source proposal changed')
    for proposal, entity, name, original_name in [(monaco, MONACO, 'Monaco', 'France'),
                                                (lux, LUXEMBOURG, 'Luxembourg', 'Belgium')]:
        require(proposal['entity_ids'] == [entity] and proposal['proposed_name'] == name,
                f'Label proposal identity changed: {entity}')
        require(before[entity]['name'] == original_name and before[entity]['level'] == 'area',
                f'Correction already installed or baseline changed: {entity}')
        require(old_members[entity] == proposal['location_ids'] and len(old_members[entity]) == 1,
                f'Area no longer has exact sole-member source scope: {entity}')
        require(by_id[old_members[entity][0]]['properties']['name'] == name,
                f'Sole-member identity changed: {entity}')
    require(before[RETAIN]['parent_id'] == before[RETIRE]['parent_id']
            and wv['same_area_parent'] is True,
            'West Virginia portions no longer share one geographic area')
    require(old_members[RETIRE] == [HANCOCK] and len(old_members[RETAIN]) == 54,
            'West Virginia source-member inventory changed')
    require(by_id[HANCOCK]['properties']['name'] == 'Hancock', 'Hancock location identity changed')
    for portion in wv['current_portions']:
        entity = portion['id']
        require(old_members[entity] == sorted(portion['member_location_ids']), 'Stale portion members')
        proof = member_proof(old_members[entity], geometry_hashes)
        require(proof['footprint_sha256'] == portion['footprint_sha256'], 'Stale portion footprint')
        diagnostic = portion['original_source_parent_diagnostic']
        require(diagnostic == america['source_evidence']['original_parent_geometry_diagnostics'][entity],
                'Source-parent diagnostic mismatch')
        require(diagnostic['current_group_footprint_sha256'] == proof['footprint_sha256'],
                'Source-parent diagnostic footprint mismatch')
        require(diagnostic['exact_name_candidate_count'] == 1
                and diagnostic['source_id'] == 'gb:USA:ADM1', 'Ambiguous original source parent')
        original = diagnostic['original_parent_candidates'][0]
        require(original['original_source_properties'] == {
            'shapeName': 'West Virginia', 'shapeISO': 'US-WV',
            'shapeID': '66186276B64762166704956', 'shapeGroup': 'USA', 'shapeType': 'ADM1'},
            'Portions have different original source parents')
        require(original['geometry_sha256'] == 'a3569955c5429a57b618f4bb0a84ede2ad84d7ddab580fee2edafa4c079221b3'
                and original['current_member_source_overlap_share'] > 0.99,
                'Original source-parent footprint identity or high overlap changed')
        require(sorted(row['id'] for row in original['member_matches']) == old_members[entity],
                'Original source-parent matches do not exhaustively account for the portion')
    registry = america['source_evidence']['west_virginia_official_county_registry']
    county_ids = sorted(old_members[RETAIN] + old_members[RETIRE])
    current_names = sorted(by_id[key]['properties']['name'] for key in county_ids)
    registry_names = sorted(row['NAME'].removesuffix(' County') for row in registry['rows'])
    require(len(set(current_names)) == len(set(registry_names)) == 55 and current_names == registry_names,
            'All 55 current counties do not match the independent official registry')
    census = next(row for row in america['source_evidence']['public_source_receipts']
                  if row['id'] == registry['source_evidence_id'])
    monaco_receipt = europe['source_evidence']['official_requests']['monaco']
    nuts_receipt = europe['source_evidence']['official_requests']['nuts_labels']
    for receipt in [census, monaco_receipt, nuts_receipt]:
        require(receipt.get('status') == 200 and len(receipt.get('sha256', '')) == 64,
                'Proposal lacks an inspected successful source receipt')
    labels = [row for row in europe['source_evidence']['official_labels'] if row['iso3'] == 'LUX']
    require({row['code'] for row in labels} == {'LU', 'LU0', 'LU00', 'LU000'}
            and all(row['name'] == 'Luxembourg' for row in labels), 'GISCO Luxembourg identity changed')
    after = copy.deepcopy(before)
    for proposal, entity in [(monaco, MONACO), (lux, LUXEMBOURG)]:
        after[entity]['name'] = proposal['proposed_name']
        after[entity]['metadata']['reference_hierarchy_correction'] = {
            'proposal_id': proposal['id'], 'before_name': before[entity]['name'],
            'reference_only': True, 'semantic_approval': False,
            'basis': 'Atlas reference label normalized to the exact sole member; original source metadata retained'}
    after[RETAIN]['metadata']['child_count'] = 55
    after[RETAIN]['metadata']['reference_hierarchy_correction'] = {
        'proposal_id': wv['id'], 'reference_only': True, 'semantic_approval': False,
        'basis': 'Same named original US-WV parent and exact 55-county official inventory',
        'retired_parent_id': RETIRE}
    del after[RETIRE]
    shared_area = before[RETAIN]['parent_id']
    area_children = [key for key, row in after.items() if row['parent_id'] == shared_area]
    after[shared_area]['metadata']['child_count'] = len(area_children)
    candidate_features = [copy.deepcopy(row) if row['id'] == HANCOCK else row for row in features]
    changed = next(row for row in candidate_features if row['id'] == HANCOCK)
    changed['properties']['parent_id'] = RETAIN
    new_members, new_chains = inventories(candidate_features, after)
    require(new_members[RETAIN] == county_ids and new_members[shared_area] == old_members[shared_area],
            'Parent merge changes an area footprint')
    require({row['id'] for row in candidate_features} == set(by_id), 'Unexpected location identity change')
    require(all(row['geometry'] == by_id[row['id']]['geometry'] for row in candidate_features),
            'Unexpected original location geometry mutation')
    affected_locations = sorted(set(county_ids + monaco['location_ids'] + lux['location_ids']))
    affected_groups = sorted({row['id'] for key in affected_locations for row in old_chains[key][1:]})
    changed_groups = [{'id': key, 'before': before[key], 'after': after.get(key)}
                      for key in sorted(before) if before[key] != after.get(key)]
    candidate = ROOT / '.cache/reference-hierarchy-corrections/geography'
    candidate.mkdir(parents=True, exist_ok=True)
    for filename in ['world-index.json'] + index['parts']:
        target = candidate / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DATA / filename, target)
    changed_part = next(filename for filename, part in parts.items()
                        if any(row['id'] == HANCOCK for row in part['features']))
    # Replace only the unique original parent token; all geometry bytes stay exact.
    raw = (candidate / changed_part).read_bytes()
    require(raw.count(RETIRE.encode()) == 1, 'Parent token is not uniquely scoped to Hancock')
    (candidate / changed_part).write_bytes(raw.replace(RETIRE.encode(), RETAIN.encode()))
    actual_candidate = read(candidate / changed_part)
    require(actual_candidate['features'] == [changed if row['id'] == HANCOCK else row
            for row in parts[changed_part]['features']], 'Unexpected candidate part alteration')
    (candidate / 'hierarchy.json').write_bytes(raw_json([after[row['id']] for row in hierarchy if row['id'] in after]))
    require(footprint_hash(DATA) == footprint_hash(candidate) == FOOTPRINT_PIN,
            'Canonical prepared location footprint hash changed')
    candidate_pins = {filename: sha((candidate / filename).read_bytes())
                      for filename in ['hierarchy.json', 'world-index.json'] + index['parts']}
    counts = lambda units: {tier: 49589 if tier == 'location' else
                           sum(row['level'] == tier for row in units.values()) for tier in TIERS}
    source_proof = {'monaco': {'proposal': monaco, 'official_receipt': monaco_receipt},
                    'luxembourg': {'proposal': lux, 'official_receipt': nuts_receipt, 'official_labels': labels},
                    'west_virginia': {'proposal': wv, 'official_receipt': census, 'official_registry': registry,
                                     'all_55_current_location_ids': county_ids, 'all_55_current_names': current_names},
                    'limitations': ['Existing pinned inspections reused; no source bytes refetched',
                                    'Named source-parent matching supports this reference correction only',
                                    'Local granularity, state cluster purpose and historic administration remain open']}
    receipt = {'version': 1, 'reference_only': True, 'status': 'candidate-not-installed',
               'semantic_complete': False, 'semantic_approvals_created': 0,
               'scope': 'Two identity-preserving area reference renames and one same-tier parent consolidation',
               'input_sha256': pins, 'preparation_script_sha256': sha(Path(__file__).read_bytes()),
               'before_sha256': pins['data/hierarchy.json'], 'after_sha256': candidate_pins['hierarchy.json'],
               'footprints_sha256_before': FOOTPRINT_PIN, 'footprints_sha256_after': FOOTPRINT_PIN,
               'before_units': [before[row['id']] for row in hierarchy], 'retired_units': [before[RETIRE]],
               'new_group_ids': [], 'group_changes': changed_groups,
               'changed_location_properties': [{'location_id': HANCOCK,
                    'before_properties': by_id[HANCOCK]['properties'], 'after_properties': changed['properties']}],
               'location_chain_crosswalk': [{'location_id': key, 'before_chain': old_chains[key],
                    'after_chain': new_chains[key], 'chain_changed': old_chains[key] != new_chains[key]}
                    for key in affected_locations],
               'affected_group_footprints': [{'id': key, 'before': member_proof(old_members[key], geometry_hashes),
                    'after': member_proof(new_members[key], geometry_hashes) if key in after else None}
                    for key in affected_groups],
               'unchanged_geometry_ids': sorted(by_id), 'unchanged_geometry_sha256': FOOTPRINT_PIN,
               'historical_claims_transferred': False, 'historical_claims_changed': False,
               'relationships': [{'old_entity_id': RETIRE, 'new_entity_id': RETAIN, 'change_type': 'merge',
                    'reference_only': True, 'history_transfer': 'none', 'proposal_id': wv['id']}],
               'source_evidence': [{'url': row['url'], 'source_sha256': row['sha256'],
                    'inspected_fact': row['inspected_fact'], 'reference_only': True}
                    for row in [monaco_receipt, nuts_receipt, census]],
               'counts': {'before': counts(before), 'after': counts(after)},
               'summary': {'geometry_changes': 0, 'new_location_ids': 0, 'retired_location_ids': 0,
                    'area_reference_renames': 2, 'reparented_locations': 1, 'retired_provinces': 1,
                    'changed_group_records': len(changed_groups), 'affected_location_ids': len(affected_locations),
                    'affected_group_ids': len(affected_groups),
                    'changed_location_chains': sum(old_chains[key] != new_chains[key] for key in by_id)},
               'candidate': {'directory': '.cache/reference-hierarchy-corrections/geography',
                    'files_sha256': candidate_pins, 'changed_geography_part': changed_part},
               'publication_gates_remaining': ['Technical-maintainer review and explicit merge crosswalk in release',
                    'Retain retired parent identity and immutable historical claims; publish new reference version',
                    'Member-derived parent boundaries and matching static/server release pins',
                    'Whole-global semantic review remains open independently of these three corrections']}
    # Reject any concurrent source mutation; these artifacts describe one exact input snapshot.
    for filename, expected in pins.items():
        require(sha((ROOT / filename).read_bytes()) == expected, f'Input changed during preparation: {filename}')
    proof_pin = write_gzip('source-proof.json.gz', source_proof, check)
    receipt['source_proof'] = proof_pin
    receipt_pin = write_gzip('migration-receipt.json.gz', receipt, check)
    print(json.dumps({'status': receipt['status'], 'summary': receipt['summary'], 'counts': receipt['counts'],
                      'archives': [proof_pin, receipt_pin]}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify deterministic committed archives without rewriting them')
    prepare(parser.parse_args().check)
