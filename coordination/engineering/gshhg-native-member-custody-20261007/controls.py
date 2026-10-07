"""Directed controls use the real source getter, parser and native reader."""
import argparse
import copy
import datetime
import gzip
import hashlib
import io
import json
import os
import pathlib
import struct
import subprocess
import tempfile
import zipfile
from unittest import mock
import codec
import reader
import producer


def rejection(action, expected):
    try:
        action()
    except (ValueError, OSError, EOFError, gzip.BadGzipFile) as exc:
        reader.require(expected in str(exc), 'Wrong rejection branch: '+str(exc))
        return str(exc)
    raise AssertionError('Actual entry accepted adverse control: '+expected)


def native_record(identity=7, n=3, level=1):
    header = reader.HEADER.pack(identity,n,level | (15 << 8),0,1000000,0,1000000,0,0,-1,-1)
    return header+struct.pack('>6i',0,0,1000000,0,0,0)


def native_parse(raw, chunks=None, count=1):
    rows = []
    parser = reader.NativeParser(rows.append,expected_count=count)
    if chunks is None:
        chunks = [raw]
    for chunk in chunks:
        parser.feed(chunk)
    proof = parser.finish()
    return rows, proof


def fragment_pin(body, raw):
    return {'path':'x.gz','bytes':len(body),'sha256':reader.sha(body),
            'uncompressed_bytes':len(raw),'uncompressed_sha256':reader.sha(raw)}


def member_fixture():
    parts = []
    offset = 0
    for i,n in enumerate((33554432,33554432,28700472)):
        parts.append({'path':f'native-{i:02}.bin.gz','ordinal':i,'offset':offset,
                      'bytes':100,'sha256':'1'*64,'uncompressed_bytes':n,'uncompressed_sha256':'2'*64})
        offset += n
    return {'member_name':reader.MEMBER,'member_bytes':reader.MEMBER_BYTES,
            'member_sha256':reader.MEMBER_SHA,'record_count':188612,'parts':parts}


