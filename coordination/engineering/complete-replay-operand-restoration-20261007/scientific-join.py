"""Lossless bounded join of completed literal numerical cohorts.

No geometry operation is performed here. Whole canonical component rows, native
source inverse aliases and complete ordinary geometry bodies are preserved. The
independently frozen plan supplies exact expected input rosters; a producer's own
inventory is never accepted as its expectation. verify_cohort is a detached whole
operand/inverse-check stage. join consumes those completed checks and actual
scientific files. Admission is the real Phase encoded+decoded+runtime+output cost;
final delivery additionally charges every preserved input/history/proof file.
This completion is one scientific join, not two-run campaign acceptance.
"""
import gzip
import io
import json
import re
from collections import Counter
from pathlib import Path

SIX = {'contradictory_land_water_support', 'extra_reconstruction',
       'mapped_inland_water_support', 'mapped_land_support',
       'missing_reconstruction', 'outside_mapped_L1_context'}
THREE = {'L2-outside-L1', 'L3-outside-L2', 'L4-outside-L3'}
MEMBER_BYTES = 95809336
MEMBER_SHA = 'af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6'
COUNTS = dict(components=1294, families=494, batches=49, ordered_queries=10419,
              native_records=8635, native_headers=188612)


def _rows(phase, pins, acq):
    for pin in pins:
        body = phase.read(pin)
        for line in body.splitlines(keepends=True):
            row = json.loads(line)
            acq.require(type(row) is dict and acq.canonical(row) == line,
                        'Scientific row is not whole original canonical JSONL')
            yield row
        del body


def _roster(pins, acq):
    rows = {}
    for pin in pins:
        acq.bounds(pin)
        key = acq.Phase.key(pin)
        acq.require(key not in rows, 'Duplicate expected full descriptor')
        rows[key] = pin
    return rows


def _stage(phase, spec, operation, acq):
    inv = acq.completed_inventory(phase, spec['publication'], spec['inventory'])
    acq.require(inv['facts'].get('operation') == operation,
                'Inherited wrong completed scientific stage')
    acq.require(_roster(inv['input_descriptors'], acq) ==
                _roster(spec['expected_inputs'], acq),
                'Executed source/code/project closure differs from frozen expectation')
    acq.require(inv['runtime_bytes'] == spec['expected_runtime_bytes'] > 0,
                'Executed actual runtime charge differs')
    acq.require(_roster(inv['outputs'], acq) == _roster(spec['outputs'], acq),
                'Incomplete/foreign actual stage outputs')
    return inv


def _scope(phase, pin, acq):
    plan = json.loads(phase.read(pin))
    acq.require(plan.get('version') == 1 and plan.get('counts') == COUNTS,
                'Frozen complete original scientific scope required')
    components = {}
    for row in plan['components']:
        identity = row['component_id']
        acq.require(type(identity) is str and identity not in components,
                    'Duplicate/foreign scope identity')
        acq.require(type(row['query_count']) is int and row['query_count'] >= 0 and
                    len(row['ordered_query_bindings']) == row['query_count'],
                    'Complete ordered query expectation differs')
        components[identity] = row
    acq.require(len(components) == COUNTS['components'] and
                len({r['family'] for r in components.values()}) == COUNTS['families'] and
                len({r['batch'] for r in components.values()}) == COUNTS['batches'] and
                sum(r['query_count'] for r in components.values()) == COUNTS['ordered_queries'],
                'Full original component/family/batch/query scope differs')
    ids = plan['native_source_parent_ids']
    acq.require(type(ids) is list and all(type(i) is int and i >= 0 for i in ids) and
                ids == sorted(set(ids)) and len(ids) == COUNTS['native_records'],
                'Full original native ancestor scope differs')
    return plan, components


