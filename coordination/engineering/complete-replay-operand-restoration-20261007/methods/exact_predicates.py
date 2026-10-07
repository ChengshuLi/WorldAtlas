"""Bounded exact predicates on unchanged, explicitly declared binary64 source values.

No projection, overlays, repairs, affiliation or geometry acceptance is performed.
"""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

VERSION = 'worldatlas-exact-source-predicates-v1'
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_DESCRIPTORS = 512
MAX_SEGMENTS = 1024
MAX_POINTS = 4096
MAX_MEMBERS = 512
MAX_POINT_SEGMENT_CHECKS = 1000000
MAX_PAIR_CHECKS = 250000
CONTEXT_KEYS = ('crs', 'axis_order', 'numeric_vintage', 'coordinate_encoding')
LIMITS = [
    'Exact arithmetic describes supplied binary64 values, not source accuracy, exact projection or ground truth.',
    'Point membership is not whole-cell/component coverage, affiliation, water or legal/historical authority.',
    'Symbolic point diagnostics never approve materialized faces or replace repair acceptance.',
    'Intersecting/touching polygon rings or multipart boundaries are conservatively unsupported where stated.',
]


class DiagnosticError(ValueError):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status, self.reason = status, reason


def reject(reason, status='invalid'):
    raise DiagnosticError(status, reason)


def context(value):
    if not isinstance(value, dict) or any(key not in value for key in CONTEXT_KEYS):
        reject('missing-coordinate-context', 'unknown')
    if any(not isinstance(value[key], str) or not value[key] for key in ('crs', 'numeric_vintage')):
        reject('missing-coordinate-context', 'unknown')
    if value['axis_order'] != ['x', 'y'] or value['coordinate_encoding'] != 'IEEE754-binary64':
        reject('unsupported-axis-or-coordinate-encoding', 'unsupported')
    return {key: value[key] for key in CONTEXT_KEYS}


