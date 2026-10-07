#!/usr/bin/env python3
"""Reproduce the bounded Terengganu source-product geometry comparison."""
import argparse
import gzip
import hashlib
import json
import pathlib
import sys

from shapely.geometry import Point, shape
from shapely.ops import unary_union

ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED = 'research/geography/malaysia-terengganu-gap-source-fitness-20261007'
CONFIG = OWNED + '/input-config.json'
COMPONENT_PREFIX = 'coordination/engineering/physical-gap-components-1005-20261005-local19/components-v3/components-'
CUSTODY = 'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'
PRODUCT = 'coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-MYS-ADM2-000.bin.gz'
ATLAS = 'data/geography/part-16.json'
REGISTRY = 'data/administrative-sources.json'
ROUTE = 'coordination/engineering/global-actionability-routing-20261007/results/'
FAMILY_PREFIX = ROUTE + 'families-'
EXPECTED_COMPONENTS = [
    'physical-component:46a2537871d6055d90416c1508d40805648567d8dfc37696192a8a23d778922b',
    'physical-component:4dbe3afea3880fac1e82de705149e196aa6ad6930a0e0d4b740059fa75d401b2',
    'physical-component:6233f6efda804999c5d871acf8fca60daf4742a13f5001a69fba6f15b375f9b6',
    'physical-component:8bb9857dc07c70b27c9b4ed6a55fe70af5b322a293423aa1879d1d4e994c8c3f',
    'physical-component:96632d82d1eb09e9410028d0259535bf712f6005d821777f3b3d65e3941eb9ff',
    'physical-component:a5dbeb12c0625bb589edcafb5bc44d9953f36980565865e2032c4888221733e9',
    'physical-component:e9dd7858cb946a4779d6c2079ddd9876cb953d0406101094a428b10d602c70d5',
    'physical-component:f181e43671a67d0313075212a5b10c5c9d086541a044284eb3d7ff70f097fb62',
]
EXPECTED_CONTACTS = [
    'gb:MYS:ADM2:92858781B15989569853600',
    'gb:MYS:ADM2:92858781B44112931825428',
    'gb:MYS:ADM2:92858781B50781472629025',
    'gb:MYS:ADM2:92858781B66748088999576',
    'gb:MYS:ADM2:92858781B69735571651191',
    'gb:MYS:ADM2:92858781B78340444844195',
    'gb:MYS:ADM2:92858781B85628090125570',
]
FAMILY_ID = 'gap-source-batch:bfb3cabaf651a97ffcfa1a76'


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def read_json(raw, compressed=False):
    return json.loads(gzip.decompress(raw) if compressed else raw)


