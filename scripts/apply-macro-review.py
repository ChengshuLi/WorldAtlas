"""Apply sourced macro-membership reference corrections without changing land.

All names describe modern/reference geography. Parent changes are cartographic
reference migrations, never historical split dates or transfers of attributes.
Run after regional/border reconciliation and before the publication audits.
"""
import collections, copy, hashlib, json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
REPORT = DATA / 'macro-corrections.json'

def read(path):
    return json.loads(path.read_text())

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')

def footprint_hash():
    return subprocess.check_output(['node', 'scripts/stamp-prepared.mjs', '--hash'], cwd=ROOT, text=True).strip()

parts = {part: read(DATA / part) for part in read(DATA / 'world-index.json')['parts']}
features = [f for part in parts.values() for f in part['features']]
locations = {f['id']: f for f in features}
units = {u['id']: u for u in read(DATA / 'hierarchy.json')}
before_units = copy.deepcopy(units)
before_names = {f['id']: f['properties']['name'] for f in features}
original_hash = footprint_hash()

def chain(feature):
    result = {}
    parent = feature['properties']['parent_id']
    while parent:
        unit = units[parent]
        result[unit['level']] = {'id': parent, 'name': unit['name']}
        parent = unit['parent_id']
    return result

before_chains = {f['id']: chain(f) for f in features}
if REPORT.exists():
    previous = read(REPORT)
    matching_locations = all(row['location_id'] in locations and before_chains[row['location_id']] == row['after_chain'] and before_names[row['location_id']] == row['after_name'] for row in previous.get('changes', []))
    matching_groups = all((row['id'] not in units) if row['after'] is None else (row['id'] in units and all(units[row['id']][key] == row['after'][key] for key in ['name', 'level', 'parent_id'])) for row in previous.get('group_changes', []))
    if previous.get('changes') and matching_locations and matching_groups and original_hash == previous.get('footprints_sha256_after'):
        print(json.dumps({'already_applied': True, 'locations': len(features), 'footprints_unchanged': True, 'counts_after': previous['counts_after']}))
        raise SystemExit
cases = []
case_for_location = collections.defaultdict(set)

SOURCE = {
    'pacific': ['https://unstats.un.org/unsd/methodology/m49/overview/', 'https://en.wikipedia.org/wiki/Melanesia'],
    'phoenix': ['https://en.wikipedia.org/wiki/Phoenix_Islands', 'https://en.wikipedia.org/wiki/Howland_Island', 'https://en.wikipedia.org/wiki/Baker_Island'],
    'cook': ['https://en.wikipedia.org/wiki/Cook_Islands', 'https://en.wikipedia.org/wiki/Tokelau'],
    'macquarie': ['https://en.wikipedia.org/wiki/Macquarie_Island'],
    'channel': ['https://en.wikipedia.org/wiki/Channel_Islands', 'https://en.wikipedia.org/wiki/Bailiwick_of_Guernsey'],
    'man': ['https://en.wikipedia.org/wiki/Isle_of_Man'],
    'bahamas': ['https://www.bahamas.com/islands/bimini', 'https://www.bahamas.com/islands/ragged-island', 'https://unstats.un.org/unsd/methodology/m49/overview/'],
    'spm': ['https://en.wikipedia.org/wiki/Saint_Pierre_and_Miquelon'],
    'sindo': ['https://en.wikipedia.org/wiki/Sindo_County'],
    'fujian': ['https://en.wikipedia.org/wiki/Kinmen', 'https://en.wikipedia.org/wiki/Matsu_Islands', 'https://en.wikipedia.org/wiki/Wuqiu,_Kinmen'],
    'korea': ['https://en.wikipedia.org/wiki/Korean_Peninsula'],
    'taiwan': ['https://en.wikipedia.org/wiki/Geography_of_Taiwan'],
    'scs': ['https://en.wikipedia.org/wiki/South_China_Sea_Islands', 'https://en.wikipedia.org/wiki/Paracel_Islands'],
    'border': ['https://www.geoboundaries.org/', 'https://en.wikipedia.org/wiki/T%C3%A1chira', 'https://en.wikipedia.org/wiki/Norte_de_Santander_Department'],
}

def find(level, name, parent=None):
    hits = [u for u in units.values() if u['level'] == level and u['name'] == name and (parent is None or u['parent_id'] == parent)]
    if len(hits) != 1:
        raise ValueError(f'Expected one {level}: {name}; found {len(hits)}')
    return hits[0]['id']

