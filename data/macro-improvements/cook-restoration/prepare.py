#!/usr/bin/env python3
"""Prepare an immutable Cook correction proposal; never edit installed geography."""
import argparse, copy, gzip, hashlib, json, pathlib, subprocess, sys
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, shape, mapping, box
from shapely.ops import unary_union
from shapely import STRtree
from pyproj import Geod

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from ellipsoidal_area import area

EVIDENCE = ROOT / 'data/macro-improvements/macro-coverage-oceania'
IDS = {'Manuae': 'COK-4951', 'Aitutaki': 'COK-4956', 'Manihiki': 'COK-4961'}
PALMERSTON = 'atlas:macro-coverage:location:bcec1e1e5eb00bd49e80'
PROVINCE = 'atlas:macro-coverage:province:29932af2f8043947ba8a'
SOUTH = 'framework:area:cook-is:ef123ee6d88f'
TIERS = ['province', 'area', 'region', 'subcontinent', 'continent']


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    raw = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()
    path.write_bytes(gzip.compress(raw, mtime=0) if path.suffix == '.gz' else raw)


def chain(parent, units):
    result = []
    for tier in TIERS:
        unit = units[parent]
        if unit['level'] != tier:
            raise ValueError('Non-adjacent parent tier')
        result.append(parent)
        parent = unit['parent_id']
    if parent is not None:
        raise ValueError('Continent has a parent')
    return result


def coast(source):
    """Directed complete coastline rings minus explicit complete inland water ways."""
    path = EVIDENCE / source['path']
    raw = gzip.decompress(path.read_bytes())
    if hashlib.sha256(raw).hexdigest() != source['sha256']:
        raise ValueError('Original OSM bytes changed')
    xml = ET.fromstring(raw)
    nodes = {n.get('id'): (float(n.get('lon')), float(n.get('lat'))) for n in xml.findall('node')}
    segments, water, waters, versions = [], [], [], []
    for way in xml.findall('way'):
        tags = {t.get('k'): t.get('v') for t in way.findall('tag')}
        if tags.get('natural') not in ['coastline', 'water']:
            continue
        refs = [n.get('ref') for n in way.findall('nd')]
        if not all(n in nodes for n in refs):
            raise ValueError('Incomplete source nodes: ' + way.get('id'))
        version = {k: way.get(k) for k in ['id', 'version', 'timestamp']}
        if tags.get('natural') == 'coastline':
            segments.append({'refs': refs, 'versions': [version]})
        else:
            if refs[0] != refs[-1]:
                raise ValueError('Unclosed explicit inland water way')
            polygon = Polygon([nodes[n] for n in refs])
            if not polygon.is_valid:
                raise ValueError('Invalid water polygon, do not silently repair')
            water.append(polygon)
            waters.append({'version': version, 'tags': tags, 'geometry': mapping(polygon)})
    # Water relations require explicit assembly; no ignored masking evidence.
    for relation in xml.findall('relation'):
        tags = {t.get('k'): t.get('v') for t in relation.findall('tag')}
        if tags.get('natural') == 'water':
            raise ValueError('Water multipolygon requires a separately reviewed assembler')
    geod, outer, inner = Geod(ellps='WGS84'), [], []
    while segments:
        row = segments.pop()
        refs, used = row['refs'], row['versions']
        while refs[0] != refs[-1]:
            matches = [i for i, candidate in enumerate(segments) if candidate['refs'][0] == refs[-1]]
            if len(matches) != 1:
                raise ValueError('Ambiguous or incomplete coastline chain')
            following = segments.pop(matches[0])
            refs += following['refs'][1:]
            used += following['versions']
        polygon = Polygon([nodes[n] for n in refs])
        if not polygon.is_valid:
            raise ValueError('Invalid coastline polygon, do not silently repair')
        (outer if geod.geometry_area_perimeter(polygon)[0] > 0 else inner).append(polygon)
        versions += used
    land = unary_union(outer)
    mask = unary_union(inner + water)
    dry = land.difference(mask)
    if dry.is_empty or not dry.is_valid or dry.geom_type not in ['Polygon', 'MultiPolygon']:
        raise ValueError('Invalid final dry-land source footprint')
    if not box(*source['bbox']).covers(dry):
        raise ValueError('A full source footprint extends outside the inspected named-domain bbox')
    return dry, {'coastline_land_rings': len(outer), 'coastline_water_rings': len(inner),
                 'explicit_water_ways': waters, 'coastline_versions': sorted(versions, key=lambda v: v['id']),
                 'dry_land_area_m2': area(dry), 'water_mask_removed_m2': area(land.intersection(mask)),
                 'source_xml_path': str(path.relative_to(ROOT)), 'source_raw_sha256': source['sha256'],
                 'source_archive_sha256': sha(path), 'url': source['url'], 'license': 'ODbL 1.0',
                 'attribution': '© OpenStreetMap contributors', 'supported_from': 2026, 'supported_to': 2027}


