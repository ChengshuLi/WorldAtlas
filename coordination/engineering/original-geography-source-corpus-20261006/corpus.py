"""Issue1236 exact original-byte custody; no geographic transformations or network."""
import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import zlib

OWNED = 'coordination/engineering/original-geography-source-corpus-20261006'
BASE = 'c6a26e1caba54e1b81a89fbda3a64fff56da323d'
REGISTRY = 'data/administrative-sources.json'
INDIA = 'data/global-sources/IND-ADM3-metadata.json'
CODEC = 'scripts/evidence/immutable.py'
PINS = {REGISTRY: 'ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633',
        INDIA: 'f7bb99ddfcadaa1091c4b634b48c8843ee9d8b636af4f6da1cefccb0d424fc33',
        CODEC: 'b7ff607b7774595788396e94f08fc29d750e4032624eb93732a5735c1ddcf7fd'}
LIMIT = 33554432
TOTAL = 268435456


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def pinned(repo, commit, path, expected=None):
    require(re.fullmatch('[a-f0-9]{40}', commit), 'Full immutable commit required')
    require(git(repo, 'rev-parse', commit + '^{commit}').decode().strip() == commit, 'Commit mismatch')
    row = git(repo, 'ls-tree', '-z', commit, '--', path).decode().rstrip('\0')
    require(row.startswith(('100644 ', '100755 ')) and row.split('\t')[1] == path, 'Ordinary Git file required')
    raw = git(repo, 'cat-file', 'blob', row.split()[2])
    if expected:
        require(digest(raw) == expected, 'Immutable pin mismatch: ' + path)
    return raw


