#!/usr/bin/env python3
"""Reproduce the source-role and geometry review for issue #393.

Geometry operations use EPSG:6933 only as a regional equal-area diagnostic.
Invalid input is retained unchanged; make_valid is used only on in-memory
diagnostic clones for overlay operations and is reported explicitly.
"""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely import make_valid
from shapely.geometry import shape
from shapely.ops import transform, unary_union


ROOT = Path.cwd()
OWNED = Path('data/regional-review/regional-review-5cf69eed7fdff0b5')
IN = OWNED / 'source'
OUT = Path('research/geography/east-siberia-assessment-integrity-1130-erratum/controls/legacy-analyzer-overwrite.json')
HASHES = OWNED / 'reproduction' / 'geoboundaries-feature-hashes.tsv'
SOURCE_PINS = {
    'geoboundaries_raw_scoped': ('0be36fd932447bcfcfecebf10b3804e8098d76f90952baea69c5c64e9cdfde41', None),
    'geoboundaries_supporting_base': ('087017889376976d2fd601dac1fa470b69c2775bd20a3b36695295b963f9e669', None),
    'geoboundaries_simplified_world': ('81dabf7930ff5e306e2423b586bcec14163fbd10481db6e49aab47273953b128', 26338801),
    'resolve_east_siberia_features': ('7a95c8e36155e02069e6e6439f1d18ad3145012e361306c155cabd581fff07e7', None),
    'resolve_completeness_query': ('235c587e0964f8c8958f17b2fab806d139b58e088a8e45c2a61354985a0f44a1', None),
    'natural_earth_lakes': ('2d036f53dedec578001c5c30c2959ee7d4eebc1306900fa4367c49929ec8f2d9', 5043554),
}
TO_EQUAL_AREA = Transformer.from_crs('EPSG:4326', 'EPSG:6933', always_xy=True).transform


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_pin(name, path):
    expected_hash, expected_bytes = SOURCE_PINS[name]
    actual_hash = sha256(path)
    actual_bytes = Path(path).stat().st_size
    if actual_hash != expected_hash or (expected_bytes is not None and actual_bytes != expected_bytes):
        raise ValueError(f'{name} pin mismatch: bytes={actual_bytes}, sha256={actual_hash}')
    return {'path': str(path), 'bytes': actual_bytes, 'sha256': actual_hash}


def as_polygonal(geometry):
    if geometry.geom_type == 'Polygon':
        return [geometry]
    if hasattr(geometry, 'geoms'):
        return [part for component in geometry.geoms for part in as_polygonal(component)]
    return []


def vertex_count(geometry):
    return sum(len(ring.coords) for part in as_polygonal(geometry)
               for ring in [part.exterior, *part.interiors])


def hole_count(geometry):
    return sum(len(part.interiors) for part in as_polygonal(geometry))


def component_count(geometry):
    return len(as_polygonal(geometry))


def diagnostic(geometry):
    """Return a repaired clone only for diagnostics; do not serialize it."""
    return make_valid(geometry) if not geometry.is_valid else geometry


def projected(geometry):
    return diagnostic(transform(TO_EQUAL_AREA, diagnostic(geometry)))


def overlap(left, right):
    left_area, right_area = left.area, right.area
    union = left.union(right).area
    return {
        'iou': left.intersection(right).area / union if union else None,
        'area_ratio_right_to_left': right_area / left_area if left_area else None,
        'area_left_km2': left_area / 1_000_000,
        'area_right_km2': right_area / 1_000_000,
    }


def index_features(paths, key):
    indexed = {}
    for path in paths:
        for feature in read_json(path)['features']:
            value = feature['properties'].get(key)
            if value is not None:
                if value in indexed:
                    raise ValueError(f'duplicate feature key {value!r}')
                indexed[value] = feature
    return indexed


def map_by_id(path):
    return index_features([path], 'shapeID')


