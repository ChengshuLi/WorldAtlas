"""Complete1394 cohort selectors from authenticated detached acquisition jobs.

Three independent projection jobs consume the complete original component,
routing and physical index rosters. They preserve every identity and full selected
index records while removing unused duplicate complement metadata from the next
job's actual input set. The generator consumes these real products, the original
joins and all71 restoration inventories. No global dictionary leaves a job.
Selectors are complete objects in bounded JSONL shards; a separate admitted job
materializes one selector for the existing cohort-acquisition entry point.
"""
import json
from pathlib import Path


OPERATIONS = {
    'physical': 'complete-original-physical-query-join',
    'query': 'complete-actual-native-query-join',
    'candidate': 'complete-candidate-bindings',
    'routing': 'complete-routing-candidate-join',
}


def completed(phase, pair, operation, acquisition):
    inventory = acquisition.completed_inventory(phase, pair[0], pair[1])
    acquisition.require(inventory['facts']['operation'] == operation, 'Wrong original cohort predecessor operation')
    return inventory


def output_set(inventory, prefix):
    return [p for p in inventory['outputs'] if Path(p['path']).name.startswith(prefix)]


def actual_outputs(inventory, supplied, prefix, acquisition):
    expected = output_set(inventory, prefix)
    acquisition.require(len({p['path'] for p in supplied}) == len(supplied) and
                        sorted(supplied, key=lambda p: p['path']) == sorted(expected, key=lambda p: p['path']),
                        'Missing/foreign actual complete cohort index product')


def mismatch_roster(phase, pins, acquisition):
    rows = acquisition.exact_ids(acquisition.raw_rows(phase, pins), 'id')
    acquisition.require(len(rows) == 1294 and len({r['family'] for r in rows.values()}) == 494 and
                        len({r['operational_batch'] for r in rows.values()}) == 49 and
                        all(r['status'] == 'original-replay-mismatch' for r in rows.values()),
                        'Incomplete original1294/494/49 mismatch selector')
    return rows


def prepare_index(phase, kind, index_pins, mismatch_pins, *, index_stage_pairs,
                  mismatch_pair, physical_join_pair, acquisition):
    """One genuine whole-roster projection job, admitted before caller executes."""
    acquisition.require(kind in ('components', 'routing', 'physical'), 'Foreign cohort projection kind')
    mismatch = completed(phase, mismatch_pair, 'complete-original-mismatch-selector', acquisition)
    actual_outputs(mismatch, mismatch_pins, 'mismatch-index-', acquisition)
    physical_join = completed(phase, physical_join_pair, OPERATIONS['physical'], acquisition)
    facts = physical_join['facts']
    acquisition.require(facts['complete'] == 95173 and facts['mismatches'] == 1294 and facts['ordered_queries'] == 10419,
                        'Missing exhaustive physical/query campaign join')
    expected_inputs = []; output_prefix = {'components': 'components-', 'routing': 'routing-',
                                         'physical': 'physical-index-'}[kind]
    for pair in index_stage_pairs:
        expected_operation = {'components': 'literal-ledger-reconstruction',
                              'routing': 'routing-containing-part',
                              'physical': 'whole-original-physical-restoration'}[kind]
        inventory = completed(phase, pair, expected_operation, acquisition)
        if kind == 'components':
            acquisition.require(inventory['facts']['ledger'] == 'components' and
                                inventory['facts']['current_count'] == 95173,
                                'Wrong complete candidate ledger projection source')
        expected_inputs += output_set(inventory, output_prefix)
    acquisition.require(sorted(index_pins, key=lambda p: p['path']) == sorted(expected_inputs, key=lambda p: p['path']) and
                        len(index_stage_pairs) == {'components': 1, 'routing': 25, 'physical': 71}[kind],
                        'Omitted original complete index containing stage')
    selected = mismatch_roster(phase, mismatch_pins, acquisition)
    table = acquisition.canonical(index_pins)
    phase.output('original-index-inputs.json', table)
    seen = set(); rows = []; scoped = 0
    for input_number, pin in enumerate(index_pins):
        for ordinal, line in enumerate(phase.read(pin).splitlines()):
            row = json.loads(line); identity = row['id']
            acquisition.require(type(identity) is str and identity not in seen, 'Duplicate/nonstring full projection identity')
            seen.add(identity)
            compact = {'id': identity}
            if kind == 'routing':
                acquisition.require(type(row['selected']) is bool, 'Wrong actual routing scope marker type')
                scoped += row['selected']
            if identity in selected:
                if kind == 'components':
                    record = {key: row[key] for key in ('id', 'alias', 'geometry_sha256')}
                else:
                    record = row
                if kind == 'routing':
                    acquisition.require(row['selected'] is True and
                                        all(row['row'][key] == selected[identity][key] for key in ('family', 'operational_batch')),
                                        'Wrong original mismatch routing family/batch membership')
                if kind == 'physical':
                    acquisition.require(row['original_path'] == selected[identity]['physical_containing_file'] and
                                        type(row['query_count']) is int and row['query_count'] >= 0,
                                        'Wrong original mismatch physical containing file/query count')
                compact.update(record=record, original_index={'input_number': input_number,
                    'row_ordinal': ordinal, 'whole_row_sha256': acquisition.sha(line+b'\n')})
            rows.append(compact)
    acquisition.require(len(seen) == 95173 and set(selected) <= seen and
                        (kind != 'routing' or scoped == 26276), 'Incomplete complete95173 projection scope')
    phase.rows('cohort-'+kind, rows)
    del selected, seen, rows
    return phase.finish({'operation': 'complete-original-cohort-index-projection', 'index_kind': kind,
                         'complete': 95173, 'mismatches': 1294,
                         'original_index_table_sha256': acquisition.sha(table)})


