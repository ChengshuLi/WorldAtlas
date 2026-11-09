"""Reference coastal-band classifier, driven by a versioned decision policy.

This research candidate uses only the physical grid and decision-derived land.
It rejects uncertifiable crop edges rather than assuming omitted shores are far.
"""
import math
import numpy as np
from scipy.spatial import cKDTree
import shared_nearest as shore
import local_water_overlay


def policy(snapshot, *, allow_selected_research=False):
    records=[p for p in snapshot.get('policies',[]) if p.get('kind')=='coastline_assignment']
    if len(records)!=1 or not isinstance(records[0].get('id'),str) or not records[0]['id']:
        raise ValueError('exactly one identified coastline policy is required')
    decision=records[0];definition=decision.get('definition',{})
    if (not allow_selected_research or snapshot.get('decision_revision',{}).get('status')!='draft'
            or not local_water_overlay.selected(snapshot,decision)):
        raise ValueError('selected draft coastal policy and explicit research opt-in required')
    required={'method','band_metres','band_tolerance_metres','shore_geometry','distance','ellipsoid','tie_rules','land_input','water_input'}
    if not isinstance(definition,dict) or set(definition)!=required or definition.get('method')!='nearest_final_shore_band_v2':
        raise ValueError('unsupported coastal policy definition')
    p=definition
    if (p['shore_geometry']!='physical_coastal_land_cell_centers_4_neighbor_v1' or p['distance']!='wgs84_ellipsoidal_center_to_center' or p['ellipsoid']!='WGS84'
            or p['land_input']!='final_decision_assigned_land' or p['water_input']!='physical_water'):
        raise ValueError('unsupported coastline inputs, geometry or distance')
    def number(raw):
        if isinstance(raw,bool):raise ValueError('invalid coastal numeric parameter')
        try:v=float(raw)
        except (TypeError,ValueError):raise ValueError('invalid coastal numeric parameter') from None
        if not math.isfinite(v):raise ValueError('invalid coastal numeric parameter')
        return v
    band,bandtol=map(number,(p['band_metres'],p['band_tolerance_metres']))
    if not (0 < band <= 1_000_000 and 0 <= bandtol <= 1):
        raise ValueError('unsupported coastal band or threshold tolerance')
    tie=p['tie_rules']
    if not isinstance(tie,dict):raise ValueError('coast tie rules required')
    entities=tie.get('priority_entity_ids')
    # Reuse exact entity-priority and 10-micrometre-capable validation.
    fake={'assignment_method':'shared_nearest_assigned_shore','participant_entity_ids':entities,'tie_rules':tie}
    pairs,tolerance=shore.selected_rules(snapshot,fake)
    land_entities={b.get('entity_id') for b in snapshot.get('category_bindings',[]) if b.get('physical_class')=='land' and b.get('code') in range(17,23)}
    if set(entities)!=land_entities or len(entities)!=6:
        raise ValueError('coastal priority must cover every continental land entity once')
    return decision,pairs,tolerance,band,bandtol


def index_present(centers,pairs):
    indices={}
    if not len(centers['mids']):return indices
    for _,lc,_ in pairs:
        m=centers['category']==lc
        if np.any(m):
            part={k:centers[k][m] for k in ('mids','lat','lon','category')}
            indices[lc]=(part,cKDTree(part['mids']))
    return indices

def classify(lat,lon,bounds,width,height,step,pairs,tolerance,band,bandtol,indices):
    return shore.classify_wgs84(lat,lon,bounds,width,height,step,pairs,tolerance,indices,band=band,bandtol=bandtol)
