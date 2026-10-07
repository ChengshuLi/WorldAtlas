"""Two-target calculation using the literal, completely authenticated recipe."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import time
import types

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE))
import reader
import products
import scope
import runtime as native_runtime

C='6a47b43025d963daf80915c6d219c75ebcc8cd91'
N='coordination/engineering/reference-source-custody-20261007/'
NS='coordination/engineering/reference-native-calculation-20261007/'
CODE=['reader.py','products.py','scope.py','runtime.py','producer.py']


def load_custody(source):
    source.read(N+'custody.py')
    spec=importlib.util.spec_from_file_location('accepted_native_custody',ROOT/N/'custody.py')
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj)
    return obj


def authenticated_module(module, raw, guard=None):
    compiled=compile(raw,module.__file__,'exec'); codes={}
    def collect(code):
        codes[code.co_qualname]=code
        for item in code.co_consts:
            if isinstance(item,types.CodeType): collect(item)
    collect(compiled)
    for name, code in codes.items():
        if name == '<module>' or '.' in name or '<' in name:
            continue
        value=getattr(module,name,None)
        if isinstance(value,types.FunctionType):
            if value.__code__ != code:
                raise ValueError('Actual imported helper callable drift')
        elif isinstance(value,type):
            for qual,expected in codes.items():
                if qual.startswith(name+'.') and qual.count('.')==1:
                    fn=getattr(value,qual.split('.')[1],None)
                    if isinstance(fn,(staticmethod,classmethod)):fn=fn.__func__
                    if not isinstance(fn,types.FunctionType) or fn.__code__!=expected:
                        raise ValueError('Actual imported helper class callable drift')
        else:
            raise ValueError('Actual imported helper callable missing')



def project_code(inputs,guard):
    modules={'reader':reader,'products':products,'scope':scope,'runtime':native_runtime,'producer':sys.modules[__name__]}
    pins=[]
    for name in CODE:
        raw=inputs.read(NS+name)
        authenticated_module(modules[name[:-3]],raw)
        pins.append(inputs.pins[NS+name])
    if reader.ROOT!=ROOT or reader.CAP!=33554432 or scope.TARGETS!=products.TARGETS or products.TARGETS!=frozenset(('atlas:physical:CAN-103:QUE','atlas:physical:CAN-114:NFL')):
        raise ValueError('Actual scientific scope/reader constants drift')
    return pins


def actual_inputs(commit):
    owned=reader.Inputs(commit);plan=owned.json(NS+'input-plan.json')
    if plan['actual_original_baseline']!=C or plan['subjects']!=sorted(products.TARGETS):
        raise ValueError('Actual original source baseline/subjects required')
    source=reader.Inputs(C)
    custody_plan=source.json(N+'input-plan.json')
    world_plan=source.json(scope.Q+'input-index.json')
    original_world=[a for a in world_plan['aliases'] if a['group']=='complete-current-world']
    original_refs=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',C,'--','data/reference-attributes/'],text=True).splitlines()
    expected_fragments=[p for p in custody_plan['original_fragment_inputs'] if '/terrain-original.' in p['path'] or '/resolve-original.' in p['path']]
    if (len(original_refs)!=93 or plan['original_reference_files']!=original_refs or
            plan['world_aliases']!=original_world or plan['complete_native_members']!=custody_plan['full_member_outputs'] or
            plan['relevant_original_fragments']!=expected_fragments):
        raise ValueError('Complete original reference/world/native closure differs from immutable originals')
    expected_paths={N+'input-plan.json',N+'runtime-plan.json',N+'runtime.py',N+'custody.py',N+'original-reference-index.json',
        N+'run-one/report.json',N+'run-two/report.json',N+'reproducibility.json',scope.Q+'input-index.json',
        scope.Q+'run-one/proposed-part-29.json.gz',scope.Q+'run-one/crosswalk.json.gz',scope.Q+'run-one/report.json',scope.Q+'verification/full-proposal-readback.json'}
    expected_paths.update(original_refs)
    expected_paths.update(p['path'] for p in custody_plan['literal_helpers'])
    expected_paths.add(custody_plan['transport_helper']['path'])
    expected_paths.update(p['path'] for p in expected_fragments)
    expected_paths.update(p['path'] for p in custody_plan['full_member_outputs'])
    expected_paths.update(scope.Q+p['ordinary']['path'] for p in original_world)
    expected_paths.update(N+'runtime/part-'+str(j).zfill(3)+'.bin.gz' for j in range(4))
    paths=[p['path'] for p in plan['source_descriptors']]
    if len(paths)!=171 or len(set(paths))!=171 or set(paths)!=expected_paths:
        raise ValueError('Complete distinct phase source inventory required')
    for pin in plan['source_descriptors']:
        raw=source.read(pin['path'])
        if source.pins[pin['path']]!={k:pin[k] for k in ('commit','path','mode','blob','bytes','sha256')}:
            raise ValueError('Whole original input descriptor drift')
        if pin.get('encoding')=='gzip':
            decoded=reader.gunzip(raw,pin['decoded_bytes'])
            if reader.sha(decoded)!=pin['decoded_sha256']:
                raise ValueError('Whole original decoded descriptor drift')
    return owned,source,plan


def run(commit,name,*,inputs_only=False):
    reader.exact_commit(commit)
    if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name):
        raise ValueError('Owned fresh run name required')
    cache=ROOT/'.cache';cache.mkdir(exist_ok=True)
    out=reader.safe(cache,name)
    if out.exists():raise ValueError('Run destination already exists')
    owned,source,plan=actual_inputs(commit)
    guard=native_runtime.original_guard(source.read(N+'runtime.py'));authenticated_module(guard,source.read(N+'runtime.py'))
    helper,objects=guard.load_original()
    code_pins=project_code(owned,guard)
    custody=load_custody(source);authenticated_module(custody,source.read(N+'custody.py'))
    budget=custody.budget([dict(pin,path=pin['path']) for pin in plan['source_descriptors']]+code_pins+[owned.pins[NS+'input-plan.json']],reserve=64*1024*1024)
    complete=scope.complete_world(source)
    bodies={p.removeprefix('data/reference-attributes/'):source.read(p) for p in plan['original_reference_files']}
    original=json.loads(bodies['index.json']);helper.type_schema(original)
    if original['footprints_sha256']!=complete['before_footprints_sha256']:
        raise ValueError('Complete original references do not bind before geography')
    products.records(original,bodies,complete['ids'])
    warm=native_runtime.warm(guard,objects)
    actual_runtime=native_runtime.snapshot(guard,objects)
    if inputs_only:
        return {'status':'PASS','scope':'complete171 original inputs/49625 pointset join/346346 original rows and tiny actual operators only',
            'budget':budget,'actual_runtime':actual_runtime,'tiny_operator_positive':warm,'no_target_GIS_calculation':True}
    expected=owned.json(NS+'runtime-plan.json')
    if actual_runtime!=expected['actual_runtime']:
        raise ValueError('Actual warmed scientific runtime does not match frozen plan')
    # Every output is fresh and job-local; original bytes are never changed.
    out.mkdir();private=out/'private-native-originals';private.mkdir()
    custody_plan=source.json(N+'input-plan.json')
    sources={}
    for obj in custody_plan['original_objects']:
        if obj['original_name']=='koppen-geiger-v3-original.zip':continue
        pins=[p for p in plan['relevant_original_fragments'] if p['path'] in obj['ordered_frames']]
        dest=private/obj['original_name'];custody.restore_original(ROOT,obj,pins,dest)
        sources['vegetation' if obj['original_name']=='resolve-original.geojson' else 'topography']=dest
    sources['climate_rasters']={}
    for pin in plan['complete_native_members']:
        path=reader.safe(ROOT,pin['path']);custody.digest(path,pin['bytes'],pin['sha256'],cap=33554432)
        sources['climate_rasters'][pin['archive_entry'].split('_')[0]]=path
    index=copy.deepcopy(original)
    after={id:p['after'] for id,p in complete['targets'].items()}
    authenticated_module(guard,source.read(N+'runtime.py'));authenticated_module(custody,source.read(N+'custody.py'))
    native_runtime.authenticate(guard,objects,expected['actual_runtime']);project_code(owned,guard)
    start=time.time()
    fresh,missing,evidence=helper.summarize_changed(set(products.TARGETS),after,index,sources)
    elapsed=time.time()-start
    authenticated_module(guard,source.read(N+'runtime.py'));authenticated_module(custody,source.read(N+'custody.py'))
    native_runtime.authenticate(guard,objects,expected['actual_runtime']);project_code(owned,guard)
    for obj in custody_plan['original_objects']:
        if obj['original_name']!='koppen-geiger-v3-original.zip':
            custody.digest(private/obj['original_name'],obj['whole_bytes'],obj['whole_sha256'])
    for pin in plan['complete_native_members']:
        custody.digest(reader.safe(ROOT,pin['path']),pin['bytes'],pin['sha256'],cap=33554432)
    upstream={'mode':'complete relevant native products; accepted whole archive/member relation upstream PR1412',
        'actual_custody_merge':C,'whole_climate_archive_sha256':original['inputs']['climate_archive'],
        'whole_vegetation_sha256':original['inputs']['ecoregions'],
        'native_members':plan['complete_native_members'],'source_custody_report_sha256':source.pins[N+'run-one/report.json']['sha256'],
        'source_proof_or_ZIP_not_read_in_this_phase':True}
    report=products.merge(helper,ROOT/'data/reference-attributes',bodies,original,index,fresh,missing,evidence,
        complete['ids'],complete['migration_receipt_sha256'],complete['after_footprints_sha256'],complete['after_geography_sha256'],out/'products',upstream)
    report.update(execution_commit=commit,actual_calculation_seconds=elapsed,
        full_world_scope_roster_sha256=reader.sha(products.dumps(complete['roster']).encode()),
        full_footprint_hash_vintage=complete['full_footprint_hash_vintage'],
        current_pointers_activated=False,parent1295_and_global1202_complete=False)
    (out/'report.json').write_text(products.dumps(report))
    (out/'execution.json').write_text(products.dumps({'code':code_pins,'source_inputs':list(source.pins.values()),
        'runtime':actual_runtime,'budget':budget,'actual_fresh_output':str(out),
        'only_two_complete_target_calculations':True,'no_archive_sourceproof_worldcompiler_or_global_audit':True}))
    return {'status':'PASS','output':str(out),'derived_records':report['derived_records'],'missing_changed':missing}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit',required=True);parser.add_argument('--name',required=True)
    parser.add_argument('--inputs-only',action='store_true')
    args=parser.parse_args();print(json.dumps(run(args.commit,args.name,inputs_only=args.inputs_only),ensure_ascii=False))
