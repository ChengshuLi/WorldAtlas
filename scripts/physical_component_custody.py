"""Whole-byte custody of repeated component exports; never scientific input.

One original encoded file per digest, exhaustive logical generation inventories,
and unchanged reports retain actual executions, including incomplete trials.
"""
import argparse
import gzip
import io
import json
import pathlib
import subprocess

from evidence.immutable import canonical_json, descriptor, sha256, safe_path, MAX_FILE_BYTES

ROOT = pathlib.Path(__file__).resolve().parents[1]
OWNED = 'coordination/engineering/physical-gap-components-1005-20261005-local19/'
VERSION = 'worldatlas-component-whole-file-custody-v1'


def describe(path, raw):
    row = descriptor(path, raw)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('Whole encoded file exceeds unchanged limit')
    if path.endswith('.json.gz'):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            decoded = stream.read(MAX_FILE_BYTES + 1)
        if len(decoded) > MAX_FILE_BYTES:
            raise ValueError('Whole decoded file exceeds unchanged limit')
        row.update(uncompressed_bytes=len(decoded), uncompressed_sha256=sha256(decoded))
    return row


def validate(root, index):
    if index['version'] != VERSION:
        raise ValueError('Unexpected whole-file custody version')
    payloads = {p['path']: p for p in index['payloads']}
    if len(payloads) != len(index['payloads']):
        raise ValueError('Duplicate physical payload')
    aliases, used = {}, set()
    for alias in index['aliases']:
        original = safe_path(alias['original']['path'])
        target = safe_path(alias['payload'])
        if original in aliases or target not in payloads:
            raise ValueError('Duplicate alias or missing payload')
        p = root / target
        if p.is_symlink() or not p.is_file():
            raise ValueError('Complete ordinary payload required')
        raw = p.read_bytes()
        original_encoded = {k: v for k, v in alias['original'].items() if not k.startswith('uncompressed_')}
        if descriptor(target, raw) != payloads[target] or descriptor(original, raw) != original_encoded:
            raise ValueError('Redirected or changed whole-file alias')
        if describe(original, raw) != alias['original']:
            raise ValueError('Redirected or changed whole-file alias')
        aliases[original] = raw
        used.add(target)
    if used != set(payloads):
        raise ValueError('Unbound physical payload')
    expected = set()
    full_reports = []
    for generation in index['generations']:
        prefix = safe_path(generation['prefix']).rstrip('/') + '/'
        entry = prefix + ('report.json' if generation['status'] == 'complete' else 'incomplete-export-receipt.json')
        if entry not in aliases:
            raise ValueError('Missing original execution report')
        report = json.loads(aliases[entry])
        rows = [r for family in report['outputs'].values() for r in family] if generation['status'] == 'complete' else report['outputs_preserved']
        inventory = [r['path'] for r in rows] + [entry]
        if inventory != generation['inventory'] or any(not p.startswith(prefix) for p in inventory):
            raise ValueError('Partial or redirected original generation inventory')
        if generation['status'] != 'complete' and report['status'] != 'incomplete-export-failed':
            raise ValueError('Failed trial cannot become complete')
        for r in rows:
            observed = describe(r['path'], aliases[r['path']]) if r['path'] in aliases else {}
            if not r.get('uncompressed_sha256'):
                observed = {k: v for k, v in observed.items() if not k.startswith('uncompressed_')}
            if observed != r:
                raise ValueError('Missing or changed original output')
        expected.update(inventory)
        for code in generation['code']:
            if code['path'] not in aliases or descriptor(code['path'], aliases[code['path']]) != code:
                raise ValueError('Missing complete executed source code')
            expected.add(code['path'])
        if generation['status'] == 'complete':
            # Compare actual preserved bytes, not regeneration or hashes alone.
            normalized = json.loads(aliases[entry].replace(prefix.encode(), b'GENERATION/'))
            full_reports.append((normalized, [aliases[r['path']] for r in rows]))
    if expected != set(aliases):
        raise ValueError('Unexpected or omitted logical custody alias')
    if len(full_reports) != 2 or full_reports[0] != full_reports[1]:
        raise ValueError('Two actual complete runs must match whole bytes and reports')
    return {'logical_files': len(aliases), 'unique_payloads': len(payloads),
            'logical_bytes': sum(len(raw) for raw in aliases.values()),
            'unique_bytes': sum(p['bytes'] for p in payloads.values())}


def pack(output, prefixes):
    output = safe_path(output)
    if not output.startswith(OWNED):
        raise ValueError('Custody must remain in owned packet')
    out = ROOT / output
    if out.exists():
        raise ValueError('Preserve prior custody vintages')
    aliases, payloads, generations = [], {}, []
    out.mkdir(parents=True)

    def retain(path, raw):
        d = describe(path, raw)
        target = output + '/payloads/' + sha256(raw) + '.bin'
        if target not in payloads:
            p = ROOT / target
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('xb') as stream:
                stream.write(raw)
            payloads[target] = descriptor(target, raw)
        aliases.append({'original': d, 'payload': target})

    for prefix in prefixes:
        prefix = safe_path(prefix).rstrip('/') + '/'
        folder = ROOT / prefix
        complete = (folder / 'report.json').is_file()
        entry = prefix + ('report.json' if complete else 'incomplete-export-receipt.json')
        raw = (ROOT / entry).read_bytes()
        report = json.loads(raw)
        rows = [r for family in report['outputs'].values() for r in family] if complete else report['outputs_preserved']
        inventory = [r['path'] for r in rows] + [entry]
        actual = sorted(str(p.relative_to(ROOT)) for p in folder.rglob('*') if p.is_file())
        if sorted(inventory) != actual:
            raise ValueError('Original folder differs from complete recorded inventory')
        for path in inventory:
            retain(path, (ROOT / path).read_bytes())
        commit = report['executed_code_commit']
        source_paths = [r['path'] for r in report['code_inputs']] if complete else [
            'scripts/build-physical-gap-components.py', 'scripts/physical_gap_crosswalk.py',
            'scripts/geographic_components.py', 'scripts/physical_gap_audit.py', 'scripts/evidence/immutable.py']
        code = []
        for path in source_paths:
            source = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)
            alias = OWNED + 'executed-code/' + commit + '/' + path
            if not any(a['original']['path'] == alias for a in aliases):
                retain(alias, source)
            code.append(descriptor(alias, source))
        generations.append({'prefix': prefix.rstrip('/'), 'status': 'complete' if complete else 'incomplete',
                            'executed_code_commit': commit, 'input_commit': report['input_commit'],
                            'inventory': inventory, 'code': code})
    index = {'version': VERSION, 'generations': generations, 'aliases': aliases,
             'payloads': list(payloads.values()), 'limits': ['Transport after actual execution; original whole bytes unchanged.',
             'Failed trial remains incomplete. No factual, source or deployment approval.']}
    result = validate(ROOT, index)
    with (out / 'index.json').open('xb') as stream:
        stream.write(canonical_json(index))
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('generations', nargs=3)
    args = parser.parse_args()
    pack(args.output, args.generations)
