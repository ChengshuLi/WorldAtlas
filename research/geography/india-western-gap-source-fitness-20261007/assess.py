#!/usr/bin/env python3
"""Reproduce the bounded western India administrative source coverage screen."""
import codecs
import csv
import gzip
import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

from shapely.geometry import box, shape
from shapely.validation import explain_validity


ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
MANIFEST_PATH = PACKET / 'evidence-quality.json'
OWNED = 'research/geography/india-western-gap-source-fitness-20261007/'
VINTAGE = 'coverage-screen-2026-10-08-03'
MAX_FILE_BYTES = 32 * 1024 * 1024


def load_pinned_reader(manifest):
    """Load the declared immutable reader from exact committed baseline bytes."""
    commit = manifest['baseline']['commit']
    helper = 'scripts/evidence/immutable.py'
    pin = next(x for x in manifest['baseline']['files'] if x['path'] == helper)
    tree = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-z', commit, '--', helper])
    row = tree.decode().rstrip('\0')
    if not row.startswith(('100644 ', '100755 ')) or '\t' + helper != row[row.find('\t'):]:
        raise ValueError('Pinned evidence reader is not an ordinary baseline file')
    blob = row.split()[2]
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', 'blob', blob])
    if len(raw) != pin['bytes'] or hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise ValueError('Pinned evidence reader bytes do not match the manifest')
    namespace = {'__name__': 'worldatlas_bootstrap_immutable', '__file__': str(ROOT / helper)}
    exec(compile(raw, str(ROOT / helper), 'exec'), namespace)
    bootstrap = namespace['Baseline'](ROOT, commit, [pin])
    return bootstrap.load_modules({'evidence.immutable': helper})['evidence.immutable']


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def git_bytes(commit, path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{commit}:{path}'])


def json_gzip(raw, baseline, name):
    decoded = gzip.decompress(raw)
    baseline.admit(name + '#decoded', len(decoded))
    if len(decoded) > MAX_FILE_BYTES:
        raise ValueError('Decoded input exceeds file limit: ' + name)
    return json.loads(decoded), decoded


def iter_top_level_features(chunks):
    """Decode FeatureCollection.features incrementally, without joining ADM3."""
    decoder = codecs.getincrementaldecoder('utf-8')()
    json_decoder = json.JSONDecoder()
    text = ''
    in_features = False
    ended = False
    for raw in chunks:
        text += decoder.decode(raw, final=False)
        if not in_features:
            match = re.search(r'"features"\s*:\s*\[', text)
            if match:
                text = text[match.end():]
                in_features = True
            elif len(text.encode('utf-8')) > MAX_FILE_BYTES:
                raise ValueError('FeatureCollection header exceeds buffer limit')
        if in_features:
            while True:
                text = text.lstrip()
                if not text:
                    break
                if text[0] == ',':
                    text = text[1:]
                    continue
                if text[0] == ']':
                    text = text[1:]
                    ended = True
                    break
                try:
                    feature, end = json_decoder.raw_decode(text)
                except json.JSONDecodeError:
                    if len(text.encode('utf-8')) > MAX_FILE_BYTES:
                        raise ValueError('Single feature exceeds decoded-file limit')
                    break
                if not isinstance(feature, dict) or feature.get('type') != 'Feature':
                    raise ValueError('Non-Feature member in top-level features array')
                yield feature
                text = text[end:]
            if ended:
                # Continue consuming bytes so upstream product length/hash checks
                # cover the complete original product, including the JSON tail.
                for _ in chunks:
                    pass
                return
    text += decoder.decode(b'', final=True)
    if not ended:
        text = text.lstrip()
        if text.startswith(']'):
            return
        raise ValueError('FeatureCollection ended before its features array closed')


def bounds_intersect(a, b):
    return a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


def text_prop(props, *names):
    for name in names:
        value = props.get(name)
        if value is not None and str(value).strip():
            return str(value).replace('\n', ' ').replace('\r', ' ')
    return ''


def main():
    manifest = json.loads(MANIFEST_PATH.read_text())
    immutable = load_pinned_reader(manifest)
    baseline = immutable.Baseline(ROOT, manifest['baseline']['commit'], manifest['baseline']['files'])
    baseline.load_modules({'evidence.immutable': 'scripts/evidence/immutable.py'})
    pins = manifest['baseline']['pin_files']
    pinned = {name: baseline.pinned_bytes(path) for name, path in pins.items()}

    # The selected family and candidate components are read only from authenticated
    # immutable blobs; no geometry is rewritten or repaired.
    component_index_path = pins['component_custody_index']
    component_index = json.loads(pinned['component_custody_index'])
    aliases = {x['payload']: x for x in component_index['aliases']}
    subject_ids = manifest['subject_ids']
    subject_paths = manifest['baseline']['subject_files']
    components = {}
    for path in sorted(set(subject_paths.values())):
        alias = aliases[path]
        compressed = baseline.pinned_bytes(path)
        decoded = gzip.decompress(compressed)
        baseline.admit(path + '#decoded', len(decoded))
        if len(decoded) != alias['original']['uncompressed_bytes'] or hashlib.sha256(decoded).hexdigest() != alias['original']['uncompressed_sha256']:
            raise ValueError('Component GeoJSON decoded identity mismatch: ' + path)
        collection = json.loads(decoded)
        if collection.get('type') != 'FeatureCollection':
            raise ValueError('Component custody payload is not a FeatureCollection')
        for feature in collection.get('features', []):
            if feature.get('id') in subject_ids:
                components[feature['id']] = feature
    if set(components) != set(subject_ids):
        raise ValueError('Complete subject roster did not resolve exactly once')

    # Preserve all source corpus partitions and verify each part before using it.
    corpus = json.loads(pinned['source_corpus_catalogue'])
    adm2_metadata = json.loads(pinned['administrative_sources'])['gb:IND:ADM2']
    adm3_metadata = json.loads(pinned['india_adm3_metadata'])
    products = {x['key']: x for x in corpus['products'] if x['key'] in ('gb:IND:ADM2', 'gb:IND:ADM3')}
    if (adm2_metadata['boundaryYearRepresented'] != '2021' or
            adm2_metadata['boundaryLicense'] != 'Open Data Commons Open Database License 1.0' or
            adm3_metadata['boundaryYearRepresented'] != '2018' or
            adm3_metadata['boundaryLicense'] != 'Open Data Commons Open Database License 1.0'):
        raise ValueError('Administrative source metadata does not match the reviewed issue claims')
    part_paths = {
        'gb:IND:ADM2': ['india_adm2_payload'],
        'gb:IND:ADM3': ['india_adm3_payload_000', 'india_adm3_payload_001'],
    }
    source_records = {}
    original_product_hashes = {}
    for key, keys in part_paths.items():
        product = products[key]
        raw_parts = [pinned[name] for name in keys]
        part_descriptors = []
        original_digest = hashlib.sha256()
        original_bytes = 0
        decoded_parts = []
        for name, raw, part in zip(keys, raw_parts, product['parts']):
            if hashlib.sha256(raw).hexdigest() != part['sha256'] or len(raw) != part['bytes']:
                raise ValueError('Source partition encoded bytes disagree with corpus catalogue')
            decoded = gzip.decompress(raw)
            baseline.admit(name + '#decoded', len(decoded))
            if len(decoded) != part['uncompressed_bytes'] or hashlib.sha256(decoded).hexdigest() != part['uncompressed_sha256']:
                raise ValueError('Source partition decoded bytes disagree with corpus catalogue')
            original_digest.update(decoded)
            original_bytes += len(decoded)
            decoded_parts.append(decoded)
            part_descriptors.append({'key': name, 'path': pins[name], 'compressed_bytes': len(raw), 'compressed_sha256': hashlib.sha256(raw).hexdigest(), 'decoded_bytes': len(decoded), 'decoded_sha256': hashlib.sha256(decoded).hexdigest()})
        original_hash = original_digest.hexdigest()
        if original_bytes != product['original_bytes'] or original_hash != product['original_sha256']:
            raise ValueError('Reconstructed original source product hash mismatch: ' + key)
        original_product_hashes[key] = {'bytes': original_bytes, 'sha256': original_hash}
        source_records[key] = {'product': product, 'parts': part_descriptors, 'decoded_parts': decoded_parts}

    admin2_bytes = source_records['gb:IND:ADM2']['decoded_parts'][0]
    adm2_collection = json.loads(admin2_bytes)
    if adm2_collection.get('type') != 'FeatureCollection':
        raise ValueError('ADM2 source is not a FeatureCollection')

    # Build valid, unmodified target geometries and audit their stored attributes.
    targets = {}
    member_rows = []
    for sid in subject_ids:
        feature = components[sid]
        geom = shape(feature['geometry']) if feature.get('geometry') else None
        props = feature.get('properties', {})
        if geom is None:
            raise ValueError('Subject lacks geometry: ' + sid)
        valid = bool(geom.is_valid)
        targets[sid] = {'feature': feature, 'geometry': geom, 'bounds': geom.bounds, 'valid': valid, 'validity': 'Valid Geometry' if valid else explain_validity(geom)}
        member_rows.append({
            'subject_id': sid,
            'source_file': subject_paths[sid],
            'geometry_type': geom.geom_type,
            'geometry_valid': str(valid).lower(),
            'geometry_validity_reason': targets[sid]['validity'],
            'bbox_min_x': repr(geom.bounds[0]), 'bbox_min_y': repr(geom.bounds[1]),
            'bbox_max_x': repr(geom.bounds[2]), 'bbox_max_y': repr(geom.bounds[3]),
            'inherited_water_status': text_prop(props, 'water_status') or 'not-recorded',
            'fragment_count': props.get('measured_fragment_count', ''),
            'measured_fragment_area_sum_m2_inherited_only': props.get('measured_fragment_area_sum_m2', ''),
            'fragment_bindings': ';'.join(sorted({str(x.get('id', '')) for x in props.get('fragment_bindings', [])})),
            'component_feature_sha256': hashlib.sha256(canonical(feature)).hexdigest(),
        })

    # The routing slice records the two inherited compatibility witnesses; keep
    # these distinct from new geometric results.
    fit_bytes = gzip.decompress(pinned['global_routing_source_match_slice_000'])
    fit_file = next(x for x in manifest['baseline']['files'] if x['path'] == pins['global_routing_source_match_slice_000'])
    baseline.admit(pins['global_routing_source_match_slice_000'] + '#decoded', len(fit_bytes))
    if len(fit_bytes) != fit_file['uncompressed_bytes'] or hashlib.sha256(fit_bytes).hexdigest() != fit_file['uncompressed_sha256']:
        raise ValueError('Routing source-match slice decoded identity mismatch')
    fit_payload = json.loads(fit_bytes)
    fit_rows = {x.get('component'): x for x in fit_payload if isinstance(x, dict) and x.get('component')}

    # Every source feature is streamed/read, while only bounding-box candidates
    # receive exact topological predicates. Invalid geometries remain untouched.
    coverage_rows = []
    source_summaries = {}
    def evaluate_product(key, features):
        product = products[key]
        source_count = 0
        invalid_source_count = 0
        missing_shape_id_count = 0
        shape_id_counts = {}
        bbox_pairs = 0
        intersect_pairs = 0
        intersect_subjects = set()
        covers_pairs = 0
        touches_pairs = 0
        failed_pairs = 0
        for source_feature in features:
            source_count += 1
            geom_json = source_feature.get('geometry')
            source_geom = shape(geom_json) if geom_json else None
            source_valid = bool(source_geom is not None and source_geom.is_valid)
            if source_geom is not None and not source_valid:
                invalid_source_count += 1
            source_id = source_feature.get('id') or text_prop(source_feature.get('properties', {}), 'shapeID', 'shapeId', 'id')
            props = source_feature.get('properties', {})
            shape_id = text_prop(props, 'shapeID', 'shapeId')
            if not shape_id:
                missing_shape_id_count += 1
            else:
                shape_id_counts[shape_id] = shape_id_counts.get(shape_id, 0) + 1
            source_name = text_prop(props, 'shapeName', 'shapeNameAlt', 'name', 'NAME_2', 'NAME_3')
            if source_geom is None:
                continue
            for sid, target in targets.items():
                if not bounds_intersect(target['bounds'], source_geom.bounds):
                    continue
                bbox_pairs += 1
                can_check = target['valid'] and source_valid
                intersects = covers = covered_by = touches = False
                validity_reason = ''
                if can_check:
                    try:
                        intersects = bool(target['geometry'].intersects(source_geom))
                        covers = bool(target['geometry'].covers(source_geom))
                        covered_by = bool(source_geom.covers(target['geometry']))
                        touches = bool(target['geometry'].touches(source_geom))
                    except Exception as error:
                        failed_pairs += 1
                        validity_reason = 'topology-error:' + type(error).__name__
                else:
                    validity_reason = 'invalid-target-or-source-geometry'
                intersect_pairs += int(intersects)
                if intersects:
                    intersect_subjects.add(sid)
                covers_pairs += int(covered_by)
                touches_pairs += int(touches)
                coverage_rows.append({
                    'source_key': key,
                    'subject_id': sid,
                    'source_feature_id': source_id,
                    'source_feature_name': source_name,
                    'bbox_candidate': 'true',
                    'source_geometry_valid': str(source_valid).lower(),
                    'target_geometry_valid': str(target['valid']).lower(),
                    'exact_intersects': str(intersects).lower() if can_check else 'unresolved',
                    'source_covers_target': str(covered_by).lower() if can_check else 'unresolved',
                    'target_covers_source': str(covers).lower() if can_check else 'unresolved',
                    'boundaries_touch': str(touches).lower() if can_check else 'unresolved',
                    'topology_limit': validity_reason,
                })
        if source_count != product['feature_count']:
            raise ValueError(f'{key} yielded {source_count} features, expected {product["feature_count"]}')
        source_summaries[key] = {
            'retained_feature_count': source_count,
            'advertised_feature_count': product['advertised_feature_count'],
            'retained_nonblank_shape_id_count': sum(shape_id_counts.values()),
            'unique_retained_shape_id_count': len(shape_id_counts),
            'duplicate_retained_shape_id_count': sum(count > 1 for count in shape_id_counts.values()),
            'missing_retained_shape_id_count': missing_shape_id_count,
            'advertised_minus_retained_feature_count': product['advertised_feature_count'] - source_count,
            'feature_count_reconciliation': 'Retained simplified-product features have nonblank unique shapeID values and no repeated shapeID. The advertised metadata count exceeds the retained feature count; neither the catalogue nor feature metadata identifies the omitted unit(s) or explains the discrepancy.',
            'invalid_source_feature_count': invalid_source_count,
            'bbox_candidate_pairs': bbox_pairs,
            'exact_intersect_pairs': intersect_pairs,
            'subjects_with_exact_intersection': len(intersect_subjects),
            'source_covers_target_pairs': covers_pairs,
            'boundary_touch_pairs': touches_pairs,
            'topology_error_pairs': failed_pairs,
            'original_product_bytes': original_product_hashes[key]['bytes'],
            'original_product_sha256': original_product_hashes[key]['sha256'],
            'source_part_descriptors': source_records[key]['parts'],
        }

    evaluate_product('gb:IND:ADM2', adm2_collection['features'])
    def adm3_chunks():
        for key, decoded in zip(part_paths['gb:IND:ADM3'], source_records['gb:IND:ADM3']['decoded_parts']):
            yield decoded
    adm3_features = iter_top_level_features(adm3_chunks())
    evaluate_product('gb:IND:ADM3', adm3_features)

    for row in member_rows:
        fit = fit_rows.get(row['subject_id'], {})
        row['inherited_family_id'] = fit.get('family', 'not-in-source-fit-slice')
        row['inherited_source_fitness_prerequisite'] = fit.get('source_fitness_prerequisite', 'not-listed')
        observations = fit.get('original_admin_observations', [])
        row['inherited_compatible_source_products'] = ';'.join(sorted({p for observation in observations for p in observation.get('source_products', [])}))
        row['inherited_observation_statuses'] = ';'.join(sorted({x.get('status', '') for x in observations}))
        row['inherited_surface_statuses'] = ';'.join(sorted({x.get('surface_status', '') for x in observations}))
        row['inherited_status'] = ';'.join(sorted({x.get('status', '') for x in observations if x.get('status')}))

    report = {
        'version': 1,
        'status': 'complete-source-coverage-screen-with-physical-status-unresolved',
        'issue': 1432,
        'baseline_commit': manifest['baseline']['commit'],
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'runtime': {'python': sys.version.split()[0], 'shapely': __import__('shapely').__version__, 'geos': __import__('shapely').geos_version_string},
        'family': {'id': 'gap-source-batch:ff84042d9e10553c98925ed5', 'complete_member_count': len(subject_ids), 'subject_ids_sha256': manifest['subject_ids_sha256']},
        'selection': {'collision_context_issue': 111, 'collision_interpretation': 'contact-only context; no exact member subject match found', 'priority_rank_reconstruction': 'reproduced in the separately bounded selection-ranking report using all 14 family output shards and the complete source-fitness slice'},
        'input_accounting': {'baseline_files': len(manifest['baseline']['files']), 'baseline_phase_consumed_bytes_including_decoded_parts': sum(baseline.consumed.values()), 'source_reconstruction': 'All compressed parts independently authenticated, decoded per part, concatenated only into a streaming digest/feature parser; ADM3 original exceeds the per-file decoded limit and was never materialized as a single file.', 'source_originals': original_product_hashes},
        'products': source_summaries,
        'physical_interpretation': {'independent_dated_land_water_evidence_found': False, 'physical_authority': 'unapproved', 'interpretation': 'ADM2 and ADM3 are administrative reference products. Their overlaps or containment can describe source-relative administrative coverage only; they do not establish dated dry-land versus inland-water truth for any candidate.', 'missing_fact': 'An independent, authoritative physical-surface observation with a date and resolution suitable for each of the 18 candidate pointsets, specifically distinguishing dry land from inland water where relevant.', 'geometry_repairs': 'none', 'area_or_distance_measurements': 'none'},
        'limits': [
            'Both products have retained feature counts below their advertised unit counts; absent records and current full-source completeness are unresolved.',
            'ADM2 is represented as 2021 and ADM3 as 2018 in upstream metadata; their age and any intervening territorial changes are not resolved.',
            'No original CRS declaration or datum sidecar was retained with the GeoJSON partitions; coordinates are used as stored in x/y order and WGS84 interpretation remains a documented assumption.',
            'The intersection screen does not establish legal authority, physical land/water status, processing cause or a safe geometry correction.',
            'Issue #111 shares seven contact references but has no exact subject-ID match; its territorial relationship remains context, not evidence of common or independent component ownership.',
        ],
    }

    selection_pin_keys = sorted(
        key for key in manifest['baseline']['pins']
        if key in {'global_routing_report', 'global_routing_family_shard_013',
                   'global_routing_source_match_slice_000', 'priority_v3_report'}
        or key.startswith('priority_v3_investigations_')
    )
    report['selection_input_sha256'] = hashlib.sha256(canonical({
        key: manifest['baseline']['pins'][key] for key in selection_pin_keys
    })).hexdigest()
    rank_report_path = PACKET / 'selection-ranking' / 'report.json'
    rank_report_raw = rank_report_path.read_bytes()
    rank_report = json.loads(rank_report_raw)
    if rank_report.get('baseline_commit') != manifest['baseline']['commit'] or rank_report.get('target_family_id') != 'gap-source-batch:ff84042d9e10553c98925ed5':
        raise ValueError('Selection rank report does not match this coverage-screen baseline/family')
    report['selection']['rank_report_path'] = str(rank_report_path.relative_to(ROOT))
    report['selection']['rank_report_sha256'] = hashlib.sha256(rank_report_raw).hexdigest()
    report['selection']['reconstructed_rank'] = rank_report['selected_family_rank']
    report['selection']['reconstructed_rank_denominator'] = rank_report['ranked_source_fitness_family_count']
    report['selection_input_sha256'] = hashlib.sha256(canonical({
        'coverage_pins': {key: manifest['baseline']['pins'][key] for key in selection_pin_keys},
        'selection_rank_input_sha256': rank_report['selection_input_sha256'],
        'selection_rank_report_sha256': report['selection']['rank_report_sha256'],
    })).hexdigest()
    source_fitness_witnesses = sorted(
        sid for sid, record in fit_rows.items()
        if sid in subject_ids and record.get('source_fitness_prerequisite')
    )
    report['source_fitness_prerequisite_subject_ids'] = source_fitness_witnesses
    report['source_fitness_prerequisite_subject_count'] = len(source_fitness_witnesses)
    report['analysis_input_sha256'] = hashlib.sha256(canonical({
        'method': 'complete-component-pointsets-versus-complete-India-ADM2-and-ADM3-native-coordinate-screen-v1',
        'component_feature_sha256': sorted(row['component_feature_sha256'] for row in member_rows),
        'source_product_sha256': {key: value['sha256'] for key, value in sorted(original_product_hashes.items())},
    })).hexdigest()
    report['selection_pin_keys'] = selection_pin_keys

    # Bind selected witness rows into member summaries without treating them as
    # new source support or physical findings.
    for row in member_rows:
        fit = fit_rows.get(row['subject_id'], {})
        if fit:
            row['inherited_source_fitness_prerequisite'] = fit.get('source_fitness_prerequisite', '')
            row['inherited_physical_authority'] = fit.get('physical_authority', '')

    file_names = ['adm2-000.bin.gz', 'adm3-000.bin.gz', 'adm3-001.bin.gz', 'source-coverage.csv', 'member-roster.csv', 'report.json']
    output_map = {}
    for key, fname in zip(part_paths['gb:IND:ADM2'] + part_paths['gb:IND:ADM3'], file_names[:3]):
        output_map[fname] = pinned[key]

    def write_csv(rows, fields):
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        return stream.getvalue().encode('utf-8')

    coverage_fields = ['source_key', 'subject_id', 'source_feature_id', 'source_feature_name', 'bbox_candidate', 'source_geometry_valid', 'target_geometry_valid', 'exact_intersects', 'source_covers_target', 'target_covers_source', 'boundaries_touch', 'topology_limit']
    member_fields = ['subject_id', 'source_file', 'geometry_type', 'geometry_valid', 'geometry_validity_reason', 'bbox_min_x', 'bbox_min_y', 'bbox_max_x', 'bbox_max_y', 'inherited_water_status', 'fragment_count', 'measured_fragment_area_sum_m2_inherited_only', 'fragment_bindings', 'component_feature_sha256', 'inherited_family_id', 'inherited_source_fitness_prerequisite', 'inherited_compatible_source_products', 'inherited_observation_statuses', 'inherited_surface_statuses', 'inherited_status', 'inherited_physical_authority']
    output_map['source-coverage.csv'] = write_csv(coverage_rows, coverage_fields)
    output_map['member-roster.csv'] = write_csv(member_rows, member_fields)

    report['products']['gb:IND:ADM2']['bbox_candidate_pairs'] = sum(x['source_key'] == 'gb:IND:ADM2' for x in coverage_rows)
    report['products']['gb:IND:ADM3']['bbox_candidate_pairs'] = sum(x['source_key'] == 'gb:IND:ADM3' for x in coverage_rows)
    report['retained_complete_member_feature_count'] = len(components)
    report['source_coverage_row_count'] = len(coverage_rows)
    report['member_roster_row_count'] = len(member_rows)
    report['unresolved_members'] = subject_ids
    output_map['report.json'] = canonical(report)

    # Publish source custody copies and all derived tables as one exclusive fresh
    # vintage using the pinned repository writer. The manifest is finalized below.
    publisher = immutable.NewVintage(baseline, OWNED, VINTAGE, file_names)
    records = publisher.publish_bytes(output_map)
    print(json.dumps({'status': 'complete', 'published': records, 'report': report}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
