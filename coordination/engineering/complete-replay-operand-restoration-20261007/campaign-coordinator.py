"""1394 metadata coordinator: exact receipts, deterministic resume, isolated jobs.

No worker is launched by reconciliation. The optional acquisition dispatch API
requires live frozen-runtime and resource callbacks, exact fresh freeze bytes,
and a fresh destination. Cohort metadata workers use the existing planner APIs;
native and numerical execution remain explicit root-owned interfaces.
"""
import argparse
import json
import datetime
import time
from pathlib import Path
import subprocess
import sys
import types

OWNED = 'coordination/engineering/complete-replay-operand-restoration-20261007/'
SCOPE = {'sources': 202, 'components': 95173, 'selected': 26276, 'complement': 68897,
         'mismatches': 1294, 'families': 494, 'batches': 49, 'ordered_queries': 10419}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def unique(pins, acquisition):
    result = {}
    for pin in pins:
        key = acquisition.Phase.key(pin)
        need(key not in result or result[key] == pin, 'Conflicting whole coordinator descriptor')
        result[key] = pin
    return list(result.values())


def validate_plan(plan):
    need(plan.get('version') == 1 and plan.get('issue') == 1394 and plan.get('scope') == SCOPE,
         'Wrong complete original campaign scope')
    jobs = plan['jobs']; seen = set()
    need(len(jobs) == 219, 'Wrong complete detached219 job roster')
    for job in jobs:
        name = job['id']
        need(type(name) is str and name not in seen and '/' not in name and '..' not in name,
             'Unsafe/duplicate original job')
        need(len(set(job['dependencies'])) == len(job['dependencies']) and
             set(job['dependencies']) <= seen, 'Non-topological/foreign original dependency')
        need(type(job['output_reserve']) is int and job['output_reserve'] >= 0,
             'Missing prospective job output budget')
        seen.add(name)
    need(jobs[-1]['id'] == 'queries-complete', 'Missing final original query join')
    return jobs



def validate_completion_scope(name, facts):
    expected = {
        'sources-complete': {'sources':202, 'encoded_bytes':232466132},
        'components': {'current_count':95173},
        'candidates-complete': {'components':95173},
        'scope': {'selected':26276, 'complement':68897},
        'routing-whole': {'parts':25},
        'routing-complete': {'complete':95173, 'selected':26276, 'complement':68897},
        'mismatches-complete': {'original_rows':26276, 'mismatches':1294, 'families':494, 'batches':49},
        'physical-complete': {'complete':95173, 'mismatches':1294, 'ordered_queries':10419},
        'queries-complete': {'components':1294, 'ordered_queries':10419},
    }.get(name, {})
    need(all(type(facts.get(k)) is int and facts[k] == v for k,v in expected.items()),
         'Completed original scope counts differ: '+name)


def reconciliation_inputs(plan_pin, plan_pair, source_pin, stage_pairs, freeze_pins, acquisition):
    """Only supplied whole pins: caller admits this union BEFORE reading metadata."""
    need(len(stage_pairs) <= 219 and len(freeze_pins) <= 219, 'Unbounded campaign receipt discovery')
    return unique([plan_pin, *plan_pair, source_pin, *freeze_pins,
                   *[p for pair in stage_pairs.values() for p in pair]], acquisition)


def completed(phase, pair, operation, acquisition):
    need(type(pair) in (list, tuple) and len(pair) == 2, 'Whole publication/inventory pair required')
    inventory = acquisition.completed_inventory(phase, *pair)
    need(inventory['facts']['operation'] == operation, 'Wrong actual completed operation')
    return inventory


def includes(inventory, pins, acquisition):
    actual = {acquisition.Phase.key(p): p for p in inventory['input_descriptors']}
    need(all(actual.get(acquisition.Phase.key(p)) == p for p in pins),
         'Receipt omits/changes required original dependency or freeze')


