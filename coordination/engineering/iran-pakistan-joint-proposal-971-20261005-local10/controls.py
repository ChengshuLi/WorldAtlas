import copy
import json
from shapely.geometry import Polygon, box, shape
from propose import build_candidate, source_agreement


def rejects(callback):
    try:
        callback()
    except (ValueError, KeyError):
        return
    raise AssertionError('Unsupported candidate accepted')


def main():
    checks = []
    component = box(1, 0, 2, 1)
    current = {'IRN': box(0, 0, 1, 1), 'PAK': box(2, 0, 3, 1)}
    sources = {'IRN': box(0, 0, 1.5, 1), 'PAK': box(1.5, 0, 3, 1)}
    candidate, proof = build_candidate(component, current, sources)
    assert candidate['IRN'].equals(box(0, 0, 1.5, 1))
    assert candidate['PAK'].equals(box(1.5, 0, 3, 1))
    assert proof['candidate_covers_entire_component'] and proof['new_neighbor_overlap']['empty']
    checks.append('bilateral source intersections close known full component')
    for country in current:
        assert proof['neighbors'][country]['lost_existing_coverage']['empty']
        assert proof['neighbors'][country]['added_outside_component']['empty']
        assert proof['neighbors'][country]['added_outside_named_source']['empty']
    checks.append('existing geometry preserved and new coverage constrained to source and component')
    broken = dict(sources); broken['PAK'] = box(1.6, 0, 3, 1)
    rejects(lambda: build_candidate(component, current, broken))
    checks.append('uncovered source stripe rejected rather than nearest-filled')
    broken = dict(sources); broken['PAK'] = box(1.4, 0, 3, 1)
    rejects(lambda: build_candidate(component, current, broken))
    checks.append('contradictory positive-area sources rejected')
    rejects(lambda: build_candidate(component, {'IRN': current['IRN']}, sources))
    checks.append('missing affected neighbor rejected')
    broken = dict(sources)
    broken['IRN'] = Polygon([(0, 0), (2, 1), (0, 1), (2, 0), (0, 0)])
    rejects(lambda: build_candidate(component, current, broken))
    checks.append('invalid source rejected without geometry repair')
    tiny = box(1, 0, 1 + 1e-8, 1)
    candidate, proof = build_candidate(tiny, current, sources)
    assert proof['neighbors']['IRN']['actual_added_coverage']['area_m2'] > 0
    assert not proof['neighbors']['IRN']['actual_added_coverage']['empty']
    checks.append('tiny positive source additions preserved')
    # A source hole cannot be silently treated as supported new coverage.
    hole = Polygon([(0, -1), (3, -1), (3, 2), (0, 2), (0, -1)],
                   [[(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)]])
    rejects(lambda: build_candidate(component, current, {'IRN': hole, 'PAK': box(4, 0, 5, 1)}))
    checks.append('source hole remains unsupported and rejected')
    original = {'elements': [{'type': 'node', 'id': 1, 'lon': 1, 'lat': 0, 'version': 1},
                             {'type': 'node', 'id': 2, 'lon': 1, 'lat': 1, 'version': 1},
                             {'type': 'way', 'id': 10, 'nodes': [1, 2], 'version': 3}]}
    agreement = source_agreement(original, copy.deepcopy(original))
    assert agreement['shared_way_ids'] == [10] and agreement['shared_node_count'] == 2
    checks.append('exact shared original source members accepted')
    changed = copy.deepcopy(original); changed['elements'][0]['lon'] = 1.000001
    rejects(lambda: source_agreement(original, changed))
    checks.append('changed shared coordinate rejected without snapping')
    changed = copy.deepcopy(original); changed['elements'][2]['version'] = 4
    rejects(lambda: source_agreement(original, changed))
    checks.append('different shared source version rejected')
    rejects(lambda: source_agreement(original, {'elements': []}))
    checks.append('absent shared source evidence rejected')
    print(json.dumps({'method_id': 'joint-source-candidate', 'kind': 'positive-control',
                      'outcome': 'passed', 'check_count': len(checks), 'checks': checks}, sort_keys=True))


if __name__ == '__main__':
    main()
