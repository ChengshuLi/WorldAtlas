"""#1364 phase-one literal source-proof caller, not native reference calculation."""
import argparse
import hashlib
import json
import inspect
import types
import re
import subprocess
import sys
from pathlib import Path
import gzip

import custody
import runtime

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
NAMESPACE = 'coordination/engineering/reference-source-custody-20261007/'
RESERVE = 2 * 1024 * 1024


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def authenticate_code(commit):
    if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Exact immutable commit required before Git')
    names = ['producer.py', 'custody.py', 'runtime.py', 'runtime-controls.py',
             'controls.py', 'input-plan.json', 'runtime-plan.json',
             'proposed-read-accounting.json', 'original-reference-index.json']
    plan = json.loads((ROOT / 'input-plan.json').read_bytes())
    names += [str(Path(x['path']).relative_to(NAMESPACE)) for x in plan['literal_helpers']]
    pins = []
    executed = {str(Path(m.__file__).resolve()): m for m in (sys.modules[__name__], custody, runtime)}
    for name in names:
        relative = NAMESPACE + name
        path = custody.ordinary(REPO, relative)
        raw = path.read_bytes()
        if len(raw) > custody.CAP:
            raise ValueError('Executed code/input cap')
        tree = subprocess.check_output(['git', '-C', str(REPO), 'ls-tree', commit, '--', relative]).decode().strip().split()
        if len(tree) != 4 or tree[0] != '100644' or tree[1] != 'blob':
            raise ValueError('Executed ordinary code mode/tree')
        oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if oid != tree[2]:
            raise ValueError('Actual executed source/input differs from frozen Git')
        if str(path.resolve()) in executed:
            expected_codes = {}
            def collect(code):
                for child in code.co_consts:
                    if isinstance(child, types.CodeType):
                        expected_codes[child.co_qualname] = child
                        collect(child)
            collect(compile(raw, str(path), 'exec'))
            obj = executed[str(path.resolve())]
            functions = [v for v in vars(obj).values() if inspect.isfunction(v) and v.__module__ == obj.__name__]
            for cls in vars(obj).values():
                if inspect.isclass(cls) and cls.__module__ == obj.__name__:
                    functions.extend(v for v in vars(cls).values() if inspect.isfunction(v))
            for fn in functions:
                original_code = expected_codes.get(fn.__qualname__)
                if original_code is None or runtime.code_value(fn.__code__) != runtime.code_value(original_code):
                    raise ValueError('Actual in-memory project callable differs from frozen source')
        pins.append({'path': relative, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                     'mode': tree[0], 'blob': oid, 'commit': commit})
    for obj in (custody, runtime):
        if Path(obj.__file__).resolve() != ROOT / (obj.__name__ + '.py'):
            raise ValueError('Imported project code path drift')
    return plan, pins


def runtime_payload(root, plan):
    # Stream exact whole runtime bodies into the premeasured ordered-byte frames.
    frame = bytearray(); ordinal = 0
    members = plan['members']
    for member in members:
        custody.digest(member['path'], member['bytes'], member['sha256'], cap=custody.CAP)
        with Path(member['path']).open('rb') as stream:
            remaining = member['bytes']
            while remaining:
                chunk = stream.read(min(custody.FRAME - len(frame), remaining))
                if not chunk:
                    raise ValueError('Runtime whole body truncated')
                frame.extend(chunk); remaining -= len(chunk)
                if len(frame) == custody.FRAME:
                    pin = plan['frames'][ordinal]
                    if hashlib.sha256(frame).hexdigest() != pin['decoded_sha256']:
                        raise ValueError('Runtime concatenated frame drift')
                    custody.publish(root, pin, gzip.compress(bytes(frame), mtime=0))
                    frame.clear(); ordinal += 1
            if stream.read(1):
                raise ValueError('Runtime whole body growth')
    if frame:
        pin = plan['frames'][ordinal]
        if len(frame) != pin['decoded_bytes'] or hashlib.sha256(frame).hexdigest() != pin['decoded_sha256']:
            raise ValueError('Runtime final frame drift')
        custody.publish(root, pin, gzip.compress(bytes(frame), mtime=0)); ordinal += 1
    if ordinal != len(plan['frames']):
        raise ValueError('Runtime frame roster drift')


def preflight(commit, source_map):
    plan, code = authenticate_code(commit)
    rp = json.loads((ROOT / 'runtime-plan.json').read_bytes())
    module, objects = runtime.load_original()
    actual = runtime.authenticate(objects, rp['actual_runtime'])
    # All operator/read paths known before any source reconstruction or extraction.
    if set(source_map) != {x['original_name'] for x in plan['original_objects']}:
        raise ValueError('Exact whole original source mapping required')
    for obj in plan['original_objects']:
        custody.digest(source_map[obj['original_name']], obj['whole_bytes'], obj['whole_sha256'])
    for member in rp['members']:
        custody.digest(member['path'], member['bytes'], member['sha256'], cap=custody.CAP)
    index = json.loads((ROOT / 'original-reference-index.json').read_bytes())
    module.type_schema(index)
    ordinary_pins = plan['original_fragment_inputs'] + plan['full_member_outputs'] + rp['frames'] + code
    admission = custody.budget(ordinary_pins, RESERVE)
    return plan, rp, module, objects, actual, code, index, admission


