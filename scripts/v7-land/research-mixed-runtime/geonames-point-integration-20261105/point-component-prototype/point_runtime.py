"""Run-scoped batching for the pinned, unchanged selected-point checkers.

GeoNames records are indexed once, then passed through the reviewed extractor.
Named-identity checks share one isolated interpreter and authenticated source
parse. Neither substitution changes selectors, geometry checks or result fields.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import FunctionType, SimpleNamespace
import zipfile


def need(ok, message):
    if not ok:
        raise ValueError(message)


class _ArchiveView:
    """Expose the original archive metadata and all matches for one selection."""
    def __init__(self, members, records):
        self.members, self.records = members, records

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def infolist(self):
        return self.members

    def open(self, member):
        return io.BytesIO(self.records[member.filename])


def extract_many(raw, source_sha256, selections, checker):
    """Return reviewed extraction results in selection order after one ZIP scan.

    Only selected raw records are retained. The complete member is still read,
    decoded and checked, so later duplicates, malformed UTF-8 and oversized lines
    remain errors even when every selected record appeared near its beginning.
    """
    need(type(raw) is bytes and 0 < len(raw) <= 16 * 1024 * 1024, 'source size')
    need(isinstance(source_sha256, str) and re.fullmatch(r'[a-f0-9]{64}', source_sha256)
         and hashlib.sha256(raw).hexdigest() == source_sha256, 'source hash')
    selections = list(selections)
    selected = {}
    for record_id, name, country, geometry_sha256 in selections:
        need(isinstance(record_id, str) and re.fullmatch(r'[1-9][0-9]{0,15}', record_id)
             and isinstance(name, str) and 0 < len(name) <= 256
             and isinstance(country, str) and re.fullmatch(r'[A-Z]{2}', country)
             and isinstance(geometry_sha256, str) and re.fullmatch(r'[a-f0-9]{64}', geometry_sha256), 'selection')
        selected.setdefault(country + '.txt', {})[record_id] = []
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            for filename, records in selected.items():
                hits = [member for member in members if member.filename == filename]
                need(len(hits) == 1 and hits[0].file_size <= 64 * 1024 * 1024
                     and not hits[0].is_dir(), 'country archive')
                with archive.open(hits[0]) as data:
                    while True:
                        line = data.readline(1024 * 1024 + 1)
                        if not line:
                            break
                        need(len(line) <= 1024 * 1024, 'country record too long')
                        record_id = line.decode('utf-8', 'strict').split('\t', 1)[0]
                        if record_id in records:
                            need(not records[record_id], 'record not unique or malformed')
                            records[record_id].append(line)
    except (zipfile.BadZipFile, UnicodeDecodeError, RuntimeError) as error:
        raise ValueError('invalid archive') from error
    results = []
    for selection in selections:
        record_id, _, country, _ = selection
        view = _ArchiveView(members, {country + '.txt': b''.join(selected[country + '.txt'][record_id])})
        module = SimpleNamespace(ZipFile=lambda *_: view, BadZipFile=zipfile.BadZipFile)
        reviewed = FunctionType(checker.__code__, {**checker.__globals__, 'zipfile': module},
                                checker.__name__, checker.__defaults__, checker.__closure__)
        results.append(reviewed(raw, source_sha256, *selection))
    return results


def run_identity(checker_bytes, requests):
    """Check an entire resolution in one isolated process, with per-item framing."""
    need(isinstance(checker_bytes, bytes) and len(checker_bytes) <= 8 * 1024 * 1024,
         'invalid checker code')
    frames = [json.dumps({'checker': checker_bytes.decode('utf-8')}, sort_keys=True).encode()]
    for request in requests:
        payload = json.dumps(request, sort_keys=True, separators=(',', ':')).encode()
        need(len(payload) <= 65536, 'worker request too large')
        frames.append(payload)
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    child = subprocess.run([sys.executable, '-I', '-c', Path(__file__).read_text()],
                           input=b'\n'.join(frames) + b'\n', stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, env=env)
    need(len(child.stderr) <= 65536, 'identity worker output too large')
    if child.returncode:
        raise ValueError('identity worker failed: ' + child.stderr.decode('utf-8', 'replace')[:500])
    lines = child.stdout.splitlines()
    need(len(lines) == len(requests), 'worker result count invalid')
    results = []
    for line in lines:
        need(len(line) <= 65536, 'identity worker output too large')
        result = json.loads(line)
        need(isinstance(result, dict) and result.get('schema') == 'named-identity-worker-v1',
             'worker result invalid')
        results.append(result['result'])
    return results


def _identity_worker():
    """Private child entry point; only the already-pinned checker is executed."""
    code = json.loads(sys.stdin.buffer.readline())['checker'].encode('utf-8')
    need(len(code) <= 8 * 1024 * 1024, 'invalid checker code')
    namespace = {'__name__': 'reviewed_named_identity'}
    exec(compile(code, '<pinned named identity>', 'exec'), namespace)
    sources = {}
    for line in iter(lambda: sys.stdin.buffer.readline(65538), b''):
        need(line.endswith(b'\n') and len(line) <= 65537, 'worker request too large')
        request = json.loads(line)
        key = request['identity_path'], request['identity_sha256']
        if key not in sources:
            with open(key[0], 'rb') as source:
                raw = source.read(8 * 1024 * 1024 + 1)
            need(len(raw) <= 8 * 1024 * 1024 and hashlib.sha256(raw).hexdigest() == key[1],
                 'identity source pin mismatch')
            sources[key] = json.loads(raw)
        result = namespace['check'](sources[key], request['point_geometry'],
                                    request['island_identity'], request['spec'])
        print(json.dumps({'schema': 'named-identity-worker-v1', 'result': result}, sort_keys=True))
    for (path, expected) in sources:
        digest = hashlib.sha256()
        with open(path, 'rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(block)
        need(digest.hexdigest() == expected, 'identity source changed during worker run')


if __name__ == '__main__':
    try:
        _identity_worker()
    except Exception as error:
        print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
        raise SystemExit(1)
