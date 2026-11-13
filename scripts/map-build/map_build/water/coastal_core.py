"""Coastal-band policy and WGS84 classification.

Uses only the physical grid and final assigned land.
It rejects uncertifiable crop edges rather than assuming omitted shores are far.
"""

import math
from map_build.water import shared_nearest as shore


def policy(snapshot):
    records = [p for p in snapshot.get('policies', []) if p.get('kind') == 'coastline_assignment']
    if len(records) != 1 or not isinstance(records[0].get('id'), str) or not records[0]['id']:
        raise ValueError('exactly one identified coastline policy is required')
    decision = records[0]
    definition = decision.get('definition', {})
    required = {
        'method',
        'band_metres',
        'band_tolerance_metres',
        'shore_geometry',
        'distance',
        'ellipsoid',
        'tie_rules',
        'land_input',
        'water_input',
    }
    if (
        not isinstance(definition, dict)
        or set(definition) != required
        or definition.get('method') != 'nearest_final_shore_band_v2'
    ):
        raise ValueError('unsupported coastal policy definition')
    p = definition
    if (
        p['shore_geometry'] != 'physical_coastal_land_cell_centers_4_neighbor_v1'
        or p['distance'] != 'wgs84_ellipsoidal_center_to_center'
        or p['ellipsoid'] != 'WGS84'
        or p['land_input'] != 'final_decision_assigned_land'
        or p['water_input'] != 'physical_water'
    ):
        raise ValueError('unsupported coastline inputs, geometry or distance')

    def number(raw):
        if isinstance(raw, bool):
            raise ValueError('invalid coastal numeric parameter')
        try:
            v = float(raw)
        except (TypeError, ValueError):
            raise ValueError('invalid coastal numeric parameter') from None
        if not math.isfinite(v):
            raise ValueError('invalid coastal numeric parameter')
        return v

    band, bandtol = map(number, (p['band_metres'], p['band_tolerance_metres']))
    if not (band > 0 and bandtol >= 0):
        raise ValueError('unsupported coastal band or threshold tolerance')
    tie = p['tie_rules']
    if not isinstance(tie, dict):
        raise ValueError('coast tie rules required')
    pairs, tolerance = shore.tie_policy(snapshot, tie)
    land_entities = {
        b['entity_id'] for b in snapshot['category_bindings'] if b['physical_class'] == 'land'
    }
    if {entity for entity, _, _ in pairs} != land_entities:
        raise ValueError('coastal priority must cover every land entity once')
    return decision, pairs, tolerance, band, bandtol


def classify(lat, lon, bounds, width, height, step, pairs, tolerance, band, bandtol, indices):
    return shore.classify_wgs84(
        lat, lon, bounds, width, height, step, pairs, tolerance, indices, band=band, bandtol=bandtol
    )
