"""Supervise the unchanged stock physical entry; no scientific method changes."""
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

root = Path.cwd().resolve()
owned = Path(__file__).resolve().parent
run = root / '.cloud-work/jmg6-physical-001'
config = run / 'physical-config.json'
relative_config = config.relative_to(root).as_posix()
destination = owned.relative_to(root).as_posix() + '/physical-result-001'
assert not (root / destination).exists()
assert owned.is_relative_to(root) and config.is_file()
limits = {'process_group_rss_bytes': 2 * 1024**3, 'wall_seconds': 180,
          'per_file_bytes': 32 * 1024**2, 'owned_physical_disk_bytes': 80 * 1024**2,
          'minimum_free_disk_bytes': 10 * 1024**3, 'poll_seconds': 0.05}
tracked = [owned, run, root / '.cache/delivery-handoff']
def disk_usage():
    return sum(p.stat().st_size for base in tracked if base.exists()
               for p in base.rglob('*') if p.is_file() and not p.is_symlink())
def free_disk():
    s = os.statvfs(root)
    return s.f_bavail * s.f_frsize
memory = {line.split(':')[0]: int(line.split()[1]) * 1024
          for line in Path('/proc/meminfo').read_text().splitlines()
          if line.startswith(('MemTotal:', 'MemAvailable:'))}
assert memory['MemAvailable'] > 2 * limits['process_group_rss_bytes']
assert free_disk() > limits['minimum_free_disk_bytes'] + limits['owned_physical_disk_bytes']
assert disk_usage() < limits['owned_physical_disk_bytes']
raw = config.read_bytes()
cohort = json.loads(raw)
assert len(cohort['physical']['inputs']) == 25
stage_pin = next(p for p in cohort['physical']['inputs']
                 if p['path'] == cohort['physical']['roles']['stages'])
assert stage_pin['commit'] == '226d2d1e80dd83e2a7198c731d53d24b3d35afab'
stages = json.loads((root / stage_pin['path']).read_bytes())
assert len(stages) == 6 and len({s['target'] for s in stages}) == 6
assert sum(s['target'].startswith('government:JMG:') for s in stages) == 5
assert stages[-1]['target'] == 'gb-full:MYS:ADM2:9469f09:92858781B56085190058706'
command = ['node', 'scripts/prepare-delivery-handoff.mjs', 'physical', relative_config, destination]
admission = {'kind': 'six-whole-member-stock-physical-prospective-admission',
             'command': command, 'limits': limits, 'config_sha256': hashlib.sha256(raw).hexdigest(),
             'supervisor_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'physical_program_sha256': hashlib.sha256((root / 'scripts/qualify-source-cohort.py').read_bytes()).hexdigest(),
             'entry_sha256': hashlib.sha256((root / command[1]).read_bytes()).hexdigest(),
             'free_disk_bytes_before': free_disk(), 'owned_disk_bytes_before': disk_usage(),
             'memory_before': memory, 'targets': [s['target'] for s in stages],
             'complete_common_input_encoded_bytes': 85926037,
             'complete_metadata_decoded_bytes': 123347986,
             'complete_native_member_decoded_bytes': 95809336,
             'limits_of_monitor': ['RSS and disk are sampled, not a hermetic cgroup quota.',
                                  'RLIMIT_FSIZE is enforced per file in the whole child process group.',
                                  'The shared producer retains its stock scientific checks and exclusive publication.']}
admission_path = owned / 'prospective-execution-admission.json'
with admission_path.open('x') as f:
    json.dump(admission, f, indent=2)
    f.write('\n')
def child_limits():
    resource.setrlimit(resource.RLIMIT_FSIZE, (limits['per_file_bytes'], limits['per_file_bytes']))
    os.umask(0o022)
start = time.monotonic()
peak_rss = peak_disk = 0
reason = None
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
for key in ['NODE_OPTIONS', 'NODE_PATH']:
    env.pop(key, None)
with (run / 'stock-entry.stdout.log').open('x') as log:
    child = subprocess.Popen(command, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                             env=env, start_new_session=True, preexec_fn=child_limits)
    while child.poll() is None:
        rss = 0
        for item in Path('/proc').iterdir():
            if not item.name.isdigit():
                continue
            try:
                status = (item / 'stat').read_text().split()
                if int(status[4]) == child.pid:
                    rss += int((item / 'statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
            except (OSError, ValueError, IndexError):
                pass
        usage = disk_usage()
        peak_rss = max(peak_rss, rss)
        peak_disk = max(peak_disk, usage)
        if rss > limits['process_group_rss_bytes']:
            reason = 'process-group-rss-limit'
        elif usage > limits['owned_physical_disk_bytes']:
            reason = 'owned-physical-disk-limit'
        elif free_disk() < limits['minimum_free_disk_bytes']:
            reason = 'minimum-free-disk-floor'
        elif time.monotonic() - start > limits['wall_seconds']:
            reason = 'wall-deadline'
        if reason:
            os.killpg(child.pid, signal.SIGKILL)
            break
        time.sleep(limits['poll_seconds'])
    code = child.wait()
receipt = {'kind': 'six-whole-member-stock-physical-actual-execution', 'exit_code': code,
           'elapsed_seconds': time.monotonic() - start, 'termination_reason': reason,
           'sampled_peak_process_group_rss_bytes': peak_rss,
           'sampled_peak_owned_physical_disk_bytes': peak_disk,
           'free_disk_bytes_after': free_disk(), 'owned_disk_bytes_after': disk_usage(),
           'admission_sha256': hashlib.sha256(admission_path.read_bytes()).hexdigest(),
           'stock_complete_products_present': all((root / destination / name).is_file()
               for name in ['whole-target-support.json', 'execution-receipt.json', 'preparation.json']),
           'native_qualification_or_repair_credit': 0}
with (owned / 'actual-execution-observation.json').open('x') as f:
    json.dump(receipt, f, indent=2)
    f.write('\n')
print(json.dumps(receipt))
if code:
    print((run / 'stock-entry.stdout.log').read_text()[-12000:])
sys.exit(code)
