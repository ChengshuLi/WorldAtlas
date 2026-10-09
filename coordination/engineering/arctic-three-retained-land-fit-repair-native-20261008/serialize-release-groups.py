"""Job-specific finished release batches; unchanged original preparation codec."""
import sys,pathlib,os,json,gzip,hashlib,marshal,ctypes,datetime
CAP=32*1024*1024

def ordinary(file):
    file=pathlib.Path(file)
    assert file.is_absolute() and '..' not in file.parts
    for parent in [file,*file.parents]:assert not parent.is_symlink()
    stat=file.stat();assert file.is_file();return stat

def admitted_read(pin,installed=False):
    file=pathlib.Path(pin['path']);before=ordinary(file)
    assert before.st_size==pin['bytes'] and before.st_mode&0o777==pin['mode']
    assert installed or before.st_size<=CAP
    with open(file,'rb') as stream:
        raw=stream.read(pin['bytes']+1);held=os.fstat(stream.fileno())
    assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
    after=ordinary(file)
    for field in ('st_dev','st_ino','st_size','st_mode','st_mtime_ns','st_ctime_ns'):
        assert getattr(before,field)==getattr(held,field)==getattr(after,field)
    return raw

def load_codec(root):
    sys.path.insert(0,str(pathlib.Path(root)/'scripts'))
    from evidence import immutable
    return immutable

