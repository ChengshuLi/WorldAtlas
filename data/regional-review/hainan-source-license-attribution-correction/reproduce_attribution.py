#!/usr/bin/env python3
"""Reproduce the bounded #1291 source-attribution correction from immutable bytes."""
import argparse
import csv
import hashlib
import io
import json
import pathlib
import re
import subprocess

BASELINE = 'a762119a4926c927617dc2f85471b3b822cadc58'
PACKET = pathlib.Path('data/regional-review/hainan-source-license-attribution-correction')
ORIGINAL = pathlib.Path('data/regional-review/regional-review-hainan-source-408')
SOURCE = pathlib.Path('data/regional-review/regional-review-365cbd6478904888/source')
README = ORIGINAL / 'README.md'
CROSSWALK = ORIGINAL / 'findings/hainan-18-crosswalk.csv'
PRODUCER = ORIGINAL / 'reproduce_hainan.py'
MANIFEST = ORIGINAL / 'evidence-quality.json'
METADATA = SOURCE / 'geoBoundaries-CHN-ADM2-metaData.json'
GEOJSON = SOURCE / 'geoBoundaries-CHN-ADM2.geojson'
PDDL = 'Open Data Commons Public Domain Dedication and License (PDDL) v1.0'
OLD_CLAIM = 'Unknown upstream provenance/reuse terms; embedded repository source metadata claims ODbL/PDDL; no new source copy redistributed.'
CORRECTED = ('Separate geoBoundaries metadata companion (not embedded in the GeoJSON) states '
             f'boundaryLicense="{PDDL}". Upstream provenance, source licensing and reuse rights remain '
             'unverified; no new source copy redistributed.')
EXPECTED = {
    str(README): '026d9b3a71a31f29cb866e32a09a5f0db0e8ecffcb4416edf6b5d01a9a6d83d2',
    str(CROSSWALK): '4c33b8f40263625a04f4a305356c668c8817a5af62c4781ad6d0725bfe4ea9e7',
    str(PRODUCER): '11d423b339d5af27405f4881ba8b21ad7146fe2e7d7f6b38bd289a9bb1bf0316',
    str(MANIFEST): 'f271f8ed0759425a565eda07bd7bf55a1326cbdf41c71df2e20ce59556f1094a',
    str(METADATA): '7f609da61c856d022a9bf83b35fb271d78ebb5855ad2c1cdff337e51acdec58a'
}
GEOJSON_SHA = '2b68d8a808742fc6d7acd769584db960d8fc2c25b9f1d20e3e98c72e9f1c4d34'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_bytes(path):
    return subprocess.check_output(['git', 'show', f'{BASELINE}:{path}'], stderr=subprocess.PIPE)


def contract_from_snapshot():
    snapshot = json.loads((PACKET / 'issue-scope-snapshot.json').read_text())
    if snapshot.get('number') != 1291 or snapshot.get('state') != 'OPEN':
        raise ValueError('Issue snapshot no longer identifies open #1291')
    if sha(snapshot['body'].encode()) != snapshot.get('body_sha256'):
        raise ValueError('Issue snapshot body hash mismatch')
    blocks = re.findall(r'<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->', snapshot['body'])
    if len(blocks) != 1:
        raise ValueError('Expected exactly one current #1291 work contract')
    contract = json.loads(blocks[0])
    if contract.get('mode') != 'geography' or contract.get('owned_paths') != [str(PACKET) + '/']:
        raise ValueError('Issue scope differs from this owned packet')
    quality = contract['evidence_quality']
    if len(quality['subject_ids']) != 18 or quality['review_kind'] != 'source':
        raise ValueError('Issue evidence declaration no longer matches exact source scope')
    return snapshot, quality


def load_originals(quality):
    files = {}
    for name, expected in EXPECTED.items():
        data = git_bytes(name)
        if sha(data) != expected:
            raise ValueError(f'Immutable #1071 baseline pin mismatch: {name}')
        files[name] = data
        if expected != quality['pins'].get(f'baseline:{name}'):
            raise ValueError(f'Issue pin mismatch: {name}')
    geometry = git_bytes(str(GEOJSON))
    if sha(geometry) != GEOJSON_SHA:
        raise ValueError('Pinned 2017 source GeoJSON hash mismatch')
    return files, geometry


