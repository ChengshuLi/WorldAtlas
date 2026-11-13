"""Apply source-backed group choices before direct satellite assignment."""


def apply_groups(result, windows):
    """Keep explicit affiliations; combine agreeing complete-component groups.

    A geographic group can replace the line-side default or resolve a component
    beyond the line's endpoints. Partial, crossing and protected components stay
    unresolved. Opposing group choices stay visible rather than depending on order.
    """
    out = {**result, 'proposals': {root: dict(value) for root, value in result['proposals'].items()},
           'review': dict(result['review']), 'regional_group_proposals': {},
           'regional_group_diagnostics': {}, 'selected_group_conflicts': {}}
    candidates = {}
    for window in windows:
        counts = dict(whole_roots=0, partial_roots=0, selected_preserved=0, eligible_held_roots=0)
        for root, component in window['components'].items():
            if component['total'] != component['in_scope']:
                counts['partial_roots'] += 1
                continue
            counts['whole_roots'] += 1
            proposal = result['proposals'].get(root)
            evidence = dict(group_id=window['group_id'], target_code=window['code'], source=window['source'])
            if proposal and proposal['basis'] == 'selected_affiliation':
                counts['selected_preserved'] += 1
                if proposal['code'] != window['code']:
                    out['selected_group_conflicts'].setdefault(root, []).append(
                        dict(evidence, selected_code=proposal['code']))
                continue
            if proposal and proposal['basis'] == 'whole_component_line_side':
                candidates.setdefault(root, []).append(evidence)
            elif result['review'].get(root) == 'outside_line_latitude':
                counts['eligible_held_roots'] += 1
                candidates.setdefault(root, []).append(evidence)
        out['regional_group_diagnostics'][window['group_id']] = counts
    for root, evidence in candidates.items():
        out['regional_group_proposals'][root] = evidence
        codes = {item['target_code'] for item in evidence}
        if len(codes) != 1:
            out['proposals'].pop(root, None)
            out['review'][root] = 'conflicting_regional_group_conventions'
        else:
            out['proposals'][root] = dict(code=next(iter(codes)), basis='inferred_source_extent_group_convention')
            out['review'].pop(root, None)
    return out
