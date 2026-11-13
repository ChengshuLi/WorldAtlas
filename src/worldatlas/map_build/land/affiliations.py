"""Resolve geographic selection rules against current land components."""

from shapely.geometry import shape

from worldatlas.map_build.inputs.features import affiliation_selection, feature_geometry


def resolve_affiliations(rules, features, components, bindings, *, protected=()):
    """Return current component claims from source-neutral geographic operations.

    Each rule combines conditions with ``all`` or ``any``. A condition selects
    a point's current component, components intersecting a polygon, or components
    wholly within a polygon. Exclusions and witnesses operate on those current
    components. No source archive or geographic-name dispatch is involved.
    """
    by_id = {f['feature_id']: f for f in features}
    if len(by_id) != len(features):
        raise ValueError('duplicate geographic feature ID')
    codes = {b['entity_id']: b['code'] for b in bindings if b['physical_class'] == 'land'}
    protected = set(protected)
    geometries, profiles = {}, {}

    def geometry(ident):
        if ident not in by_id:
            raise ValueError('component selection refers to a missing feature: ' + ident)
        if ident not in geometries:
            value = feature_geometry(
                by_id[ident],
                ('Point', 'Polygon', 'MultiPolygon'),
                coordinate_reference=by_id[ident]['coordinate_reference'],
            )
            parsed = shape(value)
            if parsed.is_empty or not parsed.is_valid:
                raise ValueError('component selection needs valid nonempty geometry')
            geometries[ident] = value
        return geometries[ident]

    def condition(record, candidates=None):
        ident, relation = record['feature_id'], record['relation']
        value = geometry(ident)
        if relation == 'point_component':
            if value['type'] != 'Point' or by_id[ident]['coordinate_reference'] != 'OGC:CRS84':
                raise ValueError('point-component selection needs a point')
            return {components.point(*value['coordinates'])}
        if relation not in ('intersects_component', 'contains_component'):
            raise ValueError('unsupported component selection relation')
        if value['type'] not in ('Polygon', 'MultiPolygon'):
            raise ValueError('polygon-component selection needs a polygon')
        if by_id[ident]['coordinate_reference'] != 'OGC:CRS84':
            operations = record['coordinate_operations']
            if operations['source_coordinate_reference'] != by_id[ident]['coordinate_reference']:
                raise ValueError(
                    'coordinate operation does not match the imported source coordinates'
                )
            if candidates is None:
                raise ValueError(
                    'projected contact needs a preceding geographic candidate selection'
                )
            counts = components.profile_projected(value, operations, candidates)
            if record.get('unknown_coordinates', 'reject') == 'reject' and any(
                v['unknown'] for v in counts.values()
            ):
                raise ValueError(
                    'coordinate operations do not cover all candidate component centers'
                )
            if record.get('unknown_coordinates', 'reject') not in ('reject', 'exclude'):
                raise ValueError('unsupported unknown-coordinate treatment')
            return {
                root
                for root, values in counts.items()
                if not values['unknown']
                and not values['boundary']
                and (
                    values['inside'] > 0
                    if relation == 'intersects_component'
                    else values['inside'] == components.totals()[root]
                )
            }
        if ident not in profiles:
            profiles[ident] = components.profile(value)
        counts = profiles[ident]
        if relation == 'intersects_component':
            return set(counts)
        totals = components.totals()
        return {root for root, count in counts.items() if count == totals[root]}

    claims, assigned, identifiers = [], {}, set()
    for rule in rules:
        ident, entity = rule['affiliation_id'], rule['entity_id']
        if ident in identifiers or entity not in codes:
            raise ValueError('duplicate affiliation or unbound target entity')
        identifiers.add(ident)
        selection = affiliation_selection(rule, by_id.keys())
        for assertion in selection.get('source_assertions', []):
            point = shape(geometry(assertion['point_feature_id']))
            area = shape(geometry(assertion['area_feature_id']))
            if point.geom_type != 'Point' or not area.contains(point):
                raise ValueError('selected source point is not inside its identity area')
        conditions = selection['conditions']
        selected = None
        for record in conditions:
            found = condition(record, selected if selection['combine'] == 'all' else None)
            selected = (
                found
                if selected is None
                else selected & found if selection['combine'] == 'all' else selected | found
            )
        for exclusion in selection.get('exclusions', []):
            selected -= condition(exclusion)
        included = [
            components.point(w['lon'], w['lat']) for w in selection.get('include_witnesses', [])
        ]
        excluded = [
            components.point(w['lon'], w['lat']) for w in selection.get('exclude_witnesses', [])
        ]
        if (
            len(set(included)) != len(included)
            or len(set(excluded)) != len(excluded)
            or set(included) & selected
            or not set(excluded) <= selected
        ):
            raise ValueError(
                'component inclusion/exclusion witnesses conflict with selected geometry'
            )
        selected = (selected - set(excluded)) | set(included)
        treatment = selection.get('protected_components', 'reject')
        if treatment == 'exclude':
            selected -= protected
        elif treatment != 'reject':
            raise ValueError('unsupported protected-component treatment')
        elif selected & protected:
            raise ValueError('regional affiliation would change a protected mainland component')
        if not selected:
            raise ValueError('geographic rule selects no current land components: ' + ident)
        for root in selected:
            if root in assigned and assigned[root] != entity:
                raise ValueError('geographic rules assign one component to different entities')
            assigned[root] = entity
        claims.append(
            {
                'affiliation_id': ident,
                'entity_id': entity,
                'entity_code': codes[entity],
                'component_ids': sorted(selected),
            }
        )
    return {'claims': claims, 'component_entities': assigned}
