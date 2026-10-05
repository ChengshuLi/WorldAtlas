#!/usr/bin/env python3
"""Reproduce the exact 224-ID Croatian source/name/parent review for #419."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.immutable import Baseline, descriptor  # noqa: E402

def subjectsHash(ids):
    return hashlib.sha256('\n'.join(sorted(ids)).encode()).hexdigest()

SOURCE_PATH = 'data/regional-review/regional-review-ce7798317652c0c2/source/geoBoundaries-HRV-ADM2-9469f09.geojson'
SOURCE_SHA256 = '68a317129a0c295fd8baf7acc0f31ffefdf65ff2f1f62f8ed90a765cc57cf01e'
SOURCE_COMMIT = '9469f09'
DZS_EXTRACT_SHA256 = '225021e29f4ec2eeeffda3801031f4c0587241e91eed984394c9d2d56b09785c'
PROVINCE_TO_DZS = {
    'framework:province:zagreb-county:0f4faa1dfd12': 'Zagrebačka',
    'framework:province:varazdin:600a45216bdf': 'Varaždinska',
    'framework:province:sisak-moslavina:b2e12bd34165': 'Sisačko-moslavačka',
    'framework:province:meimurje:db4f218a3fa6': 'Međimurska',
    'framework:province:split-dalmatia:1efff6c4b5f2': 'Splitsko-dalmatinska',
    'framework:province:koprivnica-krizevci:6c51e4b2373a': 'Koprivničko-križevačka',
    'framework:province:bjelovar-bilogora:dbaf1e92e5a7': 'Bjelovarsko-bilogorska',
    'framework:province:dubrovnik-neretva:f777dfdf8192': 'Dubrovačko-neretvanska',
}
# Independently reviewed candidates: the names below are taken from the exact
# DZS 2021 table row, and the source-label side remains unchanged in the CSV.
CORRECTION_CANDIDATES = {
    'gb:HRV:ADM2:41942358B70634803465556': 'Hrvatska Dubica',
    'gb:HRV:ADM2:41942358B91711209403379': 'Velika Pisanica',
    'gb:HRV:ADM2:41942358B35075150352147': 'Donji Kukuruzari',
    'gb:HRV:ADM2:41942358B6406776425998': 'Ivanić-Grad',
}
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}


def read_xlsx_sheet(path: Path, wanted: str):
    """Read one simple tabular XLSX sheet with Python stdlib only."""
    with zipfile.ZipFile(path) as z:
        workbook = ET.fromstring(z.read('xl/workbook.xml'))
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        rel_by_id = {r.attrib['Id']: r.attrib['Target'] for r in rels}
        sheet = next(s for s in workbook.findall('m:sheets/m:sheet', NS) if s.attrib['name'] == wanted)
        target = rel_by_id[sheet.attrib[f'{{{NS["r"]}}}id']]
        sheet_path = target.lstrip('/') if target.startswith('/') else 'xl/' + target
        if not sheet_path.startswith('xl/'):
            sheet_path = 'xl/' + sheet_path
        shared = []
        try:
            strings = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in strings.findall('m:si', NS):
                shared.append(''.join(t.text or '' for t in si.findall('.//m:t', NS)))
        except KeyError:
            pass
        root = ET.fromstring(z.read(sheet_path))
        for row in root.findall('.//m:sheetData/m:row', NS):
            values = {}
            for cell in row.findall('m:c', NS):
                ref = cell.attrib.get('r', '')
                col = re.match(r'([A-Z]+)', ref).group(1)
                kind = cell.attrib.get('t')
                val = cell.find('m:v', NS)
                if kind == 's' and val is not None:
                    value = shared[int(val.text)]
                elif kind == 'inlineStr':
                    value = ''.join(t.text or '' for t in cell.findall('.//m:t', NS))
                elif val is not None:
                    value = val.text or ''
                else:
                    value = ''
                values[col] = value
            yield int(row.attrib['r']), values


def norm_label(s: str) -> str:
    s = unicodedata.normalize('NFC', s).strip()
    s = re.sub(r'\s+', ' ', s)
    return s.casefold().replace('–', '-').replace('−', '-')


def parse_geojson(path: Path):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('Raw geoBoundaries bytes do not match the pinned retrieval SHA-256')
    doc = json.loads(raw)
    if doc.get('type') != 'FeatureCollection' or not isinstance(doc.get('features'), list):
        raise ValueError('Pinned source is not a GeoJSON FeatureCollection')
    features = {}
    for f in doc['features']:
        p = f.get('properties') or {}
        shape_id = p.get('shapeID')
        if not shape_id or shape_id in features:
            raise ValueError('Missing or duplicate native shapeID in pinned source')
        features[shape_id] = f
    return raw, doc, features


def git_file(commit: str, path: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{commit}:{path}'])


def build(commit: str, output_dir: Path, source_path: Path):
    issue = json.loads((PACKET / 'source/issue-419-api-snapshot.json').read_text())
    body = issue['body']
    m = re.search(r'Machine-readable exact workload scope \(JSON;.*?\):\s*```json\s*(.*?)\s*```', body, re.S)
    if not m:
        raise ValueError('Cannot recover the exact issue workload scope')
    issue_scope = json.loads(m.group(1))
    saved_scope = json.loads((PACKET / 'scope.json').read_text())
    if issue_scope != saved_scope:
        raise ValueError('Retained scope JSON differs from original issue body')
    ids = issue_scope['member_location_ids']
    ids_hash = subjectsHash(ids)
    if ids_hash != issue_scope['member_location_ids_sha256']:
        raise ValueError('Exact issue subject digest mismatch')
    if len(ids) != 224 or len(set(ids)) != 224:
        raise ValueError('Expected 224 unique scope subjects')

    source_raw, source_doc, source_features = parse_geojson(source_path)
    if len(source_features) != 560:
        raise ValueError(f'Pinned geoBoundaries feature count changed: {len(source_features)}')

    ds_path = PACKET / 'source/dzs-census-2021-detail-extract.csv'
    ds_summary_path = PACKET / 'source/dzs-census-2021-summary-tables.xlsx'
    if hashlib.sha256(ds_path.read_bytes()).hexdigest() != DZS_EXTRACT_SHA256:
        raise ValueError('Retained DZS detail extract differs from its pinned SHA-256')
    with ds_path.open(encoding='utf-8', newline='') as f:
        official = [{'row': int(row['source_row']), 'county': row['county'], 'kind': row['kind'],
                     'county_en': row['county_en'], 'kind_en': row['kind_en'], 'name': row['name']}
                    for row in csv.DictReader(f)]
    if len(official) != 555:
        raise ValueError(f'Unexpected DZS 2021 town/municipality detail rows: {len(official)}')
    by_county_name_type = defaultdict(list)
    for unit in official:
        by_county_name_type[(unit['county'], norm_label(unit['name']), unit['kind'])].append(unit)
    summary = {}
    for row_no, row in read_xlsx_sheet(ds_summary_path, '1.'):
        if row_no < 9:
            continue
        county, county_en = row.get('A', ''), row.get('B', '')
        if county in set(PROVINCE_TO_DZS.values()):
            summary[county] = {'county_en': county_en, 'towns': int(row['F']), 'municipalities': int(row['G'])}

    # Pin actual containing files through the shared immutable subject reader.
    paths = ['data/world-index.json', 'data/hierarchy.json',
             'data/macro-foundation/regional-handoffs.json.gz',
             'data/macro-foundation/current-membership-inventory.json.gz',
             'data/geography/part-10.json', 'data/geography/part-28.json']
    pinned = []
    for p in paths:
        raw = git_file(commit, p)
        pinned.append(descriptor(p, raw))
    baseline = Baseline(ROOT, commit, pinned)
    atlas, containing = baseline.subjects(ids)
    subject_files = {identity: containing[identity]['path'] for identity in sorted(ids)}
    if not set(subject_files.values()).issubset({'data/geography/part-10.json', 'data/geography/part-28.json'}):
        raise ValueError('Unexpected subject containing files: ' + repr(sorted(set(subject_files.values()))))

    scope_provinces = {p['id']: p for p in issue_scope['province_scopes']}
    if set(scope_provinces) != set(PROVINCE_TO_DZS):
        raise ValueError('Issue province scopes differ from reviewed eight-province subset')
    per_county_ids = Counter()
    matched_names = defaultdict(set)
    assessments = []
    source_shape_counts = Counter()
    multipart = []
    source_id_to_id = {f'gb:HRV:ADM2:{fid}': fid for fid in source_features}
    for identity in ids:
        feature = atlas[identity]
        props = feature['properties']
        province_id = props['parent_id']
        province = scope_provinces.get(province_id)
        if not province:
            raise ValueError(f'Subject parent is outside declared province scope: {identity}')
        dzs_county = PROVINCE_TO_DZS[province_id]
        per_county_ids[dzs_county] += 1
        native = identity.split(':', 3)[3]
        raw_feature = source_features.get(native)
        if not raw_feature:
            raise ValueError(f'Scoped Atlas ID absent from exact upstream collection: {identity}')
        rp = raw_feature['properties']
        if rp.get('shapeGroup') != 'HRV' or rp.get('shapeType') != 'ADM2':
            raise ValueError(f'Unexpected source identity/country/tier for {identity}')
        atlas_name = props['name']
        source_name = rp.get('shapeName', '')
        if atlas_name != source_name:
            raise ValueError(f'Atlas/source name mismatch for scoped ID {identity}')
        if atlas_name.startswith('Općina '):
            source_kind, local_name = 'Općina', atlas_name[len('Općina '):]
        elif atlas_name.startswith('Grad '):
            source_kind, local_name = 'Grad', atlas_name[len('Grad '):]
        else:
            source_kind, local_name = '', atlas_name
        candidates = by_county_name_type[(dzs_county, norm_label(local_name), source_kind)]
        correction = CORRECTION_CANDIDATES.get(identity)
        if correction:
            official_rows = by_county_name_type[(dzs_county, norm_label(correction), source_kind)]
            if len(official_rows) != 1 or local_name == correction:
                raise ValueError(f'Correction candidate no longer uniquely matches official roster: {identity}')
            official_unit = official_rows[0]
            name_status, classification = 'correction-needed', 'correction-needed'
            rationale = 'Unique baseline-parent-county- and type-matched DZS 2021 row; source label differs from official name.'
            matched_names[dzs_county].add(norm_label(correction))
        elif len(candidates) == 1:
            official_unit = candidates[0]
            name_status, classification = 'justified', 'insufficient-evidence'
            rationale = 'Unique baseline-parent-county- and type-matched official DZS 2021 town/municipality name; this does not verify the parent or boundary.'
            matched_names[dzs_county].add(norm_label(official_unit['name']))
        else:
            raise ValueError(f'Unresolved official name/type/parent crosswalk for {identity}: {atlas_name!r} ({len(candidates)} matches)')
        geom = raw_feature.get('geometry') or {}
        geom_type = geom.get('type', '')
        coords = geom.get('coordinates') or []
        if geom_type == 'Polygon':
            components = 1
        elif geom_type == 'MultiPolygon':
            components = len(coords)
            multipart.append({'id': identity, 'name': atlas_name, 'province_id': province_id,
                             'province': province['name'], 'component_count': components})
        else:
            raise ValueError(f'Non-polygon scoped source geometry: {identity}: {geom_type}')
        atlas_geom_type = feature['geometry'].get('type', '')
        source_shape_counts[geom_type] += 1
        assessments.append({
            'id': identity,
            'native_source_id': native,
            'source_id': 'gb:HRV:ADM2',
            'source_name': source_name,
            'atlas_name': atlas_name,
            'official_2021_name': official_unit['name'],
            'official_unit_type_hr': official_unit['kind'],
            'official_unit_type_en': official_unit['kind_en'],
            'official_county_hr': official_unit['county'],
            'atlas_parent_id': province_id,
            'atlas_parent_name': province['name'],
            'parent_name_crosswalk': 'Atlas baseline parent ID mapped by reviewed county alias to the DZS county; source object has no independent county parent field',
            'parent_evidence_status': 'inherited-baseline-parent-not-independently-verified',
            'classification': classification,
            'name_type_status': name_status,
            'classification_basis': rationale,
            'boundary_evidence_status': 'insufficient-evidence',
            'boundary_limit': 'No same-vintage, reusable official municipal polygon set was available for comparison; source geometry is screening evidence only.',
            'source_geometry_type': geom_type,
            'atlas_geometry_type': atlas_geom_type,
            'geometry_type_disagreement': atlas_geom_type != geom_type,
            'source_polygon_component_count': components,
        })

    province_rows = []
    for province_id, province in scope_provinces.items():
        county = PROVINCE_TO_DZS[province_id]
        if county not in summary:
            raise ValueError(f'Official DZS county summary absent: {county}')
        expected = summary[county]
        detail_count = sum(1 for u in official if u['county'] == county)
        expected_count = expected['towns'] + expected['municipalities']
        if detail_count != expected_count:
            raise ValueError(f'DZS detail/summary count mismatch for {county}: {detail_count} vs {expected_count}')
        missing = [u for u in official if u['county'] == county and norm_label(u['name']) not in matched_names[county]]
        present = per_county_ids[county]
        province_rows.append({
            'province_id': province_id, 'atlas_province_name': province['name'],
            'official_county_name': county, 'official_county_english': expected['county_en'],
            'official_towns_2021': expected['towns'], 'official_municipalities_2021': expected['municipalities'],
            'official_local_units_2021': expected_count, 'issue_scope_locations': present,
            'unmatched_official_unit_count': len(missing),
            'unmatched_official_unit_names': [u['name'] for u in missing],
            'membership_status': 'roster-count-reconciles' if not missing and present == expected_count else 'gap-or-label-review-required',
        })

    classifications = Counter(row['classification'] for row in assessments)
    name_statuses = Counter(row['name_type_status'] for row in assessments)
    official_total = sum(row['official_local_units_2021'] for row in province_rows)
    scope_total = sum(row['issue_scope_locations'] for row in province_rows)
    missing_total = sum(row['unmatched_official_unit_count'] for row in province_rows)
    summary_doc = {
        'version': 1,
        'issue': 419,
        'baseline_commit': commit,
        'scope_ids_sha256': ids_hash,
        'metrics': {
            'scoped_subject_count': len(assessments),
            'source_id_name_matches': len(assessments),
            'name_type_matches_using_baseline_parent_count': name_statuses['justified'],
            'correction_needed_label_count': name_statuses['correction-needed'],
            'insufficient_name_crosswalk_count': name_statuses.get('insufficient-evidence', 0),
            'overall_insufficient_evidence_count': classifications['insufficient-evidence'],
            'overall_correction_needed_count': classifications['correction-needed'],
            'boundary_insufficient_evidence_count': sum(row['boundary_evidence_status'] == 'insufficient-evidence' for row in assessments),
            'official_2021_local_units_in_eight_counties': official_total,
            'atlas_locations_in_issue_scope': scope_total,
            'unmatched_official_2021_units_in_eight_counties': missing_total,
            'source_polygon_count': source_shape_counts['Polygon'],
            'source_multipolygon_count': source_shape_counts['MultiPolygon'],
            'multipart_source_location_count': len(multipart),
            'geometry_type_disagreement_count': sum(row['atlas_geometry_type'] != row['source_geometry_type'] for row in assessments),
        },
        'province_completeness': province_rows,
        'multipart_source_locations': multipart,
        'source_scope_limits': [
            'The 2021 census roster establishes unit names, types and county grouping, not official polygon coordinates or coastal/island boundary completeness.',
            'The DGU INSPIRE Administrative Units feed marks a public-access limitation under INSPIRE Article 13(1)(e); no linked polygon archive was downloaded or reused.',
            'The pinned geoBoundaries metadata reports 2021 as representative year but says source data was updated 2023-01-19. This is not evidence of an exact legal boundary snapshot on 2021-08-31.',
            'Its metadata claims CC BY-SA 2.0 and points to OpenStreetMap, while current post-2012 OpenStreetMap data is distributed under ODbL and geoBoundaries gives individual data files their own license. Reuse of the raw geometry was not adjudicated; this packet retains exact restoration/hash instructions rather than redistributing the geometry file.',
            'Multipart and polygon component counts are source-shape screening only; they do not prove boundary correctness or that all named islands are included.',
            'Only the exact 224 issue members and eight declared counties are assessed. The whole-country 2021 source roster, other Croatian counties and regional integration are not certified.',
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / 'scoped-location-assessments.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(assessments[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(assessments)
    with (output_dir / 'province-completeness.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(province_rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(province_rows)
    (output_dir / 'assessment-summary.json').write_text(json.dumps(summary_doc, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({
        'subject_hash': ids_hash,
        'subjects': len(assessments),
        'classification_counts': dict(classifications),
        'name_type_status_counts': dict(name_statuses),
        'province_gap_count': missing_total,
        'source_sha256': hashlib.sha256(source_raw).hexdigest(),
        'source_bytes': len(source_raw),
        'source_features': len(source_doc['features']),
        'baseline_subject_files': dict(Counter(subject_files for subject_files in subject_files.values())),
        'outputs': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output_dir.iterdir()) if p.is_file()},
    }, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--source', required=True, help='Locally restored upstream GeoJSON; see SOURCES.md')
    args = parser.parse_args()
    build(args.baseline, Path(args.output_dir), Path(args.source))
