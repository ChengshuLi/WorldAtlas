"""Exclusive frozen whole-cohort entry; restore inputs before any replay."""
import argparse
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import types

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OWNED = 'coordination/engineering/complete-replay-operand-restoration-20261007/'


def blob(commit, name):
    row = subprocess.check_output(['git', '-C', str(REPO), 'ls-tree', '-z', commit, '--', name])
    fields = row.decode().rstrip('\0').split('\t')
    if len(fields) != 2 or fields[1] != name:
        raise ValueError('Missing frozen ordinary code path')
    mode, kind, oid = fields[0].split()
    if mode not in ('100644', '100755') or kind != 'blob':
        raise ValueError('Nonordinary frozen code')
    size = int(subprocess.check_output(['git', '-C', str(REPO), 'cat-file', '-s', oid]))
    if size > 33554432:
        raise ValueError('Frozen code exceeds ordinary bound')
    return subprocess.check_output(['git', '-C', str(REPO), 'cat-file', 'blob', oid])


def bootstrap(name, raw, path):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def frozen(commit):
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit) or \
            subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD']).decode().strip() != commit:
        raise ValueError('Exact current frozen execution commit required')
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise ValueError('Use -I -S -B cold entry; no site/.pth/project/bytecode preloads')
    cache = REPO / '.cache' / '1394-never-materialized-bytecode'
    if sys.pycache_prefix != str(cache) or cache.exists() or cache.is_symlink():
        raise ValueError('Use the fixed absent -X pycache_prefix for this author checkout')
    code_list = json.loads(blob(commit, OWNED + 'code-list.json'))
    # Preserve the original code/config roster byte-for-byte. New acquisition
    # adapters have a separate whole captured roster in the same frozen commit.
    additions = json.loads(blob(commit, OWNED + 'acquisition-code-list.json'))
    if type(additions) is not list or any(type(name) is not str for name in additions) or \
            set(additions) & set(code_list) or 'acquisition-code-list.json' in additions:
        raise ValueError('Conflicting acquisition code closure')
    code_list = code_list + ['acquisition-code-list.json'] + additions
    if len(code_list) != len(set(code_list)) or 'run.py' not in code_list or 'code-list.json' not in code_list:
        raise ValueError('Incomplete/duplicate declared code closure')
    pins = []
    raws = {}
    for name in code_list:
        if not name or '\\' in name or any(p in ('', '.', '..') for p in name.split('/')):
            raise ValueError('Unsafe executed-code path')
        path = HERE / name
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('Symlink in executed-code ancestor')
        raw = blob(commit, OWNED + name)
        with path.open('rb') as stream:
            actual = stream.read(len(raw) + 1)
        if actual != raw:
            raise ValueError('Actual materialized code/config differs: ' + name)
        raws[name] = raw
        pins.append({'commit': commit, 'path': OWNED + name, 'bytes': len(raw),
                     'sha256': hashlib.sha256(raw).hexdigest(), 'hash_kind': 'file-bytes'})
    guard = bootstrap('code_guard', raws['code_guard.py'], HERE / 'code_guard.py')
    guard.all_callables(guard, raws['code_guard.py'])
    guard.all_callables(sys.modules[__name__], raws['run.py'])
    shared = bootstrap('shared_immutable', raws['methods/shared_immutable.py'], HERE / 'methods/shared_immutable.py')
    runtime_pin = json.loads(raws['runtime-pins.json'])
    if hashlib.sha256(raws['methods/shared_immutable.py']).hexdigest() != runtime_pin['shared_immutable_sha256'] or \
            blob(runtime_pin['shared_immutable_original_commit'], runtime_pin['shared_immutable_original_path']) != raws['methods/shared_immutable.py']:
        raise ValueError('Original shared immutable helper differs')
    guard.all_callables(shared, raws['methods/shared_immutable.py'])
    runtime_index = json.loads(raws['runtime-custody-index.json'])
    if hashlib.sha256(raws['runtime-custody-index.json']).hexdigest() != runtime_pin['custody_index_sha256']:
        raise ValueError('Complete frozen runtime custody index differs')
    # Runtime data are declared whole-file inputs, distinct from executable code.
    # They are authenticated by the same actual frozen Baseline before decoding.
    custody = runtime_index['shards'] + [runtime_pin['current_runtime_delta']]
    for row in custody:
        pins.append(dict(commit=commit, path=OWNED + row['path'],
                         hash_kind='file-bytes', **{k: row[k] for k in
                         ('bytes', 'sha256', 'uncompressed_bytes', 'uncompressed_sha256')}))
    if len({p['path'] for p in pins}) != len(pins):
        raise ValueError('Duplicate declared frozen code/runtime input path')
    baseline = shared.Baseline(REPO, commit, pins)
    # The cold custody reader uses standard-library imports only. Scientific
    # package search roots are exposed after every group and raw body validates.
    modules = baseline.load_modules({'runtime': OWNED + 'runtime.py'})
    guard.all_callables(modules['runtime'], raws['runtime.py'])
    runtime = modules['runtime'].prepare(runtime_pin, raws['runtime-custody-index.json'], baseline, OWNED)
    modules.update(baseline.load_modules({name: OWNED + name + '.py' for name in
                                        ('source', 'objects', 'replay', 'products', 'controls')}))
    for name, module in modules.items():
        guard.all_callables(module, raws[name + '.py'])
    runtime['actual_runtime_callables'] = modules['runtime'].callables(runtime_pin, guard)
    runtime['cold_loaded_origins'] = modules['runtime'].loaded(
        runtime_pin, runtime_index, repo=REPO, owned=OWNED, project_pins=pins)
    return pins, baseline, shared, guard, modules, runtime, runtime_pin, runtime_index