def _native(phase, spec, plan, acq):
    inv = _stage(phase, spec, 'complete-native-source-metadata-and-inverse-custody', acq)
    facts = inv['facts']
    acq.require(facts['member_bytes'] == MEMBER_BYTES and facts['member_sha256'] == MEMBER_SHA and
                facts['complete_headers'] == COUNTS['native_headers'] and
                facts['complete_source_parent_ids'] == plan['native_source_parent_ids'] and
                facts['actual_ordered_query_bindings'] == COUNTS['ordered_queries'] and
                facts['complete_mismatch_components'] == COUNTS['components'],
                'Complete actual native proof/scope differs')
    result = {}
    previous = -1
    for row in _rows(phase, spec['outputs'], acq):
        identity, meta, alias = row['source_id'], row['complete_original_metadata'], row['alias']
        acq.require(type(identity) is int and identity > previous and identity in plan['native_source_parent_ids'],
                    'Duplicate/foreign/unordered native metadata')
        previous = identity
        acq.require(meta['id'] == identity and alias['kind'] == 'complete-original-native-record-alias' and
                    alias['member_sha256'] == MEMBER_SHA and
                    alias['record_ordinal'] == meta['ordinal'] and
                    alias['byte_offset'] == meta['native_offset'] and
                    alias['record_bytes'] == meta['native_record_bytes'] and
                    alias['record_sha256'] == meta['record_sha256'] and
                    alias['pointset_binary64_sha256'] == meta['decoded_pointset_binary64_sha256'],
                    'Whole native alias/metadata provenance differs')
        acq.require(0 <= alias['byte_offset'] < MEMBER_BYTES and
                    44 <= alias['record_bytes'] <= acq.FILE and
                    alias['byte_offset'] + alias['record_bytes'] <= MEMBER_BYTES,
                    'Native whole record escapes complete source frame')
        result[identity] = row
    acq.require(sorted(result) == plan['native_source_parent_ids'], 'Omitted native metadata/ancestor')
    for row in result.values():
        for key in ('container', 'ancestor'):
            parent = row['complete_original_metadata'][key]
            acq.require(type(parent) is int and (parent == -1 or parent in result),
                        'Omitted native complete ancestor provenance')
    return result


def _pointer(value, parts, acq):
    acq.require(type(parts) is list, 'Whole object selector must be a list')
    for part in parts:
        acq.require(type(part) in (str, int), 'Invalid whole object selector')
        if type(part) is int:
            acq.require(type(value) is list and 0 <= part < len(value), 'Whole object ordinal escapes')
        else:
            acq.require(type(value) is dict and part in value, 'Whole object member omitted')
        value = value[part]
    return value


def _inverse(alias, identity, operand, acq):
    acq.require(alias['kind'] == 'complete-original-object' and alias['component_id'] == identity,
                'Foreign original whole object alias')
    kind = alias['original_object']
    acq.require(kind in ('candidate', 'physical', 'diagnosis'), 'Wrong original object kind')
    value = _pointer(operand[kind], alias['selector'], acq)
    raw = acq.canonical(value)
    acq.require(len(raw) == alias['whole_object_bytes'] and acq.sha(raw) == alias['whole_object_sha256'],
                'Whole original object inverse bytes differ')
    if kind == 'physical':
        acq.require(alias['original_whole_row'] == operand['physical_alias'], 'Original physical full row alias differs')
    if kind == 'candidate':
        acq.require(alias['complete_candidate_feature_sha256'] == operand['routing']['current_feature_sha256'],
                    'Original candidate whole feature provenance differs')
    return value


def _walk(value, identity, operand, native, geometries, acq):
    if type(value) is list:
        return [_walk(v, identity, operand, native, geometries, acq) for v in value]
    if type(value) is not dict:
        return value
    if 'complete_inverse_alias' in value:
        acq.require(set(value) == {'complete_inverse_alias'}, 'Ambiguous whole inverse object')
        alias = value['complete_inverse_alias']
        if alias['kind'] == 'complete-original-object':
            return _inverse(alias, identity, operand, acq)
        acq.require(alias['kind'] == 'complete-native-record-geometry' and
                    type(alias['source_id']) is int and alias['source_id'] in native and
                    type(alias['periodic_offset']) in (int, float) and alias['periodic_offset'] in (-360, 0, 360),
                    'Foreign native geometry inverse')
        acq.require(alias['original_native_record'] == native[alias['source_id']]['alias'] and
                    type(alias['whole_mapping_bytes']) is int and alias['whole_mapping_bytes'] > 0 and
                    re.fullmatch('[a-f0-9]{64}', alias['whole_mapping_sha256']) is not None and
                    alias['decoder'] == 'literal original comparison.decode_record then original periodic translate',
                    'Native geometry whole source inverse provenance differs')
        # Literal numerical producer executed this inverse. Joining cannot replay
        # native geometry without a separately admitted whole native source phase.
        return value
    if 'complete_ordinary_geometry_sha256' in value:
        acq.require(set(value) == {'complete_ordinary_geometry_sha256'} and
                    value['complete_ordinary_geometry_sha256'] in geometries,
                    'Missing complete ordinary geometry body')
        return geometries[value['complete_ordinary_geometry_sha256']]['geometry']
    return {k: _walk(v, identity, operand, native, geometries, acq) for k, v in value.items()}


