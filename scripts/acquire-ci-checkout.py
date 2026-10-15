#!/usr/bin/env python3
"""Acquire one exact CI Git tree; no candidate code or persistent authentication."""
import argparse
import base64
import hashlib
import json
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
    def __init__(self, category):
        super().__init__(category)
        self.category = category


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
    def __init__(self, emit, grace=1):
        self.started = time.monotonic()
        self.emit = emit
        self.grace = grace
        self.cancelled = False
        self.unresolved_groups = set()

    def report(self, event, **fields):
        self.emit(dict(event=event,
                       elapsed_seconds=round(time.monotonic() - self.started, 3), **fields))

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
                until = time.monotonic() + self.grace
                while live_group(child.pid) and time.monotonic() < until:
                    child.poll()
                    time.sleep(0.02)
                if live_group(child.pid):
                    send(signal.SIGKILL)
            child.wait(timeout=self.grace)
            until = time.monotonic() + self.grace
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
                child.wait(timeout=self.grace)
            except (OSError, subprocess.SubprocessError):
                pass
            raise AcquisitionError('process-cleanup-failed')

    def run(self, argv, cwd, env, phase, accepted=(0,), cleanup=False, output_limit=8192, strip_output=True):
        if self.cancelled and not cleanup:
            raise AcquisitionError('cancelled')
        start = time.monotonic()
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
                for key, _ in selector.select(0.1):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if key.data == 'stdout':
                        output.extend(chunk)
                        if len(output) > output_limit:
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
                # A child may close both pipes before exiting. Keep cancellation
                # responsive here too; the runner owns the overall job timeout.
                while child.poll() is None:
                    if self.cancelled and not cleanup:
                        failure = 'cancelled'
                        break
                    time.sleep(0.1)
                self.stop_group(child)
            if self.cancelled and not cleanup:
                failure = 'cancelled'
            if not failure and child.returncode not in accepted:
                failure = 'command-failed'
            self.report('phase-complete', phase=phase, status=failure or 'success',
                        phase_seconds=round(time.monotonic() - start, 3), exit_code=child.returncode)
            if failure:
                raise AcquisitionError(failure)
            text = bytes(output).decode('utf-8', errors='strict')
            return text.strip() if strip_output else text
        finally:
            try:
                if child.pid in self.unresolved_groups:
                    self.stop_group(child)
            finally:
                selector.close()
                child.stdout.close()
                child.stderr.close()


def package_namespace_patterns(definition, prefix, extra=()):
    # Reuse package-inputs.mjs's packagePathRequired role/path semantics.
    # This retention boundary grants no package role; the real package reader
    # still validates the complete definition and every required materialized input.
    inputs = definition.get('inputs') if isinstance(definition, dict) else None
    verification = definition.get('verification_paths') if isinstance(definition, dict) else None
    if (not isinstance(definition, dict) or definition.get('version') != 1
            or not isinstance(inputs, list) or not inputs or not isinstance(verification, list)):
        raise AcquisitionError('invalid-package-inputs')
    paths = inputs + verification + list(extra)
    for name in paths:
        if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_./-]+', name)
                or name.startswith('/') or any(part in ('', '.', '..') for part in (name[:-1] if name.endswith('/') else name).split('/'))):
            raise AcquisitionError('invalid-package-inputs')
    if any(name.endswith('/') and prefix.startswith(name) for name in paths):
        return []
    retained = [name for name in paths if name.startswith(prefix)]
    directories = set()
    for name in retained:
        parent = name.rstrip('/') if name.endswith('/') else name.rsplit('/', 1)[0]
        while parent != prefix.rstrip('/'):
            directories.add(parent + '/')
            parent = parent.rsplit('/', 1)[0]
    patterns = ['!/' + prefix + '*']
    for directory in sorted(directories, key=lambda name: (name.count('/'), name)):
        patterns.append('/' + directory)
        if not any(name.endswith('/') and directory.startswith(name) for name in retained):
            patterns.append('!/' + directory + '*')
    patterns.extend('/' + name for name in retained if not name.endswith('/'))
    return patterns


