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


def build_partitions(domain):
    """Build scoped cell partitions from selected mainland lines and routes."""
    records = {('boundary', item['boundary_id']): item for item in domain['mainland_boundaries']}
    records.update({('route', item['route_id']): item for item in domain['routes']})
    result = []
    for policy in domain.get('policies', []):
        if policy['kind'] != 'scoped_land_partition':
            continue
        definition, points = policy['definition'], []
        for section in definition['sections']:
            record = records[section['kind'], section['id']]
            coordinates = feature_geometry(record, ('LineString',))['coordinates']
            if section.get('reverse', False):
                coordinates = list(reversed(coordinates))
            if points and points[-1] != coordinates[0]:
                raise ValueError('selected land partition lines do not join')
            points.extend(coordinates if not points else coordinates[1:])
        for face in partition_faces(dict(type='LineString', coordinates=points),
                                    definition['bounds_lon_lat'], definition['sides']):
            result.append(dict(face, policy_id=policy['id']))
    return result