def prepare(output):
    output = output.resolve()
    if output.exists() or output == ROOT / 'data' or ROOT / 'data' in output.parents and HERE not in output.parents:
        raise ValueError('Use a fresh output directory, never installed data')
    for source in read(HERE / 'sources.json'):
        if sha(HERE / source['path']) != source['sha256']:
            raise ValueError('Cook source archive hash changed')
    originals = read(HERE / 'original-natural-earth-features.json.gz')['features']
    if {f['properties']['adm1_code']: f['properties']['name'] for f in originals} != {
            'COK-4951': 'Aitutaki', 'COK-4956': 'Palmerston', 'COK-4961': 'Manihiki'}:
        raise ValueError('Original source identity labels differ')
    units_list = read(ROOT / 'data/hierarchy.json')
    units = {u['id']: u for u in units_list}
    index = read(ROOT / 'data/world-index.json')
    features = [f for part in index['parts'] for f in read(ROOT / 'data' / part)['features']]
    by_id = {f['id']: f for f in features}
    if len(by_id) != len(features) or PALMERSTON in by_id or PROVINCE in units:
        raise ValueError('Duplicate or already installed creation identity')
    before = [copy.deepcopy(by_id[i]) for i in IDS.values()]
    parent_ids = {f['properties']['parent_id'] for f in before}
    # An existing group rename must not rename unrelated members.
    for name in ['Manuae', 'Aitutaki']:
        identifier = IDS[name]
        parent = by_id[identifier]['properties']['parent_id']
        if [f['id'] for f in features if f['properties']['parent_id'] == parent] != [identifier]:
            raise ValueError('Existing province is not a one-location source group')
    sources = {s['name']: s for s in read(EVIDENCE / 'osm-sources.json')}
    footprints, checks = {}, {}
    for name in [*IDS, 'Palmerston']:
        footprints[name], checks[name] = coast(sources[name])
    # Exact source unit names/physical identity are independent of reference-owner labels.
    after, group_updates, operations = [], [], []
    for name, identifier in IDS.items():
        original = by_id[identifier]
        candidate = copy.deepcopy(original)
        candidate['properties']['name'] = name
        metadata = candidate['properties'].setdefault('metadata', {})
        metadata['reference_identity_correction'] = {
            'issue': 502, 'physical_id_preserved': True, 'original_reference_name': original['properties']['name'],
            'source_original_id': identifier, 'historical_name_inferred': False,
            'original_reference_label_is_not_a_verified_alias': True, 'supported_from': 2026, 'supported_to': 2027}
        if name == 'Manihiki':
            candidate['geometry'] = mapping(footprints[name])
            metadata['footprint_correction_source'] = checks[name]
        if name != 'Manihiki':
            assert candidate['geometry'] == original['geometry']
            parent = original['properties']['parent_id']
            group = copy.deepcopy(units[parent])
            group['name'] = name
            group.setdefault('metadata', {})['reference_identity_correction'] = copy.deepcopy(metadata['reference_identity_correction'])
            group_updates.append({'id': parent, 'before': units[parent], 'after': group})
        after.append(candidate)
        operations.append({'kind': 'reference-name-correction' if name != 'Manihiki' else 'existing-whole-atoll-footprint-correction',
                           'id': identifier, 'before_name': original['properties']['name'], 'after_name': name,
                           'before_geometry_sha256': hashlib.sha256(json.dumps(original['geometry'], separators=(',', ':')).encode()).hexdigest(),
                           'original_geometry_preserved_in_archive': True, 'parent_chain': chain(original['properties']['parent_id'], units),
                           'historical_claims_transfer': False, 'historical_labels_changed': False})
    new_group = {'id': PROVINCE, 'name': 'Palmerston Atoll', 'level': 'province', 'parent_id': SOUTH,
                 'metadata': {'source': 'Named Southern Cook atoll geographic grouping',
                              'source_url': 'https://en.wikipedia.org/wiki/Palmerston_Island',
                              'basis': 'Entire physically named atoll; every source dry-land islet remains one location',
                              'single_location_exception': 'Remote named atoll is already one coherent local territory; do not invent rock-level locations',
                              'reference_year': 2026, 'regional_interior_review': 'open'}}
    units[PROVINCE] = new_group
    new_location = {'type': 'Feature', 'id': PALMERSTON, 'properties': {
        'id': PALMERSTON, 'name': 'Palmerston', 'parent_id': PROVINCE,
        'metadata': {'source_name': 'OpenStreetMap', 'source_id': 'osm-api-2026-10-02',
                     'source_identity': 'osm:named-land:southern-cook-true-palmerston',
                     'source_url': sources['Palmerston']['url'], 'license': 'ODbL 1.0', 'reference_year': 2026,
                     'footprint_correction_source': checks['Palmerston'], 'historical_attributes_inferred': False,
                     'location_role': 'One whole named atoll dry-land territory, excluding sourced lagoon water'}},
        'geometry': mapping(footprints['Palmerston'])}
    geometries = [shape(f['geometry']) for f in features if f['id'] != IDS['Manihiki']]
    tree = STRtree(geometries)
    overlap_results = []
    for identifier, geometry in [(IDS['Manihiki'], footprints['Manihiki']), (PALMERSTON, footprints['Palmerston'])]:
        overlaps = [area(geometry.intersection(geometries[int(j)])) for j in tree.query(geometry, predicate='intersects')]
        if any(a > .001 for a in overlaps):
            raise ValueError('Correction introduces competing positive-area land')
        overlap_results.append({'id': identifier, 'compared_existing_locations': len(geometries), 'maximum_overlap_m2': max(overlaps, default=0)})
    # Account for removed source water, including a generalized lagoon-filled outline.
    old_manihiki = shape(by_id[IDS['Manihiki']]['geometry'])
    checks['Manihiki']['old_outline_area_m2'] = area(old_manihiki)
    checks['Manihiki']['old_outline_retained_dry_land_m2'] = area(old_manihiki.intersection(footprints['Manihiki']))
    checks['Manihiki']['old_outline_reclassified_nonland_m2'] = area(old_manihiki.difference(footprints['Manihiki']))
    preserved = {}
    entity_matches = []
    homonyms = []
    for path in sorted((ROOT / 'data/hosted-catalog').glob('batch-*.json')):
        batch = read(path)
        for table, records in batch.items():
            if not isinstance(records, list):
                continue
            if table == 'entities':
                if any(r.get('id') in [PALMERSTON, PROVINCE] for r in records):
                    raise ValueError('Creation identity already exists in retained registry')
                homonyms += [r for r in records if r.get('name', '').casefold() == 'palmerston']
            rows = [r for r in records if isinstance(r, dict) and any(r.get(k) in set(IDS.values()) | parent_ids for k in ['id', 'location_id', 'entity_id'])]
            if rows:
                preserved[str(path.relative_to(ROOT))] = {'source_sha256': sha(path), 'rows': rows, 'table': table}
                if table == 'entities':
                    entity_matches += rows
    archive = {'locations': before, 'units': [units_list[[u['id'] for u in units_list].index(p)] for p in sorted(parent_ids)],
               'hosted_catalog_records': preserved, 'history_transfer': False,
               'live_private_records_checked': False, 'live_check_required_before_apply': True}
    if {r['id'] for r in entity_matches if r['kind'] == 'location'} != set(IDS.values()):
        raise ValueError('Missing retained original identities')
    archive_scan = []
    archived_records = {}
    for name in ['geographic-migration-archive.json.gz', 'geographic-repair-evidence/archive.json.gz']:
        path = ROOT / 'data' / name
        document = read(path)
        rows = document['locations']
        records = document.get('original_records', document.get('records', {}))
        # Legacy archive rows have no column names. Preserve any matching original
        # row verbatim, rather than interpreting or redistributing its attributes.
        archived_records[name] = {table: [row for row in (value.get('rows', []) if isinstance(value, dict) else value)
                                                  if any(identifier in json.dumps(row) for identifier in IDS.values())]
                                 for table, value in records.items()}
        matches = []
        for row in rows:
            raw = row.get('feature', row).get('geometry')
            if isinstance(raw, str):
                raw = json.loads(raw)
            if raw is None:
                raise ValueError('Archived location has no inspectable original geometry')
            geometry = shape(raw)
            if geometry.intersects(footprints['Palmerston']) and area(geometry.intersection(footprints['Palmerston'])) > .001:
                matches.append(row['id'])
        if matches:
            raise ValueError('Palmerston has an archived physical predecessor; no new identity allowed')
        archive_scan.append({'path': str(path.relative_to(ROOT)), 'sha256': sha(path),
                             'location_count': len(rows), 'Palmerston_positive_area_predecessors': matches})
    archive['retained_archived_records'] = archived_records
    patch = {'version': 1, 'issue': 502, 'input_geography_version': 3, 'supported_from': 2026, 'supported_to': 2027,
             'input_hierarchy_sha256': sha(ROOT / 'data/hierarchy.json'),
             'input_part_sha256': {part: sha(ROOT / 'data' / part) for part in index['parts']},
             'operations': operations, 'existing_location_updates': after, 'existing_group_updates': group_updates,
             'added_features': [new_location], 'added_groups': [new_group], 'source_checks': checks,
             'added_parent_chain': chain(PROVINCE, units), 'overlap_checks': overlap_results,
             'archived_identity_scan': archive_scan, 'Palmerston_retained_registry_homonyms': homonyms,
             'history_transfer': False, 'publication_ready': False,
             'holds': ['Root must check private live identity/claims and all archived footprint versions before applying.',
                       'Names-only Manuae/Aitutaki retain partial existing footprints; their sourced whole-atoll extensions are recommendations, not approved updates.',
                       'Do not apply corrected present-day footprints or labels retroactively as dated historical evidence.']}
    output.mkdir(parents=True)
    source_identity = 'osm:named-land:southern-cook-true-palmerston'
    source_wrapper = {'type': 'FeatureCollection', 'features': [{
        'type': 'Feature', 'id': source_identity, 'geometry': mapping(footprints['Palmerston']),
        'properties': {'named_territory': 'Palmerston', 'derivation': checks['Palmerston']}}]}
    write(output / 'palmerston-source.geojson', source_wrapper)
    patch['creation_proof_after_name_crosswalk'] = {
        'location_id': PALMERSTON, 'parent_chain': patch['added_parent_chain'],
        'source': {'path': 'palmerston-source.geojson', 'identity': source_identity,
                   'sha256': sha(output / 'palmerston-source.geojson'), 'url': sources['Palmerston']['url'],
                   'license': 'ODbL 1.0', 'attribution': '© OpenStreetMap contributors',
                   'supported_from': 2026, 'supported_to': 2027,
                   'raw_source_archive': checks['Palmerston']['source_xml_path'],
                   'raw_source_sha256': checks['Palmerston']['source_raw_sha256'],
                   'derivation': 'Directed complete coastline rings minus complete explicit inland-water ways; source nodes unrounded'},
        'identity_review': {'status': 'distinct-new-territory',
                            'evidence_url': 'https://en.wikipedia.org/wiki/Palmerston_Island',
                            'same_name_existing_ids': sorted(r['id'] for r in homonyms if r['kind'] == 'location' and r['id'] != 'COK-4956'),
                            'rationale': 'Actual Palmerston atoll has no current or archived physical predecessor. Former COK-4956 Palmerston label was erroneous on the physically distinct Aitutaki; name-only crosswalk must precede this creation proof.'}}
    write(output / 'candidate-patch.json', patch)
    write(output / 'originals-and-records.json.gz', archive)
    write(output / 'source-dry-land.geojson.gz', {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'id': name, 'properties': {'name': name, 'source': checks[name]}, 'geometry': mapping(footprints[name])}
        for name in checks]})
    subprocess.run(['node', str(HERE / 'grid-check.mjs'), str(output)], check=True)
    manifest = {'version': 1, 'issue': 502, 'preparation_script_sha256': sha(pathlib.Path(__file__)),
                'files': {p.name: {'sha256': sha(p)} for p in sorted(output.iterdir())},
                'installed_geography_changed': False, 'historical_records_changed': False, 'publication_ready': False}
    write(output / 'index.json', manifest)
    return {'prepared': True, 'updated_physical_ids': list(IDS.values()), 'new_location_id': PALMERSTON,
            'source_water_mask_removed_m2': {name: row['water_mask_removed_m2'] for name, row in checks.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    print(json.dumps(prepare(parser.parse_args().output)))
