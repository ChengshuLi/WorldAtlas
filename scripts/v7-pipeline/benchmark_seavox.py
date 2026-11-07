#!/usr/bin/env python3
"""Time one complete batched extraction against a pinned individual-stage run.

Every selected canonical feature byte and scientific provenance field must
match. Candidate timing excludes comparison. Reference command totals came from the
original concurrent run and are not an isolated wall-clock speedup measurement.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time

from benchmark_stage import digest, environment
from exclusive_outputs import create_directory_exclusive, create_text_exclusive, write_json_exclusive


def read(path):
    return json.loads(path.read_bytes())


def selection(reference):
    request = read(reference / 'request.json')
    sources = {key: dict(request['sources'][key]) for key in ('seavox_archive', 'water_snapshot')}
    for spec in sources.values():
        path = Path(spec['path'])
        if not path.is_absolute():
            config = Path(read(reference / 'run-identity.json')['request']['path'])
            path = config.parent / path
        spec['path'] = str(path.resolve(strict=True))
        if digest(path) != spec['sha256']:
            raise ValueError('reference extraction input pin mismatch')
    decisions = read(Path(sources['water_snapshot']['path']))['basins']
    ids = [item['id'] for item in decisions]
    if (not ids or len(set(ids)) != len(ids)
            or any(not isinstance(ident, str) or not re.fullmatch(r'[a-z0-9_-]+', ident) for ident in ids)):
        raise ValueError('reference basin decision inventory is invalid')
    return request, sources, {item['id']: item for item in decisions}


def compare_extractions(reference, candidate):
    _, sources, decisions = selection(reference)
    index = read(candidate / 'batch-manifest.json')
    entries = index.get('features', [])
    if (index.get('schema') != 'worldatlas-seavox-batch-extraction-v1'
            or index.get('status') != 'completed_unverified_candidate_not_published'
            or index.get('archive_sha256') != sources['seavox_archive']['sha256']
            or index.get('decision_snapshot_sha256') != sources['water_snapshot']['sha256']
            or index.get('decision_count') != len(decisions)
            or index.get('feature_count') != len({str(item['source_feature_id']) for item in decisions.values()})
            or [entry.get('decision_id') for entry in entries] != sorted(decisions)):
        raise ValueError('candidate extraction selection or provenance differs')
    content = []
    feature_bytes = 0
    for item in entries:
        ident = item['decision_id']
        folder = reference / 'extractions' / ident
        receipt = read(reference / 'checkpoints' / ('extract-' + ident) / 'complete.json')
        expected_files = {str(folder / name) for name in ('source.geojson', 'manifest.json')}
        if (receipt.get('schema') != 'worldatlas-command-checkpoint-v1'
                or set(spec['path'] for spec in receipt.get('outputs', [])) != expected_files):
            raise ValueError('reference extraction checkpoint is incomplete')
        for spec in receipt['outputs']:
            if digest(Path(spec['path'])) != spec['sha256']:
                raise ValueError('reference extraction output differs from checkpoint')
        feature_file, manifest_file = ident + '/source.geojson', ident + '/manifest.json'
        if item.get('feature_file') != feature_file or item.get('manifest_file') != manifest_file:
            raise ValueError('candidate extraction index path differs')
        feature, manifest_path = candidate / feature_file, candidate / manifest_file
        if (digest(feature) != item.get('feature_file_sha256')
                or digest(manifest_path) != item.get('manifest_file_sha256')):
            raise ValueError('candidate extraction output differs from index')
        old, new = read(folder / 'manifest.json'), read(manifest_path)
        if (item.get('source_feature_id') != str(decisions[ident]['source_feature_id'])
                or item.get('geometry_sha256') != decisions[ident]['geometry_sha256']
                or new.get('gdal_version') != index.get('gdal_version')):
            raise ValueError('candidate extraction index identity differs')
        if (old.get('schema') != 'worldatlas-seavox-archive-extraction-v1'
                or old.get('decision_id') != ident
                or old.get('decision_snapshot_sha256') != sources['water_snapshot']['sha256']
                or old.get('archive_sha256') != sources['seavox_archive']['sha256']
                or old.get('geometry_sha256') != decisions[ident]['geometry_sha256']
                or str(old.get('source_feature_id')) != str(decisions[ident]['source_feature_id'])):
            raise ValueError('reference extraction is not the selected source')
        for doc in (old, new):
            doc.pop('processing_elapsed_seconds', None)
        if old != new:
            raise ValueError('extraction scientific provenance differs: ' + ident)
        original = digest(folder / 'source.geojson')
        if original != item['feature_file_sha256'] or original != old['feature_file_sha256']:
            raise ValueError('canonical feature bytes differ: ' + ident)
        feature_bytes += feature.stat().st_size
        content.append({'decision_id': ident, 'source_feature_id': item['source_feature_id'],
                        'geometry_sha256': item['geometry_sha256'], 'feature_file_sha256': original})
    expected = {'water/extract-' + ident for ident in decisions}
    times = {}
    with (reference / 'timing-events.jsonl').open() as stream:
        for line in stream:
            event = json.loads(line)
            if event.get('event') == 'complete' and event.get('id') in expected:
                if event['id'] in times:
                    raise ValueError('reference has ambiguous repeated extraction timings')
                times[event['id']] = event['monotonic_seconds'] - event['start_monotonic_seconds']
    if times.keys() != expected or any(seconds < 0 for seconds in times.values()):
        raise ValueError('reference extraction timing inventory is incomplete')
    return {'status': 'all-selected-feature-bytes-and-provenance-identical',
            'decision_count': len(decisions), 'feature_bytes': feature_bytes, 'features': content,
            'reference_summed_command_seconds': sum(times.values()),
            'reference_timing_scope': 'Sum of individual stage command intervals, including checkpoint completion, in the original concurrent run; not isolated wall time.',
            'candidate_index_sha256': digest(candidate / 'batch-manifest.json')}


def run(reference, code_root, out):
    reference, code_root, out = reference.resolve(), code_root.resolve(), out.absolute()
    request, sources, _ = selection(reference)
    create_directory_exclusive(out)
    scratch = create_directory_exclusive(out / 'scratch')
    env = dict(os.environ, **{key: str(scratch) for key in ('TMPDIR', 'TMP', 'TEMP', 'CPL_TMPDIR', 'SQLITE_TMPDIR')})
    env['PROJ_NETWORK'] = 'OFF'
    # Retain the interpreter selected by the original supported pipeline.
    identity = read(reference / 'run-identity.json')
    executable = Path(identity['runtime']['executable'])
    if digest(executable.resolve()) != identity['runtime']['binary_sha256']:
        raise ValueError('original extraction interpreter changed')
    builder = code_root / 'scripts/v7-replay/extract_seavox_features.py'
    command = [str(executable), str(builder),
               '--input-root', request['input_root'], '--archive', sources['seavox_archive']['path'],
               '--policy', sources['water_snapshot']['path'], '--policy-sha256', sources['water_snapshot']['sha256'],
               '--out', str(out / 'candidate'), '--work-root', str(scratch),
               '--allow-unverified-snapshot', '--allow-draft-snapshot']
    invocation = {'command': command, 'environment': {**environment(), 'TMPDIR': str(scratch), 'PROJ_NETWORK': 'OFF'},
                  'reference_request_sha256': digest(reference / 'request.json'),
                  'inputs': sources, 'code_sha256': {name: digest(code_root / 'scripts' / name) for name in (
                      'v7-replay/extract_seavox_features.py', 'v7-replay/extract_seavox_feature.py',
                      'v7-replay/decision_snapshot.py', 'v7-replay/seavox_properties.py', 'exclusive_outputs.py')}}
    write_json_exclusive(out / 'invocation.json', invocation, indent=2)
    started = time.perf_counter()
    with create_text_exclusive(out / 'builder.log') as log:
        subprocess.run(command, env=env, check=True, stdout=log, stderr=subprocess.STDOUT)
    timing = {**invocation, 'process_wall_seconds': time.perf_counter() - started,
              'scope': 'One complete pinned batch, including interpreter startup; comparison excluded.'}
    write_json_exclusive(out / 'stage-timing.json', timing, indent=2)
    comparison = compare_extractions(reference, out / 'candidate')
    write_json_exclusive(out / 'comparison.json', comparison, indent=2)
    return {'process_wall_seconds': timing['process_wall_seconds'], **comparison}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference-run', type=Path, required=True)
    p.add_argument('--code-root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(run(args.reference_run, args.code_root, args.out)))


if __name__ == '__main__':
    main()
