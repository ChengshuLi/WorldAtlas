"""Complete, streamed #1520 proposal; never installs canonical products."""
import argparse, hashlib, json, os, pathlib, subprocess, sys, marshal, types, ctypes
import numpy, shapely, pyproj
from shapely.geometry import shape, mapping, Polygon
from kernel import COMPONENT_TARGETS, exact_additions, neighbor_relation

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.geometry import canonical_prepared_land, PREPARED_DOMAIN
from evidence.immutable import canonical_json, deterministic_gzip

FILE_CAP = 32 * 1024 * 1024
PHASE_CAP = 256 * 1024 * 1024
OUTPUT_RESERVE = 18 * 1024 * 1024
CURRENT_PART29_SHA = 'c34114912dc620dce0821e251877470b5a83385ab3bf1284408f077b78bbdec8'
SOURCE_DECISIONS_SHA = '0f29f229f94c48a2ba4a520b8cbb078116d82344302f773b2171716caedac9b6'
CONSTRUCTED_COMPONENTS = (
 'physical-component:12c9ec9813490ce8602fb26ee2e54225b99c28bbd29794a7f8ac9ee60f109e8a',
 'physical-component:17bb5b7f043b0fb2b447b8ccef216e530fed4595da1aec0feb1dea235bed0dbd',
)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def callable_pin(value):
    def normalized(code):
        return code.replace(co_filename='', co_consts=tuple(normalized(c) if isinstance(c, types.CodeType) else c for c in code.co_consts))
    result = {'module': getattr(value, '__module__', None), 'qualname': getattr(value, '__qualname__', None),
              'type': type(value).__name__, 'name': getattr(value, '__name__', None)}
    if hasattr(value, '__code__'):
        result['code_sha256'] = digest(marshal.dumps(normalized(value.__code__)))
    return result

def critical_callables():
    import evidence.geometry as geometry, kernel
    result = {'kernel.exact_additions': kernel.exact_additions, 'kernel.neighbor_relation': kernel.neighbor_relation,
              'shapely.geometry.shape': shape, 'shapely.geometry.mapping': mapping}
    for name, value in vars(geometry).items():
        if callable(value) and getattr(value, '__module__', None) == 'evidence.geometry':
            result['evidence.geometry.' + name] = value
    for name in ('exact_additions', 'neighbor_relation', 'canonical_prepared_land', 'canonical_json', 'deterministic_gzip',
                 'digest', 'callable_pin', 'critical_callables', 'loaded_runtime_paths', 'ordinary', 'read', 'decoded',
                 'code_guard', 'phase_admission', 'safe_output', 'authenticate_installed_runtime', 'validate_world_index', 'require_callables', 'preflight', 'run'):
        result['producer.executed.' + name] = globals()[name]
    for name in ('union', 'difference', 'intersection', 'covers', 'equals', 'is_valid'):
        result['shapely.lib.' + name] = getattr(shapely.lib, name)
    return result

def loaded_runtime_paths():
    result = {os.path.realpath(sys.executable)}
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name:
            if name.endswith(('.pyc', '.pyo')):
                name = name[:-1]
            path = pathlib.Path(name).resolve()
            if path.is_file() and not path.is_relative_to(ROOT):
                result.add(str(path))
    library = ctypes.CDLL(None)
    library._dyld_image_count.restype = ctypes.c_uint32
    library._dyld_get_image_name.restype = ctypes.c_char_p
    for index in range(library._dyld_image_count()):
        name = library._dyld_get_image_name(index).decode()
        if os.path.isfile(name) and ('codex' in name or 'site-packages' in name):
            result.add(os.path.realpath(name))
    return result

def ordinary(path):
    path = pathlib.Path(path)
    if not path.is_absolute():
        raise ValueError('Absolute ordinary path required')
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            raise ValueError('Symlink path refused')
    if not path.is_file():
        raise ValueError('Missing ordinary body: ' + str(path))
    return path

