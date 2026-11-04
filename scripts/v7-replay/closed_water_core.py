"""Research-only unseeded-water classification from pinned ocean partition.

No old ocean labels or V2 continental labels are consulted. Component identity,
barrier counts and snapshot/physical lineage must be verified by the caller.
"""
from collections import Counter,defaultdict
import math
import numpy as np
import shared_nearest as shore


def policy(snapshot, *, allow_selected_research=False):
    policies=[p for p in snapshot.get('policies',[]) if p.get('kind')=='closed_water_assignment']
    if len(policies)!=1 or not isinstance(policies[0].get('id'),str) or not policies[0]['id']:
        raise ValueError('exactly one identified closed-water policy is required')
    decision=policies[0];d=decision.get('definition',{})
    if (not allow_selected_research or snapshot.get('decision_revision',{}).get('status')!='draft'
            or decision.get('evidence',{}).get('execution_status')!='selected_for_research'):
        raise ValueError('selected draft closed-water policy and explicit research opt-in required')
    expected={'method','boundary_participants','distance','earth_radius_metres','latitude_grid_edge_contacts',
              'multiple_participants','no_participants','one_participant','source_cut_contacts',
              'tie_rules','unresolved_zero_neighbors','shore_geometry'}
    if not isinstance(d,dict) or set(d)!=expected or d.get('method')!='closed_water_component_v1':
        raise ValueError('unsupported closed-water policy')
    p=d
    if (p['boundary_participants']!='adjacent_final_water_or_assigned_land'
        or p['latitude_grid_edge_contacts']!='report_only' or p['unresolved_zero_neighbors']!='report_only'
        or p['source_cut_contacts']!='retain_ocean_parent_source_cut_review'
        or p['one_participant']!='direct_fill' or p['multiple_participants']!='nearest_assigned_land_shore'
        or p['no_participants']!='report_only' or p['shore_geometry']!='physical_land_water_grid_edges'
        or p['distance']!='spherical_segment' or isinstance(p['earth_radius_metres'],bool)):
        raise ValueError('unsupported closed-water safety or geometry rule')
    try:radius=float(p['earth_radius_metres'])
    except (ValueError,TypeError):raise ValueError('invalid sphere radius') from None
    if not math.isfinite(radius) or radius!=shore.geom.R:raise ValueError('unsupported sphere radius')
    tie=p['tie_rules']; ids=tie.get('priority_entity_ids') if isinstance(tie,dict) else None
    fake={'assignment_method':'shared_nearest_assigned_shore','participant_entity_ids':ids,'tie_rules':tie}
    pairs,tol=shore.selected_rules(snapshot,fake)
    land_entities={b.get('entity_id') for b in snapshot.get('category_bindings',[]) if b.get('physical_class')=='land' and b.get('code') in range(17,23)}
    if len(ids)!=6 or set(ids)!=land_entities:raise ValueError('closed-water priority must cover six continents')
    return policies[0],pairs,tol


def validate_spans(by_row,width,height):
    components=defaultdict(list)
    for y,spans in sorted(by_row.items()):
        if type(y) is not int or not 0<=y<height:raise ValueError('component row out of bounds')
        prev=0
        for a,b,root in spans:
            if any(type(v) is not int for v in (a,b,root)) or not (0<=a<b<=width) or a<prev:
                raise ValueError('invalid or overlapping component span')
            components[root].append((y,a,b));prev=b
    return components


