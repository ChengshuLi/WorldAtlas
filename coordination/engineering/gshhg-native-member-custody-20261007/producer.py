"""Issue1376: declared original ZIP -> exact native-byte aliases, without GIS."""
import argparse
import datetime
import hashlib
import json
import types
import gzip
import struct
import _struct
import _hashlib
import _json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import zipfile
import zlib
import codec
import reader

HERE = pathlib.Path(__file__).resolve().parent
NS = 'coordination/engineering/gshhg-native-member-custody-20261007/'
CODE = ('producer.py','reader.py','controls.py','codec.py','input-index.json','runtime-pins.json')
SOURCE_BYTES = 118671090
ZIP_BYTES = 118617033
ZIP_SHA = '28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc'
CODEC_SHA = 'b7ff607b7774595788396e94f08fc29d750e4032624eb93732a5735c1ddcf7fd'


def callable_guard(module, raw, names):
    # Marshal reference/intern tables can differ for byte-identical loaded code.
    # Compare every public execution field and recursively typed constants instead.
    fields = ('co_argcount','co_posonlyargcount','co_kwonlyargcount','co_nlocals',
              'co_stacksize','co_flags','co_code','co_consts','co_names','co_varnames',
              'co_filename','co_name','co_qualname','co_firstlineno','co_linetable',
              'co_exceptiontable','co_freevars','co_cellvars')
    def shape(value):
        if isinstance(value,types.CodeType):
            return ['code',[[name,shape(getattr(value,name))] for name in fields]]
        if value is None:return ['none']
        if value is Ellipsis:return ['ellipsis']
        if type(value) is bool:return ['bool',value]
        if type(value) is int:return ['int',str(value)]
        if type(value) is float:return ['float',struct.pack('>d',value).hex()]
        if type(value) is complex:return ['complex',shape(value.real),shape(value.imag)]
        if type(value) is str:return ['str',value]
        if type(value) is bytes:return ['bytes',value.hex()]
        if type(value) is tuple:return ['tuple',[shape(x) for x in value]]
        if type(value) is frozenset:
            return ['frozenset',sorted((shape(x) for x in value),key=lambda x:json.dumps(x,sort_keys=True))]
        raise ValueError('Unsupported immutable callable constant: '+type(value).__name__)
    def fingerprint(code):
        return json.dumps(shape(code),ensure_ascii=True,separators=(',',':')).encode()
    compiled = compile(raw,str(pathlib.Path(module.__file__)), 'exec')
    expected = {}
    def collect(code):
        expected[code.co_qualname] = code
        for value in code.co_consts:
            if isinstance(value,types.CodeType):
                collect(value)
    collect(compiled)
    rows = []
    for name in names:
        value = module
        for part in name.split('.'):
            value = getattr(value,part)
        actual = getattr(value,'__code__',None)
        if actual is None or name not in expected or fingerprint(actual) != fingerprint(expected[name]):
            raise ValueError('Actual in-memory project callable differs: '+module.__name__+'.'+name)
        rows.append({'module':module.__name__,'callable':name,
                     'code_sha256':hashlib.sha256(fingerprint(actual)).hexdigest()})
    return rows


def code_guard(repo, commit):
    reader.require(re.fullmatch('[a-f0-9]{40}', commit) is not None, 'Full immutable execution commit required')
    reader.require(subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip() == commit,
                   'Exact current execution commit required')
    proof = []
    for name in CODE:
        path = HERE/name
        reader.require(not path.is_symlink() and path.is_file(), 'Ordinary executed dependency')
        raw = path.read_bytes()
        original = subprocess.check_output(['git','-C',str(repo),'show',commit+':'+NS+name])
        reader.require(raw == original, 'Executed code/config differs: '+name)
        proof.append({'path':NS+name,'bytes':len(raw),'sha256':reader.sha(raw)})
    for module in (reader, codec):
        path = pathlib.Path(module.__file__).resolve()
        reader.require(path.parent == HERE and path.name in CODE and path.read_bytes() ==
                       subprocess.check_output(['git','-C',str(repo),'show',commit+':'+NS+path.name]),
                       'Actual imported project module differs')
    reader.require(reader.sha((HERE/'codec.py').read_bytes()) == CODEC_SHA, 'Original codec changed')
    closures = [
        (reader, ('require','sha','safe_path','bounds','GitSources.__init__','GitSources._git',
                  'GitSources.admitted','GitSources.stream','GitSources.small','NativeParser.__init__',
                  'NativeParser._begin','NativeParser.feed','NativeParser.finish','member_index',
                  'directory_body','decoded_chunks','_verify_native_chunks','consume_native')),
        (codec, ('deterministic_gzip','canonical_json')),
        (sys.modules[__name__], ('callable_guard','code_guard','runtime','file_sha','source_index',
                                'validate_source_index','preflight','fresh_output','exclusive','directory_proof',
                                'Records.__init__','Records.emit','Records.flush','generate'))]
    for module, names in closures:
        raw = subprocess.check_output(['git','-C',str(repo),'show',commit+':'+NS+pathlib.Path(module.__file__).name])
        proof.extend(callable_guard(module,raw,names))
    return proof


