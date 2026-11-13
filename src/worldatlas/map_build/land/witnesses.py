"""Resolve imported source witnesses to current physical component groups."""

from fractions import Fraction

from shapely.geometry import Point, shape

from worldatlas.map_build.inputs.features import feature_geometry


def resolve_witnesses(domain, components):
    """Check selected point identities, neighborhoods and group relationships."""
    features = {item['feature_id']: item for item in domain['features']}
    witnesses = {}
    grid = components.grid
    for selected in domain['mainland_witnesses']:
        point = features[selected['point_feature_id']]
        area = features[selected['identity_feature_id']]
        geometry = feature_geometry(point, ('Point',))
        polygon = feature_geometry(area, ('Polygon', 'MultiPolygon'))
        properties = area['evidence']['provider_properties']
        if (
            str(properties[selected['identity_id_property']]) != area['source_feature_id']
            or properties[selected['identity_name_property']] != selected['identity_name']
            or properties[selected['identity_class_property']] != selected['identity_class']
            or point['evidence']['provider_properties']['name'] != selected['point_name']
            or str(point['evidence']['provider_properties'][selected['id_property']])
            != point['source_feature_id']
            or not shape(polygon).contains(Point(geometry['coordinates']))
        ):
            raise ValueError('mainland witness does not match its selected source identity')
        lon, lat = geometry['coordinates']
        root = components.point(lon, lat)
        step = Fraction(str(grid.step))
        x = int((Fraction(str(lon)) - Fraction(str(grid.west))) // step)
        y = int((Fraction(str(grid.north)) - Fraction(str(lat))) // step)
        radius, maximum = selected['radius_cells'], selected['max_water_cells']
        if (
            type(radius) is not int
            or radius < 0
            or type(maximum) is not int
            or not 0 <= maximum < (2 * radius + 1) ** 2
            or not radius <= y < grid.height - radius
            or 2 * radius + 1 > grid.width
        ):
            raise ValueError('invalid mainland witness neighborhood')
        observed, water = set(), 0
        for yy in range(y - radius, y + radius + 1):
            for xx in range(x - radius, x + radius + 1):
                value = components.component_at(float(grid.longitude(xx)), float(grid.latitude(yy)))
                if value is None:
                    water += 1
                else:
                    observed.add(value)
        if observed != {root} or water > maximum:
            raise ValueError('mainland witness neighborhood is water or ambiguous')
        ident = selected['witness_id']
        if ident in witnesses:
            raise ValueError('duplicate mainland witness')
        witnesses[ident] = dict(component_id=root, row=y, column=x, water_cells=water)
    groups, used = {}, set()
    for selected in domain['mainland_witness_groups']:
        members = selected['witness_ids']
        if not members or len(set(members)) != len(members) or used.intersection(members):
            raise ValueError('empty or multiply assigned mainland witnesses')
        roots = {witnesses[ident]['component_id'] for ident in members}
        if len(roots) != 1 or selected['group_id'] in groups:
            raise ValueError('same-group mainland witness mismatch')
        groups[selected['group_id']] = dict(
            component_id=next(iter(roots)),
            role=selected['role'],
            target_entity_ids=selected['target_entity_ids'],
        )
        used.update(members)
    if used != witnesses.keys():
        raise ValueError('unconsumed mainland witness')
    # Retained selections express these pairs as relation records.
    earlier = domain.get('mainland_group_relations', [])
    if any(item['relation'] != 'different' for item in earlier):
        raise ValueError('unsupported mainland group relation')
    pairs = domain.get('distinct_groups', [item['group_ids'] for item in earlier])
    for a, b in pairs:
        if groups[a]['component_id'] == groups[b]['component_id']:
            raise ValueError('different-group mainland witness mismatch')
    return dict(groups=groups, witnesses=witnesses)
