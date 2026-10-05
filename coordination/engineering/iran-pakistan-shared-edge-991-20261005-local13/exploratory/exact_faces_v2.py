"""Experimental exact planar faces, including disconnected nested boundaries.

Retains the original prototype. This is not an approved geography generator.
"""
from exact_arrangement import arrange as raw_arrange, signed_area, inside_ring
from exact_arrangement import point, crossings, boundaries as raw_boundaries


def face_interior(rings):
    ys = sorted({p[1] for ring in rings for p in ring})
    intervals = sorted(zip(ys, ys[1:]), key=lambda pair: pair[1] - pair[0], reverse=True)
    for lo, hi in intervals:
        y = (lo + hi) / 2
        xs = set()
        for ring in rings:
            for a, b in zip(ring, ring[1:] + ring[:1]):
                if a[1] <= y < b[1] or b[1] <= y < a[1]:
                    xs.add(a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]))
        xs = sorted(xs)
        for a, b in zip(xs, xs[1:]):
            p = ((a + b) / 2, y)
            if inside_ring(p, rings[0]) is True and all(inside_ring(p, h) is False for h in rings[1:]):
                return p
    raise ValueError('No exact interior outside all holes')


def arrange(segments):
    result = raw_arrange(segments)
    graph = {}
    for a, b in result['edges']:
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)
    components = {}
    component_count = 0
    for start in sorted(graph):
        if start in components:
            continue
        pending = [start]
        components[start] = component_count
        while pending:
            for neighbor in graph[pending.pop()]:
                if neighbor not in components:
                    components[neighbor] = component_count
                    pending.append(neighbor)
        component_count += 1
    if len(result['faces']) != len(result['edges']) - len(graph) + component_count:
        raise ValueError('Bounded face count violates planar Euler accounting')
    face_rings = [[face[0]] for face in result['faces']]
    attachments = []
    for index, (ring, area) in enumerate(result['negative']):
        # Distinct graph components cannot intersect. A vertex of this cycle
        # therefore lies strictly inside or outside each other component's face.
        candidates = []
        for n, (outer, outer_area, _) in enumerate(result['faces']):
            if components[outer[0]] == components[ring[0]]:
                continue
            state = inside_ring(ring[0], outer)
            if state is None:
                raise ValueError('Different graph components touch: incomplete noding')
            if state:
                candidates.append((outer_area, n))
        parent = min(candidates)[1] if candidates else None
        attachments.append({'negative_cycle': index, 'parent_face': parent})
        if parent is not None:
            face_rings[parent].append(ring)
    faces = []
    for rings in face_rings:
        area = sum(signed_area(r) for r in rings)
        if area <= 0:
            raise ValueError('Nested face has nonpositive exact area')
        faces.append((rings[0], area, face_interior(rings)))
    result.update(faces=faces, face_rings=face_rings, attachments=attachments,
                  vertices=len(graph), connected_components=component_count)
    return result


def boundaries(arrangement, labels, owner):
    expanded = []
    memberships = []
    for rings, membership in zip(arrangement['face_rings'], labels):
        for ring in rings:
            expanded.append((ring, signed_area(ring), None))
            memberships.append(membership)
    return raw_boundaries(expanded, memberships, owner)


def validate_noding(segments, arrangement, bbox_reference=False):
    """Independent all-pairs controls; intentionally bounded quadratic work."""
    original = [(point(a), point(b)) for a, b in segments if point(a) != point(b)]
    expected = [{a, b} for a, b in original]
    boxes = [(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
             for a, b in original]
    compared = 0
    for i, (a, b) in enumerate(original):
        for j in range(i + 1, len(original)):
            if bbox_reference:
                x, y = boxes[i], boxes[j]
                if x[2] < y[0] or y[2] < x[0] or x[3] < y[1] or y[3] < x[1]:
                    continue
            compared += 1
            values = crossings(a, b, *original[j])
            expected[i].update(values)
            expected[j].update(values)
    edges = set()
    for (a, b), values in zip(original, expected):
        axis = 0 if a[0] != b[0] else 1
        ordered = sorted(values, key=lambda p: p[axis])
        edges.update(tuple(sorted([u, v])) for u, v in zip(ordered, ordered[1:]))
    if edges != arrangement['edges']:
        raise ValueError('Indexed noding differs from exact all-pairs reference')
    return {'all_pairs': len(original) * (len(original) - 1) // 2,
            'compared_pairs': compared, 'exact_bbox_reference': bbox_reference,
            'exact_edges_equal': True}
