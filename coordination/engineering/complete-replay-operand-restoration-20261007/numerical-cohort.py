"""Bounded bridge to the unchanged complete nine-map replay and object writer.

The caller authenticates a full native image and all cohort inputs before this
consumer. This module changes acquisition, temporary serialization lifetime and
output admission only. Each cohort
keeps all original query objects and unknowns. Campaign completion still requires
the complete, duplicate-free 1,294-subject reconciliation and two full runs.
"""
from collections import Counter
import gzip
import hashlib
import io
import json
import re
from types import FunctionType, SimpleNamespace
import weakref
from shapely.geometry.base import BaseGeometry


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


"""Adapter-only eviction; unchanged original checks recompute on every miss."""

def bounded_replay_caches(comparison):
    def cache_require(condition, message):
        if not condition:
            raise ValueError(message)
    literal_class = comparison.ValidityCache
    literal_init, literal_check = (literal_class.__init__, literal_class.check)
    init_code, check_code = (literal_init.__code__, literal_check.__code__)
    init_defaults, check_defaults = (literal_init.__defaults__, literal_check.__defaults__)

    def binding():
        cache_require(comparison.ValidityCache is literal_class, 'Bounded original replay cache binding/type differs')
        cache_require(literal_class.__init__ is literal_init and literal_class.check is literal_check, 'Bounded original replay cache binding/type differs')
        cache_require(literal_init.__code__ is init_code and literal_check.__code__ is check_code, 'Bounded original replay cache binding/type differs')
        cache_require(literal_init.__defaults__ == init_defaults and literal_check.__defaults__ == check_defaults, 'Bounded original replay cache binding/type differs')

    class OneEntry(dict):

        def __init__(self, kind):
            super().__init__()
            self.kind = kind

        def __contains__(self, key):
            binding()
            found = dict.__contains__(self, key)
            if not found:
                dict.clear(self)
            return found

        def get(self, key, default=None):
            binding()
            if not dict.__contains__(self, key):
                dict.clear(self)
            return dict.get(self, key, default)

        def __setitem__(self, key, value):
            binding()
            if self.kind == 'shift':
                cache_require(type(key) is tuple and len(key) == 2 and (type(key[0]) is int), 'Bounded original replay cache binding/type differs')
                cache_require(type(key[1]) in (int, float) and key[1] in (-360, 0, 360), 'Bounded original replay cache binding/type differs')
                cache_require(isinstance(value, BaseGeometry), 'Bounded original replay cache binding/type differs')
            else:
                cache_require(self.kind == 'validity' and type(key) is int, 'Bounded original replay cache binding/type differs')
                cache_require(type(value) is tuple and len(value) == 2, 'Bounded original replay cache binding/type differs')
                cache_require(isinstance(value[0], BaseGeometry) and key == id(value[0]) and (type(value[1]) is bool), 'Bounded original replay cache binding/type differs')
            if key not in self:
                self.clear()
            super().__setitem__(key, value)
            cache_require(len(self) <= 1, 'Bounded original replay cache binding/type differs')

    class BoundedValidity(literal_class):

        def __init__(self):
            binding()
            literal_init(self)
            cache_require(type(self._rows) is dict and (not self._rows), 'Bounded original replay cache binding/type differs')
            self._rows = OneEntry('validity')

        def check(self, geometry):
            binding()
            cache_require(type(self._rows) is OneEntry and self._rows.kind == 'validity', 'Bounded original replay cache binding/type differs')
            cache_require(isinstance(geometry, BaseGeometry), 'Bounded original replay cache binding/type differs')
            answer = literal_check(self, geometry)
            binding()
            cache_require(type(self._rows) is OneEntry and len(self._rows) <= 1, 'Bounded original replay cache binding/type differs')
            cache_require(type(answer) is bool, 'Bounded original replay cache binding/type differs')
            return answer
    binding()
    return (BoundedValidity(), OneEntry('shift'))

def bounded_fresh_queries(trace, kernel, require):
    """Share an identical immutable-source mapping inside literal query code.

    At zero offset the literal source and shifted source are the same GEOS
    object. Serializing both into separate coordinate lists needlessly doubles
    their retained size. One weak-identity entry avoids that second graph; a
    distinct geometry still runs the complete unchanged original serializer.
    Original module globals are never changed, and the memo ends with the call.
    """
    original, serialize = trace.fresh_queries, kernel.ordinary_mapping
    code, defaults, closure = original.__code__, original.__defaults__, original.__closure__
    serialize_code, serialize_defaults = serialize.__code__, serialize.__defaults__
    serialize_closure = serialize.__closure__
    original_globals = dict(original.__globals__)
    serialize_globals = dict(serialize.__globals__)

    def binding():
        require(trace.fresh_queries is original and original.__code__ is code and
                original.__defaults__ == defaults and original.__closure__ is closure,
                'Original fresh query callable changed')
        require(kernel.ordinary_mapping is serialize and serialize.__code__ is serialize_code and
                serialize.__defaults__ == serialize_defaults and
                serialize.__closure__ is serialize_closure,
                'Original complete mapping callable changed')
        for function, expected in ((original, original_globals), (serialize, serialize_globals)):
            require(set(function.__globals__) == set(expected) and
                    all(function.__globals__[key] is value for key, value in expected.items()),
                    'Original query or mapping globals changed')

    def fresh_queries(*args, **kwargs):
        binding()
        last_ref, last_value = None, None

        def mapping(geometry):
            nonlocal last_ref, last_value
            binding()
            require(isinstance(geometry, BaseGeometry), 'Original query geometry type differs')
            if last_ref is not None and last_ref() is geometry:
                return last_value
            # Evict before allocating the next complete coordinate graph.
            last_ref, last_value = None, None
            value = serialize(geometry)
            binding()
            last_ref, last_value = weakref.ref(geometry), value
            return value

        proxy = SimpleNamespace(**vars(kernel))
        proxy.ordinary_mapping = mapping
        globals_copy = dict(original_globals)
        globals_copy['kernel'] = proxy
        literal = FunctionType(code, globals_copy, original.__name__, defaults, closure)
        try:
            answer = literal(*args, **kwargs)
            binding()
            return answer
        finally:
            last_ref, last_value = None, None

    binding()
    return fresh_queries


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
    # The literal replay consumes this local trace proxy. All original modules,
    # methods and their guarded globals remain intact for project_guard().
    trace = SimpleNamespace(**vars(scientific_modules['trace']))
    trace.fresh_queries = bounded_fresh_queries(scientific_modules['trace'],
                                               scientific_modules['kernel'], acquisition.require)
    execution_modules = dict(scientific_modules, trace=trace)
    loaded = dict(state=dict(candidates=candidates, routing=routing), physical=physical,
                  diagnoses=diagnoses, modules=execution_modules)
    products = BudgetedProducts(phase, literal_products, acquisition)
    objects = bounded_objects(objects_module, products, loaded, records, native_aliases)
    counts, queries = Counter(), 0
    for identity in sorted(subjects):
        validity, shifted = bounded_replay_caches(scientific_modules['comparison'])
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
