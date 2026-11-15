"""Construct scoped land partitions from selected lines and side witnesses."""

import math

from shapely.geometry import LineString, Point, box, mapping
from shapely.ops import split

from worldatlas.map_build.inputs.features import feature_geometry


def partition_faces(geometry, bounds, sides):
    """Split a geographic rectangle once; each witness selects one opposite face."""
    if (len(bounds) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in bounds)
            or not -180 <= bounds[0] < bounds[2] <= 180
            or not -90 <= bounds[1] < bounds[3] <= 90):
        raise ValueError('land partition needs an unwrapped geographic rectangle')
    line, scope = LineString(geometry['coordinates']), box(*bounds)
    clipped = line.intersection(scope)
    if (not line.is_simple or clipped.geom_type != 'LineString' or clipped.is_empty
            or not scope.boundary.covers(Point(clipped.coords[0]))
            or not scope.boundary.covers(Point(clipped.coords[-1]))):
        raise ValueError('selected line must cross the scope once without a loop')
    faces = list(split(scope, clipped).geoms)
    if len(faces) != 2 or len(sides) != 2 or sides[0]['entity_id'] == sides[1]['entity_id']:
        raise ValueError('land partition must have two faces and different entities')
    result, selected = [], set()
    for side in sides:
        point = Point(side['coordinates'])
        matches = [i for i, face in enumerate(faces) if face.contains(point)]
        if len(matches) != 1 or matches[0] in selected:
            raise ValueError('land partition witnesses must be inside opposite faces')
        selected.add(matches[0])
        result.append(dict(geometry=mapping(faces[matches[0]]), entity_id=side['entity_id']))
    return result


def resolve_component_partitions(records, features, components, bindings, *, protected=()):
    """Assign whole components; scope-edge pieces retain their existing assignment."""
    by_id = {f['feature_id']: f for f in features}
    codes = {b['entity_id']: b['code'] for b in bindings if b['physical_class'] == 'land'}
    protected, assigned, claims, ids = set(protected), {}, [], set()
    totals = components.totals()
    for record in records:
        if record['method'] != 'land_components':
            continue
        ident = record['id']
        if ident in ids:
            raise ValueError('duplicate geographic partition')
        ids.add(ident)
        sides = [dict(entity_id=record['side_' + side + '_entity_id'],
                      coordinates=record['side_' + side + '_witness']) for side in ('a', 'b')]
        if any(side['entity_id'] not in codes for side in sides):
            raise ValueError('geographic partition targets an unbound land entity')
        geometry = feature_geometry(by_id[record['feature_id']], ('LineString',))
        faces = partition_faces(geometry, record['bounds_lon_lat'], sides)
        within = components.profile(mapping(box(*record['bounds_lon_lat'])))
        first = components.profile(faces[0]['geometry'])
        entities, edge = {}, []
        for root, count in within.items():
            if root in protected:
                continue
            if count != totals[root]:
                edge.append(root)
                continue
            a = first.get(root, 0)
            if a not in (0, count):
                raise ValueError(f'partition {ident} crosses land component {root}')
            entity = faces[0 if a == count else 1]['entity_id']
            if root in assigned and assigned[root] != entity:
                raise ValueError('geographic partitions assign a component to different entities')
            assigned[root] = entities[root] = entity
        claims.append(dict(partition_id=ident, component_entities=entities,
                           scope_edge_components=sorted(edge)))
    return dict(component_entities=assigned, claims=claims)


def build_partitions(domain, regions):
    """Apply selected region sides to final land cells within an explicit scope."""
    from shapely.geometry import shape
    result = []
    for record in domain.get('partitions', []):
        if record['method'] != 'land_cells':
            continue
        region = shape(regions[record['mainland_region_id']]['geometry'])
        scope = box(*record['bounds_lon_lat'])
        for side, inside in [('a', True), ('b', False)]:
            witness = Point(record['side_' + side + '_witness'])
            if (not scope.contains(witness) or region.boundary.intersects(witness)
                    or region.contains(witness) != inside):
                raise ValueError('partition witnesses must be inside opposite region faces')
            face = scope.intersection(region) if inside else scope.difference(region)
            if face.is_empty or not face.is_valid:
                raise ValueError('scoped geographic partition has an empty or invalid side')
            result.append(dict(geometry=mapping(face),
                               entity_id=record['side_' + side + '_entity_id'],
                               policy_id=record['id']))
    return result