def _geometry(phase, pins, acq):
    result = {}
    for row in _rows(phase, pins, acq):
        acq.require(set(row) == {'whole_geometry_sha256', 'geometry'}, 'Wrong complete geometry row')
        key = row['whole_geometry_sha256']
        acq.require(acq.sha(acq.canonical(row['geometry'])) == key, 'Whole geometry bytes differ')
        acq.require(key not in result or acq.canonical(result[key]) == acq.canonical(row),
                    'Whole geometry digest collision')
        result[key] = row
    return result


def _science_outputs(spec, acq):
    components, geometry = [], []
    for pin in spec['outputs']:
        name = Path(pin['path']).name
        if name.startswith('components-') and name.endswith('.jsonl.gz'):
            components.append(pin)
        elif name.startswith('geometry-objects-') and name.endswith('.jsonl.gz'):
            geometry.append(pin)
        else:
            acq.require(False, 'Foreign numerical scientific product')
    acq.require(components and components == sorted(components, key=lambda p:p['path']) and
                geometry == sorted(geometry, key=lambda p:p['path']), 'Numerical shard order differs')
    return components, geometry


def verify_cohort(phase, *, plan_pin, spec, native_spec, acquisition, project_guard):
    """Detached actual whole operand/inverse verification, no geometry execution.

    Caller prospectively admits all operand, science, metadata and closure files.
    spec is read from the independently frozen plan (not producer inventory).
    The final join must consume this stage's actual publication/inventory.
    """
    a = acquisition; project_guard()
    plan, scope = _scope(phase, plan_pin, a)
    a.require(spec in plan['cohorts'], 'Cohort not in independent frozen plan')
    a.require(native_spec == plan['native'], 'Changed independent native expectation')
    native = _native(phase, native_spec, plan, a)
    inv = _stage(phase, spec, 'complete-original-nine-map-numerical-cohort', a)
    facts = inv['facts']; ids = spec['component_ids']
    a.require(ids == sorted(set(ids)) and all(i in scope for i in ids) and
              facts['component_ids'] == ids and facts['original_ordered_queries'] ==
              sum(scope[i]['query_count'] for i in ids), 'Wrong full cohort component/query scope')
    proof = facts['native']
    a.require(proof['member_bytes'] == MEMBER_BYTES and proof['member_sha256'] == MEMBER_SHA and
              proof['complete_headers'] == COUNTS['native_headers'] and
              proof['complete_parent_closure_ids'] == spec['native_source_parent_ids'] and
              all(i in native for i in proof['complete_parent_closure_ids']), 'Wrong cohort native proof')
    a.require(proof['contributing_ids'] == sorted({q['source_id'] for i in ids
              for q in scope[i]['ordered_query_bindings']}), 'Wrong cohort contributing native IDs')
    operands = {}
    for row in _rows(phase, spec['operand_pins'], a):
        i = row['id']; a.require(i in ids and i not in operands, 'Duplicate/foreign original operand')
        a.require(row['candidate']['id'] == row['physical']['component_id'] == row['diagnosis']['component_id'] == i,
                  'Whole original operand identity differs')
        operands[i] = row
    a.require(sorted(operands) == ids, 'Omitted original operand including zero-query member')
    cp, gp = _science_outputs(spec, a); geometry = _geometry(phase, gp, a)
    seen = []; statuses = Counter(); query_count = 0
    for row in _rows(phase, cp, a):
        i = row['component_id']; a.require(i in ids and i not in seen and (not seen or i > seen[-1]),
                                        'Duplicate/foreign/unordered numerical component')
        seen.append(i); operand = operands[i]; expected = scope[i]
        a.require(row['original_query_count'] == expected['query_count'] == len(operand['physical']['query_relations']),
                  'Omitted original ordered query')
        expanded = _walk(row, i, operand, native, geometry, a)
        for kind, key in [('candidate','complete_original_candidate'), ('physical','complete_original_physical_row'),
                          ('diagnosis','complete_original_diagnosis')]:
            a.require(_inverse(row[key], i, operand, a) == operand[kind], 'Omitted complete original root object')
        a.require(expanded['original_physical_unknowns'] == operand['physical'].get('unresolved', []) and
                  row['repair_approval'] is False and row['physical_authority'] == 'unapproved' and
                  row['original_contradiction_claim_allowed'] is False, 'Unknown/approval semantics changed')
        for ordinal, original in enumerate(operand['physical']['query_relations']):
            binding = {k: original[k] for k in ('source_id','source_level','source_container',
                       'source_record_sha256','source_pointset_sha256','periodic_offset')}
            a.require(binding == expected['ordered_query_bindings'][ordinal] and
                      original['source_id'] in native, 'Changed retained original query/native binding')
        replays = expanded.get('actual_query_replays', [])
        if row['status'] in ('original-mappings-matched','unknown-original-replay-mismatch'):
            a.require(set(row['complete_six_mappings']) == SIX and
                      set(row['complete_three_hierarchy_mappings']) == THREE and
                      set(row['mapping_equality']) == SIX and set(row['hierarchy_mapping_equality']) == THREE,
                      'Missing complete original six/three maps')
            a.require(all(type(v) is bool for v in [*row['mapping_equality'].values(),
                      *row['hierarchy_mapping_equality'].values()]) and
                      (row['status'] != 'original-mappings-matched' or
                       all([*row['mapping_equality'].values(), *row['hierarchy_mapping_equality'].values()])),
                      'Changed original map equality/status semantics')
            a.require('retained_query_unknowns' in row and
                      set(row['original_positive_pieces']) == {'1','2','3','4'} and
                      set(row['fresh_positive_pieces']) == {'1','2','3','4'},
                      'Missing retained query unknowns/complete positive pieces')
            a.require(len(replays) == expected['query_count'], 'Omitted actual ordered replay')
            for ordinal, replay in enumerate(replays):
                original = operand['physical']['query_relations'][ordinal]
                binding = {k: original[k] for k in ('source_id','source_level','source_container',
                           'source_record_sha256','source_pointset_sha256','periodic_offset')}
                a.require(replay['ordinal'] == ordinal and replay['original'] == original and
                          binding == expected['ordered_query_bindings'][ordinal],
                          'Changed original query order/body/native binding')
        else:
            if row['status'] == 'unknown-invalid-candidate':
                a.require(row.get('actual_query_replays') == [], 'Changed invalid candidate replay branch')
            if row['status'] == 'unknown-operation-failed':
                a.require(type(row.get('exception_type')) is str and type(row.get('exception_message')) is str,
                          'Omitted original operation failure details')
            if row['status'] == 'unknown-operation-failed' and 'actual_query_replays' in row:
                a.require(len(replays) == expected['query_count'] and all(
                          replay['ordinal'] == ordinal and replay['original'] ==
                          operand['physical']['query_relations'][ordinal]
                          for ordinal, replay in enumerate(replays)),
                          'Changed completed query replays retained by original failure branch')
            a.require(row['status'] in ('unknown-invalid-candidate','unknown-operation-failed') and
                      row['original_query_accounting'] == 'complete original physical row retained',
                      'Unknown result silently changed/omitted')
        statuses[row['status']] += 1; query_count += expected['query_count']
    a.require(seen == ids and dict(sorted(statuses.items())) == facts['statuses'],
              'Omitted/changed completed scientific results')
    project_guard()
    return phase.finish(dict(operation='whole-original-scientific-cohort-inverse-check',
                             source_spec=spec, plan_pin=plan_pin, component_ids=ids,
                             original_ordered_queries=query_count, statuses=dict(sorted(statuses.items())),
                             limits=['Native numeric inverse was executed by exact frozen literal producer.',
                                     'This stage checks full source provenance; it performs no native geometry calculation.']))


