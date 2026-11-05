"""Adapter for the existing mixed source-resolver replay, not a build driver.

Use only inside a caller that has authenticated the snapshot, pinned component
manifest and input streams, rerun every selected source resolver, verified their
reports, and authenticated the mixed_claims module. Its combine function checks
selected affiliation identity, target codes, conflicts and mainland exclusion.
"""
from regional_rule import ASIA, OCEANIA, _require, resolve


def resolve_with_mixed_replay(components, compiled, snapshot, reports, mainland_roots, mixed_claims, pending_claims=()):
    """Replay all selected groups first, then conservatively inspect a region.

    Unclaimed whole components get side-of-line proposals. A source-anchored
    geodesic satellite pass should subsequently resolve competing parent islands.
    Source resolution is delegated to the existing mixed runtime; caller must
    execute and authenticate it.
    """
    _require(hasattr(mixed_claims, 'combine') and callable(mixed_claims.combine), 'missing mixed claims resolver')
    protected=set(mainland_roots)
    replay=mixed_claims.combine(compiled, snapshot, reports, protected)
    _require(isinstance(replay, dict), 'invalid replay')
    selected, other = {}, {}
    for root, claims in replay.items():
        _require(isinstance(claims, list) and claims, 'invalid replay claim')
        codes={claim['code'] for claim in claims}
        _require(len(codes)==1, 'conflicting replay targets')
        if root not in components:
            continue
        code=next(iter(codes))
        if code in (ASIA,OCEANIA):
            selected[root]=[code]
        else:
            other[root]=claims
    pending={}
    for claim in pending_claims:
        _require(isinstance(claim,dict) and type(claim.get('component_id')) is int and
                 all(isinstance(claim.get(k),str) and claim[k] for k in
                     ('source_id','source_version','source_feature_id','source_sha256','review_reason')) and
                 len(claim['source_sha256'])==64 and all(c in '0123456789abcdef' for c in claim['source_sha256']),
                 'invalid pending source claim')
        pending.setdefault(claim['component_id'],[]).append(claim)
    candidates={root: summary for root,summary in components.items() if root not in other}
    result=resolve(candidates, selected, protected, set(pending))
    for root in other:
        result['review'][root]=('source_group_pending_review' if root in pending
                                else 'existing_other_continent')
    result['replayed_claims']={root:claims for root,claims in replay.items() if root in components}
    result['pending_source_claims']={root:claims for root,claims in pending.items() if root in components}
    return result
