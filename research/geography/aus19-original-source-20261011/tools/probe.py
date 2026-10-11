"""Unchanged source/current necessary predicates for 19 original full gaps.

Current geometries come from the genuine selected-context reader. The accepted
literal representation retains the unchanged target and candidate primitives;
dissolve measurements are reported separately and never fabricate membership.
"""
import hashlib
import json
import os
import pathlib
import resource
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OWN = HERE.parent.relative_to(ROOT).as_posix()
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def main():
    head, vintage = sys.argv[1:]
    if git('rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('Exact execution HEAD required')
    controls = {}
    for name in ['probe.py', 'probe-inputs.json']:
        raw = (HERE / name).read_bytes()
        if raw != git('show', head + ':' + HERE.relative_to(ROOT).as_posix() + '/' + name):
            raise ValueError('Unfrozen scientific control')
        controls[name] = raw
    plan = json.loads(controls['probe-inputs.json'])
    runtime_raw = git('show', head + ':' + plan['runtime_inventory']['path'])
    if len(runtime_raw) != plan['runtime_inventory']['bytes'] or sha(runtime_raw) != plan['runtime_inventory']['sha256']:
        raise ValueError('Wrong runtime inventory')
    runtime = json.loads(runtime_raw)
    charge = runtime['logical_bytes'] + len(runtime_raw) + sum(map(len, controls.values()))
    charge += sum(p['bytes'] for p in plan['files']) + plan['output_reserve_bytes'] + 4096
    if charge > 256 * 1024 ** 2:
        raise ValueError('Complete prospective input/runtime/output cap exceeded')
    if pathlib.Path(sys.executable).resolve() != pathlib.Path(runtime['python_executable']).resolve():
        raise ValueError('Wrong interpreter')
    if not os.environ.get('PYTHONDONTWRITEBYTECODE') or not os.environ.get('PYTHONPYCACHEPREFIX'):
        raise ValueError('Read-only scientific runtime required')
    for pin in runtime['files']:
        raw = pathlib.Path(pin['path']).read_bytes()
        if len(raw) != pin['bytes'] or sha(raw) != pin['sha256']:
            raise ValueError('Runtime drift: ' + pin['path'])
    helper_pin = next(p for p in plan['files'] if p['path'] == 'scripts/evidence/immutable.py')
    helper = git('show', head + ':' + helper_pin['path'])
    if sha(helper) != helper_pin['sha256'] or len(helper) != helper_pin['bytes']:
        raise ValueError('Immutable helper drift')
    ns = {'__name__': 'cohort_immutable', '__file__': str(ROOT / helper_pin['path'])}
    exec(compile(helper, ns['__file__'], 'exec'), ns)
    base = ns['Baseline'](ROOT, head, plan['files'])
    for pin in runtime['files']:
        base.admit('runtime:' + pin['path'], pin['bytes'])
    for name, raw in controls.items():
        base.admit('control:' + name, len(raw))
    base.admit('runtime-inventory', len(runtime_raw))
    base.admit('output-reserve', plan['output_reserve_bytes'])
    dest = ns['NewVintage'](base, OWN + '/', vintage, ['strict-predicates.json'])
    canon = ns['canonical_json']
    read = lambda name: json.loads(base.pinned_bytes(OWN + '/' + name))
    candidates = read('vintages/candidate-custody-001/original-components.json')
    current = read('vintages/current-neighbors-001/result.json')
    original_rows = read('vintages/administrative-custody-002/comparison-rows.json')
    comparisons = {r['component']: r for r in original_rows}
    ids = [c['id'] for c in candidates]
    if ids != plan['component_ids'] or ids != current['scopeIds']:
        raise ValueError('Changed original scope or joins')
    if current['baseline'] != plan['current_baseline'] or current['selected_active_primitives'] != 47 or current['complete_owner_rows'] != 49625:
        raise ValueError('Wrong current selected context')
    from shapely.geometry import shape, mapping
    from shapely.validation import explain_validity
    import shapely, numpy
    if (shapely.__version__, shapely.geos_version_string, numpy.__version__) != (runtime['shapely'], runtime['geos'], runtime['numpy']):
        raise ValueError('Wrong scientific library versions')
    exact = base.load_modules({'exact_predicates': 'scripts/evidence/exact_predicates.py'})['exact_predicates']
    sources = {}
    for country in ['AUS']:
        product = read('vintages/administrative-custody-002/consumed-source.geojson')
        if product.get('crs', {}).get('properties', {}).get('name') != 'urn:ogc:def:crs:OGC:1.3:CRS84':
            raise ValueError('Wrong consumed CRS/axis')
        for feature in product['features']:
            p = feature['properties']
            identity = 'gb:' + p['shapeGroup'] + ':' + p['shapeType'] + ':' + p['shapeID']
            if identity in sources:
                raise ValueError('Duplicate consumed source subject')
            sources[identity] = feature
    if len(sources) != 547:
        raise ValueError('Incomplete consumed source products')
    source_geoms = {i: shape(f['geometry']) for i, f in sources.items()}
    candidate_geoms = {c['id']: shape(c['geometry']) for c in candidates}
    addition_geoms = {r['component_id']: shape(r['geometry']) for r in current['current_additions']}
    started = time.monotonic()
    results = []
    for cf, context in zip(candidates, current['rows']):
        cid = cf['id']
        prior = comparisons[cid]
        subject = prior['uniquely_covering_compatible_recorded_subject']
        target = subject['id']
        neighbors = {r['feature']['id']: r['feature'] for r in context['candidate_neighbors']}
        if target not in neighbors or prior['full_component_feature_sha256'] != sha(canon(cf)):
            raise ValueError('Original full candidate/target custody differs')
        tf, sf = neighbors[target], sources[target]
        if tf['properties']['parent_id'] != subject['original_parent_id']:
            raise ValueError('Original stable target parent changed')
        cg, tg, sg = candidate_geoms[cid], shape(tf['geometry']), source_geoms[target]
        predicates = {'candidate_valid': cg.is_valid, 'candidate_nonempty': not cg.is_empty,
                      'current_target_valid': tg.is_valid, 'consumed_target_source_valid': sg.is_valid}
        exact_status = 'valid'
        try:
            exact.prepare_geometry(cf['geometry'])
        except exact.DiagnosticError as exc:
            exact_status = exc.status + ':' + exc.reason
        predicates['exact_binary64_candidate_topology'] = exact_status == 'valid'
        source_hits, neighbor_hits, addition_hits, cohort_hits, residuals = [], [], [], [], {}
        current_coverage = {'status': 'unresolved-invalid-input', 'proved_full_current_coverage': False}
        if all(predicates.values()):
            predicates['consumed_target_source_covers_candidate'] = sg.covers(cg)
            overlap = cg.intersection(tg)
            predicates['candidate_current_target_no_positive_area_overlap'] = overlap.area == 0
            proposal = tg.union(cg)
            gain, loss = proposal.difference(tg), tg.difference(proposal)
            residuals = {'source_uncovered_candidate': mapping(cg.difference(sg)),
                         'candidate_current_target_intersection': mapping(overlap),
                         'diagnostic_dissolved_gain': mapping(gain), 'diagnostic_dissolved_loss': mapping(loss),
                         'candidate_dissolved_gain_symmetric_difference': mapping(cg.symmetric_difference(gain))}
            for identity, geometry in source_geoms.items():
                if not cg.envelope.intersects(geometry.envelope):
                    continue
                row = {'id': identity, 'whole_source_feature_sha256': sha(canon(sources[identity])), 'valid': geometry.is_valid}
                if geometry.is_valid:
                    hit = cg.intersection(geometry)
                    row.update(covers_candidate=geometry.covers(cg), positive_area=hit.area > 0, intersection=mapping(hit))
                else:
                    row['reason'] = explain_validity(geometry)
                source_hits.append(row)
            for identity, feature in neighbors.items():
                geometry = shape(feature['geometry'])
                row = {'id': identity, 'whole_current_feature_sha256': sha(canon(feature)), 'valid': geometry.is_valid}
                if geometry.is_valid:
                    hit = cg.intersection(geometry)
                    row.update(positive_area=hit.area > 0, covers_candidate=geometry.covers(cg), intersection=mapping(hit))
                else:
                    row['reason'] = explain_validity(geometry)
                neighbor_hits.append(row)
            for screen in context['additive_geometry_screen']:
                if not screen['candidate_bbox_intersects']:
                    continue
                geometry = addition_geoms[screen['component_id']]
                row = {**screen, 'valid': geometry.is_valid}
                if geometry.is_valid:
                    hit = cg.intersection(geometry)
                    row.update(positive_area=hit.area > 0, covers_candidate=geometry.covers(cg), intersection=mapping(hit))
                else:
                    row['reason'] = explain_validity(geometry)
                addition_hits.append(row)
            for other in candidates:
                if other['id'] == cid:
                    continue
                geometry = candidate_geoms[other['id']]
                if cg.envelope.intersects(geometry.envelope):
                    hit = cg.intersection(geometry)
                    cohort_hits.append({'component_id': other['id'], 'positive_area': hit.area > 0, 'intersection': mapping(hit)})
            valid_current = all(r['valid'] for r in neighbor_hits + addition_hits)
            if valid_current:
                complete_union = shapely.union_all([shape(f['geometry']) for f in neighbors.values()] +
                    [addition_geoms[r['component_id']] for r in addition_hits])
                uncovered = cg.difference(complete_union)
                current_coverage = {'status': 'measured', 'current_union_valid': complete_union.is_valid,
                    'proved_full_current_coverage': complete_union.is_valid and complete_union.covers(cg) and uncovered.is_empty,
                    'individually_covering_owner_ids': [r['id'] for r in neighbor_hits if r.get('covers_candidate')],
                    'uncovered_candidate': mapping(uncovered), 'uncovered_is_empty': uncovered.is_empty,
                    'uncovered_area': uncovered.area}
            predicates.update({
                'all_possible_consumed_source_features_valid': all(r['valid'] for r in source_hits),
                'unique_full_cover_consumed_source': [r['id'] for r in source_hits if r.get('covers_candidate')] == [target],
                'unique_positive_area_consumed_source': [r['id'] for r in source_hits if r.get('positive_area')] == [target],
                'all_possible_current_neighbors_valid': all(r['valid'] for r in neighbor_hits),
                'no_positive_area_any_current_neighbor': not any(r.get('positive_area') for r in neighbor_hits),
                'all_contacting_current_additions_valid': all(r['valid'] for r in addition_hits),
                'no_positive_area_current_addition': not any(r.get('positive_area') for r in addition_hits),
                'no_positive_area_other_cohort_candidate': not any(r['positive_area'] for r in cohort_hits)})
            diagnostics = {'dissolved_zero_loss': loss.is_empty,
                           'dissolved_full_gain': cg.symmetric_difference(gain).is_empty,
                           'dissolved_gain_positive_area': gain.area > 0}
        else:
            diagnostics = {}
        failures = [k for k, v in predicates.items() if v is not True]
        results.append({'component_id': cid, 'target_id': target,
                        'status': 'necessary-predicate-failed' if failures else 'necessary-predicates-supported-needs-independent-review',
                        'failed_predicates': failures, 'predicates': predicates,
                        'exact_binary64_status': exact_status, 'diagnostic_dissolve': diagnostics,
                        'complete_current_coverage': current_coverage,
                        'candidate_feature_sha256': sha(canon(cf)),
                        'current_target_feature_sha256': sha(canon(tf)),
                        'consumed_target_source_feature_sha256': sha(canon(sf)),
                        'retained_detector_area_m2': cf['properties']['measured_fragment_area_sum_m2'],
                        'source_hits': source_hits, 'current_neighbor_hits': neighbor_hits,
                        'current_addition_hits': addition_hits, 'cohort_hits': cohort_hits, 'residuals': residuals})
    result = {'baseline_commit': plan['current_baseline'], 'execution_head': head,
              'scope_ids': ids, 'results': results, 'input_plan_sha256': sha(controls['probe-inputs.json']),
              'producer_sha256': sha(controls['probe.py']), 'runtime_inventory_sha256': sha(runtime_raw),
              'prospective_logical_bytes': charge, 'consumed_inputs': plan['files'],
              'elapsed_seconds': time.monotonic() - started,
              'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
              'scientific_or_publication_approval': False,
              'limits': ['Original consumed AUS2022 simplified source-relative numerical screen only; complete physical/query custody remains separately required.',
                         'No current legal/physical truth or source observation-date approval.',
                         'Literal target-plus-full-candidate representation preserves coordinates; diagnostic dissolve is separately reported.',
                         'All 19 original Australian candidates remain accounted, including failed numerical outcomes. No physical acceptance is inferred.',
                         'Independent source review and subsequent engineering SOURCE/NATIVE/selected delivery remain required.']}
    if result['peak_rss_bytes'] > 512 * 1024 ** 2:
        raise ValueError('Scientific process reservation exceeded')
    dest.publish({'strict-predicates.json': result})
    print(json.dumps({'results': [{'component_id': r['component_id'], 'failed_predicates': r['failed_predicates'], 'diagnostic_dissolve': r['diagnostic_dissolve']} for r in results], 'prospective_logical_bytes': charge, 'peak_rss_bytes': result['peak_rss_bytes'], 'elapsed_seconds': result['elapsed_seconds']}))

if __name__ == '__main__':
    main()
