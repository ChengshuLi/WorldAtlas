#!/usr/bin/env python3
"""Emit compact categorical detail tables plus one numeric count row per table."""
import csv
import io
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWN = ROOT / 'data/regional-review/argentina-adm2-source-revalidation-443'
OUT = OWN / 'findings'

# Exact raw schemas emitted by the measurement generators. An unreviewed field,
# including a newly added numeric measurement, cannot silently enter the packet.
RAW_FIELDS = {
    '2006-adm1-to-current-province-overlay.csv': (
        'current_id current_name old_intersecting_feature_count top_old_name top_old_shape_id '
        'top_old_share_of_current_area old_union_coverage_of_current union_symmetric_difference_share '
        'all_old_positive_overlaps').split(),
    'scoped-2020-to-current-georef-overlay.csv': (
        'atlas_id atlas_name atlas_parent_id source_2020_shape_id source_2020_name source_2020_admin_level '
        'source_2020_geometry_type source_2020_component_count source_2020_hole_count source_2020_valid '
        'old_area_km2_equal_area current_intersecting_feature_count top_current_georef_id top_current_name '
        'top_current_province top_current_category top_share_of_old_area current_union_coverage_of_old '
        'current_overlap_excess_share all_current_intersections same_normalized_name_candidate_count '
        'best_same_name_candidate_id best_same_name_candidate_province best_same_name_candidate_share_of_old_area '
        'best_same_name_candidate_symmetric_difference_share same_name_candidates over_1sqm_sliver_count '
        'top_five_current_hits interpretation').split(),
    'scoped-current-georef-positive-area-overlaps.csv': (
        'name_a province_a category_a name_b province_b category_b overlap_area_m2 georef_id_a georef_id_b '
        'scoped_subject_ids interpretation').split(),
    'scoped-multipart-components.csv': (
        'atlas_id atlas_name source_shape_id component_number component_count component_area_km2 '
        'interior_ring_count current_positive_area_intersections interpretation').split(),
    'scoped-parent-review.csv': (
        'atlas_parent_id atlas_parent_name official_name_check scoped_parent_review_children_from_443 '
        'direct_adm2_subjects_in_944 current_georef_exact_name_feature_id current_georef_exact_name_match_count '
        'current_georef_exact_feature_geometry_type 2006_adm1_source_id 2006_adm1_source_name '
        '2006_source_exact_name_match 2006_feature_count current_national_province_count '
        'old_2006_top_overlap_source_name old_2006_top_overlap_share_of_current '
        'old_2006_union_coverage_of_current assessment').split(),
    'scoped-2020-internal-overlaps.csv': (
        'shapeid_a name_a shapeid_b name_b intersection_area_m2 interpretation').split(),
}

DETAIL_FIELDS = {
    '2006-adm1-to-current-province-overlay.csv': (
        'current_id current_name old_intersection_class top_old_name top_old_shape_id top_overlap_class '
        'coverage_class symmetric_difference_class all_old_positive_overlaps').split(),
    'scoped-2020-to-current-georef-overlay.csv': (
        'atlas_id atlas_name atlas_parent_id source_2020_shape_id source_2020_name source_2020_admin_level '
        'source_2020_valid top_current_georef_id top_current_name top_current_province top_current_category '
        'all_current_intersections best_same_name_candidate_id best_same_name_candidate_province '
        'same_name_candidates top_five_current_hits interpretation geometry_class has_interior_rings '
        'source_area_class current_intersection_class top_share_class current_coverage_class overlap_excess_class '
        'same_name_candidate_class same_name_share_class same_name_difference_class').split(),
    'scoped-current-georef-positive-area-overlaps.csv': (
        'name_a province_a category_a name_b province_b category_b georef_id_a georef_id_b scoped_subject_ids '
        'interpretation overlap_size_class').split(),
    'scoped-multipart-components.csv': (
        'atlas_id atlas_name source_shape_id component_key current_positive_area_intersections interpretation '
        'component_area_class has_interior_ring').split(),
    'scoped-parent-review.csv': (
        'atlas_parent_id atlas_parent_name official_name_check current_georef_exact_name_feature_id '
        'current_georef_exact_feature_geometry_type 2006_adm1_source_id 2006_adm1_source_name '
        '2006_source_exact_name_match old_2006_top_overlap_source_name assessment children_in_443_class '
        'direct_subjects_in_944_class current_name_match old_top_overlap_class old_coverage_class').split(),
    'scoped-2020-internal-overlaps.csv': (
        'shapeid_a name_a shapeid_b name_b interpretation').split(),
}

