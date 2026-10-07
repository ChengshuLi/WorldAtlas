#!/usr/bin/env python3
"""Safely replay the retained MKD comparison through authenticated code bytes.

All inputs and project code come from the declared immutable Git baseline.
Writes are exclusive and confined to this issue's owned evidence directory.
"""
from __future__ import annotations
import contextlib
import hashlib
import importlib.abc
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import uuid
from types import ModuleType

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED_REL = pathlib.PurePosixPath('data/regional-review/northern-macedonia-method-995-guard-erratum')
OWNED = ROOT.joinpath(*OWNED_REL.parts)
OLD_REL = 'data/regional-review/northern-macedonia-method-995-erratum'
BASELINE = 'b6cfaada43a1e0472cd833d16733d1fd6065eaec'
OLD_PACKET_MERGE = '31ad959c0c91d4b0495a0de2c79b05f5d6861e11'
EXPECTED_DESCRIPTOR_SHA256 = '8b4ba60e0da008d63b5bd56a41ae893d4952358615c2a9b538b919b37a48a430'
EXPECTED_RUNNER_PIN_SHA256 = '8de9a4734588cf188cd6b682fbe073a958324ac149f4baf145ba78ac9926ed2e'
EXPECTED_RUNNER_SHA256 = '4985b1b1082e7720eb29c853f45b744e648478652fa8a6ac65b8327a7bc053a9'
EXPECTED_HELPERS = {
    'data/regional-review/followup-northern-macedonia-422-roster-20261005/reproduce.py': '9055d094ab0392ecbfc23cbe47876a8c9ad77bccfc2ea30b6860ae82f0d2dfb6',
    'scripts/evidence/geometry.py': '944541968fcdf065b9c4b6105be227c3e0e14b6a20916f4fa21f851338c7a305',
    'scripts/ellipsoidal_area.py': '4ead1c5de909b257a7b300984e4d3dc56124e9a6c0d27240662024e44fd8ed12',
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(ROOT), *args], stderr=subprocess.PIPE)


def baseline_blob(path: str) -> bytes:
    rows = git('ls-tree', '-z', BASELINE, '--', path).decode().split('\0')
    matches = [row for row in rows if row]
    if len(matches) != 1:
        raise ValueError(f'baseline path missing or ambiguous: {path}')
    meta, actual = matches[0].split('\t', 1)
    if meta.split()[0] != '100644' or actual != path:
        raise ValueError(f'baseline path is not an ordinary file: {path}')
    return git('cat-file', 'blob', meta.split()[2])


def _descriptor(descriptor_override: bytes | None = None, input_overrides: dict[str, bytes] | None = None) -> tuple[dict, dict[str, bytes]]:
    old = ROOT / OLD_REL
    descriptor_path = old / 'baseline-inputs.json'
    descriptor_raw = descriptor_override if descriptor_override is not None else descriptor_path.read_bytes()
    if sha(descriptor_raw) != EXPECTED_DESCRIPTOR_SHA256:
        raise ValueError('prior baseline descriptor changed')
    index = json.loads(descriptor_raw)
    canonical = (json.dumps({k: v for k, v in index.items() if k != 'sha256'}, indent=2) + '\n').encode()
    if sha(canonical) != index.get('sha256') or index.get('baseline_commit') != BASELINE or len(index.get('files', [])) != 30:
        raise ValueError('prior baseline descriptor self-check failed')
    blobs = {}
    for row in index['files']:
        path = row['path']
        raw = (input_overrides or {}).get(path, baseline_blob(path))
        if len(raw) != row['bytes'] or sha(raw) != row['sha256'] or len(raw) > 32 * 1024 * 1024:
            raise ValueError(f'baseline whole-file pin failed: {path}')
        blobs[path] = raw
    if sum(map(len, blobs.values())) != 20_430_279:
        raise ValueError('baseline aggregate byte count changed')
    return index, blobs


def _verify_checkout_code(blobs: dict[str, bytes]) -> None:
    expected = dict(EXPECTED_HELPERS)
    expected[OLD_REL + '/reproduce-retained-phase.py'] = EXPECTED_RUNNER_SHA256
    for path, digest in expected.items():
        if path not in blobs:
            # The pre-existing runner and its pin were added at the prior merge,
            # so authenticate those separately from that exact merge.
            if path.startswith(OLD_REL + '/'):
                raw = git('show', f'{OLD_PACKET_MERGE}:{path}')
            else:
                raise ValueError(f'code path absent from immutable input descriptor: {path}')
        else:
            raw = blobs[path]
        if sha(raw) != digest:
            raise ValueError(f'expected project code pin differs: {path}')
        if not path.startswith(OLD_REL + '/'):
            materialized = ROOT / path
            if sha(materialized.read_bytes()) != digest:
                raise ValueError(f'working-tree project code drift before execution: {path}')


