"""Restore complete IDN comparison products without replaying source geometry.

Two independent bounded custody phases preserve one two-case execution scope.
An already accepted complete source-metadata inverse is reused unchanged.
"""
import gzip
import hashlib
import io
import json
import os
import pathlib
import resource
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OWN = HERE.relative_to(ROOT).as_posix()
CAP = 256 * 1024 ** 2
METADATA_RESERVE = 1024 ** 2


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-c', 'user.name=WorldAtlas Agent',
                                  '-c', 'user.email=agent@invalid', '-C', str(ROOT), *args])


def unique(rows, key):
    result = {}
    for row in rows:
        identity = row[key]
        if identity in result:
            raise ValueError('Duplicate raw identity: ' + str(identity))
        result[identity] = row
    if not result:
        raise ValueError('Empty evidence roster')
    return result


def checked(raw, pin, decoded=False):
    prefix = 'uncompressed_' if decoded else ''
    if len(raw) != pin[prefix + 'bytes'] or sha(raw) != pin[prefix + 'sha256']:
        raise ValueError('Whole product differs: ' + pin['path'])
    return raw


def main():
    started = time.monotonic()
    head, group_id, vintage = sys.argv[1:]
    if git('rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('Require exact committed execution HEAD')
    controls = {}
    for name in ['restore_physical.py', 'physical-inputs.json']:
        target = HERE / name
        if target.is_symlink():
            raise ValueError('Symlink execution input')
        controls[name] = target.read_bytes()
        if controls[name] != git('show', head + ':' + OWN + '/' + name):
            raise ValueError('Unfrozen execution input: ' + name)
    config = json.loads(controls['physical-inputs.json'])
    groups = unique(config['groups'], 'id')
    group = groups[group_id]
    all_ids = [identity for g in groups.values() for identity in g['component_ids']]
    bindings = unique(config['components'], 'component_id')
    if len(all_ids) != len(set(all_ids)) or set(all_ids) != set(bindings) or len(bindings) != 2:
        raise ValueError('Incomplete or overlapping original two-case accounting')
    if config['original_batch_size'] != 318:
        raise ValueError('Original denominator changed')

    runtime_pin = config['runtime_inventory']
    runtime_raw = checked(git('show', head + ':' + runtime_pin['path']), runtime_pin)
    runtime = json.loads(runtime_raw)
    if pathlib.Path(sys.executable).resolve() != pathlib.Path(runtime['python_executable']).resolve():
        raise ValueError('Python runtime changed')
    if not os.environ.get('PYTHONDONTWRITEBYTECODE') or not os.environ.get('PYTHONPYCACHEPREFIX'):
        raise ValueError('Require read-only runtime bytecode policy')
    runtime_files = unique(runtime['files'], 'path')
    helper = next(p for p in group['files'] if p['path'] == 'scripts/evidence/immutable.py')
    raw = checked(git('show', config['baseline'] + ':' + helper['path']), helper)
    ns = {'__name__': 'phl_immutable', '__file__': str(ROOT / helper['path'])}
    exec(compile(raw, ns['__file__'], 'exec'), ns)
    base = ns['Baseline'](ROOT, config['baseline'], group['files'])
    canon = ns['canonical_json']
    names = group['products'] + ['original-components.json', 'physical-records.json',
                                 'queried-source-metadata.json', 'receipt.json']
    destination = ns['NewVintage'](base, OWN.rsplit('/', 1)[0] + '/', vintage, names)

    def read(name, pin=None, decode=False):
        raw = base.pinned_bytes(name)
        if pin is not None:
            checked(raw, pin)
        if decode:
            base.admit('decoded:' + name, pin['uncompressed_bytes'])
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw = stream.read(pin['uncompressed_bytes'] + 1)
            checked(raw, pin, True)
        return raw

    prefix = config['comparison_prefix']
    report = json.loads(read(prefix + 'report.json'))
    transport = json.loads(read(prefix + 'transport-map.json'))
    if report['execution_commit'] != transport['scientific_execution'] or report['execution_commit'] != '104091cfecd9c83a53f3e6e62f95b0a0c8074351':
        raise ValueError('Wrong scientific execution')
    if report['component_count'] != transport['complete_components'] or report['component_count'] != 95173 or report['source_record_count'] != transport['complete_sources'] or report['source_record_count'] != 188612:
        raise ValueError('Original scientific denominator differs')
    products = unique(report['products'], 'path')
    entries = unique([dict(e, path=e['delivered']['path']) for e in transport['entries']], 'path')
    source_pin = products['sources-000.jsonl.gz']
    delta_pin = config['delta_descriptor']
    decoded_pins = group['candidate_products'] + [delta_pin, source_pin]
    decoded_bytes = sum(p['uncompressed_bytes'] for p in decoded_pins)
    decoded_bytes += sum(entries[n]['delivered']['uncompressed_bytes'] for n in group['products'])
    original_output_bytes = sum(products[n]['bytes'] + products[n]['uncompressed_bytes'] for n in group['products'])
    preflight = (sum(p['bytes'] for p in group['files']) + decoded_bytes
                 + sum(p['bytes'] for p in runtime_files.values()) + len(runtime_raw)
                 + sum(map(len, controls.values())) + original_output_bytes
                 + METADATA_RESERVE + 4096)
    if preflight > CAP:
        raise ValueError('Complete custody phase exceeds budget before inverse: ' + str(preflight))
    for pin in runtime_files.values():
        checked(pathlib.Path(pin['path']).read_bytes(), pin)
        base.admit('runtime:' + pin['path'], pin['bytes'])
    base.admit('runtime-inventory', len(runtime_raw))
    for name, raw in controls.items():
        base.admit('control:' + name, len(raw))

    wanted = set()
    for name in group['products']:
        entry = entries[name]
        if entry['kind'] != 'components' or entry['original'] != products[name]:
            raise ValueError('Original/transport complete product descriptor differs')
        rows = unique([json.loads(l) for l in read(prefix + name, entry['delivered'], True).splitlines()], 'component_id')
        if wanted.intersection(rows):
            raise ValueError('Duplicate components across complete products')
        wanted.update(rows)
    del rows
    original_features = {}
    for pin in group['candidate_products']:
        rows = unique(json.loads(read(pin['path'], pin, True))['features'], 'id')
        for identity in wanted.intersection(rows):
            if identity in original_features:
                raise ValueError('Duplicate complete original feature')
            original_features[identity] = rows[identity]
    del rows
    delta = json.loads(read(delta_pin['path'], delta_pin, True))
    if delta['current_count'] != 95173 or len(delta['removed_ids']) != len(set(delta['removed_ids'])):
        raise ValueError('Original successor delta differs')
    for identity in delta['removed_ids']:
        original_features.pop(identity, None)
    upserts = unique(delta['upsert_records'], 'id')
    for identity in wanted.intersection(upserts):
        original_features[identity] = upserts[identity]
    if set(original_features) != wanted:
        raise ValueError('Incomplete original whole-product component custody')
    for identity in group['component_ids']:
        feature = original_features[identity]
        if sha(canon(feature)) != bindings[identity]['feature_sha256'] or sha(canon(feature['geometry'])) != bindings[identity]['geometry_sha256']:
            raise ValueError('Selected original feature/hash mismatch')

    restored, summaries, selected = {}, [], []
    for name in group['products']:
        entry = entries[name]
        rows = [json.loads(l) for l in read(prefix + name, entry['delivered'], True).splitlines()]
        unique(rows, 'component_id')
        for row in rows:
            if row.pop('complete_current_record_metadata_alias') != 'v1' or 'complete_original_native_byte_hash_alias' in row:
                raise ValueError('Wrong component inverse marker')
            feature = original_features[row['component_id']]
            fields = {'original_context': feature['properties'], 'candidate_feature_sha256': sha(canon(feature)),
                      'candidate_geometry_sha256': sha(canon(feature['geometry']))}
            if set(fields).intersection(row):
                raise ValueError('Conflicting aliased original fields')
            row.update(fields)
        raw = checked(b''.join(canon(row) for row in rows), entry['original'], True)
        encoded = checked(ns['deterministic_gzip'](raw), entry['original'])
        restored[name] = encoded
        selected.extend(row for row in rows if row['component_id'] in group['component_ids'])
        summaries.append({'path': name, 'rows': len(rows), 'whole_original_bytes': len(encoded),
                          'whole_original_sha256': sha(encoded), 'decoded_bytes': len(raw),
                          'decoded_sha256': sha(raw)})
    selected_by_id = unique(selected, 'component_id')
    if set(selected_by_id) != set(group['component_ids']):
        raise ValueError('Selected scope incomplete')
    sources = unique([json.loads(l) for l in read(config['source_product'], source_pin, True).splitlines()], 'id')
    old_receipt = json.loads(read(config['source_receipt']))
    old_entry = next(r for r in old_receipt['restorations'] if r['path'] == 'sources-000.jsonl.gz')
    if old_entry['rows'] != len(sources) or old_entry['whole_original_sha256'] != source_pin['sha256'] or old_entry['decoded_sha256'] != source_pin['uncompressed_sha256']:
        raise ValueError('Accepted reused source restoration differs')
    queried = []
    for row in selected:
        queries = row['query_relations']
        unique(queries, 'source_id')
        metadata = []
        for query in queries:
            source = sources[query['source_id']]
            if (source['record_sha256'], source['decoded_pointset_binary64_sha256'], source['level']) != (query['source_record_sha256'], query['source_pointset_sha256'], query['source_level']):
                raise ValueError('Original source/query identity mismatch')
            metadata.append(source)
        queried.append({'component_id': row['component_id'], 'sources': metadata})
    receipt = {'baseline': config['baseline'], 'execution_commit': head, 'group_id': group_id,
               'original_batch_id': config['original_batch_id'], 'original_batch_size': 318,
               'component_ids': group['component_ids'], 'restorations': summaries,
               'reused_source_product': config['source_product'], 'reused_source_receipt': config['source_receipt'],
               'runtime_inventory': runtime_pin, 'source_inputs': group['files'],
               'preflight_upper_bound_bytes': preflight, 'logical_consumed_input_bytes': sum(base.consumed.values()),
               'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
               'elapsed_seconds': time.monotonic() - started,
               'limits': ['Exact whole-product custody restoration only; no GIS or source/physical approval.',
                          'One two-case cohort remains within original318; these groups are byte-budget execution phases.',
                          'Existing observation-date, physical authority and current-neighbor limits remain.']}
    if receipt['peak_rss_bytes'] > 512 * 1024 ** 2:
        raise ValueError('Process reservation exceeded')
    metadata = {'original-components.json': canon([original_features[i] for i in group['component_ids']]),
                'physical-records.json': canon(selected), 'queried-source-metadata.json': canon(queried),
                'receipt.json': canon(receipt)}
    if sum(map(len, metadata.values())) > METADATA_RESERVE:
        raise ValueError('Metadata output exceeds preflight reserve')
    restored.update(metadata)
    destination.publish_bytes(restored)
    print(json.dumps({'group_id': group_id, 'restored_products': len(summaries), 'selected_cases': len(selected),
                      'peak_rss_bytes': receipt['peak_rss_bytes'], 'preflight_upper_bound_bytes': preflight,
                      'source_admitted': False}))


if __name__ == '__main__':
    main()
