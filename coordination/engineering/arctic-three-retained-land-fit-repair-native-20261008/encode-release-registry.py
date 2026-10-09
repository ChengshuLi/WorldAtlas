"""Encode the qualified full registry with the unchanged original codec."""
import sys, pathlib, os, json, gzip, hashlib, importlib.util

def run(plan, output):
    root = pathlib.Path(plan['root'])
    output = pathlib.Path(output)
    assert output.is_absolute() and '..' not in output.parts and output.is_relative_to(root / '.cache')
    assert not output.exists() and not output.is_symlink()
    for parent in [output, *output.parents]:
        assert not parent.is_symlink()
    assert plan['kind'] == 'qualified-complete-release-registry-encoding-1520'
    assert sys.version_info[:3] == (3, 12, 14) and sys.flags.isolated and sys.dont_write_bytecode
    assert os.path.realpath(sys.executable) == plan['executable']
    assert plan['source_head'] == os.environ['WORLDATLAS_SELECTED_NATIVE_HEAD']
    pins = [*plan['inputs'], *plan['code'], *plan['runtime_files']]
    assert len(pins) <= 512 and len({pin['path'] for pin in pins}) == len(pins)
    cost = sum(pin['bytes'] + pin.get('decoded_bytes', 0) for pin in pins) + plan['output_reserve'] + plan['metadata_bytes']
    assert cost <= 256 * 1024 * 1024
    for pin in pins:
        file = pathlib.Path(pin['path'])
        assert file.is_absolute() and '..' not in file.parts
        for parent in [file, *file.parents]:
            assert not parent.is_symlink()
        stat = file.stat()
        assert file.is_file() and stat.st_size == pin['bytes'] and stat.st_mode & 0o777 == pin['mode']
        assert pin in plan['runtime_files'] or (pin['bytes'] <= 32 * 1024 * 1024 and pin.get('decoded_bytes', 0) <= 32 * 1024 * 1024)
    # The external launcher authenticates every code/runtime body before import.
    module_path = root / 'coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/serialize-release-groups.py'
    spec = importlib.util.spec_from_file_location('qualified_release_codec_guards', module_path)
    guards = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guards)
    for pin in [*plan['code'], *plan['runtime_files']]:
        guards.admitted_read(pin, pin in plan['runtime_files'])
    codec = guards.load_codec(root)
    bindings = guards.capture_serialization_bindings(codec)
    callbacks = [run, guards.ordinary, guards.admitted_read, guards.load_codec, guards.loaded_paths,
                 guards.capture_serialization_bindings, guards.require_serialization_bindings,
                 codec.canonical_json, codec.deterministic_gzip]
    for fn in callbacks:
        name = os.path.realpath(fn.__code__.co_filename)
        matched = [pin for pin in plan['code'] if pin['path'] == name]
        assert len(matched) == 1
        constants = compile(guards.admitted_read(matched[0]), name, 'exec').co_consts
        expected = {code.co_name: code for code in constants if hasattr(code, 'co_code')}
        assert fn.__code__ == expected[fn.__name__]
    captured = [(fn, fn.__code__, fn.__defaults__, fn.__kwdefaults__) for fn in callbacks]
    guard_aliases = [(name, getattr(guards, name)) for name in
                    ('ordinary', 'admitted_read', 'load_codec', 'loaded_paths',
                     'capture_serialization_bindings', 'require_serialization_bindings')]
    allowed = {pin['path'] for pin in pins}

    def guard():
        for name, original in guard_aliases:
            assert getattr(guards, name) is original
        guards.require_serialization_bindings(bindings)
        assert callbacks[-2:] == [codec.canonical_json, codec.deterministic_gzip]
        for fn, code, defaults, kwdefaults in captured:
            assert fn.__code__ is code and fn.__defaults__ is defaults and fn.__kwdefaults__ is kwdefaults
        assert guards.loaded_paths() <= allowed
        for pin in [*plan['code'], *plan['runtime_files']]:
            guards.admitted_read(pin, pin in plan['runtime_files'])

    guard()
    raw = guards.admitted_read(plan['registry'])
    registry = json.loads(raw)
    issuance = json.loads(guards.admitted_read(plan['issuance']))
    terminal = json.loads(guards.admitted_read(plan['terminal']))
    baseline_raw = guards.admitted_read(plan['baseline_index'])
    baseline = json.loads(baseline_raw)
    assert issuance['issue'] == 1520 and issuance['output_sha256'] == hashlib.sha256(raw).hexdigest()
    assert issuance['output_bytes'] == len(raw) and issuance['source_head'] == terminal['head'] == plan['issuer_head']
    assert terminal['qualified'] and terminal['exit_code'] == 0 and terminal['guard_reason'] is None
    assert not terminal['owned_group_survivors'] and terminal['time_l_lifetime_max_rss_bytes'] <= 512 * 1024 * 1024
    assert issuance['complete_old_releases_retained'] == 8 and issuance['complete_old_batch_descriptors_retained'] == 3042
    assert issuance['new_products'] == 343 and issuance['membership_records_retained'] == 84833
    assert registry['releases'][-1]['id'] == issuance['release_id'] and len(registry['releases']) == 9
    assert registry['releases'][:len(baseline['releases'])] == baseline['releases']
    assert registry['batches'][:len(baseline['batches'])] == baseline['batches']
    baseline_sha = hashlib.sha256(baseline_raw).hexdigest()
    assert baseline_sha == issuance['predecessor_index_sha256']
    canonical = codec.canonical_json(registry)
    encoded = codec.deterministic_gzip(canonical)
    assert len(encoded) <= len(canonical) + 1024 and gzip.decompress(encoded) == canonical
    encoded_sha = hashlib.sha256(encoded).hexdigest()
    pointer = codec.canonical_json({'path': 'releases-v9.json.gz', 'sha256': encoded_sha,
                                    'predecessor_index_sha256': baseline_sha})
    assert len(pointer) <= 4096
    report = {'issue': 1520, 'source_head': plan['source_head'], 'issuer_head': plan['issuer_head'],
              'complete_phase_bytes': cost, 'descriptors': len(pins), 'release_id': issuance['release_id'],
              'encoded_bytes': len(encoded), 'encoded_sha256': encoded_sha,
              'decoded_bytes': len(canonical), 'decoded_sha256': hashlib.sha256(canonical).hexdigest(),
              'original_index_bytes': len(baseline_raw), 'original_index_sha256': baseline_sha,
              'current_pointer_bytes': len(pointer), 'current_pointer_sha256': hashlib.sha256(pointer).hexdigest(),
              'complete_gzip_inverse': True, 'original_index_bytes_preserved': True,
              'source_registry_receipt_sha256': plan['issuance']['sha256'],
              'scientific_reexecution': False, 'activation': False}
    receipt = json.dumps(report, separators=(',', ':')).encode() + b'\n'
    assert len(encoded) + len(canonical) + len(baseline_raw) + len(pointer) + len(receipt) <= plan['output_reserve']
    for pin in plan['inputs']:
        guards.admitted_read(pin)
    guard()
    output.mkdir(parents=True)
    for name, body in [('index.json', baseline_raw), ('releases-v9.json.gz', encoded),
                       ('current-manifest.json', pointer), ('registry-encoding.json', receipt)]:
        with (output / name).open('xb') as stream:
            stream.write(body)
        os.chmod(output / name, 0o644)
    print(json.dumps(report))

if __name__ == '__main__':
    raw = pathlib.Path(sys.argv[1]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == os.environ['WORLDATLAS_SELECTED_NATIVE_PLAN_RAW_SHA256']
    run(json.loads(raw), sys.argv[2])
