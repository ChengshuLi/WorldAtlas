"""Exact admitted GSHHG bytes: ordinary getters and no-ZIP downstream reader."""
import gzip
import hashlib
import io
import json
import pathlib
import re
import struct
import subprocess
import tempfile
import copy

LIMIT = 33554432
BLOCK = 8388608
HEADER = struct.Struct('>11i')
MEMBER = 'gshhs_f.b'
MEMBER_BYTES = 95809336
MEMBER_SHA = 'af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6'


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_path(name):
    require(isinstance(name, str) and not name.startswith('/') and '\\' not in name
            and all(p not in ('', '.', '..') for p in name.split('/')), 'Unsafe ordinary path')
    return name


def bounds(pin, decoded=False):
    for field in ('bytes', 'uncompressed_bytes') if decoded else ('bytes',):
        require(type(pin.get(field)) is int and 0 <= pin[field] <= LIMIT,
                'Declared ordinary encoded/decoded bounds')
    for field in ('sha256', 'uncompressed_sha256') if decoded else ('sha256',):
        require(re.fullmatch('[a-f0-9]{64}', pin.get(field, '')) is not None,
                'Whole ordinary hash required')


class GitSources:
    """Requests must be exact entries in the frozen complete allowlist."""
    def __init__(self, repo, pins):
        self.repo = pathlib.Path(repo)
        self.pins = {}
        self.receipts = []
        for pin in pins:
            bounds(pin)
            safe_path(pin['path'])
            require(re.fullmatch('[a-f0-9]{40}', pin.get('commit', '')) is not None,
                    'Exact immutable source commit required')
            require(pin.get('mode') in ('100644', '100755') and
                    re.fullmatch('[a-f0-9]{40}', pin.get('blob', '')) is not None,
                    'Ordinary source mode/OID required')
            key = (pin['commit'], pin['path'])
            require(key not in self.pins, 'Duplicate source identity')
            self.pins[key] = dict(pin)
        require(sum(p['bytes'] for p in pins) <= 268435456 and len(pins) <= 512,
                'Complete ordinary source admission')

    def _git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args])

    def admitted(self, pin):
        key = (pin.get('commit'), pin.get('path'))
        require(key in self.pins and pin == self.pins[key], 'Undeclared/changed actual source request')
        return self.pins[key]

    def stream(self, request):
        pin = self.admitted(request)
        # Bounds and immutable tree identity precede actual blob retrieval.
        bounds(pin)
        rows = self._git('ls-tree', '-z', pin['commit'], '--', pin['path']).split(b'\0')
        rows = [r for r in rows if r]
        require(len(rows) == 1, 'Unique ordinary tree entry required')
        attrs, name = rows[0].decode().split('\t')
        mode, kind, oid = attrs.split()
        require(name == pin['path'] and kind == 'blob' and mode in ('100644', '100755'),
                'Nonordinary Git source')
        require(mode == pin['mode'] and oid == pin['blob'], 'Original source mode/OID differs')
        require(int(self._git('cat-file', '-s', oid)) == pin['bytes'] and pin['bytes'] <= LIMIT,
                'Pre-read ordinary source size differs')
        proc = subprocess.Popen(['git', '-C', str(self.repo), 'cat-file', 'blob', oid],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        count = 0
        digest = hashlib.sha256()
        try:
            while True:
                block = proc.stdout.read(BLOCK)
                if not block:
                    break
                count += len(block)
                require(count <= pin['bytes'], 'Actual ordinary source exceeds pin')
                digest.update(block)
                yield block
            error = proc.stderr.read()
            require(proc.wait() == 0, 'Git source retrieval failed: ' + error.decode(errors='replace'))
            require(count == pin['bytes'] and digest.hexdigest() == pin['sha256'],
                    'Whole ordinary source bytes differ')
            self.receipts.append(dict(pin, actual_bytes=count, actual_sha256=digest.hexdigest()))
        finally:
            proc.stdout.close()
            proc.stderr.close()
            if proc.poll() is None:
                proc.terminate()
                proc.wait()

    def small(self, pin):
        require(pin['bytes'] <= BLOCK, 'Small metadata getter refuses full source body')
        return b''.join(self.stream(pin))


class NativeParser:
    """Original int32 record byte accounting, with bounded cross-chunk state."""
    def __init__(self, emit=None, expected_count=188612):
        self.emit = emit or (lambda row: None)
        self.expected_count = expected_count
        self.seen = set()
        self.header = bytearray()
        self.point_tail = b''
        self.record = None
        self.remaining = 0
        self.position = 0
        self.record_digest = None
        self.coordinate_digest = None

    def _begin(self):
        values = HEADER.unpack(self.header)
        identity, n, flag = values[:3]
        require(identity >= 0 and identity not in self.seen and n >= 3,
                'Duplicate/invalid native ID or point count')
        require(n * 8 <= MEMBER_BYTES - self.position, 'Impossible native coordinate length')
        require(flag & 255 in (1, 2, 3, 4, 5, 6), 'Unknown native level')
        self.seen.add(identity)
        self.remaining = n * 8
        self.record_digest = hashlib.sha256(self.header)
        self.coordinate_digest = hashlib.sha256()
        self.record = dict(ordinal=len(self.seen)-1, id=identity, offset=self.position-44,
                           record_bytes=44+n*8, header_int32=list(values), n=n, flag=flag,
                           level=flag & 255, version=(flag >> 8) & 255,
                           seam_flags=(flag >> 16) & 3, source=(flag >> 24) & 1,
                           river_lake=(flag >> 25) & 1, area_scale=(flag >> 26) & 63,
                           container=values[9], ancestor=values[10],
                           native_bounds_microdegrees=[2147483647,2147483647,-2147483648,-2147483648],
                           first_point=None, last_point=None, coordinate_out_of_range=False)
        self.header.clear()

    def feed(self, block):
        require(len(block) <= BLOCK, 'Native input block bound')
        cursor = 0
        while cursor < len(block):
            if self.record is None:
                take = min(44-len(self.header), len(block)-cursor)
                self.header.extend(block[cursor:cursor+take])
                cursor += take
                self.position += take
                if len(self.header) == 44:
                    self._begin()
            else:
                take = min(self.remaining, len(block)-cursor)
                piece = block[cursor:cursor+take]
                self.record_digest.update(piece)
                self.coordinate_digest.update(piece)
                points = self.point_tail + piece
                length = len(points)//8*8
                for x, y in struct.iter_unpack('>2i', points[:length]):
                    r = self.record
                    if r['first_point'] is None:
                        r['first_point'] = [x, y]
                    r['last_point'] = [x, y]
                    a = r['native_bounds_microdegrees']
                    a[0], a[1], a[2], a[3] = min(a[0],x), min(a[1],y), max(a[2],x), max(a[3],y)
                    r['coordinate_out_of_range'] |= not (-180000000 <= x <= 360000000 and
                                                         -90000000 <= y <= 90000000)
                self.point_tail = points[length:]
                cursor += take
                self.position += take
                self.remaining -= take
                if self.remaining == 0:
                    require(not self.point_tail, 'Native point byte alignment')
                    self.record.update(record_sha256=self.record_digest.hexdigest(),
                                       coordinate_bytes_sha256=self.coordinate_digest.hexdigest(),
                                       closed=self.record['first_point'] == self.record['last_point'],
                                       geometry_validity='not-evaluated; byte custody only')
                    self.emit(self.record)
                    self.record = None

    def finish(self):
        require(self.record is None and not self.header and not self.point_tail,
                'Truncated/trailing native record bytes')
        require(len(self.seen) == self.expected_count, 'Incomplete native record identity count')
        return {'records':len(self.seen), 'native_bytes':self.position}


def member_index(index):
    require(index.get('member_name') == MEMBER and index.get('member_bytes') == MEMBER_BYTES and
            index.get('member_sha256') == MEMBER_SHA and index.get('record_count') == 188612,
            'Fixed original native member authority differs')
    parts = index.get('parts', [])
    require(len(parts) == 3, 'Complete three native aliases required')
    offset = 0
    seen = set()
    for ordinal, (pin, size) in enumerate(zip(parts, (33554432,33554432,28700472))):
        bounds(pin, decoded=True)
        safe_path(pin['path'])
        require(pin['path'] not in seen and type(pin.get('ordinal')) is int and
                type(pin.get('offset')) is int and pin.get('ordinal') == ordinal and
                pin.get('offset') == offset and pin['uncompressed_bytes'] == size,
                'Duplicate/reordered native alias or offset differs')
        seen.add(pin['path'])
        offset += size
    require(offset == MEMBER_BYTES, 'Complete native length differs')
    return parts


def directory_body(root, pin):
    bounds(pin, decoded=True)
    root = pathlib.Path(root)
    require(root.is_absolute() and '..' not in root.parts, 'Absolute safe native root required')
    for parent in (root, *root.parents):
        require(not parent.is_symlink(), 'Native root symlink/ancestor')
    root = root.resolve()
    name = safe_path(pin['path'])
    path = root/name
    for p in (path, *path.parents):
        require(not p.is_symlink(), 'Native alias symlink/ancestor')
        if p == root:
            break
    require(path.is_file() and path.stat().st_size == pin['bytes'], 'Ordinary native alias size')
    with path.open('rb') as f:
        chunks = []
        total = 0
        for block in iter(lambda:f.read(BLOCK), b''):
            total += len(block)
            require(total <= pin['bytes'] and total <= LIMIT, 'Actual encoded native alias grew beyond bound')
            chunks.append(block)
        require(total == pin['bytes'], 'Actual encoded native alias EOF size differs')
        body = b''.join(chunks)
    require(sha(body) == pin['sha256'], 'Whole native encoded bytes differ')
    return body


def decoded_chunks(pin, encoded):
    bounds(pin, decoded=True)
    require(len(encoded) == pin['bytes'] and sha(encoded) == pin['sha256'],
            'Native encoded body differs')
    digest = hashlib.sha256()
    size = 0
    with gzip.GzipFile(fileobj=io.BytesIO(encoded)) as f:
        while True:
            block = f.read(min(BLOCK, pin['uncompressed_bytes']-size+1))
            if not block:
                break
            size += len(block)
            require(size <= pin['uncompressed_bytes'] and size <= LIMIT, 'Actual native decoded bound')
            digest.update(block)
            yield block
    require(size == pin['uncompressed_bytes'] and digest.hexdigest() == pin['uncompressed_sha256'],
            'Whole native decoded fragment differs')


def _verify_native_chunks(index, get_encoded):
    """Internal validation stream; never expose its partial bytes to operations."""
    whole = hashlib.sha256()
    total = 0
    parser = NativeParser()
    for pin in member_index(index):
        for block in decoded_chunks(pin, get_encoded(pin)):
            whole.update(block)
            total += len(block)
            parser.feed(block)
            yield block
    parsed = parser.finish()
    require(total == MEMBER_BYTES and whole.hexdigest() == MEMBER_SHA and parsed['native_bytes'] == total,
            'Whole original native reconstruction differs')


def consume_native(index, get_encoded, consumer, scratch_parent):
    """Authenticate ALL bytes before the sole consumer callback; no receipt reuse.

    The temporary file is a virtual reconstruction of three bounded inputs, not
    an additional source or a single oversized ordinary evidence descriptor.
    """
    frozen = copy.deepcopy(index)
    index_bytes = json.dumps(frozen,sort_keys=True,separators=(',',':')).encode()
    source_path = pathlib.Path(__file__)
    require(not source_path.is_symlink(), 'Ordinary executed native reader')
    code_sha = sha(source_path.read_bytes())
    member_index(frozen)
    parent = pathlib.Path(scratch_parent)
    require(parent.is_absolute() and '..' not in parent.parts and parent.is_dir(), 'Safe existing native scratch root')
    for item in (parent,*parent.parents):
        require(not item.is_symlink(), 'Native scratch root symlink/ancestor')
    # This API accepts no passed validation receipt and never rereads a changing
    # external getter after validation. It consumes only the authenticated image.
    def guarded_get(pin):
        body = get_encoded(pin)
        require(json.dumps(index,sort_keys=True,separators=(',',':')).encode() == index_bytes,
                'Native source index changed during validation')
        require(sha(source_path.read_bytes()) == code_sha, 'Native reader code changed during validation')
        return body
    with tempfile.TemporaryFile(mode='w+b',dir=parent) as image:
        for block in _verify_native_chunks(frozen,guarded_get):
            image.write(block)
        require(json.dumps(index,sort_keys=True,separators=(',',':')).encode() == index_bytes,
                'Native source index changed during validation')
        require(sha(source_path.read_bytes()) == code_sha, 'Native reader code changed during validation')
        image.flush()
        image.seek(0)
        digest = hashlib.sha256()
        total = 0
        for block in iter(lambda:image.read(BLOCK),b''):
            digest.update(block)
            total += len(block)
        require(total == MEMBER_BYTES and digest.hexdigest() == MEMBER_SHA,
                'Authenticated native image changed before consumer')
        image.seek(0)
        return consumer(image,{'member_bytes':total,'member_sha256':digest.hexdigest(),
                               'reader_sha256':code_sha,'index_sha256':sha(index_bytes),
                               'full_validation_before_consumer':True})