def group_key(item, candidate_pin):
    diagnosis = item['diagnosis_index']['input']
    return (item['physical_containing_pin']['path'], candidate_pin.get('commit'), candidate_pin['path'],
            diagnosis.get('commit'), diagnosis['path'])


def unique(pins, acquisition):
    result = {}
    for pin in pins:
        key = acquisition.Phase.key(pin)
        acquisition.require(key not in result or result[key] == pin, 'Conflicting actual next-cohort input')
        result[key] = pin
    return list(result.values())


def projection_dependencies(index_pins, mismatch_pins, index_stage_pairs,
                            mismatch_pair, physical_join_pair, acquisition):
    """Descriptor-only admission inventory; no predecessor preview/read."""
    return unique([*index_pins, *mismatch_pins, *mismatch_pair, *physical_join_pair,
                   *[pin for pair in index_stage_pairs for pin in pair]], acquisition)


def selector_dependencies(*, projected_pins, projection_pairs, mismatch_pins, mismatch_pair,
                          component_ledger_pair, candidate_table_pin, physical_stage_pairs,
                          physical_join_pair, query_join_pair, query_pins, acquisition):
    """Caller constructs Phase with these actual pins BEFORE decoding metadata."""
    return unique([*[p for values in projected_pins.values() for p in values],
                   *[p for pair in projection_pairs.values() for p in pair],
                   *mismatch_pins, *mismatch_pair, *component_ledger_pair, candidate_table_pin,
                   *[p for pair in physical_stage_pairs for p in pair],
                   *physical_join_pair, *query_join_pair, *query_pins], acquisition)


def admit_dependencies(pins, project_pins, runtime_bytes, output_reserve, acquisition):
    """Prospective actual descriptor accounting, without reading any body."""
    complete = unique([*pins, *project_pins], acquisition)
    count = len(complete)
    total = sum(acquisition.cost(p) for p in complete)+runtime_bytes+output_reserve+acquisition.RECEIPT
    acquisition.require(type(runtime_bytes) is int and runtime_bytes > 0 and type(output_reserve) is int and
                        output_reserve >= 0 and total <= acquisition.PHASE and count+2 <= 512,
                        'Prospective complete cohort metadata/runtime/output admission failed')
    return {'input_descriptors': count, 'prospective_phase_bytes': total,
            'output_reserve': output_reserve, 'runtime_bytes': runtime_bytes}


def next_inputs(selector, selector_pin, table, *, project_pins, acquisition):
    """Complete actual original source dependencies for cohort-acquisition.extract."""
    pins = [selector_pin, selector['campaign_join']['publication'], selector['campaign_join']['inventory'],
            selector['mismatch_join']['publication'], selector['mismatch_join']['inventory'],
            *selector['mismatch_index_pins'], *project_pins]
    for item in selector['rows']:
        index = item['candidate_alias']['input_index']
        acquisition.require(type(index) is int and 0 <= index < len(table), 'Escaped candidate containing-table dependency')
        pins += [item['candidate_containing_table'], table[index], item['physical_containing_pin'],
                 item['diagnosis_index']['input']]
    return unique(pins, acquisition)