def environment(repo):
    require(sys.version_info[:3] == (3, 12, 14), 'Pinned Python3.12.14 required')
    require(zlib.ZLIB_RUNTIME_VERSION == '1.2.12', 'Pinned zlib1.2.12 required')
    raw = pinned(repo, BASE, CODEC, PINS[CODEC])
    filename = pathlib.Path(repo) / CODEC
    require(filename.read_bytes() == raw, 'Actual imported codec differs from immutable code')
    spec = importlib.util.spec_from_file_location('original_corpus_immutable', filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(pathlib.Path(module.__file__).read_bytes() == raw, 'Imported codec closure mismatch')
    import shapely
    require(shapely.__version__ == '2.1.2' and shapely.geos_version_string == '3.13.1', 'Pinned Shapely/GEOS required')
    return module


def plain_json(raw):
    def constant(value):
        raise ValueError('Nonfinite JSON token: ' + value)
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON object key')
            result[key] = value
        return result
    return json.loads(raw, parse_constant=constant, object_pairs_hook=pairs)


def descriptor(path, raw, decoded=None):
    result = {'path': path, 'bytes': len(raw), 'sha256': digest(raw), 'hash_kind': 'file-bytes'}
    if decoded is not None:
        result.update(uncompressed_bytes=len(decoded), uncompressed_sha256=digest(decoded))
    return result


def read_payload(repo, part):
    path = part['path']
    require(path.startswith(OWNED + '/payloads/') and '\\' not in path
            and all(x not in ('', '.', '..') for x in path.split('/')), 'Unsafe payload path')
    target = pathlib.Path(repo) / path
    require(target.resolve() == target.absolute() and target.is_file(), 'Ordinary payload file required')
    require(part['bytes'] <= LIMIT and part['uncompressed_bytes'] <= LIMIT, 'Descriptor size bound')
    return decode_payload(target.read_bytes(), part)


def decode_payload(encoded, part):
    require(part['bytes'] <= LIMIT and part['uncompressed_bytes'] <= LIMIT, 'Descriptor size bound')
    require(len(encoded) == part['bytes'], 'Encoded size mismatch')
    require(digest(encoded) == part['sha256'], 'Encoded hash mismatch')
    with gzip.GzipFile(fileobj=__import__('io').BytesIO(encoded)) as stream:
        decoded = stream.read(LIMIT + 1)
        require(len(decoded) <= LIMIT and stream.read(1) == b'', 'Decoded size bound')
    require(len(decoded) == part['uncompressed_bytes'] and digest(decoded) == part['uncompressed_sha256'],
            'Decoded hash/size mismatch')
    return encoded, decoded


def reconstruct(repo, product, codec):
    parts = product['parts']
    require(parts and len(parts) == len({p['path'] for p in parts}), 'Missing/duplicate fragment')
    bodies = []
    offset = 0
    for ordinal, part in enumerate(parts):
        require(part['ordinal'] == ordinal and part['offset'] == offset, 'Fragment order/offset mismatch')
        encoded, raw = read_payload(repo, part)
        require(codec.deterministic_gzip(raw) == encoded, 'Payload not exact deterministic gzip')
        bodies.append(raw)
        offset += len(raw)
    require(offset == product['original_bytes'], 'Whole original size mismatch')
    raw = b''.join(bodies)
    require(digest(raw) == product['original_sha256'], 'Whole original hash mismatch')
    return raw


def validate_catalogue(catalogue, registry, india):
    products = catalogue['products']
    keys = [p['key'] for p in products]
    require(len(keys) == len(set(keys)) and set(keys) == set(registry) | {'gb:IND:ADM3'},
            'Omitted/extra/duplicate source product')
    require(len(registry) == 367 and len(products) == 368, 'Complete cohort sizes required')
    require(catalogue['baseline_commit'] == BASE and catalogue['baseline_pins'] == PINS, 'Catalogue baseline mismatch')
    seen = set()
    encoded_total = 0
    for product in products:
        require(type(product['original_bytes']) is int and product['original_bytes'] > 0, 'Whole size must be an integer')
        require(re.fullmatch('[a-f0-9]{64}', product['original_sha256']), 'Whole hash must be SHA256')
        meta = india if product['key'] == 'gb:IND:ADM3' else registry[product['key']]
        require(product['original_sha256'] == meta['sha256'], 'Wrong product/original hash')
        require(product['recorded_consumed_url'] == meta['simplifiedGeometryGeoJSON'], 'Consumed locator mismatch')
        require(product['cohort'] == ('separate-refinement' if product['key'] == 'gb:IND:ADM3' else 'administrative-registry'),
                'Mixed source cohorts')
        require(product['metadata_sha256'] == digest(json.dumps(meta, sort_keys=True, ensure_ascii=False,
                                                               separators=(',', ':'), allow_nan=False).encode()),
                'Metadata binding mismatch')
        for part in product['parts']:
            require(all(type(part[k]) is int and part[k] >= 0 for k in ('bytes', 'uncompressed_bytes', 'ordinal', 'offset')), 'Integer fragment measurements required')
            require(all(re.fullmatch('[a-f0-9]{64}', part[k]) for k in ('sha256', 'uncompressed_sha256')), 'Fragment SHA256 required')
            require(part['path'] not in seen, 'Duplicate cross-product payload')
            seen.add(part['path'])
            require(0 < part['bytes'] <= LIMIT and 0 < part['uncompressed_bytes'] <= LIMIT, 'Payload size bound')
            encoded_total += part['bytes']
    require(encoded_total <= TOTAL and len(seen) <= 512, 'Complete ordinary payload budget')
    return encoded_total, len(seen)


def validate_features(raw):
    from shapely.geometry import shape
    document = plain_json(raw)
    require(document.get('type') == 'FeatureCollection' and isinstance(document.get('features'), list),
            'Complete FeatureCollection required')
    seen = set()
    failures = []
    for index, feature in enumerate(document['features']):
        require(feature.get('type') == 'Feature', 'Source feature type')
        identity = feature.get('properties', {}).get('shapeID', feature.get('id'))
        require(isinstance(identity, str) and identity and identity not in seen, 'Missing/duplicate source identity')
        seen.add(identity)
        geometry = feature.get('geometry')
        try:
            require(isinstance(geometry, dict) and geometry.get('type') in ('Polygon', 'MultiPolygon'), 'Unsupported geometry')
            operand = shape(geometry)
            if operand.is_empty or not operand.is_valid:
                failures.append({'index': index, 'id': identity, 'empty': operand.is_empty, 'valid': operand.is_valid})
        except Exception as error:
            failures.append({'index': index, 'id': identity, 'error': str(error)})
    return len(document['features']), sorted(seen), failures


def controls(repo, catalogue, registry, india, codec):
    results = []
    def reject(name, function):
        try:
            function()
        except (ValueError, KeyError, OSError, EOFError, gzip.BadGzipFile):
            results.append({'name': name, 'outcome': 'rejected'})
        else:
            raise AssertionError('Negative control accepted: ' + name)
    reject('selected-branch-name', lambda: pinned(repo, 'main', REGISTRY))
    reject('selected-short-sha', lambda: pinned(repo, BASE[:12], REGISTRY))
    reject('duplicate-json-key', lambda: plain_json(b'{"a":1,"a":2}'))
    reject('nonfinite-json-number', lambda: plain_json(b'{"a":NaN}'))
    positive = copy.deepcopy(catalogue)
    validate_catalogue(positive, registry, india)
    p = next(p for p in catalogue['products'] if len(p['parts']) == 2)
    reconstruct(repo, p, codec)
    for name, mutation in [
        ('fragment-reordered', lambda x: x['parts'].reverse()),
        ('fragment-omitted', lambda x: x['parts'].pop()),
        ('fragment-duplicated', lambda x: x['parts'].append(copy.deepcopy(x['parts'][0]))),
        ('fragment-offset', lambda x: x['parts'][1].update(offset=0)),
        ('wrong-whole-hash', lambda x: x.update(original_sha256='0' * 64)),
        ('wrong-whole-size', lambda x: x.update(original_bytes=x['original_bytes'] - 1)),
        ('wrong-encoded-hash', lambda x: x['parts'][0].update(sha256='0' * 64)),
        ('wrong-decoded-hash', lambda x: x['parts'][0].update(uncompressed_sha256='0' * 64)),
        ('wrong-encoded-size', lambda x: x['parts'][0].update(bytes=x['parts'][0]['bytes'] + 1)),
        ('wrong-decoded-size', lambda x: x['parts'][0].update(uncompressed_bytes=x['parts'][0]['uncompressed_bytes'] - 1)),
        ('over-decoded-limit', lambda x: x['parts'][0].update(uncompressed_bytes=LIMIT + 1))]:
        mutated = copy.deepcopy(p)
        mutation(mutated)
        reject(name, lambda: reconstruct(repo, mutated, codec))
    for name, mutation in [
        ('source-omitted', lambda x: x['products'].pop()),
        ('source-extra', lambda x: x['products'].append(dict(x['products'][0], key='gb:XXX:ADM9'))),
        ('source-duplicate', lambda x: x['products'].append(copy.deepcopy(x['products'][0]))),
        ('wrong-source-product', lambda x: x['products'][0].update(original_sha256=x['products'][1]['original_sha256'])),
        ('noninteger-size', lambda x: x['products'][0].update(original_bytes=True)),
        ('oversized-encoded', lambda x: x['products'][0]['parts'][0].update(bytes=LIMIT + 1))]:
        mutated = copy.deepcopy(catalogue)
        mutation(mutated)
        reject(name, lambda: validate_catalogue(mutated, registry, india))
    first = catalogue['products'][0]
    encoded, _ = read_payload(repo, first['parts'][0])
    for name, corrupted in [('encoded-corrupted', encoded[:10] + bytes([encoded[10] ^ 1]) + encoded[11:]),
                            ('encoded-truncated', encoded[:-1]), ('encoded-trailing-bytes', encoded + b'x')]:
        reject(name, lambda: decode_payload(corrupted, first['parts'][0]))
    substituted = copy.deepcopy(p)
    substituted['parts'][0] = copy.deepcopy(first['parts'][0])
    reject('fragment-wrong-product', lambda: reconstruct(repo, substituted, codec))
    original = reconstruct(repo, first, codec)
    for name, mutated in [('raw-corrupted', original[:-1] + b'x'), ('raw-truncated', original[:-1]),
                          ('raw-trailing-bytes', original + b' '),
                          ('raw-reserialized', json.dumps(plain_json(original), sort_keys=True).encode())]:
        reject(name, lambda: require(digest(mutated) == digest(original), 'Substituted original bytes'))
    return {'method_id': 'complete-original-custody', 'kind': 'positive-control', 'outcome': 'passed',
            'positive': ['complete368-key-roster', 'original-two-fragment-reconstruction'],
            'directed_negative_controls': results}


def execute(repo, catalogue_path, selected, output):
    require(re.fullmatch('[a-f0-9]{40}', selected), 'Exact executed code head required')
    codec = environment(repo)
    this_path = OWNED + '/corpus.py'
    code = pinned(repo, selected, this_path)
    require(pathlib.Path(__file__).read_bytes() == code, 'Executed producer differs from committed code')
    catalogue_raw = pinned(repo, selected, catalogue_path)
    require((pathlib.Path(repo) / catalogue_path).read_bytes() == catalogue_raw, 'Catalogue differs from executed input head')
    catalogue = plain_json(catalogue_raw)
    registry = plain_json(pinned(repo, BASE, REGISTRY, PINS[REGISTRY]))
    india = plain_json(pinned(repo, BASE, INDIA, PINS[INDIA]))
    encoded_total, part_count = validate_catalogue(catalogue, registry, india)
    rows = []
    for product in catalogue['products']:
        for part in product['parts']:
            require(pinned(repo, selected, part['path'], part['sha256']) == (pathlib.Path(repo) / part['path']).read_bytes(),
                    'Committed payload binding mismatch')
        raw = reconstruct(repo, product, codec)
        count, ids, failures = validate_features(raw)
        require(count == product['feature_count'], 'Feature count mismatch')
        advertised = product['advertised_feature_count']
        rows.append({'key': product['key'], 'cohort': product['cohort'], 'original_bytes': len(raw),
                     'original_sha256': digest(raw), 'complete_features': count,
                     'complete_sorted_shape_ids_sha256': digest(codec.canonical_json(ids)),
                     'advertised_features': advertised, 'advertised_count_matches': advertised == count,
                     'invalid_empty_or_unsupported': failures,
                     'payload_paths': [p['path'] for p in product['parts']]})
        del raw, ids
    import shapely
    report = {'version': 1, 'baseline_commit': BASE, 'executed_code_commit': selected,
              'actual_producer_sha256': digest(code), 'actual_codec_sha256': PINS[CODEC],
              'catalogue_sha256': digest(catalogue_raw), 'python': sys.version,
              'shapely': shapely.__version__, 'geos': shapely.geos_version_string,
              'zlib': zlib.ZLIB_RUNTIME_VERSION, 'source_products': len(rows),
              'administrative_products': 367, 'refinement_products': 1,
              'payload_descriptors': part_count, 'encoded_payload_bytes': encoded_total,
              'whole_original_bytes': sum(r['original_bytes'] for r in rows),
              'complete_source_features': sum(r['complete_features'] for r in rows),
              'administrative_source_features': sum(r['complete_features'] for r in rows if r['cohort'] == 'administrative-registry'),
              'source_products_with_geometry_failures': [r['key'] for r in rows if r['invalid_empty_or_unsupported']],
              'advertised_feature_count_discrepancies': [r for r in rows if not r['advertised_count_matches']],
              'rows': rows,
              'limits': ['Exact original-byte reconstruction and unmodified source feature validity only.',
                         'No boundary, water, political ownership, effective date or source authority approval.',
                         'Retrieval timestamps are transport observations, not effective geography dates.',
                         'Duplicate shape IDs rejected within each original product; IDs across different layers need not be unique.',
                         'No normalization, MakeValid, buffer, union, source selection or geometry changes.']}
    output = pathlib.Path(output)
    output.mkdir(parents=True, exist_ok=False)
    control_report = controls(repo, catalogue, registry, india, codec)
    negative_report = dict(control_report, kind='negative-control')
    for name, value in [('complete-custody-validity.json', report), ('positive-controls.json', control_report),
                        ('negative-controls.json', negative_report)]:
        with (output / name).open('xb') as stream:
            stream.write(codec.canonical_json(value))
    print(json.dumps({k: report[k] for k in ('source_products', 'whole_original_bytes', 'complete_source_features', 'source_products_with_geometry_failures')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--selected', required=True)
    parser.add_argument('--catalogue', default=OWNED + '/catalogue.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    execute(pathlib.Path(args.repo).resolve(), args.catalogue, args.selected, args.output)
