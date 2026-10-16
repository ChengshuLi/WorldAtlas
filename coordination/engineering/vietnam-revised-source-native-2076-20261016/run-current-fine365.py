"""Bounded, captured-code launcher for the genuinely missing current-fine join."""
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time

PREFIX = 'coordination/engineering/vietnam-revised-source-native-2076-20261016/'
LIMIT = 768 * 1024 ** 2
DEADLINE = 120
FLOOR = 10 * 1024 ** 3


def digest(body):
    return hashlib.sha256(body).hexdigest()


def run(commit, destination):
    assert len(commit) == 40 and all(c in '0123456789abcdef' for c in commit)
    destination = pathlib.Path(destination)
    assert not os.path.lexists(destination), 'Execution destination must be absent'
    env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_NO_REPLACE_OBJECTS='1')
    env.pop('NODE_PATH', None)
    env.pop('NODE_OPTIONS', None)

    def captured(name):
        return subprocess.check_output(['git', '--no-lazy-fetch', '--no-replace-objects',
                                        'show', commit + ':' + PREFIX + name], env=env, timeout=15)

    launcher = captured('run-current-fine365.py')
    assert launcher == pathlib.Path(__file__).read_bytes(), 'Launcher differs from captured commit'
    script = captured('observe-current-fine365.mjs')
    disk = os.statvfs('.')
    free = disk.f_bavail * disk.f_frsize
    memory = {line.split(':')[0]: int(line.split()[1]) * 1024
              for line in pathlib.Path('/proc/meminfo').read_text().splitlines()
              if line.startswith(('MemTotal:', 'MemAvailable:'))}
    assert free > FLOOR + 32 * 1024 ** 2, 'Disk headroom refused'
    assert memory['MemAvailable'] > 2 * LIMIT, 'Memory headroom refused'
    destination.mkdir(mode=0o700)
    script_path = destination / 'captured-observe-current-fine365.mjs'
    with script_path.open('xb') as output:
        output.write(script)
    command = ['node', '--max-old-space-size=512', str(script_path.resolve()), commit,
               str((destination / 'current-fine365-observation.json').resolve())]
    admission = {'kind': 'bounded-current-fine365-prospective-admission-v1',
                 'code_commit': commit, 'launcher_sha256': digest(launcher),
                 'script_sha256': digest(script), 'command': command,
                 'scope': 'All36 indexed canonical parts/49625 features at cd68e895, all365 original keys; only missing current fine contacts/ties',
                 'complete_geography_encoded_bytes': 203282806,
                 'largest_part_encoded_bytes': 12932719,
                 'representation': 'One immutable Git part at a time; validated complete ring bounds exclude only provably irrelevant features; stock exact-native predicates for every survivor',
                 'memory_rss_limit_bytes': LIMIT, 'node_heap_limit_mib': 512,
                 'wall_deadline_seconds': DEADLINE, 'poll_seconds': 0.05,
                 'free_bytes_before': free, 'memory_before': memory,
                 'output_and_log_allowance_bytes': 32 * 1024 ** 2,
                 'sampled_peak_is_not_continuous_maximum': True}
    admission_path = destination / 'current-fine365-admission.json'
    with admission_path.open('x') as output:
        output.write(json.dumps(admission, indent=2) + '\n')
    started = time.monotonic()
    peak = 0
    reason = None
    process = None
    try:
        with (destination / 'current-fine365-execution.log').open('x') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       env=env, start_new_session=True)
            while process.poll() is None:
                rss = 0
                for entry in pathlib.Path('/proc').iterdir():
                    if not entry.name.isdigit():
                        continue
                    try:
                        fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
                        if int(fields[2]) == process.pid:
                            rss += int((entry / 'statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
                    except (OSError, ValueError, IndexError):
                        pass
                peak = max(peak, rss)
                if rss > LIMIT:
                    reason = 'process_group_rss_limit'
                elif time.monotonic() - started > DEADLINE:
                    reason = 'wall_deadline'
                elif sum(p.stat().st_size for p in destination.iterdir() if p.is_file()) > 32 * 1024 ** 2:
                    reason = 'output_log_allowance'
                if reason:
                    os.killpg(process.pid, signal.SIGKILL)
                    break
                time.sleep(0.05)
            code = process.wait()
    except BaseException:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        raise
    receipt = {'kind': 'bounded-current-fine365-actual-execution-v1', 'exit_code': code,
               'code_commit': commit, 'enforced_process_group_rss_limit_bytes': LIMIT,
               'observed_sampled_process_group_peak_rss_bytes': peak,
               'enforced_wall_deadline_seconds': DEADLINE,
               'elapsed_seconds': time.monotonic() - started, 'termination_reason': reason,
               'admission_sha256': digest(admission_path.read_bytes()),
               'native_qualification': False, 'accepted_credit': 0}
    with (destination / 'current-fine365-execution.json').open('x') as output:
        output.write(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    print((destination / 'current-fine365-execution.log').read_text())
    assert code == 0 and reason is None, 'No successful scientific completion receipt'


if __name__ == '__main__':
    assert len(sys.argv) == 3, 'Usage: python run-current-fine365.py CODE_COMMIT NEW_DESTINATION'
    run(sys.argv[1], sys.argv[2])