def reconcile(phase, *, plan_pin, plan_pair, source_pin, stage_pairs, freeze_pins,
              campaign, acquisition, driver):
    """Real bounded receipt reconciliation; neither reads products nor executes jobs."""
    plan_inventory = completed(phase, plan_pair, 'complete1394-detached-acquisition-plan', acquisition)
    need(plan_pin in plan_inventory['outputs'] and plan_inventory['facts']['jobs'] == 219,
         'Unaccepted whole original plan')
    includes(plan_inventory, [source_pin], acquisition)
    plan = json.loads(phase.read(plan_pin)); jobs = validate_plan(plan)
    source = json.loads(phase.read(source_pin)); sources, _ = driver.aliases(source)
    need(set(stage_pairs) <= {j['id'] for j in jobs}, 'Foreign campaign receipt')
    campaign = acquisition.ordinary(campaign)
    need(campaign.is_relative_to(phase.repo/'.cache') and campaign.is_dir(), 'Owned existing campaign required')
    freezes = []
    for pin in freeze_pins:
        freeze = json.loads(phase.read(pin))
        need(freeze.get('issue') == 1394 and freeze.get('version') == 1 and
             freeze.get('plan_pin') == plan_pin and
             freeze.get('plan_publication_pin') == plan_pair[0] and
             freeze.get('plan_inventory_pin') == plan_pair[1], 'Foreign historical freeze/plan lineage')
        freezes.append((pin, freeze))
    rows = []; accepted = {}; next_action = None
    for job in jobs:
        name = job['id']; destination = campaign/name
        pair = stage_pairs.get(name)
        if pair is not None:
            need(pair[0]['path'] == str(destination/'publication.json') and
                 pair[1]['path'] == str(destination/'stage-inventory.json.gz'),
                 'Receipt belongs to another campaign/destination')
            inventory = completed(phase, pair, driver.predecessor_operation(name), acquisition)
            validate_completion_scope(name, inventory['facts'])
            need(all(dep in accepted for dep in job['dependencies']), 'Completed job has unaccepted predecessor')
            includes(inventory, [plan_pin, *plan_pair,
                     *[p for dep in job['dependencies'] for p in stage_pairs[dep]],
                     *[sources[p] for p in job['source_paths']]], acquisition)
            matched = [(pin, freeze) for pin, freeze in freezes
                       if name in freeze.get('admitted_jobs', []) and pin in inventory['input_descriptors']]
            need(len(matched) == 1, 'Missing/ambiguous actual consumed historical job freeze')
            pin, freeze = matched[0]
            need(freeze.get('resource_admission', {}).get('execution_allowed') is True,
                 'Historical job lacked resource admission')
            commit = freeze['execution_commit']
            # Executed code stays tied to its own frozen commit. A future freeze
            # cannot silently relabel it; its root must explicitly accept lineage.
            code = [p for p in inventory['input_descriptors'] if p.get('commit') and p['path'].startswith(OWNED)
                    and (p['path'].endswith('.py') or Path(p['path']).name in
                         ('code-list.json', 'acquisition-code-list.json'))]
            need(code and all(p['commit'] == commit for p in code), 'Historical executed code vintage differs')
            if name in ('components', 'fragments', 'contacts', 'residues'):
                need(inventory['facts']['ledger'] == name, 'Wrong literal ledger receipt')
            accepted[name] = pair
            row = {'id': name, 'state': 'verified-historical-completion', 'publication': pair[0],
                   'inventory': pair[1], 'execution_commit': commit,
                   'complete_phase_bytes': inventory['complete_phase_bytes']}
        else:
            missing = [dep for dep in job['dependencies'] if dep not in accepted]
            # Existing partial/complete-but-unpinned destinations are never reused.
            occupied = destination.exists() or destination.is_symlink()
            state = 'occupied-unreconciled-destination' if occupied else 'blocked-predecessor' if missing else 'ready-needs-fresh-admission'
            row = {'id': name, 'state': state, 'missing_predecessors': missing}
            if next_action is None and not missing:
                next_action = {'id': name, 'state': state, 'operation': job['operation'],
                               'source_paths': job['source_paths'], 'dependencies': job['dependencies'],
                               'output_reserve': job['output_reserve']}
        rows.append(row)
    result = {'kind': 'complete-original-campaign-reconciliation', 'scope': SCOPE,
              'jobs': rows, 'verified_jobs': len(accepted), 'next_action': next_action,
              'acquisition_complete': len(accepted) == 219, 'numerical_complete': False,
              'remaining_interfaces': remaining_interfaces()}
    phase.output('campaign-state.json.gz', acquisition.canonical(result), compress=True)
    return phase.finish({'operation': 'complete-original-campaign-reconciliation',
                         'scope': SCOPE, 'jobs': 219, 'verified_jobs': len(accepted),
                         'numerical_complete': False})


