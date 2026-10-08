"""Issue1394 detached acquisition dispatcher; never invokes replay operators.

Plan generation is permitted independently. Executing any acquisition job requires
the root's immutable freeze, actual runtime verification and resource admission.
One subprocess executes one job and exits. The campaign coordinator retains only
complete receipt descriptors; it never retains candidate/native/global geometry.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

OWNED = 'coordination/engineering/complete-replay-operand-restoration-20261007/'
NUMERIC = 'coordination/engineering/complete-numeric-closure-diagnosis-20261007/'
ROUTING = 'coordination/engineering/global-actionability-routing-20261007/results/'
PHYSICAL = 'coordination/engineering/global-physical-comparison-20261006/'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def aliases(index):
    pins = {p['path']: p for p in index['files']}
    need(len(pins) == 202 and sum(p['bytes'] for p in pins.values()) == 232466132,
         'Wrong complete202 original source inventory')
    result = {}
    for pin in pins.values():
        result[(pin['commit'], pin['path'])] = pin
        relation = pin.get('original_relation')
        if relation:
            key = (relation['original_commit'], relation['original_path'])
            need(key not in result or result[key] == pin, 'Conflicting complete original source alias')
            result[key] = pin
    for alias in index['original_consumer_aliases']:
        pin = pins[alias['source_path']]
        need(all(alias[k] == pin[k] for k in ('mode', 'blob', 'bytes', 'sha256')),
             'Original consumer/source descriptor mismatch')
        key = (alias['commit'], alias['path'])
        need(key not in result or result[key] == pin, 'Conflicting actual original consumer alias')
        result[key] = pin
    return pins, result


def build_plan(adapter, source_index, config, reader_index, physical_report, *,
               runtime_bytes, project_pins):
    """Metadata-only plan. Dynamic intermediate sizes are admitted at dispatch."""
    source_pins, original = aliases(source_index)
    need(len(config['inputs']) == 44 and len(source_index['original_consumer_aliases']) == 40,
         'Wrong literal original44/derived40 input roster')
    expected_consumers = {(p['commit'], p['path'], p['bytes'], p['sha256'])
                          for p in config['inputs'] if p['kind'] != 'archive_part'}
    actual_consumers = {(p['commit'], p['path'], p['bytes'], p['sha256'])
                        for p in source_index['original_consumer_aliases']}
    need(len(expected_consumers) == len(actual_consumers) == 40 and actual_consumers == expected_consumers,
         'Duplicate/missing/foreign original consumer alias roster')
    for desc in config['inputs']:
        if desc['kind'] == 'archive_part':
            continue
        pin = original[(desc['commit'], desc['path'])]
        need(all(desc.get(k) == pin.get(k) for k in
                 ('bytes', 'sha256', 'uncompressed_bytes', 'uncompressed_sha256')),
             'Wrong actual original consumer closure')
    # Preserve the original179-body index and the literal reader's existing31
    # unused ranked/admin metadata exclusions. The actual202 source roster is
    # authoritative; these bodies are never silently fetched by this driver.
    omitted = {f'i/{n:03}.bin' for n in range(146, 176)} | {'i/177.bin'}
    missing = {p['path'] for p in reader_index['files'] if NUMERIC+p['path'] not in source_pins}
    need(missing == omitted, 'Actual source/legacy metadata exclusions differ')
    reader = {p['original_path']: source_pins[NUMERIC + p['path']]
              for p in reader_index['files'] if 'original_path' in p and p['path'] not in omitted}
    need(len(reader_index['files']) == 179 and len(reader) == 147, 'Wrong whole original reader input inventory')
    jobs = []
    def add(name, operation, sources=(), dependencies=(), reserve=1048576, **arguments):
        need(name not in {j['id'] for j in jobs}, 'Duplicate detached acquisition job')
        jobs.append({'id': name, 'operation': operation, 'source_paths': [p['path'] for p in sources],
                     'dependencies': list(dependencies), 'output_reserve': reserve, 'arguments': arguments})
    auth_groups = adapter.source_groups(source_index['files'], runtime_bytes=runtime_bytes,
                                         project_pins=project_pins)
    for number, group in enumerate(auth_groups):
        add(f'authenticate-{number:03}', 'authenticate', group)
    auth = [j['id'] for j in jobs]
    add('sources-complete', 'sources-complete', dependencies=auth)
    for kind, reserve in [('components', 96*1048576), ('fragments', 54*1048576),
                          ('contacts', 8*1048576), ('residues', 1048576)]:
        inputs = [original[(p['commit'], p['path'])] for p in config['inputs']
                  if p['kind'] in (kind, kind + '_delta', 'reconstruction_code')]
        add(kind, 'ledger', inputs, ['sources-complete'], reserve, ledger=kind)
    add('candidates-complete', 'candidate-join', dependencies=['components', 'fragments', 'contacts', 'residues'])
    add('scope', 'scope', [source_pins[NUMERIC+'scope.json.gz']], ['sources-complete'], 64*1048576)
    routing_report = reader[ROUTING+'report.json']
    route_parts = sorted((name, pin) for name, pin in reader.items()
                         if name.startswith(ROUTING+'components-'))
    need(len(route_parts) == 25, 'Wrong complete25 routing source parts')
    routing = []
    for number, (name, pin) in enumerate(route_parts):
        stage = f'routing-{number:03}'
        add(stage, 'routing-part', [pin, source_pins[NUMERIC+'scope.json.gz']],
            ['scope'] + routing[-1:], 24*1048576, ordinal=number)
        routing.append(stage)
    add('routing-whole', 'routing-whole', [routing_report], routing, 1048576)
    add('routing-complete', 'routing-join', dependencies=['components', 'scope', 'routing-whole', *routing])
    diagnoses = sorted(p for p in source_pins if p.startswith(NUMERIC+'r1/diagnoses-'))
    need(len(diagnoses) == 32, 'Wrong complete32 original diagnosis bodies')
    diagnosis_jobs = []
    for number, name in enumerate(diagnoses):
        stage = f'diagnoses-{number:03}'
        add(stage, 'diagnosis-part', [source_pins[name]], ['routing-complete'], 2*1048576)
        diagnosis_jobs.append(stage)
    add('mismatches-complete', 'diagnosis-join', dependencies=[*diagnosis_jobs, *routing])
    original_products = {p['path']: p for p in physical_report['products']}
    physical_parts = sorted((name, pin) for name, pin in reader.items()
                            if name.startswith(PHYSICAL+'results/components-') and name.endswith('.jsonl.gz'))
    need(len(physical_parts) == 71 and len(original_products) == len(physical_report['products']),
         'Wrong complete71 original physical containing files')
    component_inputs = [original[(p['commit'], p['path'])] for p in config['inputs']
                        if p['kind'] in ('components', 'components_delta', 'reconstruction_code')]
    physical = []; queries = []
    for number, (name, pin) in enumerate(physical_parts):
        stage = f'physical-{number:03}'
        original_product = original_products[name.rsplit('/', 1)[-1]]
        adapter.bounds(original_product)
        add(stage, 'physical-part', [pin, *component_inputs], ['candidates-complete', 'mismatches-complete'],
            16*1048576, original_product=original_product)
        physical.append(stage)
    add('physical-complete', 'physical-join', dependencies=[*physical, 'components', *routing, 'mismatches-complete'])
    for number, stage in enumerate(physical):
        query_stage = f'queries-{number:03}'
        add(query_stage, 'query-part', dependencies=[stage, 'mismatches-complete', 'physical-complete'],
            reserve=4*1048576)
        queries.append(query_stage)
    add('queries-complete', 'query-join', dependencies=[*queries, *physical, 'mismatches-complete'])
    return {'version': 1, 'issue': 1394, 'scope': {'sources': 202, 'components': 95173,
            'selected': 26276, 'complement': 68897, 'mismatches': 1294, 'families': 494,
            'batches': 49, 'ordered_queries': 10419}, 'runtime_bytes': runtime_bytes,
            'jobs': jobs, 'physical_report': physical_report,
            'limits': ['Planning does not authenticate or execute these jobs.',
             'Every dynamic intermediate descriptor, completion receipt and inventory enters actual dispatch admission.',
             'Scratch products are real retained evidence; final inverse delivery must inventory their provenance.',
             'No numerical replay, native acquisition or flat publication is established by this plan.']}


def unique(pins):
    result = {}
    for pin in pins:
        key = (pin.get('commit'), pin['path'])
        need(key not in result or result[key] == pin, 'Conflicting complete consumed descriptor')
        result[key] = pin
    return list(result.values())


def receipt_pins(adapter, directory):
    """Read only the small receipt to discover its bounded immutable inventory pin."""
    path = adapter.ordinary(Path(directory)/'publication.json')
    with path.open('rb') as stream:
        raw = stream.read(adapter.RECEIPT+1)
    need(len(raw) <= adapter.RECEIPT, 'Oversized actual completion receipt')
    receipt = json.loads(raw)
    need(receipt.get('complete') is True and receipt.get('version') == 1, 'Incomplete actual predecessor job')
    publication = {'path': str(path), 'bytes': len(raw), 'sha256': adapter.sha(raw)}
    return publication, receipt['inventory']


def inventory_preview(adapter, pin):
    """Preview small descriptors only; Phase later consumes these SAME whole bytes."""
    path = adapter.ordinary(pin['path'])
    with path.open('rb') as stream:
        raw = stream.read(pin['bytes']+1)
    inventory = json.loads(adapter.decode(raw, pin))
    return inventory


def predecessor_operation(name):
    exact = {'sources-complete': 'complete-original-source-authentication-reconciliation',
             'candidates-complete': 'complete-candidate-bindings', 'scope': 'scope-index',
             'routing-whole': 'whole-routing-byte-verification',
             'routing-complete': 'complete-routing-candidate-join',
             'mismatches-complete': 'complete-original-mismatch-selector',
             'physical-complete': 'complete-original-physical-query-join',
             'queries-complete': 'complete-actual-native-query-join'}
    if name in exact:
        return exact[name]
    if name in ('components', 'fragments', 'contacts', 'residues'):
        return 'literal-ledger-reconstruction'
    prefixes = {'authenticate-': 'whole-source-authentication', 'routing-': 'routing-containing-part',
                'diagnoses-': 'diagnosis-containing-file', 'physical-': 'whole-original-physical-restoration',
                'queries-': 'actual-original-native-query-containing-file'}
    for prefix, operation in prefixes.items():
        if name.startswith(prefix) and len(name.removeprefix(prefix)) == 3 and name.removeprefix(prefix).isdigit():
            return operation
    raise ValueError('Foreign1394 predecessor job')


def dispatch(adapter, repo, destination, job, campaign, metadata, modules, *, runtime_bytes,
             runtime_verified, project_pins, plan_stage=None, before_finish=None):
    """One detached worker's complete lifecycle; returns its receipt only."""
    source_index, config, reader_index, physical_report = metadata
    sources, original = aliases(source_index)
    need(all(name in sources for name in job['source_paths']), 'Foreign undeclared1394 source request')
    pairs = {}; previews = {}
    for dependency in job['dependencies']:
        pairs[dependency] = receipt_pins(adapter, campaign/dependency)
        previews[dependency] = inventory_preview(adapter, pairs[dependency][1])
    def products(dependency, prefix):
        return [p for p in previews[dependency]['outputs'] if Path(p['path']).name.startswith(prefix)]
    selected_products = []
    operation = job['operation']
    if operation == 'candidate-join':
        for kind in ('components', 'fragments', 'contacts'):
            selected_products += products(kind, kind+'-')
    elif operation == 'routing-part' and job['arguments']['ordinal']:
        selected_products += products(job['dependencies'][-1], 'boundary.json')
    elif operation == 'routing-whole':
        for dependency in job['dependencies']:
            selected_products += products(dependency, 'whole-routing-part.bin')
    elif operation in ('routing-join', 'diagnosis-join', 'physical-join', 'query-join'):
        prefixes = {'routing-join': ('components-', 'scope-selected-', 'scope-complement-', 'routing-'),
                    'diagnosis-join': ('diagnosis-index-', 'routing-'),
                    'physical-join': ('physical-index-', 'components-', 'routing-', 'mismatch-index-'),
                    'query-join': ('native-query-index-', 'physical-index-', 'mismatch-index-')}[operation]
        for dependency in job['dependencies']:
            for prefix in prefixes:
                selected_products += products(dependency, prefix)
    elif operation == 'query-part':
        selected_products += products(job['dependencies'][0], 'whole-original-physical.jsonl.gz')
        selected_products += products('mismatches-complete', 'mismatch-index-')
    consumed = unique([*[sources[name] for name in job['source_paths']], *selected_products,
                       *[pin for pair in pairs.values() for pin in pair]])
    # Project/code metadata inputs can overlap explicitly selected source pins.
    source_keys = {adapter.Phase.key(p) for p in consumed}
    project = [p for p in project_pins if adapter.Phase.key(p) not in source_keys]
    phase = adapter.Phase(repo, destination, consumed, runtime_bytes=runtime_bytes,
                          output_reserve=job['output_reserve'], runtime_verified=runtime_verified,
                          project_pins=project)
    if before_finish is not None:
        finish = phase.finish
        def guarded_finish(facts):
            before_finish()
            return finish(facts)
        phase.finish = guarded_finish
    if plan_stage is not None:
        plan_inventory = adapter.completed_inventory(phase, *plan_stage)
        need(plan_inventory['facts']['operation'] == 'complete1394-detached-acquisition-plan',
             'Wrong actual complete plan stage')
    for dependency, pair in pairs.items():
        actual = adapter.completed_inventory(phase, *pair)
        need(actual == previews[dependency], 'Predecessor inventory changed before real consumption')
        need(actual['facts']['operation'] == predecessor_operation(dependency), 'Wrong actual predecessor operation')
        if dependency in ('components', 'fragments', 'contacts', 'residues'):
            need(actual['facts']['ledger'] == dependency, 'Wrong actual complete predecessor ledger')
        if dependency.startswith('routing-') and dependency not in ('routing-whole', 'routing-complete'):
            need(actual['facts']['part'] == int(dependency.removeprefix('routing-')),
                 'Wrong/reordered actual predecessor routing part')
        need(all(any(p == required for p in actual['input_descriptors']) for required in project_pins
                 if required.get('commit') and required['path'].startswith(OWNED)),
             'Predecessor executed project closure differs from this immutable freeze')
    def read_products(dependency, prefix):
        return products(dependency, prefix)
    args = job['arguments']
    config_pin = next(p for p in project_pins if p['path'] == OWNED+'methods/legacy/input-config.json')
    source_index_pin = next(p for p in project_pins if p['path'] == OWNED+'source-index.json')
    immutable = modules.get('immutable'); inputs = modules.get('inputs'); transport = modules.get('transport')
    if operation == 'authenticate':
        return adapter.authenticate(phase)
    if operation == 'sources-complete':
        return adapter.reconcile_sources(phase, source_index_pin, list(pairs.values()))
    if operation == 'ledger':
        return adapter.ledger(phase, args['ledger'], config, config_pin, original, inputs, immutable.canonical_json)
    if operation == 'candidate-join':
        return adapter.candidate_join(phase, *[read_products(k, k+'-') for k in ('components', 'fragments', 'contacts')])
    if operation == 'scope':
        return adapter.scope_index(phase, sources[job['source_paths'][0]])
    if operation == 'routing-part':
        previous = read_products(job['dependencies'][-1], 'boundary.json') if args['ordinal'] else []
        need(len(previous) == (1 if args['ordinal'] else 0), 'Missing/duplicate actual routing boundary')
        return adapter.routing_part(phase, sources[job['source_paths'][0]], sources[job['source_paths'][1]],
                                    ordinal=args['ordinal'], previous_pin=previous[0] if previous else None)
    if operation == 'routing-whole':
        return adapter.routing_whole(phase, selected_products, sources[job['source_paths'][0]])
    if operation == 'routing-join':
        routes = [p for d in job['dependencies'] if d.startswith('routing-') and d != 'routing-whole'
                  for p in read_products(d, 'routing-')]
        return adapter.routing_join(phase, read_products('components', 'components-'), routes,
                                    read_products('scope', 'scope-selected-'), read_products('scope', 'scope-complement-'))
    if operation == 'diagnosis-part':
        return adapter.diagnoses_part(phase, sources[job['source_paths'][0]])
    if operation == 'diagnosis-join':
        diagnoses = [p for d in job['dependencies'] if d.startswith('diagnoses-') for p in read_products(d, 'diagnosis-index-')]
        routes = [p for d in job['dependencies'] if d.startswith('routing-') for p in read_products(d, 'routing-')]
        return adapter.diagnosis_join(phase, diagnoses, routes)
    if operation == 'physical-part':
        return adapter.physical_part(phase, sources[job['source_paths'][0]], args['original_product'],
                                     config, config_pin, original, inputs, transport, immutable)
    if operation == 'physical-join':
        physical = [p for d in job['dependencies'] if d.startswith('physical-') for p in read_products(d, 'physical-index-')]
        routes = [p for d in job['dependencies'] if d.startswith('routing-') for p in read_products(d, 'routing-')]
        return adapter.physical_join(phase, physical, read_products('components', 'components-'), routes,
                                     read_products('mismatches-complete', 'mismatch-index-'))
    if operation == 'query-part':
        actual = read_products(job['dependencies'][0], 'whole-original-physical.jsonl.gz')
        need(len(actual) == 1, 'Missing/duplicate actual restored physical whole file')
        return adapter.query_part(phase, actual[0], read_products('mismatches-complete', 'mismatch-index-'), immutable.canonical_json)
    if operation == 'query-join':
        queries = [p for d in job['dependencies'] if d.startswith('queries-') for p in read_products(d, 'native-query-index-')]
        physical = [p for d in job['dependencies'] if d.startswith('physical-') for p in read_products(d, 'physical-index-')]
        return adapter.query_join(phase, queries, read_products('mismatches-complete', 'mismatch-index-'), physical)
    raise ValueError('Unknown explicit1394 acquisition operation')


