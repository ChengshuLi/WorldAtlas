"""Offline full-world geography comparison and staged neighboring shapes."""
import argparse
import gzip
import importlib.util
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.immutable import Baseline, canonical_json, sha256
from geographic_grid import projected_polygon
from shapely.geometry import shape


def generate(repo, evaluation, descriptor, registry_sha, out):
    if out.exists() or out.is_symlink():
        raise ValueError('Refuse to overwrite existing output directory')
    if descriptor['sha256'] != registry_sha:
        raise ValueError('Registry pin differs from command')
    registry = json.loads(Baseline(repo, evaluation, [descriptor]).read(descriptor['path']))
    baseline = Baseline(repo, registry['baseline_commit'], registry['baseline_files'])
    # Imported code is retained trusted baseline code, never changed packet logic.
    for name in ['scripts/check-geographic-regression.py', 'scripts/geographic_grid.py',
                 'scripts/evidence/immutable.py', 'scripts/evidence/geometry.py', 'scripts/ellipsoidal_area.py']:
        if (ROOT / name).read_bytes() != baseline.read(name):
            raise ValueError('Scientific helper differs from pinned baseline: ' + name)
    spec = importlib.util.spec_from_file_location('pinned_world_regression', ROOT / 'scripts/check-geographic-regression.py')
    detector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(detector)
    world = json.loads(baseline.read('data/world-index.json'))
    before = {}
    for name in world['parts']:
        collection = json.loads(baseline.read('data/' + name))
        for feature in collection['features']:
            identity = feature.get('id', feature['properties'].get('id'))
            if not identity or identity in before:
                raise ValueError('Missing or duplicate stable subject')
            before[identity] = feature
    candidate = json.loads(baseline.read(registry['candidate_path']))
    replacements = {f['id']:f for f in candidate['candidate']['features']}
    if set(replacements) != set(registry['subject_ids']) or len(candidate['candidate']['features']) != len(replacements):
        raise ValueError('Candidate subject inventory differs')
    originals = {f['id']:f['original_feature_sha256'] for f in candidate['preserved_before_features']}
    after = dict(before)
    for identity, feature in replacements.items():
        if sha256(canonical_json(before[identity])) != originals[identity]:
            raise ValueError('Candidate before feature differs from current baseline')
        if feature['properties'] != before[identity]['properties']:
            raise ValueError('Candidate changes identity/history properties')
        after[identity] = feature
    regression = detector.compare(before, after)
    manifest = json.loads(baseline.read('data/canonical-grid/manifest.json'))
    size = manifest['size']
    grids = json.loads(gzip.decompress(baseline.read('data/canonical-grid/bounds.json.gz')))
    by_id = {row['id']:row for row in grids}
    if len(by_id) != len(grids) or set(by_id) != set(before):
        raise ValueError('Grid bounds subject inventory differs from current world')
    expected_indices = set(range(1, len(before)+1))
    if {row['index'] for row in grids} != expected_indices:
        raise ValueError('Grid bounds owner indices are not exhaustive and unique')
    bounds = [projected_polygon(shape(feature['geometry']), size).bounds
              for identity in replacements for feature in [before[identity],after[identity]]]
    # Full affected shapes plus one-cell halo. Finite region bounded, no world bitmap.
    x0 = max(0, math.floor(min(b[0] for b in bounds))-1)
    y0 = max(0, math.floor(min(b[1] for b in bounds))-1)
    x1 = min(size, math.ceil(max(b[2] for b in bounds))+1)
    y1 = min(size, math.ceil(max(b[3] for b in bounds))+1)
    if not 0 < (x1-x0)*(y1-y0) <= 16000000:
        raise ValueError('Full-shape pixel domain exceeds bounded case budget')
    selected = sorted(identity for identity, row in by_id.items()
                      if row['bounds'][0] <= x1 and row['bounds'][2] >= x0
                      and row['bounds'][1] <= y1 and row['bounds'][3] >= y0)
    if not set(replacements) <= set(selected):
        raise ValueError('Missing changed subject in full-shape neighbor domain')
    components = json.loads(gzip.decompress(baseline.read(registry['component_path'])))['features']
    component = [f for f in components if f.get('id') == registry['component_id']]
    if len(component) != 1 or sha256(canonical_json(component[0])) != candidate['original_component_feature_sha256']:
        raise ValueError('Original full component differs')
    staged = {'version':1,'evaluation_commit':evaluation,'baseline_commit':registry['baseline_commit'],
              'registry_sha256':registry_sha,'size':size,'bbox':{'x':x0,'y':y0,'width':x1-x0,'height':y1-y0,'stride':1},
              'subject_ids':registry['subject_ids'],'component':component[0],
              'baseline':[before[i] for i in selected],'candidate':[after[i] for i in selected],
              'owner_indices':{i:by_id[i]['index'] for i in selected},
              'stored_bounds':{i:by_id[i]['bounds'] for i in selected},
              'limits':[registry['limit'],'Stored world bounds select every source shape touching the full-shape pixel rectangle; no claim of geometric authority or deployment.']}
    result = {'version':1,'method_id':'full-world-offline-candidate-regression','evaluation_commit':evaluation,
              'baseline_commit':registry['baseline_commit'],'registry_sha256':registry_sha,'world_subject_count':len(before),
              'changed_subject_count':len(replacements),'pixel_domain_subject_count':len(selected),
              'installation_ready':False,'geographic_approval':'unapproved','regression':regression,
              'limits':[registry['limit'],'Entire current world considered by unchanged pinned detector. Positive new overlaps remain blockers without area waiver. Reconstructed compilation does not compare original encoded partitions.']}
    out.mkdir()
    (out/'world-regression.json').write_bytes(canonical_json(result))
    (out/'staged-neighbors.json').write_bytes(canonical_json(staged))


def main():
    p=argparse.ArgumentParser()
    for name in ['repo','commit','registry','registry-sha256','out']:
        p.add_argument('--'+name,required=True)
    a=p.parse_args()
    generate(a.repo,a.commit,json.loads(a.registry),a.registry_sha256,Path(a.out))


if __name__ == '__main__':
    main()
