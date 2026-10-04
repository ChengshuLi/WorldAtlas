#!/usr/bin/env python3
"""Prepare three reproducible reference-membership stages without editing live geography."""
import argparse
import collections
import copy
import gzip
import hashlib
import json
import pathlib
import re
import subprocess
import importlib.util

# Historical consumers load this script via importlib rather than adding scripts/
# to sys.path. Resolve the sibling helper from this file in both entry modes.
_PROVENANCE_SPEC = importlib.util.spec_from_file_location(
    "macro_policy_provenance", pathlib.Path(__file__).with_name("macro_policy_provenance.py"))
_PROVENANCE_MODULE = importlib.util.module_from_spec(_PROVENANCE_SPEC)
_PROVENANCE_SPEC.loader.exec_module(_PROVENANCE_MODULE)
verify_policy_provenance = _PROVENANCE_MODULE.verify

ROOT = pathlib.Path(__file__).resolve().parents[1]
TIERS = ['location', 'province', 'area', 'region', 'subcontinent', 'continent']


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    path.write_bytes(gzip.compress(raw, mtime=0) if path.suffix == '.gz' else raw)


def chain(feature, units):
    parent = feature['properties']['parent_id']
    result = []
    for tier in TIERS[1:]:
        if parent not in units or units[parent]['level'] != tier:
            raise ValueError('Incomplete adjacent-tier chain: ' + feature['properties']['id'])
        unit = units[parent]
        result.append({'id': parent, 'name': unit['name'], 'level': tier})
        parent = unit['parent_id']
    if parent is not None:
        raise ValueError('Continent has a parent')
    return result


def check(units, features):
    ids = [f['properties']['id'] for f in features]
    if len(ids) != len(set(ids)) or any(f.get('id') != f['properties']['id'] for f in features):
        raise ValueError('Duplicate or mismatched location identities')
    used = set()
    for f in features:
        used.update(a['id'] for a in chain(f, units))
    for identity, unit in units.items():
        if identity != unit['id'] or unit['level'] not in TIERS[1:]:
            raise ValueError('Invalid geographic identity')
        if identity not in used:
            raise ValueError('Empty geographic unit: ' + identity)
    return {f['properties']['id']: chain(f, units) for f in features}


def relationship(kind, old, new, derived=None):
    row = {'change_type': kind, 'old_entity_id': old, 'new_entity_id': new,
           'reference_only': True, 'history_transfer': 'none'}
    if derived:
        row['derived_from_id'] = derived
    return row


