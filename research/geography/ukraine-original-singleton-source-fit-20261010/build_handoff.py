"""Bind retained, unchanged scientific evidence into one complete original cohort.

This checks source custody, exact identity joins, conservative complete neighbor
exclusions and literal coordinate preservation. It does not rerun GIS or approve
current legal/physical truth, native cells, release integration or publication.
"""
import base64
import gzip
import hashlib
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = 'c28077da970ae39550e5edea790a266b060d3de5'
CID = 'physical-component:6fd25496ae4a7635eef229d0cfd1eb8dc7d9c10c252d3255fe8d42d186e706d1'
BATCH = 'gap-operational-batch:b139696d47c4fa03f8f73dbe'
TARGET = 'gb:UKR:ADM2:74538382B77535249747568'
NEIGHBOR = 'gb:HUN:ADM2:29324351B39716599464162'
PINS = []

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

HEAD = git('rev-parse', 'HEAD').decode().strip()

def read(name, commit=HEAD):
    raw = git('show', commit + ':' + name)
    assert len(raw) < 32 * 1024 ** 2
    PINS.append({'commit': commit, 'path': name, 'bytes': len(raw), 'sha256': sha(raw)})
    return raw

def own(name):
    return read((HERE / name).relative_to(ROOT).as_posix())

def same_ring(a, b):
    assert a[0] == a[-1] and b[0] == b[-1]
    a, b = a[:-1], b[:-1]
    return len(a) == len(b) and any(a == b[i:] + b[:i] for i in range(len(b)))

def same_polygon(a, b):
    return a['type'] == b['type'] == 'Polygon' and len(a['coordinates']) == len(b['coordinates']) and all(same_ring(x, y) for x, y in zip(a['coordinates'], b['coordinates']))

def empty(operation):
    geometry = operation['geometry']
    return operation['kind'] == 'empty' and operation['area_m2'] == operation['planar_area'] == 0 and (geometry.get('coordinates') == [] or geometry.get('geometries') == [])

def bounds(geometry):
    points = []
    def visit(value):
        if isinstance(value, list) and len(value) >= 2 and all(isinstance(x, (int, float)) for x in value):
            points.append(value)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(geometry['coordinates'])
    return [min(x[0] for x in points), min(x[1] for x in points), max(x[0] for x in points), max(x[1] for x in points)]

