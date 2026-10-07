"""Focused source-fit screen for the pinned MRT/SEN source products and two physical components."""
import argparse
import gzip
import hashlib
import json
import pathlib
import sys
import zlib

from shapely.geometry import shape
import shapely

OWNED = pathlib.Path('research/geography/mauritania-senegal-gap-source-fitness-20261007')
COMPONENT_ROOT = pathlib.Path('coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1')
SOURCES = {
    'MRT': ('geoBoundaries-MRT-ADM2_simplified.geojson', 124489,
            '1902199c8a95554f6fc671b72445584e6b511a79223e0cd30399de2da6fb69da', 57,
            '47542326B95460333313215'),
    'SEN': ('geoBoundaries-SEN-ADM2_simplified.geojson', 424564,
            'cb9aa64a7c8d1302527dd97e85acccafefe28b63e2a3f550c2218ed9a22ba335', 45,
            '50182788B94177495754038'),
}
COMPONENTS = {
    'physical-component:0083c01969242c7ff7bd7169be50cb52f58156add0cd4229dccb556a3f0469a6': {
        'payload': '46db0b46812e4c2f1c5af1d583e848f0217baa8f7b883ea91b29d92480490411',
        'decoded_sha256': 'eac8b87294e31722939ff834289c00be512312ab83e81720d4fabd577cd5da36',
        'fragment_binding_sha256': '7972589246b957612e80cc4b4a7b98d48ef6f185ecee8f35d25ae65060ecbd63',
        'canonical_feature_sha256': '17bf44881608474ac568161675c9636a2fcd32e2660c734a96d33303cd5369e2'},
    'physical-component:99cae6efa6335e68990e353f15940b4bda47276e159af4214919b932b232df4f': {
        'payload': 'a93dad7b38d6bad052ad57a230058466a759d7f80795e72755db0fe34dee7187',
        'decoded_sha256': '82d775abb31da05bb6058c547ea47a4e8428338f5287b79072e778c50139a7e9',
        'fragment_binding_sha256': '1c7861ff0d168d30f410218852e781da4c90d1aeae47bd27fdb794292bf1cd62',
        'canonical_feature_sha256': '2ab595fb43c7f694719467b45b472d2128709b7d753aacb948410c37cf66f8ae'},
}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode()

def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON object key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError(f'Nonfinite JSON token: {value}')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)

def require(ok, message):
    if not ok:
        raise ValueError(message)

def prepare_output(repo, output):
    repo = repo.resolve()
    rel = pathlib.Path(output)
    reproduction = (repo / OWNED / 'reproduction').absolute()
    require(not rel.is_absolute() and '\\' not in str(output) and
            all(part not in ('', '.', '..') for part in rel.parts),
            'Output must be a safe repository-relative path')
    expected_prefix = tuple((OWNED / 'reproduction').parts)
    require(rel.parts[:len(expected_prefix)] == expected_prefix and
            len(rel.parts) in (len(expected_prefix) + 1, len(expected_prefix) + 2),
            'Output must stay directly inside the owned reproduction directory')
    require(reproduction.resolve() == reproduction, 'Owned reproduction directory must not resolve through a symlink')
    target = repo / rel
    parent = target.parent
    resolved_parent = parent.resolve()
    try:
        resolved_parent.relative_to(reproduction)
    except ValueError:
        raise ValueError('Output parent escapes the owned reproduction directory')
    require(not parent.is_symlink(), 'Output parent must not be a symlink')
    if not parent.exists():
        require(parent.parent.resolve() == reproduction, 'Only a fresh run subdirectory may be created')
        parent.mkdir()
        created_parent = True
    else:
        require(parent.is_dir(), 'Output parent must be an ordinary directory')
        created_parent = False
    require(not target.exists() and not target.is_symlink(), 'Output destination already exists')
    return target, created_parent

