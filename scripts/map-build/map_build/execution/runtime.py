"""Durable pipeline identities, output checkpoints and attempt-local active timing."""
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import threading
import time
import traceback
import uuid


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def write(path, value):
    """Publish a new complete JSON file atomically; interrupted temporaries stay."""
    path = Path(path)
    temporary = path.with_name('.' + path.name + '.pending-' + uuid.uuid4().hex)
    with temporary.open('xb') as stream:
        stream.write(json_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, path)
    sync_directory(path.parent)
    temporary.unlink()
    sync_directory(path.parent)
    return path


def pin(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError('not a file: ' + str(path))
    return {'path': str(path), 'sha256': digest(path)}


def verify_pins(pins):
    for expected in pins:
        if pin(expected['path'])['sha256'] != expected['sha256']:
            raise ValueError('checkpoint/input hash mismatch: ' + expected['path'])


def journal_anchor(path):
    path = Path(path).resolve(strict=True)
    size = path.stat().st_size
    h = hashlib.sha256()
    with path.open('rb') as stream:
        remaining = size
        while remaining:
            block = stream.read(min(1 << 20, remaining))
            if not block:
                raise ValueError('timing journal shortened while sealing prefix')
            h.update(block)
            remaining -= len(block)
    return {'path': str(path), 'bytes': size, 'sha256': h.hexdigest()}


def verify_anchor(anchor, expected_path):
    if (set(anchor) != {'path', 'bytes', 'sha256'} or Path(anchor['path']).resolve() != Path(expected_path).resolve()
            or type(anchor['bytes']) is not int or anchor['bytes'] < 0):
        raise ValueError('invalid timing journal anchor')
    remaining = anchor['bytes']
    h = hashlib.sha256()
    with Path(expected_path).open('rb') as stream:
        while remaining:
            block = stream.read(min(1 << 20, remaining))
            if not block:
                raise ValueError('timing journal lost a checkpointed prefix')
            h.update(block)
            remaining -= len(block)
    if h.hexdigest() != anchor['sha256']:
        raise ValueError('timing journal checkpoint prefix changed')


def _publication_module():
    path = Path(__file__).resolve().parents[2] / 'stages/land/stage2-geodesic-20261104/atomic_move.py'
    spec = importlib.util.spec_from_file_location('pipeline_directory_publication', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inventory(paths):
    """Seal all files and exact publication receipts; reject other symlinks."""
    result = []

    def visit(path):
        if path.is_symlink():
            target, receipt = _publication_module().published_directory(path)
            result.append(pin(receipt))
            visit(target)
        elif path.is_file():
            result.append(pin(path))
        elif path.is_dir():
            for child in sorted(path.iterdir()):
                visit(child)
        else:
            raise ValueError('missing or non-regular checkpoint output: ' + str(path))

    for value in paths:
        visit(Path(value))
    return result


def code_identity(scripts):
    return {str(path.relative_to(scripts)): digest(path)
            for path in sorted(Path(scripts).rglob('*'))
            if path.is_file() and '__pycache__' not in path.parts
            and path.suffix in {'.py', '.cpp', '.c', '.h', '.hpp', '.sh'}}


def elapsed_union(intervals):
    merged = []
    for start, end in sorted(intervals):
        if not (math.isfinite(start) and math.isfinite(end) and end >= start):
            raise ValueError('invalid processing interval')
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return sum(end - start for start, end in merged)


def outside(intervals, excluded):
    """Duration in the first union outside the second union."""
    events = []
    for start, end in intervals:
        events.extend([(start, 1, 0), (end, -1, 0)])
    for start, end in excluded:
        events.extend([(start, 0, 1), (end, 0, -1)])
    active = removed = 0
    previous = None
    total = 0.0
    for point, da, dr in sorted(events):
        if previous is not None and active and not removed:
            total += point - previous
        active += da
        removed += dr
        previous = point
    return total


class RunLock:
    def __init__(self, path):
        self.stream = Path(path).open('a+b')
        try:
            fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.stream.close()
            raise ValueError('another pipeline runner still owns this run') from None

    @property
    def fd(self):
        return self.stream.fileno()

    def close(self):
        if not self.stream.closed:
            # Do not explicitly LOCK_UN: an admitted stage process may still
            # hold this same open-file description after its parent dies.
            self.stream.close()

    def __del__(self):
        self.close()


class Checkpoints:
    def __init__(self, root, attempt):
        self.root, self.attempt = Path(root).resolve(), attempt
        self.root.mkdir(exist_ok=True)
        self.preserved = self.root.parent / 'preserved'
        self.preserved.mkdir(exist_ok=True)
        self.lock = threading.Lock()

    def stage(self, name):
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in name):
            raise ValueError('unsafe checkpoint name')
        path = self.root / name
        path.mkdir(exist_ok=True)
        return path

    def completed(self, name, invocation, outputs):
        path = self.stage(name) / 'complete.json'
        if not path.exists():
            return False
        receipt = json.loads(path.read_bytes())
        verify_anchor(receipt['timing_anchor'], self.root.parent / 'timing-events.jsonl')
        request = lambda value: {k: v for k, v in value.items() if k != 'code'}
        if receipt.get('schema') != 'worldatlas-command-checkpoint-v1' or request(receipt['invocation']) != request(invocation):
            raise ValueError('completed command identity changed: ' + name)
        verify_pins(self.data_pins(receipt))
        if inventory(outputs) != receipt['outputs']:
            raise ValueError('completed stage output changed: ' + name)
        verify_pins([receipt['log']])
        return True

    @staticmethod
    def data_pins(receipt):
        # Earlier checkpoints also included the executable Python file among
        # their inputs. Preserve the receipt and verify its data inputs only.
        code_path = receipt['invocation'].get('code', {}).get('path')
        return [pin for pin in receipt['inputs'] if pin['path'] != code_path]

    def preserve(self, name, paths):
        existing = list(dict.fromkeys(Path(path) for path in paths if Path(path).exists() or Path(path).is_symlink()))
        if not existing:
            return []
        destination = self.preserved / (name + '-' + uuid.uuid4().hex)
        destination.mkdir()
        moved = []
        for index, path in enumerate(existing):
            if not path.resolve().is_relative_to(self.root.parent) or path.resolve() == self.root.parent:
                raise ValueError('partial output outside run cannot be moved')
            target = destination / f'{index}-{path.name}'
            path.rename(target)
            moved.append((path, target))
            sync_directory(path.parent)
        sync_directory(destination)
        sync_directory(destination.parent)
        return moved

    def verify_all(self):
        for path in self.root.glob('*/attempt-*/admitted.json'):
            admission = json.loads(path.read_bytes())
            verify_anchor(admission['timing_anchor'], self.root.parent / 'timing-events.jsonl')
        for path in self.root.glob('*/complete.json'):
            receipt = json.loads(path.read_bytes())
            verify_anchor(receipt['timing_anchor'], self.root.parent / 'timing-events.jsonl')
            verify_pins(self.data_pins(receipt))
            if inventory(receipt['output_roots']) != receipt['outputs']:
                raise ValueError('completed stage output changed: ' + path.parent.name)
            verify_pins([receipt['log']])

    def begin(self, name):
        path = self.stage(name) / ('attempt-' + uuid.uuid4().hex)
        path.mkdir()
        sync_directory(path.parent)
        return path

    def complete(self, name, invocation, outputs, inputs, log, timing_anchor):
        verify_pins(inputs)
        write(self.stage(name) / 'complete.json', {
            'schema': 'worldatlas-command-checkpoint-v1', 'attempt': self.attempt, 'timing_anchor': timing_anchor,
            'invocation': invocation, 'inputs': inputs, 'output_roots': [os.path.abspath(p) for p in outputs],
            'outputs': inventory(outputs), 'log': pin(log)})

    def run_function(self, name, group, function, args, *, timing, inputs, outputs, kwargs=None,
                     resume_marker=None):
        """Call an ordinary Python stage and checkpoint its returned record.

        Input/output identity controls reuse. The function's location is
        provenance, so editing or moving code does not block resume.
        """
        outputs = [Path(path).absolute() for path in outputs]
        run = self.root.parent
        if any(not path.resolve().is_relative_to(run.resolve()) or path.resolve() == run.resolve()
               for path in outputs):
            raise ValueError('stage output outside run or replaces run root')
        result_path = self.stage(name) / 'result.json'
        invocation = {'stage': name, 'inputs': inputs, 'outputs': list(map(str, outputs)),
                      'code': {'module': function.__module__, 'function': function.__qualname__}}
        sealed = [*outputs, result_path]
        if self.completed(name, invocation, sealed):
            return json.loads(result_path.read_bytes())
        if resume_marker is not None and Path(resume_marker).is_file():
            # The producer owns its validated internal checkpoints. Preserve
            # those outputs so it can continue completed shards or tiles.
            self.preserve(name, [result_path])
        else:
            self.preserve(name, sealed)
        attempt = self.begin(name)
        logs = run / 'logs'
        logs.mkdir(exist_ok=True)
        log = logs / (name + '-' + attempt.name + '.log')
        verify_pins(inputs)
        with log.open('x') as stream:
            write(attempt / 'admitted.json', {'invocation': invocation, 'inputs': inputs,
                  'log': str(log), 'timing_anchor': timing.anchor()})
            try:
                with timing.measure(group, name):
                    result = function(*args, **(kwargs or {}))
                write(result_path, result)
                stream.write(json_bytes(result).decode())
            except BaseException:
                traceback.print_exc(file=stream)
                raise
        self.complete(name, invocation, sealed, inputs, log, timing.anchor())
        return json.loads(result_path.read_bytes())


class Timing:
    """Attempt-local monotonic intervals. No subtraction crosses a restart gap."""
    def __init__(self, path, *, resume=False, attempt=None, heartbeat_seconds=0):
        self.path = Path(path)
        self.attempt = attempt or uuid.uuid4().hex
        self.lock = threading.RLock()
        self.records = []
        self.active = {}
        self.open = set()
        self.completed_groups = set()
        self.stopped = threading.Event()
        self.thread = None
        if resume:
            raw = self.path.read_bytes()
            lines = raw.splitlines(keepends=True)
            valid = 0
            for index, line in enumerate(lines):
                try:
                    if not line.endswith(b'\n'):
                        raise ValueError('torn journal tail')
                    record = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    if index != len(lines) - 1:
                        raise ValueError('invalid timing journal before final line') from None
                    backup = self.path.with_name(self.path.name + '.torn-' + uuid.uuid4().hex)
                    with backup.open('xb') as stream:
                        stream.write(raw)
                        stream.flush()
                        os.fsync(stream.fileno())
                    sync_directory(backup.parent)
                    with self.path.open('r+b') as stream:
                        stream.truncate(valid)
                        stream.flush()
                        os.fsync(stream.fileno())
                    break
                self.records.append(record)
                if record['event'] == 'group-complete':
                    self.completed_groups.add(record['group'])
                valid += len(line)
        else:
            with self.path.open('x') as stream:
                stream.flush()
                os.fsync(stream.fileno())
            sync_directory(self.path.parent)
        self.event({'event': 'attempt', 'id': self.attempt})
        if heartbeat_seconds:
            self.thread = threading.Thread(target=self._heartbeat, args=(heartbeat_seconds,), daemon=True)
            self.thread.start()

    def event(self, value):
        self.events([value])

    def events(self, values):
        values = [{'attempt': self.attempt, **value} for value in values]
        if not values:
            return
        with self.lock:
            with self.path.open('a') as stream:
                for value in values:
                    stream.write(json.dumps(value, sort_keys=True, allow_nan=False) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            self.records.extend(values)

    def _heartbeat(self, seconds):
        while not self.stopped.wait(seconds):
            with self.lock:
                now = time.monotonic()
                self.events([{'event': 'heartbeat', 'token': token, 'id': record['id'],
                              'group': record['group'], 'monotonic_seconds': now}
                             for token, record in self.active.items()])

    def close(self):
        self.stopped.set()
        if self.thread is not None:
            self.thread.join()
            self.thread = None

    @contextmanager
    def measure(self, group, name, *, kind='processing'):
        started = time.monotonic()
        token = uuid.uuid4().hex
        record = {'event': 'start', 'token': token, 'id': f'{group}/{name}', 'group': group,
                  'kind': kind, 'monotonic_seconds': started}
        with self.lock:
            self.event(record)
            self.active[token] = record
            self.open.add(token)
        try:
            yield record
        except BaseException:
            self._finish(token, record, started, 'failed')
            raise
        else:
            self._finish(token, record, started, 'complete')

    def _finish(self, token, record, started, event):
        with self.lock:
            ended = time.monotonic()
            record['end_monotonic_seconds'] = ended
            self.event({'event': event, 'token': token, 'id': record['id'], 'group': record['group'],
                        'start_monotonic_seconds': started, 'monotonic_seconds': ended})
            self.active.pop(token, None)
            self.open.discard(token)

    def anchor(self):
        with self.lock:
            return journal_anchor(self.path)

    def mark_complete(self, group, *, physical_report=None):
        # Publish the cumulative stage result with completion, rather than
        # making a reader mistake the last resumed interval for the full total.
        with self.lock:
            summary = self.summary(physical_report)[group]
            summary.update(outputs_complete=True, complete=summary['timing_complete'])
            self.event({'event': 'group-complete', 'id': group, 'group': group,
                        'timing_summary': summary})
            self.completed_groups.add(group)

    def intervals(self, group, *, kind=None):
        intervals, missing, _ = self.interval_details(group, kind=kind)
        return intervals, missing

    def interval_details(self, group, *, kind=None):
        """Keep measurable interrupted prefixes and identify every unknown tail.

        A heartbeat is a durable lower-bound endpoint, never a guessed stop
        time. Nested interval details must not be summed; stage totals use the
        attempt-local unions returned alongside them.
        """
        starts, ends, beats = {}, {}, {}
        for record in self.records:
            token = (record.get('attempt'), record.get('token'))
            if record.get('group') != group or not token[1]:
                continue
            if record['event'] == 'start':
                starts[token] = record
            elif record['event'] in ('complete', 'failed'):
                ends[token] = record['monotonic_seconds']
            elif record['event'] == 'heartbeat':
                beats[token] = max(beats.get(token, float('-inf')), record['monotonic_seconds'])
        by_attempt = {}
        incomplete = [{'attempt': record.get('attempt'), 'id': record['id']}
                      for record in self.records if record['event'] == 'unmeasured-initialization'
                      and record.get('group') == group]
        details = [{**record, 'start_monotonic_seconds': None,
                    'last_recorded_monotonic_seconds': None, 'last_recorded_event': None,
                    'recorded_elapsed_seconds': None, 'unrecorded_tail_seconds': None,
                    'reason': 'initialization has no durable start/end interval'}
                   for record in incomplete]
        for token, start in starts.items():
            if kind is not None and start.get('kind', 'processing') != kind:
                continue
            a = start['monotonic_seconds']
            b = ends.get(token, beats.get(token, a))
            if token not in ends:
                incomplete.append({'attempt': token[0], 'id': start['id']})
                details.append({'attempt': token[0], 'id': start['id'],
                    'start_monotonic_seconds': a, 'last_recorded_monotonic_seconds': b,
                    'last_recorded_event': 'heartbeat' if token in beats else 'start',
                    'recorded_elapsed_seconds': b - a, 'unrecorded_tail_seconds': None,
                    'reason': 'no durable completion or failure endpoint'})
            if b < a:
                raise ValueError('non-monotonic processing interval')
            by_attempt.setdefault(token[0], []).append((a, b))
        return by_attempt, incomplete, details

    def summary(self, physical_report):
        groups = {}
        for group in ('setup', 'physical', 'mainland', 'water', 'verification'):
            intervals, missing, interrupted = self.interval_details(group)
            measured = sum(elapsed_union(items) for items in intervals.values())
            complete = not missing
            error = None
            reused = group == 'physical' and physical_report and physical_report.get('status') == 'reused'
            if reused:
                downloads = 0.0
            elif group == 'physical':
                report = physical_report or {}
                commands, _ = self.intervals(group, kind='command')
                overhead = sum(outside(items, commands.get(attempt, []))
                               for attempt, items in intervals.items())
                child = report.get('recorded_processing_elapsed_seconds', report.get('processing_elapsed_seconds'))
                if type(child) not in (int, float) or not math.isfinite(child) or child < 0:
                    child = sum(record['seconds'] for record in self.records
                                if record['event'] == 'physical-invocation-processing')
                    complete = False
                    error = 'physical producer has no valid measured processing total'
                command_overhead = sum(record['seconds'] for record in self.records
                                       if record['event'] == 'physical-command-overhead')
                measured = overhead + command_overhead + child
                complete = complete and report.get('timing_complete', True) and report.get('status') == 'candidate-only'
                downloads = report.get('source_download_elapsed_seconds')
                if type(downloads) not in (int, float) or not math.isfinite(downloads) or downloads < 0:
                    complete = False
                    error = 'missing or invalid physical acquisition timing'
            outputs_complete = group in self.completed_groups
            groups[group] = {'processing_elapsed_seconds': measured if complete else None,
                'recorded_processing_elapsed_seconds': measured,
                'recorded_processing_is_lower_bound': not complete,
                'complete': outputs_complete and complete, 'outputs_complete': outputs_complete,
                'timing_complete': complete, 'unmeasured_interrupted_attempts': missing,
                'interrupted_interval_details': interrupted,
                'unrecorded_interruption_tail_seconds': None if not complete else 0.0,
                'semantics': 'sum of attempt-local active interval unions; no restart gap is counted'}
            if group == 'physical':
                groups[group].update({'source_download_elapsed_seconds': downloads,
                    'producer_processing_elapsed_seconds': (physical_report.get('processing_elapsed_seconds')
                                                            if physical_report and not reused else None),
                    'timing_error': error})
                if reused:
                    groups[group]['reused_from'] = physical_report['source_run']
        return groups