def read(path, pin):
    path = ordinary(path)
    size = pin['bytes']
    if type(size) is not int or not 0 <= size <= FILE_CAP or path.stat().st_size != size:
        raise ValueError('Ordinary size admission failed')
    expected_mode = {'100644': 0o644, '100755': 0o755}.get(pin.get('mode'))
    if expected_mode is None or path.stat().st_mode & 0o777 != expected_mode:
        raise ValueError('Explicit original ordinary mode differs')
    with path.open('rb') as stream:
        raw = stream.read(size + 1)
    if len(raw) != size or digest(raw) != pin['sha256']:
        raise ValueError('Whole input body differs: ' + str(path))
    return raw

def decoded(raw, pin):
    import zlib
    cap = pin['decoded_bytes']
    if type(cap) is not int or not 0 <= cap <= FILE_CAP:
        raise ValueError('Decoded admission failed')
    decoder = zlib.decompressobj(31)
    result = decoder.decompress(raw, cap + 1)
    if len(result) > cap or decoder.unconsumed_tail or not decoder.eof or decoder.unused_data:
        raise ValueError('Incomplete, concatenated or oversized gzip')
    if len(result) != cap or digest(result) != pin['decoded_sha256']:
        raise ValueError('Whole decoded body differs')
    return result

def code_guard(commit, proof):
    if proof.get('head') != commit or proof.get('root') != str(ROOT) or proof.get('kind') != 'immutable-git-code-source-v1':
        raise ValueError('Wrong independently issued immutable code source/root/head')
    paths = {HERE / 'producer.py', HERE / 'kernel.py', HERE / 'input-plan.json', HERE / 'runtime.json', HERE / 'capture-code.py'}
    for module in list(sys.modules.values()):
        f = getattr(module, '__file__', None)
        if f and pathlib.Path(f).resolve().is_relative_to(ROOT):
            paths.add(pathlib.Path(f).resolve())
    expected = {str(path.relative_to(ROOT)) for path in paths}
    rows = proof.get('files', [])
    if len(rows) != len(expected) or {pin['path'] for pin in rows} != expected:
        raise ValueError('Complete executed/imported/issuer code roster differs')
    for pin in rows:
        raw = read(ROOT / pin['path'], pin)
        if hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != pin['git_blob_oid']:
            raise ValueError('Actual code does not equal original immutable Git body')
    return rows


def phase_admission(inputs, runtime, code):
    descriptors = [*inputs, *runtime['runtime_files'], *code]
    if len(descriptors) > 512:
        raise ValueError('Complete phase exceeds512 descriptors')
    identities = [p.get('actual_path', p.get('path')) for p in descriptors]
    if any(not isinstance(path, str) or not pathlib.Path(path).is_absolute() for path in identities) or len(set(identities)) != len(identities):
        raise ValueError('Complete phase requires unique absolute actual source/runtime/code identities')
    for pin in [*inputs, *code]:
        if type(pin['bytes']) is not int or not 0 <= pin['bytes'] <= FILE_CAP:
            raise ValueError('Declared ordinary phase member exceeds cap')
        if 'decoded_bytes' in pin and (type(pin['decoded_bytes']) is not int or not 0 <= pin['decoded_bytes'] <= FILE_CAP):
            raise ValueError('Declared decoded phase member exceeds cap')
    for pin in runtime['runtime_files']:
        if type(pin['bytes']) is not int or pin['bytes'] < 0:
            raise ValueError('Invalid whole installed-runtime charge')
    source_bytes = sum(p['bytes'] + p.get('decoded_bytes', 0) for p in inputs)
    runtime_bytes = sum(p['bytes'] for p in runtime['runtime_files'])
    total = source_bytes + runtime_bytes + sum(p['bytes'] for p in code) + OUTPUT_RESERVE
    if total > PHASE_CAP:
        raise ValueError('Complete prospective encoded/decoded/runtime/output phase exceeds256MiB: ' + str(total))
    return source_bytes, runtime_bytes, total

