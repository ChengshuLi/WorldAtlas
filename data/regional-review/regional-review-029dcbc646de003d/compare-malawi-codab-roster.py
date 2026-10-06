"""Reproduce a name-only candidate roster crosswalk; this does not compare geometry."""
import hashlib, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE / 'sources/geoBoundaries-MWI-ADM2-2020.geojson'
NEW = HERE / 'sources/MWI-CODAB/mwi_admin2.geojson'
EXPECTED = {
    OLD.name: '5fe9b6313ee3eaf6d2b8a4579b7a7fa75dc1b16b9324a436f5a359da23527ea6',
    NEW.name: 'f278ce0afacba7137c6b633073cb6a2c46eaacff9b8957d1c8581c9c60fe7e5b',
}

def read(path):
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest(), json.loads(raw)

def norm(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold())

old_hash, old_doc = read(OLD)
new_hash, new_doc = read(NEW)
assert old_hash == EXPECTED[OLD.name] and new_hash == EXPECTED[NEW.name], 'source bytes differ from reviewed pins'
old_rows = old_doc['features']
new_rows = new_doc['features']
old_by_name = {norm(f['properties']['shapeName']): f for f in old_rows}
new_by_name = {norm(f['properties']['adm2_name']): f for f in new_rows}
assert len(old_rows) == 28 and len(old_by_name) == 28
assert len(new_rows) == 32 and len(new_by_name) == 32
matches = []
for key, old in sorted(old_by_name.items()):
    new = new_by_name.get(key)
    matches.append({
        'old_name': old['properties']['shapeName'],
        'old_source_id': old['properties']['shapeID'],
        'candidate_codab_name': new['properties']['adm2_name'] if new else None,
        'candidate_codab_pcode': new['properties']['adm2_pcode'] if new else None,
        'candidate_parent_name': new['properties']['adm1_name'] if new else None,
        'candidate_parent_pcode': new['properties']['adm1_pcode'] if new else None,
        'name_key': key,
        'name_key_is_identity_evidence': False,
    })
unmatched_new = [
    {'name': f['properties']['adm2_name'], 'pcode': f['properties']['adm2_pcode'],
     'parent_name': f['properties']['adm1_name'], 'parent_pcode': f['properties']['adm1_pcode']}
    for f in new_rows if norm(f['properties']['adm2_name']) not in old_by_name
]
result = {
    'version': 1,
    'method': 'Unicode casefold; remove every non-ASCII-alphanumeric character; compare names only',
    'generated_from': {'old_path': OLD.relative_to(HERE).as_posix(), 'old_sha256': old_hash,
                       'new_path': NEW.relative_to(HERE).as_posix(), 'new_sha256': new_hash},
    'counts': {'pinned_2020_geoBoundaries_features': len(old_rows),
               'CODAB_v02_ADM2_features': len(new_rows),
               'candidate_name_matches': sum(x['candidate_codab_name'] is not None for x in matches),
               'old_unmatched': sum(x['candidate_codab_name'] is None for x in matches),
               'new_unmatched': len(unmatched_new)},
    'candidate_matches': matches,
    'new_unmatched_features': unmatched_new,
    'interpretation': ('Roster screening only. A name-key match does not establish stable identity, legal/statistical equivalence, '
      'parent correctness, boundary equivalence, topology, accuracy, or completeness. COD-AB identifies four additional '
      'city-named units in the package; whether they should be separate atlas ADM2 subjects is unresolved. The separately '
      'tracked issue #1045 owns authoritative Malawi semantic adjudication and geometry comparison. No source geometry was read by this comparison.'),
}
output = Path(sys.argv[sys.argv.index('--output') + 1]) if '--output' in sys.argv else HERE / 'mwi-codab-roster-comparison.json'
output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n')
print(json.dumps(result['counts'], indent=2))
