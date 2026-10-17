"""Exercise actual Cuba adapter publication/method guards without rerunning science.
Usage: python check-adapter-publication.py REPO EXACT_METHOD_COMMIT PYTHON FRESH_OUTPUT
"""
import hashlib, json, os, pathlib, re, subprocess, sys, tempfile
assert len(sys.argv) == 5 and __debug__
W = pathlib.Path(sys.argv[1]).absolute()
C = sys.argv[2]
PYTHON = sys.argv[3]
O = pathlib.Path(sys.argv[4]).absolute()
P = 'coordination/engineering/cuba-repair-delivery-20261017'
assert re.fullmatch('[0-9a-f]{40}', C)
assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O, *O.parents))
ENV = {**os.environ, 'GIT_NO_LAZY_FETCH': '1', 'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0'}
ENV.pop('NODE_OPTIONS', None)
ENV.pop('NODE_PATH', None)
def git(*args):
    return subprocess.check_output(['git', '-c', 'protocol.allow=never', '-C', str(W), *args], env=ENV)
def sha(b):
    return hashlib.sha256(b).hexdigest()
assert git('show', C + ':' + P + '/probes/check-adapter-publication.py') == pathlib.Path(__file__).read_bytes()
methods = ['prepare-source-stage.py', 'screen-whole-foreign-bounds.mjs', 'reconcile-retained-periodic-negatives.mjs', 'prepare-native-config.mjs', 'reconcile-authority.py']
checks = []
for name in methods:
    method = W / P / 'probes' / name
    body = git('show', C + ':' + P + '/probes/' + name)
    assert method.read_bytes() == body
    executable = PYTHON if name.endswith('.py') else 'node'
    for control in ['occupied-output', 'symlink-output', 'method-drift']:
        with tempfile.TemporaryDirectory(prefix='cuba-publication-control-', dir=O.parent) as temporary:
            root = pathlib.Path(temporary)
            output = root / 'out'
            marker = b'previous owned output must survive unchanged\n'
            script = method
            if control == 'occupied-output':
                output.mkdir()
                (output / 'sentinel').write_bytes(marker)
            elif control == 'symlink-output':
                target = root / 'target'
                target.mkdir()
                (target / 'sentinel').write_bytes(marker)
                output.symlink_to(target, target_is_directory=True)
            else:
                script = root / name
                script.write_bytes(body + (b'\n# nonsemantic method drift\n' if name.endswith('.py') else b'\n// nonsemantic method drift\n'))
            run = subprocess.run([executable, str(script), str(W), C, str(output)], env=ENV, capture_output=True)
            assert run.returncode != 0, (name, control, 'unexpected success')
            if control == 'method-drift':
                assert not output.exists()
            else:
                assert (output / 'sentinel').read_bytes() == marker
                assert sorted(p.name for p in output.iterdir()) == ['sentinel']
            text = run.stderr.decode(errors='replace')
            assert 'AssertionError' in text if name.endswith('.py') else ('method drift' in text if control == 'method-drift' else any(word in text for word in ['fresh output', 'symlink']))
            checks.append({'method': P + '/probes/' + name, 'method_commit': C, 'method_sha256': sha(body), 'control': control, 'exit': run.returncode, 'stdout_sha256': sha(run.stdout), 'stderr_sha256': sha(run.stderr), 'stderr_tail': text[-800:], 'no_output_published_or_previous_bytes_changed': True})
assert len(checks) == 15
result = {'kind': 'actual-Cuba-adapter-publication-controls', 'method_commit': C, 'cases': len(checks), 'passed': len(checks), 'checks': checks, 'limits': ['These controls execute actual publication and method-identity admission. They do not replay source, physical or native geometry.', 'Positive scientific execution is the separately retained genuine source, physical, diagnostic, authority and accounting output, not a synthetic positive fixture.', 'The accepted stock pinReader and source/native constructor controls remain unchanged; their actual exact method closure is retained in the scientific manifest.']}
O.mkdir()
with (O / 'publication-controls.json').open('x') as handle:
    json.dump(result, handle, separators=(',', ':'))
    handle.write('\n')
print(json.dumps({'cases': len(checks), 'passed': len(checks)}))
