#!/usr/bin/env python3
"""Sequential, complete SeaVoX extraction A/B with exact feature/provenance QA."""
import argparse
from datetime import datetime, timezone
import importlib
import json
import re
from pathlib import Path
import sys
import time

from benchmark_stage import digest, environment
from exclusive_outputs import create_directory_exclusive, write_json_exclusive
from run_pipeline import stage_scratch


def read(path):
    return json.loads(Path(path).read_bytes())


def compare_batches(reference, candidate, policy, policy_sha256, archive_sha256):
    if digest(policy) != policy_sha256:
        raise ValueError('selected policy pin mismatch')
    selected_basins = read(policy)['basins']
    decisions = {item['id']: item for item in selected_basins}
    if (len(decisions) != len(selected_basins) or not decisions
            or any(not isinstance(name, str) or not re.fullmatch(r'[a-z0-9_-]+', name) for name in decisions)):
        raise ValueError('duplicate or unsafe selected decision')
    manifests = []
    for root in (reference, candidate):
        index = read(root / 'batch-manifest.json')
        if (index.get('schema') != 'worldatlas-seavox-batch-extraction-v1'
                or index.get('status') != 'completed_unverified_candidate_not_published'
                or index.get('decision_snapshot_sha256') != policy_sha256
                or index.get('archive_sha256') != archive_sha256
                or index.get('decision_count') != len(decisions)
                or index.get('feature_count') != len({str(value['source_feature_id']) for value in decisions.values()})
                or [item.get('decision_id') for item in index.get('features', [])] != sorted(decisions)):
            raise ValueError('complete selected batch identity differs')
        current = {}
        for item in index['features']:
            name = item['decision_id']
            selected = decisions[name]
            if (item.get('feature_file') != name + '/source.geojson'
                    or item.get('manifest_file') != name + '/manifest.json'
                    or item.get('geometry_sha256') != selected['geometry_sha256']
                    or item.get('source_feature_id') != str(selected['source_feature_id'])):
                raise ValueError('batch entry identity/path differs: ' + name)
            feature, receipt = root / item['feature_file'], root / item['manifest_file']
            if digest(feature) != item.get('feature_file_sha256') or digest(receipt) != item.get('manifest_file_sha256'):
                raise ValueError('batch output differs from its own sealed index: ' + name)
            provenance = read(receipt)
            if (provenance.get('schema') != 'worldatlas-seavox-archive-extraction-v1'
                    or provenance.get('decision_id') != name
                    or str(provenance.get('source_feature_id')) != str(selected['source_feature_id'])
                    or provenance.get('gdal_version') != index.get('gdal_version')
                    or provenance.get('geometry_sha256') != selected['geometry_sha256']
                    or provenance.get('archive_sha256') != archive_sha256
                    or provenance.get('decision_snapshot_sha256') != policy_sha256
                    or provenance.get('feature_file_sha256') != item['feature_file_sha256']):
                raise ValueError('batch provenance differs from selection: ' + name)
            provenance.pop('processing_elapsed_seconds', None)
            current[name] = {'feature_file_sha256': digest(feature), 'provenance': provenance,
                             'bytes': feature.stat().st_size}
        manifests.append(current)
    if manifests[0] != manifests[1]:
        raise ValueError('reference/candidate feature bytes or scientific provenance differ')
    return {'status': 'all-selected-feature-bytes-and-provenance-identical',
            'decision_count': len(decisions), 'feature_bytes': sum(value['bytes'] for value in manifests[0].values())}


def benchmark(archive, archive_sha256, root, policy, policy_sha256, out, code_root):
    archive, root, policy, code_root = (Path(value).resolve(strict=True) for value in (archive, root, policy, code_root))
    out = Path(out).resolve()
    if (not archive.is_relative_to(root) or not policy.is_relative_to(root)
            or not out.is_relative_to(root) or any(source.is_relative_to(out) for source in (archive, policy))):
        raise ValueError('fresh separate benchmark and pinned sources must be inside input root')
    if digest(archive) != archive_sha256 or digest(policy) != policy_sha256:
        raise ValueError('benchmark source pin mismatch')
    create_directory_exclusive(out)
    scratch = create_directory_exclusive(out / 'scratch')
    sources = ['extract_seavox_features.py', 'extract_seavox_feature.py',
               'seavox_coordinates.py', 'decision_snapshot.py', 'seavox_properties.py', 'local_water_overlay.py']
    invocation = {'archive_sha256': archive_sha256, 'policy_sha256': policy_sha256,
        'environment': environment(), 'code_sha256': {name: digest(code_root / 'scripts/v7-replay' / name) for name in sources},
        'benchmark_sha256': digest(Path(__file__)),
        'exclusive_outputs_sha256': digest(code_root / 'scripts/exclusive_outputs.py'),
        'scope': 'Complete selected batches, sequential and in-process; exact comparison excluded.'}
    write_json_exclusive(out / 'invocation.json', invocation, indent=2)
    sys.path.insert(0, str(code_root / 'scripts/v7-replay'))
    producer = importlib.import_module('extract_seavox_features')
    for name in ('extract_seavox_features', 'extract_seavox_feature', 'decision_snapshot', 'seavox_properties'):
        if Path(sys.modules[name].__file__).resolve() != code_root / 'scripts/v7-replay' / (name + '.py'):
            raise ValueError('benchmark module resolved outside the selected checkout: ' + name)
    timings = {}
    for mode in ('scalar-reference', 'arrow-candidate'):
        started_utc = datetime.now(timezone.utc).isoformat()
        started = time.perf_counter()
        with stage_scratch(str(scratch)):
            result = producer.run(archive, root, policy, policy_sha256, out / mode,
                allow_unverified=True, allow_draft=True, work_root=scratch,
                scalar_coordinates=mode == 'scalar-reference')
        timings[mode] = {'in_process_wall_seconds': time.perf_counter() - started, 'producer': result,
                        'started_at_utc': started_utc, 'ended_at_utc': datetime.now(timezone.utc).isoformat()}
    if digest(archive) != archive_sha256 or digest(policy) != policy_sha256:
        raise ValueError('benchmark source changed')
    if any(digest(code_root / 'scripts/v7-replay' / name) != value
           for name, value in invocation['code_sha256'].items()):
        raise ValueError('benchmark producer code changed')
    if (digest(Path(__file__)) != invocation['benchmark_sha256']
            or digest(code_root / 'scripts/exclusive_outputs.py') != invocation['exclusive_outputs_sha256']):
        raise ValueError('benchmark/output helper changed')
    # Deferred imports must also come from this checkout. In particular, a
    # cached array converter must not run while receipts hash a different file.
    for filename in sources:
        name = Path(filename).stem
        module = sys.modules.get(name)
        if ((name == 'seavox_coordinates' and module is None)
                or (module is not None and Path(module.__file__).resolve()
                    != code_root / 'scripts/v7-replay' / filename)):
            raise ValueError('benchmark module resolved outside the selected checkout: ' + name)
    comparison = compare_batches(out / 'scalar-reference', out / 'arrow-candidate', policy, policy_sha256, archive_sha256)
    result = {**invocation, 'timings': timings, 'comparison': comparison}
    write_json_exclusive(out / 'report.json', result, indent=2)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--archive-sha256', required=True)
    parser.add_argument('--input-root', required=True, type=Path)
    parser.add_argument('--policy', required=True, type=Path)
    parser.add_argument('--policy-sha256', required=True)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--code-root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    print(json.dumps(benchmark(args.archive, args.archive_sha256, args.input_root, args.policy,
        args.policy_sha256, args.out, args.code_root), indent=2))
