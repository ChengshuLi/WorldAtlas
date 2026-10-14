"""Retain complete provisional checkpoint bytes beside their trusted report.

This transport grants no acceptance and never rewrites producer publications.
The merge receipt and authenticated artifact remain the authority boundary.
"""
import gzip
import hashlib
import io
import json
import pathlib

FILE = 32 * 1024 * 1024
PHASE = 256 * 1024 * 1024
MEMBERS = ('derived-certificate.json.gz', 'derived-facts.json', 'derived-publication.json',
           'checkpoint-routes.json')
OPTIONAL = ('operating.json',)


def _ordinary_parent(directory):
    directory = pathlib.Path(directory).absolute()
    for target in (directory, *directory.parents):
        if target.is_symlink() or not target.is_dir():
            raise ValueError('Checkpoint output parent must be an existing ordinary directory')
    return directory


def admit_checkpoint_destination(directory):
    """Check every possible output, including dangling links, before science."""
    directory = _ordinary_parent(directory)
    for name in (*MEMBERS, *OPTIONAL):
        target = directory / name
        if target.is_symlink() or target.exists():
            raise ValueError('Checkpoint output already exists')
    return directory


def _json(body):
    return json.loads(body)


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def _matches(pin, name, descriptors):
    row = descriptors[name]
    return isinstance(pin, dict) and pin.get('path') == name and all(
        pin.get(key) == row[key] for key in ('bytes', 'sha256', *(
            ('decoded_bytes', 'decoded_sha256') if name.endswith('.gz') else ())))


def retain_checkpoint_products(source, destination, issued, *, allowance=PHASE):
    """Read the whole authenticated child set and publish copies exclusively.

    Caller has completed the actual native consumer. The descriptor is returned
    only after all writes complete; a partial write has no valid final report.
    """
    source = _ordinary_parent(source)
    destination = admit_checkpoint_destination(destination)
    names = set(p.name for p in source.iterdir())
    if not set(MEMBERS) <= names or names - set((*MEMBERS, *OPTIONAL)):
        raise ValueError('Incomplete or extra checkpoint product roster')
    if type(allowance) is not int or not 0 < allowance <= PHASE:
        raise ValueError('Invalid complete checkpoint transport allowance')
    total, sizes = 0, {}
    for name in sorted(names):
        target = source / name
        stat = target.lstat()
        if target.is_symlink() or not target.is_file() or stat.st_mode & 0o777 != 0o644 or not 0 < stat.st_size <= FILE:
            raise ValueError('Nonordinary or oversized checkpoint product')
        # Reserve encoded copies, parsing/live objects, and worst-case bounded
        # gzip output before opening it. The exact gzip size is checked next.
        decoded = 0
        if name.endswith('.gz'):
            with target.open('rb') as stream:
                stream.seek(-4, 2)
                decoded = int.from_bytes(stream.read(4), 'little')
            if not 0 < decoded <= FILE:
                raise ValueError('Checkpoint gzip decoded size exceeds file limit')
        sizes[name] = (stat.st_size, decoded)
        total += stat.st_size + 8 * (decoded or stat.st_size)
    if total > allowance:
        raise ValueError('Complete checkpoint transport exceeds current allowance')
    bodies, descriptors = {}, {}
    for name in sorted(names):
        target = source / name
        with target.open('rb') as stream:
            body = stream.read(FILE + 1)
        if len(body) != sizes[name][0]:
            raise ValueError('Checkpoint product changed beyond admitted size')
        row = {'name': name, 'bytes': len(body), 'sha256': _sha(body)}
        if name.endswith('.gz'):
            # gzip.decompress may allocate on a size lie; bounded streaming does
            # not trust the trailer, including concatenated gzip members.
            with gzip.GzipFile(fileobj=io.BytesIO(body), mode='rb') as stream:
                decoded = stream.read(sizes[name][1] + 1)
            if len(decoded) != sizes[name][1]:
                raise ValueError('Checkpoint gzip exceeds decoded file limit')
            row.update(decoded_bytes=len(decoded), decoded_sha256=_sha(decoded))
        bodies[name], descriptors[name] = body, row
    actual = sum(row['bytes'] + 8 * row.get('decoded_bytes', row['bytes']) for row in descriptors.values())
    if actual > total or actual > allowance:
        raise ValueError('Checkpoint products changed after union admission')
    derived = _json(bodies['derived-publication.json'])
    facts = _json(bodies['derived-facts.json'])
    native = issued.get('native', {})
    if (native.get('status') != 'no-new-native-loss' or native.get('candidate_code_executed') is not False
            or native.get('lost_or_reassigned_cells') != 0 or native.get('intervals') != []):
        raise ValueError('Checkpoint products lack successful native conservation')
    if (derived.get('complete') is not True or derived.get('accepted_checkpoint') is not False
            or derived.get('validation_stage') != 'native-passed'
            or issued.get('derived_checkpoint') != derived
            or not _matches(derived.get('certificate'), 'derived-certificate.json.gz', descriptors)
            or not _matches(derived.get('facts'), 'derived-facts.json', descriptors)
            or not _matches(derived.get('routes'), 'checkpoint-routes.json', descriptors)
            or facts.get('checkpoint_routes') != derived.get('routes')):
        raise ValueError('Checkpoint complete publications or member bindings differ')
    # Match the producer's pre-wrapper native report without changing either
    # the complete retained report or the provisional derived facts.
    inverse = {key: value for key, value in native.items() if key not in (
        'runtime', 'caller_runtime', 'execution_runtimes', 'execution_code_inventory')}
    inverse_bytes = (json.dumps(inverse, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode()
    if facts.get('native_result_sha256') != _sha(inverse_bytes):
        raise ValueError('Checkpoint native result does not bind derived products')
    admit_checkpoint_destination(destination)
    for name in sorted(names):
        # Preserve both ordinary and dangling-symlink collision targets. A
        # failed partial write cannot publish a descriptor or final root report.
        with (destination / name).open('xb') as stream:
            stream.write(bodies[name])
    return {'version': 1, 'kind': 'selected-checkpoint-products-v1',
            'members': [descriptors[name] for name in sorted(names)]}
