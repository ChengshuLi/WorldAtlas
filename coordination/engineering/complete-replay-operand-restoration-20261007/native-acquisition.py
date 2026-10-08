"""Whole native custody and complete source metadata, without global geometry state.

The original no-ZIP reader and binary decoder are injected as authenticated
literal modules. This adapter writes source-backed inverse aliases, never
serialized replacement geometry. Numerical consumers must decode their complete
needed original records again from an independently authenticated native image.
"""
import hashlib
import json
from pathlib import Path

FILE = 33554432
MEMBER_BYTES = 95809336
MEMBER_SHA256 = 'af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6'
HEADERS = 188612
RECORDS = 8635
QUERIES = 10419
COMPONENTS = 1294
ROW_BYTES = 2048
OUTPUT_RESERVE = 2 * RECORDS * ROW_BYTES + 524288
FIELDS = ('source_id', 'source_level', 'source_container', 'source_record_sha256',
          'source_pointset_sha256', 'periodic_offset')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False) + '\n').encode()


def sha(body):
    return hashlib.sha256(body).hexdigest()


def rows(phase, pins):
    for pin in pins:
        for line in phase.read(pin).splitlines():
            require(line, 'Empty native input row')
            row = json.loads(line)
            require(type(row) is dict, 'Nonobject native input row')
            yield row


def scope(phase, query_pins, mismatch_pins):
    """All original ordered query bindings; duplicates of a source ID are kept."""
    mismatches = set()
    for row in rows(phase, mismatch_pins):
        identity = row['id']
        require(type(identity) is str and identity not in mismatches,
                'Duplicate or malformed original mismatch component')
        mismatches.add(identity)
    require(len(mismatches) == COMPONENTS, 'Incomplete original mismatch component scope')
    wanted, by_source, ordinals = set(), {}, {}
    count = 0
    for row in rows(phase, query_pins):
        identity, ordinal, query = row['component_id'], row['query_ordinal'], row['query']
        require(identity in mismatches and type(ordinal) is int and ordinal >= 0 and
                type(query) is dict and set(query) == set(FIELDS),
                'Wrong original query component, ordinal or binding schema')
        require(type(row.get('original_query_sha256')) is str and
                len(row['original_query_sha256']) == 64 and
                all(c in '0123456789abcdef' for c in row['original_query_sha256']),
                'Missing complete original query hash')
        require(type(query['source_id']) is int and query['source_id'] >= 0,
                'Wrong original native query identity type')
        require(ordinal not in ordinals.setdefault(identity, set()),
                'Duplicate original component query ordinal')
        ordinals[identity].add(ordinal)
        wanted.add(query['source_id'])
        by_source.setdefault(query['source_id'], []).append(row)
        count += 1
    require(count == QUERIES and set(ordinals) <= mismatches and
            all(values == set(range(len(values))) for values in ordinals.values()),
            'Incomplete ordered native query/component bijection')
    return wanted, by_source, count


def headers(image, header_struct, *, member_bytes, expected_headers):
    """Scan EVERY original record header, including unrequested records."""
    result = {}
    offset = ordinal = 0
    while True:
        raw = image.read(header_struct.size)
        if not raw:
            break
        require(len(raw) == 44 == header_struct.size, 'Truncated original native header')
        values = header_struct.unpack(raw)
        identity, points, flag = values[:3]
        size = 44 + points * 8
        require(type(identity) is int and identity >= 0 and identity not in result and
                points >= 3 and 44 <= size <= FILE and offset + size <= member_bytes,
                'Duplicate, oversized or truncated original native record')
        result[identity] = (offset, size, ordinal, flag & 255, values[9])
        image.seek(size - 44, 1)
        offset += size
        ordinal += 1
    require(offset == member_bytes and ordinal == expected_headers,
            'Incomplete whole original native header/byte scope')
    return result


