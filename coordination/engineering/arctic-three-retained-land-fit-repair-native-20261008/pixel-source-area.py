"""Complete old/new target source areas using the unchanged original recipe."""
import pathlib,sys,os,json,hashlib,gzip,marshal,math,datetime,ctypes
ROOT=pathlib.Path(__file__).absolute().parents[3]
TARGETS=('atlas:physical:CAN-15:NWT','atlas:physical:CAN-25:NUN')
CAP=32*1024*1024

def ordinary(file):
    file=pathlib.Path(file)
    assert file.is_absolute() and '..' not in file.parts
    for parent in [file,*file.parents]: assert not parent.is_symlink()
    stat=file.stat();assert file.is_file()
    return stat

def admitted_read(pin,installed=False):
    file=pathlib.Path(pin['path']);before=ordinary(file)
    assert before.st_size==pin['bytes'] and before.st_mode&0o777==pin['mode']
    assert installed or before.st_size<=CAP
    with open(file,'rb') as stream:
        raw=stream.read(pin['bytes']+1)
        assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
        held=os.fstat(stream.fileno())
    after=ordinary(file)
    for field in ('st_dev','st_ino','st_size','st_mode','st_mtime_ns','st_ctime_ns'):
        assert getattr(before,field)==getattr(held,field)==getattr(after,field)
    return raw

def require_area_globals(module,np,math_module):
    flattening=1/298.257223563
    e2=flattening*(2-flattening)
    expected={'A':6378137.0,'FLATTENING':flattening,'E2':e2,'E':0.08181919084262149,'C':6378137.0**2*(1-e2)/2}
    assert module.np is np and module.math is math_module
    assert all(getattr(module,key)==value for key,value in expected.items())

