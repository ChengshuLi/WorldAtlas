"""Reproducible worldwide review gate, independent of source-inventory completion.

Every active ID gets every rubric check. Geometric screens never substitute for
an independent geographic-purpose decision. No live geography is modified.
"""
import argparse, collections, functools, gzip, hashlib, json, pathlib, re, statistics, importlib.util
from pyproj import Geod
from shapely import STRtree
from shapely.geometry import shape

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEVELS = ('location', 'province', 'area', 'region', 'subcontinent', 'continent')
BAD_ROLE = re.compile(r'^(?:unknown|nan|adm[0-5]|not independently established|named local administrative territory)$', re.I)
BAD_NAME = re.compile(r'unnamed|unknown|unorgani[sz]ed|^region\s+\d|^division\s*(?:no\.?\s*)?\d|^\d+$|\ufffd|\*$', re.I)
FINE_ROLE = re.compile(r'\bward|\b(?:local|community) board|\bborough', re.I)
GEO = Geod(ellps='WGS84')


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measured_area(geometry):
    parts = list(geometry.geoms) if geometry.geom_type == 'MultiPolygon' else [geometry]
    total = 0
    for part in parts:
        x, y = part.exterior.xy
        total += abs(GEO.polygon_area_perimeter(x, y)[0])
        for ring in part.interiors:
            x, y = ring.xy
            total -= abs(GEO.polygon_area_perimeter(x, y)[0])
    return max(0, total / 1e6)


def check(status, fact, evidence=None):
    assert status in ('supported', 'open', 'attention', 'not-applicable')
    return {'status': status, 'fact': fact, **({'evidence': evidence} if evidence else {})}


def semantic_status(checks, children_supported=True):
    """Completion is conjunctive; an inventory or one supported boundary cannot pass."""
    return 'supported' if children_supported and checks and all(
        x['status'] in ('supported', 'not-applicable') for x in checks.values()
    ) else 'open'


def assert_complete_inventory(expected, actual, label):
    actual = list(actual)
    if len(set(actual)) != len(actual) or set(expected) != set(actual):
        raise ValueError(f'{label}: duplicate, missing or unexpected reviewed IDs')


def source_atom_resolver(props, historic_changes):
    @functools.lru_cache(None)
    def atoms(id, stack=()):
        if id in stack:
            raise ValueError(f'Cyclic original-source identity: {id}')
        metadata = props.get(id, {}).get('metadata', {})
        source = metadata.get('source_id', '')
        if id.startswith('gb:'):
            return (id,)
        if source.startswith('gb:') and re.fullmatch(r'atlas:district:[A-Z]{3}\+00\?:\d+B\d+', id):
            return (source + ':' + id.rsplit(':', 1)[1],)
        members = metadata.get('source_member_ids') or historic_changes.get(id)
        if members:
            return tuple(sorted({atom for member in members for atom in atoms(
                source + ':' + member if source.startswith('gb:') and re.fullmatch(r'\d+B\d+', member) else member,
                stack + (id,))}))
        if source.startswith('gb:') and metadata.get('original_id'):
            return (source + ':' + metadata['original_id'],)
        if source.startswith('ISTAT:SLL2011-2018:'):
            return (source,)
        if id.startswith('country-'):
            return ('natural-earth:adm0:' + id.split('-', 1)[1],)
        if id.startswith('atlas:coverage:'):
            return ('natural-earth:adm1:' + id.split(':', 2)[2],)
        if re.fullmatch(r'[A-Z]{3}(?:-\d+|\+\d+\?)', id):
            return ('natural-earth:adm1:' + id,)
        if id.startswith(('atlas:district:BRA-', 'atlas:district:ESP-')):
            return (id,)
        return ('unresolved:' + id,)
    return atoms


