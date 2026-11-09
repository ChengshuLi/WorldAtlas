"""Run native commands with the enclosing build's cancellation and file lock."""
from contextlib import contextmanager
from contextvars import ContextVar
import os
import signal
import subprocess
import threading


_current = ContextVar('worldatlas_external_commands', default=None)


class ExternalCommands:
    def __init__(self, run_lock, cancelled):
        self.run_lock = run_lock
        self.cancelled = cancelled
        self.processes = set()
        self.lock = threading.RLock()

    @contextmanager
    def stage(self, log):
        token = _current.set((self, log))
        try:
            yield
        finally:
            _current.reset(token)

    def start(self, command, options):
        with self.lock:
            if self.cancelled.is_set():
                raise InterruptedError('pipeline cancelled')
            self.processes = {p for p in self.processes if p.poll() is None}
            options['pass_fds'] = (*options.get('pass_fds', ()), self.run_lock.fd)
            options['start_new_session'] = True
            process = subprocess.Popen(command, **options)
            self.processes.add(process)
            return process

    def cancel(self):
        self.cancelled.set()
        with self.lock:
            for process in self.processes:
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass


def emit(*values, **options):
    active = _current.get()
    if active is None:
        print(*values, **options)
    else:
        commands, log = active
        options.setdefault('file', log)
        with commands.lock:
            print(*values, **options)


def check_cancelled():
    active = _current.get()
    if active is not None and active[0].cancelled.is_set():
        raise InterruptedError('pipeline cancelled')


def popen(command, **options):
    active = _current.get()
    if active is None:
        return subprocess.Popen(command, **options)
    commands, log = active
    options.setdefault('stdout', log)
    options.setdefault('stderr', log)
    return commands.start(command, options)


def run(command, *, check=False, capture_output=False, **options):
    if _current.get() is None:
        return subprocess.run(command, check=check, capture_output=capture_output, **options)
    if capture_output:
        if 'stdout' in options or 'stderr' in options:
            raise ValueError('capture_output conflicts with stdout or stderr')
        options.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    with popen(command, **options) as process:
        try:
            stdout, stderr = process.communicate()
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise
    result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    if check:
        result.check_returncode()
    return result
