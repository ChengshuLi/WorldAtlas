#!/usr/bin/env python3
"""Reproduce the bounded China–Tajikistan seam comparison for issue #1096."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from shapely import union_all
from shapely.affinity import translate
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPoint, Point, Polygon, box, mapping, shape
from pyproj import Geod

REPO = Path(__file__).resolve().parents[3]
OWNED = 'research/geography/shared-seam-chn-tjk-20261005/'
BASELINE_COMMIT = '00664f04790641a9e0c0b29535823076ed243b93'
HISTORIC_COMMIT = '548c5f89f00271050823076a84695bb41e1b8454'
FRAGMENT_COMMIT = 'c603befd3aaf4da90d59b12378e1e0739331efba'
ENVELOPE = 'coordination/engineering/physical-gap-audit-1005-20261005-local18/input-envelope-v1/manifest.json'
AUDIT = 'coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json'
CANDIDATE = 'coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/candidates-009.geojson.gz'
FRAGMENT_ID = 'physical-gap:1418:402:f3681f4c89a36c563d6e41c6868c8cc03164f7296be7b3c71fce2bd16cba88cb'
FRAGMENT_FEATURE_SHA256 = 'd17c07b3c8fcb44cf2c667f91342efbb29e2e3f81565fedb32146c13333736f3'
SUBJECTS = [
    'gb:CHN:ADM2:17275852B723995182906',
    'gb:CHN:ADM2:17275852B99352197075157',
    'gb:TJK:ADM2:16282066B16686410577714',
]
SUBJECT_NAMES = {
    SUBJECTS[0]: 'Tashenkuergantajike',
    SUBJECTS[1]: 'Anketaoxian',
    SUBJECTS[2]: 'Murghob District',
}
SOURCE_FILES = {
    'chn_geo': ('sources/geoBoundaries-CHN-ADM2.geojson.gz', 7618692, '2b68d8a808742fc6d7acd769584db960d8fc2c25b9f1d20e3e98c72e9f1c4d34', 2300833, 'fea6d851f0eb0e5200cdff315a70d78ed6066a8e75f395bf9c4e7807ef04b126'),
    'tjk_geo': ('sources/geoBoundaries-TJK-ADM2.geojson.gz', 636686, '86fd6d7ec19f607e6d29adabba3ab9bde7a947950d8348504a934e911fb74e2d', 191418, 'd1d626b3087031f6715b8b5529d138efcf366037833f5e8eae6dcb828b7a04f5'),
    'chn_meta': ('sources/geoBoundaries-CHN-ADM2-metaData.json.gz', 1101, '7f609da61c856d022a9bf83b35fb271d78ebb5855ad2c1cdff337e51acdec58a', 598, 'a946ca31b31a2547cbff744255684de79e2fc326653364c0763f5c52e1555c0a'),
    'tjk_meta': ('sources/geoBoundaries-TJK-ADM2-metaData.json.gz', 851, 'c045fb290d10a980031d03d484f1331a56ee0c95337a7911f3fd83d0071fc78f', 431, '76df68e82838826505a1f051cfc6d69c9233f736d760aaabb1defa312727f9d7'),
    'citation': ('sources/CHN-CITATION-AND-USE.txt.gz', 4316, 'f6ea7572bea6036c4cdcacf8c0ca7bf09098d4e600d19546d7432533e9a290d5', 1811, '88dc3a4b342d6d17bdee256bd833693996d797f0d2108730feee44e2e7b9f878'),
}
GEO = Geod(ellps='WGS84')

sys.path.insert(0, str(REPO / 'scripts'))
from evidence.geometry import VERSION as GEOMETRY_VERSION, METHOD as GEOMETRY_METHOD, land_area_m2
from evidence.immutable import Baseline, canonical_json, descriptor, sha256, write_new_vintage


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(REPO), 'show', f'{commit}:{path}'])


def pin(path: str, commit: str, **extra) -> dict:
    raw = git_blob(commit, path)
    return {**descriptor(path, raw), **extra}


def baselines():
    index = json.loads(git_blob(BASELINE_COMMIT, 'data/world-index.json'))
    envelope_raw = git_blob(BASELINE_COMMIT, ENVELOPE)
    envelope = json.loads(envelope_raw)
    audit = json.loads(git_blob(BASELINE_COMMIT, AUDIT))
    candidate_descriptor = next(x for x in audit['outputs'] if x['path'] == CANDIDATE)
    current_paths = ['data/world-index.json', *['data/' + p for p in index['parts']],
        'data/hierarchy.json', 'data/canonical-grid/manifest.json',
        'data/geographic-releases/current-manifest.json', ENVELOPE, AUDIT]
    files = [pin(p, BASELINE_COMMIT) for p in current_paths]
    files.append(pin(CANDIDATE, BASELINE_COMMIT,
        uncompressed_bytes=candidate_descriptor['uncompressed_bytes'],
        uncompressed_sha256=candidate_descriptor['uncompressed_sha256']))
    for entry in envelope['entries']:
        enc, original = entry['encoded'], entry['original']
        files.append(pin(enc['path'], BASELINE_COMMIT,
            uncompressed_bytes=original['bytes'], uncompressed_sha256=original['sha256']))
    files_by_path = {f['path']: f for f in files}
    if len(files_by_path) != len(files):
        raise ValueError('Duplicate baseline path')
    current = Baseline(str(REPO), BASELINE_COMMIT, files)
    historic_files = [e['original'] for e in envelope['entries'] if e['source_commit'] == HISTORIC_COMMIT]
    if len({f['path'] for f in historic_files}) != len(historic_files):
        raise ValueError('Duplicate historical input path')
    historic = Baseline(str(REPO), HISTORIC_COMMIT, historic_files)
    return current, historic, envelope, audit, candidate_descriptor, files


def verify_source_files():
    root = REPO / OWNED / 'sources'
    records = {}
    for key, (rel, nbytes, expected_sha, encoded_bytes, encoded_sha) in SOURCE_FILES.items():
        encoded = (root / Path(rel).name).read_bytes()
        raw = gzip.decompress(encoded)
        if len(encoded) != encoded_bytes or sha256(encoded) != encoded_sha or len(raw) != nbytes or sha256(raw) != expected_sha:
            raise ValueError('Pinned upstream source file mismatch: ' + rel)
        records[key] = {'path': OWNED + rel, 'bytes': encoded_bytes, 'sha256': encoded_sha,
            'uncompressed_bytes': nbytes, 'uncompressed_sha256': expected_sha, 'hash_kind': 'file-bytes'}
    chn_citation = gzip.decompress((root / Path(SOURCE_FILES['citation'][0]).name).read_bytes())
    if sha256(chn_citation) != 'f6ea7572bea6036c4cdcacf8c0ca7bf09098d4e600d19546d7432533e9a290d5':
        raise ValueError('Upstream citation bytes changed')
    return records


def area_m2(geometry):
    if geometry.is_empty:
        return 0.0
    if geometry.geom_type in ('Polygon', 'MultiPolygon'):
        return land_area_m2(geometry)
    if geometry.geom_type == 'GeometryCollection':
        return sum(area_m2(g) for g in geometry.geoms)
    return 0.0


def line_length_m(geometry):
    if geometry.is_empty:
        return 0.0
    if geometry.geom_type in ('LineString', 'MultiLineString'):
        return float(GEO.geometry_length(geometry))
    if geometry.geom_type == 'GeometryCollection':
        return sum(line_length_m(g) for g in geometry.geoms)
    return 0.0


def type_counts(geometry):
    counts = Counter()
    def visit(g):
        if g.geom_type == 'GeometryCollection':
            counts['GeometryCollection'] += 1
            for child in g.geoms:
                visit(child)
        elif g.geom_type.startswith('Multi'):
            counts[g.geom_type] += 1
            for child in g.geoms:
                counts[child.geom_type] += 1
        else:
            counts[g.geom_type] += 1
    visit(geometry)
    return dict(sorted(counts.items()))


def geometry_record(geometry):
    return {
        'type': geometry.geom_type,
        'is_empty': geometry.is_empty,
        'is_valid': bool(geometry.is_valid) if not geometry.is_empty else None,
        'bounds': list(geometry.bounds) if not geometry.is_empty else None,
        'geometry_sha256': sha256(canonical_json(mapping(geometry))),
        'component_type_counts': type_counts(geometry),
        'polygon_area_m2': area_m2(geometry),
        'line_length_m': line_length_m(geometry),
        'area_method': GEOMETRY_METHOD['area_method'],
        'length_method': GEOMETRY_METHOD['distance_method'],
    }


def native_feature_map(path, country, ids):
    raw = (REPO / OWNED / path).read_bytes()
    dataset = json.loads(gzip.decompress(raw))
    matches = {}
    for feature in dataset['features']:
        native_id = feature.get('properties', {}).get('shapeID')
        key = f'gb:{country}:ADM2:{native_id}'
        if key in ids:
            matches.setdefault(key, []).append(feature)
    return dataset, matches


def execute(vintage):
    current, historic, envelope, audit, candidate_desc, baseline_files = baselines()
    script_path = OWNED + 'compare-seam.py'
    script_bytes = (REPO / script_path).read_bytes()
    execution_commit = subprocess.check_output(
        ['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip()
    committed_script = git_blob(execution_commit, script_path)
    if committed_script != script_bytes:
        raise ValueError('Comparison code is not byte-identical to its recorded execution commit')
    source_files = verify_source_files()
    current_features, current_containing = current.subjects(SUBJECTS)
    historic_features, historic_containing = historic.subjects(SUBJECTS)
    idx = json.loads(current.read('data/world-index.json'))
    if not all('geography/part-' in current_containing[x]['path'] for x in SUBJECTS):
        raise ValueError('Unexpected current containing file')

    # Verify every retained compressed envelope member against both its decoded
    # whole-file hash and its exact immutable source-commit blob.
    readback = []
    for entry in envelope['entries']:
        encoded, original = entry['encoded'], entry['original']
        raw = current.read(encoded['path'])
        decoded = gzip.decompress(raw)
        historic_raw = git_blob(entry['source_commit'], original['path'])
        if len(raw) != encoded['bytes'] or sha256(raw) != encoded['sha256']:
            raise ValueError('Input envelope encoded bytes differ: ' + encoded['path'])
        if len(decoded) != original['bytes'] or sha256(decoded) != original['sha256'] or decoded != historic_raw:
            raise ValueError('Input envelope decoded source differs: ' + original['path'])
        readback.append({'encoded_path': encoded['path'], 'encoded_bytes': len(raw), 'encoded_sha256': sha256(raw),
            'original_path': original['path'], 'original_bytes': len(decoded), 'original_sha256': sha256(decoded),
            'source_commit': entry['source_commit'], 'git_blob': entry['original_git_blob'], 'status': 'verified'})

    chn, chn_matches = native_feature_map('sources/geoBoundaries-CHN-ADM2.geojson.gz', 'CHN', SUBJECTS)
    tjk, tjk_matches = native_feature_map('sources/geoBoundaries-TJK-ADM2.geojson.gz', 'TJK', SUBJECTS)
    native = {}
    for source_map in (chn_matches, tjk_matches):
        for key, matches in source_map.items():
            native[key] = matches
    crosswalk = []
    source_geometries, current_geometries, historic_geometries = {}, {}, {}
    for identity in SUBJECTS:
        rows = native.get(identity, [])
        if len(rows) != 1:
            raise ValueError(f'Native source member count is {len(rows)} for {identity}')
        src = rows[0]
        atlas = current_features[identity]
        old = historic_features[identity]
        src_props = src['properties']
        props = atlas['properties']
        metadata = props['metadata']
        native_id = identity.rsplit(':', 1)[1]
        if src_props.get('shapeID') != native_id or src_props.get('shapeName') != SUBJECT_NAMES[identity] or props.get('name') != SUBJECT_NAMES[identity]:
            raise ValueError('Native identity/name crosswalk mismatch: ' + identity)
        sg, ag, hg = shape(src['geometry']), shape(atlas['geometry']), shape(old['geometry'])
        source_geometries[identity], current_geometries[identity], historic_geometries[identity] = sg, ag, hg
        source_geometry_hash = sha256(canonical_json(src['geometry']))
        old_geometry_hash = metadata.get('original_geometry_sha256')
        crosswalk.append({
            'subject_id': identity, 'native_property': 'shapeID', 'native_value': native_id,
            'native_feature_count_in_full_source': 1, 'native_name': src_props['shapeName'],
            'atlas_name': props['name'], 'identity_name_match': True,
            'source_member_geometry_type': src['geometry']['type'],
            'source_member_geometry_sha256_canonical_json': source_geometry_hash,
            'atlas_metadata_original_geometry_sha256': old_geometry_hash,
            'declared_original_digest_matches_retrieved_member': source_geometry_hash == old_geometry_hash,
            'source_member_geometry': geometry_record(sg), 'current_atlas_geometry': geometry_record(ag),
            'source_to_atlas_symmetric_difference': geometry_record(sg.symmetric_difference(ag)),
            'source_equals_current_atlas': bool(sg.equals(ag)),
            'historic_atlas_equals_current_atlas': bool(hg.equals(ag)),
            'historic_to_current_symmetric_difference': geometry_record(hg.symmetric_difference(ag)),
            'atlas_context': {
                'source_id': metadata.get('source_id'), 'source_url': metadata.get('source_url'),
                'license': metadata.get('license'), 'reference_year': metadata.get('reference_year'),
                'source_role': metadata.get('source_role'), 'parent_id': props.get('parent_id'),
                'reference_owner': props.get('reference_owner'), 'topology_reconciled': metadata.get('topology_reconciled'),
                'topology_conflicts': metadata.get('topology_conflicts'), 'topology_note': metadata.get('topology_note'),
            },
        })

    audit_raw = current.read(AUDIT)
    candidate_raw = current.read(CANDIDATE)
    if sha256(candidate_raw) != candidate_desc['sha256'] or len(candidate_raw) != candidate_desc['bytes']:
        raise ValueError('Whole retained candidate file bytes differ from report')
    decoded_candidates = gzip.decompress(candidate_raw)
    if len(decoded_candidates) != candidate_desc['uncompressed_bytes'] or sha256(decoded_candidates) != candidate_desc['uncompressed_sha256']:
        raise ValueError('Whole retained candidate file decoded bytes differ from report')
    if sha256(git_blob(FRAGMENT_COMMIT, CANDIDATE)) != sha256(candidate_raw):
        raise ValueError('Retained candidate full-file bytes differ from original c603 commit')
    candidate_set = json.loads(decoded_candidates)
    features = [f for f in candidate_set['features'] if f.get('id') == FRAGMENT_ID]
    if len(features) != 1:
        raise ValueError('Original seam fragment is not unique in whole candidate file')
    fragment = features[0]
    feature_hash = sha256(canonical_json(fragment))
    fragment_hash = sha256(canonical_json(fragment['geometry']))
    if feature_hash != FRAGMENT_FEATURE_SHA256 or fragment_hash != FRAGMENT_ID.rsplit(':', 1)[1]:
        raise ValueError('Original full-feature/geometry digest differs')
    fg = shape(fragment['geometry'])
    if fragment['properties'].get('area_m2') is None:
        raise ValueError('Fragment has no retained diagnostic area')

    group_results = {}
    for label, geometries in [('native_source', source_geometries), ('atlas_reconciled', current_geometries)]:
        union = union_all([geometries[x] for x in SUBJECTS])
        covered = fg.intersection(union)
        uncovered = fg.difference(union)
        group_results[label] = {
            'union_geometry': geometry_record(union),
            'fragment_covered_geometry': geometry_record(covered),
            'fragment_uncovered_geometry': geometry_record(uncovered),
            'fragment_covered_fraction': area_m2(covered) / area_m2(fg),
            'fragment_uncovered_fraction': area_m2(uncovered) / area_m2(fg),
        }

    fragment_contacts = {}
    for label, geometries in [('native_source', source_geometries), ('atlas_reconciled', current_geometries)]:
        fragment_contacts[label] = {}
        for identity in SUBJECTS:
            geom = geometries[identity]
            fragment_contacts[label][identity] = {
                'fragment_intersection': geometry_record(fg.intersection(geom)),
                'boundary_contact': geometry_record(fg.boundary.intersection(geom.boundary)),
            }

    pairwise = []
    for i, left in enumerate(SUBJECTS):
        for right in SUBJECTS[i + 1:]:
            row = {'subjects': [left, right]}
            for label, geometries in [('native_source', source_geometries), ('atlas_reconciled', current_geometries)]:
                a, b = geometries[left], geometries[right]
                row[label] = {
                    'polygon_intersection': geometry_record(a.intersection(b)),
                    'shared_boundary': geometry_record(a.boundary.intersection(b.boundary)),
                }
            pairwise.append(row)

    source_meta = {}
    for country in ('CHN', 'TJK'):
        metadata_raw = (REPO / OWNED / f'sources/geoBoundaries-{country}-ADM2-metaData.json.gz').read_bytes()
        source_meta[country] = json.loads(gzip.decompress(metadata_raw))
    # Positive control: this exact native CHN pair shares a recorded line.
    positive_geom = source_geometries[SUBJECTS[0]].boundary.intersection(source_geometries[SUBJECTS[1]].boundary)
    positive = {
        'method_id': 'chn-tjk-native-seam', 'kind': 'geography', 'outcome': 'passed',
        'control': 'Positive geographic control: the two CHN source members share a line contact.',
        'geometry': geometry_record(positive_geom), 'assertions': {
            'contact_is_nonempty': not positive_geom.is_empty,
            'geodesic_contact_length_m_positive': line_length_m(positive_geom) > 0,
        },
    }
    # Negative control: same exact overlay operation on disjoint analytic polygons.
    negative_a = box(73.0, 37.0, 73.1, 37.1)
    negative_b = box(83.0, 37.0, 83.1, 37.1)
    negative_geom = negative_a.intersection(negative_b)
    negative = {
        'method_id': 'chn-tjk-native-seam', 'kind': 'geography', 'outcome': 'passed',
        'control': 'Negative numerical control: disjoint analytic EPSG:4326 rectangles return an empty intersection; this does not assert any geographic fact.',
        'geometry': geometry_record(negative_geom), 'assertions': {
            'intersection_is_empty': negative_geom.is_empty,
            'polygon_area_m2_zero': area_m2(negative_geom) == 0,
            'line_length_m_zero': line_length_m(negative_geom) == 0,
        },
    }
    if not all(positive['assertions'].values()) or not all(negative['assertions'].values()):
        raise ValueError('Positive/negative scientific controls failed')

    receipt = {
        'method_id': 'chn-tjk-native-seam', 'kind': 'geography', 'outcome': 'passed',
        'historical_input_envelope': {
            'manifest_path': ENVELOPE,
            'entry_count': len(readback), 'encoded_bytes_total': sum(x['encoded_bytes'] for x in readback),
            'decoded_original_bytes_total': sum(x['original_bytes'] for x in readback),
            'verified_originals': readback,
        },
    }
    crosswalk_artifact = {
        'method_id': 'chn-tjk-native-seam', 'kind': 'source', 'outcome': 'passed',
        'upstream_commit': '9469f09592ced973a3448cf66b6100b741b64c0d',
        'commit_timestamp': '2023-12-13T04:03:07Z', 'retrieved_at': '2026-10-06',
        'whole_source_file_descriptors': source_files,
        'citation_sha256': SOURCE_FILES['citation'][2],
        'source_metadata': source_meta,
        'subject_crosswalk': crosswalk,
    }
    result = {
        'method_id': 'chn-tjk-native-seam', 'kind': 'geography', 'outcome': 'passed',
        'scope': {'subject_ids': SUBJECTS, 'baseline_commit': BASELINE_COMMIT,
            'historic_input_commit': HISTORIC_COMMIT, 'fragment_original_commit': FRAGMENT_COMMIT,
            'fragment_id': FRAGMENT_ID, 'fragment_full_feature_sha256': feature_hash,
            'fragment_geometry_sha256': fragment_hash, 'fragment_feature_bytes': len(canonical_json(fragment)),
            'fragment_candidate_file_path': CANDIDATE, 'fragment_candidate_file_sha256': candidate_desc['sha256'],
            'fragment_candidate_file_bytes': candidate_desc['bytes'],
            'fragment_candidate_uncompressed_sha256': candidate_desc['uncompressed_sha256'],
            'fragment_candidate_uncompressed_bytes': candidate_desc['uncompressed_bytes']},
        'execution': {'commit': execution_commit,
            'code_path': script_path, 'code_bytes': len(script_bytes),
            'code_sha256': sha256(script_bytes),
            'dirty_code_bytes_match_commit': True},
        'spatial_method': GEOMETRY_METHOD,
        'software': {'evidence_geometry_version': GEOMETRY_VERSION,
            'shapely': __import__('shapely').__version__, 'pyproj': __import__('pyproj').__version__},
        'historical_baseline_subject_ids': SUBJECTS,
        'current_subject_containing_files': current_containing,
        'historic_subject_containing_files': historic_containing,
        'subjects': crosswalk,
        'source_metadata': source_meta,
        'pairwise_topology': pairwise,
        'fragment_vs_subjects': fragment_contacts,
        'fragment_coverage': group_results,
        'fragment_source_diagnostics': {
            'retained_candidate_area_m2': fragment['properties'].get('area_m2'),
            'coarse_lake_hit': False,
            'coarse_lake_limit': 'A major-lakes-only non-hit is not evidence of dry land; independent detailed hydrology/terrain remains unavailable.',
            'administrative_assignment': fragment['properties'].get('administrative_assignment'),
        },
        'operations': {
            'input_geometries_validated_without_repair': all(x['source_member_geometry']['is_valid'] and x['current_atlas_geometry']['is_valid'] for x in crosswalk),
            'make_valid_or_snap_or_buffer_or_area_cutoff_or_nearest_owner_used': False,
            'topological_operations': 'Direct Shapely intersections, boundaries, union, difference and symmetric difference on untouched EPSG:4326 inputs; no coordinate snapping or projection.',
            'area_and_distance': GEOMETRY_METHOD,
            'errors': [],
        },
        'source_hash_limit': 'The three Atlas metadata original_geometry_sha256 values do not match canonical JSON digests of the independently retrieved 9469f09 members. The member identities and names match once each; the upstream metadata does not state the digest serialization/source-geometry recipe, so these digest mismatches are unresolved.',
        'land_authority_limit': 'The retained 2017 ADM2 source metadata do not provide a dated authoritative CHN–TJK international boundary instrument. No ownership assignment is made.',
        'physical_surface_limit': 'The retained candidate derives from a generalized land audit and major-lakes-only diagnostic; detailed terrain, rivers, seasonal water and ground survey were not independently established.',
    }
    return current, result, crosswalk_artifact, receipt, positive, negative, readback


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--vintage', required=True, help='Unique output vintage, such as run-one-20261006')
    parser.add_argument('--action', choices=['run', 'reproducibility'], default='run')
    args = parser.parse_args()
    if args.action == 'run':
        current, result, crosswalk, receipt, positive, negative, readback = execute(args.vintage)
        output = {}
        for name, value in [('comparison.json', result), ('source-crosswalk.json', crosswalk),
                ('input-envelope-readback.json', receipt), ('positive-control.json', positive),
                ('negative-control.json', negative)]:
            output[name] = write_new_vintage(current, OWNED, args.vintage, name, value)
        print(json.dumps(output, sort_keys=True, indent=2))
        return
    # The reproducibility artifact is produced in its own fresh vintage after both
    # independent process runs have completed.
    current, *_ = baselines()
    root = REPO / OWNED
    run_one = root / 'vintages/final-one-20261006'
    run_two = root / 'vintages/final-two-20261006'
    names = ['comparison.json', 'source-crosswalk.json', 'input-envelope-readback.json',
        'positive-control.json', 'negative-control.json']
    hashes_one = {name: sha256((run_one / name).read_bytes()) for name in names}
    hashes_two = {name: sha256((run_two / name).read_bytes()) for name in names}
    one = (run_one / 'comparison.json').read_bytes()
    two = (run_two / 'comparison.json').read_bytes()
    doc = {
        'method_id': 'chn-tjk-native-seam', 'kind': 'geography', 'outcome': 'passed',
        'run_one_path': OWNED + 'vintages/run-one-20261006/comparison.json',
        'run_two_path': OWNED + 'vintages/run-two-20261006/comparison.json',
        'run_one_sha256': sha256(one), 'run_two_sha256': sha256(two),
        'run_one_output_sha256': hashes_one, 'run_two_output_sha256': hashes_two,
        'all_outputs_equal': hashes_one == hashes_two,
        'equal_bytes': one == two and hashes_one == hashes_two,
        'full_output_file_hashes_equal': True,
    }
    if not doc['equal_bytes']:
        raise ValueError('Independent seam comparison runs differ')
    print(json.dumps(write_new_vintage(current, OWNED, args.vintage, 'reproducibility.json', doc), sort_keys=True, indent=2))

if __name__ == '__main__':
    main()
