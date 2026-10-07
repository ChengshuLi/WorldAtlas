"""Prepared #1295 two-target kernel; not executed scientific delivery.

The future job must authenticate the complete admitted input closure, source roles,
whole four-family roster and current prepared-domain gate before calling this.
No historical source construction, affiliation or water conclusion is made here.
"""
from shapely.geometry import shape, mapping

TARGETS = {
    'atlas:physical:CAN-103:QUE': 'physical-component:bb4a3e58a98cdc2a589c2e0d8bc2e8172e3147d7bc68fe755a0f1fc2df713121',
    'atlas:physical:CAN-114:NFL': 'physical-component:1d458ddaf986b7485036312676a27f99539ecb743c8e093805cf4d4f49c55ed8',
}

def exact_addition(subject_id, component_id, old, gap, native, retired_envelope):
    if TARGETS.get(subject_id) != component_id:
        raise ValueError('Outside exact authorized two-target component binding')
    for name, geometry in [('old',old),('gap',gap),('native',native),('retired_envelope',retired_envelope)]:
        if geometry.is_empty or not geometry.is_valid or geometry.geom_type not in ('Polygon','MultiPolygon'):
            raise ValueError('Invalid full polygon operand: '+name)
    if not native.covers(gap) or not retired_envelope.covers(gap):
        raise ValueError('Whole gain outside exact approved native/retired envelope')
    if old.intersection(gap).area != 0:
        raise ValueError('Existing positive old ownership inside proposed gain')
    new = old.union(gap)
    gain, loss = new.difference(old), old.difference(new)
    if not new.is_valid or not new.covers(old) or not new.covers(gap) or not gain.equals(gap) or not loss.is_empty:
        raise ValueError('Exact valid no-loss whole-gain construction failed')
    return new, {'old':mapping(old),'gap':mapping(gap),'new':mapping(new),
                 'native':mapping(native),'retired_envelope':mapping(retired_envelope),
                 'gain':mapping(gain),'loss':mapping(loss)}

def complete_neighbor_relations(subject_id, old, new, world):
    """Preserve every actual contact; reject any newly positive intersection."""
    seen=set(); relations=[]
    for identity, geometry in world:
        if identity in seen:
            raise ValueError('Duplicate complete-world identity')
        seen.add(identity)
        if identity==subject_id:
            if not geometry.equals(old):raise ValueError('Current full subject operand mismatch')
            continue
        if not geometry.is_valid:
            raise ValueError('Unvalidated complete-world prepared geometry: '+identity)
        if not old.intersects(geometry) and not new.intersects(geometry):continue
        before, after = old.intersection(geometry), new.intersection(geometry)
        added=after.difference(before)
        relations.append({'id':identity,'before':mapping(before),'after':mapping(after),
                          'added':mapping(added),'added_area':added.area})
        if added.area>0:raise ValueError('New positive neighbor/municipal overlap: '+identity)
    if subject_id not in seen or len(seen)!=49625:
        raise ValueError('Require complete actual49625-source world')
    return relations

def exact_two_feature_replacements(before, geometries):
    if set(geometries)!=set(TARGETS):raise ValueError('Exact two subject geometries required')
    seen=set();after=[]
    for feature in before:
        identity=feature['id']
        if identity in seen:raise ValueError('Duplicate current source identity')
        seen.add(identity)
        # All original properties and every non-target full object remain intact.
        after.append({**feature,'geometry':geometries[identity]} if identity in geometries else feature)
    if len(seen)!=49625 or not set(TARGETS)<=seen:
        raise ValueError('Incomplete current feature closure')
    return after
