#!/usr/bin/env python3
"""Bounded source and retained-result verification for issue #1424.

This reads immutable Git blobs at the declared baseline. It does not fetch,
rebuild, edit, or approve any source or geography product.
"""
import argparse
import gzip
import hashlib
import io
import json
import math
import pathlib
import platform
import struct
import subprocess
import sys
import zipfile

BASELINE = '69a5f97161c36611fc974b626c9666fdf2941a31'
ROUTE = 'coordination/engineering/global-actionability-routing-20261007'
PHYSICAL = 'coordination/engineering/global-physical-comparison-20261006'
CORPUS = 'coordination/engineering/original-geography-source-corpus-20261006'
PHYSICAL_SOURCE = 'coordination/engineering/global-physical-sources-20261006'
SUBJECTS = [
    'physical-component:721838ee1e1d6c3acde27742d49376d80aeea2a3818aff8ef006e4d407827ebb',
    'physical-component:854f216abedb0bc31b01c6cfa93a441c7aed86924b3331c0b61c72c2936733d3',
    'physical-component:10f89b3868b4e895d2339368b755f073a626d439640301111352521c9bc24b4b',
    'physical-component:6a0546bc1c627a174a8cf599f75d35bc9e6d023cc20da86326599465c5553346',
    'physical-component:2b39965dae96675fca4577dd52a5bfe9cc7e430f79dfa7089c919bd4ed616af8',
    'physical-component:7deb1a01865ea8f87256a5442ca03a55613d4187137d49c1342fdfe33573cb15',
    'physical-component:371f640e87dd9da0b20648ffcdadb479281917d49399982ba56eaf5801237bb7',
    'physical-component:abc8439a48b08d63bdd9f2c558a1b54af220f947d8377772e78401acb1b72481',
    'physical-component:cf77bf2034affdf3b9cf01618054901916271c0061bd6b79a9b57e7c22e1817d',
    'physical-component:8bce0affeeb72b155c7df58ba9138fd9cb40ed5134eb25332ef4fcb6c0335d78',
    'physical-component:5144bba87ee1f376f8a809bad0bce0b86a29418d83bb211779892346d4f6b7a2',
    'physical-component:aed8ce56171d9b7da8532f00404bbc07d547c4d75b5a73daefbd9f35290ff2c7',
]
SELECTED_FAMILIES = {
    'gap-source-batch:da01a18537aad7221b48c471',
    'gap-source-batch:cda72270fe02057af7bc959e',
    'gap-source-batch:8b0f3a4a12b1b53e8cdb8243',
    'gap-source-batch:0c1cdaad9f40381ff5391a6e',
    'gap-source-batch:26c50f1a932243cab76eb1d8',
    'gap-source-batch:e31c6e10338c57623af2d97d',
    'gap-source-batch:b0800cc5fbd19e035ee42a9a',
}
BATCH_IDS = {
    'gap-operational-batch:241e2ce0cd7b6be8a234558b',
    'gap-operational-batch:d192a3030ff44ad158d32916',
}
CANDIDATES = {
    'physical-component:721838ee1e1d6c3acde27742d49376d80aeea2a3818aff8ef006e4d407827ebb',
    'physical-component:854f216abedb0bc31b01c6cfa93a441c7aed86924b3331c0b61c72c2936733d3',
    'physical-component:10f89b3868b4e895d2339368b755f073a626d439640301111352521c9bc24b4b',
    'physical-component:6a0546bc1c627a174a8cf599f75d35bc9e6d023cc20da86326599465c5553346',
    'physical-component:2b39965dae96675fca4577dd52a5bfe9cc7e430f79dfa7089c919bd4ed616af8',
    'physical-component:abc8439a48b08d63bdd9f2c558a1b54af220f947d8377772e78401acb1b72481',
    'physical-component:8bce0affeeb72b155c7df58ba9138fd9cb40ed5134eb25332ef4fcb6c0335d78',
    'physical-component:aed8ce56171d9b7da8532f00404bbc07d547c4d75b5a73daefbd9f35290ff2c7',
}
CONTACTS = {
    '17018030B21762340724861': 'Central',
    '17018030B36628097040544': 'Isabel',
    '17018030B43755880178831': 'Makira',
    '17018030B68013150931387': 'Choiseul',
    '17018030B8659224027401': 'Western',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def git_blob(repo, path):
    return subprocess.check_output(['git', '-C', str(repo), 'show', f'{BASELINE}:{path}'])


def load_json(raw):
    return json.loads(raw)


def descriptor(path, raw, role=None):
    out = {'path': path, 'bytes': len(raw), 'sha256': digest(raw), 'hash_kind': 'file-bytes'}
    if role:
        out['role'] = role
    if path.endswith('.gz'):
        uncompressed = gzip.decompress(raw)
        out.update(uncompressed_bytes=len(uncompressed), uncompressed_sha256=digest(uncompressed))
    return out


def route_bodies(repo):
    root = f'{ROUTE}/results'
    report_raw = git_blob(repo, f'{root}/report.json')
    report = load_json(report_raw)
    bodies = {}
    input_raw = {f'{root}/report.json': report_raw}
    for body in report['complete_whole_raw_bodies']:
        if body['name'] not in ('components', 'families', 'batches', 'admin-bindings'):
            continue
        pieces = []
        for ordinal, part in enumerate(body['parts']):
            path = f"{root}/{body['name']}-{ordinal:03d}.bin.gz"
            need(part['path'] == path.split('/')[-1], 'Route result part order/name mismatch')
            raw = git_blob(repo, path)
            need(len(raw) == part['bytes'] and digest(raw) == part['sha256'], f'Route part bytes mismatch: {path}')
            decoded = gzip.decompress(raw)
            need(len(decoded) == part['uncompressed_bytes'] and digest(decoded) == part['uncompressed_sha256'],
                 f'Route decoded part mismatch: {path}')
            pieces.append(decoded)
            input_raw[path] = raw
        whole = b''.join(pieces)
        need(len(whole) == body['bytes'] and digest(whole) == body['sha256'],
             f'Complete route body mismatch: {body["name"]}')
        bodies[body['name']] = [load_json(line) for line in whole.splitlines()] if body['format'] == 'jsonl' else load_json(whole)
    return report, bodies, input_raw


def transport_data(repo):
    path = f'{PHYSICAL}/results/transport-map.json'
    raw = git_blob(repo, path)
    mapping = load_json(raw)
    entries = {}
    for item in mapping['entries']:
        entries[(item['kind'], item['delivered']['path'])] = item['delivered']
    return mapping, entries, {path: raw}


def native_source_subset(repo, source_rows, wanted_sources, source_record_hashes):
    """Restore only the queried native GSHHG records from the retained original ZIP."""
    catalogue_path = f'{PHYSICAL_SOURCE}/catalogue.json'
    catalogue_raw = git_blob(repo, catalogue_path)
    catalogue = load_json(catalogue_raw)
    archive_parts = []
    source_inputs = {catalogue_path: catalogue_raw}
    for part in catalogue['parts']:
        raw = git_blob(repo, part['path'])
        need(len(raw) == part['bytes'] and digest(raw) == part['sha256'],
             f'Original GSHHG archive part mismatch: {part["path"]}')
        archive_parts.append(raw)
        source_inputs[part['path']] = raw
    archive = b''.join(archive_parts)
    need(len(archive) == catalogue['original_bytes'] and digest(archive) == catalogue['original_sha256'],
         'Complete retained GSHHG original archive mismatch')
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        member = zipped.read(catalogue['member'])
    need(len(member) == catalogue['member_bytes'] and digest(member) == catalogue['member_sha256'],
         'Retained GSHHG native member mismatch')

    import numpy as np
    header_struct = struct.Struct('>3I4i2I2i')
    native_bytes = bytearray()
    indexed = []
    for key in sorted(wanted_sources):
        source = source_rows[key]['row']
        offset, size = source['native_offset'], source['native_record_bytes']
        record = member[offset:offset+size]
        need(len(record) == size == 44 + source['n'] * 8, f'Native record bounds mismatch: {key[0]}')
        values = header_struct.unpack(record[:44])
        need(list(values) == source['header_native_values'] and values[0] == key[0] and values[1] == source['n'],
             f'Native header/source row mismatch: {key[0]}')
        record_sha = digest(record)
        need(source_record_hashes.get(key) == {record_sha}, f'Native source-record hash mismatch: {key[0]}')
        raw_points = record[44:]
        native = np.frombuffer(raw_points, dtype='>i4').reshape(source['n'], 2)
        coordinates = native.astype(np.float64)
        coordinates *= 1.0e-6
        identity, count, flag, west = values[:4]
        seam = (flag >> 16) & 3
        threshold = 270000000 if source['ordinal'] == 0 else 180000000
        shifted = ((native[:, 0] > threshold) & bool(seam)) | (west > 180000000)
        coordinates[shifted, 0] -= 360.0
        if identity != 0 and identity != 4 and seam & 2:
            coordinates[coordinates[:, 0] < 0.0, 0] += 360.0
        pointset_sha = digest(coordinates.astype('>f8').tobytes(order='C'))
        need(pointset_sha == source['decoded_pointset_binary64_sha256'] == key[1],
             f'Native decoded pointset hash mismatch: {key[0]}')
        subset_offset = len(native_bytes)
        native_bytes.extend(record)
        indexed.append({'source_id': key[0], 'pointset_sha256': key[1],
            'source_record_sha256': record_sha, 'coordinate_bytes_sha256': digest(raw_points),
            'native_offset_in_member': offset, 'native_record_bytes': size,
            'subset_offset': subset_offset, 'subset_bytes': size})
    summary = {'archive_member': catalogue['member'], 'archive_bytes': catalogue['original_bytes'],
        'archive_sha256': catalogue['original_sha256'], 'native_member_bytes': len(member),
        'native_member_sha256': digest(member), 'restored_native_records': len(indexed)}
    return bytes(native_bytes), indexed, source_inputs, summary


def physical_record(repo, path, expected_sha, transport_entries, kind):
    name = pathlib.PurePosixPath(path).name
    receipt = transport_entries.get((kind, name))
    need(receipt is not None, f'Missing {kind} transport receipt for {name}')
    raw = git_blob(repo, f'{PHYSICAL}/results/{name}')
    need(len(raw) == receipt['bytes'] and digest(raw) == receipt['sha256'], f'Physical encoded file mismatch: {name}')
    decoded = gzip.decompress(raw)
    need(len(decoded) == receipt['uncompressed_bytes'] and digest(decoded) == receipt['uncompressed_sha256'],
         f'Physical decoded file mismatch: {name}')
    found = []
    for line in decoded.splitlines(keepends=True):
        obj = load_json(line)
        if (kind == 'components' and obj.get('component_id') in set(batch_component_ids)) or (
                kind == 'sources' and (obj.get('id'), obj.get('decoded_pointset_binary64_sha256')) in wanted_sources):
            if kind == 'components' and obj.get('component_id') in set(batch_component_ids):
                found.append((obj, line))
            elif kind == 'sources' and (obj.get('id'), obj.get('decoded_pointset_binary64_sha256')) in wanted_sources:
                found.append((obj, line))
    return raw, found


# Set only while the deterministic extraction is running.
batch_component_ids = set()
wanted_sources = set()


def geometry_contacts(repo):
    sys.path.insert(0, str(repo / 'scripts'))
    sys.path.insert(0, str(repo / 'scripts/evidence'))
    from shapely.geometry import shape, Polygon
    from shapely.affinity import translate
    import shapely
    import pyproj
    from geometry import land_area_m2, METHOD

    payload_path = f'{CORPUS}/payloads/gb-SLB-ADM1-000.bin.gz'
    payload = git_blob(repo, payload_path)
    decoded = gzip.decompress(payload)
    source_fc = load_json(decoded)
    current_fc = load_json(git_blob(repo, 'data/geography/part-22.json'))
    source_features = {f['properties']['shapeID']: f for f in source_fc['features']}
    current_features = {f['properties']['metadata']['original_id']: f for f in current_fc['features']
                        if f.get('properties', {}).get('metadata', {}).get('source_id') == 'gb:SLB:ADM1'}
    need(len(source_features) == 10 and len(current_fc['features']) == 1500, 'Administrative feature inventory differs')
    rows = []
    for shape_id, expected_name in CONTACTS.items():
        src = source_features.get(shape_id)
        cur = current_features.get(shape_id)
        need(src is not None and cur is not None, f'Missing contact feature {shape_id}')
        need(src['properties']['shapeName'] == expected_name and cur['properties']['name'] == expected_name,
             f'Contact name mismatch for {shape_id}')
        need(cur['id'] == f'gb:SLB:ADM1:{shape_id}', f'Current ADM1 identity mismatch for {shape_id}')
        sg, cg = shape(src['geometry']), shape(cur['geometry'])
        need(sg.is_valid and cg.is_valid, f'Invalid retained contact geometry: {shape_id}')
        equal = sg.equals(cg)
        diff = sg.symmetric_difference(cg)
        delta = 0.0 if diff.is_empty else land_area_m2(diff)
        rows.append({'shape_id': shape_id, 'name': expected_name, 'current_id': cur['id'],
                     'source_geometry_type': sg.geom_type, 'current_geometry_type': cg.geom_type,
                     'source_valid': bool(sg.is_valid), 'current_valid': bool(cg.is_valid),
                     'topologically_equal': bool(equal), 'symmetric_difference_area_m2': delta,
                     'symmetric_difference_area_km2': delta / 1_000_000})
    need(all(not row['topologically_equal'] and row['symmetric_difference_area_m2'] > 0 for row in rows),
         'Expected source/current discrepancy is not present for all five contacts')

    same = Polygon([(156.0, -9.0), (156.01, -9.0), (156.01, -9.01), (156.0, -9.01), (156.0, -9.0)])
    same_diff = same.symmetric_difference(same)
    positive = {'method_id': 'slb-adm1-geometry-discrepancy', 'kind': 'positive-control',
                'outcome': 'passed', 'control': 'Identical valid input polygons have a zero symmetric difference.',
                'observed_zero_area': bool(same_diff.is_empty)}
    moved = translate(same, xoff=0.001)
    moved_area = land_area_m2(same.symmetric_difference(moved))
    negative = {'method_id': 'slb-adm1-geometry-discrepancy', 'kind': 'negative-control',
                'outcome': 'passed', 'control': 'A known 0.001 degree longitude translation produces a positive difference.',
                'observed_difference_area_m2': moved_area}
    need(positive['observed_zero_area'] and moved_area > 0, 'Geometry controls failed')
    runtime = {'python': platform.python_version(), 'shapely': shapely.__version__,
               'geos': shapely.geos_version_string, 'pyproj': pyproj.__version__}
    return rows, positive, negative, METHOD, runtime, payload, decoded


def build(repo, output_dir, compare_dir=None):
    global batch_component_ids, wanted_sources
    output_names = ('batch-context.json', 'native-source-records.bin', 'assessment.json',
                    'geometry-positive-control.json', 'geometry-negative-control.json')
    if compare_dir is None:
        output_dir.mkdir(parents=True, exist_ok=True)
        need(not any((output_dir / name).exists() for name in output_names),
             'Refusing to overwrite generated evidence; choose a fresh output directory or use --compare-dir')
    report, bodies, route_inputs = route_bodies(repo)
    family_by_id = {row['id']: row for row in bodies['families']}
    batch_by_id = {row['id']: row for row in bodies['batches']}
    component_by_id = {row['component']: row for row in bodies['components']}
    need(BATCH_IDS <= set(batch_by_id), 'Both complete operational batches are missing')
    batches = [batch_by_id[x] for x in sorted(BATCH_IDS)]
    expected_batch_sizes = {
        'gap-operational-batch:241e2ce0cd7b6be8a234558b': (15, 25),
        'gap-operational-batch:d192a3030ff44ad158d32916': (13, 20),
    }
    for batch in batches:
        need((len(batch['complete_fine_family_ids']), len(batch['complete_component_ids'])) ==
             expected_batch_sizes[batch['id']], f'Complete operational batch roster differs: {batch["id"]}')
    batch_family_ids = {fid for batch in batches for fid in batch['complete_fine_family_ids']}
    batch_component_ids = {cid for batch in batches for cid in batch['complete_component_ids']}
    need((len(batch_family_ids), len(batch_component_ids)) == (28, 45), 'Full batch roster count mismatch')
    need(SELECTED_FAMILIES <= batch_family_ids and set(SUBJECTS) <= batch_component_ids,
         'Selected cohort is not contained in complete operational batches')
    family_rows = {fid: family_by_id[fid] for fid in sorted(batch_family_ids)}
    component_rows = {cid: component_by_id[cid] for cid in sorted(batch_component_ids)}
    need(len(family_rows) == 28 and len(component_rows) == 45, 'Missing full batch family/component rows')
    scoped_components = {cid: component_by_id[cid] for cid in SUBJECTS}
    scoped_families = {fid: family_by_id[fid] for fid in sorted(SELECTED_FAMILIES)}
    need(set(scoped_components) == set(SUBJECTS) and set(scoped_families) == SELECTED_FAMILIES,
         'Exact selected rows differ from issue scope')
    need(all(component_rows[cid]['family'] in batch_family_ids for cid in batch_component_ids),
         'Component-to-family handoff mismatch')
    need(all(len(family_rows[fid]['complete_component_ids']) == family_rows[fid]['component_count']
             for fid in batch_family_ids), 'Incomplete family component context')

    # Preserve all original admin-binding rows in both selected operational batches.
    admin_rows = []
    for row in bodies['admin-bindings']:
        if any(cid in json.dumps(row, ensure_ascii=False) for cid in batch_component_ids):
            admin_rows.append(row)

    transport, transport_entries, physical_inputs = transport_data(repo)
    physical_rows = {}
    physical_file_paths = sorted({row['whole_physical_containing_file'] for row in component_rows.values()})
    for path in physical_file_paths:
        raw, found = physical_record(repo, path, None, transport_entries, 'components')
        physical_inputs[f'{PHYSICAL}/results/{pathlib.PurePosixPath(path).name}'] = raw
        for obj, line in found:
            cid = obj['component_id']
            if cid in batch_component_ids:
                need(digest(line) == component_rows[cid]['whole_physical_row_sha256'],
                     f'Physical row pointer mismatch: {cid}')
                need(cid not in physical_rows, f'Duplicate physical row: {cid}')
                physical_rows[cid] = obj
    need(set(physical_rows) == batch_component_ids, 'Full batch physical result rows are incomplete')
    wanted_sources = {(relation['source_id'], relation['source_pointset_sha256'])
                      for row in physical_rows.values() for relation in row['query_relations']}
    source_rows = {}
    source_files = sorted(name for kind, name in transport_entries if kind == 'sources')
    for name in source_files:
        raw, found = physical_record(repo, name, None, transport_entries, 'sources')
        physical_inputs[f'{PHYSICAL}/results/{name}'] = raw
        for obj, line in found:
            key = (obj['id'], obj['decoded_pointset_binary64_sha256'])
            if key in wanted_sources:
                source_rows[key] = {'row': obj, 'line_sha256': digest(line), 'path': name}
    need(set(source_rows) == wanted_sources, 'A native source pointset row is missing or ambiguous')
    source_pointer_checks = 0
    source_record_hashes = {}
    for cid, row in physical_rows.items():
        for relation in row['query_relations']:
            source = source_rows[(relation['source_id'], relation['source_pointset_sha256'])]
            need(relation['source_pointset_sha256'] == source['row']['decoded_pointset_binary64_sha256'],
                 f'Native source pointset mismatch: {cid}')
            need(len(relation.get('source_record_sha256', '')) == 64 and
                 all(ch in '0123456789abcdef' for ch in relation['source_record_sha256']),
                 f'Invalid retained native source-record hash pointer: {cid}/{relation["source_id"]}')
            source_record_hashes.setdefault((relation['source_id'], relation['source_pointset_sha256']), set()).add(
                relation['source_record_sha256'])
            source_pointer_checks += 1

    dispositions = []
    for cid in SUBJECTS:
        route = scoped_components[cid]
        physical = physical_rows[cid]
        support = physical['complete_support']
        land = support['mapped_land_support']['area_m2']
        outside = support['outside_mapped_L1_context']['area_m2']
        water = support['mapped_inland_water_support']['area_m2']
        contradiction = support['contradictory_land_water_support']['area_m2']
        if cid in CANDIDATES:
            need(land > 0 and outside == 0 and water == 0 and contradiction == 0,
                 f'Compatible candidate retained support differs: {cid}')
            disposition = 'candidate-fully-covered-by-retained-GSHHG-L1-land-pointset'
        elif land > 0 and outside > 0:
            disposition = 'noncandidate-mixed-retained-L1-and-outside-support'
        else:
            need(land == 0 and outside > 0, f'Noncandidate outside-L1 classification differs: {cid}')
            disposition = 'noncandidate-outside-retained-L1-context'
        need(route['physical_status'] == physical['status'] and
             physical['physical_status'] == 'unknown-source-fitness-and-observation-date',
             f'Unknown physical source status lost: {cid}')
        dispositions.append({'component_id': cid, 'family_id': route['family'],
            'compatible_candidate': cid in CANDIDATES, 'disposition': disposition,
            'physical_status': physical['physical_status'],
            'mapped_land_support_m2': land, 'outside_mapped_L1_context_m2': outside,
            'mapped_inland_water_support_m2': water,
            'contradictory_land_water_support_m2': contradiction,
            'source_ids': sorted({q['source_id'] for q in physical['query_relations']}),
            'source_pointset_hashes': sorted({q['source_pointset_sha256'] for q in physical['query_relations']}),
            'source_record_hashes': sorted({q['source_record_sha256'] for q in physical['query_relations']}),
            'whole_physical_row_sha256': route['whole_physical_row_sha256']})
    need(sum(x['compatible_candidate'] for x in dispositions) == 8, 'Candidate count mismatch')
    mixed = sorted(x['component_id'] for x in dispositions if x['disposition'].endswith('mixed-retained-L1-and-outside-support'))
    outside_only = sorted(x['component_id'] for x in dispositions if x['disposition'].endswith('outside-retained-L1-context'))
    need(len(mixed) == 2 and len(outside_only) == 2, 'Four sibling physical classes mismatch')

    contact_rows, positive, negative, geom_method, geom_runtime, payload, source_fc_bytes = geometry_contacts(repo)
    source_registry = load_json(git_blob(repo, 'data/administrative-sources.json'))['gb:SLB:ADM1']
    catalogue = load_json(git_blob(repo, f'{CORPUS}/catalogue.json'))
    product = next(x for x in catalogue['products'] if x['key'] == 'gb:SLB:ADM1')
    custody = load_json(git_blob(repo, f'{CORPUS}/complete-custody-validity.json'))
    custody_product = next(x for x in custody['rows'] if x['key'] == 'gb:SLB:ADM1')
    need(source_registry['boundaryYearRepresented'] == '2021' and source_registry['admUnitCount'] == '10',
         'Source registry year/count differs')
    need(product['original_bytes'] == len(source_fc_bytes) and product['original_sha256'] == digest(source_fc_bytes),
         'Source catalogue payload identity differs')
    need(custody_product['complete_features'] == 10 and custody_product['original_sha256'] == digest(source_fc_bytes),
         'Source custody receipt differs')

    native_records, native_record_index, archive_inputs, archive_summary = native_source_subset(
        repo, source_rows, wanted_sources, source_record_hashes)
    physical_inputs.update(archive_inputs)

    candidate_area = math.fsum(scoped_components[cid]['measured_fragment_area_sum_m2'] or 0 for cid in CANDIDATES)
    context = {
        'version': 1, 'issue': 1424, 'baseline_commit': BASELINE,
        'batches': batches,
        'families': list(family_rows.values()),
        'components': list(component_rows.values()),
        'admin_bindings': admin_rows,
        'physical_result_rows': [physical_rows[cid] for cid in sorted(batch_component_ids)],
        'native_source_rows': [{'source_id': key[0], 'pointset_sha256': key[1],
                                'row_sha256': value['line_sha256'], 'source_shard': value['path'],
                                'row': value['row']} for key, value in sorted(source_rows.items())],
        'native_source_records': native_record_index,
        'integrity': {'route_body_hashes_verified': ['components', 'families', 'batches', 'admin-bindings'],
                      'complete_family_rows': len(family_rows), 'complete_component_rows': len(component_rows),
                      'physical_rows': len(physical_rows), 'native_source_rows': len(source_rows),
                      'native_source_pointset_joins': source_pointer_checks,
                      'native_source_archive': archive_summary,
                      'transport_map_components': transport['complete_components'],
                      'transport_map_sources': transport['complete_sources']}}
    analysis = {
        'version': 1, 'issue': 1424, 'baseline_commit': BASELINE,
        'classification_scope': 'Seven selected complete families only; full batch rows retained as context.',
        'counts': {'scoped_families': len(scoped_families), 'scoped_components': len(dispositions),
                   'compatible_candidates': len(CANDIDATES), 'noncandidate_siblings': len(dispositions)-len(CANDIDATES),
                   'shared_admin_contacts': len(contact_rows), 'context_batch_families': len(family_rows),
                   'context_batch_components': len(component_rows), 'context_physical_rows': len(physical_rows),
                   'context_native_source_rows': len(source_rows), 'context_admin_binding_rows': len(admin_rows),
                   'native_source_pointset_joins': source_pointer_checks},
        'source_product': {'id': 'gb:SLB:ADM1', 'name': 'Solomon Islands ADM1',
            'url': source_registry['simplifiedGeometryGeoJSON'], 'recorded_product_commit': '9469f09',
            'represented_year': source_registry['boundaryYearRepresented'],
            'source_data_update_date': source_registry['sourceDataUpdateDate'], 'build_date': source_registry['buildDate'],
            'effective_date': 'unknown', 'crs': 'urn:ogc:def:crs:OGC:1.3:CRS84',
            'feature_count': 10, 'compressed_bytes': len(payload), 'compressed_sha256': digest(payload),
            'decoded_bytes': len(source_fc_bytes), 'decoded_sha256': digest(source_fc_bytes),
            'source_credit': source_registry['boundarySource'], 'license_as_recorded': source_registry['boundaryLicense'],
            'derivative_terms': 'CC BY 4.0 attribution per retained geoBoundaries statement; underlying Natural Earth Public Domain metadata preserved, particulars not independently verified.'},
        'contacts': contact_rows,
        'source_current_geometry_method': {'helper': geom_method, 'interpreted_edges': 'WGS84 straight source edges',
             'comparison': 'topological equality and symmetric-difference area; diagnostic only', 'runtime': geom_runtime},
        'physical_source': {'id': 'GSHHG 2.3.7', 'release_date': '2017-06-15',
            'observation_dates': 'heterogeneous/unknown for these records',
            'license_evidence': {'retained_LICENSE.TXT': 'LGPL v3 or later',
                'official_GSHHG_page': 'LGPL v3 or any earlier version',
                'interpretation': 'Preserve the differing version wording; no legal interpretation made.'},
            'results_source_ids': sorted({key[0] for key in source_rows}),
            'pointset_source_rows': len(source_rows), 'scope_source_ids': sorted({q['source_id'] for cid in SUBJECTS for q in physical_rows[cid]['query_relations']}),
            'scope_native_source_rows': len({(q['source_id'],q['source_pointset_sha256']) for cid in SUBJECTS for q in physical_rows[cid]['query_relations']}),
            'all_scoped_pointsets_resolved': True,
            'original_native_archive_sha256': archive_summary['archive_sha256'],
            'native_member_sha256': archive_summary['native_member_sha256'],
            'native_record_subset_path': 'native-source-records.bin',
            'native_record_subset_bytes': len(native_records),
            'native_record_subset_sha256': digest(native_records),
            'candidate_total_area_m2': candidate_area,
            'limits': ['Release date is not an observation date.', 'Mapped land support is relative to this retained pointset, not legal boundary, physical-land truth, dry-land status, or ownership.', 'Shoreline registration, source precision, seasonal wetness and unrecorded river widths remain unresolved.', 'Original source license files differ in LGPL version wording; no legal interpretation is made.']},
        'components': dispositions,
        'batch_context_path': 'batch-context.json',
        'batch_context_sha256': None,
        'limits': ['The source/current geometry difference does not identify which geometry is correct.',
            'The source alone does not establish legal authority, effective boundary date, land/water truth, or source suitability at 202 m² scale.',
            'No public source download or broad imagery inspection was performed.',
            'Full batch context is retained; classification conclusions are limited to the 12 issue subjects and five named contacts.']}

    context_path = output_dir / 'batch-context.json'
    context_bytes = (json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()
    analysis['batch_context_sha256'] = digest(context_bytes)
    generated = {
        'batch-context.json': context_bytes,
        'native-source-records.bin': native_records,
        'assessment.json': (json.dumps(analysis, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode(),
        'geometry-positive-control.json': (json.dumps(positive, ensure_ascii=False, indent=2)+'\n').encode(),
        'geometry-negative-control.json': (json.dumps(negative, ensure_ascii=False, indent=2)+'\n').encode(),
    }
    if compare_dir is not None:
        for name, expected in generated.items():
            actual_path = compare_dir / name
            need(actual_path.is_file() and actual_path.read_bytes() == expected,
                 f'Reproduction differs from retained evidence: {actual_path}')
    else:
        for name, contents in generated.items():
            with (output_dir / name).open('xb') as stream:
                stream.write(contents)
    return analysis, context, route_inputs, physical_inputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[2])
    parser.add_argument('--out-dir', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    parser.add_argument('--compare-dir', type=pathlib.Path,
                        help='Compare regenerated outputs with an existing evidence directory without writing files')
    args = parser.parse_args()
    analysis, context, route_inputs, physical_inputs = build(args.repo, args.out_dir, args.compare_dir)
    print(json.dumps({'status':'passed', 'baseline_commit':BASELINE, 'scoped_components':analysis['counts']['scoped_components'],
        'context_families':analysis['counts']['context_batch_families'], 'context_components':analysis['counts']['context_batch_components'],
        'context_physical_rows':analysis['counts']['context_physical_rows'], 'native_source_rows':analysis['counts']['context_native_source_rows'],
        'context_admin_bindings':analysis['counts']['context_admin_binding_rows'],
        'candidate_total_area_m2':analysis['physical_source']['candidate_total_area_m2'],
        'contact_geometry_differences_m2':[x['symmetric_difference_area_m2'] for x in analysis['contacts']]}, allow_nan=False))


if __name__ == '__main__':
    main()
