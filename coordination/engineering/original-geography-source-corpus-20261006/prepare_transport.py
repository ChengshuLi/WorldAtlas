"""One-time issue1236 retained capture transport. No downloads/source reserialization."""
import argparse
import gzip
import io
import json
import pathlib
import tarfile
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from corpus import BASE, CODEC, INDIA, LIMIT, OWNED, PINS, REGISTRY, descriptor, digest, environment, git, pinned, plain_json, require


def sanitize(value):
    """Keep scientific/provenance pins; omit private machine paths and local credentials."""
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()
                if key not in ('path', 'body_path', 'capture_run')}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value


def main(repo, capture):
    codec = environment(repo)
    registry = plain_json(pinned(repo, BASE, REGISTRY, PINS[REGISTRY]))
    india = plain_json(pinned(repo, BASE, INDIA, PINS[INDIA]))
    inventory_raw = (capture / 'original-administrative-corpus-capture/complete-inventory.json').read_bytes()
    inventory = plain_json(inventory_raw)
    require(inventory['registry_sha256'] == PINS[REGISTRY], 'Capture registry mismatch')
    rows = inventory['rows']
    require({x['registry_key'] for x in rows} == set(registry) and len(rows) == 367, 'Complete captured roster required')
    root = repo / OWNED
    (root / 'payloads').mkdir()
    products = []
    transport_rows = []
    archive = None
    for row in rows + [{'registry_key': 'gb:IND:ADM3', 'source_kind': 'separate-refinement-immutable-gzip',
                        'expected_sha256': india['sha256'], 'sha256': india['sha256'], 'bytes': 40040002,
                        'feature_count': 6822}]:
        key = row['registry_key']
        meta = india if key == 'gb:IND:ADM3' else registry[key]
        read_receipt = sanitize(row)
        if row.get('path'):
            raw = pathlib.Path(row['path']).read_bytes()
            read_receipt['consumed_transport_kind'] = 'retained-captured-original-whole-file'
            # Nordic/IRN/PAK earlier capture receipts preserve actual retrieval observations.
            receipt_paths = {
                'gb:NOR:ADM2': pathlib.Path(row['path']).parent / 'capture-receipt.json',
                'gb:SWE:ADM2': pathlib.Path(row['path']).parent / 'capture-receipt.json',
                'gb:IRN:ADM2': pathlib.Path(row['path']).parent / 'gb-IRN-ADM2-receipt.json',
                'gb:PAK:ADM2': pathlib.Path(row['path']).parent / 'gb-PAK-ADM2-receipt.json'}
            if key in receipt_paths:
                receipt_raw = receipt_paths[key].read_bytes()
                read_receipt['earlier_transport_receipt'] = sanitize(plain_json(receipt_raw))
                read_receipt['earlier_transport_receipt_whole_sha256'] = digest(receipt_raw)
        elif row['source_kind'] == 'immutable-git-containing-file':
            encoded = git(repo, 'cat-file', 'blob', row['git_blob_oid'])
            require(digest(encoded) == row['encoded_sha256'], 'Containing blob mismatch')
            for path in row['paths']:
                require(pinned(repo, BASE, path) == encoded, 'Containing original path mismatch')
            raw = encoded
            for _ in range(row['decode_layers']):
                raw = gzip.decompress(raw)
            read_receipt['consumed_transport_kind'] = 'original-git-blob-and-recorded-lossless-decoding'
        elif key == 'gb:IND:ADM3':
            encoded = pinned(repo, BASE, 'data/global-sources/IND-ADM3.geojson.gz', india['compressed_sha256'])
            raw = gzip.decompress(encoded)
            read_receipt.update(consumed_transport_kind='separate-original-refinement-gzip',
                                original_containing_path='data/global-sources/IND-ADM3.geojson.gz',
                                original_containing_commit=BASE, original_containing_bytes=len(encoded),
                                original_containing_sha256=digest(encoded))
        else:
            require(row['source_kind'] == 'immutable-git-joined-archive-member', 'Unsupported capture transport')
            if archive is None:
                bodies = []
                for part in row['archive_parts']:
                    encoded = pinned(repo, BASE, 'data/' + part['path'], part['sha256'])
                    bodies.append(encoded)
                joined = b''.join(bodies)
                require(digest(joined) == row['archive_sha256'], 'Joined original archive mismatch')
                archive = tarfile.open(fileobj=io.BytesIO(joined), mode='r:gz')
            members = [m for m in archive.getmembers() if m.name == row['member']]
            require(len(members) == 1 and members[0].isfile(), 'Unique ordinary original archive member required')
            raw = archive.extractfile(members[0]).read()
            read_receipt['consumed_transport_kind'] = 'whole-authenticated-original-archive-member'
        require(len(raw) == row['bytes'] and digest(raw) == row['sha256'] == meta['sha256'], 'Whole original mismatch')
        require(len(plain_json(raw)['features']) == row['feature_count'], 'Complete capture count mismatch')
        parts = []
        for ordinal, offset in enumerate(range(0, len(raw), LIMIT)):
            fragment = raw[offset:offset + LIMIT]
            encoded = codec.deterministic_gzip(fragment)
            name = OWNED + '/payloads/' + key.replace(':', '-') + '-%03d.bin.gz' % ordinal
            with (repo / name).open('xb') as stream:
                stream.write(encoded)
            parts.append(dict(descriptor(name, encoded, fragment), ordinal=ordinal, offset=offset))
        products.append({'key': key, 'cohort': 'separate-refinement' if key == 'gb:IND:ADM3' else 'administrative-registry',
                         'original_bytes': len(raw), 'original_sha256': digest(raw), 'feature_count': row['feature_count'],
                         'advertised_feature_count': int(meta['admUnitCount']),
                         'metadata_sha256': digest(json.dumps(meta, sort_keys=True, ensure_ascii=False,
                                                             separators=(',', ':'), allow_nan=False).encode()),
                         'recorded_consumed_url': meta['simplifiedGeometryGeoJSON'],
                         'source_represented_year_claim': meta['boundaryYearRepresented'],
                         'recorded_license': meta['boundaryLicense'],
                         'original_metadata_file': INDIA if key == 'gb:IND:ADM3' else REGISTRY,
                         'partition_method': 'contiguous original raw bytes; no decoding/re-serialization of JSON geometry',
                         'parts': parts})
        read_receipt['actual_consumed_original_bytes'] = len(raw)
        read_receipt['actual_consumed_original_sha256'] = digest(raw)
        transport_rows.append(read_receipt)
        del raw
        if len(products) % 50 == 0:
            print('Exact source transport', len(products), '/368', flush=True)
    catalogue = {'version': 1, 'baseline_commit': BASE, 'baseline_pins': PINS,
                 'codec': 'existing immutable.deterministic_gzip(original raw bytes); empty filename,mtime0,level9',
                 'products': products, 'limits': ['Complete original pointsets are custody inputs, not approved territorial facts.',
                                                'Acquisition timestamps do not establish effective source dates.']}
    provenance = {'version': 1, 'capture_inventory_whole_sha256': digest(inventory_raw),
                  'capture_registry_commit': inventory['registry_commit'],
                  'capture_started_utc': inventory['started_utc'], 'capture_finished_utc': inventory['finished_utc'],
                  'capture_code_sha256': inventory['capture_code_sha256'],
                  'rows': transport_rows,
                  'limits': ['Initial private capture paths intentionally omitted; durable replay consumes complete ordinary payloads.',
                             'Original retrieval observations are retained as recorded, not invented for reused Git/archive products.',
                             'Containing historical archives are provenance for extraction; complete original member bytes are independently retained here.',
                             'Registry/refinement source metadata comes from exact original immutable containing files.',
                             'No original metadata history, territorial validity or water/ownership authority inferred.']}
    for name, value in [('catalogue.json', catalogue), ('transport-provenance.json', provenance)]:
        with (root / name).open('xb') as stream:
            stream.write(codec.canonical_json(value))
    print('Complete370 ordinary payloads', sum(p['bytes'] for x in products for p in x['parts']), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--capture', required=True)
    args = parser.parse_args()
    main(pathlib.Path(args.repo).resolve(), pathlib.Path(args.capture).resolve())
