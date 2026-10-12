"""One fresh bounded operand execution, including terminal group cleanup."""
import ctypes
import datetime
import json
import os
import pathlib
import signal
import subprocess
import sys
import time


def group_members(group):
    result = []
    for directory in pathlib.Path('/proc').iterdir():
        if not directory.name.isdigit():
            continue
        try:
            fields = (directory / 'stat').read_text().split(') ', 1)[1].split()
            if int(fields[2]) == group and int(fields[3]) == group:
                result.append({'pid': int(directory.name), 'state': fields[0],
                               'rss': int((directory / 'statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')})
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return result


def stop_group(group, sig):
    try:
        os.killpg(group, sig)
    except ProcessLookupError:
        pass


def reap_group(group):
    reaped = []
    while True:
        try:
            pid, status = os.waitpid(-group, os.WNOHANG)
        except ChildProcessError:
            break
        if not pid:
            break
        reaped.append({'pid': pid, 'wait_status': status})
    return reaped


def observe(command, run, env, cap, wall):
    # Linux subreaping makes orphaned grandchildren owned and waitable here.
    assert sys.platform == 'linux'
    assert ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0
    with (run / 'stdout.log').open('x') as out, (run / 'stderr.log').open('x') as err:
        process = subprocess.Popen(command, stdout=out, stderr=err, start_new_session=True, env=env)
        start, maximum, samples, stopped = time.monotonic(), 0, 0, None
        try:
            while process.poll() is None:
                total = sum(row['rss'] for row in group_members(process.pid))
                maximum, samples = max(maximum, total), samples + 1
                if total > cap or time.monotonic() - start > wall:
                    stopped = 'aggregate-rss-limit' if total > cap else 'wall-timeout'
                    break
                time.sleep(.05)
        finally:
            if process.poll() is None:
                stop_group(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    stop_group(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
            code = process.wait()
            # Parent exit does not establish complete owned-process termination.
            survivors = group_members(process.pid)
            reaped = []
            if survivors:
                stopped = stopped or 'orphaned-owned-descendants'
                for sig in [signal.SIGTERM, signal.SIGKILL]:
                    stop_group(process.pid, sig)
                    until = time.monotonic() + 5
                    while time.monotonic() < until:
                        reaped.extend(reap_group(process.pid))
                        if not group_members(process.pid):
                            break
                        time.sleep(.05)
                    if not group_members(process.pid):
                        break
            reaped.extend(reap_group(process.pid))
            remaining = group_members(process.pid)
    result = {'exit_code': code if not stopped and not remaining else code or 1,
              'parent_exit_code': code, 'elapsed_seconds': round(time.monotonic() - start, 3),
              'sampled_process_group_peak_rss_bytes': maximum, 'sampling_interval_ms': 50,
              'samples': samples, 'stopped': stopped, 'subreaper': True,
              'survivors_at_parent_terminal': survivors, 'reaped_descendants': reaped,
              'survivors_after_cleanup': remaining}
    with (run / 'process-group.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


def fresh_run(run):
    for ancestor in run.parents:
        assert ancestor.is_dir() and not ancestor.is_symlink()
    assert not os.path.lexists(run)
    run.mkdir()


def main():
    repo = pathlib.Path.cwd().resolve()
    env = dict(os.environ)
    for key in ['GH_TOKEN', 'GITHUB_TOKEN', 'GH_DEBUG', 'DEBUG', 'NODE_OPTIONS', 'NODE_PATH']:
        env.pop(key, None)
    env.update(GIT_NO_LAZY_FETCH='1', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_TERMINAL_PROMPT='0')
    if sys.argv[1:] == ['--control-orphan-cleanup']:
        run = repo / '.cache/1767/supervisor-orphan-control'
        fresh_run(run)
        child = 'import os,time; child=os.fork(); os._exit(0) if child else time.sleep(60)'
        result = observe([sys.executable, '-c', child], run, env, 64 * 1024**2, 10)
        assert result['parent_exit_code'] == 0 and result['exit_code'] != 0
        assert result['stopped'] == 'orphaned-owned-descendants'
        assert result['survivors_at_parent_terminal'] and result['reaped_descendants']
        assert not result['survivors_after_cleanup']
        print(json.dumps(result))
        return
    assert len(sys.argv) == 2
    head = sys.argv[1]
    assert len(head) == 40 and all(character in '0123456789abcdef' for character in head)
    before = '9473d184683ee8ff8546300f2313779c3cba1d2b'
    after = '791576647adc41241ce9b438f1bb0034088eed4e'
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == head
    run = repo / '.cache/1767/retained-proof-001'
    reserved = int(os.environ['WORLDATLAS_CONCURRENT_RESERVED_BYTES'])
    assert reserved >= 0
    available = int(next(line.split()[1] for line in pathlib.Path('/proc/meminfo').read_text().splitlines()
                         if line.startswith('MemAvailable:'))) * 1024
    cap, parent, residual = 2 * 1024**3, 2 * 1024**3, 768 * 1024**2
    assert available - reserved - cap - parent >= residual
    command = ['node', '--expose-gc',
               'coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs',
               'continuous', str(repo), head, before, after, str(run / 'complete'), str(pathlib.Path(sys.executable).resolve())]
    fresh_run(run)
    admission = {'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'execution_commit': head, 'baseline_commit': before, 'candidate_commit': after,
                 'command': command, 'mem_available_bytes': available, 'job_reserved_bytes': cap,
                 'parent_reserved_bytes': parent, 'concurrent_reserved_bytes': reserved,
                 'minimum_residual_bytes': residual, 'wall_seconds': 1200, 'sampling_interval_ms': 50,
                 'scope': 'One actual Node operand execution. Reuse original strict polygon result only if complete encoded/decoded operands equal retained genuine evidence.'}
    with (run / 'admission.json').open('x') as stream:
        json.dump(admission, stream, indent=2)
        stream.write('\n')
    result = observe(command, run, env, cap, 1200)
    print(json.dumps(result))
    raise SystemExit(result['exit_code'])


if __name__ == '__main__':
    main()
