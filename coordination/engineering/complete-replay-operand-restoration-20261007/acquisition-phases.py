"""Detached, bounded acquisition jobs for the original complete replay.

The caller supplies authenticated literal legacy modules and frozen descriptors.
Each job returns only an ordinary receipt. No geometry or global source dictionary
is returned across a job boundary. Scratch products are actual inputs to later jobs,
and are inventoried even when final delivery uses original-source inverse aliases.
This adapter does not run replay operators or grant a complete-run PASS.
"""
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import types

FILE = 33554432
PHASE = 268435456
RECEIPT = 4096
SHARD = 8388608


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ordinary(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'Absolute ordinary path required')
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Symlink input/destination')
    return path


def bounds(pin):
    for key in ('bytes', 'uncompressed_bytes') if 'uncompressed_bytes' in pin else ('bytes',):
        require(type(pin.get(key)) is int and 0 <= pin[key] <= FILE, 'Ordinary file bound')
    for key in ('sha256', 'uncompressed_sha256') if 'uncompressed_bytes' in pin else ('sha256',):
        require(re.fullmatch('[a-f0-9]{64}', pin.get(key, '')) is not None, 'Whole file digest required')


def cost(pin):
    bounds(pin)
    return pin['bytes'] + pin.get('uncompressed_bytes', 0)


def decode(raw, pin):
    bounds(pin)
    require(len(raw) == pin['bytes'] and sha(raw) == pin['sha256'], 'Whole encoded input differs')
    if 'uncompressed_bytes' not in pin:
        return raw
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        body = stream.read(pin['uncompressed_bytes'] + 1)
        require(not stream.read(1), 'Trailing decoded bytes')
    require(len(body) == pin['uncompressed_bytes'] and sha(body) == pin['uncompressed_sha256'],
            'Whole decoded input differs')
    return body


class Phase:
    """Reviewed-equivalent whole-file boundary with complete prospective accounting.

    runtime_bytes is a mandatory conservative charge for actual executed installed
    bodies; project pins are separate actual inputs. It must come from the frozen
    runtime guard, never from an arbitrary budget selected by a CLI user.
    """
    def __init__(self, repo, destination, pins, *, runtime_bytes, output_reserve,
                 runtime_verified, project_pins=()):
        self.repo = ordinary(repo).resolve()
        self.destination = ordinary(destination)
        require(self.destination.resolve().is_relative_to(self.repo / '.cache'), 'Escaped owned scratch')
        require(self.destination.parent.is_dir() and not self.destination.exists(), 'Fresh exclusive destination required')
        require(runtime_verified is True and type(runtime_bytes) is int and runtime_bytes > 0,
                'Frozen actual runtime admission required')
        require(type(output_reserve) is int and output_reserve >= 0, 'Prospective output reserve required')
        self.pins = {}
        for pin in [*pins, *project_pins]:
            bounds(pin)
            key = self.key(pin)
            require(key not in self.pins, 'Duplicate phase input descriptor')
            self.pins[key] = dict(pin)
        self.runtime_bytes = runtime_bytes
        self.input_bytes = sum(cost(p) for p in self.pins.values())
        self.reserve = output_reserve
        require(self.input_bytes + runtime_bytes + output_reserve + RECEIPT <= PHASE,
                'Complete prospective phase exceeds encoded/decoded/runtime/output bound')
        require(len(self.pins) < 512, 'Phase descriptor bound')
        self.reads = set()
        self.payloads = {}
        for pin in project_pins:
            self.read(pin)

    @staticmethod
    def key(pin):
        return (pin.get('commit'), pin['path'])

    def read(self, pin):
        key = self.key(pin)
        require(key in self.pins and self.pins[key] == pin, 'Undeclared or changed whole input')
        if pin.get('commit'):
            require(re.fullmatch('[a-f0-9]{40}', pin['commit']) is not None, 'Immutable commit required')
            require(type(pin['path']) is str and not pin['path'].startswith('/') and
                    all(s not in ('', '.', '..') for s in pin['path'].split('/')) and
                    '\\' not in pin['path'], 'Unsafe original path')
            row = subprocess.check_output(['git', '-C', str(self.repo), 'ls-tree', '-z',
                                            pin['commit'], '--', pin['path']]).decode().rstrip('\0')
            require('\t' in row, 'Missing exact original source')
            meta, name = row.split('\t'); mode, kind, blob = meta.split()
            require(name == pin['path'] and mode in ('100644', '100755') and kind == 'blob',
                    'Nonordinary original source')
            require(pin.get('mode', mode) == mode and pin.get('blob', blob) == blob,
                    'Original whole mode/OID differs')
            require(int(subprocess.check_output(['git', '-C', str(self.repo), 'cat-file', '-s', blob])) == pin['bytes'],
                    'Original source actual size differs')
            raw = subprocess.check_output(['git', '-C', str(self.repo), 'cat-file', 'blob', blob])
        else:
            path = ordinary(pin['path'])
            require(path.resolve().is_relative_to(self.repo / '.cache') and path.is_file(), 'Nonordinary stage input')
            with path.open('rb') as stream:
                raw = stream.read(pin['bytes'] + 1)
        body = decode(raw, pin)
        self.reads.add(key)
        return body

    def output(self, name, body, *, compress=False, encoded=None):
        require(re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9._-]*', name) is not None and name not in self.payloads,
                'Unsafe/duplicate stage output')
        require(type(body) is bytes and len(body) <= FILE, 'Complete output file bound')
        require(encoded is None or compress, 'Encoded override requires actual decoded admission')
        raw = encoded if encoded is not None else gzip.compress(body, compresslevel=9, mtime=0) if compress else body
        if encoded is not None:
            require(type(encoded) is bytes and gzip.decompress(encoded) == body, 'Whole supplied gzip differs')
        require(len(raw) <= FILE, 'Encoded output file bound')
        pin = {'path': str(self.destination / name), 'bytes': len(raw), 'sha256': sha(raw)}
        if compress:
            pin.update(uncompressed_bytes=len(body), uncompressed_sha256=sha(body))
        require(sum(cost(p) for p, _ in self.payloads.values()) + cost(pin) <= self.reserve,
                'Actual stage outputs exceed prospective reserve')
        self.payloads[name] = (pin, raw)
        return pin

    def rows(self, name, rows):
        buffer = bytearray(); ordinal = 0; pins = []
        for row in rows:
            raw = canonical(row)
            require(len(raw) <= FILE, 'Complete intermediate row bound')
            if buffer and len(buffer) + len(raw) > SHARD:
                pins.append(self.output(f'{name}-{ordinal:03}.jsonl.gz', bytes(buffer), compress=True))
                buffer.clear(); ordinal += 1
            buffer.extend(raw)
        if buffer:
            pins.append(self.output(f'{name}-{ordinal:03}.jsonl.gz', bytes(buffer), compress=True))
        return pins

    def finish(self, facts):
        require(self.reads == set(self.pins), 'Declared whole input was not actually consumed')
        pins = [p for p, _ in self.payloads.values()]
        require(len(self.pins) + len(pins) + 1 <= 512, 'Complete stage descriptor bound')
        receipt = {'version': 1, 'kind': 'bounded-original-acquisition-stage', 'facts': facts,
                   'input_descriptors': list(self.pins.values()), 'outputs': pins,
                   'input_encoded_decoded_bytes': self.input_bytes, 'runtime_bytes': self.runtime_bytes,
                   'output_encoded_decoded_bytes': sum(cost(p) for p in pins),
                   'complete_phase_bytes': self.input_bytes + self.runtime_bytes + sum(cost(p) for p in pins)}
        # Large input inventories are real products, not oversized completion receipts.
        inventory = canonical(receipt)
        self.output('stage-inventory.json.gz', inventory, compress=True)
        final = {'version': 1, 'inventory': self.payloads['stage-inventory.json.gz'][0],
                 'complete_phase_bytes': self.input_bytes + self.runtime_bytes +
                    sum(cost(p) for p, _ in self.payloads.values()) + RECEIPT,
                 'complete': True}
        raw = canonical(final)
        require(len(raw) <= RECEIPT and final['complete_phase_bytes'] <= PHASE, 'Complete receipt bound')
        require(len(self.pins) + len(self.payloads) + 1 <= 512, 'Complete stage descriptor bound')
        self.destination.mkdir(exist_ok=False)
        for name, (pin, payload) in self.payloads.items():
            with (self.destination / name).open('xb') as stream:
                stream.write(payload)
            require((self.destination / name).read_bytes() == payload, 'Whole output readback differs')
        with (self.destination / 'publication.json').open('xb') as stream:
            stream.write(raw)
        self.payloads.clear()
        return final


