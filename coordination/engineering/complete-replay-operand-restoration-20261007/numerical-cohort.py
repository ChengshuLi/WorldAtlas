"""Bounded bridge to the unchanged complete nine-map replay and object writer.

The caller authenticates a full native image and all cohort inputs before this
consumer. This module changes acquisition and output admission only. Each cohort
keeps all original query objects and unknowns. Campaign completion still requires
the complete, duplicate-free 1,294-subject reconciliation and two full runs.
"""
from collections import Counter
import gzip
import hashlib
import io
import json
import re


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False) + '\n').encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(body, compress):
    if not compress:
        return body
    buffer = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=buffer, mtime=0, compresslevel=9) as stream:
        stream.write(body)
    return buffer.getvalue()


class BudgetedProducts:
    """Keep literal Products' files readable by unchanged inverse-object checks.

    All real outputs are checked against encoded AND decoded stage admission
    before the literal writer mutates its exclusive directory. No second output
    copy is created. Inventory and completion receipt remain separately reserved.
    """
    def __init__(self, phase, literal_products, acquisition, *, metadata_reserve=1048576):
        acquisition.require(type(metadata_reserve) is int and metadata_reserve > 0 and
                            phase.reserve >= metadata_reserve and not phase.payloads,
                            'Numerical metadata reserve required')
        acquisition.require(phase.reads == set(phase.pins),
                            'All declared numerical inputs must authenticate before output creation')
        self.phase, self.acquisition = phase, acquisition
        self.metadata_reserve = metadata_reserve
        inputs = [dict(p, commit=p.get('commit')) for p in phase.pins.values()]
        self.actual = literal_products.Products(phase.destination, inputs, repo=phase.repo)
        acquisition.require(type(self.actual) is literal_products.Products and
                            self.actual.write.__func__ is literal_products.Products.write,
                            'Actual literal product class/writer identity differs')
        self.literal_write = self.actual.write
        self.actual.write = self.write

    @property
    def directory(self):
        return self.actual.directory

    @property
    def buffers(self):
        return self.actual.buffers

    @property
    def ordinals(self):
        return self.actual.ordinals

    @property
    def outputs(self):
        return self.actual.outputs

    def write(self, name, body, compress=False):
        self.acquisition.require(name not in ('stage-inventory.json.gz', 'publication.json'),
                                 'Numerical output collides with reserved completion name')
        self.acquisition.require(type(body) is bytes and len(body) <= self.acquisition.FILE,
                                 'Whole numerical output decoded bound')
        raw = encoded(body, compress)
        output_cost = len(raw) + (len(body) if compress else 0)
        used = sum(p['bytes'] + p.get('uncompressed_bytes', 0) for p in self.outputs)
        self.acquisition.require(len(raw) <= self.acquisition.FILE and
                                 used + output_cost + self.metadata_reserve <= self.phase.reserve,
                                 'Complete numerical outputs exceed admitted reserve')
        pin = self.literal_write(name, body, compress=compress)
        self.acquisition.require(pin['bytes'] == len(raw) and pin['sha256'] == digest(raw),
                                 'Actual literal numerical output differs')
        return pin

    def emit(self, kind, row):
        # Decoded pending buffers are unavoidable output cost, even before their
        # exact compressed costs are known. Reject an impossible reserve before
        # the unchanged emitter appends; do not recompress buffers on every row.
        raw = canonical(row)
        used = sum(p['bytes'] + p.get('uncompressed_bytes', 0) for p in self.outputs)
        pending = sum(len(body) for body in self.buffers.values())
        self.acquisition.require(used + pending + len(raw) + self.metadata_reserve <= self.phase.reserve,
                                 'Pending decoded numerical outputs exceed admitted reserve')
        return self.actual.emit(kind, row)

    def finish(self):
        return self.actual.finish()


