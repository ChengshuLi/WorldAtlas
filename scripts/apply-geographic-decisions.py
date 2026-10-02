"""Apply inspected reference-geography decisions without changing location land.

Six independent continent inventories feed one validated migration. Boundary
approval and completion of the descendants remain separate. Original chains,
retired groups and the complete before/after crosswalk are retained.
"""
import collections
import copy
import gzip
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
LEVELS = ['location', 'province', 'area', 'region', 'subcontinent', 'continent']

def read(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_text())

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()

def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    raw = (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    temporary.write_bytes(gzip.compress(raw, mtime=0) if path.suffix == '.gz' else raw)
    temporary.replace(path)

def validate_inventory(document, units, features):
    def continent(parent):
        while units[parent]['parent_id']:
            parent = units[parent]['parent_id']
        return units[parent]['name']
    name = document['continent']
    expected_groups = {id for id in units if continent(id) == name}
    expected_locations = {f['id'] for f in features if continent(f['properties']['parent_id']) == name}
    inventory = document['inventory']
    for key, expected in [('group_ids', expected_groups), ('location_ids', expected_locations)]:
        actual = inventory[key]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ValueError(f'{name}: incomplete or duplicate {key} inventory')
    decisions = document['decisions']
    ids = [row['id'] for row in decisions if row['action'] != 'create']
    if len(ids) != len(set(ids)) or set(ids) != expected_groups:
        raise ValueError(f'{name}: every existing group requires exactly one disposition')
    locations = [id for row in document['location_review'] for id in row['ids']]
    if len(locations) != len(set(locations)) or set(locations) != expected_locations:
        raise ValueError(f'{name}: every location requires exactly one review disposition')

def apply_documents(documents, original_units, original_features):
    units = copy.deepcopy(original_units)
    features = copy.deepcopy(original_features)
    entities = {**units, **{f['id']: {'id': f['id'], 'name': f['properties']['name'], 'parent_id': f['properties']['parent_id'], 'level': 'location'} for f in features}}
    rows = [r for d in documents for r in d['decisions']]
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate geographic decision IDs')
    # Validate every input before creating or changing anything.
    for row in rows:
        if row['action'] not in ['retain', 'rename', 'reparent', 'merge', 'create', 'open']:
            raise ValueError(f"Unsupported action for {row['id']}")
        if row['action'] != 'create':
            old = entities[row['id']]
            if (row['level'], row['current_name'], row['current_parent_id']) != (old['level'], old['name'], old['parent_id']):
                raise ValueError(f"Stale decision: {row['id']}")
        if row['boundary_status'] not in ['supported', 'open']:
            raise ValueError('Invalid boundary assessment')
        if row['boundary_status'] == 'supported' or row['action'] not in ['open', 'retain']:
            if not row['rationale'].strip() or not row['evidence'] or any(not e.get('url', '').startswith(('https://', 'http://')) or not e.get('inspected_fact', '').strip() for e in row['evidence']):
                raise ValueError(f"Inspected source evidence required: {row['id']}")
    for row in rows:
        if row['action'] == 'create':
            if row['id'] in entities or row['level'] not in LEVELS[1:]:
                raise ValueError('New group identity already exists or has invalid tier')
            unit = {'id': row['id'], 'level': row['level'], 'name': row['new_name'], 'parent_id': row.get('new_parent_id'), 'metadata': {'kind': 'geographic', 'framework_status': 'atlas-defined', 'source': row['evidence'][0].get('title'), 'source_url': row['evidence'][0]['url'], 'basis': row['rationale']}}
            units[row['id']] = unit
            entities[row['id']] = unit
    merge_targets = {r['id']: r['target_id'] for r in rows if r['action'] == 'merge'}
    def target(id):
        seen = set()
        while id in merge_targets:
            if id in seen:
                raise ValueError('Geographic merge cycle')
            seen.add(id)
            id = merge_targets[id]
        return id
    for row in rows:
        unit = units[row['id']]
        if row['action'] == 'rename':
            unit['name'] = row['new_name']
        if row['action'] == 'reparent':
            unit['parent_id'] = row['new_parent_id']
        if row['action'] == 'merge':
            other = units[target(row['id'])]
            if unit['level'] != other['level']:
                raise ValueError('Merge must preserve adjacent geographic tier')
        unit.setdefault('metadata', {})['semantic_review'] = {k: row[k] for k in ['action', 'boundary_status', 'rationale', 'evidence', 'remaining_reasons']}
    for unit in units.values():
        if unit['parent_id']:
            unit['parent_id'] = target(unit['parent_id'])
    for feature in features:
        feature['properties']['parent_id'] = target(feature['properties']['parent_id'])
    retired = {id: units.pop(id) for id in merge_targets}
    feature_by_id = {f['id']: f for f in features}
    applied_locations = set()
    for document in documents:
        for row in document.get('location_changes', []):
            key = (row['id'], row['action'])
            if key in applied_locations:
                raise ValueError('Duplicate location mutation')
            applied_locations.add(key)
            old = entities[row['id']]
            if (row['current_name'], row['current_parent_id']) != (old['name'], old['parent_id']):
                raise ValueError('Stale location mutation')
            if not row['rationale'].strip() or not row['evidence'] or any(not e.get('url', '').startswith(('http://', 'https://')) or not e.get('inspected_fact', '').strip() for e in row['evidence']):
                raise ValueError('Location change requires inspected source evidence')
            props = feature_by_id[row['id']]['properties']
            if row['action'] == 'rename':
                props['name'] = row['new_name']
            elif row['action'] == 'reparent':
                props['parent_id'] = target(row['new_parent_id'])
            else:
                raise ValueError('Unsupported location mutation')
            props['metadata'].setdefault('reference_corrections', []).append(row)
        for row in document.get('location_metadata_changes', []):
            old = entities[row['id']]
            if row['current_name'] != old['name'] or not row['rationale'].strip() or not row['evidence']:
                raise ValueError('Source-role correction requires current identity and evidence')
            allowed = {'source_role', 'location_basis', 'administrative_level', 'framework_status', 'reference_year', 'source_url', 'license', 'selection_reason'}
            if not row['changes'] or not set(row['changes']).issubset(allowed):
                raise ValueError('Unsupported reference metadata correction')
            metadata = feature_by_id[row['id']]['properties']['metadata']
            metadata.update(row['changes'])
            metadata.setdefault('reference_corrections', []).append(row)
    for unit in units.values():
        parent = unit['parent_id']
        if unit['level'] == 'continent':
            if parent is not None:
                raise ValueError('A continent cannot have a parent')
        elif parent not in units or units[parent]['level'] != LEVELS[LEVELS.index(unit['level']) + 1]:
            raise ValueError(f"Non-adjacent parent: {unit['id']}")
    members = collections.Counter()
    for feature in features:
        parent = feature['properties']['parent_id']
        if parent not in units or units[parent]['level'] != 'province':
            raise ValueError('Every location requires one province')
        while parent:
            members[parent] += 1
            parent = units[parent]['parent_id']
    unused = set(units) - set(members)
    if any(id not in original_units for id in unused):
        raise ValueError('Decision creates an empty or unreachable geographic group')
    for id in unused:
        retired[id] = units.pop(id)
    child_counts = collections.Counter(f['properties']['parent_id'] for f in features)
    child_counts.update(u['parent_id'] for u in units.values() if u['parent_id'])
    for id, unit in units.items():
        unit['metadata']['child_count'] = child_counts[id]
    for document in documents:
        by_id = {f['id']: f for f in features}
        for review_index, row in enumerate(document['location_review']):
            if row['status'] not in ['supported', 'open'] or not row['rationale'].strip():
                raise ValueError('Invalid location disposition')
            if row['status'] == 'supported' and not row['evidence']:
                raise ValueError('Location approval requires evidence')
            for id in row['ids']:
                by_id[id]['properties']['metadata']['semantic_review'] = {'status': row['status'], 'continent': document['continent'], 'decision_index': review_index, 'evidence_file': 'geographic-decisions'}
    return units, features, retired

def chain(feature, units):
    ids = []
    parent = feature['properties']['parent_id']
    while parent:
        u = units[parent]
        ids.append({'id': parent, 'name': u['name'], 'level': u['level']})
        parent = u['parent_id']
    return ids

def main():
    files = sorted((DATA / 'geographic-decisions').glob('*.json'))
    if len(files) != 6:
        raise ValueError('All six complete continent decisions must be available')
    documents = [read(p) for p in files]
    units = {u['id']: u for u in read(DATA / 'hierarchy.json')}
    parts = {p: read(DATA / p) for p in read(DATA / 'world-index.json')['parts']}
    features = [f for p in parts.values() for f in p['features']]
    input_hash = digest(documents)
    receipt_path = DATA / 'geographic-decision-migration.json.gz'
    if receipt_path.exists():
        receipt = read(receipt_path)
        if receipt['decisions_sha256'] == input_hash and receipt['after_sha256'] == digest([units, features]):
            print(json.dumps({'already_applied': True, 'changed_locations': len(receipt['changes'])}))
            return
    if {d['continent'] for d in documents} != {u['name'] for u in units.values() if u['level'] == 'continent'}:
        raise ValueError('Continent decisions do not cover the six active roots')
    for document in documents:
        validate_inventory(document, units, features)
    revised, changed, retired = apply_documents(documents, units, features)
    old_locations = {f['id']: f for f in features}
    changes = []
    for feature in changed:
        old = old_locations[feature['id']]
        if old['geometry'] != feature['geometry']:
            raise ValueError('Semantic reference migration must not change location land')
        before, after = chain(old, units), chain(feature, revised)
        def geographical_properties(props):
            result = copy.deepcopy(props)
            result.get('metadata', {}).pop('semantic_review', None)
            return result
        if before != after or geographical_properties(old['properties']) != geographical_properties(feature['properties']):
            changes.append({'location_id': feature['id'], 'before_name': old['properties']['name'], 'after_name': feature['properties']['name'], 'before_properties': old['properties'], 'after_properties': feature['properties'], 'before_chain': before, 'after_chain': after, 'history_transfer': 'none', 'footprint_unchanged': True})
    receipt = {'version': 1, 'scope': 'Reference geography correction; no invented historical effective date or historical evidence transfer', 'decisions_sha256': input_hash, 'before_sha256': digest([units, features]), 'after_sha256': digest([revised, changed]), 'before_units': list(units.values()), 'retired_units': list(retired.values()), 'group_changes': [{'id': id, 'before': units.get(id), 'after': revised.get(id)} for id in sorted(set(units) | set(revised)) if units.get(id) != revised.get(id)], 'changes': changes, 'counts': dict(collections.Counter(u['level'] for u in revised.values()))}
    if '--check' in sys.argv:
        print(json.dumps({'validated': True, 'changed_locations': len(changes), 'retired_groups': len(retired), 'counts': receipt['counts']}))
        return
    # Keep the complete pre-migration identity evidence before replacing outputs.
    save(receipt_path, receipt)
    by_id = {f['id']: f for f in changed}
    for p, collection in parts.items():
        collection['features'] = [by_id[f['id']] for f in collection['features']]
        save(DATA / p, collection)
    save(DATA / 'hierarchy.json', list(revised.values()))
    print(json.dumps({'applied': True, 'changed_locations': len(changes), 'retired_groups': len(retired), 'counts': receipt['counts']}))

if __name__ == '__main__':
    main()
