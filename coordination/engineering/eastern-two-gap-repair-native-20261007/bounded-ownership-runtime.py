#!/usr/bin/env python3
"""Run the unchanged exact-interval compiler with five smaller transport ranges.

Only the two observed oversized century buckets are subdivided. Scientific
interval dates, identities, status and evidence are never modified.
"""
import argparse, gzip, hashlib, importlib.util, json, pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
LIMIT = 32 * 1024 * 1024
STOCK = 'scripts/prepare-ownership-runtime.py'
STOCK_SHA = 'e4a701e6983740c661552d5a483cbf2bfc9e7d7b41a40e5c055e6a7608c166bb'
REPLACEMENTS = {1801: [(1801,1851),(1851,1901)],
                1901: [(1901,1926),(1926,1951),(1951,2001)]}


def digest(body):
    return hashlib.sha256(body).hexdigest()


def authenticate(commit, path):
    if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Exact immutable execution commit required before Git')
    relative = pathlib.Path(path).relative_to(ROOT).as_posix()
    actual = pathlib.Path(path).read_bytes()
    frozen = subprocess.check_output(['git', 'show', commit + ':' + relative], cwd=ROOT)
    if actual != frozen:
        raise ValueError('Executed code differs from immutable source: ' + relative)
    return {'commit': commit, 'path': relative, 'bytes': len(actual), 'sha256': digest(actual)}


def refined_ranges(original, start, end):
    before = original(start, end)
    after = []
    for a, b in before:
        if a in REPLACEMENTS:
            if b != a + 100:
                raise ValueError('Unexpected original oversized range')
            after.extend(REPLACEMENTS[a])
        else:
            after.append((a, b))
    if len(after) != len(before) + 3 or len(before) != 51:
        raise ValueError('Unexpected complete stock range roster')
    if any(a >= b for a, b in after) or any(a[1] != b[0] for a, b in zip(after, after[1:])):
        raise ValueError('Transport ranges must be ordered and contiguous')
    return after


def bounded_pin(path):
    raw = pathlib.Path(path).read_bytes()
    decoded = gzip.decompress(raw) if str(path).endswith('.gz') else raw
    if len(raw) > LIMIT or len(decoded) > LIMIT:
        raise ValueError('Ordinary encoded or decoded body exceeds 32MiB: ' + str(path))
    return {'path': pathlib.Path(path).name, 'bytes': len(raw), 'sha256': digest(raw),
            'decoded_bytes': len(decoded), 'decoded_sha256': digest(decoded)}


def run(commit, source, output, receipt):
    code = [authenticate(commit, __file__), authenticate(commit, ROOT / STOCK)]
    if code[1]['sha256'] != STOCK_SHA:
        raise ValueError('Unchanged stock compiler pin differs')
    if output.exists():
        raise ValueError('Fresh output required; no stock cache reuse')
    index = json.loads((source / 'index.json').read_text())
    inputs = [bounded_pin(source / p) for p in ['index.json'] +
              [e['path'] for e in index['parts'] + index['evidence_parts']]]
    input_bytes = sum(p['bytes'] for p in inputs) + sum(p['bytes'] for p in code)
    if input_bytes + 64 * 1024 * 1024 > 256 * 1024 * 1024:
        raise ValueError('Complete inputs and reserved outputs exceed flat aggregate')
    spec = importlib.util.spec_from_file_location('unchanged_ownership_runtime', ROOT / STOCK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.bucket_ranges
    expected = refined_ranges(original, index['valid_from'], index['valid_to'])
    module.bucket_ranges = lambda start, end: refined_ranges(original, start, end)
    result = module.prepare(source, output)
    if [(b['valid_from'], b['valid_to']) for b in result['buckets']] != expected:
        raise ValueError('Actual runtime range roster differs')
    outputs = [bounded_pin(output / p) for p in ['index.json'] + [b['path'] for b in result['buckets']]]
    total = input_bytes + sum(p['bytes'] for p in outputs)
    if total > 256 * 1024 * 1024:
        raise ValueError('Actual scoped complete aggregate exceeds limit')
    # The manual import object is explicitly authenticated, not inferred from sys.modules.
    authenticate(commit, module.__file__)
    for pin in inputs:
        if bounded_pin(source / pin['path']) != pin:
            raise ValueError('Complete input changed during compilation')
    receipt.write_text(json.dumps({'execution_commit': commit, 'executed_code': code,
        'stock_compiler_unchanged': True, 'transport_only_range_override': REPLACEMENTS,
        'inputs': inputs, 'outputs': outputs, 'source_intervals': result['source_intervals'],
        'transport_intervals': result['transport_intervals'], 'ranges': expected,
        'scoped_encoded_aggregate_bytes': total,
        'final_combined_admission_claimed': False,
        'original_interval_dates_and_evidence_preserved': True,
        'stock_encoded_only_guard_supplemented_with_decoded_limit': True}, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--source', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--receipt', type=pathlib.Path, required=True)
    args = parser.parse_args()
    run(args.commit, args.source.resolve(), args.output.resolve(), args.receipt.resolve())