def selectors(phase, *, projected_pins, projection_pairs, mismatch_pins, mismatch_pair,
              component_ledger_pair, candidate_table_pin, physical_stage_pairs,
              physical_join_pair, query_join_pair, query_pins, acquisition,
              project_pins, runtime_bytes, acquisition_output_reserve=67108864):
    """Generate the complete disjoint selector set; return receipt only."""
    mismatch_inventory = completed(phase, mismatch_pair, 'complete-original-mismatch-selector', acquisition)
    actual_outputs(mismatch_inventory, mismatch_pins, 'mismatch-index-', acquisition)
    mismatch = mismatch_roster(phase, mismatch_pins, acquisition)
    physical_join = completed(phase, physical_join_pair, OPERATIONS['physical'], acquisition)
    query_join = completed(phase, query_join_pair, OPERATIONS['query'], acquisition)
    acquisition.require(physical_join['facts']['complete'] == 95173 and
                        physical_join['facts']['mismatches'] == query_join['facts']['components'] == 1294 and
                        physical_join['facts']['ordered_queries'] == query_join['facts']['ordered_queries'] == 10419,
                        'Wrong actual complete campaign joins')
    expected_query_pins = [p for p in query_join['input_descriptors']
                          if Path(p['path']).name.startswith('native-query-index-')]
    acquisition.require(sorted(query_pins, key=lambda p: p['path']) == sorted(expected_query_pins, key=lambda p: p['path']),
                        'Omitted actual whole ordered-query index product')
    ledger = completed(phase, component_ledger_pair, 'literal-ledger-reconstruction', acquisition)
    acquisition.require(ledger['facts']['ledger'] == 'components' and ledger['facts']['current_count'] == 95173,
                        'Wrong actual complete candidate ledger')
    actual_outputs(ledger, [candidate_table_pin], 'containing-inputs.json', acquisition)
    table_raw = phase.read(candidate_table_pin); table = json.loads(table_raw)
    acquisition.require(acquisition.sha(table_raw) == ledger['facts']['containing_table_sha256'],
                        'Wrong actual candidate containing input table')
    views = {}
    for kind in ('components', 'routing', 'physical'):
        projection = completed(phase, projection_pairs[kind], 'complete-original-cohort-index-projection', acquisition)
        acquisition.require(projection['facts']['index_kind'] == kind and projection['facts']['complete'] == 95173 and
                            projection['facts']['mismatches'] == 1294, 'Wrong complete projected index predecessor')
        actual_outputs(projection, projected_pins[kind], 'cohort-'+kind+'-', acquisition)
        views[kind] = acquisition.exact_ids(acquisition.raw_rows(phase, projected_pins[kind]), 'id')
    identities = set(views['components'])
    acquisition.require(len(identities) == 95173 and identities == set(views['routing']) == set(views['physical']) and
                        all({i for i, row in views[kind].items() if 'record' in row} == set(mismatch) for kind in views),
                        'Complete current/routing/physical/mismatch projection bijection differs')
    physical = {}; indexed_count = 0
    acquisition.require(len(physical_stage_pairs) == 71, 'Omitted whole physical restoration stage')
    for pair in physical_stage_pairs:
        inventory = completed(phase, pair, 'whole-original-physical-restoration', acquisition)
        original = inventory['facts']['original']; original_path = 'coordination/engineering/global-physical-comparison-20261006/results/'+original['path']
        restored = output_set(inventory, 'whole-original-physical.jsonl.gz')
        packed = [p for p in inventory['input_descriptors'] if
                  p.get('original_relation', {}).get('original_path') == original_path]
        acquisition.require(original_path not in physical and len(restored) == len(packed) == 1 and
                            all(restored[0][key] == original[key] for key in
                                ('bytes', 'sha256', 'uncompressed_bytes', 'uncompressed_sha256')),
                            'Wrong/duplicate physical whole containing-file custody')
        physical[original_path] = (restored[0], packed[0])
        indexed_count += inventory['facts']['components']
    acquisition.require(indexed_count == 95173 and len(physical) == 71, 'Incomplete original physical restoration roster')
    counts = {identity: 0 for identity in mismatch}; wanted = {identity: set() for identity in mismatch}
    for row in acquisition.raw_rows(phase, query_pins):
        identity = row['component_id']
        acquisition.require(identity in mismatch and type(row['query_ordinal']) is int and
                            row['query_ordinal'] == counts[identity] and type(row['query']['source_id']) is int,
                            'Foreign/duplicated/reordered actual original query')
        counts[identity] += 1; wanted[identity].add(row['query']['source_id'])
    acquisition.require(sum(counts.values()) == 10419 and
                        sorted(set().union(*wanted.values())) == query_join['facts']['contributing_source_ids'],
                        'Complete original ordered-query/source closure differs')
    groups = {}
    for identity in sorted(mismatch):
        component = views['components'][identity]['record']; routing = views['routing'][identity]['record']
        support = views['physical'][identity]['record']; diagnosis = mismatch[identity]
        acquisition.require(component['alias']['whole_object_sha256'] == routing['row']['current_feature_sha256'] and
                            component['geometry_sha256'] == routing['row']['current_geometry_sha256'] and
                            support['original_path'] == routing['row']['whole_physical_containing_file'] == diagnosis['physical_containing_file'] and
                            support['packed_whole_row_sha256'] == routing['row']['whole_physical_row_sha256'] and
                            counts[identity] == support['query_count'], 'Actual complete selected operand/source binding differs')
        restored_pin, packed_pin = physical[support['original_path']]
        alias = acquisition.bind_alias(component, ledger); input_number = alias['input_index']
        acquisition.require(type(input_number) is int and 0 <= input_number < len(table), 'Wrong actual candidate containing ordinal')
        item = {'id': identity, 'candidate_alias': alias, 'candidate_containing_table': candidate_table_pin,
                'physical_index': support, 'physical_containing_pin': restored_pin,
                'packed_containing_path': packed_pin['path'], 'diagnosis_index': diagnosis, 'routing': routing}
        groups.setdefault(group_key(item, table[input_number]), []).append(item)
    def values():
        covered = set(); queries = 0
        for number, (_, items) in enumerate(sorted(groups.items())):
            ids = [item['id'] for item in items]
            acquisition.require(not covered.intersection(ids), 'Duplicate actual cohort component')
            covered.update(ids); count = sum(counts[i] for i in ids); queries += count
            selector = {'kind': 'complete-original-numerical-cohort-selector', 'cohort_ordinal': number,
                        'rows': items, 'campaign_join': {'publication': physical_join_pair[0], 'inventory': physical_join_pair[1]},
                        'campaign_join_sha256': physical_join_pair[1]['sha256'],
                        'mismatch_join': {'publication': mismatch_pair[0], 'inventory': mismatch_pair[1]},
                        'mismatch_index_pins': mismatch_pins, 'components': len(items), 'ordered_queries': count,
                        'wanted_native_ids': sorted(set().union(*(wanted[i] for i in ids)))}
            raw = acquisition.canonical(selector)
            acquisition.require(len(raw) <= acquisition.FILE, 'One complete selector exceeds ordinary bound')
            virtual_pin = {'path': str(phase.destination/f'selector-{number:03}.json'),
                           'bytes': len(raw), 'sha256': acquisition.sha(raw)}
            inputs = next_inputs(selector, virtual_pin, table, project_pins=project_pins, acquisition=acquisition)
            selector['next_acquisition_source_cost_bytes'] = sum(acquisition.cost(p) for p in inputs if p != virtual_pin)
            selector['next_acquisition_output_reserve_bytes'] = acquisition_output_reserve
            raw = acquisition.canonical(selector)
            acquisition.require(len(raw) <= acquisition.FILE, 'Complete selector/accounting ordinary bound')
            charge = selector['next_acquisition_source_cost_bytes']+len(raw)+runtime_bytes+acquisition_output_reserve+acquisition.RECEIPT
            acquisition.require(charge <= acquisition.PHASE and len(inputs)+2 <= 512,
                                'Actual containing-file cohort requires further bounded subdivision')
            yield selector
        acquisition.require(covered == set(mismatch) and queries == 10419, 'Omitted actual complete cohort selector')
    cohort_count = len(groups)
    phase.rows('cohort-selectors', values())
    del views, identities, physical, counts, wanted, groups, mismatch, table
    return phase.finish({'operation': 'complete-original-cohort-selector-plan', 'components': 1294,
                         'families': 494, 'batches': 49, 'ordered_queries': 10419,
                         'cohorts': cohort_count, 'campaign_join_sha256': physical_join_pair[1]['sha256']})


