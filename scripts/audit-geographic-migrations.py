"""Read-only, exhaustive cartographic revision crosswalk; never transfer history.

Compare the retained pre-plan snapshot with the current reference and inventory
all archived database footprints. Relationships have no historical effective date:
changing an atlas source is not evidence that a territory split in that year.
"""
import collections
import hashlib
import gzip
import json
from pathlib import Path
import sqlite3
import sys
import tarfile

from shapely import STRtree, make_valid
from shapely.geometry import shape
from majority import area, canonical

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
BASE = ROOT / '.cache/plan-baseline'
REPORT = DATA / 'geographic-migration-review.json'


def read(path):
    return json.loads(path.read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def chain(feature, units):
    result = []
    parent = feature['properties']['parent_id']
    while parent:
        unit = units[parent]
        result.append(parent)
        parent = unit['parent_id']
    return result


def load_current():
    return {feature['id']: feature for part in read(DATA / 'world-index.json')['parts']
            for feature in read(DATA / part)['features']}


def load_baseline():
    with tarfile.open(BASE / 'geography.tar.gz') as archive:
        return {feature['id']: feature
                for part in read(BASE / 'world-index.json')['parts']
                for feature in json.load(archive.extractfile(part))['features']}


def original_history(connection):
    """Check exact original rows by primary key, permitting new sourced records."""
    checks = {}
    failures = []
    for table, baseline in read(ROOT / '.cache/plan-original-records.json').items():
        columns = [row[1] for row in connection.execute('PRAGMA table_info(' + table + ')')]
        current = {row[0]: list(row) for row in connection.execute('SELECT * FROM ' + table)}
        mismatches = [row[0] for row in baseline['rows'] if current.get(row[0]) != row]
        checks[table] = {'original_rows': len(baseline['rows']), 'current_rows': len(current),
                         'preserved_exactly': len(baseline['rows']) - len(mismatches),
                         'mismatched_ids': mismatches, 'columns': columns}
        failures.extend({'table': table, 'id': key} for key in mismatches)
    return checks, failures


def compact_crosswalk(report):
    """Deduplicate provenance and repeated edge keys to stay within host limits."""
    sources = []
    source_indices = {}
    for row in report['archived']:
        source = (row.pop('source_url'), row.pop('license'))
        if source not in source_indices:
            source_indices[source] = len(sources)
            sources.append({'source_url': source[0], 'license': source[1]})
        row['source_index'] = source_indices[source]
        row.pop('method', None)
        row['successors'] = [[edge['id'], edge['predecessor_share'], edge['successor_share'], edge['overlap_km2']]
                             for edge in row['successors']]
    for row in report['added']:
        row['predecessors'] = [[edge['id'], edge['successor_share'], edge['predecessor_share']]
                               for edge in row['predecessors']]
    report['sources'] = sources
    report['relationship_columns'] = {
        'successors': ['id', 'predecessor_share', 'successor_share', 'overlap_km2'],
        'predecessors': ['id', 'successor_share', 'predecessor_share']}
    report['relationship_method'] = 'Undated cartographic overlap; records stay on the predecessor ID'
    return report


def retained_changes(baseline, current, old_units, units):
    changed = []
    for key in sorted(set(baseline) & set(current)):
        before, after = baseline[key], current[key]
        bp, ap = before['properties'], after['properties']
        flags = []
        for field in ['name', 'parent_id', 'reference_owner']:
            if bp.get(field) != ap.get(field):
                flags.append(field)
        before_chain, after_chain = chain(before, old_units), chain(after, units)
        before_names = [old_units[key]['name'] for key in before_chain]
        after_names = [units[key]['name'] for key in after_chain]
        if before_chain != after_chain:
            flags.append('parent_chain')
        if before_names != after_names:
            flags.append('parent_names')
        if digest(before['geometry']) != digest(after['geometry']):
            flags.append('geometry')
        if flags:
            changed.append({'id': key, 'changes': flags,
                            'before': {'name': bp['name'], 'chain': before_chain, 'chain_names': before_names,
                                       'geometry_sha256': digest(before['geometry'])},
                            'after': {'name': ap['name'], 'chain': after_chain, 'chain_names': after_names,
                                      'geometry_sha256': digest(after['geometry'])}})
    return changed


def preserve_reference_archive(path, payload):
    """Never replace the original snapshot with renamed/reparented reference units."""
    if path.exists():
        with gzip.open(path, 'rt') as source:
            existing = json.load(source)
        before = {row['id']: digest(row['geometry']) for row in existing['locations']}
        after = {row['id']: digest(row['geometry']) for row in payload['locations']}
        if before != after:
            raise ValueError('Archived footprints changed; preserve the existing snapshot and create an explicit additional reference archive')
        if existing['original_records'] != payload['original_records']:
            raise ValueError('Original historical records differ from the immutable reference archive')
        if existing.get('original_entities', []) != payload.get('original_entities', []):
            raise ValueError('Original settlement identities differ from the immutable reference archive')
        return existing
    with path.open('wb') as output:
        with gzip.GzipFile(fileobj=output, mode='wb', mtime=0) as compressed:
            compressed.write(json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode())
    return payload


def refresh_hierarchy_crosswalk():
    """Refresh name/membership changes without repeating spatial intersections."""
    report = read(REPORT)
    current = load_current()
    baseline = load_baseline()
    units = {unit['id']: unit for unit in read(DATA / 'hierarchy.json')}
    old_units = {unit['id']: unit for unit in read(BASE / 'hierarchy.json')}
    corrections = read(DATA / 'macro-corrections.json')
    if corrections['footprints_sha256_before'] != corrections['footprints_sha256_after']:
        raise ValueError('Macro corrections changed footprints; spatial crosswalk cannot be reused')
    prepared = read(DATA / 'reference-attributes/index.json')
    if prepared['footprints_sha256'] != corrections['footprints_sha256_after']:
        raise ValueError('Macro footprints do not match the prepared reference footprint snapshot')
    before_ids, after_ids = set(baseline), set(current)
    if sorted(before_ids - after_ids) != report['retired_baseline_ids'] or sorted(after_ids - before_ids) != sorted(row['id'] for row in report['added']):
        raise ValueError('Location IDs changed; spatial crosswalk cannot be reused')
    changed = retained_changes(baseline, current, old_units, units)
    if any('geometry' in row['changes'] for row in changed):
        raise ValueError('A retained location geometry changed; spatial crosswalk cannot be reused')
    report['changed_retained'] = changed
    report['counts']['changed_retained_ids'] = len(changed)
    report['counts']['unchanged_retained_ids'] = report['counts']['retained_ids'] - len(changed)
    for row in report['added']:
        row['name'] = current[row['id']]['properties']['name']
        row['parent_chain'] = chain(current[row['id']], units)
    report['reference_changes'] = {
        'macro_corrections': 'macro-corrections.json',
        'macro_changed_locations': len(corrections['changes']),
        'macro_changed_groups': len(corrections['group_changes']),
        'location_footprints_sha256': corrections['footprints_sha256_after'],
        'geometry_changed_locations': 0,
        'membership_and_name_changes_are_undated_reference_revisions': True,
        'spatial_relationships_reused': True,
        'original_archive_preserved': True,
        'meaning': 'Parent footprints follow current member locations; stored historical records and original archived chains stay on their original identities.'}
    paths = [BASE / 'world-index.json', BASE / 'hierarchy.json', BASE / 'geography.tar.gz',
             ROOT / '.cache/plan-original-records.json', DATA / 'world-index.json', DATA / 'hierarchy.json',
             DATA / 'macro-corrections.json'] + [DATA / part for part in read(DATA / 'world-index.json')['parts']]
    report['input_sha256'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    if hashlib.sha256((DATA / report['archive']['path']).read_bytes()).hexdigest() != report['archive']['sha256']:
        raise ValueError('Original archive hash changed')
    REPORT.write_text(json.dumps(report, ensure_ascii=False, separators=(',', ':')))
    print(json.dumps({'changed_retained': len(changed), 'geometry_changes': 0,
                      'macro_changes': len(corrections['changes']), 'spatial_crosswalk_reused': True}), flush=True)


def main():
    current = load_current()
    baseline = load_baseline()
    units = {unit['id']: unit for unit in read(DATA / 'hierarchy.json')}
    old_units = {unit['id']: unit for unit in read(BASE / 'hierarchy.json')}
    before_ids, after_ids = set(baseline), set(current)
    retained = sorted(before_ids & after_ids)
    removed = sorted(before_ids - after_ids)
    added = sorted(after_ids - before_ids)
    changed = retained_changes(baseline, current, old_units, units)
    print(json.dumps({'baseline': len(baseline), 'current': len(current),
                      'removed': len(removed), 'added': len(added),
                      'changed_retained': len(changed)}), flush=True)

    # Take one SQLite read snapshot; another process may seed extra records.
    connection = sqlite3.connect('file:' + str(DATA / 'atlas.sqlite') + '?mode=ro', uri=True)
    connection.execute('BEGIN')
    preservation, failures = original_history(connection)
    archive_rows = [dict(zip(['id', 'name', 'parent_id', 'geometry', 'metadata', 'reference_owner'], row))
                    for row in connection.execute(
                        'SELECT id,name,parent_id,geometry,metadata,reference_owner FROM locations WHERE active=0 ORDER BY id')]
    histories = collections.Counter(row[0] for row in connection.execute('SELECT location_id FROM states'))
    histories.update(row[0] for row in connection.execute('SELECT entity_id FROM entity_history'))
    archive_units = [dict(zip(['id', 'name', 'level', 'parent_id', 'metadata'], row))
                     for row in connection.execute('SELECT id,name,level,parent_id,metadata FROM units ORDER BY id')]
    for unit in archive_units:
        unit['metadata'] = json.loads(unit['metadata'])
    archive_unit_map = {unit['id']: unit for unit in archive_units}
    archive_features = []
    for row in archive_rows:
        parents = []
        parent = row['parent_id']
        seen = set()
        while parent and parent in archive_unit_map and parent not in seen:
            seen.add(parent)
            unit = archive_unit_map[parent]
            parents.append(unit)
            parent = unit['parent_id']
        archive_features.append({'id': row['id'], 'name': row['name'], 'parent_id': row['parent_id'],
                                 'parent_chain': [unit['id'] for unit in parents],
                                 'chain_complete': parent is None,
                                 'geometry': json.loads(row['geometry']),
                                 'metadata': json.loads(row['metadata']),
                                 'reference_owner': row['reference_owner']})
    original_entity_ids = {row[1] for row in read(ROOT / '.cache/plan-original-records.json')['entity_history']['rows']}
    geographic_entity_ids = {row['id'] for row in archive_rows} | {row['id'] for row in archive_units}
    entity_columns = [row[1] for row in connection.execute('PRAGMA table_info(entities)')]
    original_entities = [dict(zip(entity_columns, row)) for row in connection.execute('SELECT * FROM entities ORDER BY id')
                         if row[0] in original_entity_ids and row[0] not in geographic_entity_ids
                         and row[1] == 'settlement']
    archive_payload = {'version': 1, 'kind': 'undated-cartographic-reference-archive',
                       'historical_effective_year': None,
                       'source': 'Original reference locations retained in the atlas SQLite database',
                       'locations': archive_features,
                       'units': archive_units,
                       'original_records': read(ROOT / '.cache/plan-original-records.json'),
                       'original_entities': original_entities,
                       'record_transfer_policy': 'Keep original IDs and records; overlap relationships do not transfer historical attributes.'}
    connection.rollback()
    connection.close()
    archive_path = DATA / 'geographic-migration-archive.json.gz'
    if failures:
        raise ValueError('Original historical records were modified; archive remains untouched')
    archive_payload = preserve_reference_archive(archive_path, archive_payload)
    archive_features = archive_payload['locations']

    # All retained identities use their existing records; only retired geometries
    # and new IDs need a spatial relationship. Include archived earlier revisions.
    candidates = {row['id']: row for row in archive_rows}
    for key in removed:
        old = baseline[key]
        candidates.setdefault(key, {'id': key, 'name': old['properties']['name'],
                                    'parent_id': old['properties']['parent_id'],
                                    'geometry': json.dumps(old['geometry']),
                                    'metadata': json.dumps(old['properties'].get('metadata', {}))})
    ids = sorted(current)
    geometries = [make_valid(shape(current[key]['geometry'])) for key in ids]
    tree = STRtree(geometries)
    current_areas = {}
    archived = []
    reverse = collections.defaultdict(list)
    added_set = set(added)
    database_archived_ids = {row['id'] for row in archive_rows}
    for n, (key, record) in enumerate(sorted(candidates.items()), 1):
        raw = json.loads(record['geometry'])
        geometry = canonical(shape(raw))
        total = area(geometry)
        successors = []
        for i in tree.query(geometry, predicate='intersects'):
            i = int(i)
            cut = geometry.intersection(geometries[i])
            if cut.is_empty or cut.area == 0:
                continue
            overlap = area(cut)
            if overlap <= max(.01, total * 1e-9):
                continue
            successor = ids[i]
            if successor not in current_areas:
                current_areas[successor] = area(geometries[i])
            link = {'id': successor, 'predecessor_share': round(overlap / total, 8),
                    'successor_share': round(min(1, overlap / current_areas[successor]), 8),
                    'overlap_km2': round(overlap / 1e6, 6)}
            successors.append(link)
            if successor in added_set:
                reverse[successor].append({'id': key,
                                           'successor_share': link['successor_share'],
                                           'predecessor_share': link['predecessor_share']})
        successors.sort(key=lambda item: (-item['predecessor_share'], item['id']))
        share = min(1, sum(item['predecessor_share'] for item in successors))
        metadata = json.loads(record['metadata'])
        archived.append({'id': key, 'name': record['name'], 'parent_id': record['parent_id'],
                         'baseline_retired': key in before_ids, 'database_archived': key in database_archived_ids,
                         'geometry_sha256': digest(raw), 'land_km2': round(total / 1e6, 6),
                         'source_url': metadata.get('source_url'), 'license': metadata.get('license'),
                         'historical_records_retained': histories[key], 'successors': successors,
                         'covered_share': round(share, 8), 'uncovered_share': round(1 - share, 8),
                         'status': 'coverage-gap' if share < .99999 else 'represented',
                         'method': 'Undated cartographic overlap; records stay on the predecessor ID'})
        if n % 1000 == 0:
            print('Archived footprint relationships ' + str(n) + '/' + str(len(candidates)), flush=True)

    added_rows = [{'id': key, 'name': current[key]['properties']['name'],
                   'parent_chain': chain(current[key], units),
                   'predecessors': sorted(reverse[key], key=lambda item: (-item['successor_share'], item['id'])),
                   'status': 'related' if reverse[key] else 'no-archived-overlap'} for key in added]
    archived_ids = {row['id'] for row in archived}
    report = {
        'version': 1,
        'scope': 'Every baseline ID and every archived database location; atlas reference revision, not a historical territorial transition.',
        'method': 'WGS84 ellipsoidal land-area intersection with antimeridian normalization and 0.1-degree edge densification. Current location interiors are independently checked for overlap. Positive intersections smaller than max(0.01 square metre, 1e-9 predecessor area) are numerical slivers.',
        'historical_effective_year': None,
        'automatic_record_transfers': 0,
        'archive': {'path': 'geographic-migration-archive.json.gz',
                    'sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                    'bytes': archive_path.stat().st_size,
                    'locations': len(archive_features),
                    'original_entities': len(archive_payload.get('original_entities', [])),
                    'incomplete_archived_chains': sum(not row['chain_complete'] for row in archive_features),
                    'locations_without_recorded_license': sum(not row['metadata'].get('license') for row in archive_features)},
        'counts': {'baseline': len(before_ids), 'current': len(after_ids),
                   'retained_ids': len(retained), 'retired_ids': len(removed), 'added_ids': len(added),
                   'changed_retained_ids': len(changed),
                   'unchanged_retained_ids': len(retained) - len(changed),
                   'archived_database_ids': len(archive_rows), 'archived_crosswalk_ids': len(archived),
                   'coverage_gaps': sum(row['status'] == 'coverage-gap' for row in archived),
                   'new_ids_without_archived_overlap': sum(row['status'] == 'no-archived-overlap' for row in added_rows)},
        'accounting': {'before_complete': len(retained) + len(removed) == len(before_ids),
                       'after_complete': len(retained) + len(added) == len(after_ids),
                       'every_retired_id_crosswalked': set(removed) <= archived_ids,
                       'every_archived_id_crosswalked': {row['id'] for row in archive_rows} <= archived_ids},
        'history_preservation': preservation,
        'history_preservation_failures': failures,
        'retired_baseline_ids': removed,
        'changed_retained': changed,
        'added': added_rows,
        'archived': archived,
        'limitations': [
            'An overlap relationship does not authorize copying population, ownership, culture, religion, or names to a successor.',
            'Coverage gaps remain visible; source footprint revisions and numerical coastline differences are not silently filled.',
            'The database preserves archived geometries and history. A static profile may omit archived geometry until its evidence is requested.',
            'This crosswalk validates identity accounting and preservation, not the semantic quality of every geographic unit.'
        ],
        'input_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in [BASE / 'world-index.json', BASE / 'hierarchy.json', BASE / 'geography.tar.gz',
                                      ROOT / '.cache/plan-original-records.json', DATA / 'world-index.json', DATA / 'hierarchy.json']
                         + [DATA / part for part in read(DATA / 'world-index.json')['parts']]}
    }
    macro_path = DATA / 'macro-corrections.json'
    if macro_path.exists():
        macro = read(macro_path)
        report['reference_changes'] = {
            'macro_corrections': 'macro-corrections.json',
            'macro_changed_locations': len(macro['changes']),
            'macro_changed_groups': len(macro['group_changes']),
            'location_footprints_sha256': macro['footprints_sha256_after'],
            'geometry_changed_locations': sum('geometry' in row['changes'] for row in changed),
            'membership_and_name_changes_are_undated_reference_revisions': True,
            'spatial_relationships_reused': False,
            'original_archive_preserved': True}
        report['input_sha256']['data/macro-corrections.json'] = hashlib.sha256(macro_path.read_bytes()).hexdigest()
    compact_crosswalk(report)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, separators=(',', ':')))
    print(json.dumps({'counts': report['counts'], 'accounting': report['accounting'],
                      'history_preservation_failures': failures}), flush=True)
    assert all(report['accounting'].values())
    assert not failures, failures


if __name__ == '__main__':
    if '--reuse-spatial' in sys.argv:
        refresh_hierarchy_crosswalk()
    else:
        main()