def remaining_interfaces():
    return [
        'Root freeze must include coordinator/planner code and explicitly admit metadata workers.',
        'Each projection consumes full95173 indices; selector generation verifies1294/494/49/10419 and all71 restoration receipts.',
        'Root must admit each materialized selector and its full source dependencies before cohort-acquisition.extract.',
        'Root native worker must authenticate complete native custody and query join, then consume each ordered cohort.',
        'Root numerical worker must authenticate saved full operands/native closures and execute unchanged nine-map operators.',
        'Materialization receipt sets that exceed a real512 descriptor/256MiB metadata Phase need a separate complete bounded reconciliation; no cap waiver is implemented.',
        'Root must reconcile every numerical cohort and inventory all retained products or exact inverse provenance within final flat512/256MiB bounds.'
    ]



def cohort_recipe_plan(phase, *, state_pin, state_pair, stage_pairs, projection_pairs, selector_pair,
                       acquisition, driver, planner, project_pins, runtime_bytes, materialization_pairs=None):
    """Actual metadata recipes after all global joins; no placeholder product pins.

    This job reads only completed inventories, plus complete selector shards when
    available. Prospective worker budgets include all actual discovered inputs.
    Each worker still performs its own complete Phase admission before reads.
    """
    state_inventory = completed(phase, state_pair, 'complete-original-campaign-reconciliation', acquisition)
    need(state_pin in state_inventory['outputs'], 'Unaccepted whole campaign reconciliation')
    state = json.loads(phase.read(state_pin))
    need(state.get('scope') == SCOPE and state.get('verified_jobs') == 219 and
         state.get('acquisition_complete') is True, 'All219 acquisition jobs must be reconciled before cohort recipes')
    verified = {r['id']: [r['publication'], r['inventory']] for r in state['jobs']
                if r['state'] == 'verified-historical-completion'}
    need(all(verified.get(name) == pair for name,pair in stage_pairs.items()),
         'Cohort predecessors differ from actual reconciled campaign')
    expected = ['components', 'mismatches-complete', 'physical-complete', 'queries-complete']
    expected += [f'routing-{n:03}' for n in range(25)]
    expected += [f'physical-{n:03}' for n in range(71)]
    need(set(stage_pairs) == set(expected), 'Missing/foreign complete cohort recipe predecessor')
    inventories = {name: completed(phase, pair, driver.predecessor_operation(name), acquisition)
                   for name, pair in stage_pairs.items()}
    def products(name, prefix):
        return planner.output_set(inventories[name], prefix)
    mismatch_pins = products('mismatches-complete', 'mismatch-index-')
    physical_pairs = [stage_pairs[f'physical-{n:03}'] for n in range(71)]
    common = {'mismatch_pins': mismatch_pins, 'mismatch_pair': stage_pairs['mismatches-complete'],
              'physical_join_pair': stage_pairs['physical-complete']}
    materialization_pairs = materialization_pairs or {}
    need(len(materialization_pairs) <= 256, 'Materialization receipt roster requires a separate bounded reconciliation')
    recipes = []
    for kind, names, prefix in [('components', ['components'], 'components-'),
            ('routing', [f'routing-{n:03}' for n in range(25)], 'routing-'),
            ('physical', [f'physical-{n:03}' for n in range(71)], 'physical-index-')]:
        arguments = dict(common, kind=kind, index_pins=[p for name in names for p in products(name, prefix)],
                         index_stage_pairs=[stage_pairs[name] for name in names])
        inputs = metadata_recipe('projection', arguments, acquisition=acquisition, planner=planner)
        budget = planner.admit_dependencies(inputs, project_pins, runtime_bytes, 16777216, acquisition)
        recipes.append({'id': 'projection-'+kind, 'operation': 'projection', 'arguments': arguments,
                        'output_reserve': 16777216, 'admission': budget,
                        'state': 'verified-historical-completion' if kind in projection_pairs else 'ready-needs-fresh-admission'})
    need(set(projection_pairs) <= {'components', 'routing', 'physical'}, 'Foreign projection receipt')
    projections = {kind: completed(phase, pair, 'complete-original-cohort-index-projection', acquisition)
                   for kind, pair in projection_pairs.items()}
    for kind, inventory in projections.items():
        recipe = next(r for r in recipes if r['id'] == 'projection-'+kind)
        includes(inventory, metadata_recipe('projection', recipe['arguments'], acquisition=acquisition, planner=planner), acquisition)
        need(inventory['facts']['index_kind'] == kind and inventory['facts']['complete'] == 95173 and
             inventory['facts']['mismatches'] == 1294, 'Wrong complete cohort projection receipt')
    if len(projections) == 3:
        candidate_tables = products('components', 'containing-inputs.json')
        need(len(candidate_tables) == 1, 'Missing complete original candidate containing table')
        query_pins = [p for p in inventories['queries-complete']['input_descriptors']
                      if Path(p['path']).name.startswith('native-query-index-')]
        arguments = dict(common, projected_pins={kind: planner.output_set(inv, 'cohort-'+kind+'-')
                         for kind, inv in projections.items()}, projection_pairs=projection_pairs,
                         component_ledger_pair=stage_pairs['components'], candidate_table_pin=candidate_tables[0],
                         physical_stage_pairs=physical_pairs, query_join_pair=stage_pairs['queries-complete'],
                         query_pins=query_pins)
        inputs = metadata_recipe('selectors', arguments, acquisition=acquisition, planner=planner)
        budget = planner.admit_dependencies(inputs, project_pins, runtime_bytes, 33554432, acquisition)
        recipes.append({'id': 'selector-plan', 'operation': 'selectors', 'arguments': arguments,
                        'output_reserve': 33554432, 'admission': budget,
                        'state': 'verified-historical-completion' if selector_pair else 'ready-needs-fresh-admission'})
    if selector_pair is not None:
        need(len(projections) == 3, 'Selector plan lacks all complete projections')
        inventory = completed(phase, selector_pair, 'complete-original-cohort-selector-plan', acquisition)
        selector_recipe = next(r for r in recipes if r['id'] == 'selector-plan')
        includes(inventory, metadata_recipe('selectors', selector_recipe['arguments'], acquisition=acquisition, planner=planner), acquisition)
        facts = inventory['facts']
        need(all(facts[k] == v for k, v in {'components':1294, 'families':494, 'batches':49,
             'ordered_queries':10419}.items()), 'Selector plan scope differs')
        selectors = []; seen = set(); query_count = 0
        for pin in planner.output_set(inventory, 'cohort-selectors-'):
            for row_ordinal, line in enumerate(phase.read(pin).splitlines()):
                selector = json.loads(line); ordinal = selector['cohort_ordinal']
                need(ordinal == len(selectors), 'Noncontiguous original cohort selector order')
                ids = [r['id'] for r in selector['rows']]
                need(len(ids) == len(set(ids)) and not seen.intersection(ids), 'Duplicate original cohort identity')
                seen.update(ids); query_count += selector['ordered_queries']
                arguments = {'shard_pin': pin, 'ordinal': row_ordinal,
                             'expected_sha256': acquisition.sha(line+b'\n'),
                             'selector_plan_pair': selector_pair}
                inputs = metadata_recipe('materialize', arguments, acquisition=acquisition, planner=planner)
                budget = planner.admit_dependencies(inputs, project_pins, runtime_bytes, 33554432, acquisition)
                materialized = materialization_pairs.get(str(ordinal))
                if materialized is not None:
                    actual = completed(phase, materialized, 'complete-original-cohort-selector-materialization', acquisition)
                    includes(actual, inputs, acquisition)
                    need(actual['facts']['cohort_ordinal'] == ordinal and
                         actual['facts']['whole_selector_sha256'] == arguments['expected_sha256'] and
                         actual['facts']['components'] == selector['components'] and
                         actual['facts']['ordered_queries'] == selector['ordered_queries'],
                         'Changed actual materialized cohort selector receipt')
                selectors.append({'id': f'selector-{ordinal:03}', 'operation': 'materialize',
                                  'arguments': arguments, 'output_reserve':33554432, 'admission':budget,
                                  'state':'verified-historical-completion' if materialized else 'ready-needs-fresh-admission'})
        need(len(seen) == 1294 and query_count == 10419 and len(selectors) == facts['cohorts'],
             'Incomplete original disjoint selector campaign')
        need(set(materialization_pairs) <= {str(n) for n in range(len(selectors))}, 'Foreign materialization receipt ordinal')
        recipes += selectors
    else:
        need(not materialization_pairs, 'Materialization receipt lacks complete selector plan')
    next_action = next((r['id'] for r in recipes if r['state'] == 'ready-needs-fresh-admission'), None)
    phase.output('cohort-worker-recipes.json.gz', acquisition.canonical({'scope':SCOPE,
                 'recipes':recipes, 'next_metadata_action':next_action, 'numerical_complete':False, 'remaining_interfaces':remaining_interfaces()}), compress=True)
    return phase.finish({'operation':'complete-original-cohort-worker-recipes', 'scope':SCOPE,
                         'recipe_count':len(recipes), 'numerical_complete':False})