def complete_input_union(*rosters):
    """Collapse only identical complete descriptors of the same commit/path."""
    result = {}
    for rows in rosters:
        for row in rows:
            identity = row['commit'], row['path']
            previous = result.get(identity)
            if previous is not None and previous != row:
                raise ValueError('Conflicting duplicate actual input descriptor')
            result[identity] = row
    return list(result.values())


def final_admission(complete_inputs, products):
    # Two fresh complete executions remain mandatory. One delivered payload is
    # permitted only after whole encoded/decoded equality of both preserved trees.
    # Reserve both original reports and all controls/history/manifest separately.
    final_reserve = 9163466 + 3 * 1024 * 1024
    if sum(row['bytes'] for row in complete_inputs) + final_reserve > products.PHASE_LIMIT:
        raise ValueError('Complete final pair and evidence reserve exceeds ordinary admission')
    if len(complete_inputs) + 12 + 64 > products.DESCRIPTOR_LIMIT:
        raise ValueError('Complete final pair and evidence descriptor reserve exceeds admission')
    return final_reserve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--input-only', action='store_true')
    args = parser.parse_args()
    if not args.out.is_absolute() or '..' in args.out.parts or \
            not args.out.resolve().is_relative_to(REPO / '.cache') or args.out.exists() or \
            any(p.is_symlink() or (p.exists() and not p.is_dir()) for p in (args.out, *args.out.parents)) or \
            not args.out.parent.is_dir():
        raise ValueError('Fresh exclusive actual owned cache output required')
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tick = time.monotonic()
    pins, baseline, shared, guard, modules, runtime, runtime_pin, runtime_index = frozen(args.commit)
    callables = []
    def methods_guard(methods, code):
        callables.extend(guard.modules_guard(methods, code))
    controls = modules['controls'].run(guard, modules['objects'], modules['source'])
    loaded = modules['source'].load(REPO, baseline, shared, methods_guard)
    records, native_aliases, native_proof = modules['source'].native_operands(loaded, args.out.parent)
    runtime['preoperator_loaded_origins'] = modules['runtime'].loaded(
        runtime_pin, runtime_index, repo=REPO, owned=OWNED, project_pins=pins)
    scientific_bindings = modules['runtime'].scientific_bindings(loaded['modules'])
    sources = loaded['source']
    complete_inputs = complete_input_union(sources.index['files'], pins, runtime['whole_runtime_aliases'])
    final_reserve = final_admission(complete_inputs, modules['products'])
    preflight = {'execution_commit': args.commit, 'actual_start_utc': started,
                 'command': sys.argv, 'preoperator_controls': controls,
                 'scope_components': len(loaded['diagnoses']), 'families': 494, 'batches': 49,
                 'original_ordered_queries': 10419, 'complete_candidates': 95173,
                 'complete_original_physical_restoration': loaded['state']['physical_restore_receipts'],
                 'native': native_proof, 'actual_project_callables': callables,
                 'runtime': runtime, 'flat_inputs': complete_inputs,
                 'flat_input_bytes': sum(p['bytes'] for p in complete_inputs),
                 'final_pair_encoded_reserve_bytes': final_reserve,
                 'final_pair_descriptor_reserve': 76,
                 'single_payload_delivery_condition': 'two successful preserved full trees; independent whole encoded/decoded equality'}
    products = modules['products'].Products(args.out, complete_inputs, repo=REPO)
    if args.input_only:
        products.write('input-only.json', modules['source'].canonical(dict(preflight, mode='frozen input-only; no replay operators')))
        print(json.dumps({'status': 'PASS', 'mode': 'input-only', 'scope': 1294}), flush=True)
        return
    objects = modules['objects'].Objects(products, loaded, records, native_aliases)
    validity = loaded['modules']['comparison'].ValidityCache()
    shifted, counts = {}, Counter()
    original_queries = actual_queries = 0
    for ordinal, identity in enumerate(sorted(loaded['diagnoses'])):
        objects.begin(identity)
        result = modules['replay'].execute(identity, loaded, records, validity, shifted)
        feature = loaded['state']['candidates'][identity]
        row = loaded['physical'][identity][0]
        diagnosis = loaded['diagnoses'][identity]
        result.update(complete_original_candidate=objects.alias('candidate', identity, [], feature),
                      complete_original_physical_row=objects.alias('physical', identity, [], row),
                      complete_original_diagnosis=objects.alias('diagnosis', identity, [], diagnosis))
        original_queries += result['original_query_count']
        actual_queries += len(result.get('actual_query_replays', []))
        counts[result['status']] += 1
        products.emit('components', objects.retain(result))
        if (ordinal + 1) % 25 == 0:
            print(json.dumps({'complete_replays': ordinal + 1, 'total': 1294, 'statuses': counts}), flush=True)
    if original_queries != 10419 or sum(counts.values()) != 1294:
        raise ValueError('Incomplete full-cohort accounting')
    for identity, alias in sorted(native_aliases.items()):
        products.emit('native-record-aliases', dict(alias, source_id=identity, complete_original_metadata=records[identity][0]))
    outputs = products.finish()
    modules['runtime'].require_scientific_bindings(loaded['modules'], scientific_bindings)
    runtime['postoperator_project_callables'] = guard.modules_guard(loaded['modules'], baseline)
    runtime['postoperator_runtime_callables'] = modules['runtime'].callables(runtime_pin, guard)
    runtime['postoperator_loaded_origins'] = modules['runtime'].loaded(
        runtime_pin, runtime_index, repo=REPO, owned=OWNED, project_pins=pins)
    if sum(row['bytes'] for row in outputs) > 9163466 or len(outputs) > 12:
        raise ValueError('Actual complete science exceeds preadmitted final-pair reserve; retain failure')
    report = {'mode': 'complete original-source nine-map recovery; not geography repair',
              'execution_commit': args.commit, 'actual_start_utc': started,
              'actual_end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'elapsed_seconds': time.monotonic() - tick, 'command': sys.argv,
              'scope_components': 1294, 'families': 494, 'batches': 49,
              'original_ordered_queries': original_queries, 'actual_recorded_query_replays': actual_queries,
              'statuses': dict(sorted(counts.items())), 'outputs': outputs, 'preflight': preflight,
              'limits': ['Physical/date/political/geographic repair approval remains unknown.',
                         'Remaining mismatches and operator/source failures stay unknown.',
                         'Original diagnoses are retained; no new rational-point diagnostic campaign.',
                         'All changed maps have full ordinary bodies; equal originals have inverse whole-object aliases.']}
    products.write('report.json.gz', modules['source'].canonical(report), compress=True)
    print(json.dumps({'status': 'PASS', 'statuses': report['statuses'],
                      'actual_queries': actual_queries, 'flat_encoded_bytes': preflight['flat_input_bytes'] +
                      sum(p['bytes'] for p in products.outputs)}), flush=True)


if __name__ == '__main__':
    main()
