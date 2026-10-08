"""Root-admitted cold numerical/native worker; no launch or global state API.

The root freezes this file and run.py together with all literal/adaptor bodies.
A <=1MiB whole root request supplies exact independent dependency descriptors,
prior authority rosters, resource budget and fresh owned destination. Admission
precedes source reads and scientific module execution. Each numerical consumer
runs inside the original full-native authentication callback; complete original
coordinates, query order and unknown branches are retained. This worker never
calls source.load/Sources, changes science, or carries geometry across jobs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import types

OWNED = 'coordination/engineering/complete-replay-operand-restoration-20261007/'
METADATA_OPERATIONS = ('cohort-index-projection', 'cohort-selector-plan', 'cohort-selector-materialization', 'cohort-selectors-materialization')
OPERATIONS = ('native-metadata', 'source-cohort', 'numerical-cohort', *METADATA_OPERATIONS)
ROOT_LIMIT = 1048576
NODE = '/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'


def need(condition, message):
    if not condition:
        raise ValueError(message)


def unique(pins, acquisition):
    result = {}
    for pin in pins:
        acquisition.bounds(pin)
        key = acquisition.Phase.key(pin)
        need(key not in result or result[key] == pin, 'Conflicting complete numerical dependency')
        result[key] = pin
    return list(result.values())


def exact_roster(actual, expected, acquisition):
    def table(pins):
        rows = {}
        for pin in pins:
            acquisition.bounds(pin); key = acquisition.Phase.key(pin)
            need(key not in rows, 'Duplicate exact independent phase descriptor')
            rows[key] = pin
        return rows
    need(table(actual) == table(expected), 'Independent complete numerical dependency roster differs')


def authority_inputs(arguments):
    """Selector and global-query authority are actual consumed whole products."""
    return [arguments['selector_pin'], *arguments['selector_pair'],
            *arguments['query_join_pair'], *arguments['query_pins'],
            *arguments['mismatch_pair'], *arguments['mismatch_pins'],
            arguments['candidate_table_pin'], arguments['cohort_context']['request_pin'],
            arguments['cohort_context']['freeze_pin']]


def dependency_inputs(operation, arguments, acquisition):
    need(operation in OPERATIONS and type(arguments) is dict, 'Unknown numerical operation')
    if operation == 'cohort-index-projection':
        return projection_dependency_inputs(arguments, acquisition)
    if operation == 'cohort-selector-plan':
        return unique([arguments['predecessor_authorities_pin'],
                       *[p for values in arguments['projected_pins'].values() for p in values],
                       *[p for pair in arguments['projection_pairs'].values() for p in pair],
                       *arguments['mismatch_pins'], *arguments['mismatch_pair'],
                       *arguments['component_ledger_pair'], arguments['candidate_table_pin'],
                       *[p for pair in arguments['physical_stage_pairs'] for p in pair],
                       *arguments['physical_join_pair'], *arguments['query_join_pair'],
                       *arguments['query_pins']], acquisition)
    if operation == 'cohort-selector-materialization':
        return unique([arguments['predecessor_authorities_pin'], arguments['shard_pin'],
                       *arguments['selector_plan_pair']], acquisition)
    if operation == 'cohort-selectors-materialization':
        return unique([arguments['predecessor_authorities_pin'], *arguments['shard_pins'],
                       *arguments['selector_plan_pair']], acquisition)
    if operation == 'source-cohort':
        return unique([arguments['selector_pin'], *arguments['selector_pair'],
                       *arguments['source_inputs']], acquisition)
    native = [arguments['member_index_pin'], *arguments['part_pins'], arguments['original_reader_pin']]
    need(len(arguments['part_pins']) == 3, 'Whole original three-part native dependency required')
    if operation == 'native-metadata':
        return unique([*native, *arguments['query_join_pair'], *arguments['query_pins'],
                       *arguments['mismatch_pair'], *arguments['mismatch_pins']], acquisition)
    return unique([*native, *authority_inputs(arguments), *arguments['cohort_pair'],
                   *arguments['cohort_pins']], acquisition)


def projection_dependency_inputs(arguments, acquisition):
    # Descriptor-only equivalent of the frozen planner's projection_dependencies;
    # importing or previewing predecessor bodies before Phase is forbidden.
    return unique([arguments['predecessor_authorities_pin'],
                   *arguments['index_pins'], *arguments['mismatch_pins'],
                   *arguments['mismatch_pair'], *arguments['physical_join_pair'],
                   *[p for pair in arguments['index_stage_pairs'] for p in pair]], acquisition)


def read_root(path, digest, repo):
    need(type(digest) is str and re.fullmatch('[a-f0-9]{64}', digest) is not None,
         'Exact whole root metadata hash required')
    need(path.is_absolute() and '..' not in path.parts and path.resolve().is_relative_to(repo/'.cache') and
         not any(p.is_symlink() for p in (path, *path.parents)), 'Owned ordinary root metadata required')
    with path.open('rb') as stream:
        raw = stream.read(ROOT_LIMIT+1)
    need(len(raw) <= ROOT_LIMIT and hashlib.sha256(raw).hexdigest() == digest, 'Root whole metadata differs')
    return raw, dict(path=str(path), bytes=len(raw), sha256=digest)


def request_admission(freeze, request, request_pin, repo, *, check_fresh=True):
    need(freeze.get('version') == 1 and freeze.get('issue') == 1394 and
         freeze.get('resource_admission', {}).get('execution_allowed') is True and
         request_pin in freeze.get('admitted_numerical_requests', []),
         'Root has not admitted this exact numerical request')
    need(request.get('version') == 1 and request.get('issue') == 1394 and
         request.get('operation') in OPERATIONS, 'Wrong root numerical request')
    commit = freeze.get('execution_commit')
    need(type(commit) is str and re.fullmatch('[a-f0-9]{40}', commit) is not None and
         request.get('execution_commit') == commit, 'Immutable request/freeze commit differs')
    need(type(request.get('output_reserve')) is int and request['output_reserve'] >= 0 and
         type(request.get('expected_runtime_bytes')) is int and request['expected_runtime_bytes'] > 0 and
         type(request.get('expected_complete_phase_bytes')) is int and
         0 < request['expected_complete_phase_bytes'] <= 268435456,
         'Missing explicit complete resource admission')
    destination = Path(request['destination'])
    need(destination.is_absolute() and '..' not in destination.parts and
         destination.resolve().is_relative_to(repo/'.cache') and destination.parent.is_dir() and
         (not check_fresh or not destination.exists()) and not any(p.is_symlink() for p in (destination,*destination.parents)),
         'Fresh exclusive actual owned numerical destination required')
    need(type(request.get('expected_dependency_inputs')) is list,
         'Independent complete dependency expectation required')
    return commit, destination


def completed_authority(phase, pair, operation, expected_inputs, expected_runtime_bytes, acquisition):
    need(type(pair) is list and len(pair) == 2, 'Whole prior publication/inventory pair required')
    inventory = acquisition.completed_inventory(phase, *pair)
    need(inventory['facts'].get('operation') == operation, 'Wrong prior numerical authority operation')
    exact_roster(inventory['input_descriptors'], expected_inputs, acquisition)
    need(type(expected_runtime_bytes) is int and expected_runtime_bytes > 0 and
         inventory['runtime_bytes'] == expected_runtime_bytes, 'Prior executed runtime lineage differs')
    return inventory


def exact_products(inventory, supplied, prefix, acquisition):
    expected = [p for p in inventory['outputs'] if Path(p['path']).name.startswith(prefix)]
    exact_roster(supplied, expected, acquisition)
    need(expected, 'Missing whole authority products')


def global_queries(phase, arguments, acquisition):
    query = completed_authority(phase, arguments['query_join_pair'],
            'complete-actual-native-query-join', arguments['query_join_expected_inputs'],
            arguments['query_join_expected_runtime_bytes'], acquisition)
    facts = query['facts']
    need(facts.get('components') == 1294 and facts.get('ordered_queries') == 10419,
         'Complete original1294/10419 query authority required')
    mismatch = completed_authority(phase, arguments['mismatch_pair'],
            'complete-original-mismatch-selector', arguments['mismatch_expected_inputs'],
            arguments['mismatch_expected_runtime_bytes'], acquisition)
    mf = mismatch['facts']
    need(mf.get('mismatches') == 1294 and mf.get('families') == 494 and mf.get('batches') == 49,
         'Complete original mismatch/family/batch authority required')
    exact_products(mismatch, arguments['mismatch_pins'], 'mismatch-index-', acquisition)
    qinputs = [p for p in query['input_descriptors'] if Path(p['path']).name.startswith('native-query-index-')]
    exact_roster(arguments['query_pins'], qinputs, acquisition)
    # Native acquire independently reads and validates all actual query rows.
    # Numerical workers reconcile these same full rows with their saved cohort.
    mismatches = {}
    for pin in arguments['mismatch_pins']:
        for line in phase.read(pin).splitlines():
            row = json.loads(line); identity = row['id']
            need(type(identity) is str and identity not in mismatches, 'Duplicate complete mismatch authority')
            mismatches[identity] = row
    need(len(mismatches) == 1294 and len({r['family'] for r in mismatches.values()}) == 494 and
         len({r['operational_batch'] for r in mismatches.values()}) == 49 and
         all(r['status'] == 'original-replay-mismatch' for r in mismatches.values()),
         'Omitted mismatch/family/batch including zero-query member')
    queries = {identity: [] for identity in mismatches}
    for pin in arguments['query_pins']:
        for line in phase.read(pin).splitlines():
            row = json.loads(line); identity = row['component_id']
            need(identity in queries and type(row['query_ordinal']) is int and
                 row['query_ordinal'] == len(queries[identity]), 'Foreign/duplicate/unordered original query authority')
            fields = {'source_id','source_level','source_container','source_record_sha256',
                      'source_pointset_sha256','periodic_offset'}
            need(type(row['query']) is dict and set(row['query']) == fields and
                 re.fullmatch('[a-f0-9]{64}',row.get('original_query_sha256','')) is not None and
                 type(row.get('physical_row_ordinal')) is int and row['physical_row_ordinal'] >= 0,
                 'Whole original native query provenance differs')
            # The stored digest binds the COMPLETE original query, including
            # unknowns/witness context, not merely the six-field native subset.
            queries[identity].append(row)
    need(sum(len(rows) for rows in queries.values()) == 10419,
         'Omitted complete original ordered query authority')
    return mismatches, queries


def selector_authority(phase, arguments, acquisition):
    operation = arguments.get('selector_operation','complete-original-cohort-selector-materialization')
    need(operation in ('complete-original-cohort-selector-materialization',
                       'complete-original-all-cohort-selector-materialization'), 'Unknown selector custody operation')
    inventory = completed_authority(phase, arguments['selector_pair'],operation,
            arguments['selector_expected_inputs'],arguments['selector_expected_runtime_bytes'],acquisition)
    raw = phase.read(arguments['selector_pin']); selected = json.loads(raw)
    if operation == 'complete-original-all-cohort-selector-materialization':
        facts = inventory['facts']; number = selected['cohort_ordinal']
        need(facts['components']==1294 and facts['families']==494 and facts['batches']==49 and
             facts['ordered_queries']==10419 and len(inventory['outputs'])==facts['cohorts']==len(facts['selectors']) and
             type(number) is int and 0<=number<len(facts['selectors']), 'Incomplete all-selector authority')
        need(inventory['outputs'][number]==arguments['selector_pin'] and
             Path(arguments['selector_pin']['path']).name==f'selector-{number:03}.json', 'Foreign full selector output')
        binding = facts['selectors'][number]
    else:
        need(inventory['outputs']==[arguments['selector_pin']], 'Changed whole materialized selector product')
        binding = inventory['facts']
    need(selected.get('kind') == 'complete-original-numerical-cohort-selector' and
         acquisition.sha(raw) == binding['whole_selector_sha256'] and
         selected['cohort_ordinal'] == binding['cohort_ordinal'] and
         selected['components'] == binding['components'] and
         selected['ordered_queries'] == binding['ordered_queries'],
         'Changed complete independently materialized selector')
    ids = [row['id'] for row in selected['rows']]
    need(ids and ids == sorted(set(ids)) and len(ids) == selected['components'],
         'Duplicate/unordered materialized cohort members')
    return selected


def saved_cohort_authority(phase, arguments, project_pins, execution_commit, acquisition):
    selected = selector_authority(phase, arguments, acquisition)
    mismatch, queries = global_queries(phase, arguments, acquisition)
    need(arguments['mismatch_pair'] == [selected['mismatch_join']['publication'],selected['mismatch_join']['inventory']] and
         arguments['mismatch_pins'] == selected['mismatch_index_pins'], 'Selector has another global mismatch authority')
    table_pins = {acquisition.Phase.key(r['candidate_containing_table']):r['candidate_containing_table']
                  for r in selected['rows']}
    need(len(table_pins) == 1 and next(iter(table_pins.values())) == arguments['candidate_table_pin'],
         'Foreign selected complete candidate containing table')
    table = json.loads(phase.read(arguments['candidate_table_pin']))
    source_inputs = []
    source_inputs += [arguments['selector_pin'], selected['campaign_join']['publication'],
                     selected['campaign_join']['inventory'], selected['mismatch_join']['publication'],
                     selected['mismatch_join']['inventory'], *selected['mismatch_index_pins']]
    for item in selected['rows']:
        index = item['candidate_alias']['input_index']
        need(type(index) is int and 0 <= index < len(table), 'Foreign candidate table ordinal')
        source_inputs += [item['candidate_containing_table'],table[index],item['physical_containing_pin'],
                          item['diagnosis_index']['input']]
    source_inputs = unique(source_inputs,acquisition)
    context = arguments['cohort_context']
    need(context['request_pin']['bytes'] <= ROOT_LIMIT and context['freeze_pin']['bytes'] <= ROOT_LIMIT,
         'Bounded whole prior execution metadata required')
    prior_request = json.loads(phase.read(context['request_pin']))
    prior_freeze = json.loads(phase.read(context['freeze_pin']))
    prior_commit, prior_destination = request_admission(prior_freeze,prior_request,context['request_pin'],
                                                       phase.repo,check_fresh=False)
    need(prior_commit == execution_commit and prior_request['operation'] == 'source-cohort' and
         prior_request['arguments']['selector_pin'] == arguments['selector_pin'] and
         prior_request['arguments']['selector_pair'] == arguments['selector_pair'] and
         arguments['cohort_pair'][0]['path'] == str(prior_destination/'publication.json') and
         arguments['cohort_pair'][1]['path'] == str(prior_destination/'stage-inventory.json.gz'),
         'Saved operand authority has another frozen source extraction context')
    exact_roster(prior_request['arguments']['source_inputs'],source_inputs,acquisition)
    derived_dependencies = unique([arguments['selector_pin'],*arguments['selector_pair'],*source_inputs],acquisition)
    exact_roster(prior_request['expected_dependency_inputs'],derived_dependencies,acquisition)
    derived = unique([*derived_dependencies,context['request_pin'],context['freeze_pin'],*project_pins],acquisition)
    exact_roster(arguments['cohort_expected_inputs'],derived,acquisition)
    need(prior_request['expected_runtime_bytes'] == arguments['cohort_expected_runtime_bytes'] == phase.runtime_bytes and
         sum(acquisition.cost(p) for p in derived) + prior_request['expected_runtime_bytes'] +
         prior_request['output_reserve'] + acquisition.RECEIPT == prior_request['expected_complete_phase_bytes'],
         'Prior saved operand complete resource request differs')
    inventory = completed_authority(phase, arguments['cohort_pair'],
            'complete-original-numerical-cohort-acquisition', derived,
            arguments['cohort_expected_runtime_bytes'], acquisition)
    exact_products(inventory, arguments['cohort_pins'], 'complete-cohort-operands-', acquisition)
    facts = inventory['facts']; ids = [r['id'] for r in selected['rows']]
    need(all(i in mismatch for i in ids) and facts['component_ids'] == ids and
         facts['ordered_queries'] == selected['ordered_queries'] and
         facts['wanted_native_ids'] == selected['wanted_native_ids'] and
         facts['campaign_join_sha256'] == selected['campaign_join_sha256'],
         'Saved whole operand cohort differs from independent selector')
    selected_rows = {row['id']:row for row in selected['rows']}
    seen = []; actual_query_count = 0
    for pin in arguments['cohort_pins']:
        for line in phase.read(pin).splitlines():
            row = json.loads(line); identity = row['id']
            need(identity in ids and identity not in seen and (not seen or identity > seen[-1]),
                 'Duplicate/foreign/unordered saved original operand')
            seen.append(identity); original = row['physical']['query_relations']
            item = selected_rows[identity]; routing = item['routing']['row']
            need(acquisition.sha(acquisition.canonical(row['candidate'])) == item['candidate_alias']['whole_object_sha256'] ==
                 routing['current_feature_sha256'] and
                 len(acquisition.canonical(row['candidate'])) == item['candidate_alias']['whole_object_bytes'] and
                 acquisition.sha(acquisition.canonical(row['candidate']['geometry'])) == routing['current_geometry_sha256'] and
                 acquisition.sha(acquisition.canonical(row['physical'])) == item['physical_index']['restored_whole_row_sha256'] and
                 acquisition.sha(acquisition.canonical(row['diagnosis'])) == item['diagnosis_index']['whole_row_sha256'] and
                 row['routing'] == routing, 'Saved whole candidate/physical/diagnosis source bytes differ')
            expected_alias = dict(path=item['packed_containing_path'],original_path=item['physical_index']['original_path'],
                                  row_ordinal=item['physical_index']['row_ordinal'],
                                  whole_delivered_packed_row_sha256=item['physical_index']['packed_whole_row_sha256'],
                                  packed_row_hash_domain='complete-delivered-packed-canonical-row',
                                  restored_whole_row_sha256=item['physical_index']['restored_whole_row_sha256'],
                                  restored_row_hash_domain='original104-scientific-row-with-current-context-fields-restored',
                                  complete_current_feature_sha256=routing['current_feature_sha256'])
            need(row['physical_alias'] == expected_alias, 'Saved complete original physical inverse alias differs')
            binding = [{k:q[k] for k in ('source_id','source_level','source_container',
                       'source_record_sha256','source_pointset_sha256','periodic_offset')} for q in original]
            expected_queries = queries[identity]
            need(binding == [value['query'] for value in expected_queries] and
                 [acquisition.sha(acquisition.canonical(q)) for q in original] ==
                 [value['original_query_sha256'] for value in expected_queries] and
                 all(value['physical_row_ordinal'] == item['physical_index']['row_ordinal']
                     for value in expected_queries),
                 'Saved operand omits/reorders complete original queries or their six-field native bindings')
            need(row['candidate']['id'] == row['physical']['component_id'] == row['diagnosis']['component_id'] == identity and
                 row['diagnosis']['status'] == 'original-replay-mismatch', 'Wrong saved whole original identities')
            actual_query_count += len(original)
    need(seen == ids and actual_query_count == selected['ordered_queries'],
         'Saved original operands omit zero-query subjects or ordered queries')
    del mismatch, queries
    return selected


def source_authority(phase, arguments, modules, acquisition):
    selected = selector_authority(phase, arguments, acquisition)
    tables = {acquisition.Phase.key(row['candidate_containing_table']):row['candidate_containing_table']
              for row in selected['rows']}
    need(len(tables) == 1, 'Ambiguous full candidate containing table')
    table = json.loads(phase.read(next(iter(tables.values()))))
    derived = modules['planner'].next_inputs(selected, arguments['selector_pin'], table,
                                             project_pins=[], acquisition=acquisition)
    exact_roster(arguments['source_inputs'], derived, acquisition)
    # Complete mismatch custody in selectors is consumed even though extraction
    # only needs its actual selected original rows and full containing bodies.
    mismatch_pair = [selected['mismatch_join']['publication'], selected['mismatch_join']['inventory']]
    mismatch = acquisition.completed_inventory(phase, *mismatch_pair)
    need(mismatch['facts'].get('operation') == 'complete-original-mismatch-selector' and
         mismatch['facts'].get('mismatches') == 1294, 'Missing complete selector mismatch authority')
    exact_products(mismatch, selected['mismatch_index_pins'], 'mismatch-index-', acquisition)
    members = set()
    for pin in selected['mismatch_index_pins']:
        for line in phase.read(pin).splitlines():
            row = json.loads(line); need(row['id'] not in members, 'Duplicate mismatch member')
            members.add(row['id'])
    need(len(members) == 1294 and all(row['id'] in members for row in selected['rows']),
         'Foreign selected original mismatch')
    return selected


def metadata_pairs(operation, arguments):
    if operation == 'cohort-index-projection':
        return [*arguments['index_stage_pairs'],arguments['mismatch_pair'],arguments['physical_join_pair']]
    if operation == 'cohort-selector-plan':
        return [*arguments['projection_pairs'].values(),arguments['mismatch_pair'],
                arguments['component_ledger_pair'],*arguments['physical_stage_pairs'],
                arguments['physical_join_pair'],arguments['query_join_pair']]
    need(operation in ('cohort-selector-materialization','cohort-selectors-materialization'), 'Unknown metadata authority operation')
    return [arguments['selector_plan_pair']]


def scientific_names():
    names = {'reader': OWNED+'methods/reader-acquisition.py', 'kernel': OWNED+'methods/kernel.py',
             'exact_predicates': OWNED+'methods/exact_predicates.py', 'trace': OWNED+'methods/trace.py',
             'native_reader': OWNED+'methods/native_reader.py'}
    names.update({name:OWNED+'methods/legacy/'+name+'.py' for name in
                  ('producer','comparison','inputs','immutable','ellipsoidal_area','transport')})
    return names


def execute(phase, request, modules, loaded, *, guard, baseline, runtime_guard, project_pins):
    """Actual admitted dispatch; scientific producer objects stay in callback."""
    acquisition = modules['acquisition']; arguments = request['arguments']; operation = request['operation']
    runtime_guard()
    if operation in METADATA_OPERATIONS:
        # Root expectations are committed in the independently admitted request.
        # Every predecessor is a whole actually consumed publication/inventory.
        authorities = json.loads(phase.read(arguments['predecessor_authorities_pin']))
        need(type(authorities) is list and authorities, 'Independent metadata predecessor authority required')
        declared_pairs = metadata_pairs(operation, arguments)
        expected_pairs = {tuple((p.get('commit'),p['path']) for p in pair)
                          for pair in declared_pairs}
        need(len(expected_pairs) == len(declared_pairs), 'Duplicate declared metadata predecessor pair')
        actual_pairs = set()
        for authority in authorities:
            pair = authority['pair']; key = tuple((p.get('commit'),p['path']) for p in pair)
            need(key not in actual_pairs, 'Duplicate metadata predecessor authority')
            actual_pairs.add(key)
            completed_authority(phase,pair,authority['operation'],authority['expected_inputs'],
                                authority['runtime_bytes'],acquisition)
        need(actual_pairs == expected_pairs, 'Missing/foreign metadata predecessor authority')
        planner = modules['planner']
        if operation == 'cohort-index-projection':
            result = planner.prepare_index(phase,arguments['kind'],arguments['index_pins'],
                    arguments['mismatch_pins'],index_stage_pairs=arguments['index_stage_pairs'],
                    mismatch_pair=arguments['mismatch_pair'],physical_join_pair=arguments['physical_join_pair'],
                    acquisition=acquisition)
        elif operation == 'cohort-selector-plan':
            keys = ('projected_pins','projection_pairs','mismatch_pins','mismatch_pair',
                    'component_ledger_pair','candidate_table_pin','physical_stage_pairs',
                    'physical_join_pair','query_join_pair','query_pins')
            result = planner.selectors(phase,**{k:arguments[k] for k in keys},
                    acquisition=acquisition,project_pins=project_pins,
                    runtime_bytes=request['expected_runtime_bytes'],
                    acquisition_output_reserve=arguments['acquisition_output_reserve'])
        elif operation == 'cohort-selectors-materialization':
            result = planner.materialize_all_selectors(phase,arguments['shard_pins'],
                    arguments['selector_plan_pair'],acquisition)
        else:
            result = planner.materialize_selector(phase,arguments['shard_pin'],arguments['ordinal'],
                    arguments['expected_sha256'],arguments['selector_plan_pair'],acquisition)
        runtime_guard()
        return result
    if operation == 'source-cohort':
        source_authority(phase, arguments, modules, acquisition)
        return modules['cohort'].extract(phase, arguments['selector_pin'], acquisition=acquisition,
                                        canonical_json=loaded['source'].canonical)
    if operation == 'native-metadata':
        global_queries(phase, arguments, acquisition)
        return modules['native'].acquire(phase,
                member_index_pin=arguments['member_index_pin'], part_pins=arguments['part_pins'],
                original_reader_pin=arguments['original_reader_pin'], query_pins=arguments['query_pins'],
                mismatch_pins=arguments['mismatch_pins'],
                query_join_publication_pin=arguments['query_join_pair'][0],
                query_join_inventory_pin=arguments['query_join_pair'][1], acquisition=acquisition,
                native_reader=modules['native_reader'], comparison=modules['comparison'],
                query_bind=loaded['source'].query_bind, project_guard=runtime_guard,
                scratch_parent=phase.destination.parent)
    saved_cohort_authority(phase, arguments, project_pins, request['execution_commit'], acquisition)
    result = []
    def consumer(actual_phase, operands, records, aliases, native_proof):
        need(actual_phase is phase and not result, 'Changed/duplicate actual native consumer')
        facts = modules['numerical'].replay(phase, operands, records, aliases, native_proof,
                acquisition=acquisition, literal_products=loaded['products'], objects_module=loaded['objects'],
                replay_module=loaded['replay'], scientific_modules=modules,
                query_bind=loaded['source'].query_bind, project_guard=runtime_guard)
        result.append(facts)
    native = modules['native'].consume_cohort(phase,
                member_index_pin=arguments['member_index_pin'], part_pins=arguments['part_pins'],
                original_reader_pin=arguments['original_reader_pin'], cohort_pins=arguments['cohort_pins'],
                cohort_publication_pin=arguments['cohort_pair'][0], cohort_inventory_pin=arguments['cohort_pair'][1],
                acquisition=acquisition, native_reader=modules['native_reader'], comparison=modules['comparison'],
                query_bind=loaded['source'].query_bind, project_guard=runtime_guard,
                scratch_parent=phase.destination.parent, consumer=consumer)
    need(len(result) == 1 and native['component_ids'] == result[0]['component_ids'] and
         native['ordered_queries'] == result[0]['original_ordered_queries'], 'Incomplete actual native numerical callback')
    runtime_guard()
    facts = dict(result[0], actual_native_consumption=native,
                 execution_commit=request['execution_commit'])
    return modules['numerical'].complete(phase, facts, acquisition)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', required=True, type=Path); parser.add_argument('--freeze-sha256', required=True)
    parser.add_argument('--request', required=True, type=Path); parser.add_argument('--request-sha256', required=True)
    args = parser.parse_args(); here = Path(__file__).resolve().parent; repo = here.parents[2]
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
         'Use actual cold -I -S -B numerical entry')
    cache = repo/'.cache/1394-never-materialized-bytecode'
    need(sys.pycache_prefix == str(cache) and not cache.exists() and not cache.is_symlink(),
         'Use the fixed absent numerical pycache prefix')
    freeze_raw, freeze_pin = read_root(args.freeze, args.freeze_sha256, repo)
    request_raw, request_pin = read_root(args.request, args.request_sha256, repo)
    freeze, request = json.loads(freeze_raw), json.loads(request_raw)
    commit, destination = request_admission(freeze, request, request_pin, repo)
    # Only exact whole immutable/materialized code can bootstrap the root entry.
    need(subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip() == commit,
         'Actual numerical checkout is not frozen HEAD')
    def whole_code(name):
        row = subprocess.check_output(['git','-C',str(repo),'ls-tree','-z',commit,'--',OWNED+name]).decode().rstrip('\0')
        need('\t' in row, 'Missing ordinary frozen numerical entry')
        metadata, path = row.split('\t'); mode, kind, blob = metadata.split()
        need(path == OWNED+name and mode in ('100644','100755') and kind == 'blob', 'Nonordinary numerical code')
        n = int(subprocess.check_output(['git','-C',str(repo),'cat-file','-s',blob]))
        need(0 <= n <= 33554432, 'Frozen numerical code bound')
        raw = subprocess.check_output(['git','-C',str(repo),'cat-file','blob',blob])
        need(not any(p.is_symlink() for p in (here/name,*(here/name).parents)), 'Symlink numerical entry')
        with (here/name).open('rb') as stream:actual = stream.read(n+1)
        need(actual == raw, 'Actual whole frozen numerical code differs')
        return raw
    own_raw = whole_code('numerical-driver.py'); run_raw = whole_code('run.py')
    entry = types.ModuleType('numerical_frozen_entry'); entry.__file__ = str(here/'run.py')
    sys.modules[entry.__name__] = entry
    exec(compile(run_raw, entry.__file__, 'exec'), entry.__dict__)
    pins, baseline, shared, guard, loaded, runtime, runtime_pin, runtime_index = entry.frozen(commit)
    need(baseline.pinned_bytes(OWNED+'numerical-driver.py') == own_raw, 'Numerical driver absent/changed in full frozen roster')
    guard.all_callables(sys.modules[__name__], own_raw)
    installed = runtime['logical_runtime_raw_bytes']
    need(installed == request['expected_runtime_bytes'], 'Current actual runtime differs from root admission')
    custody = {p['path'] for p in runtime['whole_runtime_aliases']}
    project = [p for p in pins if p['path'] not in custody]
    # Normal allocator/storage check remains mandatory; its actual script is also
    # an admitted immutable whole code input rather than an unpinned shell helper.
    resource_path = 'scripts/local-workspace.mjs'
    resource_raw = subprocess.check_output(['git','-C',str(repo),'show',commit+':'+resource_path])
    need(len(resource_raw) <= 33554432 and (repo/resource_path).read_bytes() == resource_raw,
         'Actual allocator/storage code differs')
    resource_pin = dict(commit=commit,path=resource_path,bytes=len(resource_raw),
                        sha256=hashlib.sha256(resource_raw).hexdigest(),hash_kind='file-bytes')
    subprocess.run([NODE,str(repo/resource_path),'check'],cwd=repo,check=True,stdout=subprocess.DEVNULL)
    names = {'acquisition':OWNED+'acquisition-phases.py'}
    modules = baseline.load_modules(names); acquisition = modules['acquisition']
    dependencies = dependency_inputs(request['operation'],request['arguments'],acquisition)
    exact_roster(dependencies,request['expected_dependency_inputs'],acquisition)
    whole = unique([*dependencies,freeze_pin,request_pin,*project,resource_pin],acquisition)
    prospective = sum(acquisition.cost(p) for p in whole)+installed+request['output_reserve']+acquisition.RECEIPT
    need(prospective == request['expected_complete_phase_bytes'], 'Exact complete numerical phase admission differs')
    project = unique([*project,resource_pin],acquisition); project_keys={acquisition.Phase.key(p) for p in project}
    inputs = [p for p in whole if acquisition.Phase.key(p) not in project_keys]
    phase = acquisition.Phase(repo,destination,inputs,runtime_bytes=installed,runtime_verified=True,
                              project_pins=project,output_reserve=request['output_reserve'])
    phase.read(freeze_pin);phase.read(request_pin)
    remaining = {'native':OWNED+'native-acquisition.py','numerical':OWNED+'numerical-cohort.py',
                 'cohort':OWNED+'cohort-acquisition.py','planner':OWNED+'cohort-planning.py',
                 'driver':OWNED+'acquisition-driver.py',**scientific_names()}
    names.update(remaining)
    # Keep the exact acquisition module/class that constructed this real Phase;
    # loading a second identical class would leave the actual instance unguarded.
    modules.update(baseline.load_modules(remaining))
    scientific = {k:modules[k] for k in scientific_names()}
    # query_bind is the named acquisition hook in the literal reader; no declared
    # reader/scientific method is replaced, and every use gets an identity guard.
    need('query_bind' not in vars(modules['reader']), 'Unexpected declared scientific query hook')
    modules['reader'].query_bind = loaded['source'].query_bind
    bindings = loaded['runtime'].scientific_bindings(scientific)
    expected_finish = [phase.finish]
    def runtime_guard():
        need(type(phase) is modules['acquisition'].Phase and
             phase.read.__func__ is modules['acquisition'].Phase.read and
             phase.output.__func__ is modules['acquisition'].Phase.output and
             phase.rows.__func__ is modules['acquisition'].Phase.rows and
             phase.finish == expected_finish[0],
             'Actual consumed Phase class/callable binding differs')
        guard.all_callables(sys.modules[__name__],own_raw)
        for name,module in modules.items():guard.all_callables(module,baseline.pinned_bytes(names[name]))
        for name,module in loaded.items():guard.all_callables(module,baseline.pinned_bytes(OWNED+name+'.py'))
        guard.modules_guard(scientific,baseline)
        need(modules['reader'].query_bind is loaded['source'].query_bind and
             modules['kernel'].exact is modules['exact_predicates'] and
             modules['producer'].ellipsoidal_area is modules['ellipsoidal_area'],
             'Actual original science/acquisition cross-binding differs')
        loaded['runtime'].require_scientific_bindings(scientific,bindings)
        loaded['runtime'].callables(runtime_pin,guard)
        loaded['runtime'].loaded(runtime_pin,runtime_index,repo=repo,owned=OWNED,project_pins=pins)
    runtime_guard()
    # Before whole native custody, verify originals against the complete accepted
    # source index; no Sources constructor or eager all201 decode is used.
    source_pin = next(p for p in project if p['path'] == OWNED+'source-index.json')
    source = json.loads(phase.read(source_pin)); originals, aliases = modules['driver'].aliases(source)
    for pin in dependencies:
        if pin.get('commit'):
            need(aliases.get((pin['commit'],pin['path'])) == pin or pin in project,
                 'Foreign original source dependency outside complete202 custody')
    # Completion guards execute before receipt-last publication. Only this new
    # instance's completion boundary is wrapped; literal science stays unchanged.
    actual_finish = phase.finish
    def finish(facts):
        runtime_guard()
        return actual_finish(dict(facts,execution_commit=commit,
                                  execution_request_pin=request_pin,execution_freeze_pin=freeze_pin))
    phase.finish=finish; expected_finish[0]=finish
    receipt = execute(phase,request,modules,loaded,guard=guard,baseline=baseline,runtime_guard=runtime_guard,project_pins=project)
    # numerical.complete writes its own equivalent receipt and therefore has a
    # separate explicit pre-completion guard inside execute rather than wrapping.
    print(json.dumps(receipt,sort_keys=True),flush=True)


if __name__ == '__main__':
    main()
