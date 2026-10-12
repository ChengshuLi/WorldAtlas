#!/usr/bin/env python3
"""Acquire one exact CI Git tree; no candidate code or persistent authentication."""
import argparse
import base64
import json
import math
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


class AcquisitionError(Exception):
    def __init__(self, category, retryable=False):
        super().__init__(category)
        self.category = category
        self.retryable = retryable


MAX_TOTAL_SECONDS = 1800


def finite_seconds(value, name, maximum=MAX_TOTAL_SECONDS):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise AcquisitionError('invalid-' + name)
    if not math.isfinite(number) or number < 0 or number > maximum:
        raise AcquisitionError('invalid-' + name)
    return number


def live_group(pgid):
    """Zombies cannot write; never confuse reaped leader with stopped descendants."""
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    if sys.platform.startswith('linux'):
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():
                continue
            try:
                raw = (entry / 'stat').read_text()
                fields = raw[raw.rfind(')') + 2:].split()
                if int(fields[2]) == pgid and fields[0] != 'Z':
                    return True
            except (FileNotFoundError, ProcessLookupError):
                pass
        return False
    result = subprocess.run(['/bin/ps', '-axo', 'pgid=,stat='],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            universal_newlines=True, timeout=1, check=True)
    return any(len(row.split()) == 2 and row.split()[0] == str(pgid)
               and not row.split()[1].startswith('Z')
               for row in result.stdout.splitlines())


class Supervisor:
    def __init__(self, total, elapsed, emit, grace=1):
        self.started = time.monotonic()
        self.elapsed = elapsed
        self.deadline = self.started + total - elapsed
        self.emit = emit
        self.grace = grace
        self.reserve = 2 * grace + 2
        self.cancelled = False
        self.attempt = 0
        self.unresolved_groups = set()

    def report(self, event, **fields):
        self.emit(dict(event=event, attempt=self.attempt,
                       elapsed_seconds=round(time.monotonic() - self.started + self.elapsed, 3),
                       remaining_seconds=round(max(0, self.deadline - time.monotonic()), 3), **fields))

    def cancel(self, _signum, _frame):
        self.cancelled = True

    def stop_group(self, child):
        def send(sig):
            try:
                os.killpg(child.pid, sig)
            except ProcessLookupError:
                pass
        try:
            if live_group(child.pid):
                send(signal.SIGTERM)
                until = min(self.deadline, time.monotonic() + self.grace)
                while live_group(child.pid) and time.monotonic() < until:
                    child.poll()
                    time.sleep(0.02)
                if live_group(child.pid):
                    send(signal.SIGKILL)
            child.wait(timeout=max(0.01, min(self.grace, self.deadline - time.monotonic())))
            until = min(self.deadline, time.monotonic() + self.grace)
            while live_group(child.pid) and time.monotonic() < until:
                time.sleep(0.02)
            if live_group(child.pid):
                raise AcquisitionError('process-cleanup-failed')
            self.unresolved_groups.discard(child.pid)
        except (OSError, subprocess.SubprocessError):
            # Terminate our group even when inspection is unavailable, but never
            # claim verified cleanup or remove files the unknown group may use.
            try:
                send(signal.SIGKILL)
                child.wait(timeout=max(0.01, min(self.grace, self.deadline - time.monotonic())))
            except (OSError, subprocess.SubprocessError):
                pass
            raise AcquisitionError('process-cleanup-failed')

    def run(self, argv, cwd, env, phase, timeout=None, accepted=(0,), cleanup=False):
        if self.cancelled and not cleanup:
            raise AcquisitionError('cancelled')
        start = time.monotonic()
        end = self.deadline - (self.grace if cleanup else self.reserve)
        if timeout is not None:
            end = min(end, start + timeout)
        if end <= start:
            raise AcquisitionError('acquisition-deadline')
        child = subprocess.Popen(argv, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 start_new_session=True)
        self.unresolved_groups.add(child.pid)
        selector = selectors.DefaultSelector()
        selector.register(child.stdout, selectors.EVENT_READ, 'stdout')
        selector.register(child.stderr, selectors.EVENT_READ, 'stderr')
        output = bytearray()
        pending = b''
        last_progress = 0
        failure = None
        try:
            while selector.get_map():
                if self.cancelled and not cleanup:
                    failure = 'cancelled'
                    break
                if time.monotonic() >= end:
                    failure = 'phase-timeout'
                    break
                for key, _ in selector.select(min(0.1, max(0, end - time.monotonic()))):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if key.data == 'stdout':
                        output.extend(chunk)
                        if len(output) > 8192:
                            failure = 'unexpected-command-output'
                            break
                    else:
                        # Only numeric Git progress is emitted. Never echo child stderr,
                        # command lines, HTTP headers, arbitrary errors or trace files.
                        pending = (pending + chunk)[-16384:]
                        lines = re.split(br'[\r\n]', pending)
                        pending = lines.pop()[-4096:]
                        for line in lines:
                            match = re.fullmatch(
                                br'(?:remote: )?(Counting objects|Compressing objects|Receiving objects|Resolving deltas|Updating files):\s+(\d+)% \((\d+)/(\d+)\)(?:.*)', line)
                            if match and (time.monotonic() - last_progress >= 1 or match[2] == b'100'):
                                last_progress = time.monotonic()
                                self.report('git-progress', phase=phase,
                                            activity=match[1].decode('ascii'), percent=int(match[2]),
                                            current=int(match[3]), total=int(match[4]))
                if failure:
                    break
            # Even a successful launcher must not leave descendants behind.
            if failure:
                self.stop_group(child)
            else:
                try:
                    child.wait(timeout=max(0.01, end - time.monotonic()))
                except subprocess.TimeoutExpired:
                    failure = 'phase-timeout'
                self.stop_group(child)
            if self.cancelled and not cleanup:
                failure = 'cancelled'
            if not failure and child.returncode not in accepted:
                failure = 'command-failed'
            self.report('phase-complete', phase=phase, status=failure or 'success',
                        phase_seconds=round(time.monotonic() - start, 3), exit_code=child.returncode)
            if failure:
                raise AcquisitionError(failure, retryable=phase == 'fetch' and
                                       failure in ('phase-timeout', 'command-failed'))
            return bytes(output).decode('utf-8', errors='strict').strip()
        finally:
            try:
                if child.pid in self.unresolved_groups:
                    self.stop_group(child)
            finally:
                selector.close()
                child.stdout.close()
                child.stderr.close()