def runtime():
    pin = json.loads((HERE/'runtime-pins.json').read_bytes())
    reader.require(sys.version.split()[0] == pin['python'] == '3.12.14', 'Pinned Python runtime differs')
    reader.require(zlib.ZLIB_VERSION == pin['zlib_compile'] and zlib.ZLIB_RUNTIME_VERSION == pin['zlib_runtime'],
                   'Pinned zlib runtime differs')
    reader.require(str(pathlib.Path(sys.executable).resolve()) ==
                   str(pathlib.Path(pin['executable']).resolve()), 'Pinned executable path differs')
    for item in pin['whole_runtime_files']:
        path = pathlib.Path(item['path'])
        reader.require(path.is_file() and path.stat().st_size == item['bytes'] and
                       file_sha(path) == item['sha256'], 'Pinned whole runtime file differs: '+item['role'])
    for name, expected in pin['stdlib_module_paths'].items():
        module = sys.modules.get(name)
        reader.require(module is not None and str(pathlib.Path(module.__file__).resolve()) == expected,
                       'Actual standard library module path differs: '+name)
    reader.require(hashlib.sha256 is _hashlib.openssl_sha256 and struct.unpack is _struct.unpack,
                   'Actual runtime callable binding differs')
    return {'python':sys.version,'executable':sys.executable,'zlib_compile':zlib.ZLIB_VERSION,
            'zlib_runtime':zlib.ZLIB_RUNTIME_VERSION,'executable_sha256':file_sha(pathlib.Path(sys.executable))}


def file_sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(reader.BLOCK), b''):
            digest.update(block)
    return digest.hexdigest()


def source_index():
    return validate_source_index(json.loads((HERE/'input-index.json').read_bytes()))


def validate_source_index(value):
    reader.require(isinstance(value.get('decoded_fragment_sizes'),list) and
                   len(value['decoded_fragment_sizes']) == 3 and
                   all(type(x) is int for x in value['decoded_fragment_sizes']) and
                   value['decoded_fragment_sizes'] == [33554432,33554432,28700472],
                   'Exact bounded three decoded fragment sizes required')
    pins = value['source_files']
    reader.require(len(pins) == value['source_count'] == 12 and
                   sum(p['bytes'] for p in pins) == value['source_encoded_bytes'] == SOURCE_BYTES,
                   'Complete twelve original source inputs required')
    reader.require(value['zip_bytes'] == ZIP_BYTES and value['zip_sha256'] == ZIP_SHA and
                   value['member_name'] == reader.MEMBER and value['member_bytes'] == reader.MEMBER_BYTES and
                   value['member_sha256'] == reader.MEMBER_SHA and value['record_count'] == 188612,
                   'Original ZIP/native authority differs')
    parts = [p for p in pins if 'ordinal' in p]
    offset = 0
    reader.require(len(parts) == 4, 'Complete four original ZIP fragments required')
    for ordinal, p in enumerate(parts):
        reader.require(p['ordinal'] == ordinal and p['offset'] == offset, 'Original ZIP order/offset')
        offset += p['bytes']
    reader.require(offset == ZIP_BYTES, 'Whole original ZIP size differs')
    return value


def preflight(repo, index):
    source = reader.GitSources(repo, index['source_files'])
    small = {}
    for pin in index['source_files']:
        if 'ordinal' in pin:
            for block in source.stream(pin):
                pass
        else:
            small[pin['path']] = source.small(pin)
    reader.require(len(source.receipts) == 12, 'Incomplete actual source-read closure')
    inventory = json.loads(small[index['inherited_inventory_path']])
    reader.require(len(inventory) == 18 and len({r['name'] for r in inventory}) == 18,
                   'Original eighteen-member inventory differs')
    for row in inventory:
        reader.safe_path(row['name'])
        reader.require(re.fullmatch('[a-f0-9]{64}', row['sha256']) is not None,
                       'Inherited original member body hash missing')
    target = next(r for r in inventory if r['name'] == reader.MEMBER)
    reader.require(target['bytes'] == reader.MEMBER_BYTES and target['sha256'] == reader.MEMBER_SHA,
                   'Inherited original target member differs')
    return source, small, inventory


