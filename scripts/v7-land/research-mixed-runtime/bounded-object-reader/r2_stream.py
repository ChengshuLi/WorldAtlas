"""Read-only bounded R2 stream adapter for research, not a source gate.

The caller authenticates allowed object keys and validates exact sizes/hashes.
Python, CLI, credentials, and the caller-provided environment are trust inputs.
"""
from contextlib import contextmanager
from pathlib import Path
import os
import re
import selectors
import signal
import subprocess
import time


class R2StreamError(RuntimeError):
    pass


def _read_once(raw, count, timeout):
    with selectors.DefaultSelector() as selector:
        selector.register(raw.fileno(), selectors.EVENT_READ)
        ready = selector.select(timeout)
    if not ready:
        raise R2StreamError('object read timed out')
    return os.read(raw.fileno(), count)


def _kill_group(process):
    # A fresh process session is created for each reader, so its process group
    # contains only this launched command and descendants that did not detach.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError:
        raise R2StreamError('object reader group cleanup failed') from None
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        raise R2StreamError('object reader could not be reaped') from None



class BoundedReader:
    def __init__(self, raw, limit, deadline, idle_timeout):
        self._raw = raw
        self._limit = limit
        self._deadline = deadline
        self._idle_timeout = idle_timeout
        self.eof = False

    def read(self, count):
        if type(count) is not int or not 1 <= count <= self._limit:
            raise R2StreamError('invalid bounded read size')
        left = self._deadline - time.monotonic()
        if left <= 0:
            raise R2StreamError('object deadline exceeded')
        value = _read_once(self._raw, count, min(left, self._idle_timeout))
        if not isinstance(value, bytes) or len(value) > count:
            raise R2StreamError('invalid stream response')
        if not value:
            self.eof = True
        return value


class R2Reader:
    def __init__(self, wrangler, config, bucket, allowed_keys, env, *,
                 read_limit=1 << 20, idle_timeout=30, object_timeout=900,
                 launcher=subprocess.Popen):
        self.wrangler = Path(wrangler).resolve(strict=True)
        self.config = Path(config).resolve(strict=True)
        if not self.wrangler.is_file() or not self.config.is_file():
            raise R2StreamError('CLI and config must be regular files')
        if not isinstance(bucket, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,61}[a-z0-9]', bucket):
            raise R2StreamError('invalid bucket')
        if (not isinstance(allowed_keys, (set, frozenset)) or not allowed_keys
                or any(not self._key_valid(k) for k in allowed_keys)):
            raise R2StreamError('invalid allowed object keys')
        if (not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                                 for k, v in env.items())):
            raise R2StreamError('invalid subprocess environment')
        if type(read_limit) is not int or not 1 <= read_limit <= (1 << 20):
            raise R2StreamError('invalid read limit')
        if any(type(n) not in (int, float) or not 0 < n <= 3600 for n in (idle_timeout, object_timeout)):
            raise R2StreamError('invalid process timeout')
        self.bucket = bucket
        self.allowed_keys = frozenset(allowed_keys)
        self.env = dict(env)
        self.read_limit = read_limit
        self.idle_timeout = idle_timeout
        self.object_timeout = object_timeout
        self.launcher = launcher

    @staticmethod
    def _key_valid(key):
        return (isinstance(key, str) and bool(key) and not key.startswith('/')
                and '\x00' not in key and '\n' not in key and '\r' not in key
                and all(part not in ('', '.', '..') for part in key.split('/')))

    @contextmanager
    def open_part(self, key):
        if key not in self.allowed_keys or not self._key_valid(key):
            raise R2StreamError('object key not authorized by manifest')
        cmd = [str(self.wrangler), 'r2', 'object', 'get',
               self.bucket + '/' + key, '--pipe', '--remote', '--config', str(self.config)]
        try:
            process = self.launcher(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    env=dict(self.env), shell=False, start_new_session=True)
        except OSError:
            raise R2StreamError('object reader could not start') from None
        if process.stdout is None:
            _kill_group(process)
            raise R2StreamError('object stream unavailable')
        deadline = time.monotonic() + self.object_timeout
        reader = BoundedReader(process.stdout, self.read_limit, deadline, self.idle_timeout)
        try:
            yield reader
            if not reader.eof:
                raise R2StreamError('object stream not consumed to EOF')
            process.stdout.close()
            left = deadline - time.monotonic()
            if left <= 0:
                raise R2StreamError('object deadline exceeded')
            try:
                rc = process.wait(timeout=min(left, self.idle_timeout))
            except subprocess.TimeoutExpired:
                raise R2StreamError('object reader did not exit') from None
            if rc != 0:
                raise R2StreamError('object reader failed')
        except BaseException:
            process.stdout.close()
            _kill_group(process)
            raise
        else:
            # Kill same-session descendants even if they closed stdout.
            _kill_group(process)