def acquire(repository, sha, tree, workspace, fetch_timeout=240, total_timeout=420,
            max_attempts=2, elapsed_seconds=0, token=None, git_executable=None, emit=None):
    """git_executable is a library-only fault-injection seam, never a CLI option."""
    supplied_token = os.environ.pop('WORLDATLAS_CHECKOUT_TOKEN', None)
    token = supplied_token if token is None else token
    supplied_token = None
    emit = emit or (lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository or ''):
        raise AcquisitionError('invalid-repository')
    if not all(re.fullmatch(r'[a-f0-9]{40}', value or '') for value in (sha, tree)):
        raise AcquisitionError('invalid-git-identity')
    total_timeout = finite_seconds(total_timeout, 'total-timeout')
    fetch_timeout = finite_seconds(fetch_timeout, 'fetch-timeout', maximum=total_timeout)
    elapsed_seconds = finite_seconds(elapsed_seconds, 'elapsed', maximum=total_timeout)
    if fetch_timeout <= 0 or total_timeout <= 4 or elapsed_seconds >= total_timeout:
        raise AcquisitionError('invalid-deadline')
    if type(max_attempts) is not int or max_attempts not in (1, 2):
        raise AcquisitionError('invalid-attempt-limit')
    workspace = Path(workspace)
    if not workspace.is_absolute() or workspace.is_symlink() or not workspace.is_dir():
        raise AcquisitionError('invalid-workspace')
    if workspace.resolve() != workspace or list(workspace.iterdir()):
        raise AcquisitionError('workspace-not-empty-or-ordinary')
    workspace_identity = (workspace.stat().st_dev, workspace.stat().st_ino)
    executable = git_executable or shutil.which('git')
    if not executable or not os.path.isabs(executable):
        raise AcquisitionError('git-unavailable')
    env = {key: value for key, value in os.environ.items()
           if key in ('PATH', 'LANG', 'LC_ALL', 'TMPDIR', 'TMP', 'TEMP', 'SystemRoot')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT='0', GIT_NO_LAZY_FETCH='1', GIT_LFS_SKIP_SMUDGE='1')
    common = [executable, '-c', 'core.hooksPath=' + os.devnull,
              '-c', 'credential.helper=', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false']
    remote = 'https://github.com/' + repository + '.git'
    supervisor = Supervisor(total_timeout, elapsed_seconds, emit)
    previous = {sig: signal.signal(sig, supervisor.cancel) for sig in (signal.SIGINT, signal.SIGTERM)}
    staging = None
    promoted = False
    try:
        for attempt in range(1, max_attempts + 1):
            supervisor.attempt = attempt
            if supervisor.cancelled:
                raise AcquisitionError('cancelled')
            if supervisor.deadline - time.monotonic() <= supervisor.reserve:
                raise AcquisitionError('acquisition-deadline')
            staging = Path(tempfile.mkdtemp(prefix='.worldatlas-ci-checkout-', dir=str(workspace.parent)))
            if staging.stat().st_dev != workspace_identity[0]:
                raise AcquisitionError('workspace-filesystem-changed')
            supervisor.run(common + ['init', '--template=', '--quiet', str(staging)], staging, env, 'initialize')
            supervisor.run(common + ['remote', 'add', 'origin', remote], staging, env, 'initialize')
            fetch_env = dict(env)
            if token:
                fetch_env.update(GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='http.https://github.com/.extraheader',
                                 GIT_CONFIG_VALUE_0='AUTHORIZATION: basic ' +
                                 base64.b64encode(('x-access-token:' + token).encode()).decode())
            try:
                supervisor.run(common + ['-c', 'protocol.version=2', 'fetch', '--progress', '--no-tags',
                                         '--no-recurse-submodules', '--depth=1', 'origin', sha],
                               staging, fetch_env, 'fetch', timeout=fetch_timeout)
            except AcquisitionError as error:
                fetch_env.clear()
                if not error.retryable or supervisor.cancelled or attempt == max_attempts:
                    raise
                supervisor.run([sys.executable, '-c', 'import shutil,sys;shutil.rmtree(sys.argv[1])', str(staging)],
                               workspace.parent, env, 'cleanup', cleanup=True)
                staging = None
                supervisor.report('acquisition-retry', reason=error.category)
                continue
            finally:
                fetch_env.clear()
            commit = supervisor.run(common + ['rev-parse', '--verify', 'FETCH_HEAD^{commit}'], staging, env, 'verify-commit')
            if commit != sha:
                raise AcquisitionError('git-identity-mismatch')
            actual_tree = supervisor.run(common + ['rev-parse', '--verify', sha + '^{tree}'], staging, env, 'verify-tree')
            if commit != sha or actual_tree != tree:
                raise AcquisitionError('git-identity-mismatch')
            supervisor.run(common + ['checkout', '--detach', '--force', '--progress', sha], staging, env, 'materialize')
            head = supervisor.run(common + ['rev-parse', 'HEAD'], staging, env, 'verify-checkout')
            final_tree = supervisor.run(common + ['rev-parse', 'HEAD^{tree}'], staging, env, 'verify-checkout')
            credentials = supervisor.run(common + ['config', '--local', '--name-only', '--get-regexp',
                                                   r'http\..*extraheader|credential\..*|core\.sshcommand|include.*'],
                                         staging, env, 'credential-audit', accepted=(0, 1))
            if credentials or head != sha or final_tree != tree:
                raise AcquisitionError('checkout-verification-failed')
            if supervisor.cancelled:
                raise AcquisitionError('cancelled')
            if (workspace.is_symlink() or not workspace.is_dir() or
                    (workspace.stat().st_dev, workspace.stat().st_ino) != workspace_identity or list(workspace.iterdir())):
                raise AcquisitionError('workspace-changed')
            if time.monotonic() >= supervisor.deadline - supervisor.reserve:
                raise AcquisitionError('acquisition-deadline')
            # Atomic directory replacement refuses a newly nonempty destination.
            # Both directories are on one filesystem; this is not a full-tree copy.
            os.replace(str(staging), str(workspace))
            staging = None
            if supervisor.cancelled:
                raise AcquisitionError('cancelled')
            promoted = True
            supervisor.report('checkout-complete', sha=sha, tree=tree, attempts=attempt)
            return {'sha': sha, 'tree': tree, 'attempts': attempt}
        raise AcquisitionError('attempts-exhausted')
    finally:
        token = None
        try:
            if staging is not None and supervisor.unresolved_groups:
                supervisor.report('staging-preserved', reason='process-cleanup-unverified', owned_directory=str(staging))
            elif staging is not None:
                supervisor.run([sys.executable, '-c', 'import shutil,sys;shutil.rmtree(sys.argv[1])', str(staging)],
                               workspace.parent, env, 'cleanup', cleanup=True)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
            if not promoted:
                supervisor.report('acquisition-incomplete')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--tree', required=True)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--fetch-timeout-seconds', default='240')
    parser.add_argument('--total-timeout-seconds', default='420')
    parser.add_argument('--max-attempts', type=int, default=2)
    parser.add_argument('--elapsed-seconds', default='0')
    args = parser.parse_args()
    try:
        acquire(args.repository, args.sha, args.tree, args.workspace,
                args.fetch_timeout_seconds, args.total_timeout_seconds, args.max_attempts, args.elapsed_seconds)
    except AcquisitionError as error:
        print(json.dumps({'event': 'acquisition-failed', 'reason': error.category}), flush=True)
        return 130 if error.category == 'cancelled' else 1
    except Exception:
        # OS and subprocess exceptions can contain command arguments or environment.
        print(json.dumps({'event': 'acquisition-failed', 'reason': 'acquisition-error'}), flush=True)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
