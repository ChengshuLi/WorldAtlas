#!/usr/bin/env python3
"""Render the individually assessed #393 subjects and six province parents."""
import csv
import json
from pathlib import Path

root = Path('data/regional-review/regional-review-5cf69eed7fdff0b5')
assessment = json.loads((root / 'reproduction/geography-assessment.json').read_text(encoding='utf-8'))
output = Path('research/geography/east-siberia-assessment-integrity-1130-erratum/controls/legacy-renderer-overwrite.tsv')
fields = [
    'record_type', 'record_id', 'name', 'current_parent_id', 'current_parent_name',
    'source_id', 'source_role_claim', 'source_level_claim', 'source_vintage',
    'source_license', 'classification', 'source_to_current_iou',
    'source_to_current_area_ratio', 'source_to_current_components', 'source_members', 'reason',
]
rows = []
for item in assessment['subjects']:
    metric = item.get('publisher_simplified_to_current_comparison') or item.get('current_overlay_geometry_comparison') or {}
    rows.append({
        'record_type': 'scoped-location',
        'record_id': item['id'],
        'name': item['current_name'],
        'current_parent_id': item['current_parent_id'],
        'current_parent_name': item['current_parent_name'],
        'source_id': item['source_id'],
        'source_role_claim': item.get('current_source_role', ''),
        'source_level_claim': item.get('current_source_level', ''),
        'source_vintage': item.get('verified_source_vintage', item.get('source_reference_year', '')),
        'source_license': item.get('source_license', ''),
        'classification': item['classification'],
        'source_to_current_iou': '' if metric.get('iou') is None else f"{metric['iou']:.12f}",
        'source_to_current_area_ratio': '' if metric.get('area_ratio_right_to_left') is None else f"{metric['area_ratio_right_to_left']:.12f}",
        'source_to_current_components': f"{item.get('source_component_count', '')}->{item.get('current_component_count', '')}",
        'source_members': ';'.join(item['source_member_ids']),
        'reason': item['reason'],
    })
for item in assessment['provinces']:
    rows.append({
        'record_type': 'province-parent', 'record_id': item['id'], 'name': item['name'],
        'current_parent_id': '', 'current_parent_name': '',
        'source_id': 'Constitution of the Russian Federation, Article 65',
        'source_role_claim': item['legal_role'],
        'source_level_claim': item['framework_level'],
        'source_vintage': 'Constitution text amended through 2020-07-01; current framework record retained in issue baseline',
        'source_license': '', 'classification': item['classification'],
        'source_to_current_iou': '', 'source_to_current_area_ratio': '',
        'source_to_current_components': '', 'source_members': '', 'reason': item['reason'],
    })
rows.sort(key=lambda row: (row['record_type'], row['record_id']))
with output.open('w', encoding='utf-8', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, delimiter='\t', lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
print(json.dumps({'output': str(output), 'rows': len(rows)}))
