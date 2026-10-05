"""Actual Git/CLI/detector/native-source bridge for mocked read-only API tests.

Only the GitHub response transport is synthetic. Neither this fixture nor its
synthetic reviewer grants factual approval to an actual geography correction.
"""
import base64
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import geographic_adjudication as water
from evidence.immutable import canonical_json

spec = importlib.util.spec_from_file_location('native_controls', ROOT / 'test/geographic-adjudication.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
spec = importlib.util.spec_from_file_location('git_controls', ROOT / 'test/trusted-geography-check.py')
git_controls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(git_controls)

if sys.argv[1] == 'prepare':
    controls = native.Adjudication()
    controls.setUp()
    from shapely.geometry import box, mapping
    extent = box(-87.6, 47.6, -87.3, 47.85)
    before = {'synthetic:a': {'type': 'Feature', 'geometry': mapping(extent)}}
    after = {'synthetic:a': {'type': 'Feature', 'geometry': {
        'type': 'Polygon', 'coordinates': [mapping(extent)['coordinates'][0], mapping(controls.loss)['coordinates'][0]]}}}
    fixture = git_controls.Fixture()
    # Retain the temporary repository through the later validation process.
    fixture.write('data/geography/part.json', {'type': 'FeatureCollection', 'features': [
        {**feature, 'properties': {'id': key}, 'id': key} for key, feature in before.items()]})
    source = fixture.repo / native.SOURCE
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(controls.raw)
    fixture.baseline = fixture.commit('synthetic-actual-git-native-water-baseline')
    fixture.write('data/geography/part.json', {'type': 'FeatureCollection', 'features': [
        {**feature, 'properties': {'id': key}, 'id': key} for key, feature in after.items()]})
    candidate = fixture.commit('synthetic-actual-git-water-loss')
    result, report = fixture.run(candidate)
    if result.returncode != 1 or report['status'] != 'regressions-found':
        raise ValueError('Actual trusted CLI did not retain the raw loss: ' + result.stderr)
    dossier = controls.dossier(report)
    dossier_name = 'coordination/engineering/authority-fixture/dossier.json'
    # Add the dossier as candidate data; live geography inventory stays pinned.
    fixture.git('checkout', '-q', '--detach', candidate)
    fixture.write(dossier_name, dossier)
    candidate = fixture.commit('synthetic-actual-git-dossier')
    (fixture.repo / 'geography-check.json').unlink()
    result, report = fixture.run(candidate)
    if result.returncode != 1 or water.context(report) != dossier['context']:
        raise ValueError('Adding dossier changed the actual consumed geography context')
    fixture.temporary._finalizer.detach()
    print(json.dumps({'repo': str(fixture.repo), 'candidate': candidate, 'report': report,
                     'dossier': dossier, 'dossier_base64': base64.b64encode(subprocess.check_output(['git', '-C', str(fixture.repo), 'show', candidate + ':' + dossier_name])).decode(), 'source_base64': base64.b64encode(controls.raw).decode(),
                     'decoded_sha256': controls.ref['decoded_sha256']}))
elif sys.argv[1] == 'validate':
    payload = json.load(sys.stdin)
    repo = payload['repo']
    candidate = payload['candidate']
    def read(name):
        return subprocess.check_output(['git', '-C', repo, 'show', candidate + ':' + name])
    print(json.dumps(water.adjudicate(payload['report'], payload['envelope'], read)))
else:
    raise ValueError('Unknown synthetic pipeline phase')