def fresh_output(repo, path):
    repo = pathlib.Path(repo).resolve()
    path = pathlib.Path(path)
    reader.require(path.is_absolute() and '..' not in path.parts and
                   path.resolve().is_relative_to(repo/'.cache') and not path.exists() and not path.is_symlink(),
                   'Fresh exclusive owned cache run required')
    for parent in path.parents:
        reader.require(not parent.is_symlink(), 'Output symlink ancestor')
        if parent == repo:
            break
    reader.require(shutil.disk_usage(repo).free >= 536870912, 'Operating free-space reservation')
    return path


def exclusive(path, raw):
    reader.require(len(raw) <= reader.LIMIT, 'Ordinary output encoded bound')
    with path.open('xb') as stream:
        stream.write(raw)
    reader.require(path.stat().st_size == len(raw) and file_sha(path) == reader.sha(raw),
                   'Exclusive output whole readback differs')
    return {'path':path.name,'bytes':len(raw),'sha256':reader.sha(raw),'hash_kind':'file-bytes'}


def directory_proof(zipped, inherited):
    info = zipped.infolist()
    reader.require(len(info) == len(inherited) == 18 and len({x.filename for x in info}) == 18,
                   'Original ZIP member count differs')
    results = []
    for actual, original in zip(info, inherited):
        reader.safe_path(actual.filename)
        found = {'name':actual.filename,'bytes':actual.file_size,'compressed_bytes':actual.compress_size,
                 'compression':actual.compress_type,'crc32':actual.CRC}
        reader.require(all(found[k] == original[k] for k in found) and not (actual.flag_bits & 1),
                       'Original eighteen ZIP directory rows differ')
        results.append(dict(original, directory_verified=True,
                            body_verification='inherited-upstream; not-decompressed-or-recomputed-this-phase'))
    return results


class Records:
    def __init__(self, root):
        self.root = root
        self.buffer = bytearray()
        self.outputs = []
        self.count = 0

    def emit(self, row):
        body = codec.canonical_json(row)
        reader.require(len(body) <= reader.BLOCK, 'Ordinary native record metadata bound')
        if self.buffer and len(self.buffer)+len(body) > reader.BLOCK:
            self.flush()
        self.buffer.extend(body)
        self.count += 1

    def flush(self):
        if not self.buffer:
            return
        raw = bytes(self.buffer)
        encoded = codec.deterministic_gzip(raw)
        pin = exclusive(self.root/f'records-{len(self.outputs):03}.jsonl.gz', encoded)
        pin.update(uncompressed_bytes=len(raw), uncompressed_sha256=reader.sha(raw))
        self.outputs.append(pin)
        self.buffer.clear()


