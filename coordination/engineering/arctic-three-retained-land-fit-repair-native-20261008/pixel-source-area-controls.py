"""Actual cold producer custody boundaries; no world/area calculation."""
import pathlib,tempfile,hashlib,importlib.util,os,shutil
SOURCE=pathlib.Path(__file__).with_name('pixel-source-area.py')
spec=importlib.util.spec_from_file_location('pixel_source_area_controls_target',SOURCE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
root=pathlib.Path(tempfile.mkdtemp(prefix='pixel-source-area-')).resolve()
try:
    body=root/'body';body.write_bytes(b'complete-body');body.chmod(0o644)
    pin={'path':str(body),'bytes':len(b'complete-body'),'mode':0o644,'sha256':hashlib.sha256(b'complete-body').hexdigest()}
    assert module.admitted_read(pin)==b'complete-body'
    negatives=0
    def reject(call):
        global negatives
        try:call()
        except (AssertionError,FileNotFoundError):negatives+=1
        else:raise AssertionError('Adverse body accepted')
    reject(lambda:module.admitted_read({**pin,'bytes':pin['bytes']-1}))
    reject(lambda:module.admitted_read({**pin,'mode':0o755}))
    reject(lambda:module.admitted_read({**pin,'sha256':'0'*64}))
    reject(lambda:module.admitted_read({**pin,'path':str(root/'missing')}))
    link=root/'link';link.symlink_to(body)
    reject(lambda:module.admitted_read({**pin,'path':str(link)}))
    reject(lambda:module.ordinary(root/'..'/root.name/'body'))
    # Output refusal precedes runtime/module/source body reads at real run entry.
    calls=[];original=module.admitted_read
    module.admitted_read=lambda *args,**kwargs:calls.append(args)
    reject(lambda:module.run({},root/'foreign-output'))
    reject(lambda:module.run({},module.ROOT/'.cache'/'..'/'escaped'))
    assert calls==[];module.admitted_read=original
    import sys,math
    sys.path.insert(0,str(module.ROOT/'scripts'))
    import numpy,ellipsoidal_area
    module.require_area_globals(ellipsoidal_area,numpy,math)
    for name in ('A','FLATTENING','E2','E','C'):
        original=getattr(ellipsoidal_area,name);setattr(ellipsoidal_area,name,original+1)
        reject(lambda:module.require_area_globals(ellipsoidal_area,numpy,math));setattr(ellipsoidal_area,name,original)
    for name in ('np','math'):
        original=getattr(ellipsoidal_area,name);setattr(ellipsoidal_area,name,object())
        reject(lambda:module.require_area_globals(ellipsoidal_area,numpy,math));setattr(ellipsoidal_area,name,original)
    original_sqrt=math.sqrt;original_e=ellipsoidal_area.E
    math.sqrt=lambda value:2.0;ellipsoidal_area.E=2.0
    reject(lambda:module.require_area_globals(ellipsoidal_area,numpy,math))
    math.sqrt=original_sqrt;ellipsoidal_area.E=original_e
    import json
    runtime_raw=(module.ROOT/'coordination/engineering/arctic-three-retained-land-fit-repair-20261008/runtime.json').read_bytes()
    assert hashlib.sha256(runtime_raw).hexdigest()=='bc756cdc1e6bff037ed0efc60150d0dfbe94774d2c18ec9976aaa5c8611b76fa'
    initializers=[pin for pin in json.loads(runtime_raw)['runtime_files'] if pin['path'].endswith('/shapely/__init__.py')]
    assert len(initializers)==1
    sys.path.insert(0,str(pathlib.Path(initializers[0]['path']).parent.parent))
    import majority
    from shapely.geometry import Polygon
    for geometry in (Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)]),Polygon([(179,0),(-179,0),(-179,1),(179,1),(179,0)])):
        assert module.source_area(geometry)==ellipsoidal_area.area(majority.canonical(geometry))
    print({'positive':4,'negative':negatives,'source_body_opens_on_bad_destination':0,'target_source_areas_computed':0,'synthetic_recipe_controls':2})
finally:shutil.rmtree(root)
