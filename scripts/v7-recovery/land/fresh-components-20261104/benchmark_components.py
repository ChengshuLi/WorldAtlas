#!/usr/bin/env python3
"""Replay complete pinned physical RLE and verify exact component output bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import runpy
import time
from unittest.mock import patch

import components


def pin(path):
    path = Path(path).resolve(strict=True)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--physical-rows', required=True)
    parser.add_argument('--physical-runs', required=True)
    parser.add_argument('--expected-rows', required=True)
    parser.add_argument('--expected-runs', required=True)
    parser.add_argument('--width', required=True, type=int)
    parser.add_argument('--height', required=True, type=int)
    parser.add_argument('--output', required=True)
    parser.add_argument('--physical-report', help='Also exercise the complete guarded driver and atomic publication')
    args = parser.parse_args(argv)
    paths = {key: pin(getattr(args, key)) for key in ('physical_rows', 'physical_runs', 'expected_rows', 'expected_runs')}
    if args.physical_report:
        paths['physical_report'] = pin(args.physical_report)
    code = pin(Path(components.__file__))
    output = Path(args.output).resolve()
    output.mkdir()
    stage = output / 'components' if args.physical_report else output
    driver_report = None
    started = time.perf_counter()
    with patch('subprocess.Popen', side_effect=AssertionError('process launch')), \
            patch('ctypes.CDLL', side_effect=AssertionError('custom native binding')):
        if args.physical_report:
            inputs = output / 'inputs'
            inputs.mkdir()
            request = {'schema': 'fresh-physical-components-v1',
                       'grid': {'width': args.width, 'height': args.height, 'west': -180, 'north': 90, 'step': 360 / args.width},
                       'controls': {'minimum_free_bytes': 2 * 1024**3},
                       'inputs': {key: {name: value for name, value in paths[key].items() if name != 'bytes'}
                                  for key in ('physical_rows', 'physical_runs', 'physical_report')}}
            request['inputs']['component_source'] = {name: value for name, value in code.items() if name != 'bytes'}
            request_path = inputs / 'request.json'
            request_path.write_text(json.dumps(request, sort_keys=True, indent=2) + '\n')
            driver = Path(components.__file__).with_name('build_components.py')
            driver_report = runpy.run_path(str(driver))['run'](request_path, output / 'work', stage)
            result = {key: int(value) for key, value in (field.split('=') for field in driver_report['builder_output'].split())}
        else:
            result = components.build(args.width, args.height, args.physical_rows, args.physical_runs,
                                      stage / 'rows.u32le', stage / 'runs.u32le')
    seconds = time.perf_counter() - started
    actual = {name: pin(stage / (name + '.u32le')) for name in ('rows', 'runs')}
    for name in actual:
        if actual[name]['sha256'] != paths['expected_' + name]['sha256']:
            raise ValueError('complete component output differs: ' + name)
    if code != pin(Path(components.__file__)) or any(spec != pin(spec['path']) for spec in paths.values()):
        raise ValueError('source or input changed')
    report = {'status': 'complete-component-streams-byte-identical', 'grid': {'width': args.width, 'height': args.height},
              'source': code, 'inputs': paths, 'outputs': actual, 'elapsed_seconds': seconds, 'counts': result,
              'runtime': {'implementation': platform.python_implementation(), 'version': platform.python_version()},
              'process_launches': 0, 'custom_native_bindings': 0}
    if driver_report is not None:
        report['driver_report'] = driver_report
        report['publication_receipt'] = pin(stage.resolve().parent / 'publication.json')
    (output / 'report.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print(json.dumps(report, sort_keys=True))
    return report


if __name__ == '__main__':
    main()
