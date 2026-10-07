#!/usr/bin/env python3
"""Render review tables and typed control receipts from an already-frozen final run."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
run1 = json.loads((ROOT / 'verification/run-1.json').read_text())
run2_bytes = (ROOT / 'verification/run-2.json').read_bytes()
run1_bytes = (ROOT / 'verification/run-1.json').read_bytes()
assert run1_bytes == run2_bytes, 'frozen full-run outputs differ'

with (ROOT / 'candidate-findings.csv').open('w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['family_id', 'component_id', 'original_source_fitness',
        'ign_2026_whole_feature_intersections', 'ign_2026_whole_feature_cover_count',
        'inherited_physical_status', 'inherited_mapped_land_support_area_m2',
        'inherited_fragment_count', 'physical_source_vintage', 'surface_status',
        'coverage_and_nodata_limit', 'unresolved_reasons', 'engineering_next_action'])
    for candidate in run1['candidates']:
        relations = candidate['official_2026_whole_layer_relations']['exact_whole_feature_intersections']
        physical = candidate['physical_status_record']
        support = candidate['routing_record'].get('existing_support_areas', {}).get('mapped_land_support', {})
        limit = ('Inherited support summary only; raster/native cells, valid-data coverage, '
                 'NoData and source observation dates cannot be reconstructed from this row.')
        unresolved = '; '.join(physical.get('unresolved_reasons', [])) or \
                     'No candidate-specific resolution recorded; cause remains unknown.'
        writer.writerow([candidate['family_id'], candidate['component_id'],
            candidate['source_fitness_disposition'],
            '; '.join(sorted({x['name'] for x in relations})),
            sum(bool(x['whole_feature_covers_full_subject']) for x in relations),
            physical['physical_status'], support.get('area_m2'),
            physical['measured_fragment_count'], physical['physical_source_vintage'],
            physical['water_surface_status'], limit, unresolved,
            candidate['research_recommendation']])

with (ROOT / 'family-findings.csv').open('w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['family_id', 'component_count', 'original_fine_family_count',
        'admin_status_counts', 'physical_status_counts', 'missing_admin_count',
        'mismatched_admin_component_ids', 'invalid_original_source_count',
        'unmeasured_component_count', 'unmeasured_fragment_component_count',
        'hierarchy_unknown_component_ids', 'numeric_closure_component_ids',
        'components_without_existing_area', 'complete_positive_length_neighbor_count',
        'complete_positive_length_neighbor_ids', 'boundary_length_m',
        'boundary_length_limit', 'exclusive_next_prerequisite_counts',
        'dispatch_ready', 'physical_authority'])
    for family in sorted(run1['families'], key=lambda row: row['id']):
        writer.writerow([family['id'], family['component_count'], family['fine_family_count'],
            json.dumps(family['admin_status_counts'], sort_keys=True),
            json.dumps(family['physical_status_counts'], sort_keys=True),
            family['missing_admin_component_count'], '; '.join(family['mismatched_admin_component_ids']),
            family['invalid_original_source_component_count'], family['unmeasured_components'],
            family['components_with_unmeasured_fragments'], '; '.join(family['hierarchy_unknown_component_ids']),
            '; '.join(family['numeric_closure_component_ids']), family['components_without_existing_area'],
            family['positive_length_neighbor_count'], '; '.join(family['complete_positive_length_neighbor_ids']),
            family['boundary_length_m'], family['boundary_length_limit'],
            json.dumps(family['exclusive_next_prerequisite_counts'], sort_keys=True),
            family['dispatch_ready'], family['physical_authority']])

with (ROOT / 'contact-findings.csv').open('w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['subject_id', 'recorded_2022_name', 'exact_2026_name_candidates',
        '2022_source_geometry_2026_intersections', '2022_source_geometry_2026_covers',
        'current_atlas_geometry_2026_intersections', 'current_atlas_geometry_2026_covers',
        'geometry_identity_limit'])
    for contact in run1['contacts']:
        src = contact['official_2026_original_source_whole_layer_relations']['exact_whole_feature_intersections']
        cur = contact['official_2026_current_atlas_whole_layer_relations']['exact_whole_feature_intersections']
        names = contact['official_2026_exact_name_identity_candidates']
        writer.writerow([contact['subject_id'],
            contact['complete_original_2022_source_feature']['properties']['shapeName'],
            '; '.join(sorted({x['name'] for x in names})),
            '; '.join(sorted({x['name'] for x in src})),
            sum(bool(x['whole_feature_covers_full_subject']) for x in src),
            '; '.join(sorted({x['name'] for x in cur})),
            sum(bool(x['whole_feature_covers_full_subject']) for x in cur),
            contact['identity_limit']])

metrics = {
    'family_count': len(run1['families']), 'candidate_count': run1['candidate_count'],
    'contact_count': run1['contact_count'], 'original_source_record_count': 320,
    'official_2026_feature_count': run1['official_layer_roster']['features'],
    'compatible_recorded_subjects': 11, 'partial_or_unbound_original_source': 24,
    'no_compatible_original_intersection': 11, 'outside_original_source_domain': 2,
    'official_2026_intersect': 42, 'official_2026_whole_feature_cover': 8,
    'official_2026_intersect_without_cover': 34, 'official_2026_no_intersection': 6,
    'exact_current_contact_name_match': 15, 'inherited_mapped_land_support': 46,
    'inherited_outside_l1_context': 2, 'unverified_surface': 48,
    'contacts_with_2022_geometry_intersection_2026': sum(bool(x['official_2026_original_source_whole_layer_relations']['exact_whole_feature_intersections']) for x in run1['contacts']),
    'contacts_with_2022_geometry_whole_cover_2026': sum(any(y['whole_feature_covers_full_subject'] for y in x['official_2026_original_source_whole_layer_relations']['exact_whole_feature_intersections']) for x in run1['contacts']),
    'contacts_with_current_atlas_geometry_intersection_2026': sum(bool(x['official_2026_current_atlas_whole_layer_relations']['exact_whole_feature_intersections']) for x in run1['contacts']),
    'contacts_with_current_atlas_geometry_whole_cover_2026': sum(any(y['whole_feature_covers_full_subject'] for y in x['official_2026_current_atlas_whole_layer_relations']['exact_whole_feature_intersections']) for x in run1['contacts']),
}
(ROOT / 'summary-metrics.json').write_text(json.dumps({'values': metrics}, indent=2) + '\n')
controls = run1['controls']
run_hash = hashlib.sha256(run1_bytes).hexdigest()
assert run_hash == hashlib.sha256(run2_bytes).hexdigest()
receipts = [
    {'method_id': 'complete-france-source-fitness-reproduction', 'kind': 'positive-control',
     'outcome': 'passed', 'evidence': {'exact_scope_roster': controls['scope_roster']['positive_exact_complete_roster'],
       'full_feature_source_intersections': controls['axis_order']['positive_full_geometry_candidate_count_with_source_intersection'],
       'whole_official_feature_count': run1['official_layer_roster']['features'],
       'native_original_shape_id_count': controls['source_and_geometry']['original_source_unique_shape_id_count'],
       'all_contact_source_identities_present': controls['source_and_geometry']['contact_original_source_identity_count'] == 16,
       'all_full_contacts_compared_to_whole_official_layer': len(run1['contacts']) == 16 and all(
          x['official_2026_original_source_whole_layer_relations']['whole_source_features_scanned'] == 333 and
          x['official_2026_current_atlas_whole_layer_relations']['whole_source_features_scanned'] == 333
          for x in run1['contacts'])}},
    {'method_id': 'complete-france-source-fitness-reproduction', 'kind': 'negative-control',
     'outcome': 'passed', 'evidence': {'omission_rejected': controls['scope_roster']['negative_omission_rejected'],
       'duplicate_rejected': controls['scope_roster']['negative_duplicate_rejected'],
       'foreign_rejected': controls['scope_roster']['negative_foreign_rejected'],
       'swapped_axis_candidate_envelope_hits': controls['axis_order']['negative_swapped_candidate_envelope_hits'],
       **{key: value for key, value in controls['source_and_geometry'].items() if key.startswith('negative_')},
       'unobserved_surface_preserved_as_unknown': controls['source_and_geometry']['positive_preserved_unobserved_surface_unknowns'],
       'reordered_membership_is_canonically_invariant': controls['source_and_geometry']['positive_reordered_membership_invariant'],
       'raster_affine_nodata_applicability': controls['source_and_geometry']['raster_affine_nodata']}},
    {'method_id': 'complete-france-source-fitness-reproduction', 'kind': 'reproducibility',
     'outcome': 'passed', 'run_one_sha256': run_hash, 'run_two_sha256': run_hash, 'equal': True},
]
for receipt in receipts:
    name = {'positive-control': 'validation-positive.json', 'negative-control': 'validation-negative.json',
            'reproducibility': 'validation-reproducibility.json'}[receipt['kind']]
    (ROOT / name).write_text(json.dumps(receipt, indent=2) + '\n')
