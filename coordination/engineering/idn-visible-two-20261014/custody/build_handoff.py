"""Bind the two visible IDN source cases and passive original membership.

This reuses accepted source/physical pointsets and measurements. It performs no
overlay, native allocation or selected integration, and confers no approval.
"""
import base64
import gzip
import hashlib
import io
import json
import pathlib
import resource
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OWN = HERE.parent.relative_to(ROOT).as_posix()
BASE = 'a35ba193cfe5c84424a4952ca752593ebf9d7102'
BATCH = 'gap-operational-batch:0393f64c9f8549bcfca1ace9'
COHORT = 'idn2020-visible-two-20261014'
FIT = 'research/geography/southeast-asia-gap-batch-0393f64c-20261009/vintages/source-rule-fit-005/administrative-source-rule-fit.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canon(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode()


def git(*args):
    return subprocess.check_output(['git', '-c', 'user.name=WorldAtlas Agent',
                                  '-c', 'user.email=agent@invalid', '-C', str(ROOT), *args])


def unique(rows, key):
    result = {}
    for row in rows:
        if row[key] in result:
            raise ValueError('Duplicate raw identity')
        result[row[key]] = row
    if not result:
        raise ValueError('Empty evidence roster')
    return result


def bounds(geometry):
    points = []
    def visit(value):
        if isinstance(value, list) and value and isinstance(value[0], (int, float)):
            points.append(value)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(geometry['coordinates'])
    return [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)]