def load_inputs(repo, roster=None):
    roster = list(COMPONENTS) if roster is None else roster
    require(roster == list(COMPONENTS), 'Candidate roster differs from complete two-member family')
    source_rows = {}
    for country, (filename, expected_bytes, expected_hash, expected_count, contact) in SOURCES.items():
        path = repo / OWNED / 'sources/geoboundaries/original-consumed-simplified' / filename
        raw = path.read_bytes()
        require(len(raw) == expected_bytes and sha(raw) == expected_hash,
                f'{country} consumed source bytes differ from original pin')
        document = strict_json(raw)
        require(document.get('type') == 'FeatureCollection' and len(document.get('features', [])) == expected_count,
                f'{country} FeatureCollection/count mismatch')
        features = {}
        for feature in document['features']:
            props = feature.get('properties') or {}
            identity = props.get('shapeID')
            require(isinstance(identity, str) and identity and identity not in features,
                    f'{country} missing/duplicate shapeID')
            require(feature.get('type') == 'Feature' and feature.get('geometry', {}).get('type') in ('Polygon', 'MultiPolygon'),
                    f'{country} unsupported source feature')
            geom = shape(feature['geometry'])
            require(not geom.is_empty and geom.is_valid, f'{country} source geometry invalid: {identity}')
            features[identity] = (feature, geom)
        require(contact in features, f'{country} exact routing contact absent')
        source_rows[country] = (raw, document, features)
    selected = {}
    expected_hashes = {v['payload'] for v in COMPONENTS.values()}
    for digest in expected_hashes:
        payload = repo / COMPONENT_ROOT / 'payloads' / f'{digest}.bin'
        encoded = payload.read_bytes()
        require(sha(encoded) == digest, 'Physical component encoded source pin mismatch')
        decoded = gzip.decompress(encoded)
        row = next(v for v in COMPONENTS.values() if v['payload'] == digest)
        require(sha(decoded) == row['decoded_sha256'], 'Physical component decoded shard pin mismatch')
        document = strict_json(decoded)
        matches = [f for f in document['features'] if f.get('id') in COMPONENTS]
        for feature in matches:
            if feature['id'] in COMPONENTS:
                require(feature['id'] not in selected, 'Duplicate candidate physical ID in inputs')
                require(sha(canonical(feature)) == COMPONENTS[feature['id']]['canonical_feature_sha256'],
                        'Canonical candidate feature binding mismatch')
                require(feature['properties']['fragment_bindings'][0]['feature_sha256'] ==
                        COMPONENTS[feature['id']]['fragment_binding_sha256'],
                        'Original fragment-binding mismatch')
                geometry = shape(feature['geometry'])
                require(not geometry.is_empty and geometry.is_valid, 'Candidate component invalid')
                selected[feature['id']] = (feature, geometry)
    require(set(selected) == set(COMPONENTS), 'Candidate family incomplete')
    return source_rows, selected

