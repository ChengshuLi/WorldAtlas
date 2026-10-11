"""Join supported full-gap cases into one v2 handoff and preserve all100 outcomes."""
import base64
import collections
import gzip
import hashlib
import json
import pathlib
import resource
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OWN = HERE.parent.relative_to(ROOT).as_posix()
BASE = '6a99a7606b9c2d11ac8cd093610653d4cd5d1382'
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def main():
    head, vintage = sys.argv[1:]
    if git('rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('Exact committed execution HEAD required')
    pins = []
    for name in ['build_handoff.py', 'handoff-inputs.json']:
        path = HERE.relative_to(ROOT).as_posix() + '/' + name
        raw = (ROOT / path).read_bytes()
        if raw != git('show', head + ':' + path):
            raise ValueError('Unfrozen handoff control')
        pins.append({'path': path, 'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'file-bytes'})
    helper_path = 'scripts/evidence/immutable.py'
    helper = git('show', head + ':' + helper_path)
    pins.append({'path': helper_path, 'bytes': len(helper), 'sha256': sha(helper), 'hash_kind': 'file-bytes'})
    ns = {'__name__': 'cohort_immutable', '__file__': str(ROOT / helper_path)}
    exec(compile(helper, ns['__file__'], 'exec'), ns)
    base = ns['Baseline'](ROOT, head, pins)
    canon = ns['canonical_json']
    destination = ns['NewVintage'](base, OWN + '/', vintage, ['source-handoff.json', 'all100-dispositions.json'])
    inputs = {}
    def read(name, commit=head, expected=None, decode=False):
        tree = git('ls-tree', '-z', commit, '--', name).decode().rstrip('\0')
        fields, actual = tree.split('\t')
        mode, kind, blob = fields.split()
        if mode != '100644' or kind != 'blob' or actual != name:
            raise ValueError('Ordinary immutable input required')
        size = int(git('cat-file', '-s', blob))
        base.admit(commit + ':' + name, size)
        raw = git('cat-file', 'blob', blob)
        pin = {'commit': commit, 'path': name, 'mode': mode, 'blob': blob, 'bytes': len(raw), 'sha256': sha(raw)}
        if expected:
            for key in ['bytes', 'sha256']:
                if pin[key] != expected[key]:
                    raise ValueError('Whole immutable input drift: ' + name)
        inputs[commit + ':' + name] = pin
        if decode:
            maximum = (expected or {}).get('uncompressed_bytes', 32 * 1024 ** 2)
            import io
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw = stream.read(maximum + 1)
            base.admit('decoded:' + commit + ':' + name, len(raw))
            if expected and 'uncompressed_bytes' in expected and (len(raw) != expected['uncompressed_bytes'] or sha(raw) != expected['uncompressed_sha256']):
                raise ValueError('Whole decoded input drift')
        return raw
    own = lambda name: json.loads(read(OWN + '/' + name))
    config = own('cohort100-20261011/handoff-inputs.json')
    roster = own('cohort100-20261011/roster.json')
    strict = own('vintages/cohort100-strict-001/strict-predicates.json')
    physical_prefix = 'vintages/cohort100-physical-custody-001/'
    candidates = {r['id']: r for r in own(physical_prefix + 'original-components.json')}
    physical = {r['component_id']: r for r in own(physical_prefix + 'physical-records.json')}
    native = {r['component_id']: r for r in own(physical_prefix + 'queried-source-metadata.json')}
    restoration = own(physical_prefix + 'receipt.json')
    current = own('vintages/cohort100-current-neighbors-001/result.json')
    originals = own('vintages/cohort100-original-classification-001/original-comparison-rows.json')
    comparisons = {r['comparison']['component']: r for r in originals}
    custody = {r['component_id']: r for r in own('vintages/cohort100-original-candidates-001/original-candidates.json')}
    prior_dispositions = own('vintages/cohort100-original-classification-001/dispositions.json')
    selected_ids = config['component_ids']
    if len(selected_ids) != len(set(selected_ids)) or not set(selected_ids).issubset(candidates) or set(selected_ids).intersection(roster['previously_selected_excluded_ids']):
        raise ValueError('Foreign/duplicate/previously selected execution member')
    if strict['baseline_commit'] != BASE or current['baseline'] != BASE or strict['scientific_or_publication_approval'] is not False:
        raise ValueError('Wrong current numerical premises')
    measured = {r['component_id']: r for r in strict['results']}
    if set(selected_ids).intersection(config['held_necessary_only_ids']) or any(measured[cid]['failed_predicates'] for cid in selected_ids):
        raise ValueError('Failed numerical case cannot enter producer handoff')
    # Reauthenticate whole original physical products, including nonselected rows.
    report = json.loads(read('coordination/engineering/global-physical-comparison-20261006/results/report.json', BASE))
    report_products = {p['path']: p for p in report['products']}
    physical_config = own('cohort100-20261011/physical-inputs.json')
    for binding in physical_config['components']:
        name, cid = binding['comparison_product'], binding['component_id']
        raw = read(OWN + '/' + physical_prefix + name, expected=report_products[name], decode=True)
        rows = [json.loads(line) for line in raw.splitlines()]
        if len({r['component_id'] for r in rows}) != len(rows) or [r for r in rows if r['component_id'] == cid] != [physical[cid]]:
            raise ValueError('Whole original physical record differs')
    source_restoration = next(r for r in restoration['restorations'] if r['path'] == 'sources-000.jsonl.gz')
    raw = read(source_restoration['reused_product_path'], BASE, report_products['sources-000.jsonl.gz'], True)
    source_rows = [json.loads(line) for line in raw.splitlines()]
    source_by_id = {r['id']: r for r in source_rows}
    if len(source_by_id) != len(source_rows):
        raise ValueError('Duplicate original native metadata')
    for item in native.values():
        if any(source_by_id[r['id']] != r for r in item['sources']):
            raise ValueError('Original complete queried native metadata differs')
    # Independent whole original index/batch/family membership joins.
    index_path = roster['original_index']['path']
    index = json.loads(read(index_path, BASE, roster['original_index']))
    outputs = {p['path']: p for group in index['outputs'].values() for p in group}
    families, batches = {}, {}
    for product in roster['input_products']:
        rows = json.loads(read(product['path'], BASE, outputs[product['path']], True))
        target = batches if 'current-operational-batches-' in product['path'] else families
        for row in rows:
            if row['id'] in target:
                raise ValueError('Duplicate complete original index identity')
            target[row['id']] = row
    if len(batches) != 594 or index['component_count'] != 95173:
        raise ValueError('Original programme denominator differs')
    members = {r['component_id']: r for r in roster['original_gap_membership']}
    for cid in roster['candidate_ids']:
        m = members[cid]
        if m['original_family_id'] not in batches[m['original_batch_id']]['fine_family_ids'] or cid not in families[m['original_family_id']]['component_ids']:
            raise ValueError('Original full-gap membership differs')
    registry = json.loads(read('data/administrative-sources.json', BASE))
    catalogue = json.loads(read('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json', BASE))
    consumed = []
    for country in ['AGO', 'COD']:
        key = 'gb:' + country + ':ADM2'
        raw = read(OWN + '/sources/administrative/gb-' + country + '-ADM2-ADM2-consumed-simplified.geojson', BASE)
        product = next(p for p in catalogue['products'] if p['key'] == key)
        if sha(raw) != product['original_sha256'] or len(raw) != product['original_bytes'] or registry[key]['sha256'] != sha(raw):
            raise ValueError('Original consumed source edition differs')
        features = json.loads(raw)['features']
        if len(features) != product['feature_count']:
            raise ValueError('Incomplete consumed source product')
        consumed.append({'source_id': key, 'whole_bytes': len(raw), 'whole_sha256': sha(raw), 'feature_count': len(features), 'catalogue_record': product, 'registry_record': registry[key]})
    cases, physical_bindings, candidate_bindings = [], [], []
    target_bindings = {}
    for cid in selected_ids:
        candidate, comparison = candidates[cid], comparisons[cid]['comparison']
        context = next(r for r in current['rows'] if r['component_id'] == cid)
        target_id = comparison['uniquely_covering_compatible_recorded_subject']['id']
        target = next(r['feature'] for r in context['candidate_neighbors'] if r['feature']['id'] == target_id)
        if sha(canon(candidate)) != physical[cid]['candidate_feature_sha256'] or sha(canon(candidate)) != comparison['full_component_feature_sha256'] or candidate != custody[cid]['feature'] or sha(canon(target)) != measured[cid]['current_target_feature_sha256']:
            raise ValueError('Full original/source/physical/current identity differs')
        positive = [r for r in comparison['feature_intersections'] if r['intersection']['planar_area_coordinate_units_squared'] > 0]
        if comparison['status'] != 'one-compatible-recorded-subject-uniquely-covers-component' or len(positive) != 1 or not positive[0]['source_feature_covers_entire_component']:
            raise ValueError('Original unique-source premise differs')
        payload = {'component_id': cid, 'candidate_feature_sha256': sha(canon(candidate)), 'candidate_geometry_sha256': physical[cid]['candidate_geometry_sha256'], 'target_stable_location_id': target_id, 'unsupported_candidate_remainder_included': False, 'source_supported_intersection_fragments': [{'intersection_geometry': positive[0]['intersection']['geometry']}], 'target_current_feature': {'feature_sha256': sha(canon(target)), 'geometry_sha256': sha(canon(target['geometry'])), 'parent_id': target['properties']['parent_id']}}
        cases.append({'component_id': cid, 'original_candidate_feature': candidate, 'retained_payload': payload, 'retained_source_operation_row': {'source_comparison_record': comparison, 'positive_area_recorded_source_subject_ids': [target_id], 'positive_area_source_feature_intersections': [r['binding'] for r in positive]}})
        physical_bindings.append({'component_id': cid, 'physical_comparison': {'row': physical[cid]}, 'original_queried_source_metadata': [{'original_source_record_metadata': r} for r in native[cid]['sources']]})
        candidate_bindings.append({'component_id': cid, 'feature_sha256': sha(canon(candidate)), 'feature_bytes_base64': base64.b64encode(canon(candidate)).decode(), 'derived_js_canonical_sha256': context['derived_js_feature_sha256']})
        target_bindings[target_id] = {'target_id': target_id, 'feature_sha256': sha(canon(target)), 'feature_bytes_base64': base64.b64encode(canon(target)).decode(), 'geometry_sha256': sha(canon(target['geometry'])), 'geometry_bytes_base64': base64.b64encode(canon(target['geometry'])).decode()}
    historical = own('cohort100-20261011/historical-cod5-checkpoint.json')
    historical_results = {r['component']: r for r in historical['results']}
    all_dispositions = []
    for old in prior_dispositions:
        cid = old['component_id']
        row = {**old, 'retained_detector_area_m2': custody[cid]['retained_detector_area_m2'], 'resolved': False}
        if cid in historical_results:
            row.update(disposition='retained-prior-strict-target-premise-failure-not-reexecuted', historical_observation=historical_results[cid], historical_checkpoint=config['historical_checkpoint'])
        elif cid in measured:
            row.update(disposition=('source-relative-supported-awaiting-independent-review' if cid in selected_ids else 'necessary-only-held-source-sufficiency' if cid in config['held_necessary_only_ids'] else 'current-target-positive-overlap-refused'), current_numerical_observation=measured[cid])
        all_dispositions.append(row)
    if len(all_dispositions) != 100 or {r['component_id'] for r in all_dispositions} != set(roster['candidate_ids']):
        raise ValueError('Incomplete full wave dispositions')
    scope = {'execution_cohort_id': config['execution_cohort_id'], 'scopeIds': selected_ids,
        'original_gap_membership': {'version': 1, 'index': inputs[BASE + ':' + index_path], 'members': [members[cid] for cid in selected_ids]},
        'original_membership_evidence': {'programme_batches': 594, 'programme_components': 95173, 'wave_components': 100, 'excluded_previously_selected': roster['previously_selected_excluded_ids'], 'roster_path': OWN + '/cohort100-20261011/roster.json', 'roster_sha256': inputs[head + ':' + OWN + '/cohort100-20261011/roster.json']['sha256'], 'batches': [batches[i] for i in sorted({members[cid]['original_batch_id'] for cid in selected_ids})], 'families': [families[i] for i in sorted({members[cid]['original_family_id'] for cid in selected_ids})]},
        'candidate_source_native_bindings': cases, 'original_physical_comparison_bindings': physical_bindings,
        'original_candidate_canonical_bindings': candidate_bindings, 'original_target_canonical_bindings': list(target_bindings.values()),
        'consumed_source_bindings': consumed, 'current_neighbor_binding': current, 'physical_restoration': restoration,
        'retained_necessary_predicates': {'execution_commit': strict['execution_head'], 'path': OWN + '/vintages/cohort100-strict-001/strict-predicates.json', 'sha256': inputs[head + ':' + OWN + '/vintages/cohort100-strict-001/strict-predicates.json']['sha256'], 'method': 'One actual current-context numerical execution; no duplicate-only rerun.'},
        'constructor_disposition': {'source_relative_premises_supported': True, 'source_admission_requires_independent_review': True, 'literal_representation': 'Complete unchanged retained target plus complete unchanged candidate primitive; no dissolve or coordinate normalization.'},
        'unknowns': ['Independent source review is required before this proposed handoff is admitted.', 'Physical/legal/current truth, original observation dates and processing cause remain unapproved.', 'Numerical dissolve diagnostics and all held cases remain explicit in the full100 packet.', 'SOURCE/NATIVE, selected continuous conservation and application delivery remain engineering work.', 'Accepted execution membership does not close the original100 wave, original ten,130 batch or global programme.'],
        'execution_commit': head, 'consumed_inputs': list(inputs.values())}
    summary = {'scope_count': 100, 'execution_scope_proposed': selected_ids, 'disposition_counts': dict(collections.Counter(r['disposition'] for r in all_dispositions)), 'rows': all_dispositions, 'scientific_or_publication_approval': False}
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > 512 * 1024 ** 2:
        raise ValueError('Metadata process reservation exceeded')
    destination.publish({'source-handoff.json': scope, 'all100-dispositions.json': summary})
    print(json.dumps({'cohort': config['execution_cohort_id'], 'proposed_members': selected_ids, 'all_dispositions': len(all_dispositions), 'logical_input_bytes': sum(base.consumed.values()), 'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}))

if __name__ == '__main__':
    main()
