"""Bind source-derived Caucasus seed and validation to a stage-2 request.

The orchestrator authenticates the outer config and records this module and all
dependencies in its own execution/resume identity. This helper does not run a
map or choose a boundary. The caller supplies its existing integrity callback.
"""
import json
import subprocess
import sys
from pathlib import Path

import caucasus_stage2_validation as validation
from caucasus_seed_gate import digest, validate_direct_request

HERE = Path(__file__).resolve().parent
CODE = validation.CODE + ('caucasus_stage2_binding.py',)


def verify_config(config, guard=lambda: None):
    if not isinstance(config, dict) or set(config) != {'recipe', 'hydro', 'author', 'code_sha256'}:
        raise ValueError('invalid Caucasus source binding')
    code = config['code_sha256']
    if not isinstance(code, dict) or set(code) != set(CODE):
        raise ValueError('complete Caucasus code pins required')
    for name in CODE:
        guard()
        pin = code[name]
        if not isinstance(pin, str) or len(pin) != 64 or digest(HERE / name) != pin:
            raise ValueError('Caucasus binding code mismatch: ' + name)
    for name in ('recipe', 'hydro', 'author'):
        pin = config[name]
        guard()
        if (not isinstance(pin, dict) or set(pin) != {'path', 'sha256'} or
                not isinstance(pin['path'], str) or not isinstance(pin['sha256'], str) or
                len(pin['sha256']) != 64 or digest(pin['path']) != pin['sha256']):
            raise ValueError('Caucasus input pin mismatch: ' + name)


def run_seed(config, request, request_sha256, producer_dir, producer_sha256,
             work, output, gate_report, guard=lambda: None):
    if not (sys.flags.isolated and sys.flags.no_site):
        raise ValueError('Caucasus seed binding requires isolated no-site Python')
    verify_config(config, guard)
    if digest(request) != request_sha256:
        raise ValueError('seed request pin mismatch')
    validate_direct_request(request)
    # The isolated outer caller must authenticate its explicit dependency paths.
    # Carry them into the no-site child without processing .pth files.
    bootstrap = ("import json,runpy,sys; paths=json.loads(sys.argv[1]); "
                 "sys.path[:0]=paths; p=sys.argv[2]; sys.argv=sys.argv[2:]; "
                 "runpy.run_path(p,run_name='__main__')")
    cmd = [sys.executable, '-I', '-S', '-B', '-c', bootstrap,
           json.dumps([str(HERE), *sys.path]), str(HERE / 'caucasus_seed_gate.py'),
           '--request', str(request), '--request-sha256', request_sha256,
           '--recipe', config['recipe']['path'], '--recipe-sha256', config['recipe']['sha256'],
           '--hydro', config['hydro']['path'], '--author', config['author']['path'],
           '--producer-dir', str(producer_dir), '--producer-sha256', producer_sha256,
           '--work', str(work), '--output', str(output), '--report', str(gate_report)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    guard()
    if digest(request) != request_sha256:
        raise ValueError('seed request changed')
    verify_config(config, guard)


def validate_seed(config, request, request_sha256, gate_report, producer_sha256,
                  validator, seed, groups, entity_codes, metric, guard=lambda: None):
    """Independently replay sources and compare to the seed gate's trace."""
    verify_config(config, guard)
    if not isinstance(gate_report, dict):
        raise ValueError('missing seed gate report')
    result, trace = validation.validate(
        validator, seed, groups, entity_codes, metric,
        request_path=request, request_sha256=request_sha256,
        recipe=config['recipe']['path'], recipe_sha256=config['recipe']['sha256'],
        hydro=config['hydro']['path'], author=config['author']['path'],
        code_sha256={k: config['code_sha256'][k] for k in validation.CODE}, guard=guard)
    derived = trace['source_derivation']
    source = derived['source_gate']
    expected = dict(source, request_sha256=request_sha256, seed_producer_executed=True,
                    seed_producer_sha256=producer_sha256, seed_worker_sha256=None,
                    effective_snapshot=derived['effective_snapshot'])
    if gate_report != expected:
        raise ValueError('seed gate and independently derived view differ')
    verify_config(config, guard)
    return result, {'schema': 'caucasus-stage2-binding-v1', 'validation': trace,
                    'binding_code_sha256': config['code_sha256']['caucasus_stage2_binding.py']}
