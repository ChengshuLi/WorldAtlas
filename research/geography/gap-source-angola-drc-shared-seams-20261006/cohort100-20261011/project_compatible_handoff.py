"""Project authenticated retained evidence to actual SOURCE-entry-compatible IDs.

This is metadata selection only. It never reconstructs geometry, changes an
original hash or reruns source/physical/current numerical work.
"""
import collections
import copy
import hashlib
import json
import pathlib
import resource
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OWN = HERE.parent.relative_to(ROOT).as_posix()
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def main():
    head, vintage = sys.argv[1:]
    if git('rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('Exact execution HEAD required')
    paths = [HERE.relative_to(ROOT).as_posix() + '/' + n for n in
             ['project_compatible_handoff.py', 'compatible-handoff-inputs.json']]
    paths.append('scripts/evidence/immutable.py')
    pins = []
    for path in paths:
        raw = git('show', head + ':' + path)
        if raw != (ROOT / path).read_bytes():
            raise ValueError('Unfrozen metadata helper/control')
        pins.append({'path': path, 'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'file-bytes'})
    config = json.loads((ROOT / paths[1]).read_bytes())
    ns = {'__name__': 'immutable_projection', '__file__': str(ROOT / paths[2])}
    exec(compile((ROOT / paths[2]).read_bytes(), ns['__file__'], 'exec'), ns)
    base = ns['Baseline'](ROOT, head, pins + config['inputs'], max_phase_bytes=config['logical_limit_bytes'])
    destination = ns['NewVintage'](base, OWN + '/', vintage,
                                  ['source-handoff.json', 'all100-dispositions.json', 'projection.json'])
    old_scope, old_dispositions, check = [json.loads(base.pinned_bytes(pin['path'])) for pin in config['inputs']]
    original_ids = old_scope['scopeIds']
    if (len(original_ids) != 4 or check['head'] != config['predecessor_head']
            or check['handoff']['sha256'] != config['inputs'][0]['sha256']
            or check['handoff']['bytes'] != config['inputs'][0]['bytes']
            or [row['component_id'] for row in check['cases']] != original_ids):
        raise ValueError('SOURCE preflight was not the exact retained four-case handoff')
    for product in check['inputs']:
        bindings = [b for b in old_scope['consumed_source_bindings'] if b['source_id'] == product['source_id']]
        if len(bindings) != 1 or any(product[k] != bindings[0][v] for k, v in
                [('bytes', 'whole_bytes'), ('sha256', 'whole_sha256'), ('feature_count', 'feature_count')]):
            raise ValueError('Whole-source preflight edition mismatch')
    checks = {row['component_id']: row for row in check['cases']}
    selected = []
    for cid in original_ids:
        hits = checks[cid]['hits']
        passed = bool(hits) and all(len(hit['matches']) == 1
            and hit['matches'][0]['feature_sha256'] == hit['recorded_feature_sha256']
            and hit['matches'][0]['geometry_sha256'] == hit['recorded_geometry_sha256']
            and hit['passed'] for hit in hits)
        if passed:
            selected.append(cid)
    held = [cid for cid in original_ids if cid not in selected]
    if len(selected) != 3 or len(held) != 1 or not held[0].startswith('physical-component:ab0110c9') or check['passed']:
        raise ValueError('Unexpected source-entry disposition; require explicit new review')
    scope = copy.deepcopy(old_scope)
    scope['scopeIds'] = selected
    for name in ['candidate_source_native_bindings', 'original_physical_comparison_bindings', 'original_candidate_canonical_bindings']:
        scope[name] = [row for row in scope[name] if row['component_id'] in selected]
    targets = {row['retained_payload']['target_stable_location_id'] for row in scope['candidate_source_native_bindings']}
    scope['original_target_canonical_bindings'] = [row for row in scope['original_target_canonical_bindings'] if row['target_id'] in targets]
    scope['original_gap_membership']['members'] = [row for row in scope['original_gap_membership']['members'] if row['component_id'] in selected]
    members = scope['original_gap_membership']['members']
    for key, member_key in [('batches', 'original_batch_id'), ('families', 'original_family_id')]:
        keep = {row[member_key] for row in members}
        scope['original_membership_evidence'][key] = [row for row in scope['original_membership_evidence'][key] if row['id'] in keep]
    # The complete original current/physical reports are deliberately retained.
    # Their four-case execution facts must not be relabeled as three-case runs.
    scope['execution_commit'] = head
    scope['source_entry_qualification'] = {'predecessor': config['inputs'][0], 'preflight': config['inputs'][2],
        'source_relative_premise_count': 4, 'immediate_source_entry_count': 3, 'serialization_held_ids': held,
        'representation': 'Exact SOURCE-stage JavaScript full-source feature/geometry hash join; original hashes unchanged.'}
    scope['unknowns'].append('ab011 remains source-relative supported but held outside immediate execution membership because original Python source hashes differ from actual JavaScript SOURCE-stage serialization. Explicit engineering preimage support and renewed gates are required.')
    scope['consumed_inputs'] = list(scope['consumed_inputs']) + [{'commit': head, **pin} for pin in config['inputs']]
    summary = copy.deepcopy(old_dispositions)
    summary['execution_scope_proposed'] = selected
    summary['source_relative_premise_count'] = 4
    summary['immediate_source_entry_count'] = 3
    summary['serialization_held_ids'] = held
    for row in summary['rows']:
        cid = row['component_id']
        if cid in selected:
            row['disposition'] = 'literal-policy-source-supported-full-source-entry-compatible'
        elif cid in held:
            row['disposition'] = 'source-relative-supported-held-full-source-serialization'
        if cid in checks:
            row['full_source_entry_preflight'] = checks[cid]
    if len(summary['rows']) != 100 or any(row['resolved'] for row in summary['rows']):
        raise ValueError('Original accounting changed')
    summary['disposition_counts'] = dict(collections.Counter(row['disposition'] for row in summary['rows']))
    report = {'execution_commit': head, 'kind': 'metadata-only-subset-projection', 'inputs': config['inputs'],
        'execution_code': pins, 'source_relative_premise_count': 4, 'immediate_source_entry_count': 3,
        'serialization_held_ids': held, 'logical_input_bytes': sum(base.consumed.values()),
        'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'limits': ['No numerical, source, physical or current-context replay.',
                   'Prior four-case source-relative evidence and all100 outcomes are unchanged.',
                   'Actual SOURCE/NATIVE and current selected/consumer gates still required.']}
    if report['peak_rss_bytes'] > config['rss_limit_bytes']:
        raise ValueError('Metadata RSS guard exceeded')
    destination.publish({'source-handoff.json': scope, 'all100-dispositions.json': summary, 'projection.json': report})
    print(json.dumps(report))

if __name__ == '__main__':
    main()
