"""Two fresh focused subprocess executions with truthful invocation receipts."""
import argparse, datetime, hashlib, json, pathlib, subprocess, sys, types

N = 'coordination/engineering/angola-original-envelope-20261007/'
ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[2]


def main():
    p = argparse.ArgumentParser(); p.add_argument('--commit', required=True); p.add_argument('--vintage', required=True); a = p.parse_args()
    files = []
    for name in [N + 'execute.py', 'scripts/evidence/immutable.py']:
        raw = subprocess.check_output(['git', '-C', str(REPO), 'show', a.commit + ':' + name])
        path = REPO / name
        if path.is_symlink() or path.read_bytes() != raw:
            raise ValueError('Actual invocation writer/code drift')
        files.append({'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'hash_kind': 'file-bytes'})
        if name == 'scripts/evidence/immutable.py':
            helper = raw
    immutable = types.ModuleType('immutable'); immutable.__file__ = str(REPO / 'scripts/evidence/immutable.py')
    exec(compile(helper, immutable.__file__, 'exec'), immutable.__dict__)
    base = immutable.Baseline(REPO, a.commit, files)
    names = ['invocations.json', 'equality.json', 'one.stdout.txt', 'one.stderr.txt', 'two.stdout.txt', 'two.stderr.txt']
    output = immutable.NewVintage(base, N, a.vintage + '-invocations', names)
    records = []; payload = {}; product_sets = []; failed = False
    for ordinal, label in enumerate(['one', 'two'], 1):
        run = a.vintage + '-' + label
        command = [sys.executable, '-I', '-B', N + 'run.py', '--commit', a.commit, '--run', run]
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if failed:
            payload[label + '.stdout.txt'] = b''; payload[label + '.stderr.txt'] = b''
            records.append({'ordinal': ordinal, 'executed': False, 'reason': 'Previous attempt failed; no fake successful pair'})
            continue
        execution = subprocess.run(command, cwd=REPO, capture_output=True)
        ended = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if len(execution.stdout) + len(execution.stderr) > 2 * 1024 * 1024:
            raise ValueError('Actual invocation terminal cap')
        payload[label + '.stdout.txt'] = execution.stdout
        payload[label + '.stderr.txt'] = execution.stderr.replace(str(REPO).encode(), b'<owned-checkout>')
        records.append({'ordinal': ordinal, 'executed': True, 'command': ['<runtime-prefix>/bin/python', *command[1:]], 'cwd': '<owned-checkout>', 'started_utc': started, 'ended_utc': ended, 'returncode': execution.returncode, 'executable_role': 'exact fixed shared runtime; authenticated executable and installed closure in runtime-plan.json', 'platform': sys.platform})
        if execution.returncode:
            failed = True; continue
        product = ROOT / 'vintages' / run
        plan = json.loads((ROOT / 'input-plan.json').read_bytes())
        rows = []
        for name in plan['output_names']:
            raw = (product / name).read_bytes(); rows.append({'name': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        if sorted(p.name for p in product.iterdir()) != sorted(plan['output_names'] + ['publication.json']):
            raise ValueError('Actual complete product inventory')
        product_sets.append(rows)
    equal = not failed and len(product_sets) == 2 and product_sets[0] == product_sets[1]
    payload['invocations.json'] = immutable.canonical_json({'execution_commit': a.commit, 'invocations': records, 'receipt_interpretation': 'Actual invocation timestamps/commands retained; receipts excluded from scientific product equality.'})
    payload['equality.json'] = immutable.canonical_json({'status': 'complete-scientific-product-byte-equality' if equal else 'failed-execution-or-product-equality', 'all_paired_scientific_products_equal': equal, 'complete_product_sets': product_sets, 'completion_publication_receipts': 'Fresh destination paths differ truthfully; excluded from scientific product equality.'})
    output.publish_bytes(payload)
    print(json.dumps({'scientific_products_byte_equal': equal, 'executed_subprocesses': sum(r['executed'] for r in records), 'invocations': N + 'vintages/' + a.vintage + '-invocations'}))
    if not equal:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