def detached_command(python, driver, freeze, freeze_sha256, plan, campaign, job):
    """Root coordinator runs this command, waits, records receipt, then advances."""
    cache = Path(driver).resolve().parents[3]/'.cache/1394-never-materialized-bytecode'
    return [str(python), '-I', '-S', '-B', '-X', 'pycache_prefix='+str(cache), str(driver), '--freeze', str(freeze),
            '--freeze-sha256', freeze_sha256, '--plan', str(plan), '--campaign', str(campaign), '--job', job]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--freeze-sha256', required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--campaign', type=Path, required=True)
    parser.add_argument('--job', required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent; repo = here.parents[2]
    need(args.freeze.is_absolute() and args.freeze.resolve().is_relative_to(repo/'.cache') and
         not any(p.is_symlink() for p in (args.freeze, *args.freeze.parents)), 'Safe root-owned execution freeze required')
    with args.freeze.open('rb') as stream:
        freeze_raw = stream.read(1048577)
    need(len(freeze_raw) <= 1048576 and hashlib.sha256(freeze_raw).hexdigest() == args.freeze_sha256,
         'Root-issued complete freeze bytes differ')
    freeze = json.loads(freeze_raw)
    need(freeze.get('version') == 1 and freeze.get('issue') == 1394 and
         freeze.get('resource_admission', {}).get('execution_allowed') is True and
         args.job in freeze.get('admitted_jobs', []), 'Root has not admitted this exact acquisition job')
    commit = freeze['execution_commit']
    need(type(commit) is str and len(commit) == 40 and all(c in '0123456789abcdef' for c in commit),
         'Immutable root execution commit required')
    def code(name):
        raw = subprocess.check_output(['git', '-C', str(repo), 'show', commit+':'+OWNED+name])
        need(len(raw) <= 33554432 and (here/name).read_bytes() == raw,
             'Actual frozen driver/entry code changed: '+name)
        return raw
    own_raw = code('acquisition-driver.py')
    run_raw = code('run.py')
    entry = types.ModuleType('acquisition_frozen_entry'); entry.__file__ = str(here/'run.py')
    sys.modules[entry.__name__] = entry
    exec(compile(run_raw, entry.__file__, 'exec'), entry.__dict__)
    pins, baseline, shared, guard, loaded, runtime, runtime_pin, runtime_index = entry.frozen(commit)
    guard.all_callables(sys.modules[__name__], own_raw)
    installed_bytes = runtime['logical_runtime_raw_bytes']
    need(type(installed_bytes) is int and installed_bytes > 0, 'Actual installed runtime byte accounting missing')
    # Cold custody transport/logical intermediates have been discarded by prepare;
    # retain its complete final-flat source descriptors in the root freeze evidence.
    custody_paths = {p['path'] for p in runtime['whole_runtime_aliases']}
    project = [p for p in pins if p['path'] not in custody_paths]
    names = {'acquisition': OWNED+'acquisition-phases.py'}
    legacy = ()
    if args.job in ('components', 'fragments', 'contacts', 'residues'):
        legacy = ('inputs', 'immutable')
    elif args.job.startswith('physical-') and args.job != 'physical-complete':
        legacy = ('producer', 'comparison', 'inputs', 'immutable', 'ellipsoidal_area', 'transport')
    elif args.job.startswith('queries-') and args.job != 'queries-complete':
        legacy = ('immutable',)
    names.update({name: OWNED+'methods/legacy/'+name+'.py' for name in legacy})
    modules = baseline.load_modules(names)
    for name, module in modules.items():
        guard.all_callables(module, baseline.pinned_bytes(names[name]))
    adapter = modules['acquisition']
    def runtime_guard():
        loaded['runtime'].loaded(runtime_pin, runtime_index, repo=repo, owned=OWNED, project_pins=pins)
        for name, module in modules.items():
            guard.all_callables(module, baseline.pinned_bytes(names[name]))
    runtime_guard()
    campaign = adapter.ordinary(args.campaign)
    need(campaign.resolve().is_relative_to(repo/'.cache') and campaign.is_dir(), 'Existing owned campaign required')
    # Recheck normal allocation/storage admission immediately before job work.
    node = '/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
    subprocess.run([node, str(repo/'scripts/local-workspace.mjs'), 'check'], cwd=repo,
                   check=True, stdout=subprocess.DEVNULL)
    source_index = json.loads(baseline.materialized_bytes(OWNED+'source-index.json'))
    config = json.loads(baseline.materialized_bytes(OWNED+'methods/legacy/input-config.json'))
    reader_index = json.loads(baseline.materialized_bytes(OWNED+'methods/input-index.json'))
    source_pins, original = aliases(source_index)
    report_pin = next(source_pins[NUMERIC+p['path']] for p in reader_index['files']
                      if p.get('original_path') == PHYSICAL+'results/report.json')
    freeze_pin = {'path': str(args.freeze), 'bytes': len(freeze_raw), 'sha256': args.freeze_sha256}
    if args.job == 'plan':
        phase = adapter.Phase(repo, campaign/'plan', [report_pin, freeze_pin], runtime_bytes=installed_bytes,
                              output_reserve=1048576, runtime_verified=True, project_pins=project)
        physical_report = json.loads(phase.read(report_pin))
        phase.read(freeze_pin)
        metadata = (source_index, config, reader_index, physical_report)
        plan = build_plan(adapter, *metadata, runtime_bytes=installed_bytes, project_pins=project)
        phase.output('acquisition-plan.json.gz', adapter.canonical(plan), compress=True)
        runtime_guard()
        receipt = phase.finish({'operation': 'complete1394-detached-acquisition-plan', 'jobs': len(plan['jobs']),
                                'final_flat_runtime_custody': runtime['whole_runtime_aliases']})
    else:
        plan_pin = freeze['plan_pin']
        need(str(args.plan) == plan_pin['path'], 'Wrong root-admitted actual plan path')
        plan = inventory_preview(adapter, plan_pin)
        # This small original report is a complete captured plan product. It is
        # charged through the actual whole plan input, not reread covertly in
        # each source authentication job.
        physical_report = plan['physical_report']
        metadata = (source_index, config, reader_index, physical_report)
        expected = build_plan(adapter, *metadata, runtime_bytes=installed_bytes, project_pins=project)
        need(plan == expected, 'Actual detached plan disagrees with frozen complete source/config closure')
        matches = [j for j in plan['jobs'] if j['id'] == args.job]
        need(len(matches) == 1, 'Missing/duplicate root-admitted acquisition job')
        job = matches[0]
        # Planning inputs and metadata source are consumed in each real worker,
        # even when this operation otherwise needs only scratch index products.
        plan_stage = (freeze['plan_publication_pin'], freeze['plan_inventory_pin'])
        dispatch_project = unique([*project, freeze_pin, plan_pin, *plan_stage])
        receipt = dispatch(adapter, repo, campaign/job['id'], job, campaign, metadata, modules,
                           runtime_bytes=installed_bytes, runtime_verified=True, project_pins=dispatch_project,
                           plan_stage=plan_stage, before_finish=runtime_guard)
    loaded['runtime'].loaded(runtime_pin, runtime_index, repo=repo, owned=OWNED, project_pins=pins)
    print(json.dumps({'job': args.job, 'receipt': receipt, 'execution_commit': commit}))


if __name__ == '__main__':
    main()