def source_groups(pins, *, runtime_bytes, project_pins=(), output_reserve=1048576):
    """Plan every original whole body, including metadata and operand snapshot."""
    seen = set(); groups = []; group = []
    used = runtime_bytes + sum(cost(p) for p in project_pins) + output_reserve + RECEIPT
    floor = used
    for pin in pins:
        require(Phase.key(pin) not in seen, 'Duplicate original source roster')
        seen.add(Phase.key(pin))
        require(floor + cost(pin) <= PHASE, 'One original source cannot fit phase')
        if used + cost(pin) > PHASE:
            groups.append(group); group = []; used = floor
        group.append(pin); used += cost(pin)
    if group:
        groups.append(group)
    return groups


def authenticate(phase):
    for pin in phase.pins.values():
        phase.read(pin)
    return phase.finish({'operation': 'whole-source-authentication', 'sources': len(phase.pins)})


def completed_inventory(phase, publication_pin, inventory_pin):
    receipt = json.loads(phase.read(publication_pin))
    require(receipt.get('complete') is True and receipt.get('version') == 1 and
            receipt.get('inventory') == inventory_pin, 'Missing/changed real stage completion')
    inventory = json.loads(phase.read(inventory_pin))
    require(inventory.get('kind') == 'bounded-original-acquisition-stage', 'Wrong actual stage inventory')
    inputs = inventory['input_descriptors']; outputs = inventory['outputs']
    require(len({Phase.key(p) for p in inputs}) == len(inputs) and
            len({p['path'] for p in outputs}) == len(outputs) and len(inputs) + len(outputs) + 2 <= 512,
            'Duplicate/overbound complete stage inventory')
    require(sum(cost(p) for p in inputs) == inventory['input_encoded_decoded_bytes'] and
            sum(cost(p) for p in outputs) == inventory['output_encoded_decoded_bytes'] and
            inventory['input_encoded_decoded_bytes'] + inventory['runtime_bytes'] +
            inventory['output_encoded_decoded_bytes'] == inventory['complete_phase_bytes'] and
            inventory['complete_phase_bytes'] + cost(inventory_pin) + RECEIPT == receipt['complete_phase_bytes'] <= PHASE,
            'Actual complete stage accounting differs')
    return inventory