def restore_shard(recipe, *, components, geometry, native_records, acquisition):
    """Complete inverse reader usable after intermediate scratch files are gone.

    Inputs are full authenticated final objects, not hashes or fragments.
    Every selector preserves original row order including duplicate occurrences.
    """
    a = acquisition
    a.require(recipe['kind'] == 'complete-original-scientific-shard-inverse', 'Wrong complete inverse kind')
    kind = recipe['final_object_kind']; selectors = recipe['ordered_complete_selectors']
    a.require(type(selectors) is list, 'Whole shard selectors must be complete ordered list')
    if kind == 'components':
        rows = [components[i] for i in selectors]
    elif kind == 'geometry-objects':
        rows = [geometry[i] for i in selectors]
    else:
        a.require(kind == 'native-record-aliases', 'Unknown final whole object source')
        rows = []
        for i in selectors:
            final = native_records[i]
            alias = {k:v for k,v in final.items() if k not in ('source_id','complete_original_metadata')}
            rows.append(dict(source_id=final['source_id'], complete_original_metadata=final['complete_original_metadata'], alias=alias))
    pin = recipe['original_whole_file']; a.bounds(pin)
    # Prospectively stop before constructing an oversized complete inverse body.
    parts = []; used = 0
    for row in rows:
        raw = a.canonical(row); used += len(raw)
        a.require(used <= pin['uncompressed_bytes'], 'Whole inverse decoded body exceeds original bound')
        parts.append(raw)
    body = b''.join(parts)
    a.require(len(body) == pin['uncompressed_bytes'] and a.sha(body) == pin['uncompressed_sha256'],
              'Complete inverse decoded bytes differ')
    writer = recipe['original_writer']
    if writer == 'literal-products':
        buffer = io.BytesIO()
        with gzip.GzipFile(filename='', fileobj=buffer, mode='wb', mtime=0, compresslevel=9) as stream:
            stream.write(body)
        encoded = buffer.getvalue()
    else:
        a.require(writer == 'acquisition-phase', 'Unknown source gzip inverse writer')
        encoded = gzip.compress(body, mtime=0, compresslevel=9)
    a.require(len(encoded) == pin['bytes'] and a.sha(encoded) == pin['sha256'],
              'Complete inverse encoded bytes differ')
    return encoded


