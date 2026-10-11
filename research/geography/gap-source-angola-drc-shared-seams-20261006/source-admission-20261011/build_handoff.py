"""Bind two complete source-compatible cases without admitting held old cases.

This performs exact custody/identity joins and reuses unchanged original numeric
evidence. It neither reruns GIS nor approves native integration/current truth.
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
BASE = 'c3293051718839b08127db7b058536a87997a0c6'
CHECKPOINT = 'c827ea9314c6b5437183a5de0cd874c971d424df'
CHECKPOINT_RESULT = '9c6c1467f56737d0ad5565d12e31a53e4ab27638'
IDS = ['physical-component:4ceb0de66be41e24e9e2f640442ec3ae3690a7d134d73cfbe2a6ac01edf098d4',
       'physical-component:d70ba927292a3f812f481885193f21b099328f0697ff13fea7585dac7a8118c2']
TARGET = 'gb:AGO:ADM2:16411231B62076307190429'
NEIGHBOR = 'gb:COD:ADM2:63176286B94968684087840'
BATCH = 'gap-operational-batch:fd46e2f61cf28daed6ad024b'
FAMILY = 'gap-source-batch:80eb2e392d5ef4fe3781d37a'
COHORT = 'congo-ago2018-two-20261011'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
canon = lambda value: (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode()


def git(*args):
    return subprocess.check_output(['git', '-c', 'user.name=WorldAtlas Agent',
                                  '-c', 'user.email=agent@invalid', '-C', str(ROOT), *args])


def same_ring(a, b):
    if a[0] != a[-1] or b[0] != b[-1]:
        return False
    a, b = a[:-1], b[:-1]
    return len(a) == len(b) and any(a == b[i:] + b[:i] for i in range(len(b)))


def same_polygon(a, b):
    return a['type'] == b['type'] == 'Polygon' and len(a['coordinates']) == len(b['coordinates']) and all(same_ring(x, y) for x, y in zip(a['coordinates'], b['coordinates']))


def bounds(geometry):
    points = []
    def visit(v):
        if isinstance(v, list) and v and isinstance(v[0], (int, float)):
            points.append(v)
        elif isinstance(v, list):
            for child in v:
                visit(child)
    visit(geometry['coordinates'])
    return [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)]


def main():
    head, vintage = sys.argv[1:]
    if git('rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('Exact committed execution HEAD required')
    script = (HERE / 'build_handoff.py').relative_to(ROOT).as_posix()
    code = (ROOT / script).read_bytes()
    if code != git('show', head + ':' + script):
        raise ValueError('Unfrozen builder')
    helper_path = 'scripts/evidence/immutable.py'
    helper = git('show', head + ':' + helper_path)
    ns = {'__name__': 'congo_immutable', '__file__': str(ROOT / helper_path)}
    exec(compile(helper, ns['__file__'], 'exec'), ns)
    base = ns['Baseline'](ROOT, head, [{'path': script, 'bytes': len(code), 'sha256': sha(code), 'hash_kind': 'file-bytes'}, {'path': helper_path, 'bytes': len(helper), 'sha256': sha(helper), 'hash_kind': 'file-bytes'}])
    destination = ns['NewVintage'](base, OWN + '/', vintage, ['source-handoff.json'])
    pins = {}
    def read(name, commit=BASE, expected=None, decode=False):
        tree = git('ls-tree', '-z', commit, '--', name).decode().rstrip('\0')
        fields, actual_path = tree.split('\t')
        mode, kind, blob = fields.split()
        if mode != '100644' or kind != 'blob' or actual_path != name:
            raise ValueError('Ordinary exact input required')
        size = int(git('cat-file', '-s', blob))
        base.admit(commit + ':' + name, size)
        raw = git('cat-file', 'blob', blob)
        pin = {'commit': commit, 'path': name, 'mode': mode, 'blob': blob, 'bytes': len(raw), 'sha256': sha(raw)}
        if expected:
            for key in ['bytes', 'sha256']:
                if pin[key] != expected[key]:
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

    p = 'vintages/congo-physical-custody-002/'
    candidates = json.loads(own(p + 'original-components.json'))
    physical = json.loads(own(p + 'physical-records.json'))
    native = json.loads(own(p + 'queried-source-metadata.json'))
    restoration = json.loads(own(p + 'receipt.json'))
    current = json.loads(own('vintages/congo-current-neighbors-001/result.json'))
    strict_path = OWN + '/vintages/substantial-two-strict-001/strict-predicates.json'
    strict = json.loads(read(strict_path, head, {'bytes': 10887, 'sha256': '790a5ef43b55168b568b7549b322ba02ec49143d0b325ad949c3196ee4b35f26'}))
    if strict['execution_head'] != CHECKPOINT or strict['scientific_or_publication_approval'] is not False:
        raise ValueError('Wrong necessary-predicate checkpoint')
    if [c['id'] for c in candidates] != IDS or [r['component_id'] for r in physical] != IDS or [r['component_id'] for r in native] != IDS or current['scopeIds'] != IDS:
        raise ValueError('Missing, duplicate or reordered case scope')
    # Reauthenticate each whole original physical product and selected row.
    report_path = 'coordination/engineering/global-physical-comparison-20261006/results/report.json'
    report = json.loads(read(report_path))
    for name, selected_rows in [('components-021.jsonl.gz', [physical[0]]), ('components-059.jsonl.gz', [physical[1]]), ('sources-000.jsonl.gz', native[0]['sources'])]:
        descriptor = next(d for d in report['products'] if d['path'] == name)
        product_path = OWN + '/' + p + name if name.startswith('components') else restoration['restorations'][2]['reused_product_path']
        raw = read(product_path, head if name.startswith('components') else BASE, descriptor, True)
        rows = [json.loads(line) for line in raw.splitlines()]
        key = 'component_id' if name.startswith('components') else 'id'
        if len({r[key] for r in rows}) != len(rows):
            raise ValueError('Duplicate whole product row')
        for selected in selected_rows:
            if [r for r in rows if r[key] == selected[key]] != [selected]:
                raise ValueError('Selected row differs from original full product')
    # This is the immutable current-at-freeze dispatch epoch used by issue1243.
    # Earlier frozen-native fine-family IDs are a distinct view, never relabeled.
    index_prefix = 'coordination/engineering/worldwide-native-batches-1184-20261006/current-run-one/'
    index_path = index_prefix + 'report.json'
    index = json.loads(read(index_path))
    outputs = {d['path']: d for group in index['outputs'].values() for d in group}
    batch_path = index_prefix + 'current-operational-batches-000.json.gz'
    family_path = index_prefix + 'current-batches-002.json.gz'
    batches = json.loads(read(batch_path, expected=outputs[batch_path], decode=True))
    families = json.loads(read(family_path, expected=outputs[family_path], decode=True))
    batch = next(r for r in batches if r['id'] == BATCH)
    family = next(r for r in families if r['id'] == FAMILY)
    if index['operational_batch_count'] != 594 or index['component_count'] != 95173 or len(batches) != 594 or batch['component_count'] != 130 or family['component_count'] != 10 or FAMILY not in batch['fine_family_ids'] or not set(IDS).issubset(family['component_ids']):
        raise ValueError('Original programme membership mismatch')
    registry = json.loads(read('data/administrative-sources.json'))
    catalogue = json.loads(read('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json'))
    source_features = {}
    consumed = []
    for country in ['AGO', 'COD']:
        key = 'gb:' + country + ':ADM2'
        raw = read(OWN + '/sources/administrative/gb-' + country + '-ADM2-ADM2-consumed-simplified.geojson', BASE)
        product = next(r for r in catalogue['products'] if r['key'] == key)
        if sha(raw) != product['original_sha256'] or len(raw) != product['original_bytes'] or registry[key]['sha256'] != sha(raw):
            raise ValueError('Consumed source edition differs')
        features = json.loads(raw)['features']
        if len(features) != product['feature_count']:
            raise ValueError('Incomplete consumed source')
        source_features[key] = features
        consumed.append({'source_id': key, 'whole_bytes': len(raw), 'whole_sha256': sha(raw), 'feature_count': len(features), 'catalogue_record': product, 'registry_record': registry[key]})
    cases, physical_bindings, candidate_bindings = [], [], []
    target_bindings = {}
    for i, candidate in enumerate(candidates):
        cid = candidate['id']
        phys, meta, context = physical[i], native[i], current['rows'][i]
        prior = next(r for r in strict['results'] if r['component'] == cid)
        if prior['failed_predicates'] or prior['candidate_feature_sha256'] != sha(canon(candidate)) or candidate['geometry'] != prior['candidate_geometry']:
            raise ValueError('Necessary predicate does not bind full candidate')
        compare_path = 'coordination/engineering/global-source-comparisons-b-20261006/source-comparisons-b-package2/scientific/components-' + ('015' if i == 0 else '041') + '.json.gz'
        comparisons = json.loads(read(compare_path, decode=True))
        comparison = next(r for r in comparisons if r['component'] == cid)
        if phys['candidate_feature_sha256'] != sha(canon(candidate)) or comparison['full_component_feature_sha256'] != phys['candidate_feature_sha256'] or comparison['component_geometry_sha256'] != phys['candidate_geometry_sha256'] or sha(canon(candidate['geometry'])) != phys['candidate_geometry_sha256']:
            raise ValueError('Original source/physical/candidate identity mismatch')
        if not same_polygon(candidate['geometry'], phys['complete_support']['mapped_land_support']['geometry']):
            raise ValueError('Whole physical support differs')
        neighbors = {r['feature']['id']: r for r in context['candidate_neighbors']}
        if set(neighbors) != {TARGET, NEIGHBOR} or not all(not r['candidate_bbox_intersects'] for r in context['additive_geometry_screen']):
            raise ValueError('Unexpected current neighbor/addition requires new predicates')
        target = neighbors[TARGET]['feature']
        if sha(canon(target)) != prior['current_target_feature_sha256']:
            raise ValueError('Current selected target differs from tested original')
        for hit in prior['current_neighbor_hits']:
            if sha(canon(neighbors[hit['id']]['feature'])) != hit['whole_current_feature_sha256'] or hit['positive_area']:
                raise ValueError('Current selected neighbor differs from retained zero-area predicate')
        if {h['id'] for h in prior['current_neighbor_hits']} != set(neighbors):
            raise ValueError('Unproven possible neighbor')
        for key, features in source_features.items():
            box = bounds(candidate['geometry'])
            hits = [j for j, f in enumerate(features) if (lambda b: b[0] <= box[2] and b[2] >= box[0] and b[1] <= box[3] and b[3] >= box[1])(bounds(f['geometry']))]
            query = next(r for r in comparison['whole_product_bbox_queries'] if r['source_id'] == key)
            if hits != query['complete_bbox_candidate_indices'] or len(features) != query['whole_product_feature_count']:
                raise ValueError('Incomplete original source query')
            for j in hits:
                retained = next(r for r in comparison['feature_intersections'] if r['binding']['source_id'] == key and r['binding']['feature_index'] == j)
                if sha(canon(features[j])) != retained['binding']['feature_sha256'] or sha(canon(features[j]['geometry'])) != retained['binding']['geometry_sha256']:
                    raise ValueError('Consumed whole source feature differs')
        positive = [r for r in comparison['feature_intersections'] if r['intersection']['planar_area_coordinate_units_squared'] > 0]
        if comparison['status'] != 'one-compatible-recorded-subject-uniquely-covers-component' or comparison['uniquely_covering_compatible_recorded_subject']['id'] != TARGET or len(positive) != 1 or not positive[0]['source_feature_covers_entire_component'] or not same_polygon(candidate['geometry'], positive[0]['intersection']['geometry']):
            raise ValueError('Unique retained administrative coverage differs')
        payload = {'component_id': cid, 'candidate_feature_sha256': sha(canon(candidate)), 'candidate_geometry_sha256': phys['candidate_geometry_sha256'], 'target_stable_location_id': TARGET, 'unsupported_candidate_remainder_included': False, 'source_supported_intersection_fragments': [{'intersection_geometry': positive[0]['intersection']['geometry']}], 'target_current_feature': {'feature_sha256': sha(canon(target)), 'geometry_sha256': sha(canon(target['geometry'])), 'parent_id': target['properties']['parent_id']}}
        cases.append({'component_id': cid, 'original_candidate_feature': candidate, 'retained_payload': payload, 'retained_source_operation_row': {'source_comparison_record': comparison, 'positive_area_recorded_source_subject_ids': [TARGET], 'positive_area_source_feature_intersections': [r['binding'] for r in positive]}})
        physical_bindings.append({'component_id': cid, 'physical_comparison': {'row': phys}, 'original_queried_source_metadata': [{'original_source_record_metadata': r} for r in meta['sources']]})
        candidate_bindings.append({'component_id': cid, 'feature_sha256': sha(canon(candidate)), 'feature_bytes_base64': base64.b64encode(canon(candidate)).decode(), 'derived_js_canonical_sha256': context['derived_js_feature_sha256']})
        target_bindings[TARGET] = {'target_id': TARGET, 'feature_sha256': sha(canon(target)), 'feature_bytes_base64': base64.b64encode(canon(target)).decode(), 'geometry_sha256': sha(canon(target['geometry'])), 'geometry_bytes_base64': base64.b64encode(canon(target['geometry'])).decode()}
    scope = {'execution_cohort_id': COHORT, 'scopeIds': IDS,
             'original_gap_membership': {'version': 1, 'index': pins[BASE + ':' + index_path], 'members': [{'component_id': cid, 'original_batch_id': BATCH, 'original_family_id': FAMILY} for cid in IDS]},
             'original_membership_evidence': {'epoch': 'Immutable current-at-freeze dispatch view used by issue1243; distinct from the earlier frozen-native fine-family namespace.', 'batch': batch, 'family': family, 'batch_product': pins[BASE + ':' + batch_path], 'family_product': pins[BASE + ':' + family_path], 'programme_batches': 594, 'programme_components': 95173},
             'candidate_source_native_bindings': cases, 'original_physical_comparison_bindings': physical_bindings,
             'original_candidate_canonical_bindings': candidate_bindings, 'original_target_canonical_bindings': list(target_bindings.values()),
             'consumed_source_bindings': consumed, 'current_neighbor_binding': current, 'physical_restoration': restoration,
             'retained_necessary_predicates': {'commit': head, 'original_retention_commit': CHECKPOINT_RESULT, 'execution_commit': CHECKPOINT, 'path': strict_path, 'sha256': pins[head + ':' + strict_path]['sha256'], 'reuse': 'Original candidate, target and every actual possible-neighbor complete feature match. Prior numerical results are reused, not a new execution.'},
             'constructor_disposition': {'source_relative_premises_supported': True, 'source_admission_requires_independent_review': True, 'literal_representation': 'Complete unchanged retained target plus complete unchanged candidate primitive; no dissolve or coordinate normalization.'},
             'unknowns': ['Current physical or legal truth, source observation dates and processing cause remain unapproved.', 'Known execution blocker at frozen c3293051: SOURCE current-baseline and NATIVE reuse admit only ordinary-immutable-git-source target banks, while actual Cuango is in the selected encoded part-29 override. Engineering must admit and authenticate that real encoded override before execution; relabeling or old-base substitution is forbidden.', 'Native operator, native window admission, selected continuous conservation, package/reader/picker/renderer delivery and release readback remain engineering work.', 'The two cases do not close the ten-case family, the130-member original operational batch, or any other original accounting.'],
             'execution_commit': head, 'consumed_inputs': list(pins.values())}
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 512 * 1024 ** 2:
        raise ValueError('Builder process reservation exceeded')
    destination.publish({'source-handoff.json': scope})
    print(json.dumps({'cohort': COHORT, 'components': len(cases), 'source_admitted': False, 'physical_authority': [r['physical_authority'] for r in physical], 'logical_input_bytes': sum(base.consumed.values()), 'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}))


if __name__ == '__main__':
    main()
