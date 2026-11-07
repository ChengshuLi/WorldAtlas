#!/usr/bin/env python3
"""Replay an admitted mixed/regional stage with optional equivalent runtime.

Keep the admitted interpreter, selected-source producers, policy and WGS84
solver unchanged. Only the fresh output/config and explicitly selected pinned
regional hook/runtime differ. Run sequentially on already-local inputs.
"""
import argparse
import json
from pathlib import Path
import pstats
import subprocess
import sys
import time

from benchmark_stage import digest, environment

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exclusive_outputs import create_directory_exclusive, create_text_exclusive, write_json_exclusive

INTEGRATION = Path('scripts/v7-land/research-mixed-runtime/lydekker-regional-writer-integration')
STAGE3 = INTEGRATION.parent / 'stage3-mixed-leeward-full-20261105'
POINT = INTEGRATION.parent / 'geonames-point-integration-20261105/point-component-prototype'
RUNTIME_NAMES = ('component_index', 'satellite_index', 'regional_runtime')


def pin(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': digest(path)}


def normalize_equivalence(before, after, equivalence):
    """Normalize only declared, checked orchestration and runtime provenance."""
    if not equivalence:
        return after
    after = json.loads(json.dumps(after))
    for name, values in equivalence['orchestration'].items():
        if before['code_sha256'][name] != values['before'] or after['code_sha256'][name] != values['after']:
            raise ValueError('undeclared orchestration hash: ' + name)
        after['code_sha256'][name] = values['before']
        if name == 'resolver':
            if after['point_resolution']['resolver_sha256'] != values['after']:
                raise ValueError('point resolver provenance mismatch')
            after['point_resolution']['resolver_sha256'] = values['before']
    provenance = after['regional_island_rule']['provenance']['code']
    for name, values in equivalence['reviewed_code_rebindings'].items():
        if (before['regional_island_rule']['provenance']['code'][name] != values['before'] or
                provenance[name] != values['after'] or values['before']['sha256'] != values['after']['sha256']):
            raise ValueError('reviewed code rebinding mismatch: ' + name)
        provenance[name] = values['before']
    for name, container, key, schema in (
            ('point_runtime', after.get('point_resolution', {}), 'equivalent_runtime', 'selected-point-equivalent-runtime-v1'),
            ('polygon_runtime', after, 'polygon_equivalent_runtime', 'polygon-equivalent-runtime-v1')):
        spec = equivalence.get(name)
        if spec:
            evidence = container.get(key, {})
            if (evidence.get('schema') != schema or evidence.get('code') != spec or
                    evidence.get('geographic_policy_changed') is not False or
                    (name == 'polygon_runtime' and evidence.get('rasterization_changed') is not False)):
                raise ValueError('equivalent runtime provenance mismatch: ' + name)
            del container[key]
    return after


def compare(reference, candidate, equivalence=None, request_rebinding=None):
    streams = {name: {'reference': digest(reference / name), 'candidate': digest(candidate / name)}
               for name in ('rows.u32le', 'runs.u32le', 'changes.jsonl')}
    before, after = (json.loads((root / 'report.json').read_bytes()) for root in (reference, candidate))
    after = normalize_equivalence(before, after, equivalence)
    if request_rebinding and ('input_lineage' in before or 'input_lineage' in after):
        after = json.loads(json.dumps(after))
        if (before['input_lineage']['request'] != request_rebinding['before'] or
                after['input_lineage']['request'] != request_rebinding['after'] or
                before['request_sha256'] != request_rebinding['before']['sha256'] or
                after['request_sha256'] != request_rebinding['after']['sha256']):
            raise ValueError('fresh request provenance mismatch')
        after['input_lineage']['request'] = request_rebinding['before']
    decisions_equal = before['regional_island_rule']['result'] == after['regional_island_rule']['result']
    trace_equal = before['regional_island_rule']['proposal_trace'] == after['regional_island_rule']['proposal_trace']
    selected_equal = before['writer']['affiliation_statistics'] == after['writer']['affiliation_statistics']
    def scientific(report):
        result = {key: value for key, value in report.items()
                  if key not in ('processing_elapsed_seconds', 'request_sha256', 'regional_island_rule')}
        regional = report['regional_island_rule']
        result['regional_island_rule'] = {key: value for key, value in regional.items() if key != 'provenance'}
        result['regional_island_rule']['provenance'] = {
            key: value for key, value in regional.get('provenance', {}).items()
            if key not in ('driver_hook', 'equivalent_runtime')}
        return result
    return {'streams': streams, 'streams_equal': all(v['reference'] == v['candidate'] for v in streams.values()),
            'regional_decisions_equal': decisions_equal, 'regional_proposal_trace_equal': trace_equal,
            'selected_affiliation_statistics_equal': selected_equal,
            'scientific_report_equal': scientific(before) == scientific(after)}


def run(admission, out, runtime_root=None, profile=False, producer_root=None):
    admitted = json.loads(admission.read_bytes())
    command = list(admitted['invocation']['command'])
    if len(command) != 3 or Path(command[1]).name != 'apply_selected_mixed.py':
        raise ValueError('expected an admitted three-argument mixed/regional stage')
    for spec in admitted['inputs']:
        if digest(Path(spec['path'])) != spec['sha256']:
            raise ValueError('admitted input changed: ' + spec['path'])
    out = out.absolute()
    if out.exists() or not out.parent.is_dir():
        raise ValueError('fresh benchmark directory with an existing parent required')
    cfg = json.loads(Path(command[2]).read_bytes())
    original_request = pin(command[2])
    reference = Path(cfg['output'])
    cfg['output'] = str(out / 'candidate')
    point_request, equivalence = None, None
    if producer_root is not None:
        producer_root = producer_root.resolve(strict=True)
        builder = producer_root / STAGE3 / 'apply_selected_mixed.py'
        resolver = producer_root / POINT / 'resolve.py'
        equivalence = {'orchestration': {}, 'reviewed_code_rebindings': {},
                       'stage2_input_binding': {'report': cfg['stage2']['report'],
                                                'approval': cfg['stage2_approval'],
                                                'validator_sha256': cfg['code']['validator']}}
        for name, path in (('driver', builder), ('resolver', resolver)):
            equivalence['orchestration'][name] = {'before': cfg['code'][name], 'after': digest(path)}
            cfg['code'][name] = digest(path)
        for name, spec in cfg['regional']['request']['code'].items():
            path = Path(spec['path'])
            parts = path.parts
            if 'scripts' not in parts:
                raise ValueError('reviewed code must be repository-local: ' + name)
            rebound = pin(producer_root / Path(*parts[parts.index('scripts'):]))
            if rebound['sha256'] != spec['sha256']:
                raise ValueError('reviewed regional algorithm changed: ' + name)
            equivalence['reviewed_code_rebindings'][name] = {'before': spec, 'after': rebound}
            cfg['regional']['request']['code'][name] = rebound
        # Preserve the original producer report and approval. The downstream
        # validator itself must remain byte-identical; no upstream relabeling.
        validator = producer_root / 'scripts/v7-recovery/land/stage2-geodesic-20261104/validate_stage2_candidate.py'
        if digest(validator) != cfg['code']['validator']:
            raise ValueError('admitted Stage2 validator changed')
        point_request = json.loads(Path(cfg['point_request']['path']).read_bytes())
        point_request['resolver_sha256'] = cfg['code']['resolver']
        point_runtime = producer_root / POINT / 'point_runtime.py'
        polygon_runtime = producer_root / INTEGRATION / 'polygon_runtime.py'
        if point_runtime.is_file():
            point_request['runtime'] = equivalence['point_runtime'] = pin(point_runtime)
        if polygon_runtime.is_file():
            cfg['polygon_runtime'] = equivalence['polygon_runtime'] = pin(polygon_runtime)
        command[1] = str(builder)
        if runtime_root is None and all((producer_root / INTEGRATION / (name + '.py')).is_file() for name in RUNTIME_NAMES):
            runtime_root = producer_root
    if runtime_root is not None:
        integration = runtime_root.resolve(strict=True) / INTEGRATION
        cfg['regional']['hook'] = pin(integration / 'driver_hook.py')
        cfg['regional']['request']['runtime'] = {name: pin(integration / (name + '.py')) for name in RUNTIME_NAMES}
    create_directory_exclusive(out)
    create_directory_exclusive(out / 'inputs')
    if point_request is not None:
        write_json_exclusive(out / 'inputs/point-request.json', point_request, indent=2)
        cfg['point_request'] = pin(out / 'inputs/point-request.json')
    write_json_exclusive(out / 'inputs/config.json', cfg, indent=2)
    command[2] = str(out / 'inputs/config.json')
    if profile:
        command[1:1] = ['-m', 'cProfile', '-o', str(out / 'profile.pstats')]
    invocation = {'command': command, 'environment': environment(), 'admission': pin(admission),
                  'reference': str(reference), 'runtime': cfg['regional']['request'].get('runtime'),
                  'late_stage_equivalence': equivalence,
                  'request_rebinding': {'before': original_request, 'after': pin(out / 'inputs/config.json')},
                  'scope': 'complete admitted mixed/regional stage; fresh source resolution and writer; already-local inputs'}
    write_json_exclusive(out / 'invocation.json', invocation, indent=2)
    started = time.perf_counter()
    with create_text_exclusive(out / 'builder.log') as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    elapsed = time.perf_counter() - started
    write_json_exclusive(out / 'execution-timing.json', {'process_wall_seconds': elapsed}, indent=2)
    if profile:
        summarize_profile(out)
    return summarize(out)


def summarize(out):
    """Validate a completed replay, including one interrupted during analysis."""
    invocation = json.loads((out / 'invocation.json').read_bytes())
    reference = Path(invocation['reference'])
    if not all((out / 'candidate' / name).is_file() for name in ('rows.u32le', 'runs.u32le', 'changes.jsonl', 'report.json')):
        raise ValueError('producer did not complete all outputs; inspect builder.log')
    rebinding = invocation.get('request_rebinding')
    if rebinding is None:
        admitted = json.loads(Path(invocation['admission']['path']).read_bytes())
        original = Path(admitted['invocation']['command'][-1])
        rebinding = {'before': pin(original), 'after': pin(invocation['command'][-1])}
    parity = compare(reference, out / 'candidate', invocation.get('late_stage_equivalence'), rebinding)
    timing = out / 'execution-timing.json'
    elapsed = json.loads(timing.read_bytes())['process_wall_seconds'] if timing.exists() else None
    producer = json.loads((out / 'candidate/report.json').read_bytes()).get('processing_elapsed_seconds')
    report = {**invocation, 'process_wall_seconds': elapsed, 'producer_wall_seconds': producer, 'parity': parity}
    destination = out / ('stage-validation.json' if (out / 'stage-timing.json').exists() else 'stage-timing.json')
    write_json_exclusive(destination, report, indent=2)
    if not all(parity[k] for k in ('streams_equal', 'regional_decisions_equal', 'regional_proposal_trace_equal',
                                  'selected_affiliation_statistics_equal', 'scientific_report_equal')):
        raise ValueError('regional benchmark output parity failed; inspect stage-timing.json')
    return report


def summarize_profile(out):
    with create_text_exclusive(out / 'profile.txt') as stream:
        stats = pstats.Stats(str(out / 'profile.pstats'), stream=stream)
        stats.strip_dirs().sort_stats('cumulative').print_stats(100)
    report = {'function_calls': stats.total_calls, 'profiled_seconds': stats.total_tt,
              'complete_producer_output': (out / 'candidate/report.json').is_file(),
              'scope': 'cProfile diagnostics only; incomplete outputs do not establish scientific parity'}
    write_json_exclusive(out / 'profile-summary.json', report, indent=2)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--admitted', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--runtime-root', type=Path)
    ap.add_argument('--producer-root', type=Path, help='use new late-stage orchestration, retaining admitted Stage2 provenance')
    ap.add_argument('--profile', action='store_true')
    ap.add_argument('--summarize', action='store_true', help='validate an existing completed replay without rerunning it')
    ap.add_argument('--summarize-profile', action='store_true', help='analyze an existing cProfile recording without rerunning it')
    args = ap.parse_args()
    if not (args.summarize or args.summarize_profile) and args.admitted is None:
        ap.error('--admitted is required for a fresh replay')
    print(json.dumps(summarize_profile(args.out) if args.summarize_profile else summarize(args.out)
                     if args.summarize else run(args.admitted, args.out, args.runtime_root, args.profile, args.producer_root)))


if __name__ == '__main__':
    main()