def run(commit, source_map, target):
    # Immutable/fresh output validation precedes output writes or Git option exposure.
    if Path(target).exists() or Path(target).is_symlink():
        raise ValueError('Fresh owned run tree required')
    plan, rp, module, objects, actual, code, index, admission = preflight(commit, source_map)
    target = Path(target); target.mkdir(parents=True)
    delivered = target / 'delivered'; delivered.mkdir()
    work = target / 'private-whole-originals'; work.mkdir()
    frame_index = {p['path']: p for p in plan['original_fragment_inputs']}
    originals = {}
    for obj in plan['original_objects']:
        pins = [frame_index[p] for p in obj['ordered_frames']]
        custody.split_original(source_map[obj['original_name']], obj, pins, delivered)
        path = work / obj['original_name']
        custody.restore_original(delivered, obj, pins, path)
        originals[obj['original_name']] = path
    runtime_payload(delivered, rp)
    custody.extract_members(originals['koppen-geiger-v3-original.zip'], plan['full_member_outputs'], delivered)
    sources = {'climate_archive': originals['koppen-geiger-v3-original.zip'],
               'vegetation': originals['resolve-original.geojson'],
               'topography': originals['terrain-original.tif'],
               'climate_rasters': {p['archive_entry'][:4]: custody.ordinary(delivered, p['path'])
                                  for p in plan['full_member_outputs']}}
    runtime.authenticate(objects, actual)
    allowed = list(originals.values()) + list(sources['climate_rasters'].values()) + [
        module.ROOT / 'scripts' / name for name in [
            'ellipsoidal_area.py', 'majority.py', 'recheck-vegetation.py',
            'prepare-topography.py', 'prepare-reference-attributes.py']]
    gate = custody.ReadGate(allowed)
    raw_proof = gate.call(module.source_proof, index, sources)
    runtime.authenticate(objects, actual)
    # Genuine run-specific absolute paths remain in the execution capsule; portable
    # diagnostic paths identify exact whole originals/members, not reserialized data.
    portable = json.loads(json.dumps(raw_proof))
    for key, row in portable.items():
        if key != 'algorithms':
            row['path'] = ('private-whole-originals/' + Path(row['path']).name
                           if key in ('climate_archive', 'ecoregions', 'topography')
                           else next(p['path'] for p in plan['full_member_outputs']
                                     if p['archive_entry'] == row['archive_entry']))
    outputs = plan['original_fragment_inputs'] + plan['full_member_outputs'] + rp['frames']
    for pin in outputs:
        custody.digest(custody.ordinary(delivered, pin['path']), pin['bytes'], pin['sha256'], cap=custody.CAP)
    report = {'version': 1, 'issue': 1364, 'execution_commit': commit,
              'complete_ordinary_outputs': outputs, 'code_inputs': code,
              'original_objects': plan['original_objects'], 'runtime_members': rp['members'],
              'runtime': actual, 'stock_source_proof': portable, 'admission': admission,
              'source_limits': plan['source_limits'],
              'native_calculation_performed': False, 'authority_or_current_fitness_approved': False}
    raw = canonical(report)
    if len(raw) > RESERVE // 2:
        raise ValueError('Reserved complete report/capsule bound')
    (target / 'report.json').write_bytes(raw)
    capsule = {'version': 1, 'execution_commit': commit, 'stock_source_proof_actual_paths': raw_proof,
               'report_sha256': hashlib.sha256(raw).hexdigest(), 'runtime': actual,
               'source_mapping': source_map, 'ordinary_admission': admission,
               'actual_stock_open_events': gate.events}
    body = canonical(capsule)
    if len(body) > RESERVE // 2:
        raise ValueError('Reserved execution capsule bound')
    (target / 'execution.json').write_bytes(body)
    custody.budget(outputs + code + [
        {'path': 'report.json', 'bytes': len(raw)},
        {'path': 'execution.json', 'bytes': len(body)}])
    return {'report_sha256': hashlib.sha256(raw).hexdigest(), 'outputs': len(outputs),
            'admission': admission, 'native_calculation_performed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', required=True)
    parser.add_argument('--source-map', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}', args.commit):
        raise ValueError('Exact immutable commit required before input/Git operations')
    mapping = json.loads(Path(args.source_map).read_bytes())
    if args.preflight_only:
        result = preflight(args.commit, mapping)[-1]
    else:
        result = run(args.commit, mapping, args.output)
    print(json.dumps(result, sort_keys=True))
