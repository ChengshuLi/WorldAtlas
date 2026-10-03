#!/usr/bin/env python3
"""Replay a modern, retained-ID Cook dry-land correction without installing it."""
import argparse, copy, gzip, hashlib, importlib.util, json, pathlib, subprocess
from shapely.geometry import shape, mapping, box

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
IDS = {'Manuae': 'COK-4951', 'Aitutaki': 'COK-4956'}
PRIOR = ROOT / 'data/macro-improvements/cook-restoration'
TIERS = ['province', 'area', 'region', 'subcontinent', 'continent']


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def write(path, value):
    raw = encoded(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(raw, mtime=0) if path.suffix == '.gz' else raw)


def prepare(output):
    output = output.resolve()
    if output.exists():
        raise ValueError('Fresh output required; never overwrite an installed stage')
    output.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location('cook_coast', PRIOR / 'prepare.py')
    coast = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coast)
    source_file = PRIOR / 'prepared/source-dry-land.geojson.gz'
    prior_manifest = read(PRIOR / 'prepared/index.json')
    if sha(source_file) != prior_manifest['files']['source-dry-land.geojson.gz']['sha256']:
        raise ValueError('Previously archived Cook source product hash changed')
    sources = {f['id']: f for f in read(source_file)['features'] if f['id'] in IDS}
    source_shapes = {name: shape(f['geometry']) for name, f in sources.items()}
    index = read(ROOT / 'data/world-index.json')
    units = {u['id']: u for u in read(ROOT / 'data/hierarchy.json')}
    before, part_pins, total, overlap_checks = {}, {}, 0, []
    for part in index['parts']:
        path = ROOT / 'data' / part
        part_pins[part] = sha(path)
        for f in read(path)['features']:
            total += 1
            if f['id'] in IDS.values():
                if f['id'] in before:
                    raise ValueError('Duplicate retained identity')
                before[f['id']] = f
            else:
                # Bounding-box filtering avoids retaining world geometry in memory.
                raw = f['geometry']
                rings = [raw['coordinates']] if raw['type'] == 'Polygon' else raw['coordinates']
                points = [p for polygon in rings for ring in polygon for p in ring]
                bounds = (min(p[0] for p in points), min(p[1] for p in points),
                          max(p[0] for p in points), max(p[1] for p in points))
                for name, candidate in source_shapes.items():
                    if box(*bounds).intersects(candidate):
                        area = coast.area(shape(raw).intersection(candidate))
                        overlap_checks.append({'candidate': IDS[name], 'other_id': f['id'], 'area_m2': area})
                        if area > .001:
                            raise ValueError('Positive-area overlap with ' + f['id'])
    if set(before) != set(IDS.values()):
        raise ValueError('Missing retained identities')
    after, operations, wrappers, evidence = [], [], [], []
    for name, identifier in IDS.items():
        original = before[identifier]
        if original['properties']['name'] != name:
            raise ValueError('Wrong modern identity: ' + identifier)
        source = sources[name]['properties']['source']
        # Source URL's explicitly inspected domain, not a guessed geographic expansion.
        bbox = [float(v) for v in source['url'].split('bbox=')[1].split(',')]
        raw_source = ROOT / source['source_xml_path']
        source_input = {'path': str(raw_source.relative_to(coast.EVIDENCE)),
                        'bbox': bbox, 'sha256': source['source_raw_sha256'], 'url': source['url']}
        geometry, check = coast.coast(source_input)
        if check['source_archive_sha256'] != source['source_archive_sha256']:
            raise ValueError('Original source compressed archive changed')
        if not geometry.equals_exact(shape(sources[name]['geometry']), 0):
            raise ValueError('Saved source geometry differs from original-byte replay')
        old = shape(original['geometry'])
        chain, parent = [], original['properties']['parent_id']
        for tier in TIERS:
            unit = units[parent]
            if unit['level'] != tier:
                raise ValueError('Incomplete parent chain')
            chain.append(parent)
            parent = unit['parent_id']
        if parent is not None:
            raise ValueError('Continent has a parent')
        updated = copy.deepcopy(original)
        updated['geometry'] = mapping(geometry)
        point = geometry.representative_point()
        metadata = updated['properties'].setdefault('metadata', {})
        metadata['representative_point'] = [point.x, point.y]
        metadata['footprint_correction_source'] = check
        metadata['footprint_repair'] = {'proposal_id': 'cook-dry-land-v5:' + identifier,
            'method': 'source-backed-replace', 'reference_only': True,
            'history_transfer': False, 'supported_from': 2026, 'supported_to': 2027,
            'rationale': 'Replace generalized partial atoll outline with sourced whole named atoll dry land.'}
        after.append(updated)
        wrapper = {'type': 'FeatureCollection', 'features': [{
            'type': 'Feature', 'id': identifier,
            'properties': {'id': identifier, 'name': name, 'source': check},
            'geometry': mapping(geometry)}]}
        wrapper_path = 'sources/' + name.lower() + '-dry-land.geojson.gz'
        write(output / wrapper_path, wrapper)
        archive_path = 'sources/' + raw_source.name
        (output / archive_path).write_bytes(raw_source.read_bytes())
        wrappers.append({'id': identifier, 'path': wrapper_path, 'sha256': sha(output / wrapper_path),
                         'original_source_path': archive_path, 'original_source_sha256': sha(output / archive_path)})
        evidence.append({'url': check['url'], 'source_sha256': check['source_raw_sha256'],
            'archive_sha256': check['source_archive_sha256'], 'license': check['license'],
            'attribution': check['attribution'], 'supported_from': 2026, 'supported_to': 2027,
            'path': archive_path, 'wrapper_path': wrapper_path})
        operations.append({'id': identifier, 'name': name, 'kind': 'source-backed-replace',
            'before_feature_sha256': digest(original), 'before_geometry_sha256': digest(original['geometry']),
            'after_geometry_sha256': digest(updated['geometry']), 'parent_chain': chain,
            'source_checks': check, 'before_area_m2': coast.area(old), 'after_area_m2': coast.area(geometry),
            'retained_source_land_m2': coast.area(old.intersection(geometry)),
            'added_source_land_m2': coast.area(geometry.difference(old)),
            'removed_generalized_coverage_m2': coast.area(old.difference(geometry)),
            'removed_coverage_interpretation': 'Source-vintage cartographic correction; not historical disappearance.'})
    write(output / 'candidate-patch.json.gz', {'version': 1, 'issue': 540,
        'input_geography_version': 4, 'input_hierarchy_sha256': sha(ROOT / 'data/hierarchy.json'),
        'input_world_index_sha256': sha(ROOT / 'data/world-index.json'), 'input_part_sha256': part_pins,
        'supported_from': 2026, 'supported_to': 2027, 'existing_location_updates': after,
        'existing_group_updates': [], 'added_features': [], 'added_groups': [], 'operations': operations,
        'replacement_deltas': [{'id': f['id'], 'before_feature': before[f['id']], 'after_feature': f} for f in after],
        'source_wrappers': wrappers, 'source_evidence': evidence, 'history_transfer': False})
    # Shared Node implementation establishes identical full-world footprint hashes.
    js = """import fs from 'node:fs';import{gunzipSync}from'node:zlib';
import{footprintHash}from'./scripts/check-prepared.mjs';
const data=JSON.parse(fs.readFileSync('data/world-index.json')).parts.flatMap(p=>JSON.parse(fs.readFileSync('data/'+p)).features);
const patch=JSON.parse(gunzipSync(fs.readFileSync(process.argv[1]))),updates=new Map(patch.existing_location_updates.map(f=>[f.id,f]));
console.log(JSON.stringify({before:footprintHash(data),after:footprintHash(data.map(f=>updates.get(f.id)??f))}));"""
    hashes = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', js,
                         str(output / 'candidate-patch.json.gz')], cwd=ROOT))
    matched = {}
    for path in sorted((ROOT / 'data/hosted-catalog').glob('batch-*.json')):
        batch = read(path)
        tables = {table: [r for r in rows if isinstance(r, dict) and
                   any(r.get(key) in IDS.values() for key in ['id', 'location_id', 'entity_id'])]
                  for table, rows in batch.items() if isinstance(rows, list)}
        tables = {table: rows for table, rows in tables.items() if rows}
        if tables:
            matched[str(path.relative_to(ROOT))] = {'source_sha256': sha(path), 'tables': tables}
    write(output / 'originals-and-records.json.gz', {'locations': list(before.values()),
        'units': [units[p] for p in sorted({p for op in operations for p in op['parent_chain']})],
        'original_catalog_rows': matched, 'historical_records_transferred': False,
        'live_private_records_checked': False, 'live_preflight_required': True,
        'prior_cook_archive_path': str((PRIOR / 'prepared/originals-and-records.json.gz').relative_to(ROOT)),
        'prior_cook_archive_sha256': sha(PRIOR / 'prepared/originals-and-records.json.gz')})
    receipt = {'version': 1, 'geometry_stage_validated': True, 'historical_claims_transferred': False,
        'before_footprints_sha256': hashes['before'], 'after_footprints_sha256': hashes['after'],
        'changed_ids': sorted(IDS.values()), 'added_ids': [], 'removed_ids': [],
        'archives': [{'id': identifier, 'feature': feature} for identifier, feature in before.items()],
        'relationships': [{'kind': 'source-backed-replace', 'proposal_id': 'cook-dry-land-v5:' + identifier,
                           'before_ids': [identifier], 'after_ids': [identifier], 'history_transfer': False}
                          for identifier in sorted(IDS.values())], 'source_evidence': evidence}
    # Full identity dispositions are required by the generic geographic-release gate.
    receipt['reused_ids'] = sorted(f['id'] for part in index['parts']
        for f in read(ROOT / 'data' / part)['features'] if f['id'] not in IDS.values())
    write(output / 'migration-receipt.json.gz', receipt)
    report = {'version': 1, 'verified': True, 'issue': 540, 'input_location_count': total,
        'source_byte_replay': True, 'all_world_overlap_scanned': True,
        'positive_overlap_tolerance_m2': .001, 'candidate_neighbor_intersections': overlap_checks,
        'operations': operations, 'history_transfer': False, 'published': False,
        'limitations': ['Mapped inland water is not exhaustive hydrological coverage.',
            'Modern source support does not establish historical names, coastlines or factual attributes.',
            'Live direct-record scope review is required before installation.']}
    write(output / 'validation.json.gz', report)
    subprocess.run(['node', str(HERE / 'grid-check.mjs'), str(output)], cwd=ROOT, check=True)
    manifest = {'version': 1, 'issue': 540, 'history_transfer': False,
        'before_footprints_sha256': hashes['before'], 'after_footprints_sha256': hashes['after'],
        'producer_sha256': sha(HERE / 'verify.py'), 'grid_producer_sha256': sha(HERE / 'grid-check.mjs'),
        'installed_geography_changed': False, 'published': False,
        'files': {str(p.relative_to(output)): {'sha256': sha(p)} for p in sorted(output.rglob('*')) if p.is_file()}}
    write(output / 'index.json', manifest)
    print(json.dumps({'verified': True, 'output': str(output), 'changed_ids': sorted(IDS.values()),
                      'world_locations_checked': total, 'published': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=pathlib.Path, required=True)
    prepare(parser.parse_args().output)
