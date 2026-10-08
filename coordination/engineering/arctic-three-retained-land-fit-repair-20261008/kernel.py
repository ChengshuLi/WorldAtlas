"""Exact #1520 three-component union; source approval is an external prerequisite."""
from shapely.geometry import mapping

COMPONENT_TARGETS = {
 'physical-component:12c9ec9813490ce8602fb26ee2e54225b99c28bbd29794a7f8ac9ee60f109e8a': 'atlas:physical:CAN-15:NWT',
 'physical-component:add031b7195352292c8529323c8b99dd75002af629116b229e84be981893ca8d': 'atlas:physical:CAN-25:NUN',
 'physical-component:17bb5b7f043b0fb2b447b8ccef216e530fed4595da1aec0feb1dea235bed0dbd': 'atlas:physical:CAN-25:NUN',
}

def exact_additions(old, candidates, *, expected_components=tuple(COMPONENT_TARGETS)):
    expected = set(expected_components)
    if not expected or not expected <= set(COMPONENT_TARGETS) or set(candidates) != expected or set(old) != {COMPONENT_TARGETS[c] for c in expected}:
        raise ValueError('Require exactly the declared approved components and their targets')
    for geometry in [*old.values(), *candidates.values()]:
        if geometry.is_empty or not geometry.is_valid or geometry.geom_type not in ('Polygon', 'MultiPolygon'):
            raise ValueError('Complete valid polygon operands required')
    after, proofs = {}, []
    for target in sorted(old):
        original = old[target]
        current = original
        gaps = [candidates[c] for c in candidates if COMPONENT_TARGETS[c] == target]
        for gap in gaps:
            if current.intersection(gap).area != 0:
                raise ValueError('Positive preexisting or between-candidate ownership')
            current = current.union(gap)
        whole_gain = gaps[0]
        for gap in gaps[1:]:
            whole_gain = whole_gain.union(gap)
        gain, loss = current.difference(original), original.difference(current)
        if not current.is_valid or not current.covers(original) or not current.covers(whole_gain) or not loss.is_empty or not gain.equals(whole_gain):
            raise ValueError('Exact combined no-loss whole-gain construction failed')
        after[target] = current
        proofs.append({'target_id': target, 'component_ids': [c for c in candidates if COMPONENT_TARGETS[c] == target],
                       'before': mapping(original), 'after': mapping(current), 'gain': mapping(gain), 'loss': mapping(loss),
                       'gain_equals_complete_candidates': True, 'loss_empty': True})
    return after, proofs

def neighbor_relation(identity, neighbor, old, new):
    if not neighbor.is_valid:
        raise ValueError('Invalid prepared neighbor')
    if not old.intersects(neighbor) and not new.intersects(neighbor):
        return None
    before, after = old.intersection(neighbor), new.intersection(neighbor)
    added = after.difference(before)
    if added.area > 0:
        raise ValueError('New positive-area active-neighbor intersection: ' + identity)
    return {'id': identity, 'before': mapping(before), 'after': mapping(after), 'added': mapping(added), 'added_area': added.area}
