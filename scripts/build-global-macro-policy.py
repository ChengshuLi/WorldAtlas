#!/usr/bin/env python3
"""Compile reviewed macro membership proposals into explicit, bounded operations."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
loader = importlib.util.spec_from_file_location('macro', ROOT / 'scripts/prepare-global-macro-geography.py')
macro = importlib.util.module_from_spec(loader)
loader.loader.exec_module(macro)


def build(data):
    reports = {name: macro.read(data / ('macro-foundation/' + name + '-review.json.gz'))
               for name in ('africa', 'americas', 'europe-asia', 'oceania')}
    units = {u['id']: u for u in macro.read(data / 'hierarchy.json')}
    policy = {'version': 1, 'reference_only': True, 'macro_approved': False,
              'input_hierarchy_sha256': macro.sha(data / 'hierarchy.json'),
              'scope': 'Reviewed macro membership candidates; no local semantic approval or historical transfer',
              'repairs': {'new_groups': [], 'group_changes': [], 'location_changes': []},
              'areas': {'splits': []}, 'regions': {'splits': []},
              'retained_conventions': ['Chagos uses explicit Maldives/central Indian Ocean reporting association; not African continental adjacency or political-owner assignment.',
                                       'Norfolk uses explicit southwest Pacific/New Zealand reporting association; no inference from Australian ownership.'],
              'deferred_subdivisions': ['Middle Asia further subdivision']}
    repairs = policy['repairs']
    africa = macro.read(data / 'macro-foundation/africa-boundary-decisions.json')
    for row in africa['required_changes']:
        common = {'id': row['entity_id'], 'source_ids': row['source_ids'], 'review_ledger': 'africa'}
        if row['action'] == 'rename':
            repairs['group_changes'].append({**common, 'old_name': row['from_name'], 'name': row['to_name']})
        elif row['action'] == 'reparent' and row['entity_id'] != 'framework:area:chagos-archipelago:2b3dbf16c5b5':
            repairs['group_changes'].append({**common, 'old_parent_id': row['from_parent_id'], 'parent_id': row['to_parent_id']})
    for row in reports['americas']['required_corrections']:
        common = {'source_ids': row['source_ids'], 'review_ledger': 'americas'}
        if row['kind'] == 'reparent-location':
            repairs['location_changes'].append({'id': row['location_id'], 'old_parent_id': row['old_parent_id'],
                                                'parent_id': row['new_parent_id'], **common})
        elif row['kind'] == 'reparent-and-rename-area':
            repairs['group_changes'].append({'id': row['area_id'], 'old_name': row['old_name'],
                'old_parent_id': row['old_parent_id'], 'name': row['new_name'], 'parent_id': row['new_parent_id'], **common})
        elif row['kind'] == 'rename':
            repairs['group_changes'].append({'id': row['id'], 'old_name': units[row['id']]['name'], 'name': row['new_name'], **common})
        elif row['kind'] == 'replace-region-one-to-five':
            policy['regions']['splits'].append({'old_id': row['old_id'], 'children': [
                {'id': child['suggested_new_stable_id'], 'name': child['proposed_name'],
                 'parent_id': child['parent_id'], 'area_ids': sorted(a['id'] for a in child['area_assignments']),
                 'metadata': metadata(child['rationale'], 'americas', child['source_ids'])}
                for child in row['proposed_regions']]})
        else:
            raise ValueError('Unrecognized reviewed America operation')
    aru = reports['oceania']['required_corrections'][0]
    area_id, province_id = 'atlas:macro-foundation:area:aru-islands', 'atlas:macro-foundation:province:maluku-aru'
    repairs['new_groups'] += [
        {'id': area_id, 'name': aru['proposed_area']['name'], 'level': 'area',
         'parent_id': aru['proposed_region_id'], 'metadata': metadata(aru['proposed_area']['role'], 'oceania', aru['source_ids'])},
        {'id': province_id, 'name': 'Aru Islands', 'level': 'province', 'parent_id': area_id,
         'metadata': {**metadata(aru['proposed_province']['role'], 'oceania', aru['source_ids']),
                      'derived_from_id': aru['current_parent_id'],
                      'source_id': aru['proposed_province']['source_id'], 'source_administrative_name': 'Maluku'}}]
    repairs['location_changes'].append({'id': aru['location_id'], 'old_parent_id': aru['current_parent_id'],
        'parent_id': province_id, 'source_ids': aru['source_ids'], 'review_ledger': 'oceania'})
    repairs['group_changes'] += [
        {'id': 'framework:area:chagos-archipelago:2b3dbf16c5b5',
         'old_parent_id': 'framework:region:western-indian-ocean:1393877a77f7',
         'parent_id': 'framework:region:indian-subcontinent:72d264b56887',
         'source_ids': ['chagos'], 'review_ledger': 'africa'},
        {'id': 'framework:area:norfolk-is:2fc9924293ca',
         'old_parent_id': 'framework:region:australia:11dca273abf2',
         'parent_id': 'framework:region:new-zealand:e79e5965932c',
         'source_ids': ['norfolk'], 'review_ledger': 'oceania'}]
    # Named Maltese association is explicitly supported by the inspected source,
    # not inferred from owner or a nearest-neighbor heuristic.
    malta = next(s for s in reports['europe-asia']['sources'] if s['id'] == 'malta')
    if malta['status'] != 200 or not malta.get('inspected_fact'):
        raise ValueError('Malta lacks inspected source evidence')
    repairs['group_changes'].append({'id': 'framework:area:sicilia:57eec0c13aae',
        'old_parent_id': 'framework:region:southeastern-europe:e7fed0fa4e00',
        'parent_id': 'framework:region:italy:459a704de6d6', 'source_ids': ['malta'], 'review_ledger': 'europe-asia'})
    repairs['group_changes'] += [
        {'id': 'framework:area:malaya:d02eb5adc582', 'old_parent_id': 'framework:region:malesia:041eea1ae1b4',
         'parent_id': 'framework:region:indo-china:1fb8aab5aaeb', 'source_ids': ['mainland-southeast-asia'], 'review_ledger': 'europe-asia'},
        {'id': 'framework:region:malesia:041eea1ae1b4', 'old_name': 'Malesia', 'name': 'Maritime Southeast Asia',
         'source_ids': ['malesia'], 'review_ledger': 'europe-asia'},
        {'id': 'framework:region:indo-china:1fb8aab5aaeb', 'old_name': 'Indo-China', 'name': 'Mainland Southeast Asia and Andaman Arc',
         'source_ids': ['mainland-southeast-asia'], 'review_ledger': 'europe-asia'},
        {'id': 'framework:region:middle-asia:0fede64adc2e', 'old_name': 'Middle Asia', 'name': 'Central Asian Interior',
         'source_ids': ['central-asia'], 'review_ledger': 'europe-asia'}]
    western = [
        ('anatolia-eastern-mediterranean', 'Anatolia and Eastern Mediterranean',
         ['framework:area:turkey:f2a11613e268', 'framework:area:east-aegean-is:ee1869bcfe81', 'framework:area:cyprus:9a8e578f87f4'],
         ['anatolia', 'continental-boundaries', 'aegean-islands']),
        ('levant-mesopotamia', 'Levant and Mesopotamia',
         ['framework:area:sinai:10ea85f2bb8b', 'framework:area:iraq:d2153b03f1ad', 'framework:area:palestine:aebeccdc2943', 'framework:area:lebanon-syria:226c2a2acaf6'],
         ['levant', 'mesopotamia', 'continental-boundaries']),
        ('iranian-plateau', 'Iranian Plateau',
         ['framework:area:iran:c280e011aa2e', 'framework:area:afghanistan:479e1de16ab1'], ['iranian-plateau', 'west-asia'])]
    policy['regions']['splits'].append({'old_id': 'framework:region:western-asia:4231eadd1b84', 'children': [
        {'id': 'atlas:macro-foundation:region:' + key, 'name': name, 'area_ids': sorted(areas),
         'metadata': metadata('Named Western Asian geographic reporting association; native administrative reference envelopes, not exact watershed masks',
                              'europe-asia', sources)} for key, name, areas, sources in western]})
    india = reports['europe-asia']['south_asia_subdivision']
    old_region = 'framework:region:indian-subcontinent:72d264b56887'
    mapping = {r['province_id']: r['proposed_branch'] for r in india['province_mappings']}
    actual = {i for i, u in units.items() if u['level'] == 'province' and units[u['parent_id']]['parent_id'] == old_region}
    if len(mapping) != len(india['province_mappings']) or set(mapping) != actual:
        raise ValueError('Indian regional mapping is not the exact complete province inventory')
    area_by_branch = {}
    for row in india['area_mappings']:
        area, branches = row['area_id'], row['province_ids_by_branch']
        current = {i for i, u in units.items() if u['parent_id'] == area}
        flattened = [p for members in branches.values() for p in members]
        if len(flattened) != len(set(flattened)) or set(flattened) != current:
            raise ValueError('Mixed-area map does not match current members')
        if len(branches) == 1:
            branch = next(iter(branches))
            area_by_branch.setdefault(branch, []).append(area)
            continue
        targets = []
        for branch, provinces in sorted(branches.items()):
            identity = 'atlas:macro-foundation:area:' + macro.digest([area, branch])[:16]
            name = row['area_name'] + ' — ' + branch_name(branch) + ' geographic portion'
            targets.append({'id': identity, 'name': name, 'province_ids': sorted(provinces),
                'metadata': metadata('Named native administrative reference membership; geographic portion, not new government division',
                                     'europe-asia', ['mha-zonal-councils', 'indian-subcontinent'])})
            area_by_branch.setdefault(branch, []).append(identity)
        policy['areas']['splits'].append({'old_id': area, 'children': targets})
    area_by_branch.setdefault('south-asian-oceanic-islands', []).append('framework:area:chagos-archipelago:2b3dbf16c5b5')
    children = [{'id': 'atlas:macro-foundation:region:' + branch, 'name': branch_name(branch),
        'area_ids': sorted(areas), 'metadata': metadata('Sourced administrative-reference reporting zone; no exact natural watershed or historical membership asserted',
            'europe-asia', ['mha-zonal-councils', 'indian-subcontinent'])}
        for branch, areas in sorted(area_by_branch.items())]
    if len(children) != 10:
        raise ValueError('Expected ten independently documented Southern Asian reporting branches')
    policy['regions']['splits'].append({'old_id': old_region, 'children': children})
    policy['decision_files'] = sorted(str(p.relative_to(data.parent)) for p in (data / 'macro-foundation').glob('*-boundary-decisions.json'))
    return policy


def branch_name(branch):
    return {'bengal-delta-and-bangladesh': 'Bengal and Bangladesh',
            'indus-western-subcontinent': 'Indus and Western Subcontinent',
            'nepal-bhutan-himalaya': 'Nepal and Bhutan Himalaya',
            'south-asian-oceanic-islands': 'South Asian Indian Ocean Islands',
            **{'india-' + key: label + ' India' for key, label in [
                ('northern', 'Northern'), ('central', 'Central'), ('eastern', 'Eastern'),
                ('northeastern', 'Northeastern'), ('western', 'Western'), ('southern', 'Southern')]}}[branch]


def metadata(basis, ledger, source_ids):
    return {'kind': 'geographic', 'framework_status': 'atlas-defined', 'reference_only': True,
            'basis': basis, 'review_ledger': 'data/macro-foundation/' + ledger + '-review.json.gz',
            'source_ids': source_ids, 'semantic_approved': False, 'descendant_approval': False}


if __name__ == '__main__':
    macro.write(ROOT / 'data/macro-foundation/membership-decisions.json', build(ROOT / 'data'))