def apply_stage(units, features, spec, source_evidence, stage):
    """Apply only declared metadata operations; retain every untouched field exactly."""
    if not source_evidence or any(not re.match('https?://', row.get('url', '')) or
            not re.fullmatch('[a-f0-9]{64}', row.get('source_sha256', '')) for row in source_evidence):
        raise ValueError('Migration requires reproducible source URLs and hashes')
    before_units = copy.deepcopy(units)
    before_properties = {f['properties']['id']: f['properties'] for f in features}
    before_chains = check(units, features)
    before_counts = collections.Counter(f['properties']['parent_id'] for f in features)
    before_counts.update(u['parent_id'] for u in units.values() if u['parent_id'])
    geometry_hash = digest([[f['properties']['id'], f['geometry']] for f in features])
    units = copy.deepcopy(units)
    features = [{**f, 'properties': copy.deepcopy(f['properties'])} for f in features]
    by_id = {f['properties']['id']: f for f in features}
    relationships = []
    operation_ids = set()
    for row in spec.get('new_groups', []):
        unit = copy.deepcopy(row['unit'] if 'unit' in row else row)
        identity = unit['id']
        if identity in units:
            raise ValueError('Created identity already exists: ' + identity)
        units[identity] = unit
        relationships.append(relationship('create', None, identity,
                                          unit.get('metadata', {}).get('derived_from_id')))
    for row in spec.get('group_changes', []):
        identity = row['id']
        if identity not in units or identity in operation_ids:
            raise ValueError('Missing/duplicate group operation: ' + identity)
        operation_ids.add(identity)
        unit = units[identity]
        if 'old_parent_id' in row and unit['parent_id'] != row['old_parent_id']:
            raise ValueError('Stale group parent: ' + identity)
        if 'old_name' in row and unit['name'] != row['old_name']:
            raise ValueError('Stale group name: ' + identity)
        for key in ('name', 'parent_id'):
            if key in row:
                unit[key] = row[key]
    for row in spec.get('location_changes', []):
        identity = row.get('id', row.get('location_id'))
        if identity not in by_id or identity in operation_ids:
            raise ValueError('Missing/duplicate location operation: ' + str(identity))
        operation_ids.add(identity)
        properties = by_id[identity]['properties']
        if properties['parent_id'] != row['old_parent_id']:
            raise ValueError('Stale location parent: ' + identity)
        properties['parent_id'] = row['parent_id']
    for split in spec.get('splits', []):
        old = units[split['old_id']]
        level = old['level']
        if level not in ('area', 'region'):
            raise ValueError('Only area/region splits are supported')
        children = {i for i, u in units.items() if u['parent_id'] == old['id']}
        targets = split['children']
        if len(targets) < 2:
            raise ValueError('Split needs at least two successors')
        assigned = set()
        for target in targets:
            identity = target['id']
            members = target.get('member_ids', target.get('province_ids', target.get('area_ids', [])))
            if identity in units or not members or assigned.intersection(members) or len(members) != len(set(members)):
                raise ValueError('Duplicate/empty split successor or members')
            if target.get('parent_id', old['parent_id']) != old['parent_id']:
                raise ValueError('Split changes its containing parent')
            assigned.update(members)
            units[identity] = {'id': identity, 'name': target['name'], 'level': level,
                               'parent_id': old['parent_id'], 'metadata': copy.deepcopy(target.get('metadata', {}))}
            for member in members:
                if member not in children:
                    raise ValueError('Split contains a nonmember: ' + member)
                units[member]['parent_id'] = identity
            relationships.append(relationship('split', old['id'], identity))
        if assigned != children:
            raise ValueError('Split does not conserve exact member inventory: ' + old['id'])
        del units[old['id']]
    # Cascading local retirements are explicit crosswalks. Never silently remove
    # an empty region/subcontinent/continent or a newly created empty identity.
    for level in ('province', 'area'):
        counts = collections.Counter(f['properties']['parent_id'] for f in features)
        counts.update(u['parent_id'] for u in units.values() if u['parent_id'])
        for identity in sorted(list(units)):
            if units[identity]['level'] == level and not counts[identity]:
                if identity not in before_units:
                    raise ValueError('New group is empty: ' + identity)
                del units[identity]
                relationships.append(relationship('retire', identity, None))
    counts = collections.Counter(f['properties']['parent_id'] for f in features)
    counts.update(u['parent_id'] for u in units.values() if u['parent_id'])
    for identity, unit in units.items():
        if identity not in before_units or counts[identity] != before_counts[identity]:
            unit.setdefault('metadata', {})['child_count'] = counts[identity]
    after_chains = check(units, features)
    if geometry_hash != digest([[f['properties']['id'], f['geometry']] for f in features]):
        raise ValueError('Location geometry mutation')
    changes = []
    for identity in sorted(by_id):
        before = before_properties[identity]
        after = by_id[identity]['properties']
        if before != after:
            if {k: v for k, v in before.items() if k != 'parent_id'} != {k: v for k, v in after.items() if k != 'parent_id'}:
                raise ValueError('Non-parent location property mutation')
            changes.append({'location_id': identity, 'before_properties': before,
                            'after_properties': after, 'history_transfer': 'none'})
    deltas = [{'id': i, 'before': before_units.get(i), 'after': units.get(i)}
              for i in sorted(set(before_units) | set(units)) if before_units.get(i) != units.get(i)]
    retired = [before_units[i] for i in sorted(set(before_units) - set(units))]
    receipt = {'version': 1, 'stage': stage, 'reference_only': True,
               'historical_claims_transferred': False, 'before_units': [before_units[i] for i in sorted(before_units)],
               'retired_units': retired, 'group_changes': deltas, 'relationships': relationships,
               'changed_location_properties': changes, 'source_evidence': source_evidence,
               'location_chain_crosswalk': [{'location_id': i, 'before_chain': before_chains[i],
                   'after_chain': after_chains[i], 'history_transfer': 'none', 'footprint_unchanged': True}
                   for i in sorted(by_id) if before_chains[i] != after_chains[i]],
               'before_hierarchy_content_sha256': digest([before_units[i] for i in sorted(before_units)]),
               'after_hierarchy_content_sha256': digest([units[i] for i in sorted(units)]),
               'unchanged_geometry_sha256': geometry_hash,
               'counts': dict(collections.Counter(u['level'] for u in units.values())) | {'location': len(features)},
               'summary': {'geometry_changes': 0, 'historical_records_touched': 0,
                   'group_changes': len(deltas), 'retired_groups': len(retired),
                   'created_groups': len(set(units) - set(before_units)),
                   'direct_location_parent_changes': len(changes), 'semantic_complete': False}}
    return units, features, receipt


