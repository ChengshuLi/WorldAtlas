#!/usr/bin/env python3
"""Rebase frozen reference corrections into a separate immutable-baseline candidate."""
import argparse
import copy
import gzip
import io
import json
from pathlib import Path
import re
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.immutable import Baseline, VERSION, canonical_json, deterministic_gzip, descriptor, sha256

PREFIX = 'data/reference-hierarchy-corrections/'
MONACO = 'framework:area:france:a85924a668ef'
LUX = 'framework:area:belgium:3a14f80912de'
RETAIN = 'framework:province:west-virginia:4c9dc6438fb1'
RETIRE = 'framework:province:west-virginia:8d71dccb3165'
AREA = 'framework:area:south-atlantic:383dc695ee31'
HANCOCK = 'gb:USA:ADM2:52423323B20661288428578'
GROUPS = {MONACO, LUX, RETAIN, RETIRE, AREA}
TIERS = ('location', 'province', 'area', 'region', 'subcontinent', 'continent')


def require(value, message):
    if not value:
        raise ValueError(message)


def unpack(raw):
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        result = stream.read(32 * 1024 * 1024 + 1)
    require(len(result) <= 32 * 1024 * 1024, 'Expanded input exceeds byte budget')
    return result


def inventory(features, units):
    groups = {u['id']: u for u in units}
    require(len(groups) == len(units), 'Duplicate group identity')
    members = {identity: [] for identity in groups}
    chains = {}
    for feature in features:
        identity = feature['id']
        require(identity == feature['properties']['id'] and identity not in chains,
                'Duplicate or inconsistent location identity')
        chain = [{'id': identity, 'name': feature['properties']['name'], 'level': 'location'}]
        parent = feature['properties']['parent_id']
        for tier in TIERS[1:]:
            unit = groups.get(parent)
            require(unit is not None and unit['level'] == tier, 'Incomplete adjacent-tier chain')
            members[parent].append(identity)
            chain.append({key: unit[key] for key in ('id', 'name', 'level')})
            parent = unit['parent_id']
        require(parent is None, 'Continent must have no parent')
        chains[identity] = chain
    require(all(members.values()), 'Empty active group')
    require(sum(u['level'] == 'continent' for u in units) == 6, 'Six continents required')
    return {key: sorted(ids) for key, ids in members.items()}, chains


def member_proof(ids, geometries):
    # Match the frozen proposal's legacy ASCII JSON / no-newline digest contract.
    digest = lambda value: sha256(json.dumps(value, separators=(',', ':')).encode())
    return {'member_location_ids': ids, 'membership_sha256': digest(ids),
            'footprint_sha256': digest([[identity, geometries[identity]] for identity in ids])}


def apply_corrections(units, features, proposal):
    before = {u['id']: u for u in units}
    changes = proposal['group_changes']
    require(len(changes) == 5 and {r['id'] for r in changes} == GROUPS,
            'Only the exact five frozen group changes are permitted')
    require(proposal['reference_only'] is True and proposal['historical_claims_changed'] is False
            and proposal['historical_claims_transferred'] is False, 'Reference-only proposal required')
    expected_relation = {'change_type': 'merge', 'history_transfer': 'none',
                         'new_entity_id': RETAIN, 'old_entity_id': RETIRE,
                         'proposal_id': 'americas:province-family:dff0938a999e70a4', 'reference_only': True}
    require(proposal['relationships'] == [expected_relation], 'Frozen merge relationship changed')
    for row in changes:
        require(before.get(row['id']) == row['before'], 'Proposal before record no longer matches: ' + row['id'])
    rows = proposal['changed_location_properties']
    require(len(rows) == 1 and rows[0]['location_id'] == HANCOCK, 'Only Hancock may change parent')
    locations = {f['id']: f for f in features}
    require(locations.get(HANCOCK, {}).get('properties') == rows[0]['before_properties'],
            'Original Hancock properties changed')
    expected = copy.deepcopy(rows[0]['before_properties'])
    expected['parent_id'] = RETAIN
    require(rows[0]['after_properties'] == expected, 'Non-parent Hancock mutation')
    after = copy.deepcopy(before)
    for row in changes:
        if row['after'] is None:
            del after[row['id']]
        else:
            after[row['id']] = copy.deepcopy(row['after'])
    candidate = [copy.deepcopy(f) if f['id'] == HANCOCK else f for f in features]
    for feature in candidate:
        if feature['id'] == HANCOCK:
            feature['properties'] = expected
    return [after[u['id']] for u in units if u['id'] in after], candidate