def reconcile_sources(phase, source_index_pin, stage_pairs):
    index = json.loads(phase.read(source_index_pin))
    originals = index['files']
    require(len(originals) == 202 and sum(p['bytes'] for p in originals) == 232466132,
            'Complete frozen original source roster differs')
    expected = {Phase.key(p): p for p in originals}
    require(len(expected) == 202, 'Duplicate frozen original source')
    seen = set()
    for publication_pin, inventory_pin in stage_pairs:
        inventory = completed_inventory(phase, publication_pin, inventory_pin)
        require(inventory['kind'] == 'bounded-original-acquisition-stage' and
                inventory['facts']['operation'] == 'whole-source-authentication',
                'Wrong actual whole-source authentication stage')
        for actual in inventory['input_descriptors']:
            key = Phase.key(actual)
            if key not in expected:
                continue  # Its executed project closure is independently frozen.
            require(key not in seen and actual == expected[key], 'Duplicate/changed actual source authentication')
            seen.add(key)
    require(seen == set(expected), 'Missing complete original authenticated whole source')
    return phase.finish({'operation': 'complete-original-source-authentication-reconciliation',
                         'sources': 202, 'encoded_bytes': 232466132,
                         'decoded_bytes': sum(p.get('uncompressed_bytes', 0) for p in originals)})


def raw_rows(phase, pins):
    for pin in pins:
        for line in phase.read(pin).splitlines():
            require(line, 'Empty actual intermediate row')
            yield json.loads(line)


def exact_ids(rows, key, expected=None):
    result = {}
    for row in rows:
        identity = row[key]
        require(type(identity) is str and identity and identity not in result, 'Duplicate/nonstring actual identity')
        result[identity] = row
    require(result and (expected is None or set(result) == set(expected)), 'Missing/foreign actual identity')
    return result


def original_alias(repo, descriptor, pin):
    require(all(descriptor.get(k) == pin.get(k) for k in
                ('bytes', 'sha256', 'uncompressed_bytes', 'uncompressed_sha256')),
            'Original consumer/source whole alias differs')
    commit = descriptor['commit']; name = descriptor['path']
    require(re.fullmatch('[a-f0-9]{40}', commit) is not None and type(name) is str and
            not name.startswith('/') and '\\' not in name and
            all(p not in ('', '.', '..') for p in name.split('/')), 'Unsafe original consumer request')
    row = subprocess.check_output(['git', '-C', str(repo), 'ls-tree', '-z', commit, '--', name]).decode().rstrip('\0')
    require('\t' in row, 'Missing actual original consumer source')
    meta, actual_name = row.split('\t'); mode, kind, blob = meta.split()
    require(actual_name == name and kind == 'blob' and mode in ('100644', '100755') and
            (mode, blob) == (pin['mode'], pin['blob']), 'Actual original consumer mode/OID differs')


class CanonicalStream:
    """Deferred complete canonical encoding; the full source object remains."""
    __slots__ = ('value',)

    def __init__(self, value):
        self.value = value


def canonical_stream(value):
    return CanonicalStream(value)


def canonical_chunks(value):
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'),
                               ensure_ascii=False, allow_nan=False)
    for text in encoder.iterencode(value):
        # iterencode can create one whole escaped string token. Bound each UTF8
        # encoding allocation without omitting a token, record or coordinate.
        for offset in range(0, len(text), 65536):
            yield text[offset:offset + 65536].encode()
    yield b'\n'


def canonical_digest(value):
    if type(value) is not CanonicalStream:
        return hashlib.sha256(value).hexdigest()
    digest = hashlib.sha256()
    for body in canonical_chunks(value.value):
        digest.update(body)
    return digest.hexdigest()


