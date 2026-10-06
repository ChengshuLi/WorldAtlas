"""Stage the reviewed pair against a complete immutable world; never install it."""
import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.immutable import canonical_json, descriptor
spec = importlib.util.spec_from_file_location('regression', ROOT / 'scripts/check-geographic-regression.py')
regression = importlib.util.module_from_spec(spec)
spec.loader.exec_module(regression)

PROOF_COMMIT = 'd0cc67eac85038159f88a673acbc39b77ab7461d'
PROOF_PATH = 'coordination/engineering/iran-pakistan-native-joint-991-20261006-local21/results-v3/candidates.json'
TARGETS = {'gb:IRN:ADM2:26516999B17111396986996', 'gb:PAK:ADM2:60131773B78019453337506'}
MAX_BYTES = 32 * 1024 * 1024


def read(commit, name):
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + name])
    if len(raw) > MAX_BYTES:
        raise ValueError('Whole input exceeds bounded file size')
    return raw


def controls():
    def feature(identity, west, east):
        return {'type': 'Feature', 'id': identity, 'properties': {'id': identity},
                'geometry': {'type': 'Polygon', 'coordinates': [[[west, 0], [east, 0], [east, 1], [west, 1], [west, 0]]]}}
    before = {'a': feature('a', 0, 1), 'b': feature('b', 2, 3)}
    positive = regression.compare(before, {'a': feature('a', 0, 2), 'b': before['b']})
    loss = regression.compare(before, {'a': feature('a', 0, .5), 'b': before['b']})
    overlap = regression.compare(before, {'a': feature('a', 0, 2.5), 'b': before['b']})
    if positive['regressions'] != 0 or loss['regressions'] != 1 or overlap['regressions'] != 1:
        raise ValueError('Actual unchanged world detector control failed')
    if loss['findings']['features'][0]['properties']['kind'] != 'lost-previous-coverage' or overlap['findings']['features'][0]['properties']['kind'] != 'new-pair-overlap':
        raise ValueError('Detector rejected the wrong defect')
    return {'method_id': 'full-world-pair-staging', 'positive_gain_without_regression': True,
            'negative_lost_coverage_rejected': True, 'negative_new_overlap_rejected': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    if len(args.baseline) != 40 or any(c not in '0123456789abcdef' for c in args.baseline):
        raise ValueError('Exact baseline required')
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    subprocess.check_call(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', args.baseline, head])
    subprocess.check_call(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', PROOF_COMMIT, head])
    producer = []
    for name in [str(Path(__file__).relative_to(ROOT)), 'scripts/check-geographic-regression.py',
                 'scripts/evidence/geometry.py', 'scripts/evidence/immutable.py', 'requirements.txt']:
        raw = read(head, name)
        if raw != (ROOT / name).read_bytes():
            raise ValueError('Commit every executed producer before generation')
        producer.append(descriptor(name, raw))
    out = Path(args.out).resolve()
    if not out.is_relative_to(ROOT / 'coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22') or out.exists():
        raise ValueError('Fresh owned output directory required')
    control = controls()
    baseline = regression.snapshot(ROOT, args.baseline)
    proposal_raw = read(PROOF_COMMIT, PROOF_PATH)
    proposal = json.loads(proposal_raw)
    if set(proposal) != TARGETS or not TARGETS <= set(baseline['features']):
        raise ValueError('Exact target roster differs')
    candidate = dict(baseline['features'])
    archives = []
    for identity in sorted(TARGETS):
        before = baseline['features'][identity]
        after = copy.deepcopy(before)
        after['geometry'] = proposal[identity]
        candidate[identity] = after
        archives.append({'id': identity, 'feature': before})
    report = regression.compare(baseline['features'], candidate)
    if set(report['changed_location_ids']) != TARGETS:
        raise ValueError('Unexpected changed IDs')
    out.mkdir(parents=True, exist_ok=False)
    products = []

    def write(name, value, compress=False):
        decoded = canonical_json(value)
        raw = gzip.compress(decoded, mtime=0) if compress else decoded
        if max(len(decoded), len(raw)) > MAX_BYTES:
            raise ValueError('Stage product exceeds bounded size')
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
        products.append({**descriptor(name, raw), 'decoded_bytes': len(decoded),
                         'decoded_sha256': hashlib.sha256(decoded).hexdigest()})

    write('world-regression.json', report)
    write('original-target-features.json', archives)
    changed_parts = sorted({baseline['containing'][identity] for identity in TARGETS})
    for name in changed_parts:
        raw = read(args.baseline, name)
        collection = json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)
        collection['features'] = [candidate[f['id']] if f['id'] in TARGETS else f for f in collection['features']]
        write('stage/' + name, collection, compress=name.endswith('.gz'))
    summary = {'version': 1, 'baseline_commit': args.baseline, 'evaluation_commit': head,
               'candidate_geometry_commit': PROOF_COMMIT, 'candidate_geometry_file': descriptor(PROOF_PATH, proposal_raw),
               'producer': producer, 'baseline_inputs': baseline['files'], 'baseline_pins': baseline['pins'],
               'complete_world_locations': len(candidate), 'changed_ids': sorted(TARGETS),
               'changed_parts': changed_parts, 'unchanged_features': len(candidate) - len(TARGETS),
               'controls': control, 'status': report['status'], 'regressions': report['regressions'],
               'products': products, 'installed': False, 'published': False, 'history_transfer': False,
               'limits': ['Offline stage only; unchanged partitions remain referenced at the exact baseline.',
                          'Modern-reference source proposal only; no physical water, historical, legal or sovereignty determination.',
                          'Native ownership/release/certificate/content validation and independent integration review remain required.']}
    write('summary.json', summary)
    print(json.dumps({k: summary[k] for k in ['status', 'regressions', 'complete_world_locations', 'changed_ids']}))
    return 0 if report['status'] == 'no-new-regression' else 1


if __name__ == '__main__':
    sys.exit(main())
