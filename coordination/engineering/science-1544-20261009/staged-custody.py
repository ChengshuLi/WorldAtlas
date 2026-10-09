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
import stat

from evidence.immutable import Baseline, canonical_json, descriptor, sha256, safe_path, MAX_FILE_BYTES

ROOT = pathlib.Path(__file__).resolve().parents[1]
OWNED = 'coordination/engineering/physical-gap-components-1005-20261005-local19/'
VERSION = 'worldatlas-component-whole-file-custody-v1'
EXECUTED_PATHS = ['scripts/build-physical-gap-components.py', 'scripts/physical_gap_crosswalk.py',
                  'scripts/geographic_components.py', 'scripts/physical_gap_audit.py', 'scripts/evidence/immutable.py']


def ordinary_read(root, path):
    root = pathlib.Path(root)
    path = safe_path(path)
    target = root / path
    require_paths = [target, *list(target.parents)[:len(path.split('/')) - 1]]
    if root.is_symlink() or any(p.is_symlink() for p in require_paths):
        raise ValueError('Complete ordinary path required; symlinked ancestor')
    info = target.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
        raise ValueError('Complete ordinary bounded file required')
    raw = target.read_bytes()
    if len(raw) != info.st_size:
        raise ValueError('Whole file changed during read')
    return raw


def describe(path, raw):
    row = descriptor(path, raw)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('Whole encoded file exceeds unchanged limit')
    if path.endswith(('.json.gz', '.geojson.gz')):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            decoded = stream.read(MAX_FILE_BYTES + 1)
        if len(decoded) > MAX_FILE_BYTES:
            raise ValueError('Whole decoded file exceeds unchanged limit')
        row.update(uncompressed_bytes=len(decoded), uncompressed_sha256=sha256(decoded))
    return row


def validate(root, index):
    if index['version'] != VERSION:
        raise ValueError('Unexpected whole-file custody version')
    generations = index['generations']
    if (len(generations) != 3 or len({g['prefix'] for g in generations}) != 3
            or sorted(g['status'] for g in generations) != ['complete', 'complete', 'incomplete']):
        raise ValueError('Require two distinct complete runs and original incomplete trial')
    payloads = {p['path']: p for p in index['payloads']}
    if len(payloads) != len(index['payloads']):
        raise ValueError('Duplicate physical payload')
    aliases, alias_targets, used, raw_payloads = {}, {}, set(), {}
    payload_rows, descriptions = {}, {}

    def observed(original, target):
        # Reuse only descriptors of bytes captured in this invocation. Logical
        # paths still determine whether bounded gzip decoding is required; a
        # plain alias cannot authenticate a compressed alias's decoded content.
        key = (target, original.endswith(('.json.gz', '.geojson.gz')))
        if key not in descriptions:
            descriptions[key] = describe(original, raw_payloads[target])
        return {**descriptions[key], 'path': original}

    for alias in index['aliases']:
        original = safe_path(alias['original']['path'])
        target = safe_path(alias['payload'])
        if original in aliases or target not in payloads:
            raise ValueError('Duplicate alias or missing payload')
        if target not in raw_payloads:
            raw_payloads[target] = ordinary_read(root, target)
            payload_rows[target] = descriptor(target, raw_payloads[target])
        raw = raw_payloads[target]
        original_encoded = {k: v for k, v in alias['original'].items() if not k.startswith('uncompressed_')}
        if payload_rows[target] != payloads[target] or {**payload_rows[target], 'path': original} != original_encoded:
            raise ValueError('Redirected or changed whole-file alias')
        if observed(original, target) != alias['original']:
            raise ValueError('Redirected or changed whole-file alias')
        aliases[original] = raw
        alias_targets[original] = target
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
        for key in ('input_commit', 'executed_code_commit'):
            if report.get(key) != generation.get(key):
                raise ValueError('Original execution/report commit binding changed')
        rows = [r for family in report['outputs'].values() for r in family] if generation['status'] == 'complete' else report['outputs_preserved']
        inventory = [r['path'] for r in rows] + [entry]
        if inventory != generation['inventory'] or any(not p.startswith(prefix) for p in inventory):
            raise ValueError('Partial or redirected original generation inventory')
        if generation['status'] != 'complete' and report['status'] != 'incomplete-export-failed':
            raise ValueError('Failed trial cannot become complete')
        for r in rows:
            output = observed(r['path'], alias_targets[r['path']]) if r['path'] in aliases else {}
            if not r.get('uncompressed_sha256'):
                output = {k: v for k, v in output.items() if not k.startswith('uncompressed_')}
            if output != r:
                raise ValueError('Missing or changed original output')
        expected.update(inventory)
        for code in generation['code']:
            if code['path'] not in aliases or descriptor(code['path'], aliases[code['path']]) != code:
                raise ValueError('Missing complete executed source code')
            expected.add(code['path'])
        if generation['code']:
            prefix_code = OWNED + 'executed-code/' + report['executed_code_commit'] + '/'
            original_code = []
            for code in generation['code']:
                if not code['path'].startswith(prefix_code):
                    raise ValueError('Executed source alias is outside original vintage')
                original_code.append({**code, 'path': code['path'][len(prefix_code):]})
            if [c['path'] for c in original_code] != EXECUTED_PATHS:
                raise ValueError('Incomplete original executed source roster')
            baseline = Baseline(ROOT, report['executed_code_commit'], original_code)
            for code in generation['code']:
                if aliases[code['path']] != baseline.read(code['path'][len(prefix_code):]):
                    raise ValueError('Executed source code differs from immutable Git')
            if generation['status'] == 'complete' and original_code != report['code_inputs']:
                raise ValueError('Incomplete original executed source roster')
        else:
            raise ValueError('Missing original executed source roster')
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