def bounded_reconstruction(phase, reconstruct, contact_key, originals, delta,
                           literal_inputs, canonical_json, code_receipt, binding_guard):
    """Disclosed resource binding of EXACT original pure function code objects.

    The original whole source and reconstruction receipt remain unchanged. The
    new globals are private copies; neither literal functions nor modules change.
    Live whole-project/callback authentication is mandatory before and after.
    """
    require(callable(binding_guard), 'Live canonical binding guard required')
    binding_guard()
    def custody(path):
        matches = [p for p in phase.pins.values()
                   if (phase.repo / p['path']).resolve() == Path(path).resolve()]
        require(len(matches) == 1, 'Missing exact canonical callback whole-code input')
        raw = phase.read(matches[0])
        with Path(path).open('rb') as stream:
            require(stream.read(len(raw) + 1) == raw, 'Actual canonical callback whole-code differs')
        return matches[0]
    adapter_pin = custody(__file__)
    inputs_pin = custody(literal_inputs.__file__)
    canonical_pin = custody(canonical_json.__code__.co_filename)
    source_pins = [p for p in phase.pins.values()
                   if p['sha256'] == code_receipt['whole_source_sha256']]
    require(len(source_pins) == 1, 'Missing unique whole original reconstruction source')
    expected_reconstruct, expected_contact, expected_receipt = literal_inputs.existing_reconstructor(
        phase.read(source_pins[0]), code_receipt['whole_source_sha256'], canonical_json)
    require(code_receipt == expected_receipt and reconstruct.__code__ == expected_reconstruct.__code__ and
            contact_key.__code__ == expected_contact.__code__, 'Original pure source/function receipt differs')
    for actual, expected in ((reconstruct, expected_reconstruct), (contact_key, expected_contact)):
        require(actual.__closure__ is None and actual.__kwdefaults__ is None,
                'Original pure function closure/default binding differs')
        if expected.__defaults__ is None:
            require(actual.__defaults__ is None, 'Original pure function defaults changed')
        else:
            defaults = actual.__defaults__
            require(type(defaults) is tuple and len(defaults) == len(expected.__defaults__) and
                    all(type(a) is types.FunctionType and a.__code__ == e.__code__ and
                        a.__closure__ is None and a.__defaults__ is None and a.__kwdefaults__ is None and
                        a.__globals__ is actual.__globals__ for a, e in zip(defaults, expected.__defaults__)),
                    'Original pure function defaults changed')
    original_globals = reconstruct.__globals__
    require(contact_key.__globals__ is original_globals and
            original_globals['canonical_json'] is canonical_json and
            original_globals['digest'] is literal_inputs.digest and
            original_globals['reconstruct'] is reconstruct and
            original_globals['contact_key'] is contact_key,
            'Original pure reconstruction callback binding differs')
    namespace = dict(original_globals)
    namespace.update(canonical_json=canonical_stream, digest=canonical_digest)
    rebound = []
    for original in (reconstruct, contact_key):
        function = types.FunctionType(original.__code__, namespace, original.__name__,
                                      original.__defaults__, original.__closure__)
        function.__kwdefaults__ = original.__kwdefaults__
        namespace[original.__name__] = function
        rebound.append(function)
    def check():
        require(original_globals['canonical_json'] is canonical_json and
                original_globals['digest'] is literal_inputs.digest and
                original_globals['reconstruct'] is reconstruct and original_globals['contact_key'] is contact_key,
                'Original callback environment changed')
        require(namespace['canonical_json'] is canonical_stream and
                namespace['digest'] is canonical_digest and
                namespace['reconstruct'] is rebound[0] and
                namespace['contact_key'] is rebound[1], 'Streamed callback binding changed')
        for original, actual in zip((reconstruct, contact_key), rebound):
            require(actual.__code__ is original.__code__ and
                    actual.__defaults__ is original.__defaults__ and
                    actual.__closure__ is original.__closure__ and
                    actual.__kwdefaults__ is original.__kwdefaults__ and
                    actual.__globals__ is namespace, 'Exact original function binding changed')
    check()
    result = rebound[0](originals, delta, lambda row: row['id'])
    check()
    binding_guard()
    facts = {'version': 1, 'kind': 'complete-canonical-json-streamed-sha256',
             'original_reconstruction': dict(code_receipt),
             'original_source_pin': source_pins[0],
             'adapter_pin': adapter_pin, 'literal_inputs_pin': inputs_pin,
             'literal_canonical_pin': canonical_pin,
             'callbacks': ['canonical_stream', 'canonical_chunks', 'canonical_digest'],
             'json_settings': {'sort_keys': True, 'ensure_ascii': False,
                              'separators': [',', ':'], 'allow_nan': False, 'newline': True},
             'maximum_utf8_encoding_chunk_bytes': 262144,
             'whole_string_token_limit': 'Original admitted source string; iterencode may escape one whole token.'}
    return result, facts