def maybe_find(level, name, parent=None):
    hits = [u for u in units.values() if u['level'] == level and u['name'] == name and (parent is None or u['parent_id'] == parent)]
    if len(hits) > 1:
        raise ValueError(f'Ambiguous {level}: {name}')
    return hits[0]['id'] if hits else None

def group(level, name, parent, source_key, basis, predecessor=None):
    existing = maybe_find(level, name, parent)
    if existing:
        return existing
    key = hashlib.sha256(f'{level}/{parent}/{name}/{predecessor or ""}'.encode()).hexdigest()[:16]
    identity = f'atlas:macro-review:{level}:{key}'
    metadata = {'source': 'Atlas geographic reference / inspected macro-review sources', 'source_url': SOURCE[source_key][0], 'source_urls': SOURCE[source_key], 'basis': basis, 'kind': 'geographic', 'framework_status': 'atlas-defined', 'macro_correction_version': 1, 'semantic_approved': False, 'review_reasons': ['Source-backed macro membership; every lower-tier role and boundary still needs semantic review']}
    if predecessor:
        metadata['previous_group_id'] = predecessor
    units[identity] = {'id': identity, 'name': name, 'level': level, 'parent_id': parent, 'metadata': metadata}
    return identity

def case(identity, reason, source_key, status='reference-membership-corrected'):
    entry = {'id': identity, 'reason': reason, 'source_urls': SOURCE[source_key], 'status': status, 'semantic_complete': False}
    cases.append(entry)
    return entry

def mark(feature, entry):
    case_for_location[feature['id']].add(entry['id'])
    feature['properties']['metadata']['macro_membership_evidence'] = {'case_id': entry['id'], 'method': 'source-supported geographic reference reconciliation', 'source_urls': entry['source_urls'], 'basis': entry['reason'], 'historical_event': False, 'semantic_review': 'open'}

def descendants(identity):
    return [f for f in features if identity in {x['id'] for x in chain(f).values()}]

def reparent_group(identity, parent, entry):
    if units[identity]['parent_id'] == parent:
        return
    affected = descendants(identity)
    units[identity]['metadata'].update(previous_parent_id=units[identity]['parent_id'], source_urls=entry['source_urls'], membership_correction=entry['reason'], macro_correction_version=1, semantic_approved=False)
    units[identity]['parent_id'] = parent
    for f in affected:
        mark(f, entry)

def rename_group(identity, name, entry):
    unit = units[identity]
    if unit['name'] == name:
        return
    affected = descendants(identity)
    unit['metadata'].setdefault('original_source_name', unit['name'])
    unit['metadata'].update(reference_name_evidence={'source_urls': entry['source_urls'], 'method': 'geographic footprint/role reference correction', 'historical_rename': False}, macro_correction_version=1, semantic_approved=False)
    unit['name'] = name
    for f in affected:
        mark(f, entry)

def move_location(identity, area, entry):
    feature = locations[identity]
    old_province = units[feature['properties']['parent_id']]
    if old_province['parent_id'] == area:
        return
    candidates = [u for u in units.values() if u['level'] == 'province' and u['parent_id'] == area and u['name'] == old_province['name'] and u['metadata'].get('source') == old_province['metadata'].get('source')]
    if len(candidates) == 1:
        province = candidates[0]['id']
    else:
        key = hashlib.sha256(f'{old_province["id"]}/{area}'.encode()).hexdigest()[:16]
        province = f'atlas:macro-review:province:{key}'
        if province not in units:
            units[province] = copy.deepcopy(old_province)
            units[province].update(id=province, parent_id=area)
            units[province]['metadata'].update(previous_group_id=old_province['id'], membership_correction=entry['reason'], macro_correction_version=1, semantic_approved=False)
    feature['properties']['parent_id'] = province
    mark(feature, entry)

# All members are selected by observed source archipelago or stable geography ID,
# never by a dated owner or a modern sovereignty assignment.
micronesia = find('subcontinent', 'Micronesia')
polynesia = find('subcontinent', 'Polynesia')
south_central = find('region', 'South-Central Pacific')
entry = case('pacific-archipelagos', 'Separate Melanesian, Micronesian and Polynesian archipelago roles; M49 corroborates subregion conventions, while geographic archipelagos override whole-country statistical assignment.', 'pacific')
western_poly = group('region', 'Western Polynesian Islands', polynesia, 'pacific', 'Collective western Polynesian island geography; independent of owners')
equatorial_micro = group('region', 'Equatorial Micronesia', micronesia, 'pacific', 'Gilbert and Nauru equatorial island groups; independent of owners')
for name in ['Tonga', 'Tuvalu', 'Samoa', 'Wallis-Futuna Is.', 'Niue', 'Tokelau-Manihiki']:
    area = maybe_find('area', name)
    if area:
        reparent_group(area, western_poly, entry)
