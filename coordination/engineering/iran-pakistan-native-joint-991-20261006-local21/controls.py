"""Analytic controls exercise the actual exact partition/rounding/check paths."""
from fractions import Fraction as F
import importlib.util
import json
from pathlib import Path
import sys

from exact_arrangement import point, signed_area
from exact_faces_v2 import arrange, validate_noding
from reproduce import classify, rings, split_rounded

spec = importlib.util.spec_from_file_location('exact_native', Path(__file__).with_name('exact-native-check.py'))
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def expect_rejected(function, message):
    try:
        function()
    except ValueError:
        return
    raise AssertionError(message)


def run():
    square = [point(p) for p in [(0, 0), (4, 0), (4, 4), (0, 4)]]
    hole = [point(p) for p in [(1, 1), (2, 1), (2, 2), (1, 2)]]
    segments = [edge for ring in [square, hole] for edge in zip(ring, ring[1:] + ring[:1])]
    arrangement = arrange(segments)
    assert sorted(area for _, area, _ in arrangement['faces']) == [1, 15]
    assert classify(point((F(3, 2), F(3, 2))), [square, hole]) is False
    assert classify(point((3, 3)), [square, hole]) is True
    assert validate_noding(segments, arrangement)['exact_edges_equal']
    expect_rejected(lambda: classify(point((0, 0)), [square]), 'Boundary witness accepted')
    mutant = dict(arrangement, edges=set(arrangement['edges']))
    mutant['edges'].pop()
    expect_rejected(lambda: validate_noding(segments, mutant), 'Missing noded edge accepted')
    expect_rejected(lambda: rings({'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 1]]]}),
                    'Unclosed original ring accepted')
    assert native.ceiling(F(-1, 2)) == 0 and native.ceiling(F(1, 2)) == 1
    shared = [point(p) for p in [(-175, 0), (-5, 0), (-5, 10), (-175, 10)]]
    assert native.spans([shared], F(9), 36)[0] == [[0, 17]]
    assert native.spans([shared], F(0), 36)[0] == []
    assert native.spans([shared], F(10), 36)[0] == [[0, 17]]
    tiny = [point(p) for p in [(-5-F(1, 2**40), 9-F(1, 2**40)),
                              (-5+F(1, 2**40), 9-F(1, 2**40)),
                              (-5+F(1, 2**40), 9+F(1, 2**40)),
                              (-5-F(1, 2**40), 9+F(1, 2**40))]]
    assert native.spans([tiny], F(9), 36)[0] == [[17, 18]]
    loops = split_rounded(square)
    assert len(loops) == 1 and signed_area(loops[0]) == 16
    # Exact distinct vertices can collide in Float64: every resulting self-edge
    # remains present in the explicit zero-area rounded cycle, not silently lost.
    collision = [(F(1), F(0)), (F(1) + F(1, 2**60), F(0)), (F(2), F(1)), (F(1), F(1))]
    loops = split_rounded(collision)
    assert any(signed_area(c) == 0 for c in loops)
    assert sum(signed_area(c) for c in loops) == F(1, 2)
    return {'analytic_nested_faces': True, 'exact_noding_positive': True,
            'missing_noded_edge_rejected': True, 'boundary_witness_rejected': True,
            'unclosed_original_rejected': True, 'signed_column_ceil': True,
            'native_half_open_shared_edge': True, 'tiny_positive_native_feature': True,
            'rounded_edges_and_zero_area_remnants_preserved': True}


if __name__ == '__main__':
    checks = run()
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=False)
    for kind in ['positive-control', 'negative-control']:
        with (out / (kind + '.json')).open('x') as stream:
            json.dump({'method_id': 'joint-exact-native-partition', 'kind': kind,
                       'outcome': 'passed', 'checks': checks}, stream, sort_keys=True)
            stream.write('\n')
    print(json.dumps(checks))
