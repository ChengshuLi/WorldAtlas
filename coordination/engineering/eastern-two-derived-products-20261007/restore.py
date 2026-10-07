"""Restore the complete frozen source/product packet without changing scientific bytes."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
PREFIX = Path(__file__).resolve().parent
MAX = 32 * 1024 * 1024
PHASE = 256 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def gunzip(raw):
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as handle:
        decoded = handle.read(MAX + 1)
    if len(decoded) > MAX:
        raise ValueError('Decoded body exceeds cap before use')
    return decoded


def safe(value):
    if not isinstance(value, str) or not value or '\\' in value or '\0' in value or any(p in ('', '.', '..') for p in value.split('/')):
        raise ValueError('Unsafe ordinary relative path')
    return value


def checked(root, relative):
    current = root
    for piece in safe(relative).split('/'):
        current /= piece
        if current.is_symlink():
            raise ValueError('Symlink path rejected')
    return current


def raw_file(root, pin):
    p = checked(root, pin['path'])
    if not isinstance(pin['bytes'], int) or not 0 <= pin['bytes'] <= MAX or not p.is_file() or p.stat().st_size != pin['bytes']:
        raise ValueError('Ordinary declared/stat file bounds differ')
    raw = p.read_bytes()
    if sha(raw) != pin['sha256']:
        raise ValueError('Whole file checksum differs')
    return raw


def validate_index(index):
    if index['version'] != 1 or index['kind'] != 'complete-original-encoded-member-ordered-byte-transport':
        raise ValueError('Transport format differs')
    offset = 0
    seen = set()
    for part in index['parts']:
        safe(part['path'])
        if part['path'] in seen or part['offset'] != offset or not 0 < part['bytes'] <= MAX:
            raise ValueError('Incomplete ordered part closure')
        seen.add(part['path'])
        offset += part['bytes']
    if offset != index['whole_encoded_bytes'] or offset + 25 * 1024 * 1024 > PHASE:
        raise ValueError('Complete source packet phase admission fails')
    offset = 0
    for number, member in enumerate(index['members']):
        if member['id'] != number or member['offset'] != offset or member['mode'] not in ('100644', '100755'):
            raise ValueError('Complete unique member order/mode differs')
        if any(not isinstance(member[k], int) or not 0 <= member[k] <= MAX for k in ('bytes', 'decoded_bytes', 'encoded_bytes')):
            raise ValueError('Member encoded/decoded bounds fail')
        offset += member['encoded_bytes']
    if offset != index['whole_encoded_bytes']:
        raise ValueError('Member packet partition differs')
    seen = {}
    reused_world_uses = 0
    for binding in index['bindings']:
        key = (safe(binding['group']), safe(binding['path']))
        if key in seen:
            # The original before/after indexes both reference the same 35
            # literal before bodies. Preserve both logical uses, one payload.
            prior = seen[key]
            if key[0] != 'full_world_inputs' or not re.fullmatch('before/part-[0-9]+\\.json', key[1]) or prior != binding:
                raise ValueError('Duplicate complete source/role binding')
            reused_world_uses += 1
            if reused_world_uses > 35:
                raise ValueError('Duplicate complete source/role binding')
        else:
            seen[key] = binding
        member = index['members'][binding['member_id']]
        if any(binding[k] != member[k] for k in ('bytes', 'sha256', 'mode')):
            raise ValueError('Logical binding/member differs')
    if len(index['bindings']) != 688 or len(index['members']) != 422:
        raise ValueError('Frozen complete source roster omitted')
    if reused_world_uses != 35:
        raise ValueError('Complete before/after shared source uses omitted')


def member_bytes(index, member):
    # No 193MB whole stream buffer: one bounded encoded member at a time.
    start, end = member['offset'], member['offset'] + member['encoded_bytes']
    encoded = bytearray()
    for part in index['parts']:
        if part['offset'] >= end or part['offset'] + part['bytes'] <= start:
            continue
        raw = raw_file(PREFIX, part)
        a = max(start, part['offset']) - part['offset']
        b = min(end, part['offset'] + part['bytes']) - part['offset']
        encoded.extend(raw[a:b])
    if len(encoded) != member['encoded_bytes'] or sha(encoded) != member['encoded_sha256']:
        raise ValueError('Encoded complete member differs')
    raw = gunzip(encoded)
    if len(raw) != member['bytes'] or sha(raw) != member['sha256']:
        raise ValueError('Restored complete member differs')
    return raw


def original_guard(binding, raw):
    origin = binding.get('original_binding') or {}
    if origin.get('commit'):
        if not re.fullmatch('[0-9a-f]{40}', origin['commit']):
            raise ValueError('Immutable source commit required')
        safe(origin['path'])
        oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if origin.get('blob') != oid or origin.get('mode') != binding['mode']:
            raise ValueError('Actual immutable original Git blob/mode differs')
        actual = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-z', origin['commit'], '--', origin['path']])
        expected = (binding['mode'] + ' blob ' + oid + '\t' + origin['path'] + '\0').encode()
        if actual != expected:
            raise ValueError('Ordinary immutable source tree relation differs')


def authenticate_execution(commit):
    if not re.fullmatch('[a-f0-9]{40}', commit):
        raise ValueError('Execution commit required before Git')
    paths = [str(Path(__file__).relative_to(ROOT)), str((PREFIX / 'verify.py').relative_to(ROOT))]
    receipts = []
    for name in paths:
        expected = subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + name])
        local = checked(ROOT, name).read_bytes()
        if expected != local:
            raise ValueError('Actually executed local code differs')
        receipts.append({'path': name, 'bytes': len(local), 'sha256': sha(local), 'commit': commit})
    return receipts


def restore(commit, destination, identical_prior=None):
    code = authenticate_execution(commit)
    destination = Path(os.path.abspath(destination))
    if destination.parent != ROOT / '.cache' or not re.fullmatch('1386-[a-z0-9-]+', destination.name):
        raise ValueError('Fresh job-owned .cache/1386 run name required')
    for parent in destination.parents:
        if parent.is_symlink():
            raise ValueError('Symlink output ancestor rejected')
    if identical_prior is not None:
        identical_prior = Path(os.path.abspath(identical_prior))
    if destination.exists() or destination.is_symlink():
        raise ValueError('Fresh exclusively owned destination required')
    index_raw = (PREFIX / 'source-index.json').read_bytes()
    committed = subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + str((PREFIX / 'source-index.json').relative_to(ROOT))])
    if index_raw != committed:
        raise ValueError('Frozen source index changed')
    index = json.loads(index_raw)
    validate_index(index)
    destination.mkdir(parents=True)
    unique = destination / 'whole-members'
    unique.mkdir()
    stream = hashlib.sha256()
    for part in index['parts']:
        stream.update(raw_file(PREFIX, part))
    if stream.hexdigest() != index['whole_encoded_sha256']:
        raise ValueError('Complete original encoded concatenation differs')
    by_member = {}
    for binding in index['bindings']:
        by_member.setdefault(binding['member_id'], []).append(binding)
    product_rows = []
    for member in index['members']:
        raw = member_bytes(index, member)
        paths = by_member[member['id']]
        for binding in paths:
            original_guard(binding, raw)
            decoded = gunzip(raw) if binding['path'].endswith('.gz') else raw
            if len(decoded) != member['decoded_bytes'] or sha(decoded) != member['decoded_sha256']:
                raise ValueError('Actual whole decoded member differs')
        p = unique / str(member['id'])
        if identical_prior is not None:
            prior = checked(identical_prior, 'whole-members/' + str(member['id']))
            if not prior.is_file() or prior.stat().st_size != len(raw) or prior.read_bytes() != raw:
                raise ValueError('Whole prior member byte equivalence fails')
            os.link(prior, p)
        else:
            with p.open('xb') as handle:
                handle.write(raw)
        p.chmod(0o755 if member['mode'] == '100755' else 0o644)
        for binding in paths:
            target = checked(destination, binding['group'] + '/' + binding['path'])
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if target.read_bytes() != raw:
                    raise ValueError('Shared before/after whole body differs')
            else:
                os.link(p, target)  # Actual identical ordinary bodies, not symlink aliases.
            if binding['group'].startswith('full_') and binding['group'] in ('full_ownership_products180', 'full_runtime_products55', 'full_pixel_products2'):
                product_rows.append({k: binding[k] for k in ('group', 'path', 'member_id', 'bytes', 'sha256', 'mode')})
    (destination / 'package.json').write_text('{"type":"module"}\n')
    receipt = {'status': 'PASS', 'execution_commit': commit, 'executed_sources': code,
               'source_index_sha256': sha(index_raw), 'logical_bindings': len(index['bindings']),
               'unique_members': len(index['members']), 'complete_scientific_products': product_rows,
               'new_scientific_computation_claimed': False,
               'restoration_does_not_approve_source_authority': True}
    (destination / 'restoration-receipt.json').write_text(json.dumps(receipt, sort_keys=True, separators=(',', ':')) + '\n')
    return index, receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--identical-prior', type=Path)
    args = parser.parse_args()
    restore(args.commit, args.destination, args.identical_prior)