for name in ['Gilbert Is.', 'Nauru']:
    reparent_group(find('area', name), equatorial_micro, entry)
rename_group(find('region', 'Southwestern Pacific'), 'Southern Melanesian Islands', entry)

entry = case('northern-cook-and-tokelau', 'Northern Cook atolls are a distinct source geography from Tokelau/Swains. Group Northern Cook in South-Central Pacific and Tokelau in western Polynesia without transferring ownership.', 'cook')
northern_cook = group('area', 'Northern Cook Islands', south_central, 'cook', 'Named northern Cook island group of coral atolls', predecessor=maybe_find('area', 'Tokelau-Manihiki'))
for identity in ['COK-4962', 'COK-4959', 'COK-4961', 'COK-4960']:
    move_location(identity, northern_cook, entry)
rename_group(find('area', 'Tokelau-Manihiki'), 'Tokelau Archipelago', entry)

entry = case('howland-baker-phoenix', 'Howland and Baker are central equatorial Pacific islands associated geographically with the Phoenix group; no US-owner rule is used.', 'phoenix')
reparent_group(find('area', 'Howland-Baker Is.'), south_central, entry)

# A source-name mismatch is exposed rather than blindly assigning false geometry
# to the real Phoenix archipelago. All coordinates are checked on the footprint.
identity = 'gb:KIR:ADM1:97431129B36644055464690'
if identity in locations:
    feature = locations[identity]
    rings = feature['geometry']['coordinates']
    def vertices(value):
        if value and isinstance(value[0], (int, float)):
            yield value
        else:
            for child in value:
                yield from vertices(child)
    points = list(vertices(rings))
    western = all(165 < point[0] < 180 and -4 < point[1] < 5 for point in points)
    if western:
        entry = case('phoenix-source-footprint-mismatch', 'The retained location footprint lies in the western equatorial Pacific near Gilbert/Banaba geography, not the actual Phoenix archipelago around 172 W. Keep physical parent in Micronesia, expose the mismatched label, and leave missing eastern coverage open.', 'phoenix', 'name-and-coverage-unresolved')
        props = feature['properties']; props['metadata'].setdefault('original_source_name', props['name'])
        props['metadata'].update(name_evidence_status='unknown', semantic_review_reasons=['Source Phoenix Islands label disagrees with retained western footprint; eastern Phoenix coverage requires sourced geometry correction'])
        props['name'] = 'Western equatorial Pacific source remainder'
        province = units[props['parent_id']]
        rename_group(province['id'], 'Western equatorial Pacific source remainder', entry)
        mark(feature, entry)

entry = case('macquarie-southwest-pacific', 'Macquarie lies in the southwest Pacific, about 1000 km southwest of New Zealand South Island; use a collective southwest-Pacific regional association rather than create a one-island pseudo-region or assign by Australian ownership.', 'macquarie')
new_zealand = find('region', 'New Zealand')
rename_group(new_zealand, 'New Zealand and Southwest Pacific Islands', entry)
reparent_group(find('area', 'Macquarie Is.'), new_zealand, entry)

entry = case('irish-sea-isle-of-man', 'Isle of Man lies in the Irish Sea among the British/Irish islands, not Nordic Europe. The modern owner is not consulted.', 'man')
man_area = group('area', 'Isle of Man', find('region', 'Britain'), 'man', 'Named Irish Sea island geographic territory', predecessor=chain(locations['IMN+00?'])['area']['id'])
move_location('IMN+00?', man_area, entry)

entry = case('english-channel-islands', 'Channel Islands are an English Channel archipelago off Normandy, not Iberia; associate geographically with the French/Channel-coast region without asserting French political ownership.', 'channel')
channel_area = group('area', 'Channel Islands', find('region', 'France'), 'channel', 'English Channel/Normandy-coast archipelago', predecessor=chain(locations['JEY+00?'])['area']['id'])
for identity in ['JEY+00?', 'GGY+00?']:
    move_location(identity, channel_area, entry)
