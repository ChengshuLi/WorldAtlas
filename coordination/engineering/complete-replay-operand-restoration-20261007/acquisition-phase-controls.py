"""Small real-boundary controls; no global acquisition or scientific replay."""
import argparse
import datetime
import gzip
import importlib.util
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location('bounded_acquisition', here / 'acquisition-phases.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    repo = module.ordinary(args.repo).resolve(); out = module.ordinary(args.out)
    module.require(out.resolve().is_relative_to(repo / '.cache') and out.parent.is_dir()
                   and not out.exists(), 'Fresh owned control fixture directory required')
    # Entire fixture/result set is tiny and admitted before any mutation. These
    # controls use a conservative runtime charge, not a scientific runtime PASS.
    reserve = 1048576
    module.require(reserve + 50581160 + module.RECEIPT <= module.PHASE, 'Complete control fixture admission')
    out.mkdir(exist_ok=False)
    checks = []
    def write(name, body, compressed=False):
        raw = gzip.compress(body, mtime=0) if compressed else body
        pin = {'path': str(out / name), 'bytes': len(raw), 'sha256': module.sha(raw)}
        if compressed:
            pin.update(uncompressed_bytes=len(body), uncompressed_sha256=module.sha(body))
        with (out / name).open('xb') as stream:
            stream.write(raw)
        return pin
    def phase(name, pins, budget=reserve):
        return module.Phase(repo, out / name, pins, runtime_bytes=50581160,
                            runtime_verified=True, output_reserve=budget)
    def rejected(name, callback, message):
        try:
            callback()
        except ValueError as error:
            module.require(message in str(error), 'Unrelated safeguard masked intended control: ' + str(error))
            checks.append({'case': name, 'outcome': 'rejected', 'actual_error': str(error)})
        else:
            raise ValueError('Control did not reject: ' + name)
    feature = {'id': 'fixture-fragment:a', 'type': 'Feature', 'properties': {},
               'geometry': {'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 0]]]}}
    containing = write('whole.json.gz', module.canonical({'features': [feature]}), True)
    table = write('table.json', module.canonical([containing]))
    alias = {'kind': 'complete-reconstructed-ledger-object', 'ledger': 'fragments', 'id': feature['id'],
             'input_index': 0, 'selector': ['features', 0], 'containing_table_sha256': table['sha256'],
             'whole_object_bytes': len(module.canonical(feature)), 'whole_object_sha256': module.sha(module.canonical(feature))}
    job = phase('positive', [containing, table])
    actual = module.resolve(job, alias, table, module.canonical)
    module.require(actual == feature, 'Actual inverse alias roundtrip failed')
    job.output('actual-feature.json', module.canonical(actual))
    receipt = job.finish({'operation': 'tiny-real-inverse-alias-control'})
    checks.append({'case': 'actual-whole-encoded-decoded-containing-reader-and-inverse',
                   'outcome': 'passed', 'complete_phase_bytes': receipt['complete_phase_bytes']})
    publication_raw = (out / 'positive/publication.json').read_bytes()
    publication_pin = {'path': str(out / 'positive/publication.json'), 'bytes': len(publication_raw),
                       'sha256': module.sha(publication_raw)}
    job = phase('actual-completion-reader', [publication_pin, receipt['inventory']])
    inventory = module.completed_inventory(job, publication_pin, receipt['inventory'])
    module.require(inventory['facts']['operation'] == 'tiny-real-inverse-alias-control', 'Wrong actual completion facts')
    job.finish({'operation': 'tiny-real-completion-reader-control'})
    checks.append({'case': 'actual-receipt-inventory-complete-accounting', 'outcome': 'passed'})
    partial = write('partial-completion.json', module.canonical({'version': 1, 'complete': False,
                                                               'inventory': receipt['inventory']}))
    rejected('actual-partial-stage-not-complete', lambda: module.completed_inventory(
             phase('partial-reader', [partial, receipt['inventory']]), partial, receipt['inventory']),
             'Missing/changed real stage completion')
    rejected('existing-output', lambda: phase('positive', [containing]), 'Fresh exclusive')
    (out / 'dangling').symlink_to(out / 'absent')
    rejected('dangling-output', lambda: phase('dangling', [containing]), 'Symlink')
    rejected('duplicate-actual-phase-pin', lambda: phase('duplicates', [containing, containing]), 'Duplicate phase input')
    rejected('actual-duplicate-identity', lambda: module.exact_ids([{'id': 'a'}, {'id': 'a'}], 'id'), 'Duplicate/nonstring')
    rejected('actual-foreign-identity', lambda: module.exact_ids([{'id': 'b'}], 'id', ['a']), 'Missing/foreign')
    rejected('actual-nonstring-identity', lambda: module.exact_ids([{'id': 1}], 'id'), 'Duplicate/nonstring')
    bad_alias = dict(alias, selector=['features', 1])
    rejected('wrong-actual-object-ordinal', lambda: module.resolve(phase('bad-ordinal', [containing, table]),
             bad_alias, table, module.canonical), 'Escaped original object ordinal')
    wrong_table = write('wrong-table.json', module.canonical([]))
    rejected('wrong-whole-containing-table', lambda: module.resolve(phase('wrong-table', [wrong_table]),
             alias, wrong_table, module.canonical), 'Wrong actual containing descriptor table')
    other = dict(feature, id='fixture-fragment:b')
    changed = write('coherent-other.json.gz', module.canonical({'features': [other]}), True)
    changed_table = write('coherent-other-table.json', module.canonical([changed]))
    changed_alias = dict(alias, containing_table_sha256=changed_table['sha256'])
    rejected('coherent-changed-actual-feature', lambda: module.resolve(phase('wrong-object', [changed, changed_table]),
             changed_alias, changed_table, module.canonical), 'Complete inverse alias bytes differ')
    rejected('wrong-actual-alias-identity', lambda: module.resolve(phase('wrong-identity', [containing, table]),
             dict(alias, id='foreign'), table, module.canonical), 'Actual inverse alias identity differs')
    job = phase('undeclared', [table])
    rejected('foreign-whole-getter', lambda: job.read(containing), 'Undeclared or changed')
    mutated = write('mutated.json', b'{"a":1}\n')
    job = phase('actual-mutated-input', [mutated])
    Path(mutated['path']).write_bytes(b'{"a":2}\n')
    rejected('actual-consumed-input-drift', lambda: job.read(mutated), 'Whole encoded input differs')
    small = write('small.json', b'{}\n')
    job = phase('actual-output-bound', [small], budget=128)
    job.read(small)
    rejected('actual-decoded-output-aggregate', lambda: job.output('large.json.gz', b'x' * 129, compress=True),
             'Actual stage outputs exceed')
    rejected('prospective-aggregate-before-computation', lambda: phase('oversized', [small], budget=module.PHASE),
             'Complete prospective phase exceeds')
    module.require(not (out / 'oversized').exists() and not (out / 'actual-output-bound').exists(),
                   'Admission failure created a destination')
    job = phase('missing-real-input', [small, table]); job.read(small)
    rejected('declared-but-unconsumed-whole-input', lambda: job.finish({}), 'not actually consumed')
    # Original reconstruction code is a real immutable source, not a fabricated checksum fixture.
    index = json.loads((here / 'source-index.json').read_bytes())
    source = next(p for p in index['files'] if p.get('original_relation', {}).get('original_path') ==
                  'scripts/worldwide_gap_successor.py')
    original_inputs = next(p for p in index['files'] if p.get('original_relation', {}).get('original_path') ==
                           'coordination/engineering/global-physical-comparison-20261006/inputs.py')
    job = phase('actual-original-source', [source, original_inputs])
    raw = job.read(source)
    module.require(b'def reconstruct(' in raw, 'Actual original reconstruction supporting content missing')
    helper = job.read(original_inputs)
    namespace = {'__name__': 'authenticated_tiny_original_inputs'}
    exec(compile(helper, '<actual authenticated original inputs.py>', 'exec'), namespace)
    reconstruct, _, code_receipt = namespace['existing_reconstructor'](raw, source['sha256'], module.canonical)
    before = [{'id': 'a', 'value': 1}, {'id': 'b', 'value': 2}]
    after = [{'id': 'a', 'value': 1}, {'id': 'c', 'value': 3}]
    delta = {'original_count': 2, 'current_count': 2,
             'original_records_sha256': module.sha(module.canonical(before)),
             'current_records_sha256': module.sha(module.canonical(after)),
             'removed_ids': ['b'], 'retained_count': 1,
             'retained_ids_sha256': module.sha(module.canonical(['a'])), 'upsert_records': [after[1]]}
    module.require(reconstruct(before, delta) == after, 'Actual literal tiny reconstruction failed')
    checks.append({'case': 'actual-literal-reconstruct-retained-removed-upsert', 'outcome': 'passed',
                   'executed_code_receipt': code_receipt})
    rejected('actual-literal-duplicated-removal', lambda: reconstruct(before, dict(delta, removed_ids=['b', 'b'])),
             'Missing/duplicated removed record')
    rejected('actual-literal-changed-original-row', lambda: reconstruct([before[0], {'id': 'b', 'value': 4}], delta),
             'Original full record bytes differ')
    source_receipt = job.finish({'operation': 'actual-original-whole-reconstructor-body', 'source_sha256': module.sha(raw)})
    checks.append({'case': 'actual-original-whole-git-body-mode-oid', 'outcome': 'passed',
                   'complete_phase_bytes': source_receipt['complete_phase_bytes']})
    result = {'kind': 'small-actual-acquisition-boundary-controls', 'actual_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'adapter_sha256': module.sha((here / 'acquisition-phases.py').read_bytes()),
              'controls_sha256': module.sha(Path(__file__).read_bytes()), 'checks': checks,
              'limits': ['No full acquisition, ledger, physical support, native or replay run.',
                         'Conservative fixture runtime charge is not frozen scientific runtime authentication.',
                         'Global intermediate sizes and flat publication fit remain unproved.']}
    with (out / 'controls.json').open('xb') as stream:
        stream.write(module.canonical(result))
    print(json.dumps({'checks': len(checks), 'out': str(out / 'controls.json'), 'status': 'PASS-small-boundaries'}))


if __name__ == '__main__':
    main()
