"""Package complete existing bodies; this is transport, not a scientific run."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
PREFIX = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('immutable', ROOT / 'scripts/evidence/immutable.py')
immutable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(immutable)


def whole_sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preparation', type=Path, required=True)
    parser.add_argument('--preserved', type=Path, required=True)
    args = parser.parse_args()
    roster = json.loads((args.preparation / 'derived-products-child-complete-closure-roster.json').read_text())
    old_root = '/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/13630faa807843641a6abb3484134a94a87e5c38c2665c17f5c9742c84749ddf/work'
    members = []
    bindings = []
    lookup = {}
    parts = []
    payload = bytearray()
    stream_sha = hashlib.sha256()
    offset = 0
    wire = PREFIX / 'payloads'
    wire.mkdir(exist_ok=False)

    def flush():
        if not payload:
            return
        name = f'payloads/encoded-member-bytes-{len(parts):03d}.bin'
        raw = bytes(payload)
        (PREFIX / name).write_bytes(raw)
        parts.append({'path': name, 'offset': sum(p['bytes'] for p in parts),
                      'bytes': len(raw), 'sha256': whole_sha(raw)})
        payload.clear()

    for row in roster['bindings']:
        key = (row['sha256'], row['bytes'], row['mode'])
        if key not in lookup:
            p = Path(row['actual_read_path'])
            if str(p).startswith(old_root + '/.cache/'):
                p = args.preserved / str(p)[len(old_root) + 1:]
            elif str(p).startswith(old_root + '/'):
                origin = row.get('original_binding')
                if not origin or not origin.get('commit'):
                    raise ValueError('Removed tracked source lacks immutable original binding')
                raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', origin['commit'] + ':' + origin['path']])
                p = None
            if p is not None:
                if p.is_symlink() or not p.is_file() or p.stat().st_size > immutable.MAX_FILE_BYTES:
                    raise ValueError('Ordinary source body bounds')
                raw = p.read_bytes()
            if len(raw) != row['bytes'] or whole_sha(raw) != row['sha256']:
                raise ValueError('Prepared full source differs: ' + row['path'])
            decoded = gzip.decompress(raw) if row['path'].endswith('.gz') else raw
            if max(len(raw), len(decoded)) > immutable.MAX_FILE_BYTES:
                raise ValueError('Encoded/decoded member exceeds file limit')
            origin = row.get('original_binding') or {}
            if origin.get('blob'):
                actual_oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
                if actual_oid != origin['blob']:
                    raise ValueError('Actual immutable original Git blob differs')
            encoded = immutable.deterministic_gzip(raw)
            member = {'id': len(members), 'bytes': len(raw), 'sha256': whole_sha(raw),
                      'decoded_bytes': len(decoded), 'decoded_sha256': whole_sha(decoded),
                      'mode': row['mode'], 'offset': offset, 'encoded_bytes': len(encoded),
                      'encoded_sha256': whole_sha(encoded)}
            members.append(member)
            lookup[key] = member['id']
            stream_sha.update(encoded)
            offset += len(encoded)
            remaining = memoryview(encoded)
            while remaining:
                take = min(8 * 1024 * 1024 - len(payload), len(remaining))
                payload.extend(remaining[:take])
                remaining = remaining[take:]
                if len(payload) == 8 * 1024 * 1024:
                    flush()
        binding = {k: v for k, v in row.items() if k not in ('actual_read_path', 'whole_payload_alias')}
        binding['member_id'] = lookup[key]
        bindings.append(binding)
    flush()
    index = {'version': 1, 'kind': 'complete-original-encoded-member-ordered-byte-transport',
             'whole_encoded_bytes': offset, 'whole_encoded_sha256': stream_sha.hexdigest(),
             'parts': parts, 'members': members, 'bindings': bindings,
             'snapshot_original_relation': roster['snapshot_original_relation_proof'],
             'source_and_product_byte_identity_does_not_approve_authority': True,
             'prior_scientific_runs_not_new_transport_runs': True}
    (PREFIX / 'source-index.json').write_bytes(immutable.canonical_json(index))
    measured = sum(p['bytes'] for p in parts) + (PREFIX / 'source-index.json').stat().st_size
    if measured + 25 * 1024 * 1024 > immutable.MAX_PHASE_BYTES:
        raise ValueError('Complete transport plus declared reserve over phase cap')
    print(json.dumps({'status': 'PASS', 'logical_bindings': len(bindings), 'unique_members': len(members),
                      'complete_transport_bytes': measured, 'reserved_final_bytes': 25 * 1024 * 1024,
                      'scientific_method_executed': False}), flush=True)


if __name__ == '__main__':
    main()