feature = locations['GGY+00?']
entry = case('guernsey-whole-footprint-name', 'Current multipart footprint spans the Guernsey/Alderney/Sark archipelago rather than only Sark. Use Bailiwick of Guernsey as a modern reference whole-territory name; retain source Sark label and the same location identity.', 'channel')
feature['properties']['metadata'].setdefault('original_source_name', feature['properties']['name'])
feature['properties']['metadata']['reference_name_evidence'] = {'source_urls': entry['source_urls'], 'method': 'whole-territory scope checked against multipart footprint bounds', 'historical_rename': False}
feature['properties']['name'] = 'Bailiwick of Guernsey'
rename_group(feature['properties']['parent_id'], 'Bailiwick of Guernsey', entry)
mark(feature, entry)

entry = case('bahamian-bimini-and-ragged', 'Bimini and Ragged Island are named Bahamian archipelago units. Correct inherited Florida/Cuba area matches to Bahamas within the Caribbean convention; no country-owner renderer or dated evidence is changed.', 'bahamas')
bahamas = find('area', 'Bahamas')
move_location('gb:BHS:ADM1:57655419B82083755348588', bahamas, entry)
for feature in features:
    if feature['properties']['name'] == 'Ragged Island' and feature['id'].startswith('gb:BHS:ADM1:'):
        move_location(feature['id'], bahamas, entry)

entry = case('newfoundland-offshore-saint-pierre', 'Saint Pierre/Miquelon is a northwest Atlantic archipelago off Newfoundland. Associate with Northeastern North America, using its own named area, instead of a residual Eastern Canada region containing no Canadian territory.', 'spm')
spm_area = group('area', 'Saint Pierre and Miquelon', find('region', 'Northeastern North America'), 'spm', 'Named Newfoundland-adjacent Atlantic archipelago', predecessor=chain(locations['atlas:territory:SPM'])['area']['id'])
move_location('atlas:territory:SPM', spm_area, entry)

entry = case('korean-and-taiwan-region-roles', 'Korean Peninsula and Taiwan are distinct peninsula/island geographies; replace the misleading residual Eastern Asia region role while retaining stable IDs for geographic renames.', 'korea')
eastern = find('region', 'Eastern Asia', find('subcontinent', 'Eastern Asia'))
rename_group(eastern, 'Korean Peninsula', entry)
taiwan_region = group('region', 'Taiwan and Penghu', find('subcontinent', 'Eastern Asia'), 'taiwan', 'Taiwan main island and associated Penghu island geography, independent of political owner')
reparent_group(find('area', 'Taiwan'), taiwan_region, entry)
entry = case('sindo-yalu-korean-coast', 'Sindo/Pidansom lies in the Yalu estuary on the Korean coast. Restore its sourced North Pyongan administrative parent within Korean geography instead of residual Manchuria/China.', 'sindo')
move_location('gb:PRK:ADM2:82179303B2981535202544', find('area', 'Korea'), entry)

entry = case('fujian-coastal-island-geography', 'Kinmen/Matsu/Wuqiu lie off the Fujian coast in the Taiwan Strait; geographic Fujian-coast membership does not assert mainland ownership of Taiwan-administered territories.', 'fujian')
coast = find('area', 'China Southeast')
rename_group(coast, 'Fujian Coastal Islands', entry)
reparent_group(coast, find('region', 'East China', find('subcontinent', 'Eastern Asia')), entry)

entry = case('south-china-sea-archipelago-role', 'Paracels, Spratlys and Scarborough are South China Sea island groups; give them a sea-archipelago region independent of conflicting sovereignty claims and remove the misleading Southeastern Asian East China role.', 'scs')
scs_region = find('region', 'East China', find('subcontinent', 'Southeastern Asia'))
rename_group(scs_region, 'South China Sea Islands', entry)
for name in ['South China Sea', 'Paracel Islands']:
    reparent_group(find('area', name), scs_region, entry)
for f in features:
    if f['properties']['name'] == 'Scarborough Reef':
        area = group('area', 'Scarborough Shoal', scs_region, 'scs', 'Named South China Sea shoal geographic territory', predecessor=chain(f)['area']['id'])
        move_location(f['id'], area, entry)