def prepare(repo, request, output):
    require(request['version'] == 1 and request['issue'] == 6, 'Wrong preparation request')
    baseline = Baseline(repo, request['baseline']['commit'], request['baseline']['files'])
    def read(name):
        require(name in baseline.pins, 'Undeclared input: ' + name)
        return baseline.read(name)
    def load(name):
        raw = read(name)
        return json.loads(unpack(raw) if name.endswith('.gz') else raw)
    index = load('data/world-index.json')
    units = load('data/hierarchy.json')
    original = load(PREFIX + 'migration-receipt.json.gz')
    proof_raw = read(PREFIX + 'source-proof.json.gz')
    require(original['source_proof']['sha256'] == sha256(proof_raw), 'Frozen source proof changed')
    # Resolve the append-only extension rather than assuming raw index is current.
    prior = load('data/geographic-releases/index.json')
    pointer = load('data/geographic-releases/current-manifest.json')
    require(pointer['predecessor_index_sha256'] == sha256(read('data/geographic-releases/index.json')),
            'Manifest predecessor pin changed')
    extended_raw = read('data/geographic-releases/' + pointer['path'])
    require(sha256(extended_raw) == pointer['sha256'], 'Current manifest pin changed')
    manifest = json.loads(unpack(extended_raw))
    require(manifest['releases'][:len(prior['releases'])] == prior['releases'], 'Prior releases changed')
    release = manifest['releases'][-1]
    gate = load('data/research-geography-gate.json')
    approved = gate['macro_boundaries']['approved_release']
    require(gate['macro_boundaries']['publication_verified'] is True and
            all(release[key] == approved[key] for key in ('id', 'version', 'hierarchy_sha256', 'footprints_sha256')),
            'Latest retained published release and gate disagree')
    require(sha256(read('data/hierarchy.json')) == release['hierarchy_sha256'], 'Active hierarchy differs from release')
    part_bytes = {name: read('data/' + name) for name in index['parts']}
    parts = {name: json.loads(raw) for name, raw in part_bytes.items()}
    features = [feature for part in parts.values() for feature in part['features']]
    members, chains = inventory(features, units)
    counts = {tier: len(features) if tier == 'location' else sum(u['level'] == tier for u in units) for tier in TIERS}
    require(counts == release['expected_counts'], 'Current inventories disagree with published release')
    geometries = {f['id']: sha256(json.dumps(f['geometry'], sort_keys=True, separators=(',', ':')).encode()) for f in features}
    old_proofs = {r['id']: r['before'] for r in original['affected_group_footprints']}
    for identity in GROUPS:
        require(member_proof(members[identity], geometries) == old_proofs[identity],
                'Affected source territory changed: ' + identity)
    require(len(members[RETAIN]) == 54 and members[RETIRE] == [HANCOCK], 'Exact WV partition required')
    after_units, after_features = apply_corrections(units, features, original)
    after_members, after_chains = inventory(after_features, after_units)
    changed_chains = sorted(identity for identity in chains if chains[identity] != after_chains[identity])
    require(changed_chains == sorted([HANCOCK, members[MONACO][0], members[LUX][0]]),
            'Unexpected changed location chain')
    require(after_members[RETAIN] == sorted(members[RETAIN] + [HANCOCK]) and
            after_members[AREA] == members[AREA], 'Merge does not preserve containing membership')
    grid = load('data/canonical-grid/manifest.json')
    require(grid['hierarchy_sha256'] == release['hierarchy_sha256'] and
            grid['footprints_sha256'] == release['footprints_sha256'], 'Grid baseline is stale')
    ownership = []
    for part in grid['parts']:
        name = 'data/canonical-grid/' + part['path']
        raw = read(name)
        require(sha256(raw) == part['sha256'], 'Canonical ownership part changed')
        ownership.append(descriptor(name, raw))
    require(not output.exists(), 'Fresh separate output directory required')
    repo_path = Path(repo).resolve()
    require(output.resolve() != repo_path / 'data' and not output.resolve().is_relative_to(repo_path / 'data'),
            'Do not install candidate into active data')
    output.mkdir(parents=True)
    geography = output / 'geography'
    geography.mkdir()
    (geography / 'world-index.json').write_bytes(read('data/world-index.json'))
    (geography / 'hierarchy.json').write_bytes(canonical_json(after_units))
    mutated = []
    for name, raw in part_bytes.items():
        if any(f['id'] == HANCOCK for f in parts[name]['features']):
            pattern = rb'("parent_id"\s*:\s*)"' + RETIRE.encode() + rb'"'
            raw, replacements = re.subn(pattern, lambda match: match[1] + b'"' + RETAIN.encode() + b'"', raw)
            require(replacements == 1, 'Exactly one parent text replacement required')
            part_ids = {x['id'] for x in parts[name]['features']}
            expected = [f for f in after_features if f['id'] in part_ids]
            require(json.loads(raw)['features'] == expected, 'Unreceipted part mutation')
            mutated.append(name)
        target = geography / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    # Verify the actual candidate geometry digest with the established JS contract.
    helper = 'scripts/check-prepared.mjs'
    require(sha256((Path(repo) / helper).read_bytes()) == sha256(read(helper)), 'Footprint helper checkout changed')
    code = """import fs from 'node:fs';import {footprintHash} from './scripts/check-prepared.mjs';
const base=process.argv[1],index=JSON.parse(fs.readFileSync(base+'/world-index.json'));
console.log(footprintHash(index.parts.flatMap(p=>JSON.parse(fs.readFileSync(base+'/'+p)).features)));"""
    actual_footprints = subprocess.check_output(['node', '--input-type=module', '-e', code, str(geography.resolve())], cwd=repo, text=True).strip()
    require(actual_footprints == release['footprints_sha256'], 'Candidate geometry differs from published release')
    affected = sorted(set(members[RETAIN] + members[RETIRE] + members[MONACO] + members[LUX]))
    ancestors = sorted({r['id'] for identity in affected for r in chains[identity][1:]})
    receipt = copy.deepcopy(original)
    receipt.update(before_units=units, before_sha256=release['hierarchy_sha256'],
                   after_sha256=sha256((geography / 'hierarchy.json').read_bytes()),
                   footprints_sha256_before=release['footprints_sha256'], footprints_sha256_after=release['footprints_sha256'],
                   unchanged_geometry_ids=sorted(geometries), unchanged_geometry_sha256=release['footprints_sha256'],
                   location_chain_crosswalk=[{'location_id': identity, 'before_chain': chains[identity],
                                             'after_chain': after_chains[identity]} for identity in affected],
                   affected_group_footprints=[{'id': identity, 'before': member_proof(members[identity], geometries),
                                              'after': member_proof(after_members[identity], geometries) if identity in after_members else None} for identity in ancestors],
                   status='rebased-candidate-not-installed', input_sha256={name: pin['sha256'] for name, pin in baseline.pins.items()},
                   helper_version=VERSION, original_proposal_sha256=sha256(read(PREFIX + 'migration-receipt.json.gz')),
                   baseline_commit=baseline.commit, latest_published_release=release, changed_chains=changed_chains,
                   semantic_approvals_created=False, semantic_complete=False)
    # Preserve original counts/proofs as vintage context, never as current results.
    receipt['original_candidate_context'] = {key: original[key] for key in ('counts', 'candidate', 'summary')}
    receipt['counts'] = {'before': counts, 'after': {**counts, 'province': counts['province'] - 1}}
    receipt['candidate'] = {'directory': 'geography', 'published': False, 'installed': False}
    receipt['preparation_script_sha256'] = sha256(Path(__file__).read_bytes())
    receipt['rebase_limits'] = request['limits']
    (output / 'migration-receipt.json.gz').write_bytes(deterministic_gzip(canonical_json(receipt)))
    (output / 'before-hierarchy.json.gz').write_bytes(deterministic_gzip(read('data/hierarchy.json')))
    audit = {'version': 1, 'baseline_commit': baseline.commit, 'helper_version': VERSION,
             'latest_published_release': release, 'counts': receipt['counts'], 'changed_chains': changed_chains,
             'affected_location_ids': affected, 'affected_ancestor_ids': ancestors,
             'geometry_entries_sha256': sha256(canonical_json(geometries)), 'verified_geometry_entries': len(geometries),
             'actual_candidate_footprints_sha256': actual_footprints, 'geometry_text_changed': False,
             'candidate_parts': [descriptor(name, (geography / name).read_bytes()) for name in index['parts']],
             'canonical_ownership_parts': ownership, 'changed_geography_parts': mutated,
             'historical_claims_transferred': False, 'semantic_approval': False, 'installed': False, 'published': False,
             'limits': request['limits']}
    (output / 'crosswalk-audit.json.gz').write_bytes(deterministic_gzip(canonical_json(audit)))
    return {'baseline_commit': baseline.commit, 'counts': receipt['counts'], 'changed_chains': changed_chains,
            'outputs': [descriptor(name, (output / name).read_bytes()) for name in
                        ('migration-receipt.json.gz', 'before-hierarchy.json.gz', 'crosswalk-audit.json.gz')]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(ROOT, json.loads(args.request.read_bytes()), args.output), sort_keys=True))
