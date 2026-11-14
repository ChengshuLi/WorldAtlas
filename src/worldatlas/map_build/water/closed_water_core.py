"""Validate the selected enclosed-water assignment policy."""

from worldatlas.map_build.water import shared_nearest as shore


def policy(snapshot):
    policies = [
        p for p in snapshot.get('policies', []) if p.get('kind') == 'closed_water_assignment'
    ]
    if len(policies) != 1 or not isinstance(policies[0].get('id'), str) or not policies[0]['id']:
        raise ValueError('exactly one identified closed-water policy is required')
    decision = policies[0]
    d = decision.get('definition', {})
    expected = {
        'method',
        'boundary_participants',
        'distance',
        'ellipsoid',
        'latitude_grid_edge_contacts',
        'multiple_participants',
        'no_participants',
        'one_participant',
        'source_cut_contacts',
        'tie_rules',
        'unresolved_zero_neighbors',
        'shore_geometry',
    }
    if (
        not isinstance(d, dict)
        or set(d) != expected
        or d.get('method') != 'closed_water_component_v2'
    ):
        raise ValueError('unsupported closed-water policy')
    p = d
    if (
        p['boundary_participants'] != 'adjacent_final_water_or_assigned_land'
        or p['latitude_grid_edge_contacts'] != 'report_only'
        or p['unresolved_zero_neighbors'] != 'report_only'
        or p['source_cut_contacts'] != 'retain_ocean_parent_source_cut_review'
        or p['one_participant'] != 'direct_fill'
        or p['multiple_participants'] != 'nearest_assigned_land_shore'
        or p['no_participants'] != 'report_only'
        or p['shore_geometry'] != 'physical_coastal_land_cell_centers_4_neighbor_v1'
        or p['distance'] != 'wgs84_ellipsoidal_center_to_center'
        or p['ellipsoid'] != 'WGS84'
    ):
        raise ValueError('unsupported closed-water safety or geometry rule')
    tie = p['tie_rules']
    ids = tie.get('priority_entity_ids') if isinstance(tie, dict) else None
    pairs, tol = shore.tie_policy(snapshot, tie)
    land_entities = {
        b.get('entity_id')
        for b in snapshot.get('category_bindings', [])
        if b.get('physical_class') == 'land'
    }
    if set(ids) != land_entities:
        raise ValueError('closed-water priority must cover every land entity')
    return policies[0], pairs, tol
