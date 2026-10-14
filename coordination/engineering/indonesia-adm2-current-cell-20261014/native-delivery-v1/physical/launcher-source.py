import hashlib, json, os, resource, subprocess, sys, time
from pathlib import Path

root = Path('.cache/full-census')
config = json.loads((root / 'prospective-operating-config.json').read_bytes())
receipt_path = root / 'execution-receipt.json'
assert not receipt_path.exists() and not receipt_path.is_symlink()
runtime = '/Users/chengshuli/world-atlas-workspace/.cache/root1603-final-review-20261009/gis-venv/bin/python'
log = root / 'physical-run.log'
started = time.monotonic()
result = {'version': 1, 'complete': False, 'deadline_seconds': config['deadline_seconds'],
          'enforcement_limits': config['enforcement_limits'], 'repaired_credit': 0}

def file_limit():
    resource.setrlimit(resource.RLIMIT_FSIZE, (config['maximum_output_file_bytes'],
                                            config['maximum_output_file_bytes']))

try:
    with log.open('xb') as output:
        child = subprocess.run([runtime, str(root / 'physical-reproduction.py')],
                               stdout=output, stderr=subprocess.STDOUT,
                               env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'},
                               timeout=config['deadline_seconds'], preexec_fn=file_limit)
    result['exit_code'] = child.returncode
    assert child.returncode == 0, 'Physical producer failed; preserve its output'
    target = root / 'gshhg-direct/whole-target-support.json'
    data = target.read_bytes()
    assert len(data) <= config['maximum_output_file_bytes']
    body = json.loads(data)
    stages = json.loads((root / 'all-stage-inputs.json').read_bytes())
    assert [x['target'] for x in body['results']] == [x['target'] for x in stages]
    result.update(complete=True, output={'path': str(target), 'bytes': len(data),
                                        'sha256': hashlib.sha256(data).hexdigest()},
                  inspected_targets=len(body['results']),
                  targets_with_issues=sum(bool(x['issues']) for x in body['results']))
except subprocess.TimeoutExpired:
    result['failure'] = 'Deadline expired; direct child killed/waited by subprocess.run; descendant cleanup unverified'
except Exception as error:
    result['failure'] = str(error)
finally:
    peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    result['maximum_child_lifetime_rss_bytes'] = peak if sys.platform == 'darwin' else peak * 1024
    result['rss_measurement_limit'] = 'Fresh launcher child lifetime maximum; not live aggregate process-tree enforcement'
    result['elapsed_seconds'] = time.monotonic() - started
    result['within_planned_rss_ceiling'] = result['maximum_child_lifetime_rss_bytes'] <= config['fresh_admission']['physical_complete_process_planning_ceiling']
    with receipt_path.open('x') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(json.dumps(result))
if not result['complete']:
    sys.exit(1)
