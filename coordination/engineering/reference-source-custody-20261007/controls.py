"""Directed production-reader controls; tiny fixtures, no original source execution."""
import hashlib
import gzip
import json
from pathlib import Path
import tempfile
import types
from unittest.mock import patch
import zipfile
import zlib
import custody
import producer


def reject(fn, text):
    try:
        fn()
    except ValueError as exc:
        if text not in str(exc):
            raise AssertionError((text, str(exc))) from exc
        return
    raise AssertionError('Expected intended rejection: ' + text)


def run():
    checked = []
    with tempfile.TemporaryDirectory(prefix='1364-custody-controls-') as folder:
        root = Path(folder); payload = b'whole-original-fixture\x00\xff'
        original = root / 'original'; original.write_bytes(payload)
        obj = {'whole_bytes': len(payload), 'whole_sha256': hashlib.sha256(payload).hexdigest()}
        raw = gzip.compress(payload, mtime=0)
        pin = {'path': 'frames/a.gz', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
               'decoded_bytes': len(payload), 'decoded_sha256': obj['whole_sha256'], 'offset': 0, 'ordinal': 0}
        custody.split_original(original, obj, [pin], root)
        custody.restore_original(root, obj, [pin], root / 'restored')
        assert (root / 'restored').read_bytes() == payload
        checked.append('complete exact fragment positive')
        reject(lambda: custody.ordinary(root, '../outside'), 'Unsafe ordinary')
        reject(lambda: custody.ordinary(root, str(original)), 'Unsafe ordinary')
        (root / 'link').symlink_to(root / 'frames', target_is_directory=True)
        reject(lambda: custody.ordinary(root, 'link/a.gz'), 'Symlink')
        checked.extend(['traversal', 'absolute', 'ancestor symlink'])
        reject(lambda: custody.budget([pin, pin]), 'Duplicate ordinary')
        reject(lambda: custody.budget([{**pin, 'decoded_bytes': custody.CAP+1}]), 'encoded/decoded')
        reject(lambda: custody.budget([pin], custody.TOTAL), 'phase budget')
        checked.extend(['duplicate descriptor', 'decoded cap', 'aggregate reserved output cap'])
        reject(lambda: custody.restore_original(root, obj, [{**pin, 'offset': 1}], root/'bad-offset'), 'continuity')
        reject(lambda: custody.restore_original(root, {**obj, 'whole_sha256': '0'*64}, [pin], root/'bad-whole'), 'reconstructed original')
        # Coherently rehashed compressed expansion still cannot overrun decoded pin.
        long = gzip.compress(payload+b'extra', mtime=0); (root/'frames/long.gz').write_bytes(long)
        bigger = {**pin, 'path':'frames/long.gz','bytes':len(long),'sha256':hashlib.sha256(long).hexdigest()}
        reject(lambda: custody.restore_original(root,obj,[bigger],root/'bad-growth'), 'Decoded fragment growth')
        checked.extend(['fragment offset', 'whole relation', 'coherently rebound decoded growth'])
        # Actual opened stream contains seven bytes despite post-open stat reporting three.
        grow=root/'grow';grow.write_bytes(b'1234567');real_stat=custody.os.fstat
        def stale(fd):
            s=real_stat(fd);return types.SimpleNamespace(st_mode=s.st_mode,st_size=3)
        with patch.object(custody.os,'fstat',stale):
            reject(lambda: custody.digest(grow,3,hashlib.sha256(b'1234567').hexdigest()), 'Opened whole-file growth')
        checked.append('opened stream growth despite stale stat')
        archive=root/'archive.zip';name='1901_1930/koppen_geiger_0p00833333.tif'
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr(name,payload)
        with zipfile.ZipFile(archive) as z:info=z.getinfo(name)
        member={'archive_entry':name,'path':'members/'+name,'bytes':len(payload),
                'sha256':obj['whole_sha256'],'ZIP_CRC32':zlib.crc32(payload),
                'ZIP_compressed_bytes':info.compress_size}
        custody.extract_members(archive,[member],root)
        assert (root/member['path']).read_bytes()==payload
        reject(lambda:custody.extract_members(archive,[{**member,'archive_entry':'../foreign'}],root),'Missing/duplicate')
        reject(lambda:custody.extract_members(archive,[{**member,'bytes':len(payload)+1}],root),'header/type/bound')
        reject(lambda:custody.extract_members(archive,[member,member],root),'Duplicate declared')
        checked.extend(['ZIP whole member positive','foreign ZIP entry','ZIP declared size drift','duplicate native roster'])
        reject(lambda:producer.authenticate_code('--output='+str(root/'forbidden')), 'Exact immutable')
        assert not (root/'forbidden').exists();checked.append('Git option rejected before operation')
        gate=custody.ReadGate([original]); assert gate.call(lambda: original.read_bytes())==payload
        reject(lambda: custody.ReadGate([original]).call(lambda: grow.read_bytes()), 'undeclared read/write')
        reject(lambda: custody.ReadGate([original]).call(lambda: original.open('wb')), 'undeclared read/write')
        reject(lambda: custody.ReadGate([original,grow]).call(lambda: original.read_bytes()), 'incomplete actual read')
        checked.extend(['actual open audit positive','undeclared actual read','actual write','missing actual required read'])
    return {'controls':checked,'count':len(checked),'status':'PASS','original_sources_or_source_proof_invoked':False}


if __name__=='__main__':
    print(json.dumps(run(),sort_keys=True))