def bounded_objects(objects_module, products, loaded, records, native_aliases):
    """Initialize the unchanged literal object class with shorter scratch lifetime.

    Every index selector and complete expected-versus-reconstructed byte check
    is preserved; non-native resolution and recursive retention remain literal.
    Native mapping serialization avoids the redundant JSON-to-list graph.
    Scientific replay still uses the original kernel and literal methods.
    """
    objects_module.require(objects_module.Objects.__new__ is object.__new__,
                           'Original Objects allocation binding differs')
    self = objects_module.Objects.__new__(objects_module.Objects)
    self.products, self.loaded, self.records = products, loaded, records
    self.native_aliases = native_aliases
    self.verified_aliases = {}
    self.native = {}
    self.component = {}
    self.emitted = {}
    self.kernel = loaded['modules']['kernel']
    literal_resolved_bytes = self._resolved_bytes
    literal_mapping = self.kernel.mapping
    def check_resolution_binding():
        objects_module.require(self._resolved_bytes is resolved_bytes and
                               literal_resolved_bytes.__self__ is self and
                               literal_resolved_bytes.__func__ is objects_module.Objects._resolved_bytes and
                               self.kernel.mapping is literal_mapping,
                               'Original native inverse callable binding differs')
    def resolved_bytes(alias):
        check_resolution_binding()
        if alias['kind'] != 'complete-native-record-geometry':
            raw = literal_resolved_bytes(alias)
            check_resolution_binding()
            return raw
        identity, offset = alias['source_id'], alias['periodic_offset']
        objects_module.require(type(identity) is int and type(offset) in (int, float) and
                               offset in (-360, 0, 360), 'Bad native inverse alias identity/frame')
        objects_module.require(alias['original_native_record'] == self.native_aliases[identity],
                               'Native inverse alias record binding differs')
        geometry = self.records[identity][1]
        shifted = objects_module.translate(geometry, xoff=offset) if offset else geometry
        # JSON canonical bytes are identical for tuples and their decoded lists.
        # Avoid retaining a second complete coordinate graph during verification.
        raw = objects_module.canonical(literal_mapping(shifted))
        objects_module.require(len(raw) == alias['whole_mapping_bytes'] and
                               objects_module.sha(raw) == alias['whole_mapping_sha256'],
                               'Complete inverse alias reconstructed bytes differ')
        check_resolution_binding()
        return raw
    self._resolved_bytes = resolved_bytes
    wanted = {(q['source_id'], q['periodic_offset']) for row, pin in
              loaded['physical'].values() for q in row['query_relations']}
    for identity, offset in sorted(wanted):
        check_resolution_binding()
        geometry = records[identity][1]
        if geometry is None:
            continue
        shifted = objects_module.translate(geometry, xoff=offset) if offset else geometry
        raw = objects_module.canonical(literal_mapping(shifted))
        key = objects_module.sha(raw)
        alias = {'kind': 'complete-native-record-geometry', 'source_id': identity,
                 'periodic_offset': offset, 'original_native_record': native_aliases[identity],
                 'decoder': 'literal original comparison.decode_record then original periodic translate',
                 'whole_mapping_bytes': len(raw), 'whole_mapping_sha256': key}
        self.verify_alias(alias, raw)
        # The digest is a lookup index only. Every selected alias is resolved
        # and compared with complete canonical bytes before use.
        self.native.setdefault(key, []).append(alias)
        # Reconstruction was checked in full above; native index retains only
        # selectors/pins. Do not keep a second full source serialization.
        self.verified_aliases.clear()
        del raw, geometry, shifted
    # The literal recursive retain remains the only inverse/object writer.
    # Drop completed validation bodies before the next sibling; selectors,
    # component indexes, emitted full bodies and inverse checks stay unchanged.
    literal_retain = self.retain
    def retain(value):
        objects_module.require(self.retain is retain and
                               literal_retain.__self__ is self and
                               literal_retain.__func__ is objects_module.Objects.retain,
                               'Literal recursive retain binding differs')
        answer = literal_retain(value)
        objects_module.require(self.retain is retain and
                               literal_retain.__self__ is self and
                               literal_retain.__func__ is objects_module.Objects.retain,
                               'Literal recursive retain binding changed')
        self.verified_aliases.clear()
        return answer
    self.retain = retain
    return self


def replay(phase, operands, records, native_aliases, native_proof, *, acquisition,
           literal_products, objects_module, replay_module, scientific_modules,
           query_bind, project_guard):
    """Run INSIDE the already authenticated native-reader consumer callback."""
    project_guard()
    subjects = acquisition.exact_ids(operands, 'id')
    candidates = {}; physical = {}; diagnoses = {}; routing = {}
    for identity, row in subjects.items():
        acquisition.require(row['candidate']['id'] == row['physical']['component_id'] ==
                            row['diagnosis']['component_id'] == identity and
                            row['diagnosis']['status'] == 'original-replay-mismatch',
                            'Complete actual numerical cohort identity differs')
        candidates[identity] = row['candidate']; physical[identity] = (row['physical'], row['physical_alias'])
        diagnoses[identity] = row['diagnosis']; routing[identity] = row['routing']
        for query in row['physical']['query_relations']:
            acquisition.require(query['source_id'] in records, 'Missing whole native query operand')
            query_bind(query, records[query['source_id']][0])
    loaded = dict(state=dict(candidates=candidates, routing=routing), physical=physical,
                  diagnoses=diagnoses, modules=scientific_modules)
    products = BudgetedProducts(phase, literal_products, acquisition)
    objects = bounded_objects(objects_module, products, loaded, records, native_aliases)
    counts, queries = Counter(), 0
    for identity in sorted(subjects):
        validity = scientific_modules['comparison'].ValidityCache()
        shifted = {}
        objects.begin(identity)
        result = replay_module.execute(identity, loaded, records, validity, shifted)
        acquisition.require(result['component_id'] == identity and
                            result['original_query_count'] == len(physical[identity][0]['query_relations']),
                            'Original numerical query accounting differs')
        result.update(complete_original_candidate=objects.alias('candidate', identity, [], candidates[identity]),
                      complete_original_physical_row=objects.alias('physical', identity, [], physical[identity][0]),
                      complete_original_diagnosis=objects.alias('diagnosis', identity, [], diagnoses[identity]))
        products.emit('components', objects.retain(result))
        queries += result['original_query_count']; counts[result['status']] += 1
        # Cache lifetime is one complete component; no scientific query/result
        # or geometry is omitted. Do not retain prior result during the next call.
        del result, validity, shifted
    outputs = products.finish()
    acquisition.require(sum(counts.values()) == len(subjects), 'Incomplete numerical cohort')
    project_guard()
    return dict(operation='complete-original-nine-map-numerical-cohort',
                component_ids=sorted(subjects), original_ordered_queries=queries,
                statuses=dict(sorted(counts.items())), native=native_proof,
                outputs=outputs, limits=['One complete admitted cohort; not complete campaign acceptance.',
                                        'Unknowns remain unknown; no repair or physical/political approval.'])