def sources_from_reports(root, index):
    evidence = {}
    for row in index['reports']:
        path = root / row['path']
        if sha(path) != row['sha256']:
            raise ValueError('Review ledger hash mismatch: ' + row['path'])
        raw = gzip.decompress(path.read_bytes())
        if hashlib.sha256(raw).hexdigest() != row['raw_sha256']:
            raise ValueError('Review ledger content hash mismatch')
        report = json.loads(raw)
        for source in report.get('sources', []) + report.get('retained_sources', []):
            pin = source.get('sha256', source.get('source_sha256'))
            if source.get('status', 200) != 200 or source.get('inspected', True) is False:
                continue
            if not re.fullmatch('[a-f0-9]{64}', pin or '') or not re.match('https?://', source.get('url', '')):
                continue
            evidence[(source['url'], pin)] = {'url': source['url'], 'source_sha256': pin,
                                               'source_id': source.get('id'), 'review_ledger': row['path']}
    if not evidence:
        raise ValueError('No reproducible inspected source evidence')
    return [evidence[k] for k in sorted(evidence)]


def history_pins(data):
    directories = ('ownership-history', 'ownership-runtime', 'reference-attributes',
                   'dated-reference-names', 'demographic-evidence', 'population-history')
    files = [p for name in directories for p in (data / name).rglob('*') if p.is_file()]
    files += [data / name for name in ('temporal-examples.json', 'examples.json') if (data / name).is_file()]
    return {str(p.relative_to(data)): sha(p) for p in sorted(files)}


def footprint_pin(data):
    code = "import fs from 'node:fs';import{footprintHash}from './scripts/check-prepared.mjs';const d=process.argv[1],i=JSON.parse(fs.readFileSync(d+'/world-index.json'));console.log(footprintHash(i.parts.flatMap(p=>JSON.parse(fs.readFileSync(d+'/'+p)).features)));"
    return subprocess.check_output(['node', '--input-type=module', '-e', code, str(data)], cwd=ROOT, text=True).strip()


def save_stage(directory, index, parts, units, features):
    write(directory / 'world-index.json', index)
    write(directory / 'hierarchy.json', [units[i] for i in sorted(units)])
    by_id = {f['properties']['id']: f for f in features}
    for relative, collection in parts.items():
        write(directory / relative, {**collection, 'features': [by_id[f['properties']['id']] for f in collection['features']]})