def materialize_selector(phase, shard_pin, ordinal, expected_sha256, selector_plan_pair, acquisition):
    inventory = completed(phase, selector_plan_pair, 'complete-original-cohort-selector-plan', acquisition)
    facts = inventory['facts']
    acquisition.require(facts['components'] == 1294 and facts['families'] == 494 and
                        facts['batches'] == 49 and facts['ordered_queries'] == 10419 and
                        shard_pin in output_set(inventory, 'cohort-selectors-'),
                        'Missing complete1294 selector containing-byte custody')
    acquisition.require(type(ordinal) is int and ordinal >= 0, 'Wrong actual selector object ordinal')
    lines = phase.read(shard_pin).splitlines()
    acquisition.require(ordinal < len(lines), 'Omitted complete selector object')
    raw = lines[ordinal]+b'\n'; selector = json.loads(raw)
    acquisition.require(acquisition.sha(raw) == expected_sha256 and selector['kind'] ==
                        'complete-original-numerical-cohort-selector', 'Wrong actual whole selector bytes')
    phase.output('selector.json', raw)
    return phase.finish({'operation': 'complete-original-cohort-selector-materialization',
                         'cohort_ordinal': selector['cohort_ordinal'], 'whole_selector_sha256': expected_sha256,
                         'components': selector['components'], 'ordered_queries': selector['ordered_queries']})