def run(plan,output,guard_only=False):
    output=pathlib.Path(output)
    assert output.is_absolute() and '..' not in output.parts and output.is_relative_to(ROOT/'.cache')
    for parent in [output,*output.parents]: assert not parent.is_symlink()
    assert not output.exists()
    assert plan['kind']=='complete-old-new-two-target-source-area'
    assert plan['source_head']==os.environ['WORLDATLAS_SELECTED_NATIVE_HEAD']
    assert sys.version_info[:3]==(3,12,14) and os.path.realpath(sys.executable)==plan['executable']
    allpins=[*plan['inputs'],*plan['code'],*plan['runtime_files']]
    assert len(allpins)<=512 and len({p['path'] for p in allpins})==len(allpins)
    cost=sum(p['bytes']+p.get('decoded_bytes',0) for p in allpins)+plan['output_reserve']+plan['metadata_bytes']
    assert cost<=256*1024*1024
    for pin in allpins:
        stat=ordinary(pin['path']);assert stat.st_size==pin['bytes'] and stat.st_mode&0o777==pin['mode']
    for pin in [*plan['inputs'],*plan['code']]: assert 0<=pin['bytes']<=CAP and 0<=pin.get('decoded_bytes',0)<=CAP
    # External launcher authenticates the exact complete closure before import;
    # this complete admitted body guard repeats before source consumers.
    for pin in plan['runtime_files']: admitted_read(pin,True)
    for pin in plan['code']: admitted_read(pin)
    # Isolated Python excludes user-site discovery. Admit and authenticate exact
    # installed package bodies first, then expose only their declared roots.
    for package in ('numpy','shapely'):
        initializers=[pin for pin in plan['runtime_files'] if pathlib.Path(pin['path']).parts[-2:]==(package,'__init__.py')]
        assert len(initializers)==1
        package_root=pathlib.Path(initializers[0]['path']).parent.parent
        ordinary(initializers[0]['path']);sys.path.insert(0,str(package_root))
    sys.path.insert(0,str(ROOT/'scripts'))
    import numpy,shapely,ellipsoidal_area
    import shapely.geometry
    from shapely.geometry import shape
    assert numpy.__version__=='2.3.5' and shapely.__version__=='2.1.2' and shapely.geos_version_string=='3.13.1'
    allowed={p['path'] for p in [*plan['runtime_files'],*plan['code']]}
    def loaded_guard():
        for module in list(sys.modules.values()):
            file=getattr(module,'__file__',None)
            if file:
                if file.endswith(('.pyc','.pyo')):file=file[:-1]
                file=os.path.realpath(file)
                if os.path.isfile(file):assert file in allowed,'Unadmitted loaded module: '+file
        library=ctypes.CDLL(None)
        library._dyld_image_count.restype=ctypes.c_uint32
        library._dyld_get_image_name.restype=ctypes.c_char_p
        for ordinal in range(library._dyld_image_count()):
            file=os.path.realpath(library._dyld_get_image_name(ordinal).decode())
            if os.path.isfile(file) and not file.startswith(('/System/','/usr/lib/')):
                assert file in allowed,'Unadmitted loaded native image: '+file
    loaded_guard()
    functions=[ellipsoidal_area.area,ellipsoidal_area.ring_area,shape,run,ordinary,admitted_read,require_area_globals]
    algorithm=[pin for pin in plan['code'] if pin['path']==str(ROOT/'scripts/ellipsoidal_area.py')]
    assert len(algorithm)==1 and algorithm[0]['sha256']==plan['area_algorithm_sha256']=='4ead1c5de909b257a7b300984e4d3dc56124e9a6c0d27240662024e44fd8ed12'
    # Match actual loaded mathematical function bodies to independently pinned
    # whole source, rather than trusting a fingerprint captured after mutation.
    compiled=compile(admitted_read(algorithm[0]),algorithm[0]['path'],'exec')
    expected={code.co_name:code for code in compiled.co_consts if hasattr(code,'co_code')}
    for function in [ellipsoidal_area.area,ellipsoidal_area.ring_area]:
        assert function.__code__==expected[function.__name__]
    for function in [shape,run,ordinary,admitted_read,require_area_globals]:
        filename=os.path.realpath(function.__code__.co_filename)
        pins=[pin for pin in allpins if pin['path']==filename];assert len(pins)==1
        source=admitted_read(pins[0],pins[0] in plan['runtime_files'])
        codes={code.co_name:code for code in compile(source,filename,'exec').co_consts if hasattr(code,'co_code')}
        assert function.__code__==codes[function.__name__],function.__name__
    captured_codes=[f.__code__ for f in functions]
    native=shapely.lib.is_valid
    operators={name:getattr(numpy,name) for name in ('sin','cos','arctanh','deg2rad','dot','asarray')}
    math_operators={name:getattr(math,name) for name in ('fsum','sin','cos','isfinite','sqrt')}
    quadrature=[a.tobytes() for a in [ellipsoidal_area.NODES,ellipsoidal_area.WEIGHTS]]
    def guard():
        assert all(getattr(math,name) is value for name,value in math_operators.items())
        require_area_globals(ellipsoidal_area,numpy,math)
        assert functions[:3]==[ellipsoidal_area.area,ellipsoidal_area.ring_area,shape]
        assert shape is shapely.geometry.shape
        assert functions[3:]==[run,ordinary,admitted_read,require_area_globals]
        assert all(getattr(numpy,name) is value for name,value in operators.items())
        assert all(getattr(math,name) is value for name,value in math_operators.items())
        assert all(f.__code__ is code for f,code in zip(functions,captured_codes))
        assert shapely.lib.is_valid is native
        assert quadrature==[a.tobytes() for a in [ellipsoidal_area.NODES,ellipsoidal_area.WEIGHTS]]
        assert ellipsoidal_area.ring_area.__defaults__==(ellipsoidal_area.NODES,ellipsoidal_area.WEIGHTS)
    guard()
    if guard_only:
        loaded_guard();return {'guard_only':True,'source_body_reads':0,'source_areas_computed':0,'phase_bytes':cost}
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    pin=plan['original_context'];wire=admitted_read(pin)
    with gzip.GzipFile(fileobj=__import__('io').BytesIO(wire)) as stream:
        decoded=stream.read(pin['decoded_bytes']+1);assert len(decoded)==pin['decoded_bytes'] and not stream.read(1)
    assert hashlib.sha256(decoded).hexdigest()==pin['decoded_sha256']
    original=json.loads(decoded);assert len(original)==1500 and len({row['id'] for row in original})==1500
    assert [row['pixelIndex'] for row in original]==list(range(6001,7501))
    before=[row for row in original if row['id'] in TARGETS];assert len(before)==2
    # Retain only the complete two target records after whole-part validation.
    del original,decoded,wire
    after=json.loads(admitted_read(plan['current_rows']));assert len(after)==2 and {row['id'] for row in after}==set(TARGETS)
    installed=json.loads(admitted_read(plan['original_pixel']));assert len(installed['records'])==49625
    records=[]
    for identity in TARGETS:
        old=next(row for row in before if row['id']==identity);new=next(row for row in after if row['id']==identity)
        assert {k:v for k,v in old.items() if k!='geometry'}=={k:v for k,v in new.items() if k!='geometry'}
        values=[]
        for row in [old,new]:
            geometry=shape(row['geometry']);assert geometry.is_valid and not geometry.is_empty
            value=ellipsoidal_area.area(geometry);assert math.isfinite(value) and value>0;values.append(value)
        stored=[row for row in installed['records'] if row['id']==identity];assert len(stored)==1
        assert values[0]==stored[0]['source_wgs84_area_m2'],'Original source area must match installed exact recipe'
        records.append({'id':identity,'original_source_wgs84_area_m2':values[0],'current_source_wgs84_area_m2':values[1]})
    guard()
    for pin in allpins: admitted_read(pin,pin in plan['runtime_files'])
    loaded_guard()
    result={'version':1,'kind':plan['kind'],'records':records,'area_method':'unchanged ellipsoidal_area.area',
        'area_algorithm_sha256':plan['area_algorithm_sha256'],'physical_approval':False,'activated':False}
    raw=(json.dumps(result,separators=(',',':'))+'\n').encode()
    execution=(json.dumps({'source_head':plan['source_head'],'started_at':started,'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'phase_bytes':cost,'descriptors':len(allpins),'output_bytes':len(raw),'output_sha256':hashlib.sha256(raw).hexdigest()},separators=(',',':'))+'\n').encode()
    assert len(raw)+len(execution)<=plan['output_reserve']
    output.mkdir(parents=True)
    for name,body in [('source-areas.json',raw),('execution.json',execution)]:
        with open(output/name,'xb') as stream:stream.write(body)
    return json.loads(execution)

if __name__=='__main__':
    file=pathlib.Path(sys.argv[1]);assert ordinary(file).st_size<=262144
    raw=file.read_bytes();assert hashlib.sha256(raw).hexdigest()==os.environ['WORLDATLAS_SELECTED_NATIVE_PLAN_RAW_SHA256']
    print(json.dumps(run(json.loads(raw),sys.argv[2],guard_only=len(sys.argv)==4 and sys.argv[3]=='--guard-only')))
