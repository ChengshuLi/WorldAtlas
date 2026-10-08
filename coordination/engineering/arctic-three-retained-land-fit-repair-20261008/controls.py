"""Actual retained-target construction and directed guard controls; not a world run."""
import json, tempfile, pathlib, unittest.mock
import producer as p
from kernel import exact_additions, neighbor_relation, COMPONENT_TARGETS
from shapely.geometry import shape, Polygon

def rejected(fn, label):
    try:
        fn()
    except (ValueError, AssertionError):
        return {'control': label, 'status': 'PASS'}
    raise AssertionError('Control accepted: ' + label)

def run():
    plan = json.loads((p.HERE / 'input-plan.json').read_bytes())
    decisions = json.loads(p.read(p.ROOT / plan['source_decisions']['path'], plan['source_decisions']))
    rows = json.loads(p.decoded(p.read(p.HERE / plan['current_part29_local_alias'], plan['current_part29']), plan['current_part29']))['features']
    old = {f['id']: shape(f['geometry']) for f in rows if f['id'] in COMPONENT_TARGETS.values()}
    candidates = {r['component_id']: shape(r['candidate_geometry']) for r in decisions['results'] if r['component_id'] in COMPONENT_TARGETS}
    result = [rejected(lambda: exact_additions(old, candidates), 'actual-add031-and-combined-construction-fails-strict-covers')]
    eligible = dict(candidates)
    candidates = {k: candidates[k] for k in p.CONSTRUCTED_COMPONENTS}
    construct = lambda before, additions: exact_additions(before, additions, expected_components=p.CONSTRUCTED_COMPONENTS)
    after, proofs = construct(old, candidates)
    assert len(after) == 2 and len(proofs) == 2 and all(x['loss_empty'] and x['gain_equals_complete_candidates'] for x in proofs)
    result.append({'control': 'actual-two-strictly-constructible-full-target-additions', 'status': 'PASS'})
    keys = list(candidates)
    result.append(rejected(lambda: construct(old, {k:v for k,v in candidates.items() if k != keys[0]}), 'omitted-component'))
    result.append(rejected(lambda: construct(old, {**candidates, 'foreign': candidates[keys[0]]}), 'foreign-component'))
    result.append(rejected(lambda: construct({next(iter(old)): next(iter(old.values()))}, candidates), 'omitted-target'))
    invalid = Polygon([(0,0), (1,1), (1,0), (0,1), (0,0)])
    result.append(rejected(lambda: construct(old, {**candidates, keys[0]: invalid}), 'invalid-full-polygon'))
    result.append(rejected(lambda: construct(old, {**candidates, keys[0]: old[COMPONENT_TARGETS[keys[0]]]}), 'positive-existing-ownership'))
    nun = [k for k in eligible if COMPONENT_TARGETS[k] == 'atlas:physical:CAN-25:NUN']
    result.append(rejected(lambda: exact_additions(old, {**eligible, nun[1]: eligible[nun[0]]}), 'between-candidate-positive-overlap'))
    target = COMPONENT_TARGETS[keys[0]]
    result.append(rejected(lambda: neighbor_relation('foreign-owner', candidates[keys[0]], old[target], after[target]), 'introduced-positive-neighbor'))
    result.append(rejected(lambda: p.decoded(p.deterministic_gzip(b'x'), {'decoded_bytes': p.FILE_CAP+1, 'decoded_sha256': p.digest(b'x')}), 'decoded-declared-overbound'))
    result.append(rejected(lambda: p.decoded(p.deterministic_gzip(b'x'*100), {'decoded_bytes': 4, 'decoded_sha256': p.digest(b'x'*4)}), 'actual-decoded-overbound'))
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory).resolve() / 'body'
        path.write_bytes(b'body')
        with unittest.mock.patch.object(pathlib.Path, 'open', side_effect=AssertionError('Body opened before admission')) as opened:
            result.append(rejected(lambda: p.read(path, {'bytes': p.FILE_CAP+1, 'sha256': p.digest(b'body'), 'mode': '100644'}), 'declared-overbound-zero-body-opens'))
            assert opened.call_count == 0
        link = pathlib.Path(directory).resolve() / 'link'
        link.symlink_to(path)
        result.append(rejected(lambda: p.read(link, {'bytes':4, 'sha256': p.digest(b'body'), 'mode': '100644'}), 'symlink-input'))
        result.append(rejected(lambda: p.read(path, {'bytes':4, 'sha256':p.digest(b'other'), 'mode': '100644'}), 'changed-complete-body'))
        result.append(rejected(lambda: p.read(path, {'bytes':4, 'sha256':p.digest(b'body'), 'mode': '100755'}), 'wrong-original-mode'))
    runtime = json.loads((p.HERE / 'runtime.json').read_bytes())
    with unittest.mock.patch.object(pathlib.Path, 'open', side_effect=AssertionError('Body opened before complete phase admission')) as opened:
        oversized = [{'actual_path': '/bounded-fixture/' + str(i), 'bytes': p.FILE_CAP, 'sha256': '0'*64} for i in range(9)]
        result.append(rejected(lambda: p.phase_admission(oversized, runtime, []), 'complete-phase-overbudget-zero-runtime-source-opens'))
        assert opened.call_count == 0
    import kernel
    with unittest.mock.patch.object(kernel, 'exact_additions', lambda *a, **k: ({}, [])):
        result.append(rejected(lambda: p.require_callables(runtime), 'actual-imported-numerical-callable-mutation'))
    for name in ('exact_additions', 'neighbor_relation', 'canonical_prepared_land', 'read'):
        with unittest.mock.patch.object(p, name, lambda *a, **k: None):
            result.append(rejected(lambda: p.require_callables(runtime), 'actual-producer-alias-or-callable-mutation-' + name))
    world = json.loads(p.read(p.ROOT / plan['world_index']['path'], plan['world_index']))
    p.validate_world_index(world, plan)
    for label, parts in [('omitted-index-part', world['parts'][:-1]), ('reordered-index', list(reversed(world['parts']))), ('foreign-index-part', [*world['parts'][:-1], 'foreign.json'])]:
        result.append(rejected(lambda: p.validate_world_index({'parts': parts}, plan), label))
    with unittest.mock.patch.object(pathlib.Path, 'open', side_effect=AssertionError('Body opened before descriptor admission')) as opened:
        records = [{'actual_path': '/bounded-fixture/' + str(i), 'bytes': 1} for i in range(513)]
        result.append(rejected(lambda: p.phase_admission(records, {'runtime_files': []}, []), 'descriptor513-zero-body-opens'))
        result.append(rejected(lambda: p.phase_admission([records[0], records[0]], {'runtime_files': []}, []), 'duplicate-actual-identity-zero-body-opens'))
        assert opened.call_count == 0
    import shapely
    with unittest.mock.patch.object(shapely.lib, 'union', shapely.lib.intersection):
        result.append(rejected(lambda: p.require_callables(runtime), 'actual-native-ufunc-identity-substitution'))
    with unittest.mock.patch.object(pathlib.Path, 'open', side_effect=AssertionError('Opened before destination guard')) as opened:
        result.append(rejected(lambda: p.safe_output(p.ROOT / '.cache' / '..' / '..' / 'outside'), 'lexical-output-traversal-zero-opens'))
        result.append(rejected(lambda: p.safe_output(p.HERE / 'producer.py'), 'outside-owned-cache-output-zero-opens'))
        assert opened.call_count == 0
    with tempfile.TemporaryDirectory(dir=p.ROOT / '.cache') as directory:
        parent = pathlib.Path(directory)
        occupied = parent / 'occupied'; occupied.write_bytes(b'existing')
        result.append(rejected(lambda: p.safe_output(occupied), 'existing-output'))
        dangling = parent / 'dangling'; dangling.symlink_to(parent / 'missing')
        result.append(rejected(lambda: p.safe_output(dangling / 'output'), 'dangling-parent-output'))
    with unittest.mock.patch.object(pathlib.Path, 'open', side_effect=AssertionError('Opened before source identity guard')) as opened:
        result.append(rejected(lambda: p.code_guard('a'*40, {'kind':'immutable-git-code-source-v1','head':'a'*40,'root':'/wrong-root'}), 'wrong-code-source-root-zero-opens'))
        result.append(rejected(lambda: p.code_guard('a'*40, {'kind':'immutable-git-code-source-v1','head':'b'*40,'root':str(p.ROOT)}), 'wrong-code-source-head-zero-opens'))
        assert opened.call_count == 0
    return {'stage': 'retained-target and real-function controls only; no full49625-world run', 'controls': result,
            'count': len(result), 'kernel_sha256': p.digest((p.HERE/'kernel.py').read_bytes()),
            'producer_sha256': p.digest((p.HERE/'producer.py').read_bytes()),
            'before_current_v8_part29_sha256': plan['current_part29']['decoded_sha256'], 'source_decisions_sha256': plan['source_decisions']['sha256']}

if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