def adjacency(by_row,physical,prefill,width,height,pairs):
    """Count boundary codes and unknown external-zero edges independently."""
    components=validate_spans(by_row,width,height);results={r:{'codes':Counter(),'unknown_zero_edges':0,'crop_edge':False} for r in components}
    water_to_entity={w:e for e,_,w in pairs};land_to_entity={l:e for e,l,_ in pairs}
    arrays={}
    row_index={y:(np.asarray([v[0] for v in spans],dtype=np.int64),
                  np.asarray([v[1] for v in spans],dtype=np.int64),
                  np.asarray([v[2] for v in spans],dtype=np.int64)) for y,spans in by_row.items()}
    def row(y):
        if y not in arrays:
            p=shore.crop(*physical,y,0,width,width);q=shore.crop(*prefill,y,0,width,width)
            if np.any(~np.isin(p,[1,17])) or np.any((p==17)&~np.isin(q,list(land_to_entity))) or np.any((p==1)&~np.isin(q,[0,*water_to_entity])):
                raise ValueError(f'invalid physical/prefill relation at row {y}')
            arrays[y]=(p,q)
        return arrays[y]
    def owners(y,x):
        data=row_index.get(y)
        if data is None:return np.full(len(x),-1,dtype=np.int64)
        starts,ends,ids=data
        ix=np.searchsorted(starts,x,side='right')-1;found=(ix>=0)&(x<ends[np.maximum(ix,0)])
        return np.where(found,ids[np.maximum(ix,0)],-1)
    for y,spans in sorted(by_row.items()):
        arrays.clear();p,q=row(y)
        for a,b,root in spans:
            if np.any(p[a:b]!=1) or np.any(q[a:b]!=0):raise ValueError('component does not consist solely of residual physical water')
            if y==0 or y==height-1:results[root]['crop_edge']=True
            xs=np.arange(a,b,dtype=np.int64)
            for ny,nx in ((y,(xs-1)%width),(y,(xs+1)%width),(y-1,xs),(y+1,xs)):
                if ny<0 or ny>=height:continue
                own=owners(ny,nx);external=own!=root
                if not np.any(external):continue
                v=row(ny)[1][nx[external]]
                results[root]['unknown_zero_edges']+=int(np.count_nonzero(v==0))
                for code,n in zip(*np.unique(v[v!=0],return_counts=True)):
                    code=int(code);entity=water_to_entity.get(code,land_to_entity.get(code))
                    if entity is None:raise ValueError('boundary contains unsupported code')
                    results[root]['codes'][entity]+=int(n)
    return components,results


def component_method(summary,cut_edges):
    if type(cut_edges) is not int or cut_edges<0:raise ValueError('invalid source cut count')
    if cut_edges:return 'pending-source-cut-contact'
    if summary['crop_edge']:return 'pending-grid-crop-edge'
    if summary['unknown_zero_edges']:return 'pending-unknown-zero-boundary'
    count=len(summary['codes'])
    return 'pending-no-boundary-continent' if count==0 else ('direct-single-boundary-continent' if count==1 else 'nearest-participant-shore')


def cut_contacts(by_row,records,width,height):
    """Conservatively count every source cut incident to an unseeded cell.

    This includes internal cuts whose two sides reconnect into the same root;
    the upstream partition summary omits those. No full-grid expansion is used.
    """
    from bisect import bisect_right
    indexed={y:([a for a,_,_ in spans],spans) for y,spans in by_row.items()}
    def owner(y,x):
        data=indexed.get(y)
        if data is None:return None
        starts,spans=data;i=bisect_right(starts,x)-1
        return spans[i][2] if i>=0 and x<spans[i][1] else None
    counts=Counter();prev=None
    for record in records:
        if not isinstance(record,tuple) or len(record)!=3 or any(type(v) is not int for v in record):raise ValueError('invalid cut edge')
        kind,y,x=record
        if prev is not None and record<=prev:raise ValueError('cut edges must be unique and sorted')
        prev=record
        if kind==0 and 0<=y<height and 0<=x<width-1:endpoints=((y,x),(y,x+1))
        elif kind==1 and 0<=y<height-1 and 0<=x<width:endpoints=((y,x),(y+1,x))
        elif kind==2 and 0<=y<height and x==0:endpoints=((y,width-1),(y,0))
        else:raise ValueError('cut edge outside grid')
        for root in {owner(*point) for point in endpoints}-{None}:counts[root]+=1
    return counts