def apply_resolutions(id, checks, resolutions, footprint_hash):
    """Dataset evidence can resolve measured questions without editing application code."""
    record = resolutions.get(id)
    if record is None:
        return checks
    if record.get('footprint_sha256') != footprint_hash:
        raise ValueError(f'Stale semantic resolution footprint: {id}')
    for key, decision in record.get('checks', {}).items():
        if key not in checks or key in ('complete_unique_chain', 'valid_land_footprint',
                'nonoverlapping_interiors', 'complete_member_footprint', 'independent_children', 'external_source_quality'):
            raise ValueError(f'Cannot override structural or unknown check: {id}/{key}')
        evidence = decision.get('evidence', [])
        if decision.get('status') not in ('supported', 'not-applicable') or not evidence or not decision.get('rationale'):
            raise ValueError(f'Incomplete independent resolution: {id}/{key}')
        if not all(e.get('url', '').startswith(('https://', 'http://')) and e.get('inspected_fact') for e in evidence):
            raise ValueError(f'Unsourced semantic resolution: {id}/{key}')
        checks[key] = check(decision['status'], {'rationale': decision['rationale'],
            'measured_diagnostic': checks[key]}, evidence)
    return checks


def main(data, resolutions_path=None):
    index = load(data / 'world-index.json')
    inputs = ['world-index.json', 'hierarchy.json', 'location-policy.json',
              'world-review.json', 'coverage-report.json', 'global-refinement-report.json', 'semantic-report.json'] + index['parts']
    files = sorted((data / 'geographic-decisions').glob('*.json'))
    if len(files) != 6:
        raise ValueError('All six frozen continent decision inventories are required')
    inputs += [str(p.relative_to(data)) for p in files]
    if (data/'namibia-source-quality-annotations.json').exists():
        inputs.append('namibia-source-quality-annotations.json')
        inputs += [r['path'] for r in load(data/'namibia-source-quality-annotations.json')['profile_review']['public_evidence_files']]
    hashes = {p: digest(data / p) for p in inputs}
    resolution_hash = digest(resolutions_path) if resolutions_path else None
    resolutions = load(resolutions_path) if resolutions_path else {}
    features = [f for p in index['parts'] for f in load(data / p)['features']]
    units = {u['id']: u for u in load(data / 'hierarchy.json')}
    spec=importlib.util.spec_from_file_location('external_source_quality',pathlib.Path(__file__).with_name('external-source-quality.py'))
    external=importlib.util.module_from_spec(spec);spec.loader.exec_module(external)
    source_quality=external.validated_reviews(data,features,units)
    assert_complete_inventory([f['id'] for f in features], [f['id'] for f in features], 'locations')
    if len([u for u in units.values() if u['level'] == 'continent']) != 6:
        raise ValueError('Exactly six inhabited continents are required')
    profiles = load(data / 'location-policy.json')['countries']
    world = load(data / 'world-review.json')
    territory_by_owner = {r['owner']: r for r in world['territories']}
    if {f['properties']['reference_owner'] for f in features} != set(territory_by_owner):
        raise ValueError('Reference-owner crosswalk is stale')
    inspections = {}
    for path in files:
        contents = load(path)
        for i, row in enumerate(contents['location_review']):
            for id in row['ids']:
                if id in inspections:
                    raise ValueError(f'Duplicate original review: {id}')
                inspections[id] = {'file': str(path.relative_to(data)), 'row': i, 'review': row}
    # Newly merged locations can carry an explicit predecessor crosswalk. No implicit name match.
    all_ids = {f['id'] for f in features}
    missing = all_ids - set(inspections)
    for f in features:
        if f['id'] not in missing:
            continue
        predecessors = f['properties']['metadata'].get('source_territory_predecessor_ids', [])
        if not predecessors or any(id not in inspections for id in predecessors):
            raise ValueError(f'No complete independent inspection crosswalk: {f["id"]}')
        inspections[f['id']] = {'predecessors': predecessors, 'review': {'status': 'open',
            'rationale': 'Merged geometry requires its own current-footprint review'}}
    geoms = [shape(f['geometry']) for f in features]
    areas = [measured_area(g) for g in geoms]
    tree = STRtree(geoms)
    owner_areas = collections.defaultdict(list)
    source_members = collections.defaultdict(list)
    props = {f['id']: f['properties'] for f in features}
    historic_changes = {r['id']: r.get('replaces', []) for r in load(data / 'semantic-report.json')['changes']}

    atoms = source_atom_resolver(props, historic_changes)
    for i, f in enumerate(features):
        p = f['properties']; m = p['metadata']
        owner_areas[p['reference_owner']].append(areas[i])
        for atom in atoms(f['id']):
            source_members[atom].append(f['id'])
    # A repeat is a question, not a forced merge: documented physical partitions may be intentional.
    repeated = collections.defaultdict(set)
    for ids in source_members.values():
        if len(ids) > 1:
            for id in ids: repeated[id].update(ids)
    repeated = {id: sorted(ids) for id, ids in repeated.items()}
    footprint_hashes = {f['id']: hashlib.sha256(json.dumps(f['geometry'], sort_keys=True, separators=(',', ':')).encode()).hexdigest() for f in features}
    unexpected = set(resolutions) - all_ids - set(units)
    if unexpected: raise ValueError(f'Resolution contains inactive or unknown IDs: {sorted(unexpected)[:5]}')
    locations = []; members = collections.defaultdict(list); children = collections.defaultdict(list)
    for u in units.values():
        expected = LEVELS[LEVELS.index(u['level']) + 1] if u['level'] != 'continent' else None
        if expected and (u['parent_id'] not in units or units[u['parent_id']]['level'] != expected):
            raise ValueError(f'Invalid adjacent-tier group parent: {u["id"]}')
        if not expected and u['parent_id'] is not None:
            raise ValueError(f'Continent has a parent: {u["id"]}')
        if u['parent_id']:
            children[u['parent_id']].append(u['id'])
    for i, f in enumerate(features):
        p = f['properties']; m = p['metadata']; owner = p['reference_owner']; evidence = inspections[f['id']]
        row = evidence['review']; role = m.get('source_role') or m.get('location_basis') or m.get('administrative_level')
        neighbors = [int(j) for j in tree.query(geoms[i], predicate='intersects') if int(j) != i]
        neighbor_areas = [areas[j] for j in neighbors if areas[j] > 0]
        median_neighbor = statistics.median(neighbor_areas) if neighbor_areas else None
        median_owner = statistics.median(owner_areas[owner])
        ratio = areas[i] / median_neighbor if median_neighbor else None
        scale_attention = bool((ratio and (ratio > 20 or ratio < .05)) or areas[i] > 50000)
        overlaps = [features[j]['id'] for j in neighbors if geoms[i].intersection(geoms[j]).area > 1e-10]
        chain = []; parent = p['parent_id']
        for level in LEVELS[1:]:
            if parent not in units or units[parent]['level'] != level:
                raise ValueError(f'Incomplete adjacent-tier chain: {f["id"]}')
            chain.append(parent); members[parent].append(f['id']); parent = units[parent]['parent_id']
        if parent is not None or units[chain[-1]]['name'] == 'Antarctica':
            raise ValueError(f'Invalid continent: {f["id"]}')
        children[p['parent_id']].append(f['id'])
        parent_shares = {k: m[k] for k in ('framework_overlap', 'prefecture_overlap',
            'hierarchy_overlap', 'geographic_overlap') if isinstance(m.get(k), (float, int))}
        weak_parent = bool(m.get('border_parent_review')) or any(v < .8 for v in parent_shares.values())
        prior_reasons = row.get('specific_reasons') or row.get('remaining_reasons') or row.get('source_coverage_findings') or []
        parts = len(geoms[i].geoms) if geoms[i].geom_type == 'MultiPolygon' else 1
        independent = row.get('status') == 'supported'
        provenance = {'source_id': m.get('source_id'), 'url': m.get('source_url'),
            'role': role, 'location_basis': m.get('location_basis'), 'represented_year': m.get('reference_year'), 'license': m.get('license')}
        checks = {
            'complete_unique_chain': check('supported', chain),
            'external_source_quality': check('open' if f['id'] in source_quality['locations'] else 'not-applicable', source_quality['locations'].get(f['id'], 'No separately filed source-quality issue; this does not certify source completeness')),
            'valid_land_footprint': check('supported' if geoms[i].is_valid and areas[i] > 0 else 'attention',
                {'valid': geoms[i].is_valid, 'wgs84_diagnostic_km2': round(areas[i], 6)}),
            'nonoverlapping_interiors': check('attention' if overlaps else 'supported', overlaps),
            'published_source_role': check('supported' if role and not BAD_ROLE.search(role) else 'open', provenance),
            'source_vintage_and_license': check('supported' if m.get('license') and re.search(r'\b\d{4}\b', str(m.get('reference_year', ''))) else 'open',
                {'year': m.get('reference_year'), 'license': m.get('license')}),
            'local_geographic_purpose': check('supported' if independent else 'open',
                row.get('rationale', 'Independent local purpose is not approved'), {k: v for k, v in evidence.items() if k != 'review'}),
            'neighboring_granularity': check('attention' if scale_attention else 'supported',
                {'neighbor_count': len(neighbors), 'neighbor_median_km2': round(median_neighbor, 6) if median_neighbor else None,
                 'area_ratio': round(ratio, 6) if ratio else None, 'owner_median_km2': round(median_owner, 6),
                 'rule': '20-fold adjacent-area contrast or >50,000 km² triggers research; unequal areas are not rejected'}),
            'urban_fragmentation': check('attention' if role and FINE_ROLE.search(role) else 'open' if not independent else 'supported',
                {'role': role, 'aggregation_member_count': len(m.get('source_member_ids', [])),
                 'note': 'A named administrative territory does not independently establish a whole urban settlement'}),
            'anonymous_remainders': check('attention' if BAD_NAME.search(p['name']) else 'supported',
                {'name': p['name'], 'name_evidence_status': m.get('name_evidence_status')}),
            'disconnected_territories': check('attention' if parts > 1 else 'supported', {'components': parts,
                'note': 'Islands/enclaves can be legitimate; a multipart source is not automatically approved or split'}),
            'fragmented_source_identity': check('attention' if f['id'] in repeated else 'open' if any(a.startswith('unresolved:') for a in atoms(f['id'])) else 'supported', {'source_atoms': list(atoms(f['id'])), 'other_active_locations': repeated.get(f['id'], [])}),
            'source_omissions_and_islands': check('open', {'report': 'coverage-report.json',
                'finer_coverage': 'global-refinement-report.json', 'source_findings': prior_reasons,
                'note': 'Reference-coastline screening alone does not certify all islands or original source land'}),
            'parent_correspondence': check('attention' if weak_parent else 'supported',
                {'recorded_overlap': parent_shares, 'border_parent_review': m.get('border_parent_review')}),
        }
        checks = apply_resolutions(f['id'], checks, resolutions, footprint_hashes[f['id']])
        locations.append({'id': f['id'], 'footprint_sha256': footprint_hashes[f['id']], 'name': p['name'], 'owner': owner, 'province_id': p['parent_id'],
            'continent_id': chain[-1], 'region_id': chain[2], 'status': semantic_status(checks), 'checks': checks})
        if (i + 1) % 10000 == 0:
            print(json.dumps({'measured_locations': i + 1, 'total': len(features)}), flush=True)
    supported = {r['id'] for r in locations if r['status'] == 'supported'}
    groups = []
    for level in LEVELS[1:]:
        for id, u in sorted(units.items()):
            if u['level'] != level:
                continue
            assessment = u['metadata'].get('semantic_review', {})
            direct = children[id]
            checks = {
                'external_source_quality': check('open' if id in source_quality['groups'] else 'not-applicable', source_quality['groups'].get(id, 'No separately filed source-quality issue; source-purpose and child checks remain independent')),
                'complete_member_footprint': check('supported' if members[id] and direct else 'attention', {'method': 'Union of exact member locations',
                    'locations': len(members[id]), 'children': len(direct)}),
                'tier_geographic_purpose': check('supported' if assessment.get('boundary_status') == 'supported' else 'open',
                    assessment.get('rationale', 'Independent tier purpose is unapproved'), assessment.get('evidence')),
                'repeated_tiers': check('attention' if len(direct) == 1 else 'supported',
                    {'single_child': direct[0] if len(direct) == 1 else None,
                     'note': 'Coextensive compact territories require an explicit sourced exception'}),
                'remaining_boundary_questions': check('open' if assessment.get('remaining_reasons') else 'supported',
                    assessment.get('remaining_reasons', [])),
                'independent_children': check('supported' if all(child in supported for child in direct) else 'open',
                    {'supported': sum(child in supported for child in direct), 'total': len(direct)}),
            }
            member_hash = hashlib.sha256(json.dumps(sorted([[member, footprint_hashes[member]] for member in members[id]]), separators=(',', ':')).encode()).hexdigest()
            checks = apply_resolutions(id, checks, resolutions, member_hash)
            status = semantic_status(checks)
            if status == 'supported': supported.add(id)
            groups.append({'id': id, 'footprint_sha256': member_hash, 'name': u['name'], 'level': level, 'parent_id': u['parent_id'],
                'status': status, 'checks': checks})
    assert_complete_inventory(units, [g['id'] for g in groups], 'groups')
    counts = collections.Counter(f['properties']['reference_owner'] for f in features)
    territories = []
    for owner in sorted(counts):
        old = territory_by_owner[owner]; iso = old.get('iso')
        territories.append({'owner': owner, 'iso': iso, 'source_country_codes': old.get('source_country_codes', []), 'policy_present': iso in profiles,
            'locations': counts[owner], 'source_roles': old.get('source_roles', []),
            'sources': old['sources'], 'issues': old.get('issues', []),
            'source_quality_review': source_quality['profiles'].get(owner),
            'status': 'open', 'note': 'All member IDs have full rubric outcomes; aggregate source assessment is separate from semantic closure'})
    checks_count = {}
    for kind, rows in [('location', locations), ('group', groups)]:
        for row in rows:
            for key, result in row['checks'].items():
                checks_count.setdefault(f'{kind}:{key}', collections.Counter())[result['status']] += 1
    profiles_crosswalk = {iso: [r['owner'] for r in territories if r['iso'] == iso or iso in r['source_country_codes']] for iso in sorted(profiles)}
    for p, old in hashes.items():
        if digest(data / p) != old:
            raise ValueError(f'Input changed during the exhaustive audit: {p}; rerun against the completed migration')
    if resolutions_path and digest(resolutions_path) != resolution_hash:
        raise ValueError('Independent semantic resolutions changed during review')
    structural_complete = all(row['checks'][key]['status'] == 'supported' for row in locations
        for key in ('complete_unique_chain', 'valid_land_footprint', 'nonoverlapping_interiors')) and all(
        row['checks']['complete_member_footprint']['status'] == 'supported' for row in groups)
    result = {'version': 1, 'scope': 'Every current location, every parent group, all reference-owner groups and all policy profiles; exhaustive review coverage is distinct from independent semantic approval.',
        'audit_complete': True, 'structural_complete': structural_complete, 'semantic_complete': all(r['status'] == 'supported' for r in locations + groups),
        'source_quality_reviews': source_quality['manifest'], 'input_sha256': hashes, 'code_sha256': digest(pathlib.Path(__file__)), 'source_review_code_sha256': {p:digest(pathlib.Path(__file__).with_name(p)) for p in ['external-source-quality.py','prepare-namibia-source-annotations.py']}, 'independent_resolutions_sha256': resolution_hash, 'counts': {'locations': len(locations), 'groups': len(groups),
            'reference_owner_groups': len(territories), 'policy_profiles': len(profiles)},
        'level_counts': dict(collections.Counter(g['level'] for g in groups)),
        'check_status_counts': {k: dict(v) for k, v in checks_count.items()},
        'location_status_counts': dict(collections.Counter(r['status'] for r in locations)),
        'group_status_counts': dict(collections.Counter(r['status'] for r in groups)),
        'policy_crosswalk': profiles_crosswalk,
        'unmatched_reference_groups': [r['owner'] for r in territories if not r['policy_present']],
        'unmatched_policy_profiles': [iso for iso, owners in profiles_crosswalk.items() if not owners],
        'geometry_measurement': 'WGS84 pyproj polygon diagnostic, exterior minus holes; current planar intersections for adjacency and overlap. Majority ownership uses its separate antimeridian-safe exact land-area preparation.',
        'audit_order': list(reversed(LEVELS)), 'locations': locations, 'groups': groups, 'territories': territories}
    output = data / 'global-semantic-closure.json.gz'
    output.write_bytes(gzip.compress(json.dumps(result, ensure_ascii=False, separators=(',', ':')).encode(), mtime=0))
    print(json.dumps({'output': str(output), 'bytes': output.stat().st_size, 'counts': result['counts'],
        'structural_complete': structural_complete, 'semantic_complete': result['semantic_complete'], 'checks': result['check_status_counts']}), flush=True)
    if not structural_complete:
        raise ValueError('Publication blocked: unresolved structural geography defects; diagnostics were saved')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=pathlib.Path, default=ROOT / 'data')
    parser.add_argument('--resolutions', type=pathlib.Path, help='Optional independently sourced current-footprint resolutions; does not modify geography')
    args = parser.parse_args()
    main(args.data, args.resolutions)
