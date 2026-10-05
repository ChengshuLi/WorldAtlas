"""Exact connectivity of retained coverage candidates; never an ownership repair.

Positive-length contacts connect polygons. Point-only contacts are retained as
ambiguities. No buffering, coordinate rounding, area cutoff or MakeValid occurs.
Dateline contacts compare translated copies, while output preserves originals.
"""
import math

from shapely import STRtree, union_all
from shapely.affinity import translate
from shapely.geometry import box, mapping, shape

from evidence.immutable import canonical_json, sha256

VERSION = 'worldatlas-geographic-gap-components-v1'


def components(features, blocked_tiles=(), domain=(-180, -60, 180, 85.0511287798066)):
    """Return stable membership, exact shapes and separately retained contacts.

    Input must consist of positive, valid Polygon atoms with unique string IDs.
    Positive-area overlaps are input defects: retain them and flag their entire
    component; they do not establish unique measured union area.
    """
    features = sorted(features, key=lambda f: f['id'])
    ids = [f['id'] for f in features]
    if any(not isinstance(x, str) or not x for x in ids) or len(set(ids)) != len(ids):
        raise ValueError('Unique nonempty string fragment IDs required')
    geometries = [shape(f['geometry']) for f in features]
    for f, g in zip(features, geometries):
        if g.geom_type != 'Polygon' or g.is_empty or not g.is_valid or g.area <= 0:
            raise ValueError('Invalid/nonpositive polygon fragment: ' + f['id'])
        if not all(math.isfinite(v) for xy in g.exterior.coords for v in xy):
            raise ValueError('Nonfinite coordinates')
        if not box(*domain).covers(g):
            raise ValueError('Fragment outside declared domain: ' + f['id'])
        area = f['properties'].get('area_m2')
        if area is not None and (not isinstance(area, (int, float)) or isinstance(area, bool)
                                 or not math.isfinite(area) or area <= 0):
            raise ValueError('Invalid measured area')
    parent = list(range(len(features)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def join(i, j):
        a, b = root(i), root(j)
        parent[max(a, b)] = min(a, b)

    contacts, seen = [], set()

    def inspect(i, j, other, wrap):
        key = (min(i, j), max(i, j), wrap)
        if i == j or key in seen:
            return
        seen.add(key)
        intersection = geometries[i].intersection(other)
        if intersection.is_empty:
            return
        if intersection.area > 0:
            kind = 'positive-area-input-overlap'
            join(i, j)
        elif intersection.length > 0:
            kind = 'shared-edge'
            join(i, j)
        else:
            kind = 'point-only-ambiguous'
        contacts.append({'fragments': sorted([ids[i], ids[j]]), 'kind': kind,
                         'dateline': wrap, 'geometry': mapping(intersection)})

    tree = STRtree(geometries)
    for i, g in enumerate(geometries):
        for j in tree.query(g, predicate='intersects'):
            if j > i:
                inspect(i, int(j), geometries[j], False)
    # Only exact +/-180 boundary contacts receive the cylinder comparison.
    east = [i for i, g in enumerate(geometries) if g.bounds[2] == 180]
    west = [i for i, g in enumerate(geometries) if g.bounds[0] == -180]
    shifted = [translate(geometries[i], xoff=360) for i in west]
    wrapped_tree = STRtree(shifted)
    for i in east:
        for k in wrapped_tree.query(geometries[i], predicate='intersects'):
            inspect(i, west[k], shifted[k], True)
    groups = {}
    for i in range(len(features)):
        groups.setdefault(root(i), []).append(i)
    records, membership = [], {}
    blocks = [box(*t['bounds']) for t in blocked_tiles]
    # Unknown coverage at the cylinder seam is just as adjacent as fragments.
    # Exact edge/point contact keeps uncertainty; near contacts are not snapped.
    blocks += [translate(b, xoff=-360) for b in blocks if b.bounds[2] == 180] + [
        translate(b, xoff=360) for b in blocks if b.bounds[0] == -180]
    boundary = box(*domain).boundary
    for indexes in groups.values():
        bindings = [{'id': ids[i], 'feature_sha256': sha256(canonical_json(features[i]))}
                    for i in indexes]
        identity = 'gap:' + sha256(canonical_json(bindings))
        for i in indexes:
            membership[ids[i]] = identity
        # Union original positions: dateline components can remain MultiPolygon.
        # This is a wrapped component, not an invented 360-degree planar bridge.
        geometry = union_all([geometries[i] for i in indexes])
        if not geometry.is_valid or geometry.is_empty:
            raise ValueError('Invalid exact component union; preserve original inputs')
        if any(not geometry.covers(geometries[i]) for i in indexes):
            raise ValueError('Component union loses an original fragment; preserve inputs')
        measured = [features[i]['properties'].get('area_m2') for i in indexes]
        nearby = {}
        for i in indexes:
            for location in features[i]['properties'].get('nearby_locations', []):
                nearby[sha256(canonical_json(location))] = location
        records.append({'type': 'Feature', 'id': identity, 'geometry': mapping(geometry),
                        'properties': {
                            'fragment_bindings': bindings,
                            'measured_fragment_area_sum_m2': math.fsum(a for a in measured if a is not None),
                            'measured_fragment_count': sum(a is not None for a in measured),
                            'unmeasured_fragment_ids': [ids[i] for i in indexes
                                                        if features[i]['properties'].get('area_m2') is None],
                            'touches_blocked_tile': any(geometry.intersects(b) for b in blocks),
                            'touches_domain_boundary': geometry.intersects(boundary),
                            'touches_reference_shore': any(features[i]['properties'].get('touches_reference_shore')
                                                           for i in indexes),
                            'diagnostic_nearby_locations': [nearby[k] for k in sorted(nearby)],
                            'water_status': 'unverified', 'administrative_assignment': None,
                            'positive_area_input_overlap': False, 'dateline_connected': False}})
    by_id = {r['id']: r for r in records}
    for c in contacts:
        c['components'] = [membership[x] for x in c['fragments']]
        if c['kind'] == 'positive-area-input-overlap':
            by_id[c['components'][0]]['properties']['positive_area_input_overlap'] = True
        if c['dateline'] and c['kind'] != 'point-only-ambiguous':
            by_id[c['components'][0]]['properties']['dateline_connected'] = True
    return sorted(records, key=lambda f: f['id']), sorted(
        contacts, key=lambda c: (c['fragments'], c['dateline'], c['kind']))