CATEGORICAL_VALUES = {
    'old_intersection_class': {'none', 'one', 'multiple'},
    'top_overlap_class': {'<75%', '75–89.99%', '≥90%'},
    'coverage_class': {'<95%', '95–98.99%', '≥99%'},
    'symmetric_difference_class': {'≤1%', '>1–5%', '>5%'},
    'geometry_class': {'multipart', 'single-part'},
    'has_interior_rings': {'yes', 'no'},
    'source_area_class': {'<1,000 km²', '1,000–9,999 km²', '≥10,000 km²'},
    'current_intersection_class': {'none', 'one', 'multiple'},
    'top_share_class': {'<75%', '75–89.99%', '≥90%'},
    'current_coverage_class': {'<95%', '95–98.99%', '≥99%'},
    'overlap_excess_class': {'none', '<1%', '≥1%'},
    'same_name_candidate_class': {'none', 'unique', 'duplicate-name'},
    'same_name_share_class': {'<75%', '75–89.99%', '≥90%'},
    'same_name_difference_class': {'≤5%', '>5%'},
    'overlap_size_class': {'<1 hectare', '≥1 hectare'},
    'component_area_class': {'<0.1 km²', '0.1–<1 km²', '≥1 km²'},
    'has_interior_ring': {'yes', 'no'},
    'children_in_443_class': {'none', 'one', 'multiple'},
    'direct_subjects_in_944_class': {'none', 'one', 'multiple'},
    'current_name_match': {'yes', 'no'},
    'old_top_overlap_class': {'<75%', '75–89.99%', '≥90%'},
    'old_coverage_class': {'<95%', '95–98.99%', '≥99%'},
}


def validate_detail(filename, row):
    actual = set(row)
    expected = set(DETAIL_FIELDS[filename])
    if actual != expected:
        raise ValueError(f'{filename}: detail schema mismatch; unexpected={sorted(actual-expected)}, missing={sorted(expected-actual)}')
    for field, allowed in CATEGORICAL_VALUES.items():
        if field in row and row[field] not in allowed:
            raise ValueError(f'{filename}: {field} has non-categorical value {row[field]!r}')
    return row


def band(value, limits, names):
    value = float(value)
    for limit, name in zip(limits, names):
        if value < limit:
            return name
    return names[-1]