COORDINATION_SOURCE_SUFFIXES = ('.mjs', '.js', '.cjs', '.py', '.sh', '.ts', '.tsx', '.jsx',
                                '.html', '.css', '.sql', '.yml', '.yaml', '.c', '.h', '.cpp',
                                '.hpp', '.wasm', '.bat', '.cmd', '.ps1')


def coordination_execution_paths(raw):
    retained = []
    for row in raw.split('\0'):
        if not row:
            continue
        match = re.fullmatch(r'([0-7]{6}) (blob|commit) ([a-f0-9]{40})\t(.+)', row)
        if not match:
            raise AcquisitionError('invalid-coordination-tree')
        mode, kind, _oid, name = match.groups()
        if (mode == '100755' or name.lower().endswith(COORDINATION_SOURCE_SUFFIXES)
                or name.rsplit('/', 1)[-1] == 'package.json'):
            if kind != 'blob' or mode not in ('100644', '100755'):
                raise AcquisitionError('nonordinary-coordination-execution-input')
            retained.append(name)
    return retained


def acquire(repository, sha, tree, workspace, token=None, git_executable=None, emit=None,
            regression=False, selected_data=False, expectations_path=None):
    """git_executable is a library-only fault-injection seam, never a CLI option."""
    supplied_token = os.environ.pop('WORLDATLAS_CHECKOUT_TOKEN', None)
    token = supplied_token if token is None else token
    supplied_token = None
    emit = emit or (lambda row: print(json.dumps(row, sort_keys=True), flush=True))
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository or ''):
        raise AcquisitionError('invalid-repository')
    if not all(re.fullmatch(r'[a-f0-9]{40}', value or '') for value in (sha, tree)):
        raise AcquisitionError('invalid-git-identity')
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
    supervisor = Supervisor(emit)
    previous = {sig: signal.signal(sig, supervisor.cancel) for sig in (signal.SIGINT, signal.SIGTERM)}
    staging = None
    promoted = False
    try:
        if supervisor.cancelled:
            raise AcquisitionError('cancelled')
        staging = Path(tempfile.mkdtemp(prefix='.worldatlas-ci-checkout-', dir=str(workspace.parent)))
        if staging.stat().st_dev != workspace_identity[0]:
            raise AcquisitionError('workspace-filesystem-changed')
        supervisor.run(common + ['init', '--template=', '--quiet', str(staging)], staging, env, 'initialize')
        supervisor.run(common + ['remote', 'add', 'origin', remote], staging, env, 'initialize')
        if regression:
            # Source-only work is checked by the existing evidence/geography
            # readers, not by current software regressions or package inputs.
            # Required selected reads and full-build declared-input preflight
            # fail closed if future dependencies enter these namespaces.
            supervisor.run(common + ['sparse-checkout', 'init', '--no-cone'], staging, env, 'initialize')
            (staging / '.git/info/sparse-checkout').write_text(
                '/*\n!/data/regional-review/\n!/research/campaigns/\n', encoding='utf-8')
        fetch_env = dict(env)
        if token:
            fetch_env.update(GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='http.https://github.com/.extraheader',
                             GIT_CONFIG_VALUE_0='AUTHORIZATION: basic ' +
                             base64.b64encode(('x-access-token:' + token).encode()).decode())
        materialize_env = None
        try:
            supervisor.run(common + ['-c', 'protocol.version=2', 'fetch', '--progress', '--no-tags',
                                     '--no-recurse-submodules', '--depth=1',
                                     *(['--filter=blob:none'] if regression else []), 'origin', sha],
                           staging, fetch_env, 'fetch')
            commit = supervisor.run(common + ['rev-parse', '--verify', 'FETCH_HEAD^{commit}'], staging, env, 'verify-commit')
            if commit != sha:
                raise AcquisitionError('git-identity-mismatch')
            actual_tree = supervisor.run(common + ['rev-parse', '--verify', sha + '^{tree}'], staging, env, 'verify-tree')
            if commit != sha or actual_tree != tree:
                raise AcquisitionError('git-identity-mismatch')
            # Only the supervised declaration read and materialization may fetch
            # promised blobs, with transient auth and no candidate code or filters.
            materialize_env = dict(fetch_env, GIT_NO_LAZY_FETCH='0') if regression else env
            if regression and selected_data:
                name = '.github/package-inputs.json'
                row = supervisor.run(common + ['ls-tree', sha, '--', name], staging, env, 'package-inputs')
                match = re.fullmatch(r'100644 blob ([a-f0-9]{40})\t' + re.escape(name), row)
                if not match:
                    raise AcquisitionError('invalid-package-inputs')
                # Existing selected-package metadata admits ordinary bodies up
                # to 8 MiB. Never print the body or execute candidate validation.
                raw = supervisor.run(common + ['cat-file', 'blob', match[1]], staging, materialize_env,
                                     'package-inputs', output_limit=8 * 1024 * 1024, strip_output=False)
                body = raw.encode('utf-8')
                if hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest() != match[1]:
                    raise AcquisitionError('git-identity-mismatch')
                definition = json.loads(raw)
                # The classifier has already reviewed this exact file. It can be
                # outside package roles because smoke reads it from the checkout.
                if (not isinstance(expectations_path, str) or not re.fullmatch(
                        r'[A-Za-z0-9_./-]+/selected-delivery-expectations\.json', expectations_path)
                        or expectations_path.startswith('/')
                        or any(part in ('', '.', '..') for part in expectations_path.split('/'))):
                    raise AcquisitionError('invalid-selected-expectations')
                expectation = supervisor.run(common + ['ls-tree', sha, '--', expectations_path],
                                             staging, env, 'selected-expectations')
                if not re.fullmatch(r'100644 blob [a-f0-9]{40}\t' + re.escape(expectations_path), expectation):
                    raise AcquisitionError('invalid-selected-expectations')
                execution_tree = supervisor.run(common + ['ls-tree', '-rz', sha, '--', 'coordination/engineering/'],
                                               staging, env, 'coordination-tree', output_limit=16 * 1024 * 1024,
                                               strip_output=False)
                retained = coordination_execution_paths(execution_tree) + [expectations_path]
                patterns = package_namespace_patterns(definition, 'research/geography/', [expectations_path])
                patterns += package_namespace_patterns(definition, 'coordination/engineering/', retained)
                with (staging / '.git/info/sparse-checkout').open('a', encoding='utf-8') as output:
                    output.write('\n'.join(patterns) + '\n')
            supervisor.run(common + ['checkout', '--detach', '--force', '--progress', sha],
                           staging, materialize_env, 'materialize')
        finally:
            fetch_env.clear()
            if regression and materialize_env is not None:
                materialize_env.clear()
        if regression:
            # No later consumer may silently hydrate the excluded namespaces.
            # Historical regression commits keep their existing explicit full fetch.
            supervisor.run(common + ['config', '--local', 'remote.origin.promisor', 'false'], staging, env, 'verify-checkout')
            supervisor.run(common + ['config', '--local', '--unset-all', 'remote.origin.partialclonefilter'],
                           staging, env, 'verify-checkout', accepted=(0, 5))
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
        # Atomic directory replacement refuses a newly nonempty destination.
        # Both directories are on one filesystem; this is not a full-tree copy.
        os.replace(str(staging), str(workspace))
        staging = None
        if supervisor.cancelled:
            raise AcquisitionError('cancelled')
        promoted = True
        supervisor.report('checkout-complete', sha=sha, tree=tree, source_only_omitted=regression)
        return {'sha': sha, 'tree': tree}
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
    args = parser.parse_args()
    try:
        acquire(args.repository, args.sha, args.tree, args.workspace,
                regression=os.environ.get('INTEGRATION_PROFILE') == 'full' and
                os.environ.get('INTEGRATION_TEST_SELECTION') in ('complete', 'selected-data'),
                selected_data=os.environ.get('INTEGRATION_TEST_SELECTION') == 'selected-data',
                expectations_path=os.environ.get('SELECTED_EXPECTATIONS_PATH'))
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
