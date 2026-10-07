"""Authenticated ordinary source acquisition for the complete original cohort.

The literal original reader/operators are loaded from captured committed bytes.
Only acquisition is interposed: no ZIP getter or legacy source Context can run.
"""
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess

LIMIT = 33554432
PHASE = 268435456
NUMERIC = 'coordination/engineering/complete-numeric-closure-diagnosis-20261007/'
NATIVE = 'coordination/engineering/gshhg-native-member-custody-20261007/'
OWNED = 'coordination/engineering/complete-replay-operand-restoration-20261007/'
HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False) + '\n').encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def tree(repo, commit, name):
    raw = subprocess.check_output(['git', '-C', str(repo), 'ls-tree', '-z', commit, '--', name])
    row = raw.decode().rstrip('\0').split('\t')
    require(len(row) == 2 and row[1] == name, 'Missing exact ordinary source path')
    mode, kind, oid = row[0].split()
    require(mode in ('100644', '100755') and kind == 'blob', 'Nonordinary source')
    return mode, oid


def decoded(raw, pin):
    require(len(raw) == pin['bytes'] <= LIMIT and sha(raw) == pin['sha256'],
            'Whole encoded source differs')
    if 'uncompressed_sha256' not in pin:
        return raw
    require(type(pin['uncompressed_bytes']) is int and 0 <= pin['uncompressed_bytes'] <= LIMIT,
            'Declared decoded source bound')
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
        body = stream.read(pin['uncompressed_bytes'] + 1)
    require(len(body) == pin['uncompressed_bytes'] and sha(body) == pin['uncompressed_sha256'],
            'Whole decoded source differs or exceeds bound')
    return body


def query_bind(query, meta):
    fields = {'source_id': meta['id'], 'source_level': meta['level'],
              'source_container': meta['container'], 'source_record_sha256': meta['record_sha256'],
              'source_pointset_sha256': meta['decoded_pointset_binary64_sha256']}
    require(all(type(query.get(k)) is int and type(fields[k]) is int for k in
                ('source_id', 'source_level', 'source_container')) and
            all(query.get(k) == value for k, value in fields.items()) and
            type(query.get('periodic_offset')) in (int, float) and
            query['periodic_offset'] in (-360, 0, 360),
            'Source record/container/level/native-frame binding differs')


