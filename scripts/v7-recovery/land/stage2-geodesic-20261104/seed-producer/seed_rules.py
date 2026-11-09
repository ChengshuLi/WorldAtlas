"""Resolve selected simple mainland partition rules to current ephemeral roots."""

def unique(items,key):
 if not isinstance(items,list):raise ValueError('invalid decision list')
 out={}
 for x in items:
  if not isinstance(x,dict) or key not in x or x[key] in out:raise ValueError('duplicate or invalid decision ID')
  out[x[key]]=x
 return out

def compile_rules(snapshot,resolution,snapshot_sha256,selected_region_ids):
 if not isinstance(snapshot,dict) or snapshot.get('source')!='neon-export' or snapshot.get('schema')!='worldatlas-geography-decision-draft-evidence-v1':raise ValueError('selected Neon export required')
 rev=snapshot.get('decision_revision',{});entity_rev=snapshot.get('entity_revision',{})
 if rev.get('status')!='draft' or entity_rev.get('status')!='draft' or rev.get('entity_revision')!=entity_rev.get('id'):raise ValueError('invalid revision linkage')
 lp=snapshot.get('land_baseline_policy')
 if not isinstance(lp,dict) or lp.get('execution_status')!='selected_for_research' or lp.get('decision_revision')!=rev.get('id') or lp.get('island_overrides')!='none':raise ValueError('simple baseline policy required')
 rule_ids=lp.get('mainland_rule_ids');region_ids=lp.get('region_ids')
 if not isinstance(rule_ids,list) or not rule_ids or len(rule_ids)!=len(set(rule_ids)) or not isinstance(region_ids,list) or len(region_ids)!=len(set(region_ids)) or set(region_ids)!=set(selected_region_ids):raise ValueError('invalid selected rule/region list')
 if not isinstance(resolution,dict) or resolution.get('schema')!='mainland-witness-resolution-v1' or resolution.get('status')!='selected-research-identity-claims-not-mainland-proof' or resolution.get('snapshot_sha256')!=snapshot_sha256 or resolution.get('decision_revision')!=rev.get('id') or resolution.get('entity_revision')!=entity_rev.get('id'):raise ValueError('witness resolution mismatch')
 groups=unique(resolution.get('groups'),'group_id');rules=unique(snapshot.get('mainland_component_rules'),'rule_id');entities=unique(snapshot.get('entities'),'id')
 bindings={}
 for b in snapshot.get('category_bindings',[]):
  if b.get('physical_class')!='land':continue
  eid=b.get('entity_id');code=b.get('code');entity=entities.get(eid)
  if eid in bindings or type(code) is not int or not 17<=code<=22 or not entity or entity.get('level')!='continent':raise ValueError('invalid continent category binding')
  bindings[eid]=code
 if len(bindings)!=6 or len(set(bindings.values()))!=6:raise ValueError('incomplete continent categories')
 if any(x not in rules for x in rule_ids):raise ValueError('selected mainland rule missing')
 out=[];roots=set();used_regions=set();used_groups=set()
 for rid in rule_ids:
  r=rules[rid];required={'rule_id','decision_revision','execution_status','group_id','region_id','inside_entity_id','outside_entity_id'}
  if set(r)!=required or r['decision_revision']!=rev['id'] or r['execution_status']!='selected_for_research':raise ValueError('invalid selected mainland rule')
  group=groups.get(r['group_id']);root=group.get('component_id_current_generation_only') if group else None
  if not group or group.get('role')!='mainland' or type(root) is not int or root<0 or root>=0xffffffff or root in roots or r['group_id'] in used_groups:raise ValueError('invalid or duplicate mainland group/root')
  inside,outside=r['inside_entity_id'],r['outside_entity_id'];region=r['region_id']
  if inside not in bindings or outside not in bindings or set(group.get('target_entity_ids',[]))!={inside,outside}:raise ValueError('mainland group/continent target mismatch')
  if region is None:
   if inside!=outside:raise ValueError('whole-component rule has conflicting categories')
  else:
   if region not in set(region_ids) or inside==outside:raise ValueError('unselected or unnecessary region in mainland rule')
   used_regions.add(region)
  roots.add(root);used_groups.add(r['group_id']);out.append({'rule_id':rid,'group_id':r['group_id'],'component_id_current_generation_only':root,'region_id':region,'inside_entity_id':inside,'outside_entity_id':outside,'inside_code':bindings[inside],'outside_code':bindings[outside]})
 if used_regions!=set(region_ids):raise ValueError('unused selected region')
 selected_mainlands={gid for gid,g in groups.items() if g.get('role')=='mainland'}
 if used_groups!=selected_mainlands:raise ValueError('unconsumed selected mainland group')
 if {v for r in out for v in (r['inside_code'],r['outside_code'])}!=set(bindings.values()):raise ValueError('incomplete mainland category coverage')
 return out
