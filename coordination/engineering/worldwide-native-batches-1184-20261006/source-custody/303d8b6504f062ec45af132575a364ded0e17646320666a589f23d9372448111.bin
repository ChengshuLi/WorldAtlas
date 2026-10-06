"""Focused regional orchestration views over complete coordinated source families."""
from collections import defaultdict
from evidence.immutable import canonical_json, sha256

def operational_batches(families):
    ids=[f['id'] for f in families]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate fine source family')
    groups={}
    for family in families:
        grouping=family['grouping']
        key={'complete_subcontinent_set':grouping['subcontinents'],
             'responsible_role':family['responsible_role'],
             'observed_scope_bucket':grouping['observed_scope_bucket']}
        identity='gap-operational-batch:'+sha256(canonical_json(key))[:24]
        batch=groups.setdefault(identity,{'id':identity,'grouping':key,'fine_family_ids':[],
            'component_count':0,'source_family_count':0,'existing_related_issues':set(),
            'known_extents':[],'unknown_extent_components':0,'best_rank':{}})
        batch['fine_family_ids'].append(family['id'])
        batch['component_count']+=family['component_count'];batch['source_family_count']+=1
        batch['existing_related_issues'].update(family['existing_related_issues'])
        if family['aggregate_extent_lonlat'] is not None:batch['known_extents'].append(family['aggregate_extent_lonlat'])
        batch['unknown_extent_components']+=len(family['original_member_extent_references']['missing_extent_component_ids'])
        for name,rank in family['best_rank'].items():batch['best_rank'][name]=min(rank,batch['best_rank'].get(name,rank))
    result=[]
    for identity in sorted(groups):
        batch=groups[identity];batch['fine_family_ids'].sort()
        batch['fine_family_ids_sha256']=sha256(canonical_json(batch['fine_family_ids']))
        batch['existing_related_issues']=sorted(batch['existing_related_issues'])
        extents=batch.pop('known_extents')
        batch['aggregate_extent_lonlat']=None if not extents else [min(e[0]for e in extents),min(e[1]for e in extents),max(e[2]for e in extents),max(e[3]for e in extents)]
        batch['membership_view']='Union every referenced complete fine-family component roster; never split a shared-source/cross-subcontinent family.'
        batch['next_action']='Review related open and archived issues, select a bounded complete source family closure, check current canonical claim and source contract, then dispatch source research or engineering reproduction.'
        batch['eligibility']='Prioritized orchestration backlog; live canonical claim eligibility is not established.'
        result.append(batch)
    verify_operational_batches(result,families)
    return result

def verify_operational_batches(batches,families):
    by_id={f['id']:f for f in families};seen=[];components=[]
    for batch in batches:
        ids=batch['fine_family_ids']
        if ids!=sorted(set(ids)) or not set(ids)<=set(by_id):raise ValueError('Missing or duplicate referenced fine family')
        if sha256(canonical_json(ids))!=batch['fine_family_ids_sha256']:raise ValueError('Operational fine roster binding differs')
        if len(ids)!=batch['source_family_count']:raise ValueError('Operational source-family count differs')
        if sum(by_id[i]['component_count']for i in ids)!=batch['component_count']:raise ValueError('Operational component count differs')
        for identity in ids:
            family=by_id[identity]
            expected={'complete_subcontinent_set':family['grouping']['subcontinents'],
                      'responsible_role':family['responsible_role'],
                      'observed_scope_bucket':family['grouping']['observed_scope_bucket']}
            if expected!=batch['grouping']:raise ValueError('Coordinated family redirected or split across regional role/bucket')
            components.extend(family['component_ids'])
        seen.extend(ids)
    original=[c for f in families for c in f['component_ids']]
    if len(seen)!=len(set(seen)) or set(seen)!=set(by_id):raise ValueError('Incomplete or repeated operational family membership')
    if len(components)!=len(set(components)) or set(components)!=set(original) or len(original)!=len(set(original)):
        raise ValueError('Operational component membership incomplete or not disjoint')

def dispatch_candidates(batches,limit=20):
    if type(limit)is not int or not 1<=limit<=32:raise ValueError('Bounded operational dispatch limit required')
    return [{'operational_batch_id':b['id'],'component_count':b['component_count'],
        'source_family_count':b['source_family_count'],'grouping':b['grouping'],
        'best_rank':b['best_rank'],'existing_related_issues':b['existing_related_issues'],
        'eligibility':b['eligibility']}for b in sorted(batches,key=lambda b:(b['best_rank']['measured_impact'],b['id']))[:limit]]