class Sources:
    def __init__(self, repo, index, baseline_class):
        self.repo = Path(repo).resolve()
        self.index = index
        rows = index['files']
        require(len(rows) == 202 and len({(p['commit'], p['path']) for p in rows}) == 202,
                'Complete original 202-source roster differs')
        require(sum(p['bytes'] for p in rows) == 232466132, 'Complete source byte floor differs')
        self.snapshot = [p for p in rows if p['path'].endswith('/trace.py')]
        require(len(self.snapshot) == 1, 'Original operand-adapter snapshot differs')
        originals = [p for p in rows if p not in self.snapshot]
        self.pins = {p['path']: p for p in originals}
        self.baseline = baseline_class(self.repo, index['source_baseline_commit'],
            [dict(p, hash_kind='file-bytes') for p in originals])
        self.aliases = {}
        self.reads = []
        for p in originals:
            mode, oid = tree(self.repo, index['source_baseline_commit'], p['path'])
            require((mode, oid) == (p['mode'], p['blob']), 'Current source mode/OID differs')
            self.aliases[(p['commit'], p['path'])] = p
            relation = p.get('original_relation')
            if relation:
                key = (relation['original_commit'], relation['original_path'])
                if key in self.aliases:
                    require(self.aliases[key]['blob'] == p['blob'], 'Conflicting original aliases')
                self.aliases[key] = p
            decoded(self.baseline.pinned_bytes(p['path']), p)
        consumers = index['original_consumer_aliases']
        require(len(consumers) == 40 and
                len({(p['commit'], p['path']) for p in consumers}) == 40,
                'Incomplete original component consumer alias roster')
        for alias in consumers:
            require(alias['source_path'] in self.pins, 'Undeclared original consumer source')
            p = self.pins[alias['source_path']]
            require(all(alias[k] == p[k] for k in ('mode', 'blob', 'bytes', 'sha256')) and
                    tree(self.repo, alias['commit'], alias['path']) == (p['mode'], p['blob']),
                    'Original consumer whole source mode/OID/hash differs')
            key = (alias['commit'], alias['path'])
            require(key not in self.aliases or self.aliases[key]['blob'] == p['blob'],
                    'Conflicting original consumer aliases')
            self.aliases[key] = p
        snapshot = self.snapshot[0]
        raw = (HERE/'methods/trace.py').read_bytes()
        require(len(raw) == snapshot['bytes'] and sha(raw) == snapshot['sha256'],
                'Literal unmerged original-method snapshot differs')
        require(tree(self.repo, snapshot['commit'], snapshot['path']) ==
                (snapshot['mode'], snapshot['blob']), 'Original snapshot mode/OID differs')
        require(subprocess.check_output(['git', '-C', str(self.repo), 'cat-file', 'blob',
                                        snapshot['blob']]) == raw, 'Snapshot original whole body differs')

    def encoded(self, name):
        require(name in self.pins, 'Undeclared ordinary source request')
        p = self.pins[name]
        raw = self.baseline.pinned_bytes(name)
        decoded(raw, p)
        self.reads.append({'path': name, 'sha256': p['sha256'], 'bytes': len(raw)})
        return raw

    def checked(self, root, pin):
        name = NUMERIC + pin['path']
        require(name in self.pins, 'Undeclared original reader alias')
        p = self.pins[name]
        for field in ('bytes', 'sha256', 'uncompressed_bytes', 'uncompressed_sha256'):
            require(pin.get(field) == p.get(field), 'Original reader alias descriptor differs')
        return decoded(self.encoded(name), p)

    def encoded_checked(self, root, pin):
        name = NUMERIC + pin['path']
        require(name in self.pins, 'Undeclared original encoded reader alias')
        p = self.pins[name]
        for field in ('bytes', 'sha256', 'uncompressed_bytes', 'uncompressed_sha256'):
            require(pin.get(field) == p.get(field), 'Original encoded reader descriptor differs')
        return self.encoded(name)

    def ordinary_git(self, repo, commit, name, expected):
        require(Path(repo).resolve() == self.repo and (commit, name) in self.aliases,
                'Undeclared original getter or ZIP fallback')
        p = self.aliases[(commit, name)]
        require(tree(self.repo, commit, name) == (p['mode'], p['blob']),
                'Actual requested original mode/OID differs')
        require(expected['bytes'] == p['bytes'] and expected['sha256'] == p['sha256'],
                'Actual original getter whole binding differs')
        return self.encoded(p['path'])


def load(repo, code_baseline, shared, module_guard=None):
    """No geometry operator is invoked in this complete acquisition stage."""
    index = json.loads(code_baseline.materialized_bytes(OWNED+'source-index.json'))
    original_config = json.loads(code_baseline.materialized_bytes(OWNED+'methods/legacy/input-config.json'))
    expected = {(p['commit'], p['path'], p['bytes'], p['sha256']) for p in
                original_config['inputs'] if p['kind'] != 'archive_part'}
    actual = {(p['commit'], p['path'], p['bytes'], p['sha256']) for p in
              index['original_consumer_aliases']}
    require(len(expected) == 40 and actual == expected,
            'Original consumer getter closure differs from literal config')
    source = Sources(repo, index, shared.Baseline)
    modules = {
        'reader': 'methods/reader-acquisition.py', 'kernel': 'methods/kernel.py',
        'exact_predicates': 'methods/exact_predicates.py', 'trace': 'methods/trace.py',
        'native_reader': 'methods/native_reader.py',
        **{name: 'methods/legacy/'+name+'.py' for name in
           ('producer', 'comparison', 'inputs', 'immutable', 'ellipsoidal_area', 'transport')},
    }
    modules = code_baseline.load_modules({k: OWNED+v for k, v in modules.items()})
    if module_guard is not None:
        module_guard(modules, code_baseline)
    reader = modules['reader']
    # Explicit acquisition adapters; the literal comparison and decoder stay unchanged.
    reader.checked = source.checked
    reader.encoded_checked = source.encoded_checked
    reader.query_bind = query_bind
    modules['inputs'].ordinary_git = source.ordinary_git
    state = reader.load(repo)
    diagnoses = {}
    all_ids = set()
    for name, p in sorted(source.pins.items()):
        if not name.startswith(NUMERIC+'r1/diagnoses-'):
            continue
        for line in decoded(source.encoded(name), p).splitlines():
            row = json.loads(line)
            identity = row['component_id']
            require(identity not in all_ids, 'Duplicate complete original diagnosis')
            all_ids.add(identity)
            if row['status'] == 'original-replay-mismatch':
                diagnoses[identity] = row
    require(len(all_ids) == 26276 and all_ids == set(state['routing']),
            'Complete original diagnosis/routing bijection differs')
    require(len(diagnoses) == 1294, 'Complete original mismatch selector differs')
    require(len({state['routing'][i]['family'] for i in diagnoses}) == 494 and
            len({state['routing'][i]['operational_batch'] for i in diagnoses}) == 49,
            'Complete original family/batch scope differs')
    physical = {}
    for identity, row, pin in reader.physical_rows(state):
        if identity in diagnoses:
            physical[identity] = (row, pin)
    require(set(physical) == set(diagnoses), 'Complete physical cohort differs')
    require(sum(len(row['query_relations']) for row, pin in physical.values()) == 10419,
            'Complete original ordered query cohort differs')
    # Ordinary source guard replaces acquisition before any numerical callback.
    return {'source': source, 'modules': modules, 'state': state,
            'diagnoses': diagnoses, 'physical': physical}