def generate(repo, commit, out, input_only=False):
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tick = time.monotonic()
    code = code_guard(repo, commit)
    rt = runtime()
    index = source_index()
    source, small, inventory = preflight(repo, index)
    out = fresh_output(repo, out)
    out.mkdir(parents=True, exist_ok=False)
    zip_path = out/'original.zip.scratch'
    digest = hashlib.sha256()
    length = 0
    # Complete sources have passed before any run/scratch destination is created.
    with zip_path.open('xb') as stream:
        for pin in (p for p in index['source_files'] if 'ordinal' in p):
            for block in source.stream(pin):
                stream.write(block)
                digest.update(block)
                length += len(block)
    reader.require(length == ZIP_BYTES and digest.hexdigest() == ZIP_SHA, 'Whole original ZIP differs')
    outputs = []
    native_parts = []
    downstream = None
    with zipfile.ZipFile(zip_path) as zipped:
        members = directory_proof(zipped, inventory)
        if not input_only:
            writer = Records(out)
            parser = reader.NativeParser(writer.emit)
            whole = hashlib.sha256()
            count = 0
            # Only this member is decompressed. No testzip/read-all traversal.
            with zipped.open(reader.MEMBER) as stream:
                for ordinal, expected_size in enumerate(index['decoded_fragment_sizes']):
                    raw = bytearray()
                    while len(raw) < expected_size:
                        block = stream.read(min(reader.BLOCK, expected_size-len(raw)))
                        reader.require(bool(block), 'Truncated target native member')
                        raw.extend(block)
                        whole.update(block)
                        parser.feed(block)
                        count += len(block)
                    encoded = codec.deterministic_gzip(raw)
                    pin = exclusive(out/f'native-{ordinal:02}.bin.gz', encoded)
                    pin.update(ordinal=ordinal, offset=count-len(raw),
                               uncompressed_bytes=len(raw), uncompressed_sha256=reader.sha(raw))
                    native_parts.append(pin)
                    outputs.append(pin)
                    del raw, encoded
                reader.require(not stream.read(1), 'Trailing target native bytes')
            parsed = parser.finish()
            reader.require(count == reader.MEMBER_BYTES and whole.hexdigest() == reader.MEMBER_SHA and
                           parsed['native_bytes'] == count, 'Complete original native bytes differ')
            for member_row in members:
                if member_row['name'] == reader.MEMBER:
                    member_row['body_verification'] = 'recomputed-this-phase; complete target decompression/hash/parser passed'
            writer.flush()
            reader.require(writer.count == 188612, 'Complete emitted native record roster')
            outputs.extend(writer.outputs)
            member = {'version':1,'member_name':reader.MEMBER,'member_bytes':count,
                      'member_sha256':whole.hexdigest(),'record_count':188612,'parts':native_parts,
                      'original_source_commit':index['source_delivery'],
                      'original_zip_bytes':ZIP_BYTES,'original_zip_sha256':ZIP_SHA,
                      'records':writer.outputs,'geometry_operations':False}
            outputs.append(exclusive(out/'member-index.json', codec.canonical_json(member)))
            def actual_consumer(image, receipt):
                digest = hashlib.sha256()
                count = 0
                for block in iter(lambda:image.read(reader.BLOCK),b''):
                    digest.update(block)
                    count += len(block)
                reader.require(receipt['full_validation_before_consumer'] is True and
                               count == reader.MEMBER_BYTES and digest.hexdigest() == reader.MEMBER_SHA,
                               'Actual downstream complete member callback differs')
                return dict(receipt,actual_consumer_bytes=count,actual_consumer_sha256=digest.hexdigest(),
                            native_geometry_operations=False,source_zip_reads_by_downstream=0,
                            complete_original_record_count=188612)
            downstream = reader.consume_native(member,lambda pin:reader.directory_body(out,pin),
                                               actual_consumer,out)
            outputs.append(exclusive(out/'downstream-reader.json',codec.canonical_json(downstream)))
    outputs.append(exclusive(out/'members.json', codec.canonical_json(members)))
    # Scratch removal is limited to the just-created, whole-verified virtual ZIP.
    reader.require(zip_path.stat().st_size == ZIP_BYTES and file_sha(zip_path) == ZIP_SHA,
                   'Owned original ZIP scratch changed before cleanup')
    # Preserve this actual owned virtual ZIP with the run, outside final Git payloads.
    reader.require(SOURCE_BYTES + sum(p['bytes'] for p in outputs) <= 268435456,
                   'Complete generated ordinary phase exceeds aggregate')
    report = {'status':'PASS','mode':'input-only; directory checks, no member decompression' if input_only else
              'complete native-byte custody; no GIS','execution_commit':commit,'code':code,'runtime':rt,
              'source_inputs':source.receipts,'unique_source_input_count':12,'unique_source_bytes':SOURCE_BYTES,
              'repeated_zip_source_reads':4,'original_zip_bytes':length,'original_zip_sha256':digest.hexdigest(),
              'member_payloads_decompressed':[] if input_only else [reader.MEMBER],
              'actual_downstream_reader':downstream,
              'other17_body_hashes':'inherited upstream only; not newly decompressed or recomputed',
              'outputs':outputs,'preserved_virtual_zip':{'path':zip_path.name,'bytes':ZIP_BYTES,'sha256':ZIP_SHA},
              'actual_start_utc':start,
              'actual_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'elapsed_seconds':time.monotonic()-tick,'command':sys.argv,'pid':os.getpid(),
              'limits':['Source/date/license/registration uncertainty retained; no source truth or physical approval.',
                        'Native integer bytes are unchanged; geometry validity and GIS not evaluated.']}
    exclusive(out/'report.json', codec.canonical_json(report))
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo',type=pathlib.Path,required=True)
    ap.add_argument('--commit',required=True)
    ap.add_argument('--out',type=pathlib.Path,required=True)
    ap.add_argument('--input-only',action='store_true')
    args = ap.parse_args()
    result = generate(args.repo,args.commit,args.out,args.input_only)
    print(json.dumps({'status':result['status'],'mode':result['mode'],'outputs':len(result['outputs'])}))
