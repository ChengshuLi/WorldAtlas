"""Frozen #1394 custody continuation; preserves every original ce98 execution.

Reconciles complete membership within ordinary phase admission, then invokes the
unchanged original query callables. This entry does not run numerical replay.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types

OWNED = 'coordination/engineering/complete-replay-operand-restoration-20261007/'
OLD = 'ce98a747ecab13ba05bd35b7dd3e20662bc70193'
LIMIT = 1048576


def need(ok, message):
    if not ok:
        raise ValueError(message)


def safe_input(path, repo):
    need(path.is_absolute() and path.is_relative_to(repo / '.cache') and
         not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file(),
         'Ordinary owned complete continuation input required')


def fresh_output(path, repo):
    need(path.is_absolute() and path.is_relative_to(repo / '.cache') and
         '..' not in path.parts and not os.path.lexists(path) and
         path.parent.is_dir() and
         not any(p.is_symlink() or (p.exists() and not p.is_dir())
                 for p in path.parents), 'Fresh ordinary owned output required')


def small(path, *, digest, repo):
    safe_input(path, repo)
    need(path.stat().st_size <= LIMIT, 'Complete continuation metadata over bound')
    with path.open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    need(len(raw) <= LIMIT and hashlib.sha256(raw).hexdigest() == digest,
         'Whole continuation metadata hash differs')
    return raw


def original_project(entry, baseline, current_project):
    names = json.loads(entry.blob(OLD, OWNED + 'code-list.json'))
    names += ['acquisition-code-list.json'] + json.loads(
        entry.blob(OLD, OWNED + 'acquisition-code-list.json'))
    need(len(names) == len(set(names)), 'Original code roster duplicates')
    result = []
    aliases = []
    distinct = []
    current = {p['path']: p for p in current_project}
    def tree(pin):
        row = subprocess.check_output(['git', '-C', str(entry.REPO), 'ls-tree', '-z', pin['commit'], '--', pin['path']]).decode().rstrip('\0')
        meta, path = row.split('\t')
        mode, kind, oid = meta.split()
        need(path == pin['path'] and mode in ('100644', '100755') and kind == 'blob', 'Original/current alias is not ordinary')
        return {'mode': mode, 'blob': oid}
    for name in names:
        raw = entry.blob(OLD, OWNED + name)
        old = {'commit': OLD, 'path': OWNED + name, 'bytes': len(raw),
               'sha256': hashlib.sha256(raw).hexdigest(), 'hash_kind': 'file-bytes'}
        result.append(old)
        new = current.get(old['path'])
        if new is not None and baseline.pinned_bytes(new['path']) == raw:
            old_tree, new_tree = tree(old), tree(new)
            need(old_tree == new_tree and new['bytes'] == old['bytes'] and new['sha256'] == old['sha256'], 'Whole original/current code alias differs')
            aliases.append({'original': dict(old, **old_tree), 'current': dict(new, **new_tree), 'whole_byte_identity': True})
        else:
            distinct.append(old)
    need(len(result) == 46 and len(aliases) == 45 and len(distinct) == 1 and
         distinct[0]['path'] == OWNED + 'acquisition-code-list.json', 'Exact original46 code custody alias roster differs')
    return result, distinct, aliases


def derive_spec(adapter, driver, plan, campaign, prior, admitted_spec):
    """Derive old complete stage rosters from the actual original plan/receipts."""
    jobs = {j['id']: j for j in plan['jobs']}
    need(len(jobs) == len(plan['jobs']) and plan['scope']['components'] == 95173 and
         plan['scope']['ordered_queries'] == 10419, 'Original complete plan differs')
    admitted = {'components': admitted_spec['components'],
                'mismatches-complete': admitted_spec['mismatches']}
    admitted.update({f'physical-{i:03}': value for i, value in enumerate(admitted_spec['physical'])})
    admitted.update({f'routing-{i:03}': value for i, value in enumerate(admitted_spec['routing'])})
    need(len(admitted) == 98, 'Complete original98 predecessor metadata required')
    def stage(name, ordinal=None):
        need(name in jobs and name in admitted, 'Foreign original predecessor stage')
        publication = admitted[name]['publication']
        inventory = admitted[name]['inventory']
        need(publication['path'] == str(campaign / name / 'publication.json') and
             type(publication['bytes']) is int and publication['bytes'] <= adapter.RECEIPT and
             inventory['path'] == str(campaign / name / 'stage-inventory.json.gz'),
             'Admitted original publication/inventory path differs')
        # Read ONLY the already prospectively admitted whole publication bytes.
        # Reject a returned foreign inventory before opening its body.
        receipt = driver.inventory_preview(adapter, publication)
        need(receipt.get('complete') is True and receipt.get('version') == 1 and
             receipt['inventory'] == inventory, 'Actual receipt returned unadmitted inventory')
        preview = driver.inventory_preview(adapter, inventory)
        operation = driver.predecessor_operation(name)
        need(preview['facts']['operation'] == operation,
             'Original predecessor operation differs')
        value = {'publication': publication, 'inventory': inventory,
                 'outputs': preview['outputs'], 'operation': operation}
        if ordinal is not None:
            value['ordinal'] = ordinal
        return value
    return {'version': 1, 'scientific_execution_commit': OLD,
            'continuation_execution_commit': None,
            'scope': {'components': 95173, 'mismatches': 1294,
                      'ordered_queries': 10419},
            'prior_project_pins': prior,
            'components': stage('components'),
            'mismatches': stage('mismatches-complete'),
            'physical': [stage(f'physical-{i:03}', i) for i in range(71)],
            'routing': [stage(f'routing-{i:03}', i) for i in range(25)]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--freeze-sha256', required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    repo = here.parents[2]
    raw = small(args.freeze, digest=args.freeze_sha256, repo=repo)
    freeze = json.loads(raw)
    need(freeze.get('version') == 1 and freeze.get('issue') == 1394 and
         freeze.get('resource_admission', {}).get('execution_allowed') is True,
         'Explicit root continuation admission required')
    head = freeze['execution_commit']
    need(head != OLD and len(head) == 40 and all(c in '0123456789abcdef' for c in head),
         'Fresh frozen continuation head required')
    request_pin = freeze['request_pin']
    request_raw = small(Path(request_pin['path']), digest=request_pin['sha256'], repo=repo)
    need(len(request_raw) == request_pin['bytes'], 'Whole request length differs')
    request = json.loads(request_raw)
    operation = request['operation']
    need(operation in freeze['admitted_operations'], 'Operation not root admitted')
    reserves = {'physical-membership': 52428800, 'physical-membership-join': 1048576,
                'physical-membership-inverse': 1048576, 'query-part-continuation': 4194304,
                'query-join-continuation': 1048576}
    need(operation in reserves and type(request.get('output_reserve')) is int and
         request['output_reserve'] == reserves[operation], 'Exact prospective operation reserve required')
    destination = Path(request['destination'])
    fresh_output(destination, repo)
    spec_pin = request['spec_pin']
    spec_raw = small(Path(spec_pin['path']), digest=spec_pin['sha256'], repo=repo)
    need(len(spec_raw) == spec_pin['bytes'], 'Whole spec length differs')
    spec = json.loads(spec_raw)
    run_raw = subprocess.check_output(['git', '-C', str(repo), 'show', head + ':' + OWNED + 'run.py'])
    need((here / 'run.py').read_bytes() == run_raw, 'Cold entry source differs')
    entry = types.ModuleType('physical_continuation_frozen_entry')
    entry.__file__ = str(here / 'run.py')
    sys.modules[entry.__name__] = entry
    exec(compile(run_raw, entry.__file__, 'exec'), entry.__dict__)
    pins, baseline, shared, guard, loaded, runtime, runtime_pin, runtime_index = entry.frozen(head)
    own_raw = baseline.pinned_bytes(OWNED + 'physical-continuation.py')
    own_module = sys.modules[__name__]
    def own_globals():
        return {key: (json.dumps(value, sort_keys=True) if type(value) in
                      (dict, list, int, float, str, bool, type(None)) else value)
                for key, value in vars(own_module).items() if not key.startswith('__')}
    own_snapshot = own_globals()
    own_defaults = {key: repr((value.__defaults__, value.__kwdefaults__))
                    for key, value in vars(own_module).items()
                    if isinstance(value, types.FunctionType) and value.__module__ == __name__}
    pin_snapshot = json.dumps([head, spec_pin, request_pin, freeze, spec, request], sort_keys=True)
    guard.all_callables(sys.modules[__name__], own_raw)
    names = {'acquisition': OWNED + 'acquisition-phases.py',
             'driver': OWNED + 'acquisition-driver.py',
             'membership': OWNED + 'physical-membership.py',
             'dispatch': OWNED + 'physical-continuation-dispatch.py',
             'immutable': OWNED + 'methods/legacy/immutable.py'}
    modules = baseline.load_modules(names)
    for name in ('acquisition', 'driver', 'immutable'):
        need(baseline.pinned_bytes(names[name]) == entry.blob(OLD, names[name]),
             'Original scientific/custody callable source changed')
    snapshots = {}
    defaults = {}
    class_bindings = {}
    class_defaults = {}
    phase = None
    finish_callback = None
    for name, module in modules.items():
        snapshots[name] = {key: (json.dumps(value, sort_keys=True) if type(value) in
                                (dict, list, int, float, str, bool, type(None)) else value)
                           for key, value in vars(module).items() if not key.startswith('__')}
    for name, module in modules.items():
        defaults[name] = {key: repr((value.__defaults__, value.__kwdefaults__))
                          for key, value in vars(module).items()
                          if isinstance(value, types.FunctionType) and value.__module__ == module.__name__}
    for name, module in modules.items():
        class_bindings[name] = {key: dict(vars(value)) for key, value in vars(module).items()
                               if isinstance(value, type) and value.__module__ == module.__name__}
        class_defaults[name] = {}
        for key, values in class_bindings[name].items():
            for method_name, value in values.items():
                function = value.__func__ if isinstance(value, (staticmethod, classmethod)) else value.fget if isinstance(value, property) else value
                if isinstance(function, types.FunctionType):
                    class_defaults[name][(key, method_name)] = repr((function.__defaults__, function.__kwdefaults__))
    local_proxy = types.ModuleType('physical_continuation_local_guard')
    local_proxy.__file__ = str(here / 'physical-continuation.py')
    local_proxy.main = types.SimpleNamespace()
    local_callables = types.SimpleNamespace()
    setattr(local_proxy.main, '<locals>', local_callables)
    def live_guard():
        need(own_globals() == own_snapshot, 'Own module global/function identity changed')
        need({key: repr((value.__defaults__, value.__kwdefaults__))
              for key, value in vars(own_module).items()
              if isinstance(value, types.FunctionType) and value.__module__ == __name__} == own_defaults,
             'Own function defaults changed')
        need(json.dumps([head, spec_pin, request_pin, freeze, spec, request], sort_keys=True) == pin_snapshot,
             'Completion source/request/freeze closure binding changed')
        need(own_globals.__defaults__ is None and own_globals.__kwdefaults__ is None and
             live_guard.__defaults__ is None and live_guard.__kwdefaults__ is None,
             'Actual live guard defaults changed')
        guard.callable_guard(local_proxy, own_raw, ['main.<locals>.live_guard', 'main.<locals>.own_globals'] +
                             (['main.<locals>.guarded_finish'] if finish_callback is not None else []))
        loaded['runtime'].loaded(runtime_pin, runtime_index, repo=repo, owned=OWNED, project_pins=pins)
        guard.all_callables(sys.modules[__name__], own_raw)
        for name, module in modules.items():
            guard.all_callables(module, baseline.pinned_bytes(names[name]))
            actual = {key: (json.dumps(value, sort_keys=True) if type(value) in
                           (dict, list, int, float, str, bool, type(None)) else value)
                      for key, value in vars(module).items() if not key.startswith('__')}
            need(actual == snapshots[name], 'Live module constant/global binding changed')
            current_defaults = {key: repr((value.__defaults__, value.__kwdefaults__))
                                for key, value in vars(module).items()
                                if isinstance(value, types.FunctionType) and value.__module__ == module.__name__}
            need(current_defaults == defaults[name], 'Live callable defaults changed')
            for key, values in class_bindings[name].items():
                actual_class = dict(vars(getattr(module, key)))
                need(actual_class == values, 'Live class callable/descriptor binding changed')
                for method_name, value in actual_class.items():
                    function = value.__func__ if isinstance(value, (staticmethod, classmethod)) else value.fget if isinstance(value, property) else value
                    if isinstance(function, types.FunctionType):
                        need(repr((function.__defaults__, function.__kwdefaults__)) == class_defaults[name][(key, method_name)],
                             'Live method defaults changed')
        if finish_callback is not None:
            need(phase.finish is finish_callback and finish_callback.__defaults__ is None and
                 finish_callback.__kwdefaults__ is None and finish.__self__ is phase and
                 finish.__func__ is modules['acquisition'].Phase.finish,
                 'Actual Phase completion callback/default/closure changed')
    local_callables.live_guard = live_guard
    local_callables.own_globals = own_globals
    live_guard()
    adapter = modules['acquisition']
    custody = {p['path'] for p in runtime['whole_runtime_aliases']}
    current_project = [p for p in pins if p['path'] not in custody]
    prior, distinct_prior, code_aliases = original_project(entry, baseline, current_project)
    modules['membership'].exact(spec['prior_project_pins'], prior, adapter)
    campaign = Path(freeze['original_campaign'])
    safe_input(campaign / 'plan' / 'publication.json', repo)
    plan_pin = freeze['original_plan_pin']
    freeze_pin = {'path': str(args.freeze), 'bytes': len(raw), 'sha256': args.freeze_sha256}
    project = modules['driver'].unique([*current_project, *distinct_prior, spec_pin, request_pin, freeze_pin, plan_pin])
    runtime_bytes = runtime['logical_runtime_raw_bytes']
    modules['driver'].admit_previews(adapter, project, runtime_bytes=runtime_bytes,
                                     runtime_verified=True, output_reserve=request['output_reserve'])
    plan = modules['driver'].inventory_preview(adapter, plan_pin)
    discovery = []
    if operation in ('physical-membership', 'physical-membership-join'):
        # Qualify the complete spec once in membership and again in its parent.
        # All98 actual old publication/inventory bodies are real phase inputs.
        discovery = [p for stage in [spec['components'], spec['mismatches'], *spec['physical'], *spec['routing']]
                     for p in (stage['publication'], stage['inventory'])]
        modules['driver'].admit_previews(adapter, [*project, *discovery], runtime_bytes=runtime_bytes,
                                         runtime_verified=True, output_reserve=request['output_reserve'])
        expected = derive_spec(adapter, modules['driver'], plan, campaign, prior, spec)
        expected['continuation_execution_commit'] = head
        need(spec == expected, 'Spec does not match original complete plan/actual receipts')
    else:
        # The immutable qualified membership/JOIN consumed by the dispatcher
        # authenticates this exact spec/current code; no off-ledger old previews.
        need(operation in ('physical-membership-inverse', 'query-part-continuation', 'query-join-continuation'),
             'Unsupported qualified continuation operation')
    context = {'execution_commit': head, 'scientific_execution_commit': OLD,
               'request_pin': request_pin, 'freeze_pin': freeze_pin, 'spec_pin': spec_pin,
               'current_project_pins': current_project, 'runtime_bytes': runtime_bytes,
               'bootstrap_project_pins': modules['driver'].unique([*current_project, *distinct_prior, spec_pin, plan_pin])}
    arguments = request['arguments']
    if 'member' in arguments:
        context['membership_stage'] = arguments['member']
    elif 'membership_stage' in request:
        context['membership_stage'] = request['membership_stage']
    dependencies = modules['dispatch'].dependencies(operation, spec, arguments,
                                                     adapter, modules['membership'])
    project = modules['driver'].unique([*project, *discovery])
    keys = {adapter.Phase.key(pin) for pin in dependencies}
    project = [pin for pin in project if adapter.Phase.key(pin) not in keys]
    phase = adapter.Phase(repo, destination, dependencies, runtime_bytes=runtime_bytes,
                          output_reserve=request['output_reserve'], runtime_verified=True,
                          project_pins=project)
    for pin in (spec_pin, request_pin, freeze_pin, plan_pin):
        phase.read(pin)
    finish = phase.finish
    def guarded_finish(facts):
        live_guard()
        return finish(dict(facts, execution_commit=head,
                           scientific_execution_commit=OLD, request_pin=request_pin,
                           freeze_pin=freeze_pin, spec_pin=spec_pin,
                           original_project_pins=prior, whole_original_current_code_aliases=code_aliases,
                           distinct_original_code_inputs=distinct_prior))
    local_callables.guarded_finish = guarded_finish
    finish_callback = guarded_finish
    phase.finish = guarded_finish
    receipt = modules['dispatch'].execute(operation, phase, spec=spec,
        arguments=arguments, context=context, acquisition=adapter,
        helper=modules['membership'], original_immutable=modules['immutable'],
        live_guard=live_guard)
    live_guard()
    print(json.dumps({'operation': operation, 'execution_commit': head,
                      'scientific_execution_commit': OLD, 'receipt': receipt}))


if __name__ == '__main__':
    main()