def point(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        reject('expected-two-coordinate-values', 'unsupported')
    result = []
    for coordinate in value:
        if isinstance(coordinate, bool) or not isinstance(coordinate, (int, float)):
            reject('coordinate-is-not-a-json-number')
        try:
            number = float(coordinate)
        except (OverflowError, ValueError):
            reject('nonfinite-coordinate')
        if not math.isfinite(number):
            reject('nonfinite-coordinate')
        if isinstance(coordinate, int) and number != coordinate:
            reject('integer-not-exactly-encoded-as-binary64', 'unsupported')
        result.append(Fraction(number))
    return tuple(result)


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def subtract(a, b):
    return a[0] - b[0], a[1] - b[1]


def orientation(a, b, p):
    return cross(subtract(b, a), subtract(p, a))


def on_segment(p, a, b):
    return orientation(a, b, p) == 0 and all(min(a[i], b[i]) <= p[i] <= max(a[i], b[i]) for i in (0, 1))


def segment_contacts(a, b, c, d):
    """Exact closed segment contact, including endpoints and collinear overlap."""
    if any(max(a[i], b[i]) < min(c[i], d[i]) or max(c[i], d[i]) < min(a[i], b[i]) for i in (0, 1)):
        return False
    o1, o2, o3, o4 = orientation(a, b, c), orientation(a, b, d), orientation(c, d, a), orientation(c, d, b)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    return any(on_segment(p, x, y) for p, x, y in ((c, a, b), (d, a, b), (a, c, d), (b, c, d)))


def ring_state(p, ring):
    """Half-open ray test with boundary checked first; winding order independent."""
    inside = False
    for a, b in zip(ring, ring[1:]):
        if on_segment(p, a, b):
            return 'boundary'
        if (a[1] > p[1]) != (b[1] > p[1]):
            intersection_x = a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if p[0] < intersection_x:
                inside = not inside
    return 'inside' if inside else 'outside'


def polygon_state(p, rings):
    states = [ring_state(p, ring) for ring in rings]
    if 'boundary' in states:
        return 'boundary'
    return 'inside' if states[0] == 'inside' and all(s == 'outside' for s in states[1:]) else 'outside'


def prepare_geometry(geometry):
    """Validate original ring topology exactly within explicit work bounds."""
    if not isinstance(geometry, dict) or geometry.get('type') not in ('Polygon', 'MultiPolygon'):
        reject('nonpolygon-or-missing-geometry', 'unsupported' if geometry is not None else 'unknown')
    coordinates = geometry.get('coordinates')
    if not isinstance(coordinates, list) or not coordinates:
        reject('empty-polygon')
    polygons = [coordinates] if geometry['type'] == 'Polygon' else coordinates
    prepared, segments = [], []
    for pi, polygon in enumerate(polygons):
        if not isinstance(polygon, list) or not polygon:
            reject('empty-polygon-member')
        rings = []
        for ri, original in enumerate(polygon):
            if not isinstance(original, list) or len(original) < 4:
                reject('ring-has-too-few-vertices')
            if len(segments) + len(original) - 1 > MAX_SEGMENTS:
                reject('segment-budget-exceeded', 'unsupported')
            ring = [point(p) for p in original]
            if ring[0] != ring[-1]:
                reject('ring-not-closed')
            if any(a == b for a, b in zip(ring, ring[1:])):
                reject('zero-length-original-segment')
            if sum(cross(a, b) for a, b in zip(ring, ring[1:])) == 0:
                reject('zero-exact-ring-area')
            rings.append(ring)
            segments.extend((pi, ri, si, a, b, len(ring) - 1) for si, (a, b) in enumerate(zip(ring, ring[1:])))
        prepared.append(rings)
    if len(segments) * (len(segments) - 1) // 2 > MAX_PAIR_CHECKS:
        reject('topology-pair-budget-exceeded', 'unsupported')
    for i, (pi, ri, si, a, b, size) in enumerate(segments):
        for pj, rj, sj, c, d, _ in segments[i + 1:]:
            if pi == pj and ri == rj and (abs(si - sj) == 1 or {si, sj} == {0, size - 1}):
                # Adjacent edges may share one endpoint, but cannot backtrack/overlap.
                common = set((a, b)) & set((c, d))
                remaining = [x for x in (a, b, c, d) if x not in common]
                if len(common) != 1 or any(on_segment(x, a, b) and on_segment(x, c, d) for x in remaining):
                    reject('adjacent-segments-overlap')
                continue
            if segment_contacts(a, b, c, d):
                reject('self-intersecting-ring' if pi == pj and ri == rj else 'touching-or-crossing-rings',
                       'invalid' if pi == pj else 'unsupported')
    for rings in prepared:
        for i, hole in enumerate(rings[1:]):
            if ring_state(hole[0], rings[0]) != 'inside':
                reject('hole-outside-shell')
            if any(ring_state(hole[0], other) == 'inside' or ring_state(other[0], hole) == 'inside'
                   for other in rings[1:i + 1]):
                reject('nested-or-overlapping-holes')
    for i, rings in enumerate(prepared):
        for other in prepared[i + 1:]:
            if polygon_state(rings[0][0], other) == 'inside' or polygon_state(other[0][0], rings) == 'inside':
                reject('overlapping-multipart-interiors')
    return prepared


def geometry_state(p, prepared):
    states = [polygon_state(p, polygon) for polygon in prepared]
    return 'inside' if 'inside' in states else 'boundary' if 'boundary' in states else 'outside'


def rational(value):
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def segment_certificate(first, second, exported=None):
    """Exact original-segment crossing and typed Float64 export incidence check."""
    result = {'helper_version': VERSION, 'geometry_acceptance': 'not-assessed'}
    try:
        if not isinstance(first, dict) or not isinstance(second, dict):
            reject('malformed-original-segments')
        if context(first.get('context')) != context(second.get('context')):
            reject('segment-coordinate-context-mismatch', 'unknown')
        for segment in (first, second):
            if not isinstance(segment.get('id'), str) or not segment['id']:
                reject('missing-original-segment-id')
            if not isinstance(segment.get('endpoints'), list) or len(segment['endpoints']) != 2:
                reject('expected-two-original-endpoints')
        a, b = map(point, first['endpoints']); c, d = map(point, second['endpoints'])
        if a == b or c == d:
            reject('degenerate-original-segment')
        u, v, w = subtract(b, a), subtract(d, c), subtract(c, a)
        denominator = cross(u, v)
        result['original_segment_ids'] = [first['id'], second['id']]
        if denominator == 0:
            result.update(status='unsupported' if segment_contacts(a, b, c, d) else 'disjoint',
                          reason='collinear-contact-needs-separate-ledger' if segment_contacts(a, b, c, d) else 'parallel-disjoint')
            return result
        t, q = cross(w, v) / denominator, cross(w, u) / denominator
        if not (0 <= t <= 1 and 0 <= q <= 1):
            result.update(status='disjoint', reason='intersection-outside-segment-ranges')
            return result
        node = tuple(a[i] + t * u[i] for i in (0, 1))
        nearest = tuple(float(x) for x in node)
        representable = all(Fraction(x) == y for x, y in zip(nearest, node))
        result.update(exact_node=[rational(x) for x in node], exact_parameters=[rational(t), rational(q)],
                      exactly_representable_binary64=representable, nearest_binary64=list(nearest))
        tested = point(list(nearest) if exported is None else exported)
        incidence = [on_segment(tested, a, b), on_segment(tested, c, d)]
        result.update(tested_export=list(nearest) if exported is None else exported, exact_segment_incidence=incidence,
                      status='exact-incidence' if all(incidence) else 'export-incidence-failure',
                      reason='exact-original-crossing' if all(incidence) else
                      'nonrepresentable-crossing' if not representable else 'altered-export-coordinate')
    except DiagnosticError as error:
        result.update(status=error.status, reason=error.reason)
    return result


def unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            reject('duplicate-json-object-key')
        result[key] = value
    return result


def read_inputs(root, request):
    """Whole-byte custody plus complete original FeatureCollection member closure."""
    declared_context = context(request.get('context'))
    files, collections, total = request.get('files'), request.get('collections'), 0
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_DESCRIPTORS:
        reject('descriptor-budget-or-missing-files')
    if not isinstance(collections, dict) or set(collections) != {'gap', 'first', 'second'}:
        reject('missing-three-collection-closure', 'unknown')
    if any(not isinstance(value, dict) or not isinstance(value.get('provider_id'), str) or not value['provider_id'] for value in collections.values()):
        reject('missing-provider-closure', 'unknown')
    prepared = {role: [] for role in collections}; seen_paths = set(); custody = []
    for descriptor in files:
        if not isinstance(descriptor, dict):
            reject('malformed-source-descriptor')
        role = descriptor.get('role'); path = descriptor.get('path')
        if role not in prepared or not isinstance(path, str) or path in seen_paths:
            reject('duplicate-file-or-invalid-role')
        seen_paths.add(path)
        candidate = Path(path)
        if candidate.is_absolute() or any(part in ('', '.', '..') for part in path.split('/')) or '\\' in path or '\0' in path:
            reject('unsafe-original-file-path')
        source = root / candidate
        if any((root / Path(*candidate.parts[:i])).is_symlink() for i in range(1, len(candidate.parts) + 1)):
            reject('symlink-original-file')
        if not source.is_file() or source.stat().st_size > MAX_FILE_BYTES:
            reject('missing-or-oversized-original-file')
        raw = source.read_bytes(); total += len(raw)
        if total > MAX_TOTAL_BYTES:
            reject('total-reader-budget-exceeded')
        if descriptor.get('bytes') != len(raw) or descriptor.get('sha256') != hashlib.sha256(raw).hexdigest():
            reject('original-byte-pin-mismatch')
        if context(descriptor.get('context')) != declared_context:
            reject('source-coordinate-context-mismatch', 'unknown')
        if descriptor.get('provider_id') != collections[role].get('provider_id'):
            reject('provider-closure-mismatch', 'unknown')
        try:
            doc = json.loads(raw, object_pairs_hook=unique_json_object)
        except (ValueError, UnicodeError):
            reject('invalid-source-json')
        if not isinstance(doc, dict):
            reject('unsupported-source-document', 'unsupported')
        features = doc.get('features') if doc.get('type') == 'FeatureCollection' else [doc]
        if not isinstance(features, list) or not features:
            reject('empty-source-member-collection', 'unknown')
        if sum(len(members) for members in prepared.values()) + len(features) > MAX_MEMBERS:
            reject('member-budget-exceeded', 'unsupported')
        for feature in features:
            if not isinstance(feature, dict) or feature.get('type') != 'Feature' or not isinstance(feature.get('id'), str):
                reject('missing-original-member-id')
            member = {'member_id': feature['id'], 'provider_id': descriptor['provider_id'], 'source_path': path,
                      'source_sha256': descriptor['sha256'], 'status': 'valid'}
            try:
                member['prepared'] = prepare_geometry(feature.get('geometry'))
            except DiagnosticError as error:
                member.update(status=error.status, reason=error.reason)
            prepared[role].append(member)
        custody.append(dict(descriptor))
    for role, members in prepared.items():
        expected = collections[role].get('member_ids'); actual = [m['member_id'] for m in members]
        if not isinstance(expected, list) or not expected or not all(isinstance(x, str) and x for x in expected):
            reject('missing-original-member-roster', 'unknown')
        if len(expected) != len(set(expected)) or len(actual) != len(set(actual)) or sorted(expected) != sorted(actual):
            reject('omitted-duplicate-or-altered-member-closure', 'unknown')
    return prepared, custody



def original_segment(prepared, reference, declared_context):
    """Resolve a certificate operand from byte-verified, complete source members."""
    if not isinstance(reference, dict) or reference.get('role') not in prepared:
        reject('missing-source-segment-reference')
    matches = [m for m in prepared[reference['role']] if m['member_id'] == reference.get('member_id')]
    if len(matches) != 1:
        reject('original-segment-member-not-in-closure', 'unknown')
    member = matches[0]
    if member['status'] != 'valid':
        reject('original-segment-geometry-not-valid', 'unknown')
    if reference.get('source_sha256') != member['source_sha256']:
        reject('original-segment-byte-pin-mismatch')
    indices = [reference.get(key) for key in ('polygon_index', 'ring_index', 'segment_index')]
    if any(isinstance(i, bool) or not isinstance(i, int) or i < 0 for i in indices):
        reject('invalid-original-segment-index')
    try:
        pi, ri, si = indices
        ring = member['prepared'][pi][ri]
        a, b = ring[si], ring[si + 1]
    except IndexError:
        reject('original-segment-index-out-of-range')
    return {'id': ':'.join([member['provider_id'], member['member_id'], member['source_sha256'], *map(str, indices)]),
            'context': declared_context, 'endpoints': [[float(x) for x in a], [float(x) for x in b]],
            'source_reference': dict(reference), 'source_path': member['source_path']}


def collection_state(p, members):
    rows = []
    for member in members:
        row = {key: value for key, value in member.items() if key != 'prepared'}
        row['point_state'] = geometry_state(p, member['prepared']) if member['status'] == 'valid' else 'unknown'
        rows.append(row)
    if any(row['point_state'] == 'inside' for row in rows):
        state = 'inside'
    elif any(row['point_state'] == 'boundary' for row in rows):
        state = 'boundary'
    else:
        state = 'unknown' if any(row['point_state'] == 'unknown' for row in rows) else 'outside'
    # Known inside evidence is retained, but unknown members prohibit a definitive four-class result.
    return {'state': state, 'members': rows, 'inside_member_ids': [r['member_id'] for r in rows if r['point_state'] == 'inside'],
            'boundary_member_ids': [r['member_id'] for r in rows if r['point_state'] == 'boundary'],
            'unknown_member_ids': [r['member_id'] for r in rows if r['point_state'] == 'unknown']}


def diagnose(root, request):
    result = {'helper_version': VERSION, 'kind': 'symbolic-original-source-point-diagnostic',
              'geometry_acceptance': 'not-assessed', 'limits': LIMITS, 'points': []}
    if not isinstance(request, dict):
        return dict(result, status='invalid', reason='malformed-request')
    result['declared_collections'] = request.get('collections')
    try:
        prepared, custody = read_inputs(Path(root), request)
        queries = request.get('points')
        if not isinstance(queries, list) or len(queries) > MAX_POINTS:
            reject('query-point-budget-or-missing-points', 'unsupported')
        segment_count = sum(len(ring) - 1 for members in prepared.values() for member in members if member['status'] == 'valid'
                            for polygon in member['prepared'] for ring in polygon)
        if len(queries) * segment_count > MAX_POINT_SEGMENT_CHECKS:
            reject('point-segment-work-budget-exceeded', 'unsupported')
        result.update(context=context(request['context']), source_files=custody, status='diagnostic')
        ids = [q.get('id') for q in queries if isinstance(q, dict)]
        if len(ids) != len(queries) or not all(isinstance(x, str) and x for x in ids) or len(ids) != len(set(ids)):
            reject('missing-or-duplicate-query-point-id')
        for query in queries:
            row = {'point_id': query['id'], 'classes': [], 'status': 'unknown'}
            try:
                p = point(query.get('xy'))
                states = {role: collection_state(p, members) for role, members in prepared.items()}
                row['collections'] = states
                if any(s['unknown_member_ids'] for s in states.values()):
                    row['reason'] = 'invalid-unsupported-or-unknown-original-member'
                elif states['gap']['state'] == 'outside':
                    row.update(status='outside-gap')
                elif any(s['boundary_member_ids'] for s in states.values()):
                    row.update(status='boundary', reason='original-ring-boundary-members-retained')
                else:
                    first, second = (states[r]['state'] == 'inside' for r in ('first', 'second'))
                    label = 'both' if first and second else 'first-only' if first else 'second-only' if second else 'neither'
                    row.update(status='classified', classes=[label], ambiguity='source-overlap' if label == 'both' else 'source-uncovered' if label == 'neither' else 'none')
            except DiagnosticError as error:
                row.update(status=error.status, reason=error.reason)
            result['points'].append(row)
    except DiagnosticError as error:
        result.update(status=error.status, reason=error.reason)
    return result
