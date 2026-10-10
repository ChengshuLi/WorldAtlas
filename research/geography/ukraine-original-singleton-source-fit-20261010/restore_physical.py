"""Restore two complete original products from authenticated whole custody shards.

No GIS calculation or source approval. Equality is checked against the original
scientific product's complete decoded and encoded hashes, not selected rows.
"""
import gzip
import hashlib
import json
import pathlib
import resource
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CID = 'physical-component:6fd25496ae4a7635eef229d0cfd1eb8dc7d9c10c252d3255fe8d42d186e706d1'
LIMIT = 32 * 1024 ** 2

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode()

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def checked(raw, pin, decoded=False):
    prefix = 'uncompressed_' if decoded else ''
    assert len(raw) <= LIMIT
    assert len(raw) == pin[prefix + 'bytes']
    assert digest(raw) == pin[prefix + 'sha256']
    return raw

def main():
    started = time.monotonic()
    head = git('rev-parse', 'HEAD').decode().strip()
    for name in ['restore_physical.py', 'physical-restoration-inputs.json']:
        target = HERE / name
        assert not target.is_symlink()
        assert target.read_bytes() == git('show', head + ':' + target.relative_to(ROOT).as_posix())
    config = json.loads((HERE / 'physical-restoration-inputs.json').read_bytes())
    destination = HERE / 'vintages' / 'physical-restoration-001'
    for path in [destination, *destination.parents]:
        assert not path.is_symlink()
        if path == ROOT:
            break
    assert not destination.exists()
    bodies = {}
    for pin in config['inputs']:
        bodies[pin['path']] = checked(git('show', config['baseline'] + ':' + pin['path']), pin)
    assert sum(map(len, bodies.values())) < 32 * 1024 ** 2
    comparison = 'coordination/engineering/global-physical-comparison-20261006/results/'
    native = 'coordination/engineering/global-physical-sources-20261006/run-one/'
    custody = 'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/'
    transport = json.loads(bodies[comparison + 'transport-map.json'])
    report = json.loads(bodies[comparison + 'report.json'])
    assert report['component_count'] == transport['complete_components'] == 95173
    assert report['source_record_count'] == transport['complete_sources'] == 188612
    assert report['execution_commit'] == transport['scientific_execution'] == '104091cfecd9c83a53f3e6e62f95b0a0c8074351'
    entries = {row['delivered']['path']: row for row in transport['entries']}
    original_products = {row['path']: row for row in report['products']}
    source_report = json.loads(bodies[native + 'report.json'])
    source_pin = next(row for row in source_report['products'] if row['path'] == 'records-000.jsonl.gz')
    source_raw = checked(bodies[native + 'records-000.jsonl.gz'], source_pin)
    source_decoded = checked(gzip.decompress(source_raw), source_pin, True)
    native_rows = [json.loads(line) for line in source_decoded.splitlines()]
    native_by_id = {row['id']: row for row in native_rows}
    assert len(native_by_id) == len(native_rows)
    index = json.loads(bodies[custody + 'index.json'])
    alias = next(row for row in index['aliases'] if row['original']['path'].endswith('/components-004.json.gz'))
    component_raw = checked(bodies[alias['payload']], alias['original'])
    component_decoded = checked(gzip.decompress(component_raw), alias['original'], True)
    features = json.loads(component_decoded)['features']
    feature_by_id = {row['id']: row for row in features}
    assert len(feature_by_id) == len(features)
    restored = {}
    summaries = []
    for name, kind in [('components-030.jsonl.gz', 'components'), ('sources-000.jsonl.gz', 'sources')]:
        entry = entries[name]
        assert entry['kind'] == kind and entry['original'] == original_products[name]
        delivered = checked(bodies[comparison + name], entry['delivered'])
        decoded = checked(gzip.decompress(delivered), entry['delivered'], True)
        rows = [json.loads(line) for line in decoded.splitlines()]
        assert decoded.endswith(b'\n') and rows
        seen = set()
        for row in rows:
            identity = row['component_id'] if kind == 'components' else row['id']
            assert identity not in seen
            seen.add(identity)
            if kind == 'components':
                assert row.pop('complete_current_record_metadata_alias') == 'v1'
                feature = feature_by_id[identity]
                fields = {'original_context': feature['properties'], 'candidate_feature_sha256': digest(canonical(feature)), 'candidate_geometry_sha256': digest(canonical(feature['geometry']))}
            else:
                assert row.pop('complete_original_native_byte_hash_alias') == 'v1'
                original = native_by_id[identity]
                for actual, expected in [('native_offset', 'offset'), ('native_record_bytes', 'record_bytes'), ('ordinal', 'ordinal'), ('n', 'n')]:
                    assert row[actual] == original[expected]
                assert row['header_native_values'] == original['header_int32']
                fields = {key: original[key] for key in ['record_sha256', 'coordinate_bytes_sha256']}
            assert not set(fields).intersection(row)
            row.update(fields)
        raw = b''.join(map(canonical, rows))
        checked(raw, entry['original'], True)
        # The predecessor uses an mtime-zero gzip stream with no filename.
        import io
        stream = io.BytesIO()
        with gzip.GzipFile(fileobj=stream, mode='wb', mtime=0, compresslevel=9) as output:
            output.write(raw)
        encoded = stream.getvalue()
        checked(encoded, entry['original'])
        restored[name] = encoded
        restored[kind] = rows
        summaries.append({'path': name, 'rows': len(rows), 'whole_original_bytes': len(encoded), 'whole_original_sha256': digest(encoded), 'decoded_bytes': len(raw), 'decoded_sha256': digest(raw)})
    row = next(row for row in restored['components'] if row['component_id'] == CID)
    queries = row['query_relations']
    assert queries and len({q['source_id'] for q in queries}) == len(queries)
    query_rows = []
    for query in queries:
        source = next(r for r in restored['sources'] if r['id'] == query['source_id'])
        assert source['record_sha256'] == query['source_record_sha256']
        assert source['decoded_pointset_binary64_sha256'] == query['source_pointset_sha256']
        assert source['level'] == query['source_level']
        query_rows.append(source)
    receipt = {'baseline': config['baseline'], 'execution_commit': head, 'component_id': CID, 'complete_original_batch_count': 1, 'restorations': summaries, 'source_inputs': config['inputs'], 'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, 'elapsed_seconds': time.monotonic() - started, 'limits': ['Exact original custody restoration only; no new GIS calculation or scientific approval.', 'Original current-physical-authority and observation-date limitations are unchanged.']}
    assert receipt['peak_rss_bytes'] < 512 * 1024 ** 2
    destination.mkdir()
    for name in ['components-030.jsonl.gz', 'sources-000.jsonl.gz']:
        (destination / name).write_bytes(restored[name])
    for name, value in [('original-component.json', feature_by_id[CID]), ('physical-record.json', row), ('queried-source-metadata.json', query_rows), ('receipt.json', receipt)]:
        (destination / name).write_bytes(canonical(value))
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