def validate_world_index(world, plan):
    paths = ['data/' + name for name in world.get('parts', [])]
    expected = [p['path'] for p in plan['current_world_inputs']]
    if len(paths) != 36 or len(set(paths)) != 36 or paths != expected:
        raise ValueError('Full immutable36-part world index differs from declared source roster')
    return paths

def require_callables(runtime):
    current = critical_callables()
    if set(current) != set(INITIAL_EXECUTED_CALLABLES) or any(current[name] is not value for name, value in INITIAL_EXECUTED_CALLABLES.items()):
        raise ValueError('Captured actual numerical/imported callable identity changed')
    if {name: callable_pin(value) for name, value in critical_callables().items()} != runtime['critical_callables']:
        raise ValueError('Actual numerical callable changed before source consumer')

def authenticate_installed_runtime(runtime):
    # Caller admits complete phase before this first runtime body operation.
    for pin in runtime['runtime_files']:
        path = ordinary(pin['path'])
        before = path.stat()
        if before.st_size != pin['bytes'] or oct(before.st_mode & 0o777) != pin['mode']:
            raise ValueError('Installed runtime stat changed')
        h = hashlib.sha256()
        consumed = 0
        with path.open('rb') as stream:
            while True:
                chunk = stream.read(min(1024 * 1024, pin['bytes'] - consumed + 1))
                if not chunk:
                    break
                consumed += len(chunk)
                if consumed > pin['bytes']:
                    raise ValueError('Installed runtime grew beyond admitted bytes')
                h.update(chunk)
        after_stat = path.stat()
        if consumed != pin['bytes'] or (after_stat.st_dev, after_stat.st_ino, after_stat.st_size, after_stat.st_mode, after_stat.st_mtime_ns) != (before.st_dev, before.st_ino, before.st_size, before.st_mode, before.st_mtime_ns) or h.hexdigest() != pin['sha256']:
            raise ValueError('Whole installed runtime changed')

def preflight(commit, code_source, code_source_sha, code_source_bytes):
    # Import/operator warming is a bounded runtime-preparation operation, not a source computation.
    decoded(deterministic_gzip(b'[]\n'), {'decoded_bytes': 3, 'decoded_sha256': digest(b'[]\n')})
    canonical_prepared_land(Polygon([(0, 0), (1, 0), (0, 1), (0, 0)]))
    if sys.version_info[:3] != (3, 12, 14) or shapely.__version__ != '2.1.2' or shapely.geos_version_string != '3.13.1':
        raise ValueError('Frozen numerical runtime required')
    if type(code_source_bytes) is not int or not 0 < code_source_bytes <= 65536:
        raise ValueError('Bounded independently issued code source required')
    source_pin = {'bytes': code_source_bytes, 'sha256': code_source_sha, 'mode': '100644'}
    proof = json.loads(read(code_source, source_pin))
    code = code_guard(commit, proof)
    plan = json.loads((HERE / 'input-plan.json').read_bytes())
    runtime = json.loads((HERE / 'runtime.json').read_bytes())
    inputs = [p for p in plan['current_world_inputs'] if p['role'] != 'historical-tracked-body-only']
    inputs = [{**p, 'actual_path': str(ROOT / p['path'])} for p in inputs]
    inputs += [{**plan['current_part29'], 'actual_path': str(HERE / plan['current_part29_local_alias'])},
               {**plan['source_decisions'], 'actual_path': str(HERE / plan['source_decisions_local_alias'])},
               {**plan['applicability_receipt'], 'actual_path': str(HERE / plan['applicability_receipt']['local_path'])},
               {**plan['world_index'], 'actual_path': str(ROOT / plan['world_index']['path'])},
               {**source_pin, 'actual_path': str(pathlib.Path(code_source).absolute())}]
    admitted_code = [{**p, 'actual_path': str(ROOT / p['path'])} for p in code]
    source_bytes, runtime_bytes, total = phase_admission(inputs, runtime, admitted_code)
    if loaded_runtime_paths() - {p['path'] for p in runtime['runtime_files']}:
        raise ValueError('Actual loaded runtime exceeds the admitted frozen roster')
    if sys.flags.optimize or sys.flags.dont_write_bytecode != runtime['dont_write_bytecode'] or os.path.realpath(sys.executable) != runtime['executable']:
        raise ValueError('Wrong actual interpreter invocation')
    require_callables(runtime)
    authenticate_installed_runtime(runtime)
    if plan['source_decisions']['sha256'] != SOURCE_DECISIONS_SHA or plan['current_part29']['decoded_sha256'] != CURRENT_PART29_SHA:
        raise ValueError('Wrong reviewed source or installedv8 baseline')
    world = json.loads(read(ROOT / plan['world_index']['path'], plan['world_index']))
    validate_world_index(world, plan)
    return plan, {'complete_phase_bytes': total, 'complete_phase_descriptors': len(inputs) + len(code) + len(runtime['runtime_files']), 'source_encoded_decoded_bytes': source_bytes,
                  'installed_runtime_bytes': runtime_bytes, 'output_reserve_bytes': OUTPUT_RESERVE,
                  'executed_code': code, 'source_count': len(inputs), 'runtime_count': len(runtime['runtime_files'])}