def reproduce(output_path):
    config = json.loads((ROOT / CONFIG).read_text())
    baseline = config['baseline']
    sys.path.insert(0, str(ROOT / 'scripts'))
    from evidence.immutable import Baseline, sha256, VERSION
    pin = Baseline(ROOT, baseline['commit'], baseline['files'])
    if VERSION != 'worldatlas-evidence-preparation-v1':
        raise ValueError('Unexpected immutable helper version')
    custody = read_json(pin.pinned_bytes(CUSTODY))
    from physical_component_custody import validate as validate_custody
    custody_validation = validate_custody(ROOT, custody)
    aliases = {row['original']['path']: row for row in custody['aliases']}
    component_aliases = [p for p in aliases if p.startswith(COMPONENT_PREFIX)]
    components = {}
    for source_path in sorted(component_aliases):
        alias = aliases[source_path]
        raw = pin.pinned_bytes(alias['payload'])
        if sha256(raw) != alias['original']['sha256']:
            raise ValueError('Custodied component input hash mismatch')
        collection = read_json(raw, compressed=True)
        if collection.get('type') == 'FeatureCollection':
            for feature in collection.get('features', []):
                if feature.get('id') in EXPECTED_COMPONENTS:
                    if feature['id'] in components:
                        raise ValueError('Duplicate target component identity')
                    components[feature['id']] = (feature, source_path, alias['payload'])
    if set(components) != set(EXPECTED_COMPONENTS):
        raise ValueError('Complete eight-component roster is not present in pinned custody')

    product_descriptor = next(row for row in baseline['files'] if row['path'] == PRODUCT)
    product_bytes = pin.pinned_bytes(PRODUCT)
    product = read_json(product_bytes, compressed=True)
    features = product['features']
    registry = read_json(pin.pinned_bytes(REGISTRY))['gb:MYS:ADM2']
    product_uncompressed_sha = sha256(gzip.decompress(product_bytes))
    if registry['sha256'] != product_uncompressed_sha:
        raise ValueError('Consumed simplified product bytes disagree with the pinned administrative registry')
    if registry.get('boundaryYearRepresented') != '2020' or registry.get('admUnitCount') != '160':
        raise ValueError('Pinned source registry vintage/count changed')
    source_features = {}
    for feature in features:
        properties = feature.get('properties') or {}
        feature_id = feature.get('id') or properties.get('id') or (
            'gb:MYS:ADM2:' + properties['shapeID'] if properties.get('shapeID') else None)
        if not feature_id:
            raise ValueError('Simplified source feature lacks stable identity')
        if feature_id in source_features:
            raise ValueError('Duplicate simplified source feature identity')
        source_features[feature_id] = feature
    if not set(EXPECTED_CONTACTS) <= set(source_features):
        raise ValueError('At least one exact contact feature is absent from the pinned full product')

    atlas = read_json(pin.pinned_bytes(ATLAS))
    atlas_features = {f.get('id') or (f.get('properties') or {}).get('id'): f for f in atlas['features']}
    contact_rows = []
    for feature_id in EXPECTED_CONTACTS:
        src = source_features[feature_id]
        atlas_feature = atlas_features.get(feature_id)
        if atlas_feature is None:
            raise ValueError('Contact feature missing from current Atlas part')
        name = (src.get('properties') or {}).get('shapeName')
        source_geom = shape(src['geometry'])
        atlas_geom = shape(atlas_feature['geometry'])
        contact_rows.append({
            'id': feature_id,
            'name': name,
            'product_feature_present': True,
            'source_feature_sha256': sha256(canonical(src)),
            'source_geometry_sha256': sha256(canonical(src['geometry'])),
            'current_atlas_feature_present': True,
            'current_atlas_representation': 'data/geography/part-16.json; derivative/display geometry, not the pinned original source bytes',
            'geometry_topologically_equal': bool(source_geom.equals(atlas_geom)),
            'geometry_coordinate_order_equal': src['geometry'] == atlas_feature['geometry'],
        })

    source_shapes = [(fid, shape(feature['geometry'])) for fid, feature in source_features.items()]
    source_names = {fid: (feature.get('properties') or {}).get('shapeName') for fid, feature in source_features.items()}
    if any(not geom.is_valid for _, geom in source_shapes):
        raise ValueError('Invalid original simplified source geometry; no automatic repair')
    source_union = unary_union([geom for _, geom in source_shapes])
    component_rows = []
    for component_id in EXPECTED_COMPONENTS:
        feature, source_path, payload_path = components[component_id]
        geom = shape(feature['geometry'])
        if not geom.is_valid:
            raise ValueError('Invalid original component geometry; no automatic repair')
        touching = []
        positive = []
        for (feature_id, source_geom), source_feature in zip(source_shapes, features):
            if geom.intersects(source_geom):
                touching.append(feature_id)
                # This computes an area-sign Boolean in input coordinate space.
                # No numeric area value is emitted or interpreted as ground area.
                if geom.intersection(source_geom).area > 0:
                    positive.append(feature_id)
        component_rows.append({
            'id': component_id,
            'custody_source_path': source_path,
            'custody_payload_path': payload_path,
            'geometry_sha256': sha256(canonical(feature['geometry'])),
            'fragment_binding_count': len(feature['properties']['fragment_bindings']),
            'fragment_bindings': feature['properties']['fragment_bindings'],
            'intersecting_simplified_feature_ids': touching,
            'intersecting_simplified_feature_names': [source_names[fid] for fid in touching],
            'positive_coordinate_plane_intersection_feature_ids': positive,
            'covered_by_simplified_product_union': bool(source_union.covers(geom)),
        })

    # Non-vacuous controls against the pinned whole product; no source classification.
    selected = shape(source_features[EXPECTED_CONTACTS[2]]['geometry'])
    inside = selected.representative_point()
    outside = Point(180.0, 0.0)
    positive_control = bool(selected.covers(inside))
    negative_control = not any(geom.covers(outside) for _, geom in source_shapes)
    if not positive_control or not negative_control:
        raise ValueError('Predicate controls did not pass')

    family = None
    for index in range(14):
        path = f'{FAMILY_PREFIX}{index:03d}.bin.gz'
        rows = gzip.decompress(pin.pinned_bytes(path)).splitlines()
        for line in rows:
            if FAMILY_ID.encode() in line:
                row = json.loads(line)
                if family is not None:
                    raise ValueError('Duplicate global routing family row')
                family = row
    if family is None:
        raise ValueError('Exact complete routing family not found')
    if family['complete_component_ids'] != EXPECTED_COMPONENTS:
        raise ValueError('Issue component roster differs from complete pinned routing family')
    if family['original_fine_family']['contact_ids'] != EXPECTED_CONTACTS:
        raise ValueError('Issue contact roster differs from original family contract')
    if family['numeric_closure_component_count'] != 3:
        raise ValueError('Frozen numeric-closure count changed')

    result = {
        'version': 1,
        'issue': 1408,
        'family_id': FAMILY_ID,
        'operational_batch': family['operational_batch'],
        'baseline_commit': baseline['commit'],
        'input_hashes': {
            'custody_index_sha256': next(row['sha256'] for row in baseline['files'] if row['path'] == CUSTODY),
            'simplified_geoBoundaries_payload_sha256': product_descriptor['sha256'],
            'current_atlas_part_sha256': next(row['sha256'] for row in baseline['files'] if row['path'] == ATLAS),
        },
        'rosters': {
            'component_ids': EXPECTED_COMPONENTS,
            'contact_ids': EXPECTED_CONTACTS,
            'numeric_closure_component_ids': family['numeric_closure_component_ids'],
        },
        'whole_file_custody_validation': custody_validation,
        'preserved_original_family_status': {
            'admin_status_counts': family['admin_status_counts'],
            'physical_status_counts': family['physical_status_counts'],
            'physical_reason_incidence_counts': family['physical_reason_incidence_counts'],
            'physical_authority': family['physical_authority'],
            'source_fitness': family['source_fitness'],
            'dispatch_ready': family['dispatch_ready'],
            'numeric_closure_component_count': family['numeric_closure_component_count'],
            'measured_fragment_area_sum_m2': family['measured_fragment_area_sum_m2'],
            'measured_fragment_area_sum_interpretation': 'Frozen routing diagnostic only; not a dry-land measurement or repair authorization.',
        },
        'simplified_product': {
            'source_path': PRODUCT,
            'whole_file_sha256': product_descriptor['sha256'],
            'uncompressed_sha256': sha256(gzip.decompress(product_bytes)),
            'feature_count': len(features),
            'registry_advertised_feature_count': 160,
            'feature_count_difference': len(features) - 160,
            'declared_crs': product.get('crs'),
            'axis_order': 'longitude-latitude per GeoJSON coordinates',
            'role': 'exact simplified geoBoundaries product pinned in baseline recipe; comparative source only',
            'baseline_registry_sha256_field': registry['sha256'],
            'boundary_license_claim': registry.get('boundaryLicense'),
            'license_source_claim': registry.get('licenseSource'),
            'source_url_claim': registry.get('boundarySourceURL'),
            'simplified_geometry_url': registry.get('simplifiedGeometryGeoJSON'),
        },
        'contact_features': contact_rows,
        'components': component_rows,
        'predicate_summary': {
            'components_intersecting_any_feature': sum(bool(row['intersecting_simplified_feature_ids']) for row in component_rows),
            'components_covered_by_product_union': sum(row['covered_by_simplified_product_union'] for row in component_rows),
            'components_not_covered_by_product_union': sum(not row['covered_by_simplified_product_union'] for row in component_rows),
            'coordinate_plane_intersection_area_sign_predicate_used': True,
            'numeric_area_values_or_dry_land_area_reported': False,
            'classification_or_ownership_inferred': False,
        },
        'controls': {
            'positive': {'feature_id': EXPECTED_CONTACTS[2], 'predicate': 'selected feature covers its representative point', 'passed': positive_control},
            'negative': {'point': [180.0, 0.0], 'predicate': 'no Malaysia ADM2 source feature covers distant point', 'passed': negative_control},
        },
        'limits': [
            'Simplified geoBoundaries is a comparative product and is not Malaysian legal authority.',
            'The pinned registry advertises 160 units while the complete pinned simplified payload contains 159 features.',
            'The seven selected feature IDs/names are present in the complete source payload, but their current Atlas part-16 geometries are not coordinate-identical or topologically equal to these source geometries; the part-16 artifact is not the source bytes.',
            'The positive-intersection diagnostic uses intersection(...).area > 0 as a Boolean in source longitude/latitude coordinates. No numeric area is reported; this coordinate-plane area sign is not physical area and the geometries are not registered to Malaysian survey geometry.',
            'The official MyGOS layer has a separate CRS metadata conflict and provider-controlled reuse terms; it is assessed separately in the source notes.',
            'Physical land/water, effective legal date, boundary authority, registration accuracy, cause, and rightful ownership remain unresolved.',
            'All three numeric-closure components remain in the frozen issue cohort and retain their original unknown status.',
        ],
    }
    out = ROOT / output_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonical(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if not args.output.startswith(OWNED + '/runs/'):
        raise SystemExit('Output must remain under this packet runs directory')
    reproduce(args.output)
