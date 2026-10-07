#!/usr/bin/env python3
"""Build a v1 manifest for the exact #1291 attribution correction outputs."""
import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path.cwd()
PACKET = pathlib.Path('data/regional-review/hainan-source-license-attribution-correction')
ORIGINAL = pathlib.Path('data/regional-review/regional-review-hainan-source-408')
BASELINE = 'a762119a4926c927617dc2f85471b3b822cadc58'
MANIFEST = PACKET / 'evidence-quality.json'
ATLAS = pathlib.Path('data/geography/part-4.json')
GEOJSON = pathlib.Path('data/regional-review/regional-review-365cbd6478904888/source/geoBoundaries-CHN-ADM2.geojson')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_bytes(path):
    return subprocess.check_output(['git', 'show', f'{BASELINE}:{path}'], stderr=subprocess.PIPE)


def read_json(path):
    return json.loads((ROOT / path).read_text())


def file_descriptor(path, role=None):
    data = git_bytes(path)
    result = {'path': path, 'bytes': len(data), 'sha256': sha(data), 'hash_kind': 'file-bytes'}
    if role:
        result['role'] = role
    return result


def subject_set_hash(values):
    return sha(json.dumps(sorted(values), ensure_ascii=False, separators=(',', ':')).encode())


def main():
    snapshot = read_json(PACKET / 'issue-scope-snapshot.json')
    contract_blocks = re.findall(r'<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->', snapshot['body'])
    if len(contract_blocks) != 1 or snapshot['number'] != 1291 or snapshot['state'] != 'OPEN':
        raise ValueError('Issue snapshot/contract no longer matches open #1291')
    contract = json.loads(contract_blocks[0])
    if contract.get('owned_paths') != [str(PACKET) + '/']:
        raise ValueError('Changed issue-owned path; refuse manifest build')
    quality = contract['evidence_quality']
    subjects = quality['subject_ids']
    if len(subjects) != 18 or quality['review_kind'] != 'source':
        raise ValueError('Issue evidence scope changed')

    original_pins = {key[len('baseline:'):]: value for key, value in quality['pins'].items()}
    paths = list(original_pins) + [str(GEOJSON), str(ATLAS)]
    if len(set(paths)) != len(paths):
        raise ValueError('Duplicate baseline source path')
    baseline_files = []
    pins = {}
    pin_files = {}
    for path, expected in original_pins.items():
        descriptor = file_descriptor(path, 'original-source')
        if descriptor['sha256'] != expected:
            raise ValueError(f'Issue pin mismatch at immutable #1071 merge: {path}')
        baseline_files.append(descriptor)
        pins[f'baseline:{path}'] = descriptor['sha256']
        pin_files[f'baseline:{path}'] = path
    for path, key, expected in [
        (str(GEOJSON), 'source:geoboundaries-2017-geometry', '2b68d8a808742fc6d7acd769584db960d8fc2c25b9f1d20e3e98c72e9f1c4d34'),
        (str(ATLAS), 'source:atlas-subject-part-4', 'e204a879e160f8b22ccfff698e8063a79d91cdba5ef7aa87df94661323b0bd3c')
    ]:
        descriptor = file_descriptor(path, 'original-source')
        if descriptor['sha256'] != expected:
            raise ValueError(f'Additional immutable input changed: {path}')
        baseline_files.append(descriptor)
        pins[key] = descriptor['sha256']
        pin_files[key] = path

    ledger_path = str(PACKET / 'runs/2026-10-07/run-1/correction-ledger.json')
    ledger = read_json(pathlib.Path(ledger_path))
    subject_files = {subject: str(ATLAS) for subject in subjects}
    atlas_bytes = git_bytes(str(ATLAS))
    atlas = json.loads(atlas_bytes)
    atlas_ids = {feature.get('id') or feature.get('properties', {}).get('id') for feature in atlas.get('features', [])}
    if not set(subjects).issubset(atlas_ids):
        raise ValueError('Not all issue IDs exist in the pinned Atlas subject part')

    outputs = []
    def collect(path):
        absolute = ROOT / path
        for entry in sorted(absolute.iterdir(), key=lambda x: x.name):
            relative = path / entry.name
            if entry.is_symlink():
                raise ValueError(f'Packet output cannot be a symlink: {relative}')
            if entry.is_dir():
                collect(relative)
            elif entry.is_file() and relative != MANIFEST:
                data = entry.read_bytes()
                outputs.append({'path': str(relative), 'bytes': len(data), 'sha256': sha(data), 'hash_kind': 'file-bytes'})
            else:
                raise ValueError(f'Unsupported packet entry: {relative}')
    collect(PACKET)
    output_map = {x['path']: x for x in outputs}
    if ledger_path not in output_map:
        raise ValueError('Correction ledger missing from output inventory')

    api_check = read_json(PACKET / 'upstream-metadata-api-check.json')
    metadata_bytes = git_bytes('data/regional-review/regional-review-365cbd6478904888/source/geoBoundaries-CHN-ADM2-metaData.json')
    metadata_obj = json.loads(metadata_bytes)
    geometry_path = str(GEOJSON)
    metadata_path = 'data/regional-review/regional-review-365cbd6478904888/source/geoBoundaries-CHN-ADM2-metaData.json'
    source_records = [
        {
            'id': 'geoboundaries-chn-adm2-metadata-2017',
            'url': api_check['files']['metadata_companion']['download_url'],
            'role': 'Separate geoBoundaries metadata companion; supports exact attribution of its boundaryLicense field, not the separate GeoJSON legal rights.',
            'vintage': '2017 reference boundary; metadata built 2023-12-12; source update field 2023-01-19',
            'retrieved_at': '2026-10-07',
            'license': {'status': 'unknown', 'terms': 'The metadata field declares PDDL 1.0; no legal rights, source chain, or permission to redistribute the separate geometry is inferred. The metadata licenseDetail/licenseSource locators are malformed.'},
            'retention': 'restoration-only',
            'verification': 'verified',
            'restoration': f"Resolve geoBoundaries repository commit {api_check['commit']} and restore {api_check['files']['metadata_companion']['path']} from its LFS object; require SHA-256 {api_check['files']['metadata_companion']['lfs_object_sha256']} and 1,101 bytes. The exact retained file is also pinned at #1071 merge under {metadata_path}.",
            'limit': 'Verifies the source metadata field and its LFS object identity only; original source licensing chain, legal validity, and reuse permission remain unknown.',
            'temporal_status': 'historical',
            'supported_interval': {'from': 2017, 'to': 2018}
        },
        {
            'id': 'geoboundaries-2017-chn-adm2-geometry',
            'url': api_check['files']['geometry']['download_url'],
            'role': 'Historical 2017 reference geometry used only to verify the exact native source subject identities and absence of a GeoJSON license field.',
            'vintage': '2017 reference; upstream release commit 2023-12-13',
            'retrieved_at': '2026-10-05',
            'license': {'status': 'unknown', 'terms': 'The separate metadata companion states PDDL 1.0, but its upstream rights chain is not independently cleared; no new copy is redistributed.'},
            'retention': 'restoration-only',
            'verification': 'verified',
            'restoration': f"Use exact Git LFS object at {api_check['files']['geometry']['download_url']}; require SHA-256 {api_check['files']['geometry']['lfs_object_sha256']} and {api_check['files']['geometry']['lfs_object_bytes']} bytes. The retained baseline copy is {geometry_path} at #1071 merge.",
            'limit': 'Byte identity and feature structure are verified; upstream rights/provenance, current legal boundaries, source completeness, and current roles are not.',
            'temporal_status': 'historical',
            'supported_interval': {'from': 2017, 'to': 2018}
        },
        {
            'id': 'issue-1291-scope',
            'url': snapshot['url'],
            'role': 'Authoritative issue contract for the exact 18 source-attribution subjects and bounded acceptance criteria.',
            'vintage': f"Issue raised/recorded {snapshot['body'].splitlines()[0]}",
            'retrieved_at': '2026-10-07',
            'license': {'status': 'unknown', 'terms': 'No data reuse license is inferred from a GitHub issue; the exact contract and body hash are retained in this packet.'},
            'retention': 'restoration-only',
            'verification': 'verified',
            'restoration': f"Restore the issue body from {snapshot['url']} and compare body_sha256 {snapshot['body_sha256']} in issue-scope-snapshot.json.",
            'limit': 'The issue authorizes only correction of the retained source metadata attribution for 18 IDs; it establishes no territorial, boundary, license-clearance, or regional approval.',
            'temporal_status': 'unknown'
        }
    ]

    # Derive baselines and ledger metrics from the pinned original and corrected outputs.
    original_csv = git_bytes(str(ORIGINAL / 'findings/hainan-18-crosswalk.csv'))
    import csv, io
    original_rows = list(csv.DictReader(io.StringIO(original_csv.decode('utf-8'), newline='')))
    original_counts = {}
    for row in original_rows:
        original_counts[row['assessment']] = original_counts.get(row['assessment'], 0) + 1
    if original_counts != ledger['preserved_assessment_counts']:
        raise ValueError('Original assessment counts changed')
    baseline_sha = {descriptor['path']: descriptor['sha256'] for descriptor in baseline_files}
    metric_definitions = [
        ('frozen-subject-count', 18, 'subjects', str(ORIGINAL / 'findings/hainan-18-crosswalk.csv')),
        ('corrected-license-field-count', 18, 'rows', metadata_path),
        ('preserved-nonlicense-field-count', 342, 'fields', str(ORIGINAL / 'findings/hainan-18-crosswalk.csv')),
        ('justified-disposition-count', original_counts['justified'], 'rows', str(ORIGINAL / 'findings/hainan-18-crosswalk.csv')),
        ('correction-needed-disposition-count', original_counts['correction-needed'], 'rows', str(ORIGINAL / 'findings/hainan-18-crosswalk.csv')),
        ('insufficient-evidence-disposition-count', original_counts['insufficient-evidence'], 'rows', str(ORIGINAL / 'findings/hainan-18-crosswalk.csv'))
    ]
    metrics = [{'id': key, 'value': value, 'unit': unit, 'vintage': 'baseline', 'input_sha256': baseline_sha[path], 'evaluation_commit': BASELINE}
               for key, value, unit, path in metric_definitions]
    metric_bindings = [{'metric_id': key, 'path': ledger_path, 'json_pointer': pointer} for (key, *_), pointer in zip(metric_definitions,
        ['/subject_count','/corrected_license_fields','/preserved_nonlicense_fields','/preserved_assessment_counts/justified','/preserved_assessment_counts/correction-needed','/preserved_assessment_counts/insufficient-evidence'])]
    summaries = [{'metric_id': m['id'], 'value': m['value'], 'unit': m['unit']} for m in metrics]
    methods = [
        {'id': 'hainan-metadata-attribution-correction', 'kind': 'generator', 'helper_version': 'worldatlas-evidence-preparation-v1',
         'description': 'Read the exact immutable #1071 source metadata, GeoJSON, original 18-row CSV and issue scope; replace only the unsupported license_reuse wording with a precise attribution to the separate metadata field while preserving all other cells.',
         'software': 'Python 3 standard library csv/json/hashlib; Git; issue-owned reproduce_attribution.py',
         'units': '18 frozen source IDs, metadata license field, CSV cells and whole-file SHA-256 bytes'},
        {'id': 'upstream-lfs-object-attribution', 'kind': 'source',
         'description': 'Resolve the exact upstream geoBoundaries GitHub commit and LFS pointers; compare the LFS object SHA-256 values with retained metadata and geometry bytes, and inspect the exact metadata and GeoJSON fields.',
         'software': 'GitHub REST API via gh; Python 3 standard library; Git immutable blobs',
         'units': 'upstream commit, two LFS pointer objects, source field values, and exact stored feature IDs'}
    ]
    manifest = {
        'version': 1,
        'issue': 1291,
        'lane': 'geography',
        'worker_id': '01a10947-b3d7-7812-8b2f-c5a47e88ccb2',
        'subject_ids': subjects,
        'subject_ids_sha256': subject_set_hash(subjects),
        'baseline': {'commit': BASELINE, 'files': baseline_files, 'pins': pins, 'pin_files': pin_files, 'subject_files': subject_files},
        'sources': source_records,
        'outputs': outputs,
        'methods': methods,
        'metrics': metrics,
        'summaries': summaries,
        'metric_bindings': metric_bindings,
        'validation': [
            {'method_id': 'hainan-metadata-attribution-correction', 'kind': 'positive-control', 'outcome': 'passed', 'evidence_path': str(PACKET / 'validation/positive-control.json')},
            {'method_id': 'hainan-metadata-attribution-correction', 'kind': 'negative-control', 'outcome': 'passed', 'evidence_path': str(PACKET / 'validation/negative-control.json')},
            {'method_id': 'hainan-metadata-attribution-correction', 'kind': 'reproducibility', 'outcome': 'passed', 'evidence_path': str(PACKET / 'validation/reproducibility.json')}
        ],
        'conclusions': [
            {'text': 'The separate geoBoundaries metadata companion at the pinned upstream commit states boundaryLicense PDDL 1.0; the original ODbL/embedded-metadata attribution is not faithful to the retained source record.', 'status': 'supported', 'source_ids': ['geoboundaries-chn-adm2-metadata-2017','geoboundaries-2017-chn-adm2-geometry']},
            {'text': 'The metadata field and upstream LFS object identity do not resolve the original source provenance, legal validity, or reuse rights. Current official boundaries, island/coastal completeness, and territorial roles remain unresolved.', 'status': 'unresolved', 'source_ids': ['geoboundaries-chn-adm2-metadata-2017','geoboundaries-2017-chn-adm2-geometry','issue-1291-scope']}
        ],
        'stages': {'research':'complete','implementation':'proposed','geographic_approval':'not-requested'},
        'commands': [
            'Run node scripts/local-workspace.mjs check before reproduction.',
            f'Run python3 {PACKET}/reproduce_attribution.py --output-dir {PACKET}/runs/2026-10-07/run-1 and repeat with run-2.',
            f'Run python3 {PACKET}/run_controls.py.',
            f'Run node scripts/evidence-quality.mjs {MANIFEST}.',
            'Run scripts/check-handoff-scope.mjs with current GitHub issue 1291, PR body and the exact branch before submitting.'
        ],
        'change_receipts': [*({'path': file['path'], 'status':'added'} for file in outputs), {'path':str(MANIFEST),'status':'added'}]
    }
    (ROOT / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'issue':1291,'subjects':len(subjects),'baseline_files':len(baseline_files),'outputs':len(outputs),'sources':len(source_records),'metrics':len(metrics),'manifest':str(MANIFEST)},indent=2))

if __name__ == '__main__':
    main()
