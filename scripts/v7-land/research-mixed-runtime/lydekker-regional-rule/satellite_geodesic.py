"""Whole-island satellite proposals using exact WGS84 center distances.

This module does not discover source identities. The caller authenticates a
complete component generation and a source-backed set of named main islands,
resolves each source witness to its physical root, and loads the project's
pinned stage-2 `run_pair` implementation. Proximity is an operational convention,
not proof of geographic group membership.
"""
import math
from bisect import bisect_left, bisect_right
from regional_rule import ASIA, OCEANIA, _require

# Lower bound on WGS84 distance per radian of latitude (metres).
MIN_MERIDIONAL_RADIUS = 6335439.0
BOUND_GUARD_M = 1000.0


def run_lower_bound(y,a,b,yy,c,d,width,north):
    """Spherical lower bound for two discrete center runs, including wrap."""
    step=360/width
    gap=min(max(0, max(c+shift-(b-1), a-(d-1+shift))) for shift in (-width,0,width))
    p1=math.radians(north-(y+0.5)*step);p2=math.radians(north-(yy+0.5)*step)
    dl=math.radians(gap*step);dp=p2-p1
    hav=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*math.asin(math.sqrt(min(1.0,max(0.0,hav))))*MIN_MERIDIONAL_RADIUS


def apply_satellites(result, components, root_runs, anchors, exact_run_pair, *,
                     width, north, max_satellite_cells, max_gap_m, candidate_roots, tie_m=1e-5):
    """Apply main-island convention after explicit replay and initial line side.

    root_runs must include *all* components larger than the candidate that
    could lie within the search distance, including unanchored competing land; their complete global
    counts must match components. The caller proves this spatial completeness.
    anchors maps generation-only roots to {code, source_id, source_feature_id},
    each resolved from a source-backed named island and already selected or
    unambiguously line-classified. Distances are exact minimum WGS84 center to
    center over complete runs. If equally near land has different or unknown
    target, remove the line proposal and report ambiguity. Existing selected
    affiliations and protected mainland always win. Split or touching components
    remain in review, but an otherwise complete component beyond an endpoint can
    inherit an independently established source anchor without extending the line.
    The size and gap parameters are operational policy,
    not proof of source membership. No chaining through inferred satellites.
    """
    _require(isinstance(result, dict) and isinstance(components,dict) and
             isinstance(root_runs,dict) and isinstance(anchors,dict) and
             callable(exact_run_pair), 'invalid satellite inputs')
    _require(type(width) is int and width>=2 and type(north) in (int,float) and math.isfinite(north) and -90<=north<=90 and
             type(max_satellite_cells) is int and max_satellite_cells>0 and
             type(max_gap_m) in (int,float) and math.isfinite(max_gap_m) and max_gap_m>0 and
             type(tie_m) in (int,float) and math.isfinite(tie_m) and tie_m>=0, 'invalid satellite policy')
    for root,runs in root_runs.items():
        _require(root in components and isinstance(runs,list) and runs, 'missing component runs')
        _require(all(isinstance(run,(tuple,list)) and len(run)==3 and all(type(v) is int for v in run) and
                     0<=run[0] and -90<=north-(run[0]+0.5)*360/width<=90 and 0<=run[1]<run[2]<=width for run in runs), 'invalid run')
        _require(sum(b-a for _,a,b in runs)==components[root]['total'] and
                 len(set(map(tuple,runs)))==len(runs) and
                 all((a[0],a[2]) <= (b[0],b[1]) for a,b in zip(runs,runs[1:])), 'incomplete or overlapping runs')
    root_runs={root:[tuple(run) for run in runs] for root,runs in root_runs.items()}
    for root,a in anchors.items():
        _require(root in root_runs and isinstance(a,dict) and a.get('code') in (ASIA,OCEANIA) and
                 isinstance(a.get('source_id'),str) and a['source_id'] and
                 isinstance(a.get('source_feature_id'),str) and a['source_feature_id'] and
                 isinstance(a.get('source_version'),str) and a['source_version'] and
                 isinstance(a.get('source_sha256'),str) and len(a['source_sha256'])==64 and
                 all(ch in '0123456789abcdef' for ch in a['source_sha256']) and
                 isinstance(a.get('main_island_evidence'),str) and a['main_island_evidence'], 'invalid source-backed main island')
        proposal=result['proposals'].get(root)
        _require(proposal is not None and proposal['code']==a['code'], 'anchor target not established')
    potential_parents=set(root_runs)
    out={**result,'proposals':{k:dict(v) for k,v in result['proposals'].items()},
         'review':dict(result['review']),'satellites':{},'nearest_unanchored':{}}
    _require(isinstance(candidate_roots,(set,frozenset)) and candidate_roots.issubset(root_runs), 'candidate runs missing')
    step=360/width
    rows={r:(v[0][0],v[-1][0]) for r,v in root_runs.items()}
    # Monotonic rows permit exact latitude-only pruning before expensive run
    # comparisons; one extra row absorbs floating-point rounding.
    max_dy=math.ceil((max_gap_m+tie_m+BOUND_GUARD_M)/MIN_MERIDIONAL_RADIUS*180/math.pi/step)+1
    for root in candidate_roots:
        runs=root_runs[root]
        if root in anchors or components[root]['total']>max_satellite_cells:
            continue
        proposal=out['proposals'].get(root)
        if proposal and proposal['basis']=='selected_affiliation':
            continue
        if out['review'].get(root) in ('protected_mainland','existing_other_continent','crosses_or_touches_line','source_group_pending_review'):
            continue
        # Partial-window components are not regional satellite decisions.
        if components[root]['in_scope'] != components[root]['total']:
            continue
        distances=[]
        for parent in potential_parents:
            if parent==root or components[parent]['total']<=components[root]['total']:
                continue
            low,high=rows[root]; plow,phigh=rows[parent]
            row_gap=max(0,plow-high,low-phigh)
            if row_gap*step*math.pi/180*MIN_MERIDIONAL_RADIUS>max_gap_m+tie_m+BOUND_GUARD_M:
                continue
            best=math.inf
            for y,a,b in runs:
                parent_runs=root_runs[parent]
                lo=bisect_left(parent_runs,(max(0,y-max_dy),0,0))
                hi=bisect_right(parent_runs,(y+max_dy,width,width))
                for yy,c,d in parent_runs[lo:hi]:
                    lower=abs(y-yy)*step*math.pi/180*MIN_MERIDIONAL_RADIUS
                    if lower>min(max_gap_m,best)+tie_m+BOUND_GUARD_M:
                        continue
                    if run_lower_bound(y,a,b,yy,c,d,width,north)>min(max_gap_m,best)+tie_m+BOUND_GUARD_M:
                        continue
                    distance,_=exact_run_pair(y,a,b,yy,c,d,width,north=north,
                                              incumbent=min(max_gap_m,best)+tie_m,tol=tie_m)
                    if distance is not None:
                        _require(math.isfinite(distance) and distance>=0,'invalid geodesic result')
                        best=min(best,distance)
            if best<=max_gap_m+tie_m:
                distances.append((best,parent))
        if not distances:
            continue
        distances.sort(); minimum=distances[0][0]
        if minimum>max_gap_m:
            continue
        nearest=[p for distance,p in distances if distance<=minimum+tie_m]
        targets={anchors[p]['code'] if p in anchors else
                 result['proposals'].get(p,{}).get('code') for p in nearest}
        if any(p not in anchors for p in nearest):
            # Mere proximity to unnamed or unanchored land is not evidence that
            # the approved line-side target is wrong. Preserve it unless a
            # nearest independently classified competitor has another target.
            out['nearest_unanchored'][root]={'roots_current_generation_only':nearest,'distance_m':minimum}
            known=targets-{None}
            if proposal and proposal['basis']=='whole_component_line_side':
                if not known or known=={proposal['code']}:
                    continue
                out['proposals'].pop(root,None)
                out['review'][root]='conflicting_nearest_land_targets'
            # A component beyond the endpoints has no line-side target, and
            # remains in its existing review state without extrapolation.
            continue
        if len(targets)>1:
            out['proposals'].pop(root,None)
            out['review'][root]='conflicting_nearest_land_targets'
            continue
        parent=min(nearest)
        code=next(iter(targets))
        out['proposals'][root]={'code':code,'basis':'source_anchored_nearest_main_island'}
        out['review'].pop(root,None)
        out['satellites'][root]={'parent_root_current_generation_only':parent,
                                 'distance_m':minimum,'source_id':anchors[parent]['source_id'],
                                 'source_feature_id':anchors[parent]['source_feature_id'],
                                 'source_version':anchors[parent]['source_version'],
                                 'source_sha256':anchors[parent]['source_sha256'],
                                 'main_island_evidence':anchors[parent]['main_island_evidence']}
    return out