def metadata_recipe(operation, arguments, *, acquisition, planner):
    """Derive real metadata worker input union without opening any product."""
    if operation == 'cohort-recipes':
        return unique([arguments['state_pin'], *arguments['state_pair'],
                       *[p for pair in arguments['stage_pairs'].values() for p in pair],
                       *[p for pair in arguments['projection_pairs'].values() for p in pair],
                       *(arguments['selector_pair'] or []), *arguments.get('selector_shard_pins', []),
                       *[p for pair in arguments.get('materialization_pairs', {}).values() for p in pair]], acquisition)
    if operation == 'projection':
        need(arguments['kind'] in ('components', 'routing', 'physical'), 'Foreign projection kind')
        return planner.projection_dependencies(arguments['index_pins'], arguments['mismatch_pins'],
                    arguments['index_stage_pairs'], arguments['mismatch_pair'], arguments['physical_join_pair'], acquisition)
    if operation == 'selectors':
        keys = ('projected_pins', 'projection_pairs', 'mismatch_pins', 'mismatch_pair', 'component_ledger_pair',
                'candidate_table_pin', 'physical_stage_pairs', 'physical_join_pair', 'query_join_pair', 'query_pins')
        need(set(arguments) == set(keys), 'Foreign/missing actual selector arguments')
        return planner.selector_dependencies(**arguments, acquisition=acquisition)
    if operation == 'materialize':
        need(type(arguments['ordinal']) is int and arguments['ordinal'] >= 0, 'Wrong selector ordinal')
        return unique([arguments['shard_pin'], *arguments['selector_plan_pair']], acquisition)
    raise ValueError('Unimplemented metadata operation')