def main():
    head, vintage = sys.argv[1:]
    if git('rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('Require exact committed execution HEAD')
    script = (HERE / 'build_handoff.py').relative_to(ROOT).as_posix()
    code = (ROOT / script).read_bytes()
    if code != git('show', head + ':' + script):
        raise ValueError('Unfrozen builder')
    helper_path = 'scripts/evidence/immutable.py'
    helper = git('show', head + ':' + helper_path)
    ns = {'__name__': 'phl_immutable', '__file__': str(ROOT / helper_path)}
    exec(compile(helper, ns['__file__'], 'exec'), ns)
    base = ns['Baseline'](ROOT, head, [{'path': script, 'bytes': len(code), 'sha256': sha(code), 'hash_kind': 'file-bytes'},
                                     {'path': helper_path, 'bytes': len(helper), 'sha256': sha(helper), 'hash_kind': 'file-bytes'}])
    destination = ns['NewVintage'](base, OWN + '/', vintage, ['source-handoff.json'])
    pins = {}

    def read(name, commit=BASE, expected=None, decode=False):
        tree = git('ls-tree', '-z', commit, '--', name).decode().rstrip('\0')
        fields, actual_path = tree.split('\t')
        mode, kind, blob = fields.split()
        if mode != '100644' or kind != 'blob' or actual_path != name:
            raise ValueError('Require ordinary exact input')
        size = int(git('cat-file', '-s', blob))
        base.admit(commit + ':' + name, size)
        raw = git('cat-file', 'blob', blob)
        pin = {'commit': commit, 'path': name, 'mode': mode, 'blob': blob, 'bytes': len(raw), 'sha256': sha(raw)}
        if expected and any(pin[key] != expected[key] for key in ['bytes', 'sha256']):
            raise ValueError('Whole input differs: ' + name)
        pins[commit + ':' + name] = pin
        if decode:
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw = stream.read(32 * 1024 ** 2 + 1)
            base.admit('decoded:' + commit + ':' + name, len(raw))
            if expected and (len(raw) != expected['uncompressed_bytes'] or sha(raw) != expected['uncompressed_sha256']):
                raise ValueError('Decoded input differs: ' + name)
        return raw

    def own(name):
        return read(OWN + '/' + name, head)

    config = json.loads(own('custody/physical-inputs.json'))
    ids = [r['component_id'] for r in config['components']]
    fit = json.loads(read(FIT, expected={'bytes': 1688243, 'sha256': '77aec8595ae41b03f595f28e14c05b5fa09e1a98e15a918dbe0c49cb95866f3b'}))
    unique(fit['cases'], 'component_id')
    selected_fit = [r for r in fit['cases'] if r['component_id'] in ids]
    if fit['batch_id'] != BATCH or [r['component_id'] for r in selected_fit] != ids or len(ids) != 2:
        raise ValueError('Exact retained visible two-case scope differs')
    state_path = FIT.rsplit('/', 1)[0] + '/component-state-318.json'
    family_path = FIT.rsplit('/', 1)[0] + '/family-roster-122.json'
    state = json.loads(read(state_path, expected={'bytes': 505063, 'sha256': '8aaa5d4558eb5137775c159ec234d3dc2a9a90ae965aeaaf27086a63d0462cfd'}))
    ledger = json.loads(read(family_path, expected={'bytes': 39180, 'sha256': 'acb22105b074fefca33b84488d0d0322ebdba3195a3eff4b0421f53668e651ef'}))
    states, ledger_families = unique(state['rows'], 'component_id'), unique(ledger['families'], 'family_id')
    if len(states) != 318 or len(ledger_families) != 122 or state['family_rows'] != ledger['families'] or state['batch_id'] != BATCH or ledger['batch_id'] != BATCH:
        raise ValueError('Accepted unchanged source ledger differs')
    ledger_ids = [cid for row in ledger_families.values() for cid in row['component_ids']]
    if len(ledger_ids) != 318 or len(set(ledger_ids)) != 318 or set(ledger_ids) != set(states):
        raise ValueError('Accepted ledger membership incomplete')
    for row in selected_fit:
        if row['component_id'] not in states or ledger_families[row['family_id']]['component_ids'].count(row['component_id']) != 1:
            raise ValueError('Accepted source record escaped original ledger')
    current = json.loads(own('vintages/idn-current-neighbors-001/result.json'))
    if current['scopeIds'] != ids or current['complete_owner_rows'] != 49625 or current['complete_source_parts'] != 36:
        raise ValueError('Current selected context scope incomplete')
    contexts = unique(current['rows'], 'component_id')
    foreign = json.loads(own('vintages/foreign-neighbors-001/result.json'))
    foreign_rows = {(r['component_id'], r['foreign_id']): r for r in foreign['results']}
    if len(foreign_rows) != 3 or not all(r['strictly_disjoint'] for r in foreign_rows.values()):
        raise ValueError('Complete actual foreign-neighbor predicates missing')
    # The Node-written context preserves numeric values, not Python's original
    # 0.0/0 spelling. Recover preimages only from authenticated complete banks.
    ordinary_targets = {}
    for name in ['data/geography/part-10.json']:
        context_pin = next(p for p in current['inputs'] if p['path'] == name)
        bank = unique(json.loads(read(name, expected=context_pin))['features'], 'id')
        for retained in selected_fit:
            identity = retained['compatible_recorded_subject']['record']['id']
            if identity in bank:
                if identity in ordinary_targets:
                    raise ValueError('Duplicate ordinary target across banks')
                ordinary_targets[identity] = bank[identity]
    if len(ordinary_targets) != 2:
        raise ValueError('Incomplete original target preimages')
    candidates, physical, native, restorations = [], [], [], []
    report = json.loads(read('coordination/engineering/global-physical-comparison-20261006/results/report.json'))
    report_products = unique(report['products'], 'path')
    for group in ['physical-custody-002']:
        prefix = 'vintages/' + group + '/'
        candidates.extend(json.loads(own(prefix + 'original-components.json')))
        records = json.loads(own(prefix + 'physical-records.json'))
        physical.extend(records)
        native.extend(json.loads(own(prefix + 'queried-source-metadata.json')))
        receipt = json.loads(own(prefix + 'receipt.json'))
        restorations.extend(receipt['restorations'])
        for product in receipt['restorations']:
            name = product['path']
            raw = read(OWN + '/' + prefix + name, head, report_products[name], True)
            rows = unique([json.loads(line) for line in raw.splitlines()], 'component_id')
            if len(rows) != product['rows']:
                raise ValueError('Complete original product count differs')
            for record in records:
                if record['component_id'] in rows and record != rows[record['component_id']]:
                    raise ValueError('Prepared selected physical row differs from original')
    candidates = unique(candidates, 'id')
    physical = unique(physical, 'component_id')
    native = unique(native, 'component_id')
    if any(set(rows) != set(ids) for rows in [candidates, physical, native]):
        raise ValueError('Incomplete selected custody')
    source_path = config['source_product']
    sources = unique([json.loads(line) for line in read(source_path, expected=report_products['sources-000.jsonl.gz'], decode=True).splitlines()], 'id')
    source_receipt = json.loads(read(config['source_receipt']))
    source_restoration = next(r for r in source_receipt['restorations'] if r['path'] == 'sources-000.jsonl.gz')
    restorations.append({**source_restoration, 'reused_product_path': source_path, 'reused_receipt_path': config['source_receipt']})
    if len(sources) != source_restoration['rows']:
        raise ValueError('Complete source restoration differs')

    index_prefix = 'coordination/engineering/worldwide-native-batches-1184-20261006/current-run-one/'
    index_path = index_prefix + 'report.json'
    index = json.loads(read(index_path))
    batch_pin = index['outputs']['current-operational-batches'][0]
    batches = unique(json.loads(read(batch_pin['path'], expected=batch_pin, decode=True)), 'id')
    batch = batches[BATCH]
    families = {}
    wanted_families = {r['family_id'] for r in selected_fit}
    for pin in index['outputs']['current-batches']:
        rows = unique(json.loads(read(pin['path'], expected=pin, decode=True)), 'id')
        for identity in wanted_families.intersection(rows):
            if identity in families:
                raise ValueError('Duplicate family across index parts')
            families[identity] = rows[identity]
    if index['operational_batch_count'] != 594 or index['component_count'] != 95173 or len(batches) != 594 or batch['component_count'] != 318 or len(batch['fine_family_ids']) != 122 or set(families) != wanted_families:
        raise ValueError('Original programme membership differs')
    if set(batch['fine_family_ids']) != set(ledger_families):
        raise ValueError('Accepted ledger changed original dispatch families')
    members = []
    for row in selected_fit:
        family = families[row['family_id']]
        if row['family_id'] not in batch['fine_family_ids'] or family['component_ids'].count(row['component_id']) != 1:
            raise ValueError('Original component-family-batch join differs')
        members.append({'component_id': row['component_id'], 'original_batch_id': BATCH, 'original_family_id': row['family_id']})

    registry = json.loads(read('data/administrative-sources.json'))
    catalogue = json.loads(read('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json'))
    product = next(r for r in catalogue['products'] if r['key'] == 'gb:IDN:ADM2')
    if len(product['parts']) != 1:
        raise ValueError('Unexpected consumed product partition')
    source_part = product['parts'][0]
    raw = read(source_part['path'], expected=source_part, decode=True)
    if sha(raw) != product['original_sha256'] or len(raw) != product['original_bytes'] or registry['gb:IDN:ADM2']['sha256'] != sha(raw):
        raise ValueError('Consumed source edition differs')
    features = json.loads(raw)['features']
    if len(features) != product['feature_count'] or len(features) != 519:
        raise ValueError('Incomplete IDN source')
    feature_boxes = [bounds(f['geometry']) for f in features]
    cases, physical_bindings, target_bindings, source_queries = [], [], [], []
    for retained in selected_fit:
        cid = retained['component_id']
        candidate, phys, context = candidates[cid], physical[cid], contexts[cid]
        op = retained['original_administrative_comparison']['record']
        subject = retained['compatible_recorded_subject']['record']
        if candidate != retained['current_component_candidate']['feature'] or sha(canon(candidate)) != phys['candidate_feature_sha256'] or sha(canon(candidate['geometry'])) != phys['candidate_geometry_sha256']:
            raise ValueError('Source/physical candidate identity differs')
        target_neighbors = [n for n in context['candidate_neighbors'] if n['feature']['id'] == subject['id']]
        if len(target_neighbors) != 1 or any(r['candidate_bbox_intersects'] for r in context['additive_geometry_screen']):
            raise ValueError('Current intended target/additive context differs')
        for neighbor in context['candidate_neighbors']:
            if neighbor['feature']['id'] != subject['id']:
                proof = foreign_rows.get((cid, neighbor['feature']['id']))
                if not proof or not proof['strictly_disjoint'] or proof['candidate_geometry_sha256'] != sha(canon(candidate['geometry'])) or proof['foreign_geometry_sha256'] != sha(canon(neighbor['feature']['geometry'])):
                    raise ValueError('Actual foreign target pointsets do not match exact proof')
        target = ordinary_targets[subject['id']]
        if target != target_neighbors[0]['feature'] or sha(canon(target)) != subject['original_feature_sha256'] or target['properties']['parent_id'] != subject['original_parent_id']:
            raise ValueError('Actual selected target or parent changed')
        hits = [h for h in op['feature_intersections'] if h['intersection']['planar_area_coordinate_units_squared'] > 0]
        if len(hits) != 1 or hits[0]['binding']['recorded_stable_subjects'] != [subject] or not hits[0]['source_feature_covers_entire_component']:
            raise ValueError('Retained unique full source relation differs')
        hit = hits[0]
        source_feature = features[hit['binding']['feature_index']]
        if sha(canon(source_feature)) != hit['binding']['feature_sha256'] or sha(canon(source_feature['geometry'])) != hit['binding']['geometry_sha256']:
            raise ValueError('Retained relation does not bind whole consumed feature')
        box = bounds(candidate['geometry'])
        bbox_ids = [i for i, b in enumerate(feature_boxes) if b[0] <= box[2] and b[2] >= box[0] and b[1] <= box[3] and b[3] >= box[1]]
        queries = [q for q in op['whole_product_bbox_queries'] if q['source_id'] == 'gb:IDN:ADM2']
        if len(queries) != 1 or queries[0]['complete_bbox_candidate_indices'] != bbox_ids or queries[0]['whole_product_feature_count'] != len(features):
            raise ValueError('Original complete administrative query changed')
        source_queries.append({'component_id': cid, 'complete_bbox_indices': bbox_ids})
        metadata = native[cid]['sources']
        if len(metadata) != len(phys['query_relations']) or any(sources[r['id']] != r for r in metadata):
            raise ValueError('Prepared native metadata differs from complete original')
        payload = {'component_id': cid, 'candidate_feature_sha256': phys['candidate_feature_sha256'],
                   'candidate_geometry_sha256': phys['candidate_geometry_sha256'], 'target_stable_location_id': target['id'],
                   'unsupported_candidate_remainder_included': False,
                   'source_supported_intersection_fragments': [{'intersection_geometry': hit['intersection']['geometry']}],
                   'target_current_feature': {'feature_sha256': sha(canon(target)), 'geometry_sha256': sha(canon(target['geometry'])), 'parent_id': target['properties']['parent_id']}}
        cases.append({'component_id': cid, 'original_candidate_feature': candidate, 'retained_payload': payload,
                      'retained_source_operation_row': {'source_comparison_record': op, 'positive_area_recorded_source_subject_ids': [target['id']], 'positive_area_source_feature_intersections': [hit['binding']]},
                      'original_source_rule_fit_record': retained})
        physical_bindings.append({'component_id': cid, 'physical_comparison': {'row': phys}, 'original_queried_source_metadata': [{'original_source_record_metadata': r} for r in metadata]})
        certificate_entry = target_neighbors[0]['certificate_entry']
        if certificate_entry[6] != sha(canon(target)) or certificate_entry[7] != sha(canon(target['geometry'])):
            target_bindings.append({'target_id': target['id'], 'feature_sha256': sha(canon(target)), 'feature_bytes_base64': base64.b64encode(canon(target)).decode(),
                                    'geometry_sha256': sha(canon(target['geometry'])), 'geometry_bytes_base64': base64.b64encode(canon(target['geometry'])).decode()})
    scope = {'execution_cohort_id': COHORT, 'scopeIds': ids,
             'original_gap_membership': {'version': 1, 'index': pins[BASE + ':' + index_path], 'members': members},
             'original_membership_evidence': {'epoch': 'Immutable current-at-freeze dispatch view; passive provenance only.', 'original_batch_size': 318, 'original_family_count': 122, 'programme_batches': 594, 'programme_components': 95173},
             'candidate_source_native_bindings': cases, 'original_physical_comparison_bindings': physical_bindings,
             'original_target_canonical_bindings': target_bindings,
             'consumed_source_bindings': [{'source_id': 'gb:IDN:ADM2', 'whole_bytes': len(raw), 'whole_sha256': sha(raw), 'feature_count': len(features), 'catalogue_record': product, 'registry_record': registry['gb:IDN:ADM2'], 'per_case_original_bbox_queries': source_queries}],
             'current_neighbor_binding': current, 'current_foreign_neighbor_binding': foreign,
             'physical_restoration': {'restorations': restorations, 'source_metadata_reused': True, 'component_products_restored': 2},
             'source_rule_fit_binding': pins[BASE + ':' + FIT],
             'accepted_ledger_bindings': [pins[BASE + ':' + state_path], pins[BASE + ':' + family_path]],
             'constructor_disposition': {'source_relative_premises_require_independent_review': True, 'literal_representation': 'Complete unchanged retained target plus complete original candidate primitive; no dissolve or coordinate normalization.'},
             'unknowns': ['Current physical/legal truth, observation dates, source registration accuracy, cause and repair authority remain unapproved.',
                          'Complete current envelopes and exact binary64 predicates exclude all three foreign neighbors; exact intended-target gain and native qualification remain unexecuted here.',
                          'Source/native programme registration, native-positive/zero-cell decisions, current continuous conservation, package/reader/picker/renderer and selected integration remain engineering gates.',
                          'These two visible cases do not close the original318 operational batch or alter any of the other316 states.'],
             'execution_commit': head, 'consumed_inputs': list(pins.values())}
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 256 * 1024 ** 2:
        raise ValueError('Metadata builder reservation exceeded')
    destination.publish({'source-handoff.json': scope})
    print(json.dumps({'cohort': COHORT, 'components': len(cases), 'source_admitted': False,
                      'logical_input_bytes': sum(base.consumed.values()), 'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}))


if __name__ == '__main__':
    main()