def row_hash(row, license_field):
    retained = {key: value for key, value in row.items() if key != license_field}
    encoded = json.dumps(retained, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    return sha(encoded)


def build_artifacts(metadata, geometry, csv_bytes, expected_ids):
    if metadata.get('boundaryLicense') != PDDL:
        raise ValueError('Separate metadata boundaryLicense does not exactly match pinned PDDL 1.0 declaration')
    if metadata.get('boundaryID') != 'CHN-ADM2-17275852' or metadata.get('boundaryISO') != 'CHN' or \
       metadata.get('boundaryType') != 'ADM2' or metadata.get('boundaryYear') != '2017':
        raise ValueError('Metadata identity or vintage differs from the pinned China ADM2 record')
    geo = json.loads(geometry)
    if geo.get('type') != 'FeatureCollection' or set(geo) != {'type', 'crs', 'features'}:
        raise ValueError('Pinned GeoJSON structure differs from reviewed source record')
    property_keys = sorted({key for feature in geo['features'] for key in (feature.get('properties') or {})})
    if any(re.search(r'licen[cs]e', key, re.I) for key in [*geo.keys(), *property_keys]):
        raise ValueError('Pinned GeoJSON unexpectedly carries a license field')
    source_ids = set()
    for feature in geo['features']:
        p = feature.get('properties') or {}
        if p.get('shapeGroup') == 'CHN' and p.get('shapeType') == 'ADM2' and p.get('shapeID'):
            source_ids.add(f"gb:{p['shapeGroup']}:{p['shapeType']}:{p['shapeID']}")
    if not set(expected_ids).issubset(source_ids):
        raise ValueError('Pinned 2017 GeoJSON does not contain the exact frozen subjects')

    reader = csv.DictReader(io.StringIO(csv_bytes.decode('utf-8'), newline=''))
    if not reader.fieldnames or 'location_id' not in reader.fieldnames or 'license_reuse' not in reader.fieldnames:
        raise ValueError('Original ledger is missing required identity/license columns')
    fieldnames = list(reader.fieldnames)
    rows = list(reader)
    ids = [row['location_id'] for row in rows]
    if len(rows) != 18 or len(set(ids)) != 18 or set(ids) != set(expected_ids):
        raise ValueError('Original ledger IDs differ from exact frozen 18-member scope')
    if any(row['license_reuse'] != OLD_CLAIM for row in rows):
        raise ValueError('Original license field differs from the reproduced incorrect statement')
    unchanged_hashes = {row['location_id']: row_hash(row, 'license_reuse') for row in rows}
    for row in rows:
        row['license_reuse'] = CORRECTED
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator='\n', extrasaction='raise')
    writer.writeheader()
    writer.writerows(rows)
    corrected_csv = output.getvalue().encode('utf-8')
    after_reader = csv.DictReader(io.StringIO(corrected_csv.decode('utf-8'), newline=''))
    corrected_rows = list(after_reader)
    if [row['location_id'] for row in corrected_rows] != ids:
        raise ValueError('Correction changed row order or subject IDs')
    if any(row['license_reuse'] != CORRECTED for row in corrected_rows):
        raise ValueError('Every exact subject must carry the corrected metadata statement')
    if any(row_hash(row, 'license_reuse') != unchanged_hashes[row['location_id']] for row in corrected_rows):
        raise ValueError('A non-license field or finding changed')
    dispositions = {}
    for row in corrected_rows:
        dispositions[row['assessment']] = dispositions.get(row['assessment'], 0) + 1
    ledger = {
        'version': 1,
        'issue': 1291,
        'reviewed_issue': 1053,
        'baseline_commit': BASELINE,
        'original_vintage': {'commit': BASELINE, 'path': str(CROSSWALK), 'license_reuse': OLD_CLAIM},
        'corrected_vintage': 'source-attribution-only derivative of the immutable 2026-10-07 baseline; no territory or assessment is changed',
        'metadata_companion': {
            'path': str(METADATA),
            'boundaryID': metadata['boundaryID'],
            'boundaryISO': metadata['boundaryISO'],
            'boundaryType': metadata['boundaryType'],
            'boundaryYear': metadata['boundaryYear'],
            'boundaryLicense': metadata['boundaryLicense'],
            'licenseDetail': metadata.get('licenseDetail'),
            'licenseSource': metadata.get('licenseSource'),
            'boundarySourceURL': metadata.get('boundarySourceURL')
        },
        'geojson_license_declaration': None,
        'geojson_top_level_keys': sorted(geo.keys()),
        'geojson_feature_property_keys': property_keys,
        'subjects': [
            {'id': row['location_id'], 'corrected_license_reuse': row['license_reuse'],
             'preserved_nonlicense_row_sha256': unchanged_hashes[row['location_id']]}
            for row in corrected_rows
        ],
        'subject_count': len(corrected_rows),
        'corrected_license_fields': sum(row['license_reuse'] == CORRECTED for row in corrected_rows),
        'preserved_nonlicense_fields': len(corrected_rows) * (len(fieldnames) - 1),
        'preserved_assessment_counts': dispositions,
        'limits': [
            'The separate geoBoundaries metadata companion states PDDL 1.0; this is an attribution to the metadata field, not an independent legal conclusion or reuse clearance.',
            'The upstream provenance/source URLs in the retained metadata are malformed or unresolved; the upstream source licensing chain remains unverified.',
            'The pinned 2017 GeoJSON contains no license field; its recorded byte identity does not establish current legal boundaries, completeness, current roles or territorial approval.'
        ]
    }
    return corrected_csv, (json.dumps(ledger, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    out = pathlib.Path(args.output_dir).resolve()
    packet_abs = (pathlib.Path.cwd() / PACKET).resolve()
    try:
        out.relative_to(packet_abs)
    except ValueError:
        raise ValueError('Output directory must be a child of the issue-owned packet')
    if out == packet_abs:
        raise ValueError('Output directory must be a child of the issue-owned packet')
    snapshot, quality = contract_from_snapshot()
    originals, geometry = load_originals(quality)
    metadata = json.loads(originals[str(METADATA)])
    corrected_csv, ledger = build_artifacts(metadata, geometry, originals[str(CROSSWALK)], quality['subject_ids'])
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError('Output directory must be empty; preserve existing evidence')
    (out / 'hainan-18-crosswalk.csv').write_bytes(corrected_csv)
    (out / 'correction-ledger.json').write_bytes(ledger)
    print(json.dumps({'issue':1291,'baseline_commit':BASELINE,'subjects':18,
        'corrected_license_fields':18,'preserved_nonlicense_fields':342,
        'corrected_csv_sha256':sha(corrected_csv),'correction_ledger_sha256':sha(ledger)},indent=2))

if __name__ == '__main__':
    main()
