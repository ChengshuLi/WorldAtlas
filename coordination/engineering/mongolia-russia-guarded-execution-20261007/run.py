"""Authenticate the complete frozen comparison boundary before source processing."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import types

HERE = Path(__file__).absolute().parent
REPO = HERE.parents[2]
OWNED = 'coordination/engineering/mongolia-russia-guarded-execution-20261007/'
BYTECODE_PREFIX = REPO / '.cache' / '1421-never-materialized-bytecode'
LIMIT = 32 * 1024 * 1024
PHASE = 256 * 1024 * 1024


def whole(commit, path):
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Exact lowercase execution commit required')
    if not path or '\\' in path or any(p in ('', '.', '..') for p in path.split('/')):
        raise ValueError('Unsafe frozen path')
    row = subprocess.check_output(['git', '-C', str(REPO), 'ls-tree', '-z', commit, '--', path]).decode().rstrip('\0')
    fields = row.split('\t')
    if len(fields) != 2 or fields[1] != path:
        raise ValueError('Missing frozen file')
    mode, kind, oid = fields[0].split()
    if mode not in ('100644', '100755') or kind != 'blob':
        raise ValueError('Nonordinary frozen file')
    size = int(subprocess.check_output(['git', '-C', str(REPO), 'cat-file', '-s', oid]))
    if size > LIMIT:
        raise ValueError('Frozen file exceeds ordinary cap')
    return subprocess.check_output(['git', '-C', str(REPO), 'cat-file', 'blob', oid])


def materialized(commit, name):
    expected = whole(commit, OWNED + name)
    path = HERE / name
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Symlink in consumed path')
    with path.open('rb') as stream:
        actual = stream.read(len(expected) + 1)
    if actual != expected:
        raise ValueError('Actually consumed code/config bytes differ')
    return actual


def destination(path):
    if not path.is_absolute() or '..' in path.parts or not path.resolve().is_relative_to(REPO / '.cache'):
        raise ValueError('Fresh owned absolute cache destination required')
    if path.exists() or not path.parent.is_dir() or any(
        p.is_symlink() or (p.exists() and not p.is_dir()) for p in (path, *path.parents)
    ):
        raise ValueError('Destination exists or has a nonordinary ancestor')


def load(commit):
    if not sys.flags.isolated or not sys.flags.no_site or not sys.dont_write_bytecode or sys.pycache_prefix!=str(BYTECODE_PREFIX) or BYTECODE_PREFIX.exists() or BYTECODE_PREFIX.is_symlink():
        raise ValueError('Use isolated -B Python with the fixed nonexistent bytecode prefix; no cached or preloaded project execution')
    if subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD']).decode().strip() != commit:
        raise ValueError('Current exact immutable execution commit required')
    inventory = json.loads(materialized(commit, 'code-list.json'))
    required={'run.py','code-list.json','code_guard.py','science.py','input-plan.json','runtime-plan.json','publication-plan.json','methods/immutable.py','methods/geometry.py','methods/ellipsoidal_area.py'}
    if len(inventory) != len(set(inventory)) or not required.issubset(inventory):
        raise ValueError('Incomplete executed inventory')
    raw = {name: materialized(commit, name) for name in inventory}
    guard = types.ModuleType('frozen_code_guard')
    guard.__file__ = str(HERE / 'code_guard.py')
    exec(compile(raw['code_guard.py'], guard.__file__, 'exec'), guard.__dict__)
    guard.all_callables(guard, raw['code_guard.py'])
    guard.all_callables(sys.modules[__name__], raw['run.py'])
    pins = [dict(path=OWNED + name, bytes=len(b), sha256=hashlib.sha256(b).hexdigest(), hash_kind='file-bytes') for name,b in raw.items()]
    plan = json.loads(raw['input-plan.json'])
    runtime = json.loads(raw['runtime-plan.json'])
    # Every installed body is authenticated against its retained whole byte alias,
    # before imports of the scientific packages or pinned project helpers.
    for row in runtime['files']:
        expected = materialized(commit, row['alias'])
        if len(expected) != row['bytes'] or hashlib.sha256(expected).hexdigest() != row['sha256']:
            raise ValueError('Whole runtime body alias differs')
        with Path(row['path']).open('rb') as stream:
            actual = stream.read(len(expected) + 1)
        if actual != expected:
            raise ValueError('Actual installed runtime body differs')
    if str(Path(sys.executable).resolve()) != runtime['executable'] or sys.version != runtime['python']:
        raise ValueError('Actual interpreter differs')
    # Explicit frozen package paths replace site/.pth execution under -S.
    if len(runtime['site_paths'])!=len(set(runtime['site_paths'])) or any(not Path(x).is_absolute() or not Path(x).is_dir() for x in runtime['site_paths']):
        raise ValueError('Frozen package path inventory differs')
    sys.path[:0]=runtime['site_paths']
    module = types.ModuleType('frozen_immutable')
    module.__file__ = str(HERE / 'methods/immutable.py')
    exec(compile(raw['methods/immutable.py'], module.__file__, 'exec'), module.__dict__)
    guard.all_callables(module, raw['methods/immutable.py'])
    original = module.Baseline(REPO, plan['original_commit'], plan['original_files'])
    own = module.Baseline(REPO, commit, pins)
    captured = {}
    for alias in plan['aliases']:
        name = alias['delivered']['path']
        body = own.materialized_bytes(name)
        if body != original.pinned_bytes(alias['original']['path']):
            raise ValueError('Complete original source/alias body relation differs')
        captured[alias['original']['path']] = body
    decoded = {}
    for name, body in captured.items():
        if body[:2] == b'\x1f\x8b':
            pin = original.pins[name]
            with gzip.GzipFile(fileobj=io.BytesIO(body)) as stream:
                value = stream.read(LIMIT + 1)
            if len(value) > LIMIT or len(value) != pin['uncompressed_bytes'] or hashlib.sha256(value).hexdigest() != pin['uncompressed_sha256']:
                raise ValueError('Whole decoded source differs or exceeds cap')
            original.admit(name + ':decoded', len(value))
            decoded[name] = value
    # One whole combined phase; separate Baseline instances do not split its cap.
    combined = sum(original.consumed.values()) + sum(own.consumed.values())
    if combined + 24 * 1024 * 1024 > PHASE or len(original.pins) + len(own.pins) + 16 > 512:
        raise ValueError('Complete inputs and pair/evidence reserve exceed admission')
    publication=json.loads(raw['publication-plan.json'])
    output_rows=publication['outputs']
    if len(output_rows)!=len({x['path'] for x in output_rows}) or any(not x['path'].startswith(OWNED) or x['encoded_and_decoded_ceiling']>LIMIT or x['encoded_and_decoded_ceiling']<0 for x in output_rows):
        raise ValueError('Malformed frozen full publication closure')
    public_input_bytes=sum(x['bytes'] for x in plan['original_files'])+sum(x['bytes']for x in pins)
    if public_input_bytes+sum(x['encoded_and_decoded_ceiling']for x in output_rows)>PHASE or len(original.pins)+len(pins)+len(output_rows)>512:
        raise ValueError('Complete concrete outputs/reports/controls/manifest publication forecast exceeds cap')
    validate_scope(captured, plan)
    methods = own.load_modules({'ellipsoidal_area': OWNED+'methods/ellipsoidal_area.py', 'geometry': OWNED+'methods/geometry.py', 'science': OWNED+'science.py'})
    for name,method in methods.items():
        guard.all_callables(method, raw['science.py' if name=='science' else 'methods/'+name+'.py'])
    loaded=runtime_loaded(runtime)
    return module, methods, captured, decoded, dict(actual_loaded_runtime=loaded,original_consumed=original.consumed, own_consumed=own.consumed, combined_input_bytes=combined, reserved_output_bytes=24*1024*1024, runtime=runtime, source_commit=plan['original_commit']),guard,raw


def runtime_loaded(runtime):
    """Every actual installed origin must be a whole retained immutable body."""
    import ctypes
    known={row['path']:row for row in runtime['files']}
    rows=[]
    for name,mod in sorted(sys.modules.items()):
        origin=getattr(mod,'__file__',None)
        if not origin:
            continue
        path=Path(origin).resolve()
        if str(path)==str(Path(__file__).resolve()):
            continue
        if path.suffix=='.pyc':
            path=Path(str(path)[:-1])
        pin=known.get(str(path))
        if not pin:
            raise ValueError('Actually loaded runtime origin lacks whole body: '+name+':'+str(path))
        with path.open('rb') as stream:
            body=stream.read(pin['bytes']+1)
        if len(body)!=pin['bytes'] or hashlib.sha256(body).hexdigest()!=pin['sha256']:
            raise ValueError('Actually loaded runtime origin differs: '+name)
        rows.append(dict(module=name,path=str(path),sha256=pin['sha256'],bytes=len(body)))
    # Installed native dependency images are executable bodies even when they
    # have no Python module object. OS shared-cache images remain named platform
    # dependencies, not fabricated ordinary on-disk byte aliases.
    import ctypes
    library=ctypes.CDLL(None)
    library._dyld_image_count.restype=ctypes.c_uint32
    library._dyld_get_image_name.argtypes=[ctypes.c_uint32]
    library._dyld_get_image_name.restype=ctypes.c_char_p
    for i in range(library._dyld_image_count()):
        name=library._dyld_get_image_name(i).decode()
        if name.startswith('/Users/chengshuli/'):
            path=str(Path(name).resolve());pin=known.get(path)
            if not pin:
                raise ValueError('Actually loaded installed native image lacks whole pin: '+path)
            with Path(path).open('rb') as stream:
                body=stream.read(pin['bytes']+1)
            if len(body)!=pin['bytes'] or hashlib.sha256(body).hexdigest()!=pin['sha256']:
                raise ValueError('Actually loaded native image differs')
            rows.append(dict(native_image=path,bytes=len(body),sha256=pin['sha256']))
        elif name not in runtime['system_image_paths']:
            raise ValueError('Unrecorded platform native image: '+name)
    return rows


def scientific_bindings(methods):
    # Exact frozen installed bodies are verified before these cold imports;
    # preserve actual callable objects/code and quadrature globals across use.
    import numpy as np
    import shapely
    import shapely.geometry
    import shapely.geometry.base
    import shapely.strtree
    ell=methods['ellipsoidal_area']
    functions={
        'shape':shapely.geometry.shape,
        'tree_query':shapely.strtree.STRtree.query,
        'predicate_method':shapely.geometry.base.BaseGeometry.intersects,
        'intersection_method':shapely.geometry.base.BaseGeometry.intersection,
        'predicate':shapely.intersects,'intersection':shapely.intersection,
        'native_predicate':shapely.lib.intersects,
        'native_intersection':shapely.lib.intersection,
        **{name:getattr(np,name) for name in ('sin','cos','arctanh','dot','asarray','deg2rad')},
        'area':ell.area,'ring_area':ell.ring_area,
    }
    return {name:(value,getattr(value,'__code__',None)) for name,value in functions.items()}, {
        name:getattr(ell,name).tobytes() for name in ('NODES','WEIGHTS')
    }


def require_scientific_bindings(methods, expected):
    actual=scientific_bindings(methods)
    if actual[0].keys()!=expected[0].keys() or actual[1]!=expected[1] or any(
        actual[0][name][0] is not val or actual[0][name][1] is not code
        for name,(val,code) in expected[0].items()
    ):
        raise ValueError('Actual scientific callable or quadrature binding changed')


def publication=json.loads(raw['publication-plan.json'])
    output_rows=publication['outputs']
    if len(output_rows)!=len({x['path'] for x in output_rows}) or any(not x['path'].startswith(OWNED) or x['encoded_and_decoded_ceiling']>LIMIT or x['encoded_and_decoded_ceiling']<0 for x in output_rows):
        raise ValueError('Malformed frozen full publication closure')
    public_input_bytes=sum(x['bytes'] for x in plan['original_files'])+sum(x['bytes']for x in pins)
    if public_input_bytes+sum(x['encoded_and_decoded_ceiling']for x in output_rows)>PHASE or len(original.pins)+len(pins)+len(output_rows)>512:
        raise ValueError('Complete concrete outputs/reports/controls/manifest publication forecast exceeds cap')
    validate_scope(captured, plan):
    prefix='research/geography/mongolia-russia-gap-source-fitness-20261007/inputs/'
    family=json.loads(captured[prefix+'complete-family.json'])
    physical=json.loads(captured[prefix+'physical-component-features.geojson'])['features']
    route=[json.loads(line) for line in captured[prefix+'route-component-rows.jsonl'].splitlines() if line.strip()]
    contacts=json.loads(captured[prefix+'current-contact-features.geojson'])['features']
    def identity(f):
        p=f.get('properties', {});return str(f.get('id', p.get('component_id',p.get('id'))))
    a=[identity(f) for f in physical]
    b=[str(r.get('component',r.get('component_id',r.get('id')))) for r in route]
    c=[identity(f) for f in contacts]
    expected={x for x in plan['component_ids'] if x.startswith('physical-component:')}
    contact_expected=set(plan['component_ids'])-expected
    if len(a)!=48 or len(set(a))!=48 or set(a)!=expected or len(b)!=48 or len(set(b))!=48 or set(a)!=set(b) or len(c)!=8 or len(set(c))!=8 or set(c)!=contact_expected or family['component_count']!=48 or set(family['complete_component_ids'])!=expected or set(family['complete_positive_length_neighbor_ids'])!=contact_expected:
        raise ValueError('Complete original family/route/contact join differs')


def main():
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--out',required=True,type=Path);p.add_argument('--input-only',action='store_true');args=p.parse_args()
    destination(args.out)
    module, methods, captured, decoded, receipt,guard,raw=load(args.commit)
    if args.input_only:
        print(json.dumps(dict(status='PASS',mode='input-only; no comparisons',receipt=receipt),sort_keys=True));return
    bindings=scientific_bindings(methods)
    runtime_loaded(receipt['runtime'])
    result=methods['science'].compare(captured,decoded,methods['geometry'],methods['ellipsoidal_area'])
    require_scientific_bindings(methods,bindings)
    receipt['actual_loaded_runtime_after']=runtime_loaded(receipt['runtime'])
    for name,method in methods.items():
        guard.all_callables(method, raw['science.py' if name=='science' else 'methods/'+name+'.py'])
    data=module.canonical_json(result)
    receipt_data=module.canonical_json(receipt)
    if len(data)>2*1024*1024 or len(receipt_data)>2*1024*1024 or len(data)+len(receipt_data)>11*1024*1024:
        raise ValueError('Whole result/receipt exceeds complete pair/evidence reserve')
    args.out.mkdir()
    with (args.out/'comparison.json').open('xb') as stream:stream.write(data)
    with (args.out/'input-receipt.json').open('xb') as stream:stream.write(receipt_data)
    print(json.dumps(dict(status='PASS',sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),components=48,contacts=8)))


if __name__=='__main__':
    main()