def native_operands(loaded, scratch_parent):
    """Decode original records only after complete native-byte authentication."""
    source = loaded['source']
    modules = loaded['modules']
    comparison = modules['comparison']
    index = json.loads(source.encoded(NATIVE+'results/member-index.json'))
    wanted = {q['source_id'] for row, pin in loaded['physical'].values()
              for q in row['query_relations']}

    def consume(image, proof):
        headers = {}
        offset = ordinal = 0
        while True:
            raw = image.read(44)
            if not raw:
                break
            require(len(raw) == 44, 'Trailing native header bytes')
            values = comparison.HEADER.unpack(raw)
            size = 44 + values[1]*8
            require(values[0] not in headers and size >= 44 and
                    offset+size <= proof['member_bytes'], 'Duplicate/truncated original native record')
            headers[values[0]] = (offset, size, ordinal, values)
            image.seek(size-44, 1)
            offset += size
            ordinal += 1
        require(offset == 95809336 and ordinal == 188612 and wanted <= headers.keys(),
                'Incomplete original native/query header closure')
        closure = set(wanted)
        for identity in sorted(wanted):
            visited = set()
            cur = identity
            while headers[cur][3][2] & 255 in (2, 3, 4):
                if cur in visited:
                    break
                visited.add(cur)
                parent = headers[cur][3][9]
                if parent not in headers:
                    break
                closure.add(parent)
                cur = parent
        records = {}
        aliases = {}
        for identity in sorted(closure):
            start, size, number, header = headers[identity]
            image.seek(start)
            record = image.read(size)
            require(len(record) == size, 'Authenticated native image truncated')
            meta, geometry = comparison.decode_record(record[:44], record[44:], number, start)
            records[identity] = (meta, geometry)
            aliases[identity] = {'kind': 'complete-original-native-record-alias',
                'member_sha256': proof['member_sha256'], 'record_ordinal': number,
                'byte_offset': start, 'record_bytes': size, 'record_sha256': sha(record),
                'pointset_binary64_sha256': meta['decoded_pointset_binary64_sha256'],
                'decoder_original_commit': '104091cfecd9c83a53f3e6e62f95b0a0c8074351',
                'decoder': 'literal comparison.decode_record; original GMT longitude conversion'}
        for row, pin in loaded['physical'].values():
            for query in row['query_relations']:
                query_bind(query, records[query['source_id']][0])
        return records, aliases, dict(proof, complete_headers=ordinal,
            contributing_ids=sorted(wanted), complete_parent_closure_ids=sorted(closure))

    def getter(pin):
        require(type(pin['path']) is str and pin['path'] == Path(pin['path']).name and
                '/' not in pin['path'] and '\\' not in pin['path'] and
                pin['path'] not in ('', '.', '..'), 'Unsafe native fragment alias')
        name = NATIVE+'results/'+pin['path']
        require(name in source.pins, 'Undeclared native fragment getter')
        declared = source.pins[name]
        for field in ('bytes', 'sha256', 'uncompressed_bytes', 'uncompressed_sha256'):
            require(pin[field] == declared[field], 'Native index/ordinary descriptor differs')
        return source.encoded(name)

    return modules['native_reader'].consume_native(index, getter, consume, scratch_parent)
