"""One bounded invocation of the unchanged preparation JSON/gzip functions."""
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / 'scripts'))
from evidence.immutable import canonical_json, deterministic_gzip


def main():
    target = pathlib.Path(sys.argv[1])
    if not target.is_absolute() or target.exists() or target.parent.resolve() != target.parent:
        raise ValueError('Fresh ordinary serialization output required')
    target.mkdir()
    seen = set()
    for line in sys.stdin.buffer:
        if len(line) > 1048576:
            raise ValueError('Atomic serialization input exceeds existing cap')
        row = json.loads(line)
        name = row['path']
        if not isinstance(name, str) or '/' in name or '\\' in name or name in seen or not name.endswith('.json.gz'):
            raise ValueError('Distinct bounded release filename required')
        seen.add(name)
        raw = canonical_json(row['payload'])
        if len(raw) > 1048576:
            raise ValueError('Atomic serialization payload exceeds existing cap')
        encoded = deterministic_gzip(raw)
        with (target / name).open('xb') as stream:
            stream.write(encoded)
        print(json.dumps({'path': name, 'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest(),
                          'decoded_bytes': len(raw), 'payload_sha256': hashlib.sha256(raw).hexdigest()}), flush=True)


if __name__ == '__main__':
    main()