def main():
    assert pathlib.Path(__file__).read_bytes() == own('build_handoff.py')
    destination = HERE / 'vintages/source-handoff-002'
    assert not destination.exists()
    for parent in [destination, *destination.parents]:
        assert not parent.is_symlink()
        if parent == ROOT:
            break
    raw = own('vintages/physical-restoration-001/original-component.json')
    candidate = json.loads(raw)
    assert candidate['id'] == CID and sha(raw) == 'acd61551d2dbc9b6925e6d8c2d17cb210a6dcf6f3d80bbbadb64951660e3b746'
    physical = json.loads(own('vintages/physical-restoration-001/physical-record.json'))
    native = json.loads(own('vintages/physical-restoration-001/queried-source-metadata.json'))
    restoration = json.loads(own('vintages/physical-restoration-001/receipt.json'))
    for name, selected_rows in [('components-030.jsonl.gz', [physical]), ('sources-000.jsonl.gz', native)]:
        encoded = own('vintages/physical-restoration-001/' + name)
        descriptor = next(row for row in restoration['restorations'] if row['path'] == name)
        assert len(encoded) == descriptor['whole_original_bytes'] and sha(encoded) == descriptor['whole_original_sha256']
        decoded = gzip.decompress(encoded)
        assert len(decoded) == descriptor['decoded_bytes'] and sha(decoded) == descriptor['decoded_sha256']
        rows = [json.loads(line) for line in decoded.splitlines()]
        key = 'component_id' if name.startswith('components') else 'id'
        for selected in selected_rows:
            originals = [row for row in rows if row[key] == selected[key]]
            assert originals == [selected]
    serial = json.loads(own('vintages/serialization-proof-001/result.json'))
    source = json.loads(own('vintages/consumed-source-probe-001/result.json'))
    old_target = json.loads(own('vintages/current-target-probe-001/result.json'))
    current = json.loads(own('vintages/current-neighbor-bindings-001/result.json'))
    registry = json.loads(read('data/administrative-sources.json', BASE))
    recipe = read('scripts/administrative.py', BASE)
    assert sha(recipe) == 'd9df8285f1c270856a8e79b95636cf4b8d8496f48b30348a1e4d6d20619b2f22'
    catalogue = json.loads(read('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json', BASE))
    comparison_path = 'coordination/engineering/global-source-comparisons-a-001-20261006/scientific/components-003.json.gz'
    comparison_rows = json.loads(gzip.decompress(read(comparison_path, BASE)))
    matches = [row for row in comparison_rows if row['component'] == CID]
    assert len(matches) == 1
    comparison = matches[0]
    assert physical['component_id'] == source['component'] == old_target['component'] == current['component_id'] == CID
    assert physical['candidate_feature_sha256'] == source['component_feature_sha256'] == comparison['full_component_feature_sha256'] == sha(raw)
    assert physical['candidate_geometry_sha256'] == source['component_geometry_sha256'] == comparison['component_geometry_sha256'] == sha(canonical(candidate['geometry']))
    assert physical['status'] == 'mapped-land-support'
    support = physical['complete_support']
    assert same_polygon(candidate['geometry'], support['mapped_land_support']['geometry'])
    assert all(empty(support[key]) for key in ['mapped_inland_water_support', 'outside_mapped_L1_context', 'contradictory_land_water_support', 'missing_reconstruction', 'extra_reconstruction'])
    assert all(empty(value) for value in support['hierarchy_disagreements'].values())
    assert len(native) == len(physical['query_relations']) == 1
    query = physical['query_relations'][0]
    assert native[0]['id'] == query['source_id'] == 0
    assert native[0]['record_sha256'] == query['source_record_sha256'] and native[0]['decoded_pointset_binary64_sha256'] == query['source_pointset_sha256']
    assert query['source_level'] == 1 and query['source_covers_candidate'] and not query['disjoint'] and query['intersects'] and query['status'] == 'checked' and query['container_chain_issues'] == []
    expected_box = bounds(candidate['geometry'])
    consumed = []
    for code in ['UKR', 'HUN']:
        key = 'gb:' + code + ':ADM2'
        source_raw = own('inputs/geoBoundaries-' + code + '-ADM2_simplified.geojson')
        product = next(row for row in catalogue['products'] if row['key'] == key)
        assert sha(source_raw) == product['original_sha256'] == registry[key]['sha256']
        features = json.loads(source_raw)['features']
        assert len(features) == product['feature_count']
        hits = []
        for ordinal, feature in enumerate(features):
            b = bounds(feature['geometry'])
            if b[0] <= expected_box[2] and b[2] >= expected_box[0] and b[1] <= expected_box[3] and b[3] >= expected_box[1]:
                hits.append((ordinal, feature))
        original_query = next(row for row in comparison['whole_product_bbox_queries'] if row['source_id'] == key)
        assert [row[0] for row in hits] == original_query['complete_bbox_candidate_indices'] and len(features) == original_query['whole_product_feature_count']
        for ordinal, feature in hits:
            retained = next(row for row in comparison['feature_intersections'] if row['binding']['source_id'] == key and row['binding']['feature_index'] == ordinal)
            assert sha(canonical(feature)) == retained['binding']['feature_sha256']
            assert sha(canonical(feature['geometry'])) == retained['binding']['geometry_sha256']
        consumed.append({'source_id': key, 'whole_bytes': len(source_raw), 'whole_sha256': sha(source_raw), 'feature_count': len(features), 'complete_bbox_indices': [row[0] for row in hits], 'catalogue_record': product, 'registry_record': registry[key]})
    assert source['predicates']['source_target_covers_whole_component'] and source['predicates']['unsupported_remainder_empty'] and source['predicates']['source_intersection_symmetric_difference_empty'] and source['predicates']['only_target_positive_area_source']
    assert comparison['status'] == 'one-compatible-recorded-subject-uniquely-covers-component' and comparison['uniquely_covering_compatible_recorded_subject']['id'] == TARGET
    positive = [row for row in comparison['feature_intersections'] if row['intersection']['planar_area_coordinate_units_squared'] > 0]
    assert len(positive) == 1 and positive[0]['source_feature_covers_entire_component'] and same_polygon(candidate['geometry'], positive[0]['intersection']['geometry'])
    assert len(current['candidate_neighbors']) == 2 and {row['feature']['id'] for row in current['candidate_neighbors']} == {TARGET, NEIGHBOR}
    targets = {row['feature']['id']: row for row in current['candidate_neighbors']}
    target = targets[TARGET]['feature']
    assert targets[TARGET]['certificate_entry'][6] == old_target['target']['feature_sha256']
    assert targets[NEIGHBOR]['certificate_entry'][6] == old_target['neighbor']['feature_sha256']
    assert target['properties'] == old_target['target']['properties']
    assert old_target['conditions']['target_candidate_overlap_zero_area'] and not old_target['conditions']['target_already_covers_candidate'] and old_target['conditions']['named_HUN_neighbor_positive_overlap_absent']
    assert all(not row['candidate_bbox_intersects'] for row in current['additive_geometry_screen'])
    assert not old_target['conditions']['gain_equals_candidate_literal_empty_symmetric_difference']
    payload = {'component_id': CID, 'candidate_feature_sha256': sha(raw), 'candidate_geometry_sha256': sha(canonical(candidate['geometry'])), 'target_stable_location_id': TARGET, 'unsupported_candidate_remainder_included': False, 'source_supported_intersection_fragments': [{'intersection_geometry': positive[0]['intersection']['geometry']}], 'target_current_feature': {'feature_sha256': old_target['target']['feature_sha256'], 'geometry_sha256': targets[TARGET]['certificate_entry'][7], 'parent_id': target['properties']['parent_id']}}
    case = {'component_id': CID, 'original_candidate_feature': candidate, 'retained_payload': payload, 'retained_source_operation_row': {'source_comparison_record': comparison, 'positive_area_recorded_source_subject_ids': [TARGET], 'positive_area_source_feature_intersections': [row['binding'] for row in positive]}}
    scope = {'scopeIds': [CID], 'original_batch_id': BATCH, 'original_batch_component_count': 1, 'candidate_source_native_bindings': [case], 'original_physical_comparison_bindings': [{'component_id': CID, 'physical_comparison': {'row': physical}, 'original_queried_source_metadata': [{'original_source_record_metadata': row} for row in native]}], 'original_candidate_canonical_bindings': [{'component_id': CID, 'feature_sha256': sha(raw), 'feature_bytes_base64': base64.b64encode(raw).decode(), 'derived_js_canonical_sha256': serial['derived_js_canonical_sha256']}], 'consumed_source_bindings': consumed, 'current_neighbor_binding': current, 'physical_restoration': restoration, 'constructor_disposition': {'ordinary_GEOS_union_gain_failed': True, 'literal_representation': 'Complete unchanged retained target plus the complete unchanged candidate primitive. No dissolve or coordinate normalization.', 'source_relative_premises_supported': True, 'source_admission_requires_independent_review': True, 'common_adapter_candidate_serialization_not_yet_admitted': True}, 'unknowns': ['Current physical or legal truth and source observation dates remain unapproved.', 'Native operator, zero-cell disposition, exact selected continuous integration, drawing/picking and release readback remain engineering work.'], 'original_failed_dissolve': old_target, 'actual_current_target': target, 'execution_commit': HEAD, 'consumed_inputs': PINS}
    assert sum(pin['bytes'] for pin in PINS) < 64 * 1024 ** 2
    destination.mkdir()
    (destination / 'source-handoff.json').write_bytes(canonical(scope))
    print(json.dumps({'component': CID, 'complete_original_batch_components': 1, 'source_relative_premises_supported': True, 'native_or_continuous_delivered': False, 'source_admitted': False, 'input_bytes': sum(pin['bytes'] for pin in PINS)}))

if __name__ == '__main__':
    main()
