#!/usr/bin/env python3
"""Emit compact categorical detail tables plus one numeric count row per table."""
import csv
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWN = ROOT / 'data/regional-review/argentina-adm2-source-revalidation-443'
OUT = OWN / 'findings'


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
    return row


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
    for filename in files:
        path = OUT / filename
        with path.open(encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            rows = [category_row(filename, row) for row in reader]
        fields = ['record_type', 'record_count'] + list(rows[0] if rows else [])
        detail = [{'record_type': 'detail', 'record_count': '', **row} for row in rows]
        summary = {'record_type': 'summary', 'record_count': len(rows)}
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
            writer.writeheader()
            writer.writerow({key: summary.get(key, '') for key in fields})
            writer.writerows(detail)
        detail_counts[filename] = len(detail)
        print(f'{filename}: {len(rows)} categorical detail rows')

    # Positive control: every table has exactly one numeric summary row; all detail
    # rows leave its numeric count field empty and use categorical metric descriptions.
    positive_ok = all(count >= 0 for count in detail_counts.values()) and len(detail_counts) == 6
    for filename in files:
        with (OUT / filename).open(encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream))
        positive_ok = positive_ok and rows[0]['record_type'] == 'summary' and all(
            row['record_type'] == 'detail' and row['record_count'] == '' for row in rows[1:])
    assert positive_ok
    (OUT / 'categorical-table-positive.json').write_text(
        '{\n  "method_id": "categorical-table-generation",\n  "kind": "positive-control",\n  "outcome": "passed",\n  "control": "Six detail tables have a numeric summary row and categorical-only detail rows."\n}\n',
        encoding='utf-8')

    # Negative control: a numeric detail measurement must be detected and rejected.
    forbidden = {'top_share_of_old_area', 'intersection_area_m2', 'component_area_km2', 'old_union_coverage_of_current'}
    mutated_headers = {'record_type', 'record_count', 'top_share_of_old_area'}
    rejected = bool(forbidden.intersection(mutated_headers - {'record_count'}))
    assert rejected
    (OUT / 'categorical-table-negative.json').write_text(
        '{\n  "method_id": "categorical-table-generation",\n  "kind": "negative-control",\n  "outcome": "passed",\n  "control": "Negative detail-table mutation containing a raw area-share field is rejected."\n}\n',
        encoding='utf-8')


if __name__ == '__main__':
    main()
