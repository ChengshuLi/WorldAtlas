"""Tiny directed checks of the discovery admission used by the real driver.

These exercise byte and descriptor admission only. They do not establish a
complete source acquisition, native replay, physical classification or repair.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    here = Path(__file__).resolve().parent
    adapter = load('preview_control_adapter', here / 'acquisition-phases.py')
    driver = load('preview_control_driver', here / 'acquisition-driver.py')
    pin = {'path': '/example/inventory.json.gz', 'bytes': 10,
           'sha256': 'a' * 64, 'uncompressed_bytes': 100,
           'uncompressed_sha256': 'b' * 64}
    controls = []

    def check(name, pins, *, runtime=50, reserve=20, verified=True,
              expected=None, reject=False):
        try:
            actual = driver.admit_previews(
                adapter, pins, runtime_bytes=runtime,
                runtime_verified=verified, output_reserve=reserve)
        except ValueError:
            if not reject:
                raise
        else:
            if reject or (expected is not None and actual != expected):
                raise AssertionError(name)
        controls.append({'name': name, 'passed': True})

    check('whole encoded plus decoded charged', [pin], expected=110)
    check('same whole input charged once', [pin, pin], expected=110)
    check('conflicting descriptor rejected', [pin, dict(pin, bytes=11)], reject=True)
    check('decoded oversized before opening',
          [dict(pin, uncompressed_bytes=adapter.FILE + 1)], reject=True)
    check('aggregate discovery rejected before opening',
          [dict(pin, path='/example/%d' % i, bytes=adapter.FILE,
                uncompressed_bytes=adapter.FILE) for i in range(5)], reject=True)
    check('unverified runtime rejected', [pin], verified=False, reject=True)
    check('output reserve fully charged', [pin], reserve=adapter.PHASE, reject=True)
    check('descriptor cap rejected',
          [dict(pin, path='/example/%d' % i) for i in range(512)], reject=True)
    print(json.dumps({
        'status': 'passed', 'controls': controls,
        'driver_sha256': hashlib.sha256((here / 'acquisition-driver.py').read_bytes()).hexdigest(),
        'scope': 'Tiny direct discovery-admission controls; no global numerical execution.'},
        sort_keys=True))


if __name__ == '__main__':
    main()
