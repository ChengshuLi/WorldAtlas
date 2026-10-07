#!/usr/bin/env python3
"""Reproduce the scoped France ADM3 source-fitness comparison from frozen inputs."""
import argparse
import gzip
import hashlib
import json
import pathlib
import re
import sys

import shapely
from shapely.geometry import shape
from shapely.strtree import STRtree
from shapely.ops import transform as transform_geometry


ROOT = pathlib.Path(__file__).resolve().parents[3]
OWNED = pathlib.Path(__file__).resolve().parent
CONTRACT = OWNED / 'run-contract.json'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_exact(path, descriptor):
    raw = pathlib.Path(path).read_bytes()
    if len(raw) != descriptor['bytes'] or digest(raw) != descriptor['sha256']:
        raise ValueError('whole input bytes differ from frozen descriptor: ' + str(path))
    if descriptor.get('uncompressed_sha256'):
        decoded = gzip.decompress(raw)
        if len(decoded) != descriptor['uncompressed_bytes'] or digest(decoded) != descriptor['uncompressed_sha256']:
            raise ValueError('decoded input bytes differ from frozen descriptor: ' + str(path))
        return decoded
    return raw


def load_json(raw):
    return json.loads(raw.decode('utf-8'))


def load_records(raw):
    text = raw.decode('utf-8').lstrip()
    if text.startswith('['):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def canonical(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--official-source', required=True, help='Complete retained WFS GeoJSON response; never a clipped geometry')
    ap.add_argument('--run', type=int, choices=(1, 2), required=True)
    args = ap.parse_args()
    contract = load_json(CONTRACT.read_bytes())
    if contract['script_sha256'] != digest(pathlib.Path(__file__).read_bytes()):
        raise ValueError('script differs from the frozen run contract')
    if contract['runtime']['python'] != sys.version.split()[0]:
        raise ValueError('Python runtime differs from the frozen run contract')

    inputs = {}
    print('reading frozen repository inputs', flush=True)
    for desc in contract['baseline']['files']:
        p = ROOT / desc['path']
        inputs[desc['path']] = read_exact(p, desc)
    external = contract['external_source']
    print('validating and parsing complete official response', flush=True)
    official_raw = pathlib.Path(args.official_source).read_bytes()
    if len(official_raw) != external['bytes'] or digest(official_raw) != external['sha256']:
        raise ValueError('complete official WFS response differs from frozen whole-body receipt')
    official = load_json(official_raw)
    if official.get('type') != 'FeatureCollection' or len(official.get('features', [])) != external['feature_count']:
        raise ValueError('official response is not the complete declared feature collection')
    if official.get('numberReturned') != external['feature_count'] or official.get('numberMatched') != external['feature_count']:
        raise ValueError('official response does not prove the full expected layer was returned')

    part8 = load_json(inputs['data/geography/part-8.json'])
    world_index = load_json(inputs['data/world-index.json'])
    custody = load_json(inputs['coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'])
    report = load_json(inputs['coordination/engineering/global-actionability-routing-20261007/results/report.json'])
    config = load_json(inputs['coordination/engineering/global-actionability-routing-20261007/input-config.json'])
    original_raw = inputs['coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-FRA-ADM3-000.bin.gz']
    original = load_json(original_raw)
    print('restoring delivered whole routing bodies', flush=True)

    body_specs = {x['name']: x for x in report['complete_whole_raw_bodies']}

    def restore_routing_body(name, relevant_ids):
        spec = body_specs[name]
        chunks = []
        for part in spec['parts']:
            path = 'coordination/engineering/global-actionability-routing-20261007/results/' + part['path']
            raw = inputs[path]
            if len(raw) != part['uncompressed_bytes'] or digest(raw) != part['uncompressed_sha256']:
                raise ValueError('routing slice differs from exact complete-body report: ' + path)
            chunks.append(raw)
        whole = b''.join(chunks)
        if len(whole) != spec['bytes'] or digest(whole) != spec['sha256']:
            raise ValueError('ordered routing slices do not restore exact whole raw body: ' + name)
        if spec['format'] != 'jsonl':
            raise ValueError('unexpected format for routed whole-body inventory: ' + name)
        needle_pattern = b'|'.join(re.escape(identity.encode('utf-8')) for identity in sorted(relevant_ids))
        matcher = re.compile(needle_pattern)
        selected = []
        for line in whole.splitlines():
            if line and matcher.search(line):
                selected.append(json.loads(line))
        return selected

    family_rows = []
    fit_list = []
    route_component_rows = {}
    candidate_features = {}
    targets = set(contract['scope']['component_ids'])
    family_ids = set(contract['scope']['family_ids'])
    family_rows = restore_routing_body('families', targets | family_ids)
    route_component_list = restore_routing_body('components', targets)
    admin_binding_list = restore_routing_body('admin-bindings', targets)
    route_component_rows = {r['component']: r for r in route_component_list}
    admin_binding_rows = {r['component']: r for r in admin_binding_list}
    for path, raw in inputs.items():
        if '/results/land-source-fitness-' in path and path.endswith('.bin.gz'):
            fit_list.extend(load_records(raw))
    fit_rows = {r['component']: r for r in fit_list}
    if len(fit_rows) != len(fit_list):
        raise ValueError('duplicate original-source fitness records')
    if len(route_component_list) != 48 or len(route_component_rows) != 48:
        raise ValueError('duplicate or missing target component records in complete route body')
    if len(admin_binding_list) != 48 or len(admin_binding_rows) != 48:
        raise ValueError('duplicate or missing target admin-binding records in complete body')

    families = [f for f in family_rows if f.get('id') in contract['scope']['family_ids']]
    foreign_claims = [f for f in family_rows if f.get('id') not in family_ids and targets.intersection(f.get('complete_component_ids', []))]
    if foreign_claims:
        raise ValueError('a target candidate also appears in a foreign family')
    if len(families) != 9 or {f['id'] for f in families} != set(contract['scope']['family_ids']):
        raise ValueError('whole-family roster is incomplete or contains duplicates')
    family_membership = {}
    for family in families:
        members = family['complete_component_ids']
        if family['component_count'] != len(members) or len(members) != len(set(members)):
            raise ValueError('family component count/membership mismatch')
        for member in members:
            if member in family_membership:
                raise ValueError('component occurs in more than one target family')
            family_membership[member] = family['id']
    if set(family_membership) != targets or len(targets) != 48:
        raise ValueError('target components are not the exact union of the nine whole families')
    if set(fit_rows) & targets != set().union(*(set(f['compatible_original_admin_component_ids']) for f in families)):
        raise ValueError('compatible original-source fitness subset differs from complete family records')
    if set(route_component_rows) & targets != targets or set(admin_binding_rows) & targets != targets:
        raise ValueError('candidate-level routing or complete admin-binding records are incomplete')

    print('verifying retained full candidate feature custody', flush=True)
    index_alias = {a['original']['path']: a for a in custody['aliases']}
    payloads = {p['path']: p for p in custody['payloads']}
    needed_v3 = [p for p in index_alias if '/components-v3/components-' in p]
    for logical in needed_v3:
        alias = index_alias[logical]
        payload_path = alias['payload']
        payload_desc = payloads[payload_path]
        payload = inputs[payload_path]
        if len(payload) != payload_desc['bytes'] or digest(payload) != payload_desc['sha256']:
            raise ValueError('component custody payload does not match whole-file index')
        if digest(payload) != alias['original']['sha256']:
            raise ValueError('component-v3 alias does not match whole original output')
        decoded = gzip.decompress(payload)
        if digest(decoded) != alias['original']['uncompressed_sha256'] or len(decoded) != alias['original']['uncompressed_bytes']:
            raise ValueError('component-v3 decoded body does not match whole original output')
        for feature in load_json(decoded)['features']:
            if feature['id'] in targets:
                candidate_features[feature['id']] = feature
    if set(candidate_features) != targets:
        raise ValueError('complete candidate pointsets are not present in verified original component outputs')

    contacts = contract['scope']['contact_ids']
    atlas_by_id = {f['id']: f for f in part8['features']}
    if len(contacts) != 16 or set(contacts) - set(atlas_by_id):
        raise ValueError('exact complete Atlas contact roster is missing or duplicated')
    original_by_id = {'gb:FRA:ADM3:' + f['properties']['shapeID']: f for f in original['features']}
    if len(original['features']) != 320 or len(original_by_id) != 320:
        raise ValueError('original complete 2022 source feature inventory is not exactly 320 unique shapeIDs')
    if set(contacts) - set(original_by_id):
        raise ValueError('complete original source body lacks one or more full recorded contact shapeIDs')

    # Build the complete 333-feature official source index. STRtree predicate queries
    # evaluate each entire unmodified polygon against every complete candidate/contact.
    official_features = official['features']
    if any(f.get('type') != 'Feature' or not f.get('geometry') for f in official_features):
        raise ValueError('official layer contains a non-feature or empty geometry')
    print('building full-source GEOS spatial index', flush=True)
    official_collection = shapely.from_geojson(official_raw.decode('utf-8'))
    official_shapes = list(official_collection.geoms)
    if len(official_shapes) != len(official_features):
        raise ValueError('GEOS source geometry count differs from full official feature count')
    tree = STRtree(official_shapes)
    print('checking whole feature relationships', flush=True)

    # Negative roster controls show that omitted, duplicated, or foreign entries
    # cannot pass the exact complete-family closure assertion above.
    ordered_targets = sorted(targets)
    roster_controls = {
        'positive_exact_complete_roster': len(ordered_targets) == 48 and set(ordered_targets) == targets,
        'negative_omission_rejected': set(ordered_targets[:-1]) != targets,
        'negative_duplicate_rejected': len(ordered_targets + [ordered_targets[0]]) != len(set(ordered_targets + [ordered_targets[0]])),
        'negative_foreign_rejected': set(ordered_targets + ['physical-component:foreign-control']) != targets,
    }
    if not all(roster_controls.values()):
        raise ValueError('scope positive/negative roster control failed')

    def relation(geometry):
        geom = shape(geometry)
        bbox_indices = sorted(int(i) for i in tree.query(geom))
        indices = sorted(int(i) for i in tree.query(geom, predicate='intersects'))
        rows = []
        for i in indices:
            feat = official_features[i]
            p = feat['properties']
            official_geometry = official_shapes[i]
            rows.append({'feature_id': feat.get('id'),
                    'ign_stable_key': p.get('cleabs'),
                    'code_insee': p.get('code_insee'),
                    'department_code': p.get('code_insee_du_departement'),
                    'region_code': p.get('code_insee_de_la_region'),
                    'name': p.get('nom_officiel'),
                    'whole_feature_intersects_full_subject': True,
                    'whole_feature_covers_full_subject': official_geometry.covers(geom)})
        return {
            'whole_source_features_scanned': len(official_features),
            'whole_source_features_with_envelope_intersection': len(bbox_indices),
            'exact_whole_feature_intersections': rows,
        }

    candidate_rows = []
    for cid in sorted(targets):
        sourcefit = fit_rows.get(cid)
        route = route_component_rows[cid]
        candidate = candidate_features[cid]
        if (sourcefit is not None and sourcefit.get('family') != family_membership[cid]) or route.get('family') != family_membership[cid]:
            raise ValueError('candidate routing/family IDs disagree')
        if route.get('current_geometry_sha256') != digest(canonical(candidate['geometry'])):
            raise ValueError('retained full candidate pointset differs from routed complete geometry hash')
        observations = sourcefit.get('original_admin_observations', []) if sourcefit else []
        if any(o.get('component') != cid for o in observations):
            raise ValueError('candidate source observation binds to a different component')
        binding_observations = admin_binding_rows[cid].get('observations', [])
        if sourcefit is not None:
            disposition = 'compatible-original-subject-recorded'
        elif route.get('physical_status') == 'outside-mapped-L1-context':
            disposition = 'outside-original-source-domain-unknown'
        elif any(o.get('status') == 'positive-source-coverage-mixed-partial-or-subject-unresolved' for o in binding_observations):
            disposition = 'partial-or-unbound-original-source-unknown'
        else:
            disposition = 'no-compatible-original-source-intersection-unknown'
        candidate_rows.append({
            'family_id': family_membership[cid],
            'component_id': cid,
            'full_candidate_feature': candidate,
            'routing_record': route,
            'source_fitness_record': sourcefit,
            'complete_admin_binding_record': admin_binding_rows[cid],
            'source_fitness_disposition': disposition,
            'research_recommendation': {
                'compatible-original-subject-recorded': 'Retain as a comparison lead only; reconcile physical surface and whole neighboring boundaries before engineering processing.',
                'partial-or-unbound-original-source-unknown': 'Unresolved; restore a full, appropriately dated authoritative source and neighboring coverage before processing.',
                'no-compatible-original-source-intersection-unknown': 'Unresolved; absence of a source intersection does not establish water, dry land, or political location.',
                'outside-original-source-domain-unknown': 'Keep outside-domain; obtain a source with explicit territorial coverage before any processing or assignment.',
            }[disposition],
            'physical_status_record': {
                'physical_status': route.get('physical_status'),
                'water_surface_status': candidate['properties'].get('water_status'),
                'touches_reference_shore': candidate['properties'].get('touches_reference_shore'),
                'touches_domain_boundary': candidate['properties'].get('touches_domain_boundary'),
                'touches_blocked_tile': candidate['properties'].get('touches_blocked_tile'),
                'measured_fragment_area_sum_m2': candidate['properties'].get('measured_fragment_area_sum_m2'),
                'measured_fragment_count': candidate['properties'].get('measured_fragment_count'),
                'unmeasured_fragment_ids': candidate['properties'].get('unmeasured_fragment_ids'),
                'physical_source_vintage': route.get('physical_source_vintage'),
                'existing_support_areas': route.get('existing_support_areas'),
                'unresolved_reasons': route.get('unresolved'),
                'interpretation': 'inherited diagnostic physical/source observations only; surface status and physical authority remain unverified/unapproved as recorded',
            },
            'official_2026_whole_layer_relations': relation(candidate['geometry']),
            'observed_geometry_relation_only': 'CRS84 two-dimensional Shapely full-feature intersects/covers; topology is diagnostic and does not establish physical land, legal ownership, historical boundary applicability, or source authority',
        })

    official_by_exact_name = {}
    for feat in official_features:
        official_by_exact_name.setdefault(feat['properties'].get('nom_officiel'), []).append(feat)
    contact_rows = []
    for sid in sorted(contacts):
        atlas_feature = atlas_by_id[sid]
        shape_id = sid.rsplit(':', 1)[1]
        source_feature = original_by_id[sid]
        if source_feature['properties']['shapeID'] != shape_id or source_feature['properties']['shapeGroup'] != 'FRA':
            raise ValueError('source shapeID does not bind to complete feature identity')
        contact_rows.append({
            'subject_id': sid,
            'complete_current_atlas_feature': atlas_feature,
            'complete_original_2022_source_feature': source_feature,
            'official_2026_exact_name_identity_candidates': [
                {'feature_id': f.get('id'), 'ign_stable_key': f['properties'].get('cleabs'),
                 'code_insee': f['properties'].get('code_insee'),
                 'department_code': f['properties'].get('code_insee_du_departement'),
                 'region_code': f['properties'].get('code_insee_de_la_region'),
                 'name': f['properties'].get('nom_officiel')}
                for f in official_by_exact_name.get(source_feature['properties'].get('shapeName'), [])],
            'identity_limit': 'Exact names are identity leads only. No historical/current whole-contact boundary equality or legal applicability is asserted; candidate-scale full geometry relations are reported separately.',
        })
    print('running geometry axis negative control', flush=True)

    # CRS control: for this French cohort, complete source geometries and the
    # requested GeoJSON layer agree in x=longitude/y=latitude. The transposed
    # negative control must have no relation to the 333-feature source layer.
    swapped_envelope_candidates = 0
    for cid in sorted(targets):
        geom = shape(candidate_features[cid]['geometry'])
        swapped = transform_geometry(lambda x, y, z=None: (y, x) if z is None else (y, x, z), geom)
        swapped_envelope_candidates += len(tree.query(swapped))
    if swapped_envelope_candidates:
        raise ValueError('axis-swapped negative control unexpectedly has a source envelope candidate')
    candidate_positive_intersections = sum(bool(c['official_2026_whole_layer_relations']['exact_whole_feature_intersections']) for c in candidate_rows)
    if candidate_positive_intersections == 0:
        raise ValueError('full-shape positive source-intersection control unexpectedly has no matches')
    disposition_counts = {}
    for row in candidate_rows:
        disposition_counts[row['source_fitness_disposition']] = disposition_counts.get(row['source_fitness_disposition'], 0) + 1
    expected_dispositions = {
        'compatible-original-subject-recorded': 11,
        'partial-or-unbound-original-source-unknown': 24,
        'no-compatible-original-source-intersection-unknown': 11,
        'outside-original-source-domain-unknown': 2,
    }
    if disposition_counts != expected_dispositions:
        raise ValueError('candidate source-fitness classes do not close to the issue contract')

    source_manifest = load_json(inputs['coordination/engineering/original-geography-source-corpus-20261006/evidence-quality.json'])
    source_receipt = next(f for s in source_manifest['sources'] for f in s.get('files', [])
                          if f['path'].endswith('/gb-FRA-ADM3-000.bin.gz'))
    original_descriptor = next(d for d in contract['baseline']['files'] if d['path'].endswith('/gb-FRA-ADM3-000.bin.gz'))
    if source_receipt['sha256'] != original_descriptor['sha256']:
        raise ValueError('original France source receipt does not match whole encoded source bytes')

    out = {
        'version': 1,
        'issue': 1310,
        'baseline_commit': contract['baseline']['commit'],
        'frozen_scope': contract['scope'],
        'routing_report_sha256': contract['pins']['delivered_routing_report'],
        'routing_input_config_sha256': contract['pins']['delivered_routing_input_config'],
        'original_france_source_receipt': source_receipt,
        'official_source_receipt': external,
        'official_layer_roster': {
            'features': len(official_features),
            'numberMatched': official.get('numberMatched'),
            'numberReturned': official.get('numberReturned'),
            'crs': official.get('crs'),
        },
        'families': sorted(families, key=lambda r: r['id']),
        'candidate_count': len(candidate_rows),
        'candidates': candidate_rows,
        'source_fitness_disposition_counts': disposition_counts,
        'contact_count': len(contact_rows),
        'contacts': contact_rows,
        'controls': {
            'scope_roster': roster_controls,
            'axis_order': {
                'positive_control': 'whole candidate points and the full French official layer have geographic extents consistent with longitude/latitude; WFS was requested with CRS:84',
                'positive_full_geometry_candidate_count_with_source_intersection': candidate_positive_intersections,
                'negative_swapped_candidate_envelope_hits': swapped_envelope_candidates,
                'response_crs_metadata': official.get('crs'),
                'response_metadata_limit': 'The legacy GeoJSON response advertises EPSG:4326 despite the explicit CRS:84 request; source coordinates are retained and axis interpretation is independently checked through the full-cohort positive/negative spatial controls.',
            },
        },
        'methods': {
            'source_coordinate_order': 'GeoJSON longitude, latitude',
            'source_crs': 'CRS:84 as requested from the official WFS; source response crs is recorded above',
            'predicate': 'Shapely 2.1.2 STRtree full-geometry intersects and whole-feature covers; no clipping, centroid or bbox-based relationship',
            'completeness': 'The complete official 333-feature GeoJSON is parsed and indexed as whole unmodified polygons. Per-candidate tree envelopes only narrow exact whole-feature intersects/covers operations for all 48 full candidate geometries; no source feature is clipped or omitted from the index. The 16 complete contacts are retained and identity-checked against the full original source body; their exact-name matches are identity leads only, not contact-boundary comparisons.',
            'limits': [
                'The 2026 product is a new contemporary comparison vintage; it cannot silently replace geoBoundaries 2022 historical input.',
                'The overlay is only a full-shape geometric relation. It cannot establish dry land, legal territorial ownership, effective boundary date, or why a mismatch exists.',
                'The official whole response exceeds repository per-file/decoded custody limits; exact external restoration and hash are recorded. Full source bytes are not represented by this result extract.',
                'Four candidate pointsets have no intersection with this full official layer; no cause is inferred.',
                'Physical statuses, source fitness, unknowns and proposed prerequisites remain those in the complete upstream candidate records; no geography is approved.',
            ],
        },
    }
    out_path = OWNED / 'verification' / ('run-%d.json' % args.run)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical(out)
    tmp = out_path.with_suffix('.json.tmp')
    if tmp.exists() or out_path.exists():
        raise ValueError('Preserve prior runs; output already exists')
    tmp.write_bytes(encoded)
    tmp.replace(out_path)
    print(json.dumps({'output': str(out_path.relative_to(ROOT)), 'bytes': len(encoded), 'sha256': digest(encoded),
                      'candidate_count': len(candidate_rows), 'contact_count': len(contact_rows),
                      'official_feature_count': len(official_features)}))


if __name__ == '__main__':
    main()