def roman(number):
    digits = ((10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I'))
    result = ''
    for value, glyph in digits:
        while number >= value:
            result += glyph
            number -= value
    return result


def category_row(filename, row):
    if filename not in RAW_FIELDS or set(row) != set(RAW_FIELDS[filename]):
        expected = set(RAW_FIELDS.get(filename, ()))
        actual = set(row)
        raise ValueError(f'{filename}: raw schema mismatch; unexpected={sorted(actual-expected)}, missing={sorted(expected-actual)}')
    if filename == '2006-adm1-to-current-province-overlay.csv':
        count = int(row.pop('old_intersecting_feature_count'))
        top = float(row.pop('top_old_share_of_current_area'))
        coverage = float(row.pop('old_union_coverage_of_current'))
        difference = float(row.pop('union_symmetric_difference_share'))
        row['old_intersection_class'] = 'none' if count == 0 else 'one' if count == 1 else 'multiple'
        row['top_overlap_class'] = band(top, (.75, .90), ('<75%', '75–89.99%', '≥90%'))
        row['coverage_class'] = band(coverage, (.95, .99), ('<95%', '95–98.99%', '≥99%'))
        row['symmetric_difference_class'] = band(difference, (.01, .05), ('≤1%', '>1–5%', '>5%'))
    elif filename == 'scoped-2020-to-current-georef-overlay.csv':
        row.pop('source_2020_component_count')
        row['geometry_class'] = 'multipart' if row.pop('source_2020_geometry_type') == 'MultiPolygon' else 'single-part'
        row['has_interior_rings'] = 'yes' if row.pop('source_2020_hole_count') else 'no'
        area = float(row.pop('old_area_km2_equal_area'))
        row['source_area_class'] = band(area, (1000, 10000), ('<1,000 km²', '1,000–9,999 km²', '≥10,000 km²'))
        count = int(row.pop('current_intersecting_feature_count'))
        row['current_intersection_class'] = 'none' if count == 0 else 'one' if count == 1 else 'multiple'
        share = float(row.pop('top_share_of_old_area'))
        row['top_share_class'] = band(share, (.75, .90), ('<75%', '75–89.99%', '≥90%'))
        coverage = float(row.pop('current_union_coverage_of_old'))
        row['current_coverage_class'] = band(coverage, (.95, .99), ('<95%', '95–98.99%', '≥99%'))
        excess = float(row.pop('current_overlap_excess_share'))
        row['overlap_excess_class'] = 'none' if excess <= 1e-9 else '<1%' if excess < .01 else '≥1%'
        count = int(row.pop('same_normalized_name_candidate_count'))
        row['same_name_candidate_class'] = 'none' if count == 0 else 'unique' if count == 1 else 'duplicate-name'
        share = float(row.pop('best_same_name_candidate_share_of_old_area'))
        row['same_name_share_class'] = band(share, (.75, .90), ('<75%', '75–89.99%', '≥90%'))
        difference = float(row.pop('best_same_name_candidate_symmetric_difference_share'))
        row['same_name_difference_class'] = '≤5%' if difference <= .05 else '>5%'
        row.pop('over_1sqm_sliver_count')
    elif filename == 'scoped-current-georef-positive-area-overlaps.csv':
        area = float(row.pop('overlap_area_m2'))
        row['overlap_size_class'] = '<1 hectare' if area < 10000 else '≥1 hectare'
    elif filename == 'scoped-multipart-components.csv':
        number = int(row.pop('component_number'))
        row.pop('component_count')
        row['component_key'] = roman(number)
        area = float(row.pop('component_area_km2'))
        row['component_area_class'] = band(area, (.1, 1), ('<0.1 km²', '0.1–<1 km²', '≥1 km²'))
        row['has_interior_ring'] = 'yes' if int(row.pop('interior_ring_count')) else 'no'
    elif filename == 'scoped-parent-review.csv':
        value = int(row.pop('scoped_parent_review_children_from_443'))
        row['children_in_443_class'] = 'none' if value == 0 else 'one' if value == 1 else 'multiple'
        value = int(row.pop('direct_adm2_subjects_in_944'))
        row['direct_subjects_in_944_class'] = 'none' if value == 0 else 'one' if value == 1 else 'multiple'
        value = int(row.pop('current_georef_exact_name_match_count'))
        row['current_name_match'] = 'yes' if value else 'no'
        row.pop('2006_feature_count')
        row.pop('current_national_province_count')
        value = float(row.pop('old_2006_top_overlap_share_of_current'))
        row['old_top_overlap_class'] = band(value, (.75, .90), ('<75%', '75–89.99%', '≥90%'))
        value = float(row.pop('old_2006_union_coverage_of_current'))
        row['old_coverage_class'] = band(value, (.95, .99), ('<95%', '95–98.99%', '≥99%'))
    elif filename == 'scoped-2020-internal-overlaps.csv':
        raise AssertionError('A positive-area historical overlap row appeared; inspect it before classification')
    return validate_detail(filename, row)


def main():
    files = [
        '2006-adm1-to-current-province-overlay.csv',
        'scoped-2020-to-current-georef-overlay.csv',
        'scoped-current-georef-positive-area-overlaps.csv',
        'scoped-multipart-components.csv',
        'scoped-parent-review.csv',
        'scoped-2020-internal-overlaps.csv',
    ]
    detail_counts = {}
    raw_rows_by_file = {}
    for filename in files:
        path = OUT / filename
        with path.open(encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != RAW_FIELDS[filename]:
                raise ValueError(f'{filename}: raw CSV header mismatch')
            raw_rows = [dict(row) for row in reader]
        raw_rows_by_file[filename] = raw_rows
        rows = [category_row(filename, dict(row)) for row in raw_rows]
        fields = ['record_type', 'record_count'] + DETAIL_FIELDS[filename]
        detail = [{'record_type': 'detail', 'record_count': '', **row} for row in rows]
        summary = {'record_type': 'summary', 'record_count': len(rows)}
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n', extrasaction='raise')
            writer.writeheader()
            writer.writerow({key: summary.get(key, '') for key in fields})
            writer.writerows(detail)
        detail_counts[filename] = len(detail)
        print(f'{filename}: {len(rows)} categorical detail rows')

    # Positive control exercises the emitted files and verifies exact detail schemas,
    # categorical classes and the one numeric count row against each actual row count.
    positive_ok = len(detail_counts) == 6
    for filename in files:
        with (OUT / filename).open(encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ['record_type', 'record_count'] + DETAIL_FIELDS[filename]:
                raise ValueError(f'{filename}: emitted CSV header mismatch')
            rows = list(reader)
        if not rows or rows[0]['record_type'] != 'summary' or int(rows[0]['record_count']) != detail_counts[filename]:
            raise ValueError(f'{filename}: invalid numeric summary row')
        for row in rows[1:]:
            if row['record_type'] != 'detail' or row['record_count'] != '':
                raise ValueError(f'{filename}: malformed detail row')
            validate_detail(filename, {key: row[key] for key in DETAIL_FIELDS[filename]})
    assert positive_ok
    (OUT / 'categorical-table-positive.json').write_text(
        json.dumps({'method_id': 'categorical-table-generation', 'kind': 'positive-control', 'outcome': 'passed',
                    'control': 'Six emitted tables match exact detail schemas, allowed categorical values and one numeric summary row per actual detail count.'}, indent=2) + '\n',
        encoding='utf-8')

    # Negative control mutates a real measurement row, serializes/re-reads it as CSV,
    # then requires the production categorizer to reject the unreviewed numeric column.
    filename = 'scoped-2020-to-current-georef-overlay.csv'
    raw_row = raw_rows_by_file[filename][0]
    mutated_fields = RAW_FIELDS[filename] + ['unreviewed_numeric_measurement']
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=mutated_fields, lineterminator='\n')
    writer.writeheader()
    writer.writerow({**raw_row, 'unreviewed_numeric_measurement': '0.123456789'})
    buffer.seek(0)
    mutated = next(csv.DictReader(buffer))
    try:
        category_row(filename, mutated)
    except ValueError as error:
        rejected = 'unreviewed_numeric_measurement' in str(error)
    else:
        rejected = False
    assert rejected, 'mutated measurement input was not rejected by production categorizer'
    (OUT / 'categorical-table-negative.json').write_text(
        json.dumps({'method_id': 'categorical-table-generation', 'kind': 'negative-control', 'outcome': 'passed',
                    'mutated_table': filename, 'mutated_column': 'unreviewed_numeric_measurement',
                    'rejection': 'production category_row rejected the mutated raw table schema'}, indent=2) + '\n',
        encoding='utf-8')


if __name__ == '__main__':
    main()
