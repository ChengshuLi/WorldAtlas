import hashlib
import json
from fractions import Fraction as F
from pathlib import Path
from exact_arrangement import point, inside_ring, signed_area, export_rings
from exact_faces_v2 import arrange, boundaries, validate_noding
from shapely.geometry import shape


def square(x, y, size):
    return [point(p) for p in [(x, y), (x + size, y), (x + size, y + size), (x, y + size)]]


def segments(rings):
    return [edge for ring in rings for edge in zip(ring, ring[1:] + ring[:1])]


def run(name, rings, expected_faces, expected_area, expected_holes):
    raw = segments(rings)
    result = arrange(raw)
    noding = validate_noding(raw, result)
    assert len(result['faces']) == expected_faces
    assert sum(face[1] for face in result['faces']) == expected_area
    assert sum(len(r) - 1 for r in result['face_rings']) == expected_holes
    for (_, _, p), face_rings in zip(result['faces'], result['face_rings']):
        assert inside_ring(p, face_rings[0]) is True
        assert all(inside_ring(p, r) is False for r in face_rings[1:])
    # Every face's exact reconstructed boundary has identical signed area.
    for index, (_, area, _) in enumerate(result['faces']):
        labels = [['selected'] if n == index else [] for n in range(expected_faces)]
        reconstructed = boundaries(result, labels, 'selected')
        assert sum(signed_area(r) for r in reconstructed) == area
        assert shape(export_rings(reconstructed)).is_valid
    return {'case': name, 'faces': expected_faces, 'holes': expected_holes,
            'area': str(expected_area), 'noding': noding, 'passed': True}


records = [
    run('nested hole', [square(0, 0, 10), square(2, 2, 6)], 2, F(100), 1),
    run('island within hole', [square(0, 0, 10), square(2, 2, 6), square(3, 3, 2)], 3, F(100), 2),
    run('separate islands', [square(0, 0, 2), square(5, 5, 3)], 2, F(13), 0),
    run('overlapping neighbors', [square(0, 0, 2), square(1, 1, 2)], 3, F(7), 0),
    run('shared edge', [square(0, 0, 2), square(2, 0, 2)], 2, F(8), 0),
    run('coincident opposite rings', [square(0, 0, 2), list(reversed(square(0, 0, 2)))], 1, F(4), 0),
]
raw = segments([square(0, 0, 10), square(2, 2, 6)])
raw.extend([(point((0, 0)), point((2, 2))), (point((10, 10)), point((11, 11)))])
connected = arrange(raw)
validate_noding(raw, connected)
assert len(connected['faces']) == 2
assert sum(face[1] for face in connected['faces']) == 100
assert connected['connected_components'] == 1
records.append({'case': 'bridge and dangling segment', 'passed': True})

from exact_collinear_v3 import split_exact_walk, reduce_ring
triangle = [point(p) for p in [(0, 0), (2, 1), (1, 2)]]
touching = arrange(segments([square(0, 0, 10), triangle]))
validate_noding(segments([square(0, 0, 10), triangle]), touching)
assert len(touching['faces']) == 2
labels = [['annulus'] if area > 50 else [] for ring, area, p in touching['faces']]
walks = boundaries(touching, labels, 'annulus')
assert not shape(export_rings(walks)).is_valid
split = [reduce_ring(c)[0] for walk in walks for c in split_exact_walk(walk)]
assert shape(export_rings(split)).is_valid
assert sum(signed_area(r) for r in split) == F(197, 2)
records.append({'case': 'point-touching hole preserves every edge and valid output', 'passed': True})

near_straight = [point(p) for p in [(0, 0), (1, F(1, 10**50)), (2, 0), (2, 2), (0, 2)]]
reduced, removed = reduce_ring(near_straight)
assert reduced == near_straight and removed == []
records.append({'case': 'nonzero exact bend never removed by magnitude', 'passed': True})
records.append(run('nonzero tiny face retained', [square(0, 0, F(1, 10**20))], 1, F(1, 10**40), 0))

# Negative control: the old independent-cycle implementation picks a point
# inside a nested island for the containing annulus, proving the fixture
# catches the actual known classification failure.
from exact_arrangement import arrange as old_arrange
old = old_arrange(segments([square(0, 0, 10), square(2, 2, 6)]))
assert any(inside_ring(p, square(2, 2, 6)) is True for ring, area, p in old['faces'] if area == 100)
records.append({'case': 'old nested-face classifier rejected', 'passed': True})

# Negative control: removing a noded edge fails the independent all-pairs check.
broken = arrange(segments([square(0, 0, 2), square(1, 1, 2)]))
broken['edges'].pop()
try:
    validate_noding(segments([square(0, 0, 2), square(1, 1, 2)]), broken)
except ValueError:
    records.append({'case': 'missing edge rejected', 'passed': True})
else:
    raise AssertionError('Missing-edge negative control passed incorrectly')

result = {'experimental': True, 'controls': records,
          'limits': ['Synthetic exact planar controls only; not global audit, source authority, spherical/dateline correctness or valid rounded repair.']}
payload = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
Path('.cache/shared-edge-991/exact-faces-controls-v2.json').write_bytes(payload)
print(json.dumps({'controls_passed': len(records), 'sha256': hashlib.sha256(payload).hexdigest()}))
