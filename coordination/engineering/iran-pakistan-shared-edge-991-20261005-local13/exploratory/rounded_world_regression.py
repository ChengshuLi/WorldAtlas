"""Run the unchanged detector against every immutable world footprint."""
import hashlib
import importlib.util
import json
import pathlib
import sys
import time
sys.path.insert(0, str(pathlib.Path('scripts').resolve()))
from evidence.immutable import canonical_json
path = pathlib.Path('scripts/check-geographic-regression.py')
spec = importlib.util.spec_from_file_location('trusted_regression', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
commit = '06bf4087bf5aec0e7071830ba61e99105f2c3697'
candidate_path = pathlib.Path('.cache/shared-edge-991/rounded-walk-diagnostic-v1.json')
raw = candidate_path.read_bytes()
candidate = json.loads(raw)
started = time.monotonic()
snapshot = module.snapshot(pathlib.Path('.'), commit)
before = snapshot['features']
after = dict(before)
for owner, geometry in candidate['candidates'].items():
    after[owner] = {**before[owner], 'geometry': geometry}
result = module.compare(before, after)
out = {'experimental': True, 'evaluation_commit': commit,
       'unchanged_detector_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
       'candidate_sha256': hashlib.sha256(raw).hexdigest(),
       'original_world_locations': len(before), 'files': snapshot['files'], 'pins': snapshot['pins'],
       'comparison': result,
       'limits': ['Unchanged detector results retained in full; no area threshold or adjudication.',
                  'Valid rounded diagnostic geometry does not approve rounding loss, source authority, county crosswalk or installation.']}
payload = canonical_json(out)
destination = pathlib.Path('.cache/shared-edge-991/rounded-world-regression-v1.json')
if destination.exists():
    raise ValueError('Refuse output overwrite')
destination.write_bytes(payload)
print(json.dumps({'sha256': hashlib.sha256(payload).hexdigest(), 'world_locations': len(before),
                  'status': result['status'], 'regressions': result['regressions'],
                  'geometry_errors': result['geometry_errors'],
                  'finding_types': [f['properties']['kind'] for f in result['findings']['features']],
                  'seconds': time.monotonic() - started}))
