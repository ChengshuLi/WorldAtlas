"""Research-only plan to omit one cut component from polygon seed generation.

Only in-memory views are filtered. The original snapshot pin is preserved and
no derived view is represented as a new Neon export. No seed or map is built.
"""
import copy
from selection import selected_cut, need


def plan(snapshot, witness, snapshot_sha, component_hashes, grid, rule_id, boundary_id,
         compile_rules, boundary_records, selected_regions):
    need(all(callable(x) for x in (compile_rules,boundary_records,selected_regions)), 'trusted adapters required')
    selected=selected_cut(snapshot,witness,snapshot_sha,component_hashes,rule_id,boundary_id,grid)
    policy=snapshot.get('land_baseline_policy',{});region_ids=policy.get('region_ids')
    need(isinstance(region_ids,list) and len(region_ids)==len(set(region_ids)),'invalid selected region IDs')
    full_rules=compile_rules(snapshot,witness,snapshot_sha,region_ids)
    omitted=[r for r in full_rules if r.get('rule_id')==rule_id]
    need(len(omitted)==1,'omitted selected rule must be unique');target=omitted[0]
    need(target.get('region_id') in region_ids and target.get('component_id_current_generation_only')==selected['component']
         and target.get('inside_code')==selected['inside_code'] and target.get('outside_code')==selected['outside_code'],
         'direct split differs from selected rule')
    remaining=[r for r in full_rules if r.get('rule_id')!=rule_id]
    need(remaining and all(r.get('region_id')!=target['region_id'] for r in remaining),'shared or missing remaining rule')
    kept_regions=[r for r in snapshot.get('seed_regions',[]) if r.get('region_id') in region_ids and r.get('region_id')!=target['region_id']]
    kept_ids=[r['region_id'] for r in kept_regions]
    need(len(kept_ids)==len(set(kept_ids)) and set(kept_ids)==set(region_ids)-{target['region_id']},'missing retained region')
    boundary_ids=set();route_ids=set()
    for region in kept_regions:
        for segment in region.get('segments',[]):
            need(isinstance(segment,dict) and segment.get('kind') in ('boundary','route') and isinstance(segment.get('id'),str),'invalid retained segment')
            (boundary_ids if segment['kind']=='boundary' else route_ids).add(segment['id'])
    need(boundary_ids<=set(policy.get('boundary_ids',[])) and route_ids<=set(policy.get('route_ids',[])),'retained geometry not selected')
    view=copy.deepcopy(snapshot);view['seed_regions']=copy.deepcopy(kept_regions)
    view['mainland_boundaries']=[b for b in view.get('mainland_boundaries',[]) if b.get('boundary_id') in boundary_ids]
    view['land_baseline_policy']['region_ids']=kept_ids
    view['land_baseline_policy']['boundary_ids']=[x for x in policy['boundary_ids'] if x in boundary_ids]
    view['land_baseline_policy']['route_ids']=[x for x in policy['route_ids'] if x in route_ids]
    revision,entity,boundaries,sources=boundary_records(view)
    regions,records=selected_regions(view,revision,boundaries,sources)
    need({r.get('region_id') for r in regions}==set(kept_ids),'retained adapter region mismatch')
    need({r.get('region_id') for r in remaining if r.get('region_id') is not None}==set(kept_ids),'retained rule/region mismatch')
    return {'status':'research-plan-not-a-build','snapshot_sha256':snapshot_sha,'decision_revision':revision,'entity_revision':entity,
            'omitted_rule':target,'remaining_rules':remaining,'remaining_regions':regions,'records':records,'sources':sources,
            'limitations':['This is only a plan; it does not create a partial seed or authenticate the export.',
                           'The direct split and full downstream output require independent verification before any switch.']}