def ledger(phase, kind, config, config_pin, original_pins, literal_inputs, canonical_json,
           binding_guard=None):
    """Invoke the authenticated existing pure reconstruct on one COMPLETE kind.

    Output aliases select actual whole containing source objects. Delta upserts
    select the complete original delta body, never a hash-only replacement.
    """
    require(kind in ('components', 'fragments', 'contacts', 'residues'), 'Unknown original ledger')
    require(json.loads(phase.read(config_pin)) == config, 'Actually consumed original config differs')
    descriptors = [p for p in config['inputs'] if p['kind'] in (kind, kind + '_delta', 'reconstruction_code')]
    originals = []; locators = {}; delta = None; source = None
    containing = [original_pins[(d['commit'], d['path'])] for d in descriptors]
    table = canonical(containing)
    phase.output('containing-inputs.json', table)
    table_sha = sha(table)
    def key(row):
        return sha(canonical_json([row['fragments'], row['dateline'], row['kind']])) if kind == 'contacts' else row['id']
    for input_index, desc in enumerate(descriptors):
        pin = original_pins[(desc['commit'], desc['path'])]
        original_alias(phase.repo, desc, pin)
        body = phase.read(pin)
        if desc['kind'] == 'reconstruction_code':
            source = body
            continue
        value = json.loads(body)
        del body
        if desc['kind'] == kind + '_delta':
            require(delta is None, 'Duplicate original ledger delta')
            delta = value; delta_index = input_index
            del value
            continue
        rows = value['features'] if type(value) is dict else value
        require(type(rows) is list and rows, 'Empty/wrong original whole ledger')
        for ordinal, row in enumerate(rows):
            identity = key(row)
            require(type(identity) is str and identity not in locators, 'Duplicate/nonstring original ledger identity')
            locators[identity] = {'input_index': input_index,
                                  'selector': ['features', ordinal] if type(value) is dict else [ordinal]}
            originals.append(row)
        del value, rows, row
    require(source is not None and delta is not None, 'Missing full original reconstruction dependency')
    reconstruct, contact_key, code_receipt = literal_inputs.existing_reconstructor(
        source, config['existing_reconstructor']['sha256'], canonical_json)
    canonical_binding = None
    if kind == 'fragments':
        current, canonical_binding = bounded_reconstruction(
            phase, reconstruct, contact_key, originals, delta, literal_inputs,
            canonical_json, code_receipt, binding_guard)
    else:
        current = reconstruct(originals, delta, contact_key if kind == 'contacts' else lambda row: row['id'])
    # Literal reconstruction rejects a retained/upsert conflict; independently reject duplicate upserts too.
    upserts = set()
    for ordinal, row in enumerate(delta['upsert_records']):
        identity = key(row)
        require(identity not in upserts, 'Duplicate actual delta upsert')
        upserts.add(identity)
        locators[identity] = {'input_index': delta_index, 'selector': ['upsert_records', ordinal]}
    def indexes():
        for row in current:
            identity = key(row); raw = canonical_json(row)
            # Kind, ledger, table and reconstruction are recorded once in the
            # authenticated complete stage inventory. bind_alias restores those
            # fields before resolution; indexes do not duplicate them per row.
            alias = {**locators[identity], 'whole_object_bytes': len(raw), 'whole_object_sha256': sha(raw)}
            record = {'id': identity, 'alias': alias}
            if kind == 'components':
                record['geometry_sha256'] = sha(canonical_json(row['geometry']))
            if kind == 'components':
                record['fragment_bindings'] = row['properties']['fragment_bindings']
            elif kind == 'contacts':
                record.update(components=row['components'], fragments=row['fragments'])
            yield record
    phase.rows(kind, indexes())
    count = len(current)
    if kind == 'components':
        require(count == config['current_components'] == 95173, 'Incomplete complete current component ledger')
    del current, originals, locators, delta
    facts = {'operation': 'literal-ledger-reconstruction', 'ledger': kind,
             'current_count': count, 'reconstruction': code_receipt,
             'containing_table_sha256': table_sha}
    if canonical_binding is not None:
        facts['canonical_hash_binding'] = canonical_binding
    return phase.finish(facts)


def bind_alias(index_row, completed_ledger_inventory):
    facts = completed_ledger_inventory['facts']
    require(facts['operation'] == 'literal-ledger-reconstruction' and
            facts['ledger'] in ('components', 'fragments', 'contacts', 'residues'),
            'Wrong actual complete ledger alias inventory')
    return {'kind': 'complete-reconstructed-ledger-object', 'ledger': facts['ledger'],
            'id': index_row['id'], 'containing_table_sha256': facts['containing_table_sha256'],
            **index_row['alias']}


def resolve(phase, alias, table_pin, canonical_json):
    """Resolve only from actual complete admitted containing bytes."""
    require(alias['kind'] == 'complete-reconstructed-ledger-object', 'Wrong inverse alias kind')
    table_raw = phase.read(table_pin)
    require(sha(table_raw) == alias['containing_table_sha256'], 'Wrong actual containing descriptor table')
    table = json.loads(table_raw); index = alias['input_index']
    require(type(index) is int and 0 <= index < len(table), 'Escaped whole containing input index')
    value = json.loads(phase.read(table[index]))
    for part in alias['selector']:
        require(type(part) in (str, int), 'Wrong original object selector type')
        if type(part) is int:
            require(type(value) is list and 0 <= part < len(value), 'Escaped original object ordinal')
        else:
            require(type(value) is dict and part in value, 'Missing original object member')
        value = value[part]
    raw = canonical_json(value)
    require(len(raw) == alias['whole_object_bytes'] and sha(raw) == alias['whole_object_sha256'],
            'Complete inverse alias bytes differ')
    if alias['ledger'] == 'contacts':
        identity = sha(canonical_json([value['fragments'], value['dateline'], value['kind']]))
    else:
        identity = value.get('id')
    require(type(identity) is str and identity == alias['id'], 'Actual inverse alias identity differs')
    return value


def candidate_join(phase, component_pins, fragment_pins, contact_pins):
    components = exact_ids(raw_rows(phase, component_pins), 'id')
    fragments = exact_ids(raw_rows(phase, fragment_pins), 'id')
    require(len(components) == 95173, 'Incomplete full candidate roster')
    members = {}
    for identity, row in components.items():
        for binding in row['fragment_bindings']:
            child = binding['id']
            require(child in fragments and child not in members and
                    binding['feature_sha256'] == fragments[child]['alias']['whole_object_sha256'],
                    'Missing/multiply bound/changed full fragment')
            members[child] = identity
    require(set(members) == set(fragments), 'Complete fragment/component bijection differs')
    for row in raw_rows(phase, contact_pins):
        require(type(row['components']) is list and type(row['fragments']) is list and
                set(row['components']) <= set(components) and set(row['fragments']) <= set(fragments),
                'Actual contact ledger escapes complete reconstructed roster')
    facts = {'operation': 'complete-candidate-bindings', 'components': len(components),
             'fragments': len(fragments), 'components_sha256': sha(canonical(sorted(components)))}
    del components, fragments, members
    return phase.finish(facts)


