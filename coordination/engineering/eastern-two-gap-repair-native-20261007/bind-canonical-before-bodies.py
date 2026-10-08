"""Bind each permitted pre-restoration body to the genuine parent PR baseline."""
import hashlib
import json
from pathlib import Path
import subprocess
BASE = 'f17edd3d48ed10073afd5983d4090276418e4d13'
ROOT = Path(__file__).resolve().parents[3]
CAP = 32 * 1024 * 1024

def bind(source, output):
    if output.exists() or output.parent != ROOT / '.cache':
        raise ValueError('Fresh owned pre-restoration binding required')
    map_raw = (source / 'canonical-path-map.json').read_bytes()
    result = json.loads(map_raw)
    for pin in result['logical_targets']:
        name = pin['target']
        if name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/')):
            raise ValueError('Exact canonical path required')
        entry = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-z', BASE, '--', name])
        pin['existing_original'] = None
        if entry:
            info, actual = entry.decode().rstrip('\0').split('\t')
            mode, kind, oid = info.split(' ')
            if actual != name or kind != 'blob' or mode not in ('100644', '100755'):
                raise ValueError('Whole original ordinary entry required')
            size = int(subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', '-s', oid]))
            if not 0 <= size <= CAP:
                raise ValueError('Whole original bounds before allocation')
            with subprocess.Popen(['git', '-C', str(ROOT), 'cat-file', 'blob', oid], stdout=subprocess.PIPE) as process:
                raw = process.stdout.read(size + 1)
                extra = process.stdout.read(1)
                code = process.wait()
            if len(raw) != size or extra or code:
                raise ValueError('Whole original bounded EOF differs')
            if hashlib.sha1(b'blob ' + str(size).encode() + b'\0' + raw).hexdigest() != oid:
                raise ValueError('Original whole Git body differs')
            pin['existing_original'] = {'commit': BASE, 'path': name, 'blob': oid, 'mode': mode,
                                        'bytes': size, 'sha256': hashlib.sha256(raw).hexdigest()}
    output.mkdir(); (output / 'objects').mkdir()
    for pin in result['distinct_objects']:
        from os import link
        link(source / pin['path'], output / pin['path'])
    (output / 'canonical-path-map.json').write_text(json.dumps(result, separators=(',', ':')) + '\n')
    return {'status': 'PASS', 'paths': len(result['logical_targets']),
            'existing_original_paths': sum(p['existing_original'] is not None for p in result['logical_targets']),
            'original_commit': BASE, 'scientific_producers_invoked': False}

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('--source', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(bind(args.source, args.output)))