def closure(wanted, index):
    require(wanted <= set(index), 'Original ordered query source absent from full native member')
    complete = set(wanted)
    for identity in sorted(wanted):
        visited, current = set(), identity
        while index[current][3] in (2, 3, 4):
            if current in visited:
                break
            visited.add(current)
            parent = index[current][4]
            if parent not in index:
                break
            complete.add(parent)
            current = parent
    return complete


def record_rows(image, index, selected, by_source, comparison, query_bind, proof):
    """Literal decoder runs once per complete record; geometry is discarded."""
    for identity in sorted(selected):
        offset, size, ordinal, _, _ = index[identity]
        image.seek(offset)
        record = image.read(size)
        require(len(record) == size, 'Authenticated full native record truncated')
        meta, geometry = comparison.decode_record(record[:44], record[44:], ordinal, offset)
        require(meta['id'] == identity and meta['ordinal'] == ordinal and
                meta['native_offset'] == offset and meta['native_record_bytes'] == size and
                meta['record_sha256'] == sha(record), 'Literal native metadata/source binding differs')
        for query in by_source.get(identity, []):
            query_bind(query['query'], meta)
        alias = {'kind': 'complete-original-native-record-alias',
                 'member_sha256': proof['member_sha256'], 'record_ordinal': ordinal,
                 'byte_offset': offset, 'record_bytes': size, 'record_sha256': sha(record),
                 'pointset_binary64_sha256': meta['decoded_pointset_binary64_sha256'],
                 'decoder_original_commit': '104091cfecd9c83a53f3e6e62f95b0a0c8074351',
                 'decoder': 'literal comparison.decode_record; original GMT longitude conversion'}
        row = {'source_id': identity, 'complete_original_metadata': meta, 'alias': alias}
        require(len(canonical(row)) <= ROW_BYTES, 'Complete native metadata row exceeds admitted bound')
        del geometry, record
        yield row


def custody(phase, member_index_pin, part_pins, original_reader_pin, native_reader):
    original_reader = phase.read(original_reader_pin)
    executed_reader = Path(native_reader.__file__).read_bytes()
    require(original_reader == executed_reader, 'Literal no-ZIP native reader body differs')
    member = json.loads(phase.read(member_index_pin))
    declared = native_reader.member_index(member)
    require(len(part_pins) == len(declared) == 3 and
            len({(p['commit'], p['path']) for p in part_pins}) == 3,
            'Incomplete original native containing-file roster')
    mapping = {}
    for wanted, pin in zip(declared, part_pins):
        require(Path(pin['path']).name == wanted['path'] and
                all(pin[k] == wanted[k] for k in
                    ('bytes', 'sha256', 'uncompressed_bytes', 'uncompressed_sha256', 'ordinal', 'offset')),
                'Wrong original native containing-file/part binding')
        mapping[wanted['path']] = pin
    git_sources = native_reader.GitSources(phase.repo, part_pins)
    def get_encoded(request):
        require(request['path'] in mapping and request in declared,
                'Undeclared native original member request')
        pin = mapping[request['path']]
        # Phase.read admits/authenticates the decoded body too. The literal
        # immutable stream retrieves the same committed encoded body for the
        # accepted reader; no pathname or changing external getter is reused.
        phase.read(pin)
        body = b''.join(git_sources.stream(pin))
        require(len(body) == pin['bytes'] <= FILE and sha(body) == pin['sha256'],
                'Whole native encoded getter binding differs')
        return body
    return member, get_encoded, sha(executed_reader)


