"""Independent majority oracle for reused per-location geometry caches."""
import itertools
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from majority import area, canonical, decide
from shapely import union_all
from shapely.geometry import Polygon, box


def oracle(location, claims, preclipped=False):
    """No geometry identity caches, including within a single dated decision."""
    total = area(location)
    groups = {}
    for owner, geometries in claims.items():
        local = geometries if preclipped else [location if g.covers(location) else g.intersection(location) for g in geometries]
        unique = list({id(g): g for g in local}.values())
        groups[owner] = location if any(g is location or g.equals(location) for g in unique) else unique[0] if len(unique) == 1 else union_all(unique)
    measured = {owner: total if g is location else area(g) for owner, g in groups.items()}
    shares = {owner: min(1, size / total) for owner, size in measured.items() if size > total * 1e-8}
    ordered = sorted(shares, key=lambda owner: (-shares[owner], owner))
    unique_groups = list({id(g): g for g in groups.values()}.values())
    coverage = 1 if any(g is location for g in unique_groups) else min(1, area(union_all(unique_groups)) / total) if unique_groups else 0
    conflict = any((measured[b] if groups[a] is location else measured[a] if groups[b] is location else area(groups[a].intersection(groups[b]))) > total * 1e-6 for a, b in itertools.combinations(ordered, 2))
    status = 'disputed' if conflict else 'derived' if ordered and shares[ordered[0]] > .50000001 else 'no-majority' if ordered else 'unknown'
    return {'owner': ordered[0] if status == 'derived' else None, 'status': status, 'share': round(shares[ordered[0]], 12) if ordered else 0, 'coverage': round(coverage, 12), 'candidates': [[owner, round(shares[owner], 12)] for owner in ordered]}


def check(location, claims, cache=None, preclipped=False):
    expected = oracle(location, claims, preclipped)
    actual = decide(location, claims, preclipped=preclipped, cache=cache)
    assert actual == expected, (actual, expected)


rng = random.Random(57)
decisions = 0
for latitude in (0, 60, 85):
    for case in range(100):
        location = box(0, latitude, 1, latitude + 1)
        sources = [box(rng.uniform(-1, .8), latitude + rng.uniform(-1, .8), rng.uniform(.81, 2), latitude + rng.uniform(.81, 2)) for _ in range(8)]
        clips = [location if g.covers(location) else g.intersection(location) for g in sources]
        # Keep the full clip pool alive, just as the production per-location intern table does.
        cache = {'areas': {id(g): area(g) for g in clips}}
        for interval in range(8):
            indices = rng.sample(range(len(clips)), rng.randrange(1, len(clips) + 1))
            claims = {}
            for i in indices:
                claims.setdefault('owner:' + str((i + interval) % 3), []).append(clips[i])
            check(location, claims, cache=cache, preclipped=True)
            # Repeated/reordered date visits must not change a cached decision.
            check(location, {owner: list(reversed(gs)) for owner, gs in reversed(list(claims.items()))}, cache=cache, preclipped=True)
            decisions += 2
        original = {'owner:' + str(i): sources[2*i:2*i+2] for i in range(3)}
        check(location, original)
        decisions += 1

# Freshly clipped objects must stay alive for any id used in a cache key; otherwise
# Python may reuse a freed id for a different owner's union within the same call.
for case in range(100):
    location = box(0, 0, 1, 1)
    claims = {str(i): [box(rng.uniform(-1, .8), rng.uniform(-1, .8), rng.uniform(.81, 2), rng.uniform(.81, 2)) for _ in range(2)] for i in range(3)}
    check(location, claims)
    decisions += 1

for location in [box(0, 0, .000001, .000001), canonical(Polygon([(179, 0), (-179, 0), (-179, 2), (179, 2), (179, 0)], [[(179.5, .5), (-179.5, .5), (-179.5, 1.5), (179.5, 1.5), (179.5, .5)]]))]:
    cache = {}
    for claims in [{'a': [location, location]}, {'a': [location], 'b': [location]}, {}]:
        check(location, claims, cache=cache, preclipped=True)
        check(location, claims)
        decisions += 2

near_majority = box(0, 0, 1, 1)
result = decide(near_majority, {'a': [box(0, 0, .50000005, 1)]})
assert result['owner'] == 'a' and result['share'] > .5
for latitude in (0, 60, 85):
    location = box(0, latitude, 1.01, latitude + 1)
    left, right = box(0, latitude, .505, latitude + 1), box(.505, latitude, 1.01, latitude + 1)
    # Longitude symmetry gives exactly half the ellipsoidal land area. Unequal
    # perimeter subdivision during area approximation must not invent a winner.
    for claims in [{'a': [left]}, {'a': [left], 'b': [right]}]:
        result = decide(location, claims)
        assert result['owner'] is None and result['status'] == 'no-majority', ('geometric half must remain unresolved', latitude, result)
        decisions += 1
print(f'PASS: {decisions} independent cached/uncached decisions over 300 locations, dated claim sets, tiny footprints and antimeridian holes')