def _shard_inverse(phase, pin, selectors, kind, writer, components, geometry, native_records, acq):
    recipe = dict(kind='complete-original-scientific-shard-inverse', original_whole_file=pin,
                  original_writer=writer, final_object_kind=kind, ordered_complete_selectors=selectors,
                  reconstruction='complete final rows in original order; native row restores nested alias; literal deterministic gzip')
    encoded = restore_shard(recipe, components=components, geometry=geometry,
                            native_records=native_records, acquisition=acq)
    # Real whole original source was consumed under this Phase admission, and
    # actual byte equality is executed, beyond the retained descriptor hashes.
    phase.read(pin)
    with acq.ordinary(pin['path']).open('rb') as stream:
        actual = stream.read(pin['bytes'] + 1)
    acq.require(encoded == actual, 'Complete source shard inverse actual bytes differ')
    return recipe


def join(phase, *, plan_pin, verification_specs, acquisition, project_guard,
         final_delivery_pins, final_metadata_reserve, final_metadata_descriptor_reserve):
    """Join full actual rows under both real Phase and complete flat delivery caps.

    final_delivery_pins is the independent complete original/code/runtime/history/
    evidence roster, excluding final files generated here. No hashes are used to
    collapse distinct paths. An over-budget attempt remains incomplete.
    """
    a = acquisition; project_guard(); plan, scope = _scope(phase, plan_pin, a)
    a.require(type(final_metadata_reserve) is int and final_metadata_reserve >= a.RECEIPT,
              'Explicit final report/history/receipt reserve required')
    a.require(type(final_metadata_descriptor_reserve) is int and final_metadata_descriptor_reserve >= 2,
              'Explicit complete final metadata descriptor reserve required')
    delivery = _roster(final_delivery_pins, a)
    a.require(sum(p['bytes'] for p in delivery.values()) + final_metadata_reserve <= a.PHASE and
              len(delivery) + final_metadata_descriptor_reserve <= 512, 'Final complete flat delivery already exceeds cap')
    native = _native(phase, plan['native'], plan, a)
    a.require(len(verification_specs) == len(plan['cohorts']), 'Omitted completed cohort inverse check')
    components = {}; geometry = {}; statuses = Counter(); seen_specs = []; inverse_requests = []
    for check in verification_specs:
        ci = _stage(phase, check, 'whole-original-scientific-cohort-inverse-check', a)
        a.require(not check['outputs'] and ci['facts']['plan_pin'] == plan_pin,
                  'Foreign scientific verification product/plan')
        spec = ci['facts']['source_spec']
        a.require(spec in plan['cohorts'] and spec not in seen_specs, 'Duplicate/foreign inherited cohort')
        seen_specs.append(spec)
        inv = _stage(phase, spec, 'complete-original-nine-map-numerical-cohort', a)
        a.require(ci['facts']['component_ids'] == inv['facts']['component_ids'] == spec['component_ids'] and
                  ci['facts']['statuses'] == inv['facts']['statuses'] and
                  ci['facts']['original_ordered_queries'] == inv['facts']['original_ordered_queries'],
                  'Changed verified scientific source facts')
        cp, gp = _science_outputs(spec, a)
        for pin in gp:
            selectors = [r['whole_geometry_sha256'] for r in _rows(phase, [pin], a)]
            inverse_requests.append((pin, selectors, 'geometry-objects', 'literal-products'))
        for key, row in _geometry(phase, gp, a).items():
            a.require(key not in geometry or a.canonical(geometry[key]) == a.canonical(row),
                      'Across-cohort full geometry collision')
            geometry[key] = row
        actual_ids = []
        for pin in cp:
            selectors = [r['component_id'] for r in _rows(phase, [pin], a)]
            inverse_requests.append((pin, selectors, 'components', 'literal-products'))
        for row in _rows(phase, cp, a):
            identity = row['component_id']
            a.require(identity in scope and identity not in components and
                      (not actual_ids or identity > actual_ids[-1]), 'Duplicate/foreign/unordered joined component')
            a.require(row['original_query_count'] == scope[identity]['query_count'], 'Changed joined query count')
            actual_ids.append(identity); components[identity] = row; statuses[row['status']] += 1
        a.require(actual_ids == spec['component_ids'], 'Omitted joined component including zero queries')
    a.require(sorted(components) == sorted(scope) and len(seen_specs) == len(plan['cohorts']),
              'Incomplete original global scientific join')
    for pin in plan['native']['outputs']:
        selectors = [r['source_id'] for r in _rows(phase, [pin], a)]
        inverse_requests.append((pin, selectors, 'native-record-aliases', 'acquisition-phase'))
    native_final = {i:dict(native[i]['alias'], source_id=i,
                   complete_original_metadata=native[i]['complete_original_metadata']) for i in native}
    inverses = []
    for pin, selectors, kind, writer in inverse_requests:
        inverses.append(_shard_inverse(phase, pin, selectors, kind, writer,
                                       components, geometry, native_final, a))
    # Canonical rows remain exact; only file sharding and whole-byte duplicate
    # geometry deduplication change. Native source aliases retain original schema.
    phase.rows('components', (components[i] for i in sorted(components)))
    phase.rows('geometry-objects', (geometry[i] for i in sorted(geometry)))
    phase.rows('native-record-aliases', (native_final[i] for i in sorted(native_final)))
    phase.rows('scientific-stage-inverses', inverses)
    outputs = [p for p, _ in phase.payloads.values()]
    total = sum(p['bytes'] for p in delivery.values()) + sum(p['bytes'] for p in outputs) + final_metadata_reserve
    a.require(total <= a.PHASE and len(delivery) + len(outputs) + final_metadata_descriptor_reserve <= 512,
              'Final complete flat scientific delivery exceeds actual cap; preserve failed attempt')
    project_guard()
    facts = dict(operation='complete-original-scientific-join', counts=COUNTS,
                             statuses=dict(sorted(statuses.items())), plan_pin=plan_pin,
                             complete_source_scientific_shard_inverses=len(inverses),
                             complete_flat_encoded_with_reserved_metadata=total,
                             complete_flat_descriptor_count_with_metadata=len(delivery)+len(outputs)+final_metadata_descriptor_reserve,
                             final_delivery_descriptors=list(delivery.values()),
                             final_metadata_reserve=final_metadata_reserve,
                             final_metadata_descriptor_reserve=final_metadata_descriptor_reserve,
                             limits=['One joined execution; two actual frozen full successes and whole equality still required.',
                                     'Unknowns preserved. No physical approval, new geography or campaign completion.'])
    projected_inventory = dict(version=1, kind='bounded-original-acquisition-stage', facts=facts,
                               input_descriptors=list(phase.pins.values()), outputs=outputs,
                               input_encoded_decoded_bytes=phase.input_bytes, runtime_bytes=phase.runtime_bytes,
                               output_encoded_decoded_bytes=sum(a.cost(p) for p in outputs),
                               complete_phase_bytes=phase.input_bytes+phase.runtime_bytes+sum(a.cost(p) for p in outputs))
    inventory_encoded = gzip.compress(a.canonical(projected_inventory), compresslevel=9, mtime=0)
    a.require(len(inventory_encoded) + a.RECEIPT <= final_metadata_reserve,
              'Actual final inventory/publication exceed complete metadata reserve')
    return phase.finish(facts)