def scope_index(phase, scope_pin):
    scope = json.loads(phase.read(scope_pin))
    selected = exact_ids(scope['rows'], 'component')
    complement = scope['complement_ids']
    require(type(complement) is list and all(type(i) is str for i in complement) and
            len(complement) == len(set(complement)) == 68897 and len(selected) == 26276 and
            not set(selected) & set(complement), 'Incomplete scoped/complement partition')
    require(len({r['family'] for r in selected.values()}) == 3503 and
            len({r['operational_batch'] for r in selected.values()}) == 253,
            'Wrong complete numeric family/batch roster')
    phase.rows('scope-selected', scope['rows'])
    phase.rows('scope-complement', ({'id': i} for i in complement))
    del scope, selected, complement
    return phase.finish({'operation': 'scope-index', 'selected': 26276, 'complement': 68897})


def routing_part(phase, pin, scope_pin, *, ordinal, previous_pin=None):
    """A true containing-part job; boundary bytes become an explicit next input."""
    scope = json.loads(phase.read(scope_pin))
    selected = exact_ids(scope['rows'], 'component'); complement = set(scope['complement_ids'])
    require(len(selected) == 26276 and len(complement) == len(scope['complement_ids']) == 68897 and
            not set(selected) & complement, 'Incomplete routing scope/complement')
    previous = json.loads(phase.read(previous_pin)) if previous_pin else {
        'next_part': 0, 'next_row': 0, 'last_identity': '', 'pending_base64': ''}
    require(previous['next_part'] == ordinal, 'Missing/reordered routing containing part')
    body = phase.read(pin)
    # Exact decoded stream bodies are bounded scratch products used by whole-hash verification.
    phase.output('whole-routing-part.bin', body)
    pending = base64.b64decode(previous['pending_base64'], validate=True)
    lines = (pending + body).split(b'\n'); pending = lines.pop()
    count = previous['next_row']; last = previous['last_identity']; indexes = []
    for line in lines:
        row = json.loads(line); identity = row['component']
        require(type(identity) is str and identity > last, 'Unsorted/duplicate full routing row')
        if row['next_prerequisite'] == 'engineering-numeric-closure-first':
            require(identity in selected, 'Foreign actual scoped routing row')
            expected = selected[identity]
            require(expected['actual_routing_row_ordinal'] == count and
                    expected['actual_routing_row_sha256'] == sha(line + b'\n') and
                    all(expected[k] == row[k] for k in ('current_feature_sha256', 'current_geometry_sha256',
                        'whole_physical_row_sha256', 'family', 'operational_batch')),
                    'Actual routing scope/type/hash/ordinal binding differs')
        else:
            require(identity in complement, 'Foreign actual complement routing row')
        fields = ('current_feature_sha256', 'current_geometry_sha256', 'family', 'operational_batch',
                  'whole_physical_containing_file', 'whole_physical_row_sha256')
        indexes.append({'id': identity, 'selected': identity in selected,
                        'row': {key: row[key] for key in fields},
                        'original_row_ordinal': count, 'original_row_sha256': sha(line + b'\n')})
        count += 1; last = identity
    phase.rows('routing', indexes)
    boundary = {'next_part': ordinal + 1, 'next_row': count, 'last_identity': last,
                'pending_base64': base64.b64encode(pending).decode()}
    phase.output('boundary.json', canonical(boundary))
    del scope, selected, complement, indexes, lines, body, pending
    return phase.finish({'operation': 'routing-containing-part', 'part': ordinal, 'boundary': boundary})


def routing_whole(phase, raw_part_pins, report_pin):
    report = json.loads(phase.read(report_pin))
    entry = next(x for x in report['complete_whole_raw_bodies'] if x['name'] == 'components')
    require(len(raw_part_pins) == len(entry['parts']) == 25, 'Incomplete whole routing stream')
    digest = hashlib.sha256(); total = 0
    for actual, original in zip(raw_part_pins, entry['parts']):
        body = phase.read(actual)
        require(len(body) == original['uncompressed_bytes'] and sha(body) == original['uncompressed_sha256'],
                'Wrong/reordered full decoded routing part')
        digest.update(body); total += len(body)
    require(digest.hexdigest() == entry['sha256'], 'Whole original routing stream differs')
    return phase.finish({'operation': 'whole-routing-byte-verification', 'parts': 25,
                         'decoded_bytes': total, 'whole_sha256': digest.hexdigest()})


def routing_join(phase, component_pins, routing_pins, selected_pins, complement_pins):
    components = exact_ids(raw_rows(phase, component_pins), 'id')
    routing = exact_ids(raw_rows(phase, routing_pins), 'id', components)
    selected = exact_ids(raw_rows(phase, selected_pins), 'component')
    complement = exact_ids(raw_rows(phase, complement_pins), 'id')
    require(len(components) == 95173 and len(selected) == 26276 and len(complement) == 68897 and
            not set(selected) & set(complement) and set(components) == set(selected) | set(complement),
            'Complete actual routing/current/scoped/complement bijection differs')
    for identity, item in routing.items():
        row = item['row']; candidate = components[identity]
        require(item['selected'] == (identity in selected) and
                candidate['alias']['whole_object_sha256'] == row['current_feature_sha256'] and
                candidate['geometry_sha256'] == row['current_geometry_sha256'],
                'Whole actual current feature/geometry routing binding differs')
    del components, routing, selected, complement
    return phase.finish({'operation': 'complete-routing-candidate-join', 'complete': 95173,
                         'selected': 26276, 'complement': 68897})