def metadata_worker(phase, operation, arguments, *, acquisition, planner, project_pins, runtime_bytes):
    """One admitted detached job: no payload returned across the worker boundary."""
    if operation == 'projection':
        return planner.prepare_index(phase, acquisition=acquisition, **arguments)
    if operation == 'selectors':
        return planner.selectors(phase, acquisition=acquisition, project_pins=project_pins,
                                 runtime_bytes=runtime_bytes, **arguments)
    if operation == 'materialize':
        return planner.materialize_selector(phase, arguments['shard_pin'], arguments['ordinal'],
                   arguments['expected_sha256'], arguments['selector_plan_pair'], acquisition)
    raise ValueError('Unimplemented metadata worker')


def dispatch_next(phase, *, freeze_pin, state_pin, state_pair, plan_pin, plan_pair,
                  campaign, python, driver_path, acquisition, driver, runtime_guard,
                  resource_guard, current_commit):
    """Optional root call ONLY. Child reauthenticates freeze/runtime/resource itself.

    Live callbacks must raise on failure. No callback may be substituted with an
    input boolean. This function does not claim child success: only a zero exit
    and a subsequently separately reconciled complete receipt establish progress.
    """
    need(callable(runtime_guard) and callable(resource_guard), 'Live admission callbacks required')
    state_inventory = completed(phase, state_pair, 'complete-original-campaign-reconciliation', acquisition)
    need(state_pin in state_inventory['outputs'], 'Unaccepted campaign state product')
    state = json.loads(phase.read(state_pin)); freeze = json.loads(phase.read(freeze_pin))
    plan_inventory = completed(phase, plan_pair, 'complete1394-detached-acquisition-plan', acquisition)
    need(plan_pin in plan_inventory['outputs'], 'Unaccepted dispatch plan')
    plan = json.loads(phase.read(plan_pin)); jobs = validate_plan(plan)
    action = state.get('next_action')
    need(state.get('scope') == SCOPE and action and action['state'] == 'ready-needs-fresh-admission',
         'No safe fresh next acquisition destination')
    job = next((j for j in jobs if j['id'] == action['id']), None)
    need(job and all(action[k] == job[k] for k in ('operation', 'source_paths', 'dependencies', 'output_reserve')),
         'State next action differs from immutable original plan')
    need(freeze.get('version') == 1 and freeze.get('issue') == 1394 and
         freeze.get('execution_commit') == current_commit and
         freeze.get('resource_admission', {}).get('execution_allowed') is True and
         action['id'] in freeze.get('admitted_jobs', []) and freeze.get('plan_pin') == plan_pin and
         freeze.get('plan_publication_pin') == plan_pair[0] and freeze.get('plan_inventory_pin') == plan_pair[1],
         'Fresh root freeze has not admitted this exact next job and whole plan')
    historical = [r['publication'] for r in state['jobs'] if r['state'] == 'verified-historical-completion']
    need(freeze.get('accepted_historical_publication_pins') == historical,
         'Fresh root must explicitly accept exact historical publication lineage')
    campaign = acquisition.ordinary(campaign)
    need(campaign.is_relative_to(phase.repo/'.cache') and campaign.is_dir() and
         not (campaign/action['id']).exists() and not (campaign/action['id']).is_symlink(),
         'Dispatch destination is occupied or foreign')
    need(Path(python) == Path(sys.executable) and Path(driver_path) == phase.repo/OWNED/'acquisition-driver.py',
         'Only actual frozen interpreter and original detached driver permitted')
    runtime_guard(); resource_guard()
    command = driver.detached_command(python, driver_path, freeze_pin['path'], freeze_pin['sha256'],
                                      plan_pin['path'], campaign, action['id'])
    # Keep actual execution logs even if the child fails or final admission fails.
    # The parent reads only bounded logs, never the child's geometry or state.
    log_dir = acquisition.ordinary(phase.destination.parent /
                                  (phase.destination.name + '.child-logs'))
    need(not log_dir.exists(), 'Fresh exclusive child log destination required')
    log_dir.mkdir(exist_ok=False)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tick = time.monotonic()
    with (log_dir/'stdout.txt').open('xb') as stdout, (log_dir/'stderr.txt').open('xb') as stderr:
        result = subprocess.run(command, cwd=phase.repo, stdin=subprocess.DEVNULL,
                                stdout=stdout, stderr=stderr, check=False)
    elapsed = time.monotonic()-tick
    ended = datetime.datetime.now(datetime.timezone.utc).isoformat()
    runtime_guard()
    for name in ('stdout.txt', 'stderr.txt'):
        with (log_dir/name).open('rb') as stream:
            raw = stream.read(acquisition.FILE+1)
        need(len(raw) <= acquisition.FILE, 'Actual child log exceeds ordinary bound; preserve failure')
        phase.output('child-'+name, raw)
    phase.output('dispatch-result.json', acquisition.canonical({'job': action['id'], 'returncode': result.returncode,
                 'command': command, 'actual_start_utc': started, 'actual_end_utc': ended,
                 'elapsed_seconds': elapsed, 'preserved_log_directory': str(log_dir),
                 'receipt_reconciliation_required': True, 'numerical_complete': False}))
    return phase.finish({'operation': 'original-acquisition-child-dispatch', 'job': action['id'],
                         'returncode': result.returncode, 'receipt_reconciliation_required': True})



