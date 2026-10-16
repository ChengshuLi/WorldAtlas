"""Run the stock constructor with captured code and explicit finite resources."""
import hashlib
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import time

PREFIX = 'coordination/engineering/vietnam-revised-source-native-2076-20261016/'
LIMIT = 768 * 1024 ** 2
DEADLINE = 120
PATTERN = re.compile(r'''(?:\b(?:import|export)\s[^;]*?\bfrom\s*|\bimport\s*\(\s*|\bimport\s*)(['"])([^'"\n]+)\1''')


def sha(body):
    return hashlib.sha256(body).hexdigest()


def main(code_commit, config_commit, config_path, destination):
    assert all(re.fullmatch('[a-f0-9]{40}', c) for c in [code_commit, config_commit])
    assert re.fullmatch(r'[a-zA-Z0-9_./-]+', config_path) and '..' not in config_path.split('/')
    dest = pathlib.Path(destination)
    assert destination.startswith('.cache/') and '..' not in dest.parts and not os.path.lexists(dest)
    for ancestor in dest.parents:
        if ancestor.exists():
            assert ancestor.is_dir() and not ancestor.is_symlink() and ancestor.resolve() == ancestor.absolute()
    env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_NO_REPLACE_OBJECTS='1', GIT_TERMINAL_PROMPT='0')
    env.pop('NODE_PATH', None)
    env.pop('NODE_OPTIONS', None)

    def git(*args):
        return subprocess.check_output(['git', '--no-lazy-fetch', '--no-replace-objects', *args], env=env, timeout=15)

    def body(commit, name):
        row = git('ls-tree', '-lz', commit, '--', name)
        match = re.fullmatch(rb'100644 blob ([a-f0-9]{40})\s+(\d+)\t([^\0]+)\0', row)
        assert match and match[3].decode() == name
        raw = git('cat-file', 'blob', match[1].decode())
        assert len(raw) == int(match[2]) and hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == match[1].decode()
        return raw, dict(commit=commit, path=name, mode='100644', git_blob_oid=match[1].decode(), bytes=len(raw), sha256=sha(raw))

    launcher, launcher_pin = body(code_commit, PREFIX + 'run-bounded-native348.py')
    assert pathlib.Path(__file__).read_bytes() == launcher
    modules = {}
    pending = ['scripts/prepare-delivery-handoff.mjs']
    while pending:
        name = pending.pop()
        if name in modules:
            continue
        raw, pin = body(code_commit, name)
        modules[name] = (raw, pin)
        for _, specifier in PATTERN.findall(raw.decode()):
            if specifier.startswith('node:'):
                continue
            assert specifier.startswith('.'), 'Uncaptured package or nonliteral execution dependency: ' + specifier
            relative = os.path.normpath(os.path.join(os.path.dirname(name), specifier))
            assert not relative.startswith('../') and not os.path.isabs(relative)
            assert relative.endswith(('.js', '.mjs', '.cjs'))
            pending.append(relative)
    package, package_pin = body(code_commit, 'package.json')
    config, config_pin = body(config_commit, config_path)
    disk = os.statvfs('.')
    free = disk.f_bavail * disk.f_frsize
    memory = {line.split(':')[0]: int(line.split()[1]) * 1024 for line in pathlib.Path('/proc/meminfo').read_text().splitlines()
              if line.startswith(('MemTotal:', 'MemAvailable:'))}
    assert free > 10 * 1024 ** 3 + 32 * 1024 ** 2 and memory['MemAvailable'] > 2 * LIMIT
    dest.mkdir(mode=0o700)
    captured = dest / 'captured-code'
    captured.mkdir()
    for name, (raw, _) in {**modules, 'package.json': (package, package_pin)}.items():
        target = captured / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as output:
            output.write(raw)
    config_local = dest / 'captured-config.json'
    with config_local.open('xb') as output:
        output.write(config)
    command = ['node', str(captured / 'scripts/prepare-delivery-handoff.mjs'), 'native-authority', str(config_local), str(dest / 'authority')]
    admission = dict(kind='bounded-captured-stock-native348-prospective-admission-v1', command=command,
                     code_commit=code_commit, config=config_pin, launcher=launcher_pin,
                     project_code=[pin for _, pin in modules.values()] + [package_pin],
                     node_version=subprocess.check_output(['node', '--version'], env=env).decode().strip(),
                     runtime_flags=[], memory_rss_limit_bytes=LIMIT, wall_deadline_seconds=DEADLINE,
                     poll_seconds=0.05, free_bytes_before=free, memory_before=memory,
                     source_bank_and_physical_replay=False, output_log_allowance_bytes=32 * 1024 ** 2)
    admission_path = dest / 'admission.json'
    with admission_path.open('x') as output:
        output.write(json.dumps(admission, indent=2) + '\n')
    start = time.monotonic()
    peak = 0
    reason = None
    process = None
    try:
        with (dest / 'execution.log').open('x') as log:
            process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
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
                elif time.monotonic() - start > DEADLINE:
                    reason = 'wall_deadline'
                elif sum(p.stat().st_size for p in dest.rglob('*') if p.is_file()) > 32 * 1024 ** 2:
                    reason = 'output_log_allowance'
                if reason:
                    os.killpg(process.pid, signal.SIGKILL)
                    break
                time.sleep(0.05)
            code = process.wait()
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    receipt = dict(kind='bounded-captured-stock-native348-actual-execution-v1', exit_code=code,
                   elapsed_seconds=time.monotonic() - start, termination_reason=reason,
                   enforced_process_group_rss_limit_bytes=LIMIT, observed_sampled_process_group_peak_rss_bytes=peak,
                   enforced_wall_deadline_seconds=DEADLINE, admission_sha256=sha(admission_path.read_bytes()),
                   current_owner_zero=False, predecessor_conservation=False, accepted_credit=0)
    with (dest / 'execution.json').open('x') as output:
        output.write(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    print((dest / 'execution.log').read_text())
    assert code == 0 and reason is None, 'No successful native qualification execution'


if __name__ == '__main__':
    assert len(sys.argv) == 5
    main(*sys.argv[1:])