def diagnoses_part(phase, pin):
    rows = []
    for ordinal, line in enumerate(phase.read(pin).splitlines()):
        row = json.loads(line)
        require(type(row.get('component_id')) is str, 'Wrong original diagnosis identity type')
        rows.append({'id': row['component_id'], 'status': row['status'], 'input': pin,
                     'row_ordinal': ordinal, 'whole_row_sha256': sha(line + b'\n')})
    exact_ids(rows, 'id')
    phase.rows('diagnosis-index', rows)
    count = len(rows); del rows
    return phase.finish({'operation': 'diagnosis-containing-file', 'rows': count})


def diagnosis_join(phase, diagnosis_pins, routing_pins):
    diagnoses = exact_ids(raw_rows(phase, diagnosis_pins), 'id')
    routing = exact_ids((r for r in raw_rows(phase, routing_pins) if r['selected']), 'id', diagnoses)
    require(len(diagnoses) == len(routing) == 26276, 'Incomplete original diagnosis/routing join')
    selected = [dict(row, family=routing[i]['row']['family'],
                     operational_batch=routing[i]['row']['operational_batch'],
                     physical_containing_file=routing[i]['row']['whole_physical_containing_file'])
                for i, row in sorted(diagnoses.items()) if row['status'] == 'original-replay-mismatch']
    require(len(selected) == 1294 and len({r['family'] for r in selected}) == 494 and
            len({r['operational_batch'] for r in selected}) == 49, 'Original mismatch/family/batch selector differs')
    phase.rows('mismatch-index', selected)
    del diagnoses, routing, selected
    return phase.finish({'operation': 'complete-original-mismatch-selector', 'original_rows': 26276,
                         'mismatches': 1294, 'families': 494, 'batches': 49})


def physical_part(phase, packed_pin, original, config, config_pin, original_pins, literal_inputs,
                  literal_transport, literal_immutable):
    """Restore one COMPLETE original physical file using full literal components.

    All eleven component bodies, the complete component delta and reconstruction
    source are admitted in this job. Their full reconstruction exists only here;
    the caller receives a file receipt, never the component dictionary.
    """
    require(json.loads(phase.read(config_pin)) == config, 'Actually consumed original config differs')
    originals = []; delta = None; source = None
    for descriptor in config['inputs']:
        kind = descriptor['kind']
        if kind not in ('components', 'components_delta', 'reconstruction_code'):
            continue
        pin = original_pins[(descriptor['commit'], descriptor['path'])]
        original_alias(phase.repo, descriptor, pin)
        body = phase.read(pin)
        if kind == 'reconstruction_code':
            source = body
        elif kind == 'components_delta':
            require(delta is None, 'Duplicate full component delta')
            delta = json.loads(body)
        else:
            value = json.loads(body)
            originals.extend(value['features'] if type(value) is dict else value)
    require(source is not None and delta is not None, 'Missing literal current reconstruction input')
    reconstruct, _, code_receipt = literal_inputs.existing_reconstructor(
        source, config['existing_reconstructor']['sha256'], literal_immutable.canonical_json)
    current = reconstruct(originals, delta, lambda row: row['id'])
    require(len(current) == config['current_components'] == 95173, 'Missing full current component roster')
    class Context:
        component = literal_transport.Context.component
    context = Context(); context.components = {}
    for row in current:
        identity = row['id']
        require(type(identity) is str and identity not in context.components, 'Duplicate/wrong full current component')
        context.components[identity] = (row['properties'], sha(literal_immutable.canonical_json(row)),
                                        sha(literal_immutable.canonical_json(row['geometry'])))
    del originals, current, delta, source
    literal_transport.original_bounds(original)
    packed = phase.read(packed_pin); restored = bytearray(); indexes = []; seen = set(); queries = 0
    phase.output('packed-containing-input.json', canonical(packed_pin))
    original_path = packed_pin.get('original_relation', {}).get('original_path')
    require(type(original_path) is str, 'Missing exact physical original relation')
    for ordinal, line in enumerate(packed.splitlines()):
        row = json.loads(line); identity = row['component_id']
        require(type(identity) is str and identity not in seen and identity in context.components,
                'Duplicate/foreign physical component')
        seen.add(identity)
        actual = literal_transport.restore_row(row, 'components', context)
        raw = literal_immutable.canonical_json(actual)
        require(len(restored) + len(raw) <= FILE, 'Actual original restored physical file bound')
        restored.extend(raw)
        query_rows = actual['query_relations']
        require(type(query_rows) is list, 'Wrong original ordered query type')
        queries += len(query_rows)
        indexes.append({'id': identity, 'original_path': original_path, 'row_ordinal': ordinal,
                        'packed_whole_row_sha256': sha(literal_immutable.canonical_json(row)),
                        'restored_whole_row_sha256': sha(raw), 'query_count': len(query_rows)})
    body = bytes(restored)
    require(len(body) == original['uncompressed_bytes'] and sha(body) == original['uncompressed_sha256'],
            'Whole restored original physical decoded file differs')
    encoded = literal_immutable.deterministic_gzip(body)
    require(len(encoded) == original['bytes'] and sha(encoded) == original['sha256'],
            'Whole restored original physical encoded file differs')
    phase.output('whole-original-physical.jsonl.gz', body, compress=True, encoded=encoded)
    phase.rows('physical-index', indexes)
    count = len(seen)
    del context, packed, restored, indexes, seen, body, encoded
    return phase.finish({'operation': 'whole-original-physical-restoration', 'original': original,
                         'components': count, 'queries': queries, 'reconstruction': code_receipt})