def screen(repo, roster=None):
    require(sys.version_info[:3] == (3, 12, 14), 'Pinned Python 3.12.14 required')
    require(zlib.ZLIB_RUNTIME_VERSION == '1.2.12', 'Pinned zlib 1.2.12 required')
    require(shapely.__version__ == '2.1.2' and shapely.geos_version_string == '3.13.1',
            'Pinned Shapely 2.1.2 / GEOS 3.13.1 required')
    source_rows, components = load_inputs(repo, roster)
    results = []
    for component_id in COMPONENTS:
        feature, geometry = components[component_id]
        relations = []
        bbox_candidates = []
        for country, (_, _, source_features) in source_rows.items():
            for shape_id, (source, source_geometry) in source_features.items():
                cb = geometry.bounds
                sb = source_geometry.bounds
                bbox_overlap = cb[0] <= sb[2] and sb[0] <= cb[2] and cb[1] <= sb[3] and sb[1] <= cb[3]
                if bbox_overlap:
                    intersects = geometry.intersects(source_geometry)
                    intersection = geometry.intersection(source_geometry) if intersects else None
                    candidate = {
                        'country': country,
                        'source_shape_id': shape_id,
                        'source_name': source['properties'].get('shapeName'),
                        'source_feature_canonical_sha256': sha(canonical(source)),
                        'bbox_intersects': True,
                        'topological_intersects': intersects,
                        'source_covers_component': source_geometry.covers(geometry),
                        'component_within_source': geometry.within(source_geometry),
                        'intersection_area_coordinate_units_squared': intersection.area if intersects else None,
                        'intersection_fraction_of_component_coordinate_area': intersection.area / geometry.area if intersects and geometry.area else None,
                    }
                    bbox_candidates.append(candidate)
                    if intersects:
                        relations.append(candidate)
        results.append({
            'physical_component_id': component_id,
            'source_component_feature_sha256': COMPONENTS[component_id]['canonical_feature_sha256'],
            'original_fragment_binding_sha256': COMPONENTS[component_id]['fragment_binding_sha256'],
            'water_status_input': feature['properties'].get('water_status'),
            'measured_fragment_area_sum_m2_input': feature['properties'].get('measured_fragment_area_sum_m2'),
            'component_geometry_coordinate_area': geometry.area,
            'component_bounds': list(geometry.bounds),
            'bbox_candidates': sorted(bbox_candidates, key=lambda r:(r['country'], r['source_shape_id'])),
            'relations': sorted(relations, key=lambda r:(r['country'], r['source_shape_id'])),
        })
    return {
        'version': 1,
        'producer': {'path': str(pathlib.Path(__file__).resolve().relative_to(repo.resolve())),
                     'bytes': pathlib.Path(__file__).stat().st_size,
                     'sha256': sha(pathlib.Path(__file__).read_bytes())},
        'purpose': 'Full-product exact-source fit screen for the complete two-member family; not physical truth or repair approval.',
        'candidate_family_id': 'gap-source-batch:4c735331be01be152eda6db6',
        'operational_batch_id': 'gap-operational-batch:ade3f99f475181e3f9ac2694',
        'family_member_ids': list(COMPONENTS),
        'source_products': [
            {'country': country, 'variant': 'original-consumed simplified ADM2', 'bytes': len(raw), 'sha256': sha(raw),
             'features': len(doc['features']), 'recorded_source_represented_year_claim': '2020' if country == 'MRT' else '2019'}
            for country, (raw, doc, _) in source_rows.items()],
        'runtime': {'python': sys.version.split()[0], 'shapely': shapely.__version__,
                    'geos': shapely.geos_version_string},
        'method': ['Check whole source byte sizes and SHA-256 pins before parsing.',
                   'Validate complete source feature rosters, unique shapeIDs, supported polygonal geometry, nonempty and valid geometry.',
                   'Check both complete candidate IDs and immutable component feature bindings.',
                   'Compare candidate components with every feature in both complete source products using unmodified WGS84 coordinates.',
                   'Record topological covers/within and coordinate-space intersection measures only.',
                   'No reprojection, normalization, repair, buffering, simplification, geometry editing, water classification or administrative approval.'],
        'limits': ['Coordinate-space intersection areas are diagnostic only, in degree-squared units; the near-degenerate component rings make fractions numerically fragile.',
                   'Recorded represented-year claims are not demonstrated effective physical dates.',
                   'Administrative polygons cannot establish whether a microscopic component was land or water.',
                   'No source-authority approval or physical correction is inferred.'],
        'component_screens': results,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    target, created_parent = prepare_output(repo, args.output)
    try:
        report = screen(repo)
    except BaseException:
        if created_parent:
            target.parent.rmdir()
        raise
    with target.open('xb') as stream:
        stream.write(canonical(report) + b'\n')
    print(json.dumps({'output': str(target.relative_to(repo)), 'family_members': len(report['family_member_ids']),
                      'component_screens': len(report['component_screens'])}))

if __name__ == '__main__':
    main()
