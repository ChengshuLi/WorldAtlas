"""Authenticate and restore the two complete original physical comparison shards.

This is a byte-for-byte custody inverse, not a new GIS execution. The unchanged
source metadata product is reused from the accepted Ukraine restoration.
"""
import base64
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
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-c', 'user.name=WorldAtlas Agent',
                                  '-c', 'user.email=agent@invalid', '-C', str(ROOT), *args])


def main():
    started = time.monotonic()
    head, vintage = sys.argv[1:]
    if git('rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('Exact committed execution HEAD required')
    controls = {}
    for name in ['restore_physical.py', 'physical-inputs.json']:
        actual = (HERE / name).read_bytes()
        if actual != git('show', head + ':' + OWN + '/' + name):
            raise ValueError('Unfrozen control: ' + name)
        controls[name] = actual
    config = json.loads(controls['physical-inputs.json'])
    rp = config['runtime_inventory']
    runtime_raw = git('show', rp['commit'] + ':' + rp['path'])
    if len(runtime_raw) != rp['bytes'] or sha(runtime_raw) != rp['sha256']:
        raise ValueError('Runtime inventory drift')
    runtime = json.loads(runtime_raw)
    if pathlib.Path(sys.executable).resolve() != pathlib.Path(runtime['python_executable']).resolve():
        raise ValueError('Wrong Python runtime')
    if not os.environ.get('PYTHONDONTWRITEBYTECODE') or not os.environ.get('PYTHONPYCACHEPREFIX'):
        raise ValueError('Require read-only runtime and fresh bytecode destination')
    for pin in runtime['files']:
        raw = pathlib.Path(pin['path']).read_bytes()
        if len(raw) != pin['bytes'] or sha(raw) != pin['sha256']:
            raise ValueError('Runtime changed: ' + pin['path'])
    helper = next(p for p in config['files'] if p['path'] == 'scripts/evidence/immutable.py')
    raw = git('show', config['baseline'] + ':' + helper['path'])
    if len(raw) != helper['bytes'] or sha(raw) != helper['sha256']:
        raise ValueError('Immutable helper drift')
    ns = {'__name__': 'congo_immutable', '__file__': str(ROOT / helper['path'])}
    exec(compile(raw, ns['__file__'], 'exec'), ns)
    base = ns['Baseline'](ROOT, config['baseline'], config['files'])
    for pin in runtime['files']:
        base.admit('runtime:' + pin['path'], pin['bytes'])
    for name, raw in controls.items():
        base.admit('control:' + name, len(raw))
    base.admit('runtime-inventory', len(runtime_raw))
    canon = ns['canonical_json']
    names = ['components-021.jsonl.gz', 'components-059.jsonl.gz',
             'original-components.json', 'physical-records.json',
             'queried-source-metadata.json', 'receipt.json']
    destination = ns['NewVintage'](base, OWN + '/', vintage, names)

    def checked(raw, pin, decoded=False):
        prefix = 'uncompressed_' if decoded else ''
        if len(raw) != pin[prefix + 'bytes'] or sha(raw) != pin[prefix + 'sha256']:
            raise ValueError('Whole product drift: ' + pin['path'])
        return raw

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
        raise ValueError('Wrong original scientific execution')
    if report['component_count'] != transport['complete_components'] or report['component_count'] != 95173 or report['source_record_count'] != transport['complete_sources'] or report['source_record_count'] != 188612:
        raise ValueError('Incomplete original scientific roster')
    products = {p['path']: p for p in report['products']}
    entries = {p['delivered']['path']: p for p in transport['entries']}
    original_features = {}
    restored = {}
    summaries = []
    selected = []
    for binding in config['components']:
        pin = binding['candidate_product']
        features = json.loads(read(pin['path'], pin, True))['features']
        by_id = {f['id']: f for f in features}
        if len(by_id) != len(features):
            raise ValueError('Duplicate original candidate identity')
        candidate = features[binding['feature_index']]
        if candidate['id'] != binding['component_id'] or sha(canon(candidate)) != binding['candidate_feature_sha256'] or sha(canon(candidate['geometry'])) != binding['candidate_geometry_sha256']:
            raise ValueError('Original ordinal or complete candidate mismatch')
        original_features[candidate['id']] = candidate
        name = binding['comparison_product']
        entry = entries[name]
        if entry['kind'] != 'components' or entry['original'] != products[name]:
            raise ValueError('Wrong whole original product descriptor')
        rows = [json.loads(line) for line in read(prefix + name, entry['delivered'], True).splitlines()]
        ids = [r['component_id'] for r in rows]
        if not rows or len(set(ids)) != len(ids):
            raise ValueError('Missing or duplicate physical rows')
        for row in rows:
            if row.pop('complete_current_record_metadata_alias') != 'v1':
                raise ValueError('Wrong inverse marker')
            feature = by_id[row['component_id']]
            fields = {'original_context': feature['properties'],
                      'candidate_feature_sha256': sha(canon(feature)),
                      'candidate_geometry_sha256': sha(canon(feature['geometry']))}
            if set(fields).intersection(row):
                raise ValueError('Unexpected original fields alongside alias')
            row.update(fields)
        raw = b''.join(canon(row) for row in rows)
        checked(raw, entry['original'], True)
        encoded = ns['deterministic_gzip'](raw)
        checked(encoded, entry['original'])
        restored[name] = encoded
        selected.append(next(r for r in rows if r['component_id'] == binding['component_id']))
        summaries.append({'path': name, 'rows': len(rows),
                          'whole_original_bytes': len(encoded), 'whole_original_sha256': sha(encoded),
                          'decoded_bytes': len(raw), 'decoded_sha256': sha(raw),
                          'restored_in_this_execution': True})
    source_pin = products['sources-000.jsonl.gz']
    source_raw = read(config['reused_source_product'], source_pin, True)
    sources = [json.loads(line) for line in source_raw.splitlines()]
    by_id = {r['id']: r for r in sources}
    if len(by_id) != len(sources):
        raise ValueError('Duplicate restored native source identity')
    old_receipt = json.loads(read(config['reused_source_receipt']))
    old_entry = next(r for r in old_receipt['restorations'] if r['path'] == 'sources-000.jsonl.gz')
    if old_entry['rows'] != len(sources) or old_entry['whole_original_sha256'] != source_pin['sha256'] or old_entry['decoded_sha256'] != source_pin['uncompressed_sha256']:
        raise ValueError('Reused complete source restoration differs')
    summaries.append({**old_entry, 'restored_in_this_execution': False,
                      'reused_product_path': config['reused_source_product'],
                      'reused_receipt_path': config['reused_source_receipt']})
    queried = []
    for row in selected:
        queries = row['query_relations']
        if not queries or len({q['source_id'] for q in queries}) != len(queries):
            raise ValueError('Missing or duplicate original queries')
        metadata = []
        for query in queries:
            source = by_id[query['source_id']]
            if source['record_sha256'] != query['source_record_sha256'] or source['decoded_pointset_binary64_sha256'] != query['source_pointset_sha256'] or source['level'] != query['source_level']:
                raise ValueError('Native/query original identity mismatch')
            metadata.append(source)
        queried.append({'component_id': row['component_id'], 'sources': metadata})
    receipt = {'baseline': config['baseline'], 'execution_commit': head,
               'component_ids': [b['component_id'] for b in config['components']],
               'restorations': summaries, 'source_inputs': config['files'],
               'runtime_inventory': rp, 'logical_consumed_input_bytes': sum(base.consumed.values()),
               'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
               'elapsed_seconds': time.monotonic() - started,
               'limits': ['Exact whole-product custody inverse only; no new GIS calculation or source approval.',
                          'The original physical-authority and observation-date limits remain unchanged.',
                          'The complete source metadata product is reused, not recomputed.']}
    if receipt['peak_rss_bytes'] > 512 * 1024 ** 2:
        raise ValueError('Process reservation exceeded')
    restored.update({'original-components.json': canon(list(original_features.values())),
                     'physical-records.json': canon(selected),
                     'queried-source-metadata.json': canon(queried), 'receipt.json': canon(receipt)})
    destination.publish_bytes(restored)
    print(json.dumps({'components': len(selected), 'restored_products': 2,
                      'reused_source_products': 1, 'peak_rss_bytes': receipt['peak_rss_bytes'],
                      'elapsed_seconds': receipt['elapsed_seconds'], 'source_admitted': False}))


if __name__ == '__main__':
    main()