def physical_join(phase, physical_pins, component_pins, routing_pins, mismatch_pins):
    physical = exact_ids(raw_rows(phase, physical_pins), 'id')
    components = exact_ids(raw_rows(phase, component_pins), 'id', physical)
    routing = exact_ids(raw_rows(phase, routing_pins), 'id', physical)
    mismatches = exact_ids(raw_rows(phase, mismatch_pins), 'id')
    require(len(physical) == len(components) == len(routing) == 95173 and len(mismatches) == 1294,
            'Incomplete whole physical/current/routing/mismatch identities')
    count = 0
    for identity, item in routing.items():
        if not item['selected']:
            continue
        row = item['row']; support = physical[identity]
        source_path = support['original_path']
        # The adapter consumes the current ordinary alias; original path relation is
        # pinned in source-index, rather than inferred from its current basename.
        require(source_path == row['whole_physical_containing_file'] and
                support['packed_whole_row_sha256'] == row['whole_physical_row_sha256'],
                'Wrong whole physical containing-file/row binding')
        if identity in mismatches:
            require(mismatches[identity]['physical_containing_file'] == source_path,
                    'Original mismatch physical containing-file differs')
            count += support['query_count']
    require(count == 10419 and set(mismatches) <= set(physical), 'Complete original ordered query cohort differs')
    del physical, components, routing, mismatches
    return phase.finish({'operation': 'complete-original-physical-query-join', 'complete': 95173,
                         'mismatches': 1294, 'ordered_queries': 10419})


def query_part(phase, restored_physical_pin, mismatch_pins, canonical_json):
    """Actual original queries for native binding, from a whole restored body.

    The containing descriptor and original row/query ordinals in the authenticated
    stage inventory provide the inverse to complete original query objects. The
    native binding subset is derived from those objects, never from counts alone.
    """
    mismatches = exact_ids(raw_rows(phase, mismatch_pins), 'id')
    require(len(mismatches) == 1294, 'Incomplete original native-query mismatch selector')
    rows = []; seen = set(); components = []
    fields = ('source_id', 'source_level', 'source_container', 'source_record_sha256',
              'source_pointset_sha256', 'periodic_offset')
    for ordinal, line in enumerate(phase.read(restored_physical_pin).splitlines()):
        row = json.loads(line); identity = row['component_id']
        require(type(identity) is str and identity not in seen, 'Duplicate actual original physical query component')
        seen.add(identity)
        if identity not in mismatches:
            continue
        components.append(identity)
        require(type(row['query_relations']) is list, 'Wrong actual original ordered query roster')
        for query_ordinal, query in enumerate(row['query_relations']):
            require(all(type(query.get(k)) is int for k in ('source_id', 'source_level', 'source_container')) and
                    type(query.get('periodic_offset')) in (int, float) and query['periodic_offset'] in (-360, 0, 360),
                    'Wrong actual original query native/frame types')
            for key in ('source_record_sha256', 'source_pointset_sha256'):
                require(re.fullmatch('[a-f0-9]{64}', query.get(key, '')) is not None, 'Wrong actual native query whole digest')
            item = {'component_id': identity, 'physical_row_ordinal': ordinal,
                    'query_ordinal': query_ordinal, 'original_query_sha256': sha(canonical_json(query)),
                    'query': {key: query[key] for key in fields}}
            require(len(canonical(item)) <= 1024, 'Actual query binding row exceeds admitted metadata bound')
            rows.append(item)
    phase.rows('native-query-index', rows)
    count = len(rows)
    del mismatches, rows, seen
    return phase.finish({'operation': 'actual-original-native-query-containing-file',
                         'whole_restored_physical_input': restored_physical_pin,
                         'components': components, 'ordered_queries': count, 'maximum_row_bytes': 1024})


def query_join(phase, query_pins, mismatch_pins, physical_pins):
    mismatches = exact_ids(raw_rows(phase, mismatch_pins), 'id')
    physical = exact_ids(raw_rows(phase, physical_pins), 'id')
    require(len(mismatches) == 1294 and len(physical) == 95173 and set(mismatches) <= set(physical),
            'Incomplete actual query/physical/mismatch roster')
    ordinals = {identity: 0 for identity in mismatches}; total = 0; wanted = set()
    for row in raw_rows(phase, query_pins):
        identity = row['component_id']; number = row['query_ordinal']
        require(identity in ordinals and type(number) is int and number == ordinals[identity],
                'Missing/duplicated/reordered/foreign actual native query')
        require(type(row['query']['source_id']) is int, 'Wrong actual native source identity type')
        ordinals[identity] += 1; total += 1; wanted.add(row['query']['source_id'])
    require(total == 10419 and all(ordinals[i] == physical[i]['query_count'] for i in mismatches),
            'Complete actual native-query ordered coverage differs')
    del mismatches, physical, ordinals
    return phase.finish({'operation': 'complete-actual-native-query-join', 'components': 1294,
                         'ordered_queries': total, 'contributing_source_ids': sorted(wanted)})
