"""Streaming physical/component/seed coverage check before WGS84 search."""
import numpy as np
from write_land_stream import _Rows,_full,_components,PAIR,TRIPLE

def validate(width,height,component_rows,component_runs,physical_rows,physical_runs,mainland_rows,mainland_runs,roots,seed_roots,required_codes=range(17,23),guard=lambda:None,seed_rules=None,expected_rule_population=None,expected_category_counts=None):
 roots=np.asarray(roots,dtype=np.uint32);seed_roots=set(map(int,seed_roots));seen=np.zeros(len(roots),dtype=bool);seeds_seen=set();codes=set();land=0;by_root={};category_counts={}
 if len(roots)==0 or np.any(roots[1:]<=roots[:-1]) or not seed_roots or any(int(x) in seed_roots for x in roots):raise ValueError('bad component root lists')
 # Every root is indexed once; no bounded cache or component sample is used.
 positions={int(root):i for i,root in enumerate(roots)}
 streams=[]
 try:
  for rp,sp,typ in ((component_rows,component_runs,TRIPLE),(physical_rows,physical_runs,PAIR),(mainland_rows,mainland_runs,PAIR)):streams.append(_Rows(rp,sp,height,typ))
  for y in range(height):
   if y%128==0:guard()
   its=[iter(_components(streams[0].next(),width)),iter(_full(streams[1].next(),width,{1,17},'physical')),iter(_full(streams[2].next(),width,{0,17,18,19,20,21,22},'mainland'))];cur=[next(i) for i in its];x=0
   while x<width:
    end=min(cur[0][1],cur[1][1],cur[2][1]);root,phys,seed=cur[0][2],cur[1][2],cur[2][2]
    if (root is not None)!=(phys==17):raise ValueError('physical/component mismatch at row '+str(y))
    if root is None:
     if seed:raise ValueError('seed outside physical land')
    elif root in seed_roots:
     if not seed:raise ValueError('seed root gap')
     seeds_seen.add(root);codes.add(seed);land+=end-x
     by_root.setdefault(int(root),{});by_root[int(root)][int(seed)]=by_root[int(root)].get(int(seed),0)+end-x;category_counts[int(seed)]=category_counts.get(int(seed),0)+end-x
    else:
     if seed:raise ValueError('seed on nonseed root')
     i=positions.get(root)
     if i is None:raise ValueError('unknown nonseed root')
     seen[i]=True;land+=end-x
    x=end
    for i in range(3):
     if cur[i][1]==x:cur[i]=next(its[i],None)
   if any(v is not None for v in cur):raise ValueError('row extends past width')
  for s in streams:s.finish()
  if seeds_seen!=seed_roots or not np.all(seen) or codes!=set(required_codes):raise ValueError('incomplete seed/root/category coverage')
  if seed_rules is not None:
   if not isinstance(seed_rules,list) or len(seed_rules)!=len(seed_roots):raise ValueError('invalid seed rule count')
   rules={r['component_id_current_generation_only']:r for r in seed_rules}
   if len(rules)!=len(seed_rules) or set(rules)!=seed_roots:raise ValueError('seed rule root mismatch')
   if not isinstance(expected_rule_population,dict) or set(expected_rule_population)!={str(root) for root in seed_roots}:raise ValueError('seed rule population root mismatch')
   for root,r in rules.items():
    inside,outside=r['inside_code'],r['outside_code'];region=r['region_id'];counts=by_root[root]
    if region is None:
     if inside!=outside or set(counts)!={inside}:raise ValueError('whole-component seed category mismatch')
     expected={'inside_cells':counts[inside],'outside_cells':0}
    else:
     if inside==outside or set(counts)!={inside,outside}:raise ValueError('split-component seed category mismatch')
     expected={'inside_cells':counts[inside],'outside_cells':counts[outside]}
    if not isinstance(expected_rule_population,dict) or expected_rule_population.get(str(root))!=expected:raise ValueError('seed rule population mismatch')
   if not isinstance(expected_category_counts,dict) or expected_category_counts!={str(k):v for k,v in category_counts.items()}:raise ValueError('seed category population mismatch')
  return {'land_cells':land,'nonseed_roots':len(roots),'seed_roots':sorted(seeds_seen),'seed_codes':sorted(codes),'seed_category_cells':{str(k):v for k,v in category_counts.items()}}

 finally:
  for s in streams:s.close()
