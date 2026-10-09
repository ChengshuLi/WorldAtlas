"""Replay captured before/after project code without changing the checkout."""
import hashlib, importlib.util, json, pathlib, subprocess, sys, types, unittest
root = pathlib.Path.cwd()
sys.path.insert(0, str(root / 'scripts'))
phase, stage = sys.argv[1:]
sys.argv = [sys.argv[0]]
scope = json.loads((root / '.cache/science-1544-profile/input-code-scope.json').read_text())
pins = {r['path']: r['sha256'] for r in scope['files']}

def capture(path):
    if stage == 'before':
        raw = subprocess.check_output(['git', 'show', scope['commit'] + ':' + path])
        if hashlib.sha256(raw).hexdigest() != pins[path]:
            raise ValueError('Captured baseline code differs')
    else:
        raw = (root / path).read_bytes()
    return raw

def module(name, path):
    result = types.ModuleType(name)
    result.__file__ = str(root / path)
    sys.modules[name] = result
    exec(compile(capture(path), result.__file__, 'exec'), result.__dict__)
    return result

module('physical_component_custody', 'scripts/physical_component_custody.py')
v = module('captured_validator', 'scripts/validate-physical-component-evidence.py')
if phase == 'positive':
    print(json.dumps(v.validate_science()))
elif phase == 'controls':
    path = root / 'test/physical-component-evidence-controls.py'
    if hashlib.sha256(path.read_bytes()).hexdigest() != pins[str(path.relative_to(root))]:
        raise ValueError('Original control code changed')
    spec = importlib.util.spec_from_file_location('captured_controls', path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.validator = v
    unittest.main(module=helper, defaultTest='Controls', verbosity=2, failfast=True)
else:
    raise ValueError('Unknown comparison phase')