def prepare(data, policy_path, output, receipts):
    policy = read(policy_path)
    # Validate the frozen decision citation before any candidate output is written.
    if 'data/macro-foundation/europe-asia-boundary-decisions.json' in policy.get('decision_files', []):
        provenance = verify_policy_provenance(data.parent)
        if sha(policy_path) != provenance['policy_sha256']:
            raise ValueError('Supplied policy differs from corrected frozen reference')
    if output == data or data in output.parents:
        raise ValueError('Candidate output must be outside live data')
    index = read(data / 'world-index.json')
    original_units = read(data / 'hierarchy.json')
    units = {u['id']: u for u in original_units}
    if len(units) != len(original_units):
        raise ValueError('Duplicate current group identities')
    parts = {relative: read(data / relative) for relative in index['parts']}
    features = [f for part in parts.values() for f in part['features']]
    review = read(data / 'macro-foundation/review-index.json')
    if sha(data / 'hierarchy.json') != review['input_hierarchy_sha256']:
        raise ValueError('Macro review belongs to a different current hierarchy')
    evidence = sources_from_reports(data.parent, review)
    decision_pins = {}
    for relative in policy.get('decision_files', []):
        path = (data.parent / relative).resolve()
        if data.resolve() not in path.parents:
            raise ValueError('Decision evidence path escapes live data')
        decision = read(path)
        if decision.get('input_hierarchy_sha256') != review['input_hierarchy_sha256']:
            raise ValueError('Decision evidence refers to a different hierarchy')
        decision_pins[relative] = sha(path)
        for source in decision.get('sources', []) + decision.get('new_sources', []) + decision.get('retained_sources', []):
            pin = source.get('sha256', source.get('source_sha256'))
            if source.get('status', 200) == 200 and source.get('inspected', True) is not False and re.fullmatch('[a-f0-9]{64}', pin or '') and re.match('https?://', source.get('url', '')):
                evidence.append({'url': source['url'], 'source_sha256': pin,
                                 'source_id': source.get('id'), 'decision_file': relative})
    evidence = sorted({(e['url'], e['source_sha256']): e for e in evidence}.values(), key=lambda e: (e['url'], e['source_sha256']))
    original_pin, preserved = footprint_pin(data), history_pins(data)
    original_files = {str(p.relative_to(data)): sha(p) for p in [data / 'world-index.json', data / 'hierarchy.json'] + [data / p for p in index['parts']]}
    for stage in ('repairs', 'areas', 'regions'):
        units, features, receipt = apply_stage(units, features, policy[stage], evidence, stage)
        destination = output / stage / 'after'
        save_stage(destination, index, parts, units, features)
        if footprint_pin(destination) != original_pin:
            raise ValueError('Canonical location footprint hash changed')
        receipt.update(before_footprints_sha256=original_pin, after_footprints_sha256=original_pin,
                       input_files_sha256=original_files, preserved_historical_files_sha256=preserved,
                       policy_sha256=sha(policy_path), decision_files_sha256=decision_pins, preparation_script_sha256=sha(pathlib.Path(__file__)))
        write(receipts / ('migration-' + stage + '.json.gz'), receipt)
        write(output / stage / 'migration-receipt.json.gz', receipt)
    save_stage(output / 'after', index, parts, units, features)
    if history_pins(data) != preserved or any(sha(data / p) != pin for p, pin in original_files.items()):
        raise ValueError('Preparation altered live geography or historical products')
    result = {'locations': len(features), 'footprints_sha256': original_pin,
              'counts': dict(collections.Counter(u['level'] for u in units.values())),
              'historical_files_preserved': len(preserved), 'candidate_only': True,
              'macro_approved': False, 'regional_interiors_approved': False}
    write(output / 'preparation-summary.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=pathlib.Path, default=ROOT / 'data')
    parser.add_argument('--policy', type=pathlib.Path, default=ROOT / 'data/macro-foundation/membership-decisions.json')
    parser.add_argument('--output', type=pathlib.Path, default=ROOT / '.cache/global-macro-foundation')
    parser.add_argument('--receipts', type=pathlib.Path, default=ROOT / 'data/macro-foundation')
    args = parser.parse_args()
    print(json.dumps(prepare(args.data.resolve(), args.policy.resolve(), args.output.resolve(), args.receipts.resolve())))


if __name__ == '__main__':
    main()