def safe_output(output):
    path = pathlib.Path(output)
    if not path.is_absolute() or '..' in path.parts or any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('Absolute nontraversing ordinary owned-cache output required')
    if not path.is_relative_to(ROOT / '.cache') or path.exists():
        raise ValueError('Fresh exclusive owned-cache output required')
    return path

def run(commit, output, input_only=False, *, code_source, code_source_sha, code_source_bytes):
    if not input_only:
        output = safe_output(output)
    plan, admission = preflight(commit, code_source, code_source_sha, code_source_bytes)
    if input_only:
        return {'status': 'input-plan/runtime admission PASS; no repair calculation', **admission}
    receipt = json.loads(read(HERE / plan['applicability_receipt']['local_path'], plan['applicability_receipt']))
    if receipt['id'] != plan['applicability_receipt']['comment_id'] or receipt['html_url'] != plan['pre_edit_review_url']:
        raise ValueError('Wrong independent posted applicability receipt')
    decisions = json.loads(read(HERE / plan['source_decisions_local_alias'], plan['source_decisions']))
    ready = {r['component_id']: r for r in decisions['results'] if r['decision'] == 'repair-ready-geometric-proposal'}
    if set(ready) != set(COMPONENT_TARGETS) or len(decisions['results']) != 7:
        raise ValueError('Full seven-case source scope differs')
    gaps = {identity: shape(ready[identity]['candidate_geometry']) for identity in CONSTRUCTED_COMPONENTS}
    part29_raw = decoded(read(HERE / plan['current_part29_local_alias'], plan['current_part29']), plan['current_part29'])
    part29 = json.loads(part29_raw)
    targets = {f['id']: f for f in part29['features'] if f['id'] in COMPONENT_TARGETS.values()}
    old = {identity: shape(f['geometry']) for identity, f in targets.items()}
    after, proofs = exact_additions(old, gaps, expected_components=CONSTRUCTED_COMPONENTS)
    prepared_old = {k: canonical_prepared_land(g) for k, g in old.items()}
    prepared_after = {k: canonical_prepared_land(g) for k, g in after.items()}
    seen = set()
    unrelated_hash = hashlib.sha256()
    relations = {k: [] for k in after}
    parts = []
    for pin in plan['current_world_inputs']:
        raw = part29_raw if pin['role'] == 'historical-tracked-body-only' else read(ROOT / pin['path'], pin)
        features = json.loads(raw)['features']
        parts.append({'path': pin['path'], 'bytes': len(raw), 'sha256': digest(raw), 'features': len(features)})
        for feature in features:
            identity = feature['id']
            if identity in seen:
                raise ValueError('Duplicate complete-world ID')
            seen.add(identity)
            if identity not in targets:
                unrelated_hash.update(canonical_json(feature))
            neighbor = canonical_prepared_land(shape(feature['geometry']))
            for target in after:
                if identity == target:
                    if not neighbor.equals(prepared_old[target]):
                        raise ValueError('Current target operand differs')
                    continue
                relation = neighbor_relation(identity, neighbor, prepared_old[target], prepared_after[target])
                if relation:
                    relations[target].append(relation)
        del features
    if len(seen) != 49625 or not set(targets) <= seen:
        raise ValueError('Require full49625 current-world universe')
    proposed = {**part29, 'features': [{**f, 'geometry': mapping(after[f['id']])} if f['id'] in after else f for f in part29['features']]}
    for before, current in zip(part29['features'], proposed['features'], strict=True):
        if before['id'] not in after and before != current:
            raise ValueError('Unrelated full record changed')
        if {k: v for k, v in before.items() if k != 'geometry'} != {k: v for k, v in current.items() if k != 'geometry'}:
            raise ValueError('Identity, metadata or affiliation changed')
    raw = canonical_json(proposed)
    encoded = deterministic_gzip(raw)
    proof = canonical_json({'issue': 1520, 'stage': 'two-strictly-constructed-components-seven-case-source-scope', 'pre_edit_review_url': plan['pre_edit_review_url'],
             'before_part29_sha256': CURRENT_PART29_SHA, 'after_part29_sha256': digest(raw), 'world_rows': len(seen),
             'unchanged_full_rows': len(seen) - len(targets), 'unchanged_full_rows_canonical_sha256': unrelated_hash.hexdigest(),
             'changed_ids': sorted(targets), 'source_eligible_components': sorted(COMPONENT_TARGETS), 'constructed_components': list(CONSTRUCTED_COMPONENTS),
             'construction_failed_components': ['physical-component:add031b7195352292c8529323c8b99dd75002af629116b229e84be981893ca8d'],
             'failed_construction_predicate': 'new.covers(old)==False; no predicate weakened and no addition made', 'source_rule_failed_components': plan['unresolved_components'],
             'complete_world_inputs': parts, 'exact_constructions': proofs, 'complete_neighbor_relations': relations,
             'prepared_domain': PREPARED_DOMAIN, 'limitations': plan['limitations'], 'admission': admission,
             'current_pointers_activated': False, 'full_geographic_audit_claimed': False})
    runtime = json.loads((HERE / 'runtime.json').read_bytes())
    if loaded_runtime_paths() - {p['path'] for p in runtime['runtime_files']} or {name: callable_pin(value) for name, value in critical_callables().items()} != runtime['critical_callables']:
        raise ValueError('Runtime or numerical callable drift after complete source operation')
    if code_guard(commit, json.loads(read(code_source, {'bytes': code_source_bytes, 'sha256': code_source_sha, 'mode': '100644'}))) != admission['executed_code']:
        raise ValueError('Executed project code drift after complete source operation')
    if max(map(len, (raw, encoded, proof))) > FILE_CAP or len(raw) + len(encoded) + len(proof) > OUTPUT_RESERVE:
        raise ValueError('Actual complete output exceeds admitted reserve')
    output.mkdir(parents=True)
    for name, body in [('proposed-part-29.json', raw), ('proposed-part-29.json.gz', encoded), ('geometry-proof.json', proof)]:
        with (output / name).open('xb') as stream:
            stream.write(body)
    return {'status': 'PASS', 'world_rows': len(seen), 'changed_targets': len(targets), 'source_eligible_components': 3, 'constructed_components': len(gaps),
            'output_bytes': len(raw) + len(encoded) + len(proof), 'after_part29_sha256': digest(raw), **admission}

INITIAL_EXECUTED_CALLABLES = critical_callables()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', required=True)
    parser.add_argument('--out')
    parser.add_argument('--input-only', action='store_true')
    parser.add_argument('--code-source', required=True)
    parser.add_argument('--code-source-sha', required=True)
    parser.add_argument('--code-source-bytes', required=True, type=int)
    args = parser.parse_args()
    print(json.dumps(run(args.commit, args.out, args.input_only, code_source=args.code_source, code_source_sha=args.code_source_sha, code_source_bytes=args.code_source_bytes), sort_keys=True))