def acquire(phase, *, member_index_pin, part_pins, original_reader_pin,
            query_pins, mismatch_pins, query_join_publication_pin, query_join_inventory_pin,
            acquisition, native_reader, comparison, query_bind,
            project_guard, scratch_parent):
    """Real admitted full-source stage. Caller constructs Phase before this call.

    query_pins must be products of accepted whole-original physical restoration
    and full query join, not unauthenticated caller-selected IDs. Their complete
    descriptors and the mismatch products are actual declared stage inputs.
    """
    require(phase.reserve >= OUTPUT_RESERVE, 'Complete native output reserve was not admitted')
    project_guard()
    member, get_encoded, reader_sha = custody(phase, member_index_pin, part_pins,
                                                original_reader_pin, native_reader)
    wanted, by_source, query_count = scope(phase, query_pins, mismatch_pins)
    joined = acquisition.completed_inventory(phase, query_join_publication_pin, query_join_inventory_pin)
    joined_facts = joined['facts']
    require(joined_facts.get('operation') == 'complete-actual-native-query-join' and
            joined_facts.get('components') == COMPONENTS and
            joined_facts.get('ordered_queries') == QUERIES and
            joined_facts.get('contributing_source_ids') == sorted(wanted),
            'Missing complete actual original query/component join')
    joined_inputs = {phase.key(pin): pin for pin in joined['input_descriptors']}
    require(all(joined_inputs.get(phase.key(pin)) == pin for pin in [*query_pins, *mismatch_pins]),
            'Native query or mismatch product differs from actual complete join')
    joined_queries = {phase.key(pin) for pin in joined['input_descriptors']
                      if Path(pin['path']).name.startswith('native-query-index-')}
    require(joined_queries == {phase.key(pin) for pin in query_pins},
            'Omitted native query product from complete original join')
    del joined, joined_inputs, joined_queries
    def consume(image, proof):
        project_guard()
        require(proof['full_validation_before_consumer'] is True and
                proof['member_bytes'] == MEMBER_BYTES and proof['member_sha256'] == MEMBER_SHA256,
                'Full original native authentication must precede consumer')
        whole_headers = headers(image, comparison.HEADER, member_bytes=MEMBER_BYTES,
                                expected_headers=HEADERS)
        selected = closure(wanted, whole_headers)
        require(len(selected) == RECORDS, 'Complete original source/container closure differs')
        phase.rows('native-metadata', record_rows(image, whole_headers, selected, by_source,
                                                 comparison, query_bind, proof))
        facts = {'operation': 'complete-native-source-metadata-and-inverse-custody',
                 'member_bytes': MEMBER_BYTES, 'member_sha256': MEMBER_SHA256,
                 'complete_headers': HEADERS, 'complete_source_parent_records': len(selected),
                 'actual_requested_source_ids': sorted(wanted),
                 'complete_source_parent_ids': sorted(selected),
                 'actual_ordered_query_bindings': query_count, 'complete_mismatch_components': COMPONENTS,
                 'zero_query_components_preserved_by_complete_scope_join': True,
                 'literal_native_reader_sha256': reader_sha,
                 'literal_comparison_sha256': sha(Path(comparison.__file__).read_bytes()),
                 'original_native_proof': proof, 'complete_query_join_inventory_sha256': query_join_inventory_pin['sha256'],
                 'alias_kind': 'whole original source inverse; not geometry output',
                 'limits': ['Numerical consumers must independently authenticate full original source before decoding their complete cohort.',
                            'No new geography, water classification or political affiliation is authorized.']}
        del whole_headers, selected
        return facts
    facts = native_reader.consume_native(member, get_encoded, consume, scratch_parent)
    project_guard()
    del wanted, by_source
    return phase.finish(facts)