def run(repo, commit, out):
    code = producer.code_guard(repo, commit)
    result = []
    def positive(name, action):
        action()
        result.append({'case':name,'status':'PASS'})
    def negative(name, action, reason):
        result.append({'case':name,'status':'PASS','rejection':rejection(action,reason)})
    raw = native_record()
    rows, proof = native_parse(raw)
    reader.require(rows[0]['record_sha256'] == reader.sha(raw) and
                   rows[0]['coordinate_bytes_sha256'] == reader.sha(raw[44:]) and proof['native_bytes'] == len(raw),
                   'Actual complete native record SHA accounting')
    positive('crossing-header-and-coordinate-boundaries-preserves-entire-record',
             lambda:reader.require(native_parse(raw,[raw[:9],raw[9:43],raw[43:47],raw[47:]]) == (rows,proof),
                                   'Cross-fragment record changed'))
    negative('truncated-header-real-parser',lambda:native_parse(raw[:43]),'Truncated/trailing')
    negative('truncated-coordinate-real-parser',lambda:native_parse(raw[:-1]),'Truncated/trailing')
    negative('trailing-byte-real-parser',lambda:native_parse(raw+b'x'),'Truncated/trailing')
    negative('duplicate-record-real-parser',lambda:native_parse(raw+raw,count=2),'Duplicate/invalid')
    bad = bytearray(raw);bad[4:8]=struct.pack('>i',-1)
    negative('negative-point-count-real-parser',lambda:native_parse(bytes(bad)),'Duplicate/invalid')
    bad = bytearray(raw);bad[4:8]=struct.pack('>i',2147483647)
    negative('impossible-point-byte-count-before-payload',lambda:native_parse(bytes(bad)),'Impossible native')
    bad = bytearray(raw);bad[8:12]=struct.pack('>i',0)
    negative('unknown-level-real-parser',lambda:native_parse(bytes(bad)),'Unknown native level')
    negative('missing-record-identity-count',lambda:native_parse(raw,count=2),'Incomplete native')
    positive('fixed-three-part-index-production-guard',lambda:reader.member_index(member_fixture()))
    for label, mutate, reason in (
        ('missing',lambda i:i['parts'].pop(),'Complete three'),
        ('extra',lambda i:i['parts'].append(i['parts'][0]),'Complete three'),
        ('reordered',lambda i:i['parts'].reverse(),'Duplicate/reordered'),
        ('duplicate-path',lambda i:i['parts'][1].update(path=i['parts'][0]['path']),'Duplicate/reordered'),
        ('wrong-offset',lambda i:i['parts'][1].update(offset=0),'Duplicate/reordered'),
        ('wrong-member-coherently-rebound',lambda i:i.update(member_name='gshhs_h.b',member_sha256='3'*64),
         'Fixed original'),
        ('wrong-original-wholehash-coherently-rebound',lambda i:i.update(member_sha256='3'*64),'Fixed original'),
        ('decoded-overbound',lambda i:i['parts'][0].update(uncompressed_bytes=reader.LIMIT+1),'Declared ordinary'),
        ('encoded-overbound',lambda i:i['parts'][0].update(bytes=reader.LIMIT+1),'Declared ordinary'),
        ('traversal',lambda i:i['parts'][0].update(path='../x.gz'),'Unsafe ordinary'),
        ('absolute',lambda i:i['parts'][0].update(path='/x.gz'),'Unsafe ordinary')):
        index=member_fixture();mutate(index)
        negative('native-index-'+label,lambda i=index:reader.member_index(i),reason)
    encoded = codec.deterministic_gzip(raw)
    pin = fragment_pin(encoded,raw)
    positive('actual-small-gzip-production-decoder',lambda:reader.require(b''.join(reader.decoded_chunks(pin,encoded)) == raw,
                                                                        'Actual decoder changed bytes'))
    altered=dict(pin,uncompressed_bytes=len(raw)-1)
    negative('actual-decoded-size-bomb-coherently-pinned-encoded',
             lambda:list(reader.decoded_chunks(altered,encoded)),'Actual native decoded bound')
    altered=dict(pin,uncompressed_sha256='4'*64)
    negative('actual-decoded-hash-disagreement',lambda:list(reader.decoded_chunks(altered,encoded)),
             'Whole native decoded fragment')
    corrupted=encoded[:-1]+bytes([encoded[-1]^1]);altered=fragment_pin(corrupted,raw)
    negative('gzip-trailer-coherently-rehashed',lambda:list(reader.decoded_chunks(altered,corrupted)),
             'Incorrect length')
    # Tiny independent Git corpus exercises production mode/OID/pre-read guards.
    with tempfile.TemporaryDirectory(prefix='1376-controls-',dir=repo/'.cache') as tmp:
        root=pathlib.Path(tmp)
        def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE)
        git('init','-q');(root/'body.bin').write_bytes(raw);(root/'link').symlink_to('body.bin')
        git('add','body.bin','link');git('-c','user.name=Custody control','-c','user.email=control@example.invalid',
                                        'commit','-qm','bounded immutable control')
        fixed=git('rev-parse','HEAD').decode().strip();oid=git('rev-parse','HEAD:body.bin').decode().strip()
        source={'commit':fixed,'path':'body.bin','mode':'100644','blob':oid,'bytes':len(raw),'sha256':reader.sha(raw)}
        admitted=reader.GitSources(root,[source])
        positive('actual-Git-ordinary-source',lambda:reader.require(b''.join(admitted.stream(source)) == raw,'Changed body'))
        negative('undeclared-source-request-before-Git-read',lambda:list(admitted.stream(dict(source,path='absent'))),
                 'Undeclared/changed')
        changed=dict(source,blob='1'*40);wrong=reader.GitSources(root,[changed])
        negative('coherently-pinned-wrong-original-OID',lambda:list(wrong.stream(changed)),'Original source mode/OID')
        changed=dict(source,bytes=len(raw)-1);wrong=reader.GitSources(root,[changed])
        negative('actual-pre-read-stat-mismatch',lambda:list(wrong.stream(changed)),'Pre-read ordinary')
        symlink_oid=git('rev-parse','HEAD:link').decode().strip()
        changed=dict(source,path='link',blob=symlink_oid,bytes=len('body.bin'),sha256=reader.sha(b'body.bin'))
        wrong=reader.GitSources(root,[changed])
        negative('actual-Git-symlink-original-body',lambda:list(wrong.stream(changed)),'Nonordinary Git source')
        negative('source-declared-overbound-before-Git-body',
                 lambda:reader.GitSources(root,[dict(source,bytes=reader.LIMIT+1)]),'Declared ordinary')
        negative('duplicate-source-allowlist',lambda:reader.GitSources(root,[source,source]),'Duplicate source identity')
        # The real directory reader checks all eighteen metadata rows without
        # opening any member body; coherent metadata changes hit identity checks.
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for i in range(18):z.writestr(f'member-{i:02}.b',bytes([i]))
        archive.seek(0)
        with zipfile.ZipFile(archive) as z:
            inventory=[{'name':x.filename,'bytes':x.file_size,'compressed_bytes':x.compress_size,
                        'compression':x.compress_type,'crc32':x.CRC,'sha256':reader.sha(bytes([i]))}
                       for i,x in enumerate(z.infolist())]
            positive('actual-all-eighteen-directory-positive-no-body-read',
                     lambda:reader.require(len(producer.directory_proof(z,inventory))==18,'Directory count'))
            for label,mutate in (
                ('wrong-member',lambda v:v[0].update(name='foreign.b')),
                ('reordered',lambda v:v.reverse()),
                ('wrong-crc',lambda v:v[0].update(crc32=v[0]['crc32']^1)),
                ('wrong-compressed-size',lambda v:v[0].update(compressed_bytes=v[0]['compressed_bytes']+1))):
                changed=copy.deepcopy(inventory);mutate(changed)
                negative('actual-eighteen-directory-'+label,
                         lambda v=changed:producer.directory_proof(z,v),'Original eighteen ZIP directory')
            original_flag=z.infolist()[0].flag_bits
            try:
                z.infolist()[0].flag_bits |= 1
                negative('actual-eighteen-directory-encryption-rejection',
                         lambda:producer.directory_proof(z,inventory),'Original eighteen ZIP directory')
            finally:z.infolist()[0].flag_bits=original_flag
        negative('existing-output-before-run-creation',lambda:producer.fresh_output(repo,root),
                 'Fresh exclusive owned cache')
        original_codec_file=codec.__file__
        try:
            codec.__file__=str(root/'foreign-codec.py')
            negative('actual-imported-codec-foreign-module',lambda:producer.code_guard(repo,commit),
                     'Actual imported project module')
        finally:codec.__file__=original_codec_file
        (root/'x.gz').write_bytes(encoded)
        positive('actual-native-directory-getter',lambda:reader.require(reader.directory_body(root,pin)==encoded,
                                                                       'Directory body changed'))
        (root/'link.gz').symlink_to('x.gz')
        negative('actual-native-alias-symlink',lambda:reader.directory_body(root,dict(pin,path='link.gz')),
                 'Native alias symlink')
        wrongpin=dict(pin,bytes=len(encoded)+1)
        negative('actual-native-alias-stat-mismatch',lambda:reader.directory_body(root,wrongpin),
                 'Ordinary native alias size')
        linked=root/'linked-root';linked.symlink_to(root,target_is_directory=True)
        negative('actual-native-symlink-root-before-resolve',lambda:reader.directory_body(linked,pin),
                 'Native root symlink')
        index=member_fixture();first=index['parts'][0]
        first.update(bytes=len(encoded),sha256=reader.sha(encoded))
        invoked=[]
        def side_effect_consumer(stream, receipt):
            invoked.append(True)
        negative('entire-member-validation-before-any-consumer',
                 lambda:reader.consume_native(index,lambda part:encoded,side_effect_consumer,root),
                 'Whole native decoded fragment')
        reader.require(not invoked,'Failed whole-member validation performed consumer side effect')
        corrupted=encoded[:-1]+bytes([encoded[-1]^1])
        index=member_fixture();index['parts'][0].update(bytes=len(corrupted),sha256=reader.sha(corrupted))
        negative('coherently-rehashed-corrupt-native-before-consumer',
                 lambda:reader.consume_native(index,lambda part:corrupted,side_effect_consumer,root),
                 'Incorrect length')
        reader.require(not invoked,'Corrupt native performed consumer side effect')
        negative('native-consumer-scratch-symlink-root',
                 lambda:reader.consume_native(member_fixture(),lambda part:encoded,side_effect_consumer,linked),
                 'Native scratch root symlink')
        original_file=reader.__file__
        try:
            reader.__file__=str(root/'foreign-reader.py')
            negative('actual-imported-reader-foreign-module',lambda:producer.code_guard(repo,commit),
                     'Actual imported project module')
        finally:
            reader.__file__=original_file
        negative('branch-ref-code-selector',lambda:producer.code_guard(repo,'HEAD'),'Full immutable')
        negative('short-SHA-code-selector',lambda:producer.code_guard(repo,commit[:8]),'Full immutable')
        for owner, attr in ((reader.NativeParser,'feed'),(reader.GitSources,'stream'),(producer,'generate')):
            original=getattr(owner,attr)
            try:
                setattr(owner,attr,lambda *a,**k:None)
                negative('actual-in-memory-callable-'+attr,lambda:producer.code_guard(repo,commit),
                         'Actual in-memory project callable differs')
            finally:
                setattr(owner,attr,original)
        original_unpack=producer.struct.unpack
        try:
            producer.struct.unpack=lambda *a:None
            negative('actual-standard-runtime-callable-binding',producer.runtime,'Actual runtime callable')
        finally:
            producer.struct.unpack=original_unpack
        original_here=producer.HERE
        try:
            runtime_pin=json.loads((original_here/'runtime-pins.json').read_bytes())
            runtime_pin['whole_runtime_files'][0]['sha256']='0'*64
            (root/'runtime-pins.json').write_text(json.dumps(runtime_pin))
            producer.HERE=root
            negative('actual-frozen-whole-runtime-file-hash',producer.runtime,'Pinned whole runtime file')
        finally:
            producer.HERE=original_here
        index=member_fixture();index['parts'][0].update(bytes=len(encoded),sha256=reader.sha(encoded))
        def changing_index(part):
            index['member_sha256']='0'*64
            return encoded
        negative('source-index-mutation-by-getter-before-consumer',
                 lambda:reader.consume_native(index,changing_index,side_effect_consumer,root),
                 'Native source index changed during validation')
        reader.require(not invoked,'Index-mutation case performed consumer side effect')
        fixed_sources=json.loads((producer.HERE/'input-index.json').read_bytes())
        for sizes in ([],[33554432]*2,[33554433,33554431,28700472],[True,33554432,28700472],
                      [33554432.0,33554432,28700472],[33554432,33554432,28700471]):
            bad=copy.deepcopy(fixed_sources);bad['decoded_fragment_sizes']=sizes
            negative('actual-decoded-fragment-size-list-'+repr(sizes),
                     lambda v=bad:producer.validate_source_index(v),'Exact bounded three decoded')
        (root/'x.gz').write_bytes(encoded)
        ordinary_open=pathlib.Path.open
        class Growing:
            def __init__(self,path):
                self.path=path;self.f=ordinary_open(path,'rb');self.first=True
            def __enter__(self):return self
            def __exit__(self,*args):self.f.close()
            def read(self,n):
                data=self.f.read(n)
                if self.first:
                    self.first=False
                    with ordinary_open(self.path,'ab') as other:other.write(b'x')
                return data
        def growing_open(path,*args,**kwargs):
            if path==root/'x.gz' and args==('rb',):return Growing(path)
            return ordinary_open(path,*args,**kwargs)
        with mock.patch.object(pathlib.Path,'open',growing_open):
            negative('actual-growing-ordinary-native-body-before-append',
                     lambda:reader.directory_body(root,pin),'Actual encoded native alias grew')
    # No source payload is decompressed by these bounded controls.
    value={'status':'PASS','execution_commit':commit,'code':code,'controls':result,'count':len(result),
           'runtime':producer.runtime(),'command':__import__('sys').argv,'pid':os.getpid(),
           'actual_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'limits':['Bounded directed fixtures, not complete original source executions or physical approval.']}
    out=producer.fresh_output(repo,out);out.mkdir(parents=True,exist_ok=False)
    producer.exclusive(out/'controls.json',codec.canonical_json(value))
    print(json.dumps({'status':'PASS','count':len(result)}))
    return value


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=pathlib.Path,required=True)
    ap.add_argument('--commit',required=True);ap.add_argument('--out',type=pathlib.Path,required=True)
    a=ap.parse_args();run(a.repo,a.commit,a.out)
