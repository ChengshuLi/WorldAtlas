"""Construct scoped land partitions from selected lines and side witnesses."""

import math

from shapely.geometry import LineString, Point, box, mapping
from shapely.ops import split

from map_build.inputs.features import feature_geometry


def build_partitions(domain):
    """Resolve ordinary scoped-line rules without changing distance seeds.

    Each rule selects an ordered sequence of boundary/route records, a rectangle
    and two witnesses with target entity IDs. The selected line must divide the
    rectangle into exactly two faces; witnesses identify their intended owners.
    """
    records = {('boundary', item['boundary_id']): item for item in domain['mainland_boundaries']}
    records.update({('route', item['route_id']): item for item in domain['routes']})
    partitions = []
    for policy in domain.get('policies', []):
        if policy['kind'] != 'scoped_land_partition':
            continue
        definition = policy['definition']
        bounds = definition['bounds_lon_lat']
        if (
            len(bounds) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in bounds)
            or not -180 <= bounds[0] < bounds[2] <= 180
            or not -90 <= bounds[1] < bounds[3] <= 90
        ):
            raise ValueError('land partition needs an unwrapped geographic rectangle')
        points = []
        for section in definition['sections']:
            record = records[section['kind'], section['id']]
            coordinates = feature_geometry(record, ('LineString',))['coordinates']
            if section.get('reverse', False):
                coordinates = list(reversed(coordinates))
            if points and points[-1] != coordinates[0]:
                raise ValueError('selected land partition lines do not join')
            points.extend(coordinates if not points else coordinates[1:])
        line = LineString(points)
        scope = box(*bounds)
        clipped = line.intersection(scope)
        if (
            not line.is_simple
            or clipped.geom_type != 'LineString'
            or clipped.is_empty
            or not scope.boundary.covers(Point(clipped.coords[0]))
            or not scope.boundary.covers(Point(clipped.coords[-1]))
        ):
            raise ValueError('selected line must cross the scope once without a loop')
        faces = list(split(scope, clipped).geoms)
        witnesses = definition['sides']
        if len(faces) != 2 or len(witnesses) != 2:
            raise ValueError('land partition must have exactly two faces and witnesses')
        selected = set()
        for side in witnesses:
            point = Point(side['coordinates'])
            matches = [i for i, face in enumerate(faces) if face.contains(point)]
            if len(matches) != 1 or matches[0] in selected:
                raise ValueError('land partition witnesses must be inside opposite faces')
            selected.add(matches[0])
            partitions.append(
                dict(
                    geometry=mapping(faces[matches[0]]),
                    entity_id=side['entity_id'],
                    policy_id=policy['id'],
                )
            )
    return partitions
