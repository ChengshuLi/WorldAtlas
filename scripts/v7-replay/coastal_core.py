"""Reference coastal-band classifier, driven by a versioned decision policy.

This research candidate uses only the physical grid and decision-derived land.
It rejects uncertifiable crop edges rather than assuming omitted shores are far.
"""
import math
import numpy as np
from scipy.spatial import cKDTree
import shared_nearest as shore


def policy(snapshot, *, allow_selected_research=False):
    records=[p for p in snapshot.get('policies',[]) if p.get('kind')=='coastline_assignment']
    if len(records)!=1 or not isinstance(records[0].get('id'),str) or not records[0]['id']:
        raise ValueError('exactly one identified coastline policy is required')
    decision=records[0];definition=decision.get('definition',{})
    if (not allow_selected_research or snapshot.get('decision_revision',{}).get('status')!='draft'
            or decision.get('evidence',{}).get('execution_status')!='selected_for_research'):
        raise ValueError('selected draft coastal policy and explicit research opt-in required')
    required={'method','band_metres','band_tolerance_metres','shore_geometry','distance','earth_radius_metres','tie_rules','land_input','water_input'}
    if not isinstance(definition,dict) or set(definition)!=required or definition.get('method')!='nearest_final_shore_band_v1':
        raise ValueError('unsupported coastal policy definition')
    p=definition
    if (p['shore_geometry']!='physical_land_water_grid_edges' or p['distance']!='spherical_segment'
            or p['land_input']!='final_decision_assigned_land' or p['water_input']!='physical_water'):
        raise ValueError('unsupported coastline inputs, geometry or distance')
    def number(raw):
        if isinstance(raw,bool):raise ValueError('invalid coastal numeric parameter')
        try:v=float(raw)
        except (TypeError,ValueError):raise ValueError('invalid coastal numeric parameter') from None
        if not math.isfinite(v):raise ValueError('invalid coastal numeric parameter')
        return v
    band,bandtol,radius=map(number,(p['band_metres'],p['band_tolerance_metres'],p['earth_radius_metres']))
    if not (0 < band <= 1_000_000 and 0 <= bandtol <= 1 and radius==shore.geom.R):
        raise ValueError('unsupported coastal band, threshold tolerance or sphere radius')
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


def index_present(edges,pairs):
    indices={}
    if not len(edges['mids']):return indices
    for _,lc,_ in pairs:
        m=edges['category']==lc
        if np.any(m):
            part={k:edges[k][m] for k in ('mids','lat0','lon0','lat1','lon1','kind','half_lengths','category')}
            indices[lc]=(part,cKDTree(part['mids']),float(part['half_lengths'].max()))
    return indices


def classify(lat,lon,bounds,width,height,step,pairs,tolerance,band,bandtol,indices):
    """Return code 0 outside band or participant water code inside.

    Per-class midpoint bounds certify common cases; exact spherical distances
    resolve ambiguous cells. Every result must be safe against omitted shores.
    """
    lat=np.asarray(lat,dtype=np.float64);lon=np.asarray(lon,dtype=np.float64)
    if len(lat)!=len(lon):raise ValueError('latitude and longitude lengths differ')
    points=shore.geom.unit(lat,lon);boundary=shore.boundary_lower(lat,lon,bounds,width,height,step)
    available=[p for p in pairs if p[1] in indices]
    if not available:
        if np.any(boundary<=band+bandtol):raise ValueError('crop cannot certify coastal band; increase halo')
        return np.zeros(len(lat),dtype=np.uint8),{'bounded':len(lat),'exact':0}
    lows=[];highs=[]
    for _,lc,_ in available:
        data,tree,maxhalf=indices[lc];chord,ix=tree.query(points,k=1,workers=1)
        mid=2*shore.geom.R*np.arcsin(np.clip(chord/2,0,1))
        lows.append(np.maximum(0,mid-maxhalf));highs.append(mid+data['half_lengths'][ix])
    lows=np.column_stack(lows);highs=np.column_stack(highs)
    chosen=np.argmin(highs,axis=1);upper=highs[np.arange(len(lat)),chosen]
    other=lows.copy();other[np.arange(len(lat)),chosen]=np.inf
    safe_inside=(upper<=band+bandtol)&(upper+tolerance<other.min(axis=1))&(upper+tolerance<boundary)
    safe_outside=(lows.min(axis=1)>band+bandtol)&(boundary>band+bandtol)
    out=np.zeros(len(lat),dtype=np.uint8)
    for i,(_,_,code) in enumerate(available):out[safe_inside & (chosen==i)]=code
    pending=np.flatnonzero(~(safe_inside|safe_outside))
    if len(pending):
        ds=[]
        for _,lc,_ in available:
            data,tree,maxhalf=indices[lc]
            d,_,_=shore.geom.nearest(points[pending],lat[pending],lon[pending],data,tree=tree,maxhalf=maxhalf,tol_m=tolerance,workers=1)
            ds.append(d)
        ds=np.column_stack(ds);minimum=ds.min(axis=1);inside=minimum<=band+bandtol
        if np.any(inside & (minimum+tolerance>=boundary[pending])) or np.any(~inside & (boundary[pending]<=band+bandtol)):
            raise ValueError('crop cannot certify coastal band; increase halo')
        selected=np.argmax(ds<=minimum[:,None]+tolerance,axis=1)
        for i,(_,_,code) in enumerate(available):out[pending[inside & (selected==i)]]=code
    return out,{'bounded':int(len(lat)-len(pending)),'exact':int(len(pending))}