def _open_dir(parent_fd: int, name: str, create: bool = False) -> int:
    flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    try:
        return os.open(name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        if not create:
            raise
        os.mkdir(name, 0o755, dir_fd=parent_fd)
        return os.open(name, flags, dir_fd=parent_fd)


def _root_fd() -> int:
    # ROOT is canonicalized from this script's real path. Open each owned path
    # component with O_NOFOLLOW so a symlink cannot redirect publication.
    root_fd = os.open(str(ROOT), os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    return root_fd


def _open_owned_dir(create: bool = False) -> int:
    fd = _root_fd()
    try:
        for part in OWNED_REL.parts:
            child = _open_dir(fd, part, create=create)
            os.close(fd)
            fd = child
        return fd
    except Exception:
        os.close(fd)
        raise


def _parts_for_output(output: str) -> tuple[str, ...]:
    candidate = pathlib.PurePosixPath(output)
    if candidate.is_absolute() or not candidate.parts or any(p in ('', '.', '..') for p in candidate.parts):
        raise ValueError('output must be a relative owned path without dot/traversal components')
    if candidate.parts[:len(OWNED_REL.parts)] != OWNED_REL.parts or len(candidate.parts) <= len(OWNED_REL.parts):
        raise ValueError('output must remain below this issue owned prefix')
    return candidate.parts[len(OWNED_REL.parts):]


def _prepare_destination(output: str) -> tuple[int, str]:
    parts = _parts_for_output(output)
    fd = _open_owned_dir(create=True)
    try:
        for part in parts[:-1]:
            child = _open_dir(fd, part, create=True)
            os.close(fd)
            fd = child
        return fd, parts[-1]
    except Exception:
        os.close(fd)
        raise


def _publish(output: str, raw: bytes) -> None:
    parent_fd, name = _prepare_destination(output)
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
        file_fd = os.open(name, flags, 0o644, dir_fd=parent_fd)
        with os.fdopen(file_fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(parent_fd)


class _VerifiedLoader(importlib.abc.Loader):
    def __init__(self, fullname: str, path: str, raw: bytes, expected: str):
        self.fullname, self.path, self.raw, self.expected = fullname, path, raw, expected

    def create_module(self, spec):
        return None

    def exec_module(self, module: ModuleType) -> None:
        if sha(self.raw) != self.expected:
            raise ValueError(f'actual import-boundary code rejected: {self.path}')
        module.__file__ = self.path
        module.__loader__ = self
        exec(compile(self.raw, self.path, 'exec', dont_inherit=True), module.__dict__)
        try:
            recorded_path = pathlib.Path(self.path).relative_to(ROOT).as_posix()
        except ValueError:
            raise ValueError('executed project code is outside the repository root')
        _EXECUTED[self.fullname] = {'path': recorded_path, 'sha256': sha(self.raw), 'bytes': len(self.raw), 'authority': BASELINE}


class _PinnedFinder(importlib.abc.MetaPathFinder):
    def __init__(self, blobs: dict[str, bytes], overrides: dict[str, bytes] | None = None):
        self.blobs, self.overrides = blobs, overrides or {}

    def find_spec(self, fullname, path=None, target=None):
        mapping = {'evidence.geometry': 'scripts/evidence/geometry.py', 'ellipsoidal_area': 'scripts/ellipsoidal_area.py'}
        rel = mapping.get(fullname)
        if rel is None:
            return None
        raw = self.overrides.get(rel, self.blobs[rel])
        loader = _VerifiedLoader(fullname, str(ROOT / rel), raw, EXPECTED_HELPERS[rel])
        return importlib.util.spec_from_loader(fullname, loader, origin=str(ROOT / rel))


_EXECUTED: dict[str, dict] = {}


def _verify_runner_pin(runner_raw: bytes, runner_pin_raw: bytes) -> None:
    if sha(runner_pin_raw) != EXPECTED_RUNNER_PIN_SHA256 or json.loads(runner_pin_raw)['sha256'] != EXPECTED_RUNNER_SHA256:
        raise ValueError('immutable previous runner pin file failed')
    if sha(runner_raw) != EXPECTED_RUNNER_SHA256:
        raise ValueError('immutable previous runner code pin failed')


def _verify_self_pin(runner_raw: bytes, pin_raw: bytes) -> None:
    try:
        expected = json.loads(pin_raw)['sha256']
    except Exception as exc:
        raise ValueError('current runner pin is malformed') from exc
    if len(pin_raw) > 4096 or sha(runner_raw) != expected:
        raise ValueError('current runner complete-file pin failed')


def _run_legacy(output_buffer: str, blobs: dict[str, bytes], overrides: dict[str, bytes] | None = None,
                runner_override: bytes | None = None, runner_pin_override: bytes | None = None) -> tuple[bytes, dict[str, dict]]:
    old_runner_path = OLD_REL + '/reproduce-retained-phase.py'
    old_runner_raw = runner_override if runner_override is not None else git('show', f'{OLD_PACKET_MERGE}:{old_runner_path}')
    runner_pin_raw = runner_pin_override if runner_pin_override is not None else git('show', f'{OLD_PACKET_MERGE}:{OLD_REL}/runner-pin.json')
    _verify_runner_pin(old_runner_raw, runner_pin_raw)
    if sha((ROOT / old_runner_path).read_bytes()) != EXPECTED_RUNNER_SHA256:
        raise ValueError('working-tree previous runner drift')
    module = ModuleType('_authenticated_prior_phase')
    module.__file__ = str(ROOT / old_runner_path)
    _EXECUTED['_authenticated_prior_phase'] = {'path': old_runner_path, 'sha256': sha(old_runner_raw), 'bytes': len(old_runner_raw), 'authority': OLD_PACKET_MERGE}
    exec(compile(old_runner_raw, module.__file__, 'exec', dont_inherit=True), module.__dict__)
    # Point only its generated report destination at this issue's owned packet.
    module.OWNED = OWNED
    module.DESCRIPTORS = ROOT / OLD_REL / 'baseline-inputs.json'
    module.RUNNER_PIN = ROOT / OLD_REL / 'runner-pin.json'
    scripts_path = str(ROOT / 'scripts')
    inserted_scripts_path = scripts_path not in sys.path
    if inserted_scripts_path:
        sys.path.insert(0, scripts_path)
    _EXECUTED.clear()
    _EXECUTED['_authenticated_prior_phase'] = {'path': old_runner_path, 'sha256': sha(old_runner_raw), 'bytes': len(old_runner_raw), 'authority': OLD_PACKET_MERGE}
    finder = _PinnedFinder(blobs, overrides)
    sys.meta_path.insert(0, finder)
    sys.modules.pop('evidence.geometry', None)
    sys.modules.pop('ellipsoidal_area', None)
    original_spec_from_file = importlib.util.spec_from_file_location

    def pinned_spec(name, location, *args, **kwargs):
        if name == 'pinned_original_reproducer':
            rel = 'data/regional-review/followup-northern-macedonia-422-roster-20261005/reproduce.py'
            raw = (overrides or {}).get(rel, blobs[rel])
            loader = _VerifiedLoader(name, str(ROOT / rel), raw, EXPECTED_HELPERS[rel])
            return importlib.util.spec_from_loader(name, loader, origin=str(ROOT / rel))
        return original_spec_from_file(name, location, *args, **kwargs)

    import contextlib
    captured = io.StringIO()
    importlib.util.spec_from_file_location = pinned_spec
    old_argv = sys.argv
    try:
        sys.argv = [str(ROOT / old_runner_path), output_buffer]
        with contextlib.redirect_stdout(captured):
            module.main()
    finally:
        sys.argv = old_argv
        importlib.util.spec_from_file_location = original_spec_from_file
        sys.meta_path.remove(finder)
        sys.modules.pop('evidence.geometry', None)
        sys.modules.pop('ellipsoidal_area', None)
        if inserted_scripts_path:
            sys.path.remove(scripts_path)
    report = json.loads(captured.getvalue())
    buffer_path = pathlib.Path(output_buffer)
    raw = buffer_path.read_bytes()
    if sha(raw) != report['sha256']:
        raise ValueError('prior runner output readback hash mismatch')
    buffer_path.unlink()
    if set(_EXECUTED) != {'_authenticated_prior_phase', 'pinned_original_reproducer', 'evidence.geometry', 'ellipsoidal_area'}:
        raise ValueError('not every pinned project code unit crossed the verified import boundary')
    return raw, dict(_EXECUTED)


def run(output: str, code_overrides: dict[str, bytes] | None = None, *, descriptor_override: bytes | None = None,
        input_overrides: dict[str, bytes] | None = None, runner_override: bytes | None = None,
        runner_pin_override: bytes | None = None) -> dict:
    # Reject unsafe output names and static symlink ancestors before input/code work.
    _parts_for_output(output)
    parent_fd, final_name = _prepare_destination(output)
    os.close(parent_fd)
    index, blobs = _descriptor(descriptor_override, input_overrides)
    _verify_checkout_code(blobs)
    own_runner = pathlib.Path(__file__).read_bytes()
    own_pin_raw = (OWNED / 'runner-pin.json').read_bytes()
    _verify_self_pin(own_runner, own_pin_raw)
    buffer_name = f'.authenticated-output-{uuid.uuid4().hex}.json'
    buffer_rel = str(OWNED_REL / buffer_name)
    buffer_fd, buffer_file = _prepare_destination(buffer_rel)
    os.close(buffer_fd)
    buffer_path = ROOT / buffer_rel
    try:
        raw, code = _run_legacy(str(buffer_path), blobs, code_overrides, runner_override, runner_pin_override)
    except Exception:
        try:
            buffer_path.unlink()
        except FileNotFoundError:
            pass
        raise
    _publish(output, raw)
    print(json.dumps({'output': output, 'bytes': len(raw), 'sha256': sha(raw), 'executed_code': code}, sort_keys=True))
    return {'output': output, 'bytes': len(raw), 'sha256': sha(raw), 'executed_code': code}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: guarded_reproduce.py data/regional-review/northern-macedonia-method-995-guard-erratum/v1/run-one.json')
    run(sys.argv[1])
