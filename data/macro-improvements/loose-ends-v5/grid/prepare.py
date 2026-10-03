#!/usr/bin/env python3
"""Reproduce two exact-source additions; never mutate the installed geography."""
import copy, gzip, hashlib, importlib.util, json, pathlib, sys
sys.dont_write_bytecode = True
sys.path.insert(0, 'scripts')
spec = importlib.util.spec_from_file_location('land_creations', 'scripts/validate-land-creations.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
validate = module.validate

BASE = pathlib.Path('data/macro-improvements/loose-ends-v5/grid')
OUT = BASE / 'prepared'
OUT.mkdir(exist_ok=True)
(OUT / 'sources').mkdir(exist_ok=True)
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda p: json.loads(gzip.decompress(pathlib.Path(p).read_bytes()) if str(p).endswith('.gz') else pathlib.Path(p).read_bytes())
save = lambda p, d: pathlib.Path(p).write_bytes(gzip.compress(json.dumps(d, separators=(',', ':')).encode(), mtime=0))
features = []
files = []
for part in read('data/world-index.json')['parts']:
    file = pathlib.Path('data') / part
    files.append({'path': str(file), 'sha256': sha(file.read_bytes())})
    features.extend(read(file)['features'])
groups = read('data/hierarchy.json')
staged = read(BASE / 'held-islands.geojson')['features']
routes = read('data/macro-improvements/macro-coverage-oceania/osm-report.json')['routes']
previous = read('data/macro-improvements/oceania-restoration/retained-identity-scan.json.gz')
proofs, added, scans = [], [], []
for old in staged:
    p, source = old['properties'], old['properties']['source']
    route = next(x for x in routes if x['name'] == p['name'])
    source_bytes = pathlib.Path(source['path']).read_bytes()
    assert sha(source_bytes) == source['archive_sha256']
    assert sha(gzip.decompress(source_bytes)) == source['sha256']
    source_identity = p['source_identity']
    same_name = sorted(f['id'] for f in features if f['properties'].get('name', '').casefold() == p['name'].casefold())
    id_collisions = [f['id'] for f in features if f['id'] == old['id'] or f['properties'].get('metadata', {}).get('source_identity') == source_identity]
    assert not id_collisions
    archived = next(x for x in previous['candidates'] if x['name'] == p['name'])
    assert not archived['spatial_predecessors'] and not archived['exact_name_or_alias_registry_matches']
    filename = 'kingman.geojson' if p['name'] == 'Kingman Reef' else 'gardner.geojson'
    wrapper = {'type': 'Feature', 'id': source_identity, 'geometry': old['geometry'], 'properties': {'name': p['name'], 'original_osm': source, 'source_components': route['current_source_components']}}
    raw = (json.dumps(wrapper, separators=(',', ':')) + '\n').encode()
    (OUT / 'sources' / filename).write_bytes(raw)
    feature = {'type': 'Feature', 'id': old['id'], 'geometry': copy.deepcopy(old['geometry']), 'properties': {'id': old['id'], 'name': p['name'], 'parent_id': p['parent_id'], 'reference_owner': None, 'metadata': {
        'source_id': 'osm-api-2026-10-02', 'source_identity': source_identity,
        'source_name': 'OpenStreetMap named dry-land coastline union', 'source_url': source['url'],
        'license': 'ODbL 1.0', 'attribution': '© OpenStreetMap contributors',
        'source_raw_sha256': source['sha256'], 'source_way_ids': [way for component in route['current_source_components'] for way in component['osm_way_ids']],
        'reference_year': 2026, 'supported_from': 2026, 'supported_to': 2027,
        'source_role': 'One whole named island/reef dry-land territory, all three preserved source rings; not one location per rock/ring.',
        'parent_match': p['parent_choice'], 'semantic_review': {'status': 'open', 'scope': 'regional interior'}, 'historical_claims_transferred': False}}}
    added.append(feature)
    proofs.append({'location_id': old['id'], 'parent_chain': p['parent_chain'], 'source': {
        'path': f'sources/{filename}', 'url': source['url'], 'identity': source_identity,
        'sha256': sha(raw), 'license': 'ODbL 1.0', 'attribution': '© OpenStreetMap contributors',
        'supported_from': 2026, 'supported_to': 2027, 'original_archive': {'path': source['path'], 'raw_sha256': source['sha256'], 'archive_sha256': source['archive_sha256'], 'gzip_wrapped': True}},
        'identity_review': {'status': 'distinct-new-territory', 'evidence_url': source['url'],
        'rationale': 'Whole named source dry-land territory absent from current and retained archived identity/spatial inventories. Three rings form one location. Existing archipelago parents and fixed macro route reused; no historical claim transfer.', 'same_name_existing_ids': same_name}})
    scans.append({'id': old['id'], 'name': p['name'], 'source_identity': source_identity, 'current_identity_collisions': id_collisions, 'current_same_name_ids': same_name, 'archived_preflight': archived})
patch = {'version': 1, 'issue': 540, 'input_geography_version': 4, 'input_hierarchy_sha256': sha(pathlib.Path('data/hierarchy.json').read_bytes()), 'added_features': added, 'added_groups': [], 'new_groups': [], 'added_units': [], 'changed_features': [], 'removed_ids': [], 'creation_proofs': proofs, 'history_transfer': False, 'publication_ready': False, 'private_live_registry_checked': False}
save(OUT / 'candidate-patch.json.gz', patch)
save(OUT / 'creation-proofs.json.gz', proofs)
receipt = validate({'before': features, 'after': features + added, 'units': groups, 'proofs': proofs, 'base': str(OUT)})
save(OUT / 'creation-receipt.json.gz', receipt)
save(OUT / 'identity-scan.json.gz', {'issue': 540, 'current_count': len(features), 'current_part_hashes': files, 'previous_scan_path': 'data/macro-improvements/oceania-restoration/retained-identity-scan.json.gz', 'previous_scan_sha256': sha(pathlib.Path('data/macro-improvements/oceania-restoration/retained-identity-scan.json.gz').read_bytes()), 'candidates': scans, 'private_live_registry_and_claims_checked': False})
print(json.dumps({'patch': str(OUT / 'candidate-patch.json.gz'), 'creations': len(added), 'added_groups': 0, 'exact_source_geometry_validated': receipt['verified'], 'historical_claims_transferred': False}))
