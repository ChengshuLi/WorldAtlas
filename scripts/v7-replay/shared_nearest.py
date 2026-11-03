"""Shared SeaVoX basin assignment from physical water and final land only.

No previous water labels are inputs. Distances are to the spherical grid-edge
shore, in metres. Each participant is indexed independently; missing shores or
an insufficient crop fail closed. This module is a candidate, not a release.
"""
from __future__ import annotations
import math
import numpy as np
from scipy.spatial import cKDTree
import spherical_shore as geom


def binding(snapshot, entity, physical_class, codes):
    values = [b.get('code') for b in snapshot.get('category_bindings', [])
              if b.get('entity_id') == entity and b.get('physical_class') == physical_class]
    if len(values) != 1 or type(values[0]) is not int or values[0] not in codes:
        raise ValueError(f'entity {entity} lacks a unique {physical_class} binding')
    return values[0]


def selected_rules(snapshot, basin):
    """Resolve the versioned priority by stable entity ID, not category order."""
    if basin.get('assignment_method') != 'shared_nearest_assigned_shore':
        raise ValueError('unsupported shared-basin assignment method')
    participants = basin.get('participant_entity_ids')
    if not isinstance(participants, list) or len(participants) < 2 or len(set(participants)) != len(participants):
        raise ValueError('shared basin requires distinct participant entities')
    tie = basin.get('tie_rules')
    if (not isinstance(tie, dict) or set(tie) != {'method','tie_break','priority_entity_ids','tolerance_metres'}
            or tie.get('method') != 'within_minimum_distance_tolerance' or tie.get('tie_break') != 'first_entity_in_priority_order'):
        raise ValueError('unsupported or missing shared-basin tie rules')
    order = tie.get('priority_entity_ids')
    if not isinstance(order, list) or len(order) != len(participants) or len(set(order)) != len(order) or set(order) != set(participants):
        raise ValueError('tie priority must list each participant exactly once')
    raw = tie.get('tolerance_metres')
    if isinstance(raw, bool): raise ValueError('invalid tie tolerance')
    try: tolerance = float(raw)
    except (TypeError, ValueError): raise ValueError('invalid tie tolerance') from None
    if not math.isfinite(tolerance) or tolerance < 0 or tolerance > 1:
        raise ValueError('invalid tie tolerance')
    pairs = [(entity, binding(snapshot, entity, 'land', range(17,23)),
              binding(snapshot, entity, 'water', range(1,7))) for entity in order]
    if len({p[1] for p in pairs}) != len(pairs) or len({p[2] for p in pairs}) != len(pairs):
        raise ValueError('participant land and water bindings must be distinct')
    return pairs, tolerance


def crop(rows, runs, y, x0, x1, width):
    if not (0 <= y < len(rows)-1 and 0 < x1-x0 <= width): raise ValueError('invalid crop')
    first,last=int(rows[y]),int(rows[y+1]); ends=runs[2*first:2*last:2]; vals=runs[2*first+1:2*last:2]
    if not len(ends) or int(ends[0]) <= 0 or int(ends[-1]) != width or np.any(ends[1:] <= ends[:-1]):
        raise ValueError(f'invalid RLE row {y}')
    result=np.empty(x1-x0, dtype=np.uint32); cur=0; x=x0
    while x < x1:
        xm=x%width; take=min(x1-x,width-xm); stop=xm+take
        i=int(np.searchsorted(ends,xm,side='right'))
        while xm < stop:
            e=min(int(ends[i]),stop); result[cur:cur+e-xm]=int(vals[i]); cur+=e-xm; xm=e; i+=1
        x+=take
    return result


def crop_bounds(bounds, width, height, step, pad_degrees):
    x0,x1,y0,y1=bounds
    if not math.isfinite(pad_degrees) or pad_degrees <= 0: raise ValueError('pad must be positive')
    pad=math.ceil(pad_degrees/step)
    xa,xb=x0-pad,x1+pad
    if xb-xa >= width: xa,xb=0,width
    return xa,xb,max(0,y0-pad),min(height,y1+pad)