def loaded_paths():
    files={os.path.realpath(sys.executable)}
    for module in list(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if file:
            if file.endswith(('.pyc','.pyo')):file=file[:-1]
            file=os.path.realpath(file)
            if os.path.isfile(file):files.add(file)
    library=ctypes.CDLL(None)
    library._dyld_image_count.restype=ctypes.c_uint32
    library._dyld_get_image_name.restype=ctypes.c_char_p
    for at in range(library._dyld_image_count()):
        file=os.path.realpath(library._dyld_get_image_name(at).decode())
        if os.path.isfile(file) and not file.startswith(('/System/','/usr/lib/')):files.add(file)
    return files

def successor_member_payload(original,header,pin):
    release=header['release'];old='geography:review:896bf79dd6e5661dfbbffba60da96fa987b9971af2b884cf52347189861ebe9e'
    assert release['version']==9 and release['metadata']['predecessor_release_id']==old
    assert original['release_id']==old and set(original)=={'release_id','ingestion_id','memberships'}
    binding=[row for row in header['complete_member_inputs'] if row['relative']==pin['relative']]
    assert len(binding)==1
    for field in ('bytes','sha256','decoded_bytes','decoded_sha256'):assert binding[0][field]==pin[field]
    offset=pin['offset'];assert isinstance(offset,int) and not isinstance(offset,bool) and 0<=offset<84833 and offset%250==0
    assert pin['relative']==f'data/geographic-releases/8-memberships-{offset}.json.gz'
    rows=original['memberships'];assert len(rows)==min(250,84833-offset)
    assert original['ingestion_id']==f"{old}:memberships:{offset}"
    return {'release_id':release['id'],'memberships':rows,'ingestion_id':f"{release['id']}:memberships:{offset}"}

def run(plan,output):
    root=pathlib.Path(plan['root']);output=pathlib.Path(output)
    assert output.is_absolute() and '..' not in output.parts and output.is_relative_to(root/'.cache')
    for parent in [output,*output.parents]:assert not parent.is_symlink()
    assert not output.exists()
    assert plan['kind']=='complete-retained-record-release-batch-serialization'
    assert sys.version_info[:3]==(3,12,14) and os.path.realpath(sys.executable)==plan['executable']
    assert sys.flags.isolated and sys.dont_write_bytecode
    assert plan['source_head']==os.environ['WORLDATLAS_SELECTED_NATIVE_HEAD']
    pins=[*plan['inputs'],*plan['code'],*plan['runtime_files']]
    assert len(pins)<=512 and len({pin['path'] for pin in pins})==len(pins)
    cost=sum(pin['bytes']+pin.get('decoded_bytes',0) for pin in pins)+plan['output_reserve']+plan['metadata_bytes']
    assert cost<=256*1024*1024
    for pin in pins:
        stat=ordinary(pin['path']);assert stat.st_size==pin['bytes'] and stat.st_mode&0o777==pin['mode']
        assert pin in plan['runtime_files'] or (pin['bytes']<=CAP and pin.get('decoded_bytes',0)<=CAP)
    for pin in [*plan['runtime_files'],*plan['code']]:admitted_read(pin,pin in plan['runtime_files'])
    codec=load_codec(root)
    callbacks=[run,ordinary,admitted_read,load_codec,loaded_paths,successor_member_payload,codec.canonical_json,codec.deterministic_gzip]
    for function in callbacks:
        filename=os.path.realpath(function.__code__.co_filename)
        matches=[pin for pin in pins if pin['path']==filename];assert len(matches)==1
        expected={code.co_name:code for code in compile(admitted_read(matches[0]),filename,'exec').co_consts if hasattr(code,'co_code')}
        assert function.__code__==expected[function.__name__]
    captured=[(fn,fn.__code__,fn.__defaults__,fn.__kwdefaults__) for fn in callbacks]
    allowed={pin['path'] for pin in pins}
    def guard():
        assert callbacks[-2:]==[codec.canonical_json,codec.deterministic_gzip]
        for fn,code,defaults,kwdefaults in captured:
            assert fn.__code__ is code and fn.__defaults__ is defaults and fn.__kwdefaults__ is kwdefaults
        assert loaded_paths()<=allowed
        for pin in [*plan['runtime_files'],*plan['code']]:admitted_read(pin,pin in plan['runtime_files'])
    guard();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    header=json.loads(admitted_read(plan['header']));assert header['issue']==1520 and header['activated'] is False
    assert header['membership_count']==84833 and header['memberships_reused_as_complete_records'] is True
    release=header['release'];old='geography:review:896bf79dd6e5661dfbbffba60da96fa987b9971af2b884cf52347189861ebe9e'
    assert release['version']==9 and release['metadata']['predecessor_release_id']==old
    products=[];retained=0
    output.mkdir(parents=True)
    def write(name,payload,route):
        nonlocal retained
        assert '/' not in name and '\\' not in name and name.endswith('.json.gz')
        raw=codec.canonical_json(payload);assert len(raw)<=1048576
        encoded=codec.deterministic_gzip(raw);assert gzip.decompress(encoded)==raw
        retained+=len(raw)+len(encoded);assert retained+1024*1024<=plan['output_reserve']
        with (output/name).open('xb') as stream:stream.write(encoded)
        os.chmod(output/name,0o644)
        products.append(dict(path=name,route=route,bytes=len(encoded),sha256=hashlib.sha256(encoded).hexdigest(),
            decoded_bytes=len(raw),payload_sha256=hashlib.sha256(raw).hexdigest(),mode='100644'))
    members=0
    for pin in plan['members']:
        raw=gzip.decompress(admitted_read(pin));assert len(raw)==pin['decoded_bytes'] and hashlib.sha256(raw).hexdigest()==pin['decoded_sha256']
        original=json.loads(raw);assert codec.canonical_json(original)==raw
        payload=successor_member_payload(original,header,pin);rows=original['memberships'];offset=pin['offset']
        assert payload['memberships'] is rows and len(codec.canonical_json(payload))==len(raw)
        write(f'9-memberships-{offset}.json.gz',payload,'/api/geography/stage');members+=len(rows)
    if plan['include_headers']:
        write('sources-9.json.gz',{'sources':[header['source']],'ingestion_id':release['id']+':sources'},'/api/records/import')
        write('release-9.json.gz',{'release':release,'ingestion_id':release['id']+':header'},'/api/geography/stage')
        write('9-changes-0.json.gz',{'release_id':release['id'],'changes':header['changes'],'ingestion_id':release['id']+':changes:0'},'/api/geography/stage')
    for pin in plan['inputs']:admitted_read(pin)
    guard()
    report={'version':1,'issue':1520,'source_head':plan['source_head'],'complete_phase_bytes':cost,'descriptors':len(pins),
        'release_id':release['id'],'memberships':members,'products':products,'actual_encoded_decoded_output_bytes':retained,
        'complete_members_preserved':True,'scientific_algorithms_rerun':False,'activation':False,
        'codec':'Unchanged evidence.immutable canonical_json and deterministic_gzip'}
    encoded=json.dumps(report,separators=(',',':')).encode()+b'\n';assert len(encoded)+retained<=plan['output_reserve']
    with (output/'serialization-proof.json').open('xb') as stream:stream.write(encoded)
    os.chmod(output/'serialization-proof.json',0o644)
    print(json.dumps({'started_at':started,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),**report}))

if __name__=='__main__':
    if sys.argv[1]=='--runtime-only':
        load_codec(sys.argv[2]);files=sorted(loaded_paths()-{os.path.realpath(__file__),str(pathlib.Path(sys.argv[2])/'scripts/evidence/immutable.py')})
        print(json.dumps([dict(path=p,bytes=ordinary(p).st_size,sha256=hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest(),mode=ordinary(p).st_mode&0o777) for p in files]))
    else:
        raw=pathlib.Path(sys.argv[1]).read_bytes();assert hashlib.sha256(raw).hexdigest()==os.environ['WORLDATLAS_SELECTED_NATIVE_PLAN_RAW_SHA256']
        run(json.loads(raw),sys.argv[2])