# For Colombia/Venezuela source mismatches, correct the stated administrative
# role while preserving the present macro-region. Moving to a country area
# would silently select a macro-region from nationality, which is forbidden.
entry = case('colombia-venezuela-source-portions', 'Sourced Táchira and Norte de Santander units are administrative regional portions, not foreign country areas. Preserve their existing physical macro-region pending exact border-geography review; use transparent named-source-portion areas and keep repeated-tier role review open.', 'border', 'administrative-role-corrected-macro-boundary-open')
for identity, name in [('gb:COL:ADM2:7082276B36155963658062', 'Norte de Santander — northern geographic portion'), ('gb:VEN:ADM2:92452058B18404635880934', 'Táchira — western geographic portion'), ('gb:VEN:ADM2:92452058B93734391596245', 'Táchira — western geographic portion')]:
    old = chain(locations[identity])
    area = group('area', name, old['region']['id'], 'border', 'Named portion of the original source administrative parent; regional boundary and repeated-tier role remain open', predecessor=old['area']['id'])
    move_location(identity, area, entry)

used = set()
for feature in features:
    current = chain(feature)
    if set(current) != {'province', 'area', 'region', 'subcontinent', 'continent'}:
        raise ValueError(f'Incomplete chain: {feature["id"]}')
    used.update(row['id'] for row in current.values())
retired = [copy.deepcopy(unit) for identity, unit in units.items() if identity not in used]
units = {identity: unit for identity, unit in units.items() if identity in used}
child_count = collections.Counter(f['properties']['parent_id'] for f in features)
child_count.update(u['parent_id'] for u in units.values() if u['parent_id'])
for unit in units.values():
    unit['metadata']['child_count'] = child_count[unit['id']]
changes = []
for feature in features:
    identity = feature['id']; after = chain(feature)
    if before_chains[identity] != after or before_names[identity] != feature['properties']['name']:
        changes.append({'location_id': identity, 'before_name': before_names[identity], 'after_name': feature['properties']['name'], 'before_chain': before_chains[identity], 'after_chain': after, 'case_ids': sorted(case_for_location[identity])})
changed_groups = [{'id': identity, 'before': before_units.get(identity), 'after': units.get(identity)} for identity in sorted(set(before_units) | set(units)) if before_units.get(identity) != units.get(identity)]
report = {'version': 1, 'scope': 'Source-supported macro-membership and reference-name corrections only; location IDs and geometry are immutable. Cartographic reference migrations are not historical political or settlement events.', 'semantic_complete': False, 'footprints_sha256_before': original_hash, 'footprints_sha256_after': original_hash, 'locations': len(features), 'counts_before': dict(collections.Counter(u['level'] for u in before_units.values())), 'counts_after': dict(collections.Counter(u['level'] for u in units.values())), 'cases': cases, 'changes': changes, 'group_changes': changed_groups, 'retired_groups': retired, 'remaining_work': ['All lower-tier semantic role and boundary research remains open.', 'Exact continent conventions for Azores, Caucasus, Aegean, Kazakhstan and remote islands remain open.', 'Eastern Phoenix archipelago source coverage and the retained western source-remainder label require sourced geometry correction.', 'Colombia/Venezuela macro-border geography and repeated tier roles remain open.']}
evidence_path = DATA / 'macro-review-evidence.json'
report['sources'] = read(evidence_path).get('sources', []) if evidence_path.exists() else []
report['source_proof_scope'] = 'Fetched source content hashes establish what was inspected; unavailable requests are explicitly not evidence. Membership decisions also use observed footprint location and pinned source administrative IDs.'
if '--dry-run' in sys.argv:
    print(json.dumps({'dry_run': True, 'changed_locations': len(changes), 'changed_groups': len(changed_groups), 'counts_after': report['counts_after'], 'cases': [c['id'] for c in cases]}))
    raise SystemExit
snapshot = ROOT / '.cache/macro-review-before'
snapshot.mkdir(parents=True, exist_ok=True)
(snapshot / 'hierarchy.json').write_text(json.dumps(list(before_units.values()), ensure_ascii=False, separators=(',', ':')))
write(snapshot / 'location-parent-names.json', [{'id': f['id'], 'name': before_names[f['id']], 'chain': before_chains[f['id']]} for f in features])
for part, payload in parts.items():
    write(DATA / part, payload)
write(DATA / 'hierarchy.json', list(units.values()))
final_hash = footprint_hash()
if final_hash != original_hash:
    raise RuntimeError('Footprint or stable location identity changed unexpectedly')
report['footprints_sha256_after'] = final_hash
write(REPORT, report)
print(json.dumps({'changed_locations': len(changes), 'changed_groups': len(changed_groups), 'retired_groups': len(retired), 'counts_after': report['counts_after'], 'footprints_unchanged': True}))
