"""First ordinary conflict3 native-authority call, after Root confirms local warming."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
REPO = Path('/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/267133ee5fd33696ea7c63ec50cf78bebfb3c92f9a18ca0fb1c4db8be3e0c49e/review')
NODE = '/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
HEAD = 'f82acf8da15646afd9ef51d57e2bd0c186f4aabd'
ENTRY_SHA = '6ca4f00e7617506c2d1276fd100f5c16a79e84c1a5a45715200be85afb9d5146'
INPUT = '4b14731f2a8cc602ed0a5a7e220f0d0a5b9d72d3'
PREFIX = 'coordination/engineering/indonesia-adm2-current-cell-20261014/remaining474-source-refinement-001/conflict3'
CONFIG = '.cache/conflict3-worker5-native-authority-001/config.json'
OUTPUT = '.cache/delivery-handoff/conflict3-worker5-native-authority-001'
EXPECTED = {'source-evidence.json': 'c0b3d974fe666c7c8c0f60df3a41a1cd4af29a63f2ad58ed0034a2bb76c2dc3a',
            'candidate-native-patch.json': 'bd99c1ef53c688c16e2e8c92a4412ffcbf47c771f730fb9745fc6bcab61add08'}

env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_NO_REPLACE_OBJECTS='1',
           GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='protocol.allow', GIT_CONFIG_VALUE_0='never')
for key in ['NODE_OPTIONS', 'NODE_PATH', 'WORLDATLAS_MEMORY_HEADROOM_BYTES', 'WORLDATLAS_CONCURRENT_RESERVED_BYTES']:
    env.pop(key, None)

def git(*args):
    return subprocess.check_output(['git', '-C', str(REPO)] + list(args), env=env)

assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert hashlib.sha256((REPO / 'scripts/prepare-delivery-handoff.mjs').read_bytes()).hexdigest() == ENTRY_SHA
assert not (HERE / 'authority-active-001.json').exists(), 'Prior launch exists; reconcile instead of repeating.'
assert not (REPO / CONFIG).exists() and not (REPO / OUTPUT).exists()
for relative in [CONFIG, OUTPUT]:
    subprocess.check_call(['git', '-C', str(REPO), 'check-ignore', '-q', '--', relative], env=env)
bindings = []
for name, expected in EXPECTED.items():
    body = git('show', INPUT + ':' + PREFIX + '/' + name)
    assert body == (HERE / name).read_bytes() and hashlib.sha256(body).hexdigest() == expected
    bindings.append({'commit': INPUT, 'path': PREFIX + '/' + name,
                     'bytes': len(body), 'sha256': expected})
config = {'version': 1,
          'source_evidence': {'commit': INPUT, 'path': PREFIX + '/source-evidence.json'},
          'native_patch': {'commit': INPUT, 'path': PREFIX + '/candidate-native-patch.json'}}
(REPO / CONFIG).parent.mkdir(parents=True, exist_ok=True)
with (REPO / CONFIG).open('x') as stream:
    json.dump(config, stream, indent=2)
    stream.write('\n')
(HERE / 'native-authority-config-001.json').write_bytes((REPO / CONFIG).read_bytes())
command = ['/usr/bin/time', '-l', NODE, 'scripts/prepare-delivery-handoff.mjs',
           'native-authority', CONFIG, OUTPUT]
at = datetime.datetime.now(datetime.timezone.utc).isoformat()
started = time.monotonic()
with (HERE / 'authority-stdout-001.log').open('xb') as stdout, (HERE / 'authority-stderr-001.log').open('xb') as stderr:
    child = subprocess.Popen(command, cwd=str(REPO), env=env, stdout=stdout, stderr=stderr)
    (HERE / 'authority-active-001.json').write_text(json.dumps(
        {'pid': child.pid, 'started_utc': at, 'command': command, 'cwd': str(REPO)}) + '\n')
    status = child.wait()
products = []
if (REPO / OUTPUT).exists():
    destination = HERE / 'actual-native-authority-001'
    assert not destination.exists()
    shutil.copytree(str(REPO / OUTPUT), str(destination))
    for path in sorted(destination.rglob('*')):
        if path.is_file():
            body = path.read_bytes()
            products.append({'path': str(path.relative_to(HERE)), 'bytes': len(body),
                             'sha256': hashlib.sha256(body).hexdigest()})
stderr = (HERE / 'authority-stderr-001.log').read_text()
receipt = {'kind': 'original-conflict3-first-stock-native-authority',
           'outcome': 'EXIT0' if status == 0 else 'STOCK_REFUSAL_OR_FAILURE',
           'exit_code': status, 'started_utc': at,
           'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'elapsed_seconds': time.monotonic() - started,
           'command': command, 'cwd': str(REPO), 'executing_checkout_head': HEAD,
           'executing_entry_sha256': ENTRY_SHA, 'input_bindings': bindings,
           'original_package': 'gb-IDN-ADM2--source-conflict', 'original_denominator': 27,
           'requested_original_cells': 3, 'repair474_requested_cells': 0,
           'source_or_physical_producer_replayed': False,
           'shared_index_or_branch_mutation': False, 'products': products,
           'actual_stderr_tail': stderr[-6000:] if status else None,
           'adoption_or_repair_credit': 0}
(HERE / 'authority-execution-001.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt), flush=True)
