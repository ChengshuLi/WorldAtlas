"""Remove exact straight-through graph nodes before float conversion.

No coordinate move, epsilon, area cutoff or omitted exact face is permitted.
Original graph and every removed rational coordinate remain diagnostic records.
"""
from exact_arrangement import on, signed_area, export_rings


def split_exact_walk(ring):
    """Represent point-touching holes as distinct cycles, preserving every edge."""
    stack = []
    positions = {}
    cycles = []
    for p in ring + ring[:1]:
        if p in positions:
            n = positions[p]
            cycle = stack[n:]
            if len(cycle) < 3 or signed_area(cycle) == 0:
                raise ValueError('Degenerate exact closed walk remains unresolved')
            cycles.append(cycle)
            for deleted in stack[n + 1:]:
                del positions[deleted]
            stack = stack[:n + 1]
        else:
            positions[p] = len(stack)
            stack.append(p)
    if len(stack) != 1 or sum(signed_area(c) for c in cycles) != signed_area(ring):
        raise ValueError('Exact cycle decomposition changed the boundary')
    original_edges = sorted(zip(ring, ring[1:] + ring[:1]))
    cycle_edges = sorted(e for c in cycles for e in zip(c, c[1:] + c[:1]))
    if original_edges != cycle_edges:
        raise ValueError('Exact cycle decomposition did not preserve every edge')
    return cycles


def reduce_ring(original):
    ring = list(original)
    removed = []
    while True:
        changed = False
        for n, p in enumerate(ring):
            a, b = ring[n - 1], ring[(n + 1) % len(ring)]
            if len(ring) > 3 and a != b and on(a, b, p):
                removed.append({'point': [str(v) for v in p],
                                'previous': [str(v) for v in a], 'next': [str(v) for v in b]})
                del ring[n]
                changed = True
                break
        if not changed:
            break
    if signed_area(ring) != signed_area(original):
        raise ValueError('Exact straight-through reduction changed signed area')
    return ring, removed


if __name__ == '__main__':
    exec(open('.cache/shared-edge-991/exact_world_v2.py').read().split('export = {}')[0])
    from shapely.validation import explain_validity
    from exact_faces_v2 import boundaries
    candidates = {}
    summaries = {}
    certificates = {}
    for owner in d['subject_ids']:
        originals = boundaries(arrangement, labels, owner)
        rings = []
        certificates[owner] = []
        for original in originals:
            ring, removed = reduce_ring(original)
            rings.append(ring)
            certificates[owner].append(removed)
        candidate = export_rings(rings)
        polygon = shape(candidate)
        candidates[owner] = candidate
        summaries[owner] = {'removed_exact_collinear_points': sum(len(r) for r in certificates[owner]),
                            'valid_rounded': polygon.is_valid, 'validity_reason': explain_validity(polygon)}
    result = {'experimental': True, 'summaries': summaries, 'candidates': candidates,
              'certificates': certificates,
              'limits': ['Exact collinear reduction only; all invalid rounded geometry remains rejected.',
                         'Not source/geographic approval, not a worldwide audit or installed repair.']}
    payload = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
    pathlib.Path('.cache/shared-edge-991/exact-collinear-v2.json').write_bytes(payload)
    print(json.dumps({'sha256': hashlib.sha256(payload).hexdigest(), 'summaries': summaries}))