def edges_for_crop(physical, land, bounds, width, height, step, land_codes):
    x0,x1,y0,y1=bounds; parts=[]; w=x1-x0
    def add(lat0,lon0,lat1,lon1,kind,cats):
        n=len(cats)
        if n: parts.append(tuple(np.asarray(v,dtype=(np.uint8 if i in (4,5) else np.float64))
                                 for i,v in enumerate((lat0,lon0,lat1,lon1,np.full(n,kind),cats))))
    prevp=prevl=None
    # Add a neighboring row so a boundary edge on the crop boundary is not omitted.
    for y in range(max(0,y0-1), min(height,y1+1)):
        p=crop(*physical,y,x0,x1,width); l=crop(*land,y,x0,x1,width)
        if np.any(~np.isin(p,[1,17])) or np.any((p==17)&~np.isin(l,range(17,23))):
            raise ValueError(f'physical or land assignment invalid at row {y}')
        dry=(p==17)&np.isin(l,land_codes); top=90-y*step; bot=top-step
        for side in (0,1):
            mask=np.zeros(w,dtype=bool)
            if side==0: mask[1:]=dry[1:]&(p[:-1]==1)
            else: mask[:-1]=dry[:-1]&(p[1:]==1)
            ix=np.flatnonzero(mask)
            lon=-180+(x0+ix+(1 if side else 0))*step
            add(np.full(len(ix),top),lon,np.full(len(ix),bot),lon,0,l[ix])
        if w==width:
            for ix,neighbor,lon in ((0,w-1,-180.0),(w-1,0,180.0)):
                if dry[ix] and p[neighbor]==1: add([top],[lon],[bot],[lon],0,[l[ix]])
        if prevp is not None:
            lat=90-y*step
            for mask,cats in (((prevp==17)&(p==1)&np.isin(prevl,land_codes),prevl),
                              ((prevp==1)&(p==17)&np.isin(l,land_codes),l)):
                ix=np.flatnonzero(mask)
                if len(ix):
                    cuts=np.r_[0,np.flatnonzero((np.diff(ix)>1)|(cats[ix[1:]]!=cats[ix[:-1]]))+1,len(ix)]
                    starts=ix[cuts[:-1]]; ends=ix[cuts[1:]-1]+1
                    lo=-180+(x0+starts)*step; hi=-180+(x0+ends)*step
                    add(np.full(len(starts),lat),lo,np.full(len(starts),lat),hi,1,cats[starts])
        prevp,prevl=p,l
    data=geom.edge_data(parts)
    if not len(data['mids']): raise ValueError('no participant shorelines in crop')
    return data


def boundary_lower(lat,lon,bounds,width,height,step):
    """Conservative distance to any shoreline omitted outside the crop."""
    x0,x1,y0,y1=bounds; latr=np.deg2rad(lat); lonr=np.deg2rad(lon)
    d=np.full(len(lat),np.inf,dtype=np.float64)
    if y0>0: d=np.minimum(d,np.abs(lat-(90-y0*step))*math.pi/180*geom.R)
    if y1<height: d=np.minimum(d,np.abs(lat-(90-y1*step))*math.pi/180*geom.R)
    if x1-x0<width:
        for edge in (x0,x1):
            lam=math.radians(-180+edge*step)
            d=np.minimum(d,geom.R*np.arcsin(np.clip(np.abs(np.cos(latr)*np.sin(lonr-lam)),0,1)))
    return d


def make_indexes(edges, pairs):
    indexes={}
    for _,land_code,_ in pairs:
        mask=edges['category']==land_code
        if not np.any(mask): raise ValueError(f'crop has no shoreline for participant land code {land_code}')
        part={k:edges[k][mask] for k in ('mids','lat0','lon0','lat1','lon1','kind','half_lengths','category')}
        indexes[land_code]=(part,cKDTree(part['mids']),float(part['half_lengths'].max()))
    return indexes


def classify(lat,lon,bounds,width,height,step,pairs,tolerance,indexes):
    """Classify points; prove omitted shore cannot change result or fail."""
    lat=np.asarray(lat,dtype=np.float64); lon=np.asarray(lon,dtype=np.float64)
    points=geom.unit(lat,lon); lower_boundary=boundary_lower(lat,lon,bounds,width,height,step)
    lows=[]; highs=[]
    for _,land_code,_ in pairs:
        data,tree,maxhalf=indexes[land_code]
        chord,idx=tree.query(points,k=1,workers=1)
        mid=2*geom.R*np.arcsin(np.clip(chord/2,0,1))
        lows.append(np.maximum(0,mid-maxhalf)); highs.append(mid+data['half_lengths'][idx])
    lows=np.column_stack(lows); highs=np.column_stack(highs)
    best=np.argmin(highs,axis=1); upper=highs[np.arange(len(lat)),best]
    other=lows.copy(); other[np.arange(len(lat)),best]=np.inf
    cert=(upper+tolerance < other.min(axis=1)) & (upper+tolerance < lower_boundary)
    chosen=best.copy(); exact=~cert
    if np.any(exact):
        ix=np.flatnonzero(exact); distances=[]
        for _,land_code,_ in pairs:
            data,tree,maxhalf=indexes[land_code]
            distance,_,_=geom.nearest(points[ix],lat[ix],lon[ix],data,tree=tree,maxhalf=maxhalf,tol_m=tolerance,workers=1)
            distances.append(distance)
        distances=np.column_stack(distances); minimum=distances.min(axis=1)
        if np.any(minimum+tolerance >= lower_boundary[ix]):
            raise ValueError('crop cannot certify nearest shore; increase pad')
        # Pairs are in explicitly persisted entity priority order.
        chosen[ix]=np.argmax(distances <= minimum[:,None]+tolerance,axis=1)
    return np.asarray([pairs[i][2] for i in chosen],dtype=np.uint8), int(cert.sum()), int(exact.sum())
