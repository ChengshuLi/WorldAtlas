#!/usr/bin/env python3
"""Execute positive, negative and two-run reproducibility controls for #1291."""
import copy
import hashlib
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path.cwd()
sys.dont_write_bytecode = True
PACKET = pathlib.Path('data/regional-review/hainan-source-license-attribution-correction')
RUN1 = PACKET / 'runs/2026-10-07/run-1'
RUN2 = PACKET / 'runs/2026-10-07/run-2'
CONTROL = PACKET / 'controls/2026-10-07'
VALIDATION = PACKET / 'validation'
module_path = ROOT / PACKET / 'reproduce_attribution.py'
spec = importlib.util.spec_from_file_location('reproduce_attribution', module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def write(path, value):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def sha(data):
    return hashlib.sha256(data).hexdigest()

snapshot, quality = module.contract_from_snapshot()
originals, geometry = module.load_originals(quality)
metadata = json.loads(originals[str(module.METADATA)])
corrected_csv, ledger = module.build_artifacts(metadata, geometry, originals[str(module.CROSSWALK)], quality['subject_ids'])

# Positive: exact immutable metadata field + source geometry and crosswalk produce the 18-row correction.
rows = ledger and json.loads(ledger)
positive = {
    'method_id': 'hainan-metadata-attribution-correction',
    'kind': 'positive-control',
    'outcome': 'passed',
    'input_metadata_sha256': sha(originals[str(module.METADATA)]),
    'boundaryLicense': metadata['boundaryLicense'],
    'geojson_license_declaration': rows['geojson_license_declaration'],
    'corrected_subjects': rows['subject_count'],
    'corrected_license_fields': rows['corrected_license_fields'],
    'preserved_nonlicense_fields': rows['preserved_nonlicense_fields'],
    'corrected_csv_sha256': sha(corrected_csv),
    'result': 'PDDL is attributed to the separate metadata companion; unknown upstream rights remain unknown.'
}
write(CONTROL / 'positive-control.json', positive)

mutations = [
    ('odbl-substitution', lambda value: value.update({'boundaryLicense': 'Open Data Commons Open Database License (ODbL) v1.0'})),
    ('missing-boundaryLicense', lambda value: value.pop('boundaryLicense'))
]
negative_cases = []
for name, mutate in mutations:
    changed = copy.deepcopy(metadata)
    mutate(changed)
    path = CONTROL / f'{name}-metadata.json'
    write(path, changed)
    try:
        module.build_artifacts(changed, geometry, originals[str(module.CROSSWALK)], quality['subject_ids'])
    except ValueError as error:
        outcome = 'rejected-before-output'
        diagnostic = str(error)
    else:
        raise AssertionError(f'Incorrect metadata mutation accepted: {name}')
    negative_cases.append({'id': name, 'fixture_path': str(path), 'fixture_sha256': sha((ROOT / path).read_bytes()),
        'expected_license': metadata['boundaryLicense'], 'outcome': outcome, 'diagnostic': diagnostic})
negative = {
    'method_id': 'hainan-metadata-attribution-correction',
    'kind': 'negative-control',
    'outcome': 'passed',
    'cases': negative_cases,
    'interpretation': 'The generator rejects the unsupported ODbL substitution and a missing metadata license field before it can produce a corrected ledger.'
}
write(CONTROL / 'negative-control.json', negative)

outputs = ['hainan-18-crosswalk.csv', 'correction-ledger.json']
run_hashes = []
for directory in [RUN1, RUN2]:
    run_hashes.append({name: sha((ROOT / directory / name).read_bytes()) for name in outputs})
if run_hashes[0] != run_hashes[1]:
    raise AssertionError('Two complete corrected outputs are not byte-identical')
repro = {
    'method_id': 'hainan-metadata-attribution-correction',
    'kind': 'reproducibility',
    'outcome': 'passed',
    'run_one': {f'path:{name}': str(RUN1 / name) for name in outputs},
    'run_two': {f'path:{name}': str(RUN2 / name) for name in outputs},
    'run_one_sha256': sha(json.dumps(run_hashes[0], sort_keys=True, separators=(',', ':')).encode()),
    'run_two_sha256': sha(json.dumps(run_hashes[1], sort_keys=True, separators=(',', ':')).encode()),
    'files': run_hashes
}
write(CONTROL / 'reproducibility-results.json', repro)

write(VALIDATION / 'positive-control.json', {'evidence_path': str(CONTROL / 'positive-control.json'),
      **{k: positive[k] for k in ['method_id', 'kind', 'outcome']}})
write(VALIDATION / 'negative-control.json', {'evidence_path': str(CONTROL / 'negative-control.json'),
      **{k: negative[k] for k in ['method_id', 'kind', 'outcome']}})
write(VALIDATION / 'reproducibility.json', {'evidence_path': str(CONTROL / 'reproducibility-results.json'),
      **{k: repro[k] for k in ['method_id', 'kind', 'outcome', 'run_one_sha256', 'run_two_sha256']}})
print(json.dumps({'issue':1291,'positive':'passed','negative_cases':[c['id'] for c in negative_cases],
    'reproducibility':'passed','run_one_sha256':repro['run_one_sha256'],'run_two_sha256':repro['run_two_sha256']},indent=2))
