"""Propose whole-component endpoint groups within sourced geographic extents.

This is an inferred geographic convention, not proof that each component is a
member of a named archipelago. The caller authenticates the source and scans
complete physical components. Explicit selected and pending claims always win.
"""
from regional_rule import _require

def apply_groups(result, windows):
    _require(isinstance(result,dict) and isinstance(windows,list), 'invalid group input')
    out={**result,'proposals':{r:dict(v) for r,v in result['proposals'].items()},
         'review':dict(result['review']),
         'regional_group_proposals':{int(r):list(v) for r,v in result.get('regional_group_proposals',{}).items()},
         'regional_group_diagnostics':dict(result.get('regional_group_diagnostics',{})),
         'selected_group_conflicts':{int(r):list(v) for r,v in result.get('selected_group_conflicts',{}).items()},
         'group_anchor_conflicts':{int(r):dict(v) for r,v in result.get('group_anchor_conflicts',{}).items()}}
    candidates={}
    for window in windows:
        _require(isinstance(window,dict) and isinstance(window.get('group_id'),str) and window['group_id'] and
                 type(window.get('code')) is int and window['code'] in (18,22) and
                 isinstance(window.get('components'),dict) and isinstance(window.get('source'),dict), 'invalid group window')
        counts={'whole_roots':0,'partial_roots':0,'selected_preserved':0,'eligible_held_roots':0}
        for r,c in window['components'].items():
            if c['total']!=c['in_scope']:
                counts['partial_roots']+=1;continue
            counts['whole_roots']+=1
            p=out['proposals'].get(r)
            if p and p['basis']=='selected_affiliation':
                counts['selected_preserved']+=1
                if p['code']!=window['code']:
                    out['selected_group_conflicts'].setdefault(r,[]).append(
                        {'group_id':window['group_id'],'target_code':window['code'],'source':window['source'],'selected_code':p['code']})
                continue
            evidence={'group_id':window['group_id'],'target_code':window['code'],'source':window['source']}
            if p and p['basis']=='inferred_source_extent_group_convention':
                prior=out['regional_group_proposals'].setdefault(r,[])
                if evidence not in prior: prior.append(evidence)
                if p['code']!=window['code']:
                    out['proposals'].pop(r,None)
                    out['review'][r]='conflicting_regional_group_conventions'
                continue
            if out['review'].get(r) in ('conflicting_regional_group_conventions','conflicting_group_and_anchor'):
                prior=out['regional_group_proposals'].setdefault(r,[])
                if evidence not in prior:prior.append(evidence)
                continue
            # Source groups precede a line default or inferred satellite.
            # Pending, protected, conflict, crossing and partial holds stay held.
            if p and p['basis'] in ('whole_component_line_side','source_anchored_nearest_main_island'):
                candidates.setdefault(r,[]).append(window);continue
            if out['review'].get(r)!='outside_line_latitude':continue
            counts['eligible_held_roots']+=1
            candidates.setdefault(r,[]).append(window)
        out['regional_group_diagnostics'][window['group_id']]=counts
    for r,groups in candidates.items():
        if len({g['code'] for g in groups})!=1:
            out['proposals'].pop(r,None)
            out['regional_group_proposals'][r]=[{'group_id':g['group_id'],'target_code':g['code'],'source':g['source']} for g in groups]
            out['review'][r]='conflicting_regional_group_conventions';continue
        prior=out['proposals'].get(r)
        out['regional_group_proposals'][r]=[{'group_id':g['group_id'],'target_code':g['code'],'source':g['source']} for g in groups]
        if prior and prior['basis']=='source_anchored_nearest_main_island' and prior['code']!=groups[0]['code']:
            out['proposals'].pop(r,None)
            out['review'][r]='conflicting_group_and_anchor'
            out['group_anchor_conflicts'][r]={'group_target_code':groups[0]['code'],
                'prior_satellite_proposal':dict(prior),
                'prior_satellite_evidence':result.get('satellites',{}).get(r,result.get('satellites',{}).get(str(r)))}
            continue
        out['proposals'][r]={'code':groups[0]['code'],'basis':'inferred_source_extent_group_convention'}
        out['review'].pop(r,None)
    return out
