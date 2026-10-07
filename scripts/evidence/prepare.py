"""Generate a separate pinned subject-area ledger, never run packet scripts."""
import argparse
import json
from pathlib import Path
import sys
from shapely.geometry import shape
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence.geometry import METHOD, land_area_m2
from evidence.immutable import Baseline, VERSION, NewVintage, validate_source_receipts


def prepare(repo, request):
    if request.get('version') != 1:
        raise ValueError('Unsupported preparation request')
    baseline = Baseline(repo, request['baseline']['commit'], request['baseline']['files'])
    destination = NewVintage(baseline, request['owned_path'], request['new_vintage'], [request['output_filename']])
    for role in ('release', 'hierarchy', 'scope', 'source_registry'):
        if request['baseline'].get('pin_files', {}).get(role) not in baseline.pins:
            raise ValueError('Missing reviewed whole-file pin for ' + role)
    if request.get('source_receipts') is not None:
        registry = json.loads(baseline.read(request['baseline']['pin_files']['source_registry']))
        validate_source_receipts(registry, request['source_receipts'], baseline)
    subjects, files = baseline.subjects(request['subject_ids'])
    rows = [{'id': identity, 'area_m2': land_area_m2(shape(subjects[identity]['geometry'])),
             'containing_file': files[identity]} for identity in sorted(subjects)]
    value = {'version': VERSION, 'baseline_commit': baseline.commit, 'method': METHOD,
             'status': 'diagnostic-new-vintage', 'subjects': rows}
    record = destination.publish({request['output_filename']: value})[0]
    if request['output_filename'].endswith('.gz'):
        from evidence.immutable import canonical_json, sha256
        raw = canonical_json(value)
        record.update(uncompressed_sha256=sha256(raw), uncompressed_bytes=len(raw))
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--request', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.repo, json.loads(Path(args.request).read_text())), sort_keys=True))