def complete(phase, facts, acquisition):
    """Equivalent receipt-last completion after the literal product writer.

    The existing completed_inventory reader validates this same stage envelope.
    Actual files are read back again and the complete encoded/decoded inventory,
    receipt and descriptor costs enter admission before completion is published.
    """
    acquisition.require(phase.reads == set(phase.pins) and not phase.payloads,
                        'Declared numerical input was not actually consumed')
    acquisition.require(type(facts['outputs']) is list and facts['outputs'],
                        'Missing complete numerical outputs')
    names = []
    for p in facts['outputs']:
        name = p.get('path')
        acquisition.require(type(name) is str and re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9._-]*', name) is not None,
                            'Numerical output must be one ordinary relative filename')
        acquisition.require(name not in ('stage-inventory.json.gz', 'publication.json'),
                            'Numerical output collides with reserved completion name')
        acquisition.bounds(p)
        names.append(name)
    acquisition.require(len(names) == len(set(names)), 'Duplicate complete numerical output filename')
    destination = acquisition.ordinary(phase.destination)
    acquisition.require(destination.is_dir() and {p.name for p in destination.iterdir()} == set(names),
                        'Foreign numerical output file')
    outputs = []
    for p in facts['outputs']:
        pin = dict(p, path=str(destination / p['path']))
        path = acquisition.ordinary(pin['path'])
        acquisition.require(path.is_file(), 'Missing ordinary numerical output file')
        with path.open('rb') as stream:
            actual = stream.read(pin['bytes'] + 1)
        acquisition.decode(actual, pin)
        outputs.append(pin)
    output_cost = sum(acquisition.cost(p) for p in outputs)
    inventory = dict(version=1, kind='bounded-original-acquisition-stage', facts=facts,
                     input_descriptors=list(phase.pins.values()), outputs=outputs,
                     input_encoded_decoded_bytes=phase.input_bytes, runtime_bytes=phase.runtime_bytes,
                     output_encoded_decoded_bytes=output_cost,
                     complete_phase_bytes=phase.input_bytes + phase.runtime_bytes + output_cost)
    body = canonical(inventory); raw = encoded(body, True)
    inventory_pin = dict(path=str(phase.destination/'stage-inventory.json.gz'), bytes=len(raw),
                         sha256=digest(raw), uncompressed_bytes=len(body), uncompressed_sha256=digest(body))
    acquisition.bounds(inventory_pin)
    total = inventory['complete_phase_bytes'] + acquisition.cost(inventory_pin) + acquisition.RECEIPT
    acquisition.require(output_cost + acquisition.cost(inventory_pin) <= phase.reserve and
                        total <= acquisition.PHASE and len(phase.pins) + len(outputs) + 2 <= 512,
                        'Actual complete numerical stage exceeds admission')
    final = dict(version=1, inventory=inventory_pin, complete_phase_bytes=total, complete=True)
    receipt = canonical(final)
    acquisition.require(len(receipt) <= acquisition.RECEIPT, 'Numerical receipt bound')
    expected_names = {p['path'].rsplit('/', 1)[-1] for p in outputs}
    acquisition.require({p.name for p in phase.destination.iterdir()} == expected_names,
                        'Foreign numerical output file')
    for name, payload in [('stage-inventory.json.gz', raw), ('publication.json', receipt)]:
        with (phase.destination/name).open('xb') as stream:
            stream.write(payload)
        with (phase.destination/name).open('rb') as stream:
            actual = stream.read(len(payload) + 1)
        acquisition.require(actual == payload, 'Whole numerical completion readback differs')
    return final