def consume_cohort(phase, *, member_index_pin, part_pins, original_reader_pin,
                   cohort_pins, cohort_publication_pin, cohort_inventory_pin,
                   acquisition, native_reader, comparison, query_bind,
                   project_guard, scratch_parent, consumer):
    """Full native source before literal numerical consumer, inside one real phase.

    The numerical consumer receives complete needed original geometries only
    during the accepted authenticated-image callback. It writes results through
    the already admitted phase budget; no record/image dictionary escapes this
    stage. The caller owns actual output writing and complete receipt publication
    after this returns facts; this function never writes a completion receipt.
    """
    project_guard()
    inventory = acquisition.completed_inventory(phase, cohort_publication_pin, cohort_inventory_pin)
    facts = inventory['facts']
    require(facts.get('operation') == 'complete-original-numerical-cohort-acquisition',
            'Wrong whole cohort acquisition authority')
    declared = {phase.key(pin): pin for pin in inventory['outputs']}
    require(cohort_pins and all(phase.key(pin) in declared and declared[phase.key(pin)] == pin
                               for pin in cohort_pins), 'Cohort products absent from whole acquisition inventory')
    expected_products = [pin for pin in inventory['outputs']
                         if Path(pin['path']).name.startswith('complete-cohort-operands-')]
    require({phase.key(pin) for pin in cohort_pins} == {phase.key(pin) for pin in expected_products},
            'Omitted whole numerical cohort operand product')
    operands, wanted, by_source, queries = [], set(), {}, 0
    identities = set()
    for row in rows(phase, cohort_pins):
        identity = row['id']
        require(type(identity) is str and identity not in identities and
                row['candidate']['id'] == identity and row['physical']['component_id'] == identity and
                row['diagnosis']['component_id'] == identity,
                'Duplicate or wrong complete native cohort component')
        identities.add(identity)
        operands.append(row)
        for ordinal, query in enumerate(row['physical']['query_relations']):
            require(type(query['source_id']) is int and query['source_id'] >= 0,
                    'Wrong cohort original native source identity')
            wanted.add(query['source_id'])
            by_source.setdefault(query['source_id'], []).append(
                {'component_id': identity, 'query_ordinal': ordinal, 'query': query})
            queries += 1
    require(identities and sorted(identities) == facts['component_ids'] and
            queries == facts['ordered_queries'] and sorted(wanted) == facts['wanted_native_ids'],
            'Incomplete whole cohort native/query inventory')
    member, get_encoded, reader_sha = custody(phase, member_index_pin, part_pins,
                                              original_reader_pin, native_reader)
    def consume(image, proof):
        project_guard()
        require(proof['full_validation_before_consumer'] is True and
                proof['member_bytes'] == MEMBER_BYTES and proof['member_sha256'] == MEMBER_SHA256,
                'Full native source must precede numerical cohort')
        whole_headers = headers(image, comparison.HEADER, member_bytes=MEMBER_BYTES,
                                expected_headers=HEADERS)
        selected = closure(wanted, whole_headers)
        records, aliases = {}, {}
        for identity in sorted(selected):
            offset, size, ordinal, _, _ = whole_headers[identity]
            image.seek(offset)
            body = image.read(size)
            require(len(body) == size, 'Complete cohort native record truncated')
            meta, geometry = comparison.decode_record(body[:44], body[44:], ordinal, offset)
            require(meta['id'] == identity and meta['record_sha256'] == sha(body),
                    'Actual cohort native identity/body binding differs')
            for query in by_source.get(identity, []):
                query_bind(query['query'], meta)
            records[identity] = (meta, geometry)
            aliases[identity] = {'kind': 'complete-original-native-record-alias',
                'member_sha256': proof['member_sha256'], 'record_ordinal': ordinal,
                'byte_offset': offset, 'record_bytes': size, 'record_sha256': sha(body),
                'pointset_binary64_sha256': meta['decoded_pointset_binary64_sha256'],
                'decoder_original_commit': '104091cfecd9c83a53f3e6e62f95b0a0c8074351',
                'decoder': 'literal comparison.decode_record; original GMT longitude conversion'}
            del body
        native_proof = dict(proof, complete_headers=HEADERS, contributing_ids=sorted(wanted),
                            complete_parent_closure_ids=sorted(selected))
        del whole_headers
        consumer(phase, operands, records, aliases, native_proof)
        project_guard()
        result = {'operation': 'complete-native-backed-numerical-cohort',
                  'component_ids': sorted(identities), 'ordered_queries': queries,
                  'complete_headers': HEADERS, 'full_native_source_before_consumer': True,
                  'needed_parent_source_ids': sorted(selected), 'native_source_proof': proof,
                  'literal_native_reader_sha256': reader_sha,
                  'cohort_inventory_sha256': cohort_inventory_pin['sha256']}
        del records, aliases, selected
        return result
    result = native_reader.consume_native(member, get_encoded, consume, scratch_parent)
    project_guard()
    del operands, wanted, by_source, identities
    return result