def detached_metadata_command(python, coordinator, freeze_pin, request_pin):
    """Descriptor-only root launch recipe; no process or payload is opened."""
    cache = Path(coordinator).resolve().parents[3]/'.cache/1394-never-materialized-bytecode'
    return [str(python), '-I', '-S', '-B', '-X', 'pycache_prefix='+str(cache), str(coordinator),
            '--freeze', freeze_pin['path'], '--freeze-sha256', freeze_pin['sha256'],
            '--request', request_pin['path'], '--request-sha256', request_pin['sha256']]


def main():
    """Future frozen metadata-only worker. There is deliberately no launch CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--freeze-sha256', required=True)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--request-sha256', required=True)
    args = parser.parse_args(); here = Path(__file__).resolve().parent; repo = here.parents[2]
    def bounded_root(path, digest):
        need(path.is_absolute() and path.is_relative_to(repo/'.cache') and
             not any(p.is_symlink() for p in (path, *path.parents)), 'Owned ordinary root metadata required')
        with path.open('rb') as stream:
            raw = stream.read(1048577)
        import hashlib
        need(len(raw) <= 1048576 and hashlib.sha256(raw).hexdigest() == digest, 'Root metadata whole pin differs')
        return raw
    freeze_raw = bounded_root(args.freeze, args.freeze_sha256); freeze = json.loads(freeze_raw)
    request_raw = bounded_root(args.request, args.request_sha256); request = json.loads(request_raw)
    need(freeze.get('issue') == 1394 and freeze.get('version') == 1 and
         freeze.get('resource_admission', {}).get('execution_allowed') is True and
         {'path': str(args.request), 'bytes': len(request_raw), 'sha256': args.request_sha256}
         in freeze.get('admitted_coordinator_requests', []), 'Unadmitted exact coordinator request')
    commit = freeze['execution_commit']
    need(type(commit) is str and len(commit) == 40 and all(c in '0123456789abcdef' for c in commit), 'Immutable execution commit required')
    run_raw = subprocess.check_output(['git', '-C', str(repo), 'show', commit+':'+OWNED+'run.py'])
    need((here/'run.py').read_bytes() == run_raw, 'Frozen root entry changed')
    entry = types.ModuleType('campaign_frozen_entry'); entry.__file__ = str(here/'run.py'); sys.modules[entry.__name__] = entry
    exec(compile(run_raw, entry.__file__, 'exec'), entry.__dict__)
    pins, baseline, shared, guard, loaded, runtime, runtime_pin, runtime_index = entry.frozen(commit)
    own_raw = baseline.pinned_bytes(OWNED+'campaign-coordinator.py')
    guard.all_callables(sys.modules[__name__], own_raw)
    names = {'acquisition': OWNED+'acquisition-phases.py', 'driver': OWNED+'acquisition-driver.py',
             'planner': OWNED+'cohort-planning.py'}
    modules = baseline.load_modules(names)
    def runtime_guard():
        loaded['runtime'].loaded(runtime_pin, runtime_index, repo=repo, owned=OWNED, project_pins=pins)
        guard.all_callables(sys.modules[__name__], own_raw)
        for name, module in modules.items():
            guard.all_callables(module, baseline.pinned_bytes(names[name]))
    runtime_guard()
    node = '/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
    subprocess.run([node, str(repo/'scripts/local-workspace.mjs'), 'check'], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    acquisition = modules['acquisition']; custody = {p['path'] for p in runtime['whole_runtime_aliases']}
    project = [p for p in pins if p['path'] not in custody]; installed = runtime['logical_runtime_raw_bytes']
    operation = request['operation']; arguments = request['arguments']
    root_pins = [{'path': str(args.freeze), 'bytes': len(freeze_raw), 'sha256': args.freeze_sha256},
                 {'path': str(args.request), 'bytes': len(request_raw), 'sha256': args.request_sha256}]
    if operation == 'reconcile':
        inputs = reconciliation_inputs(arguments['plan_pin'], arguments['plan_pair'], arguments['source_pin'],
                                       arguments['stage_pairs'], arguments['freeze_pins'], acquisition)
    else:
        inputs = metadata_recipe(operation, arguments, acquisition=acquisition, planner=modules['planner'])
    whole = unique([*inputs, *root_pins, *project], acquisition)
    project_keys = {acquisition.Phase.key(p) for p in project}
    actual_inputs = [p for p in whole if acquisition.Phase.key(p) not in project_keys]
    phase = acquisition.Phase(repo, Path(request['destination']), actual_inputs,
                              runtime_bytes=installed, runtime_verified=True, project_pins=project,
                              output_reserve=request['output_reserve'])
    for pin in root_pins:
        phase.read(pin)
    # Recheck callable/runtime custody immediately before completion publication.
    original_finish = phase.finish
    def guarded_finish(facts):
        runtime_guard()
        return original_finish(facts)
    phase.finish = guarded_finish
    if operation == 'reconcile':
        receipt = reconcile(phase, acquisition=acquisition, driver=modules['driver'], **arguments)
    elif operation == 'cohort-recipes':
        recipe_args = {k:v for k,v in arguments.items() if k != 'selector_shard_pins'}
        receipt = cohort_recipe_plan(phase, acquisition=acquisition, driver=modules['driver'],
                     planner=modules['planner'], project_pins=project, runtime_bytes=installed, **recipe_args)
    else:
        receipt = metadata_worker(phase, operation, arguments, acquisition=acquisition, planner=modules['planner'],
                                  project_pins=project, runtime_bytes=installed)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
