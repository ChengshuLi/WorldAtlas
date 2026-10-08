#!/usr/bin/env python3
"""Run and retain two isolated non-geographic safe-publication controls."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guarded_run
import verify_bounded_run


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def run(prefix):
    if not prefix or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in prefix):
        raise ValueError('Run prefix must be lowercase letters, digits and hyphens')
    try:
        baseline = guarded_run.baseline_for()
        guarded_run.refuse_original(guarded_run.REPO, baseline)
    except ValueError as error:
        refusal = str(error)
        if 'Complete logical stream exceeds per-file limit' not in refusal or 'complete phase budget' not in refusal:
            raise
    else:
        raise ValueError('Original complete operation unexpectedly admitted')
    runs = []
    for index in (1, 2):
        vintage = prefix + '-run-' + str(index)
        started = utc()
        output_descriptors = guarded_run.run_synthetic(guarded_run.REPO, vintage, baseline)
        root = guarded_run.OWNED
        run_dir = guarded_run.REPO / root / 'vintages' / vintage
        verified = verify_bounded_run.verify_run(run_dir)
        runs.append({'vintage': vintage, 'started_at_utc': started, 'finished_at_utc': utc(),
                     'verification': verified, 'outputs': output_descriptors})
    if [[row['bytes'], row['sha256']] for row in runs[0]['outputs']] != [[row['bytes'], row['sha256']] for row in runs[1]['outputs']]:
        raise ValueError('Independent bounded products differ')
    manifest = json.loads(guarded_run.MANIFEST.read_bytes())
    closure = manifest['original_operation']['input_closure']
    receipt = {'version': 1, 'status': 'complete', 'geographic_claim': False,
               'scope': 'Synthetic writer/acceptance controls only; no original extraction or geography rerun.',
               'runtime': {'python': platform.python_version(), 'platform': platform.platform(),
                           'helper': 'worldatlas-evidence-preparation-v1'},
               'execution_code_sha256': {'producer': digest(HERE / 'guarded_run.py'),
                                         'acceptance_reader': digest(HERE / 'verify_bounded_run.py'),
                                         'runner': digest(__file__)},
               'original_operation': {'authenticated_unique_inputs': len(closure),
                                     'raw_encoded_bytes': sum(row['bytes'] for row in closure),
                                     'declared_decoded_bytes': sum(row.get('uncompressed_bytes', 0) for row in closure),
                                     'complete_phase_lower_bound_bytes': 531409507,
                                     'component_logical_stream_bytes': 208391779,
                                     'family_logical_stream_bytes': 111223285},
               'limits': {'max_file_bytes': 33554432, 'max_phase_bytes': 268435456,
                          'original_operation_refused_before_decode': True,
                          'refusal_reason': refusal},
               'runs': runs}
    from evidence.immutable import NewVintage
    run = NewVintage(baseline, root, prefix + '-receipt', ['bounded-control-runs.json'])
    descriptors = run.publish({'bounded-control-runs.json': receipt})
    return {'receipt_vintage': prefix + '-receipt', 'outputs': descriptors,
            'runs': [{'vintage': row['vintage'], 'outputs': len(row['outputs'])} for row in runs]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', required=True)
    print(json.dumps(run(parser.parse_args().prefix), sort_keys=True))
