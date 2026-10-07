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
    if not sys.flags.isolated:
        raise ValueError('Use the isolated Python entry; no environment/project preloads')
    code_list = json.loads(blob(commit, OWNED + 'code-list.json'))
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
    baseline = shared.Baseline(REPO, commit, pins)
    modules = baseline.load_modules({name: OWNED + name + '.py' for name in
                                    ('source', 'objects', 'replay', 'products', 'runtime')})
    for name, module in modules.items():
        guard.all_callables(module, raws[name + '.py'])
    runtime = modules['runtime'].cold(runtime_pin, guard)
    return pins, baseline, shared, guard, modules, runtime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--input-only', action='store_true')
    args = parser.parse_args()
    if not args.out.is_absolute() or '..' in args.out.parts or \
            not args.out.resolve().is_relative_to(REPO / '.cache') or args.out.exists() or \
            any(p.is_symlink() for p in (args.out, *args.out.parents)):
        raise ValueError('Fresh exclusive actual owned cache output required')
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tick = time.monotonic()
    pins, baseline, shared, guard, modules, runtime = frozen(args.commit)
    callables = []
    def methods_guard(methods, code):
        callables.extend(guard.modules_guard(methods, code))
    loaded = modules['source'].load(REPO, baseline, shared, methods_guard)
    records, native_aliases, native_proof = modules['source'].native_operands(loaded, args.out.parent)
    sources = loaded['source']
    complete_inputs = sources.index['files'] + pins + [dict(row, commit='external-runtime-file-v1')
                                                     for row in runtime['whole_runtime_files']]
    preflight = {'scope_components': len(loaded['diagnoses']), 'families': 494, 'batches': 49,
                 'original_ordered_queries': 10419, 'complete_candidates': 95173,
                 'complete_original_physical_restoration': loaded['state']['physical_restore_receipts'],
                 'native': native_proof, 'actual_project_callables': callables,
                 'runtime': runtime, 'flat_inputs': complete_inputs,
                 'flat_input_bytes': sum(p['bytes'] for p in complete_inputs)}
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
    products.write('report.json', modules['source'].canonical(report))
    print(json.dumps({'status': 'PASS', 'statuses': report['statuses'],
                      'actual_queries': actual_queries, 'flat_encoded_bytes': preflight['flat_input_bytes'] +
                      sum(p['bytes'] for p in products.outputs)}), flush=True)


if __name__ == '__main__':
    main()