def main():
    inventory_path = OWNED / 'reproduction' / 'scope-inventory.run-1.json'
    inventory = read_json(inventory_path)
    if len(inventory['subjects']) != 207 or len({s['id'] for s in inventory['subjects']}) != 207:
        raise ValueError('Issue #393 exact scope must be 207 unique subjects.')

    scoped_path = IN / 'geoboundaries-rus-adm2-2017-scope-185-original-features.geojson'
    base_path = IN / 'geoboundaries-rus-adm2-2017-adaptation-base-8-original-features.geojson'
    simplified_path = IN / 'geoboundaries-rus-adm2-2017-simplified-full-source.geojson'
    resolve_path = IN / 'resolve-ecoregions-east-siberia-query.json'
    resolve_candidates_path = IN / 'resolve-ecoregions-east-siberia-8-member-completeness.json'
    lakes_path = IN / 'ne_10m_lakes-pinned-source.geojson'
    pins = {
        'geoboundaries_raw_scoped': check_pin('geoboundaries_raw_scoped', scoped_path),
        'geoboundaries_supporting_base': check_pin('geoboundaries_supporting_base', base_path),
        'geoboundaries_simplified_world': check_pin('geoboundaries_simplified_world', simplified_path),
        'resolve_east_siberia_features': check_pin('resolve_east_siberia_features', resolve_path),
        'resolve_completeness_query': check_pin('resolve_completeness_query', resolve_candidates_path),
        'natural_earth_lakes': check_pin('natural_earth_lakes', lakes_path),
    }

    current = index_features(sorted(set(s['feature_path'] for s in inventory['subjects'])), 'id')
    raw_direct = map_by_id(scoped_path)
    raw_base = map_by_id(base_path)
    simplified_all = map_by_id(simplified_path)
    if len(raw_direct) != 185 or len(raw_base) != 8 or len(simplified_all) != 2327:
        raise ValueError('Pinned source feature counts changed.')

    resolve_features = read_json(resolve_path)['features']
    resolve_by_id = {str(int(f['properties']['ECO_ID'])): f for f in resolve_features}
    candidate_features = read_json(resolve_candidates_path)['features']
    candidates_by_id = {str(int(f['properties']['ECO_ID'])): f for f in candidate_features}
    lakes = read_json(lakes_path)['features']
    baikal = [f for f in lakes if str(f['properties'].get('ne_id')) == '1159113127']
    if len(baikal) != 1:
        raise ValueError('Natural Earth lake ne_id 1159113127 must resolve once.')

    hash_rows = {}
    for line in HASHES.read_text(encoding='utf-8').splitlines():
        shape_id, _name, digest = line.split('\t')
        hash_rows[shape_id] = digest

    units = []
    geo_metrics = []
    for subject in inventory['subjects']:
        feature = current.get(subject['id'])
        if feature is None:
            raise ValueError(f"Missing current feature {subject['id']}")
        current_shape = shape(feature['geometry'])
        item = {
            'id': subject['id'], 'current_name': subject['current_name'],
            'current_parent_id': subject['current_parent_id'],
            'current_parent_name': subject['current_parent_name'],
            'feature_path': subject['feature_path'], 'source_id': subject['source_id'],
            'source_original_id': subject['source_original_id'],
            'source_member_ids': subject['source_member_ids'],
            'current_source_role': feature['properties']['metadata'].get('source_role'),
            'current_source_level': feature['properties']['metadata'].get('source_level'),
            'current_selection_reason': feature['properties']['metadata'].get('selection_reason'),
            'source_reference_year': subject['source_reference_year'],
            'source_license': subject['source_license'],
            'current_geometry_type': current_shape.geom_type,
            'current_geometry_valid': current_shape.is_valid,
            'current_component_count': component_count(current_shape),
            'current_vertex_count': vertex_count(current_shape),
            'current_hole_count': hole_count(current_shape),
        }

        if subject['source_id'] == 'gb:RUS:ADM2':
            sid = subject['source_original_id']
            original = raw_direct[sid]
            generalized = simplified_all[sid]
            original_shape = shape(original['geometry'])
            generalized_shape = shape(generalized['geometry'])
            source_name = original['properties']['shapeName']
            current_name = feature['properties']['name']
            role_signal = 'urban-okruг' if ('городской округ' in source_name.lower() or
                                            'urban okrug' in source_name.lower() or
                                            'urban district' in source_name.lower()) else (
                'closed-territory-name' if ('зато' in source_name.lower() or
                                             'closed administrative' in source_name.lower()) else None)
            raw_to_simplified = overlap(projected(original_shape), projected(generalized_shape))
            simplified_to_current = overlap(projected(generalized_shape), projected(current_shape))
            item.update({
                'source_name': source_name,
                'verified_source_vintage': ('2017 geoBoundaries boundaries; source input last updated 2023-03-03; '
                                            'published build 2023-12-12'),
                'current_name_matches_source': current_name == source_name,
                'source_geometry_type': original_shape.geom_type,
                'source_geometry_valid': original_shape.is_valid,
                'source_component_count': component_count(original_shape),
                'source_vertex_count': vertex_count(original_shape),
                'source_hole_count': hole_count(original_shape),
                'simplified_geometry_valid': generalized_shape.is_valid,
                'simplified_component_count': component_count(generalized_shape),
                'simplified_vertex_count': vertex_count(generalized_shape),
                'simplified_hole_count': hole_count(generalized_shape),
                'source_feature_sha256': hash_rows[sid],
                'raw_to_publisher_simplified_comparison': raw_to_simplified,
                'publisher_simplified_to_current_comparison': simplified_to_current,
                'role_signal_needs_official_crosswalk': role_signal,
                'classification': 'insufficient-evidence',
                'reason': ('Pinned 2017 gbOpen ADM2 feature identity, source name, ODbL, and current province parent were matched. '
                           'Unit-level legal role/current status, country-wide completeness, and acceptable Atlas geometry '
                           'generalization still require authoritative unit crosswalk and tolerance evidence.'),
            })
            geo_metrics.append(item)

        elif subject['source_id'].startswith('resolve:'):
            eco_id = subject['source_id'].split(':', 1)[1]
            eco_feature = resolve_by_id[eco_id]
            member_key = sid = subject['source_original_id']
            base_feature = raw_base[sid]
            base_shape = shape(base_feature['geometry'])
            eco_shape = shape(eco_feature['geometry'])
            input_was_invalid = not base_shape.is_valid or not eco_shape.is_valid
            expected_shape = diagnostic(base_shape).intersection(diagnostic(eco_shape))
            overlay_comparison = overlap(projected(expected_shape), projected(current_shape))
            item.update({
                'source_name': eco_feature['properties']['ECO_NAME'],
                'verified_source_vintage': ('RESOLVE ecoregion lineage cites Dinerstein et al. 2017; '
                                            'current service layer dataLastEditDate 2022-01-27; queried 2026-10-06'),
                'source_ecoregion_id': int(eco_id),
                'source_ecoregion_role': 'ecological ecoregion, not administrative unit',
                'source_ecoregion_biome': eco_feature['properties']['BIOME_NAME'],
                'source_ecoregion_realm': eco_feature['properties']['REALM'],
                'source_member_admin_name': base_feature['properties']['shapeName'],
                'source_member_admin_id': 'gb:RUS:ADM2:' + member_key,
                'source_overlay_input_invalid_before_diagnostic_clone': input_was_invalid,
                'current_overlay_geometry_comparison': overlay_comparison,
                'current_source_role': feature['properties']['metadata'].get('source_role'),
                'current_location_basis': feature['properties']['metadata'].get('location_basis'),
                'classification': 'correction-needed',
                'reason': ('The pinned geometry is a published ecoregion clipped to a 2017 ADM2 feature; current metadata '
                           'calls the result a Raion and identifies it as a subdivision while parenting it to the province. '
                           'Record the ecological/administrative overlay and restore the exact parent/role semantics before use.'),
            })

        elif subject['source_id'] == 'natural-earth:lake:1159113127':
            lake = baikal[0]
            lake_shape = shape(lake['geometry'])
            member_key = sid = subject['source_original_id']
            base_feature = raw_base[sid]
            base_shape = shape(base_feature['geometry'])
            input_was_invalid = not base_shape.is_valid or not lake_shape.is_valid
            expected_shape = diagnostic(base_shape).intersection(diagnostic(lake_shape))
            overlay_comparison = overlap(projected(expected_shape), projected(current_shape))
            item.update({
                'source_name': lake['properties']['name'],
                'verified_source_vintage': ('Natural Earth pinned commit ca96624a56bd078437bca8184e78163e5039ad19; '
                                            'feature year field -99, no year-specific hydrology; underlying admin source claims 2017'),
                'source_ne_id': lake['properties']['ne_id'],
                'source_natural_earth_class': lake['properties']['featurecla'],
                'source_natural_earth_year_field': lake['properties'].get('year'),
                'source_member_admin_name': base_feature['properties']['shapeName'],
                'source_member_admin_id': 'gb:RUS:ADM2:' + member_key,
                'source_overlay_input_invalid_before_diagnostic_clone': input_was_invalid,
                'current_overlay_geometry_comparison': overlay_comparison,
                'classification': 'correction-needed',
                'reason': ('This is a Natural Earth Lake Baikal water fragment intersected with an ODbL district polygon, '
                           'not a Raion boundary; its source vintage is a modern reference rather than 2017. The current '
                           'role and direct province parent obscure the source overlay.'),
            })
        else:
            raise ValueError(f"Unexpected source for scoped ID {subject['id']}: {subject['source_id']}")
        units.append(item)

    # The eight supporting districts and 16 ecoregions bound the expected overlay set.
    observed_pairs = defaultdict(set)
    for item in units:
        if item['source_id'].startswith('resolve:'):
            observed_pairs[item['source_original_id']].add(str(item['source_ecoregion_id']))
    expected_pairs = defaultdict(set)
    overlay_coverage = {}
    invalid_source_ids = []
    for base_id, base_feature in raw_base.items():
        base_geom = shape(base_feature['geometry'])
        if not base_geom.is_valid:
            invalid_source_ids.append(base_id)
        fixed_base = diagnostic(base_geom)
        intersections = []
        for eco_id, eco_feature in candidates_by_id.items():
            eco_geom = shape(eco_feature['geometry'])
            if not eco_geom.is_valid:
                invalid_source_ids.append('resolve:' + eco_id)
            intersection = fixed_base.intersection(diagnostic(eco_geom))
            if not intersection.is_empty and intersection.area > 0:
                expected_pairs[base_id].add(eco_id)
                intersections.append(intersection)
        union = unary_union(intersections) if intersections else fixed_base.intersection(fixed_base)
        projected_base = projected(fixed_base)
        projected_union = projected(union)
        overlay_coverage[base_id] = {
            'source_name': base_feature['properties']['shapeName'],
            'expected_ecoregion_ids': sorted(expected_pairs[base_id], key=int),
            'current_ecoregion_ids': sorted(observed_pairs.get(base_id, set()), key=int),
            'pair_set_complete': expected_pairs[base_id] == observed_pairs.get(base_id, set()),
            'source_area_coverage_by_all_ecoregions': projected_union.area / projected_base.area if projected_base.area else None,
            'invalid_original_geometry_left_unchanged_and_only_diagnostic_cloned': not base_geom.is_valid,
        }

    # Measure whether the ecological and named-water fragments cover each source district.
    lake_subject = next(s for s in inventory['subjects']
                        if s['source_id'] == 'natural-earth:lake:1159113127')
    lake_base_id = lake_subject['source_original_id']
    lake_source_shape = shape(baikal[0]['geometry'])
    for base_id, group in overlay_coverage.items():
        members = [item for item in units
                   if item.get('source_member_admin_id') == 'gb:RUS:ADM2:' + base_id]
        pieces = [projected(shape(current[item['id']]['geometry'])) for item in members]
        if pieces:
            combined = unary_union(pieces)
            raw_base_shape = projected(shape(raw_base[base_id]['geometry']))
            group['current_piece_union_to_admin_base'] = overlap(raw_base_shape, combined)
            group['current_piece_count'] = len(pieces)
        if base_id == lake_base_id:
            base_geom = diagnostic(shape(raw_base[base_id]['geometry']))
            expected_lake = projected(base_geom.intersection(diagnostic(lake_source_shape)))
            expected_eco = [projected(base_geom.intersection(diagnostic(shape(candidates_by_id[eco_id]['geometry']))))
                            for eco_id in group['expected_ecoregion_ids']]
            expected_combined = unary_union(expected_eco + [expected_lake])
            raw_base_shape = projected(shape(raw_base[base_id]['geometry']))
            group['named_water_source_id'] = 'natural-earth:lake:1159113127'
            group['expected_ecoregion_plus_named_water_union_to_admin_base'] = overlap(raw_base_shape, expected_combined)
            group['combined_current_physical_pieces_to_admin_base'] = group.get('current_piece_union_to_admin_base')

    # Individual current province records and their frozen hierarchy review state.
    hierarchy = read_json('data/hierarchy.json')
    province_ids = sorted(set(s['current_parent_id'] for s in inventory['subjects']))
    provinces = []
    for province_id in province_ids:
        record = next((entry for entry in hierarchy if entry.get('id') == province_id), None)
        if record is None:
            raise ValueError(f'Missing frozen province framework record {province_id}')
        stats_key = next(key for key in inventory['parent_distribution'] if key.startswith(province_id + '|'))
        province_name = stats_key.split('|', 1)[1]
        provinces.append({
            'id': province_id, 'name': province_name,
            'current_child_count': inventory['parent_distribution'][stats_key],
            'framework_level': record.get('level'),
            'framework_status': record.get('metadata', {}).get('framework_status'),
            'semantic_review': record.get('metadata', {}).get('semantic_review'),
            'current_child_parent_reference_state': 'frozen current relationship; not an independent boundary/completeness proof',
            'legal_role': 'Russian federal subject listed in Constitution Article 65',
            'classification': 'insufficient-evidence',
            'reason': ('Legal parent role is supported by Constitution Article 65. Frozen framework boundary and exact complete '
                       'membership remain under open semantic review; parent/region interiors are not certified by this packet.'),
        })

    metro_signals = Counter(item['role_signal_needs_official_crosswalk'] for item in geo_metrics)
    metro_signals.pop(None, None)
    city_candidates = [item for item in geo_metrics if item['role_signal_needs_official_crosswalk']]
    mismatched_parts = [item for item in geo_metrics
                        if item['source_component_count'] != item['current_component_count']]
    ious = sorted(item['publisher_simplified_to_current_comparison']['iou'] for item in geo_metrics)
    summaries = {
        'issue_scope_subjects': len(units),
        'direct_adm2_subjects': len(geo_metrics),
        'physical_overlay_subjects': sum(1 for item in units if item['source_id'].startswith('resolve:')),
        'natural_earth_lake_fragments': sum(1 for item in units if item['source_id'].startswith('natural-earth:')),
        'classifications': dict(Counter(item['classification'] for item in units)),
        'direct_adm2_unique_source_features': len(raw_direct),
        'supporting_admin_source_features_not_in_issue_scope': len(raw_base),
        'raw_publisher_feature_count': 2327,
        'metadata_claimed_feature_count': 2328,
        'resolved_name_equals_pinned_source': sum(item['current_name_matches_source'] for item in geo_metrics),
        'source_admin_geometry_valid_count': sum(item['source_geometry_valid'] for item in geo_metrics),
        'current_admin_geometry_valid_count': sum(item['current_geometry_valid'] for item in geo_metrics),
        'source_current_part_count_differences': len(mismatched_parts),
        'publisher_simplified_vertices_total': sum(item['simplified_vertex_count'] for item in geo_metrics),
        'current_admin_vertices_total': sum(item['current_vertex_count'] for item in geo_metrics),
        'publisher_simplified_to_current_iou_min_median_max': [ious[0], ious[len(ious) // 2], ious[-1]],
        'publisher_simplified_to_current_iou_below_0_99': sum(value < 0.99 for value in ious),
        'publisher_simplified_to_current_iou_below_0_95': sum(value < 0.95 for value in ious),
        'publisher_simplified_to_current_iou_below_0_90': sum(value < 0.90 for value in ious),
        'name_level_urban_okrug_or_zato_candidates_for_official_crosswalk': len(city_candidates),
        'candidate_name_signals': dict(metro_signals),
        'ecoregion_source_subject_ids': sorted(resolve_by_id, key=int),
        'ecoregion_expected_pair_count': sum(len(value) for value in expected_pairs.values()),
        'ecoregion_current_pair_count': sum(len(value) for value in observed_pairs.values()),
        'ecoregion_pair_set_exactly_reproduced_per_source_admin_unit': all(v['pair_set_complete'] for v in overlay_coverage.values()),
        'supporting_source_geometries_invalid_on_original_bytes': sorted(set(invalid_source_ids)),
        'natural_earth_lake_identity': {'ne_id': 1159113127, 'name': 'Lake Baikal', 'feature_class': baikal[0]['properties']['featurecla']},
        'region_certification': inventory['frozen_pins'],
    }
    output = {
        'version': 1,
        'issue': 393,
        'baseline_commit': inventory['baseline_commit'],
        'retrieved_at_utc': '2026-10-06',
        'method': {
            'area_crs': 'EPSG:6933',
            'comparison': 'intersection-over-union (IoU), equal-area projection; area ratio uses right/left',
            'diagnostic_geometry_policy': 'Invalid inputs are reported and remain unchanged; make_valid is used only on in-memory diagnostic clones for overlay.',
            'thresholds': '0.99, 0.95, and 0.90 are triage flags only, not acceptance thresholds or truth judgments.',
        },
        'source_pins': pins,
        'summaries': summaries,
        'provinces': provinces,
        'ecoregion_adaptation_completeness': dict(sorted(overlay_coverage.items())),
        'subjects': sorted(units, key=lambda item: item['id']),
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(OUT), 'bytes': OUT.stat().st_size, 'sha256': sha256(OUT), 'summaries': summaries}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
