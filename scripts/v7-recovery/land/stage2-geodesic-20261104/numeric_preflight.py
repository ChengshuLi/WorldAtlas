"""Experimental complete NumPy coverage check; production remains unchanged.

This removes Python dispatch per interval, not validation or input coverage.
Use only for explicit paired validation until full-input parity/timing exists.
"""
import numpy as np
from row_overlay import RowStream,overlay,overlay_batch


def validate(width,height,component_rows,component_runs,physical_rows,physical_runs,mainland_rows,mainland_runs,roots,seed_roots,required_codes=range(17,23),guard=lambda:None,seed_rules=None,expected_rule_population=None,expected_category_counts=None,*,batch_rows=1):
    if type(batch_rows) is not int or batch_rows<1:raise ValueError('invalid row batch')
    roots=np.asarray(roots,dtype=np.uint32);seed_roots=set(map(int,seed_roots))
    if roots.ndim!=1 or len(roots)==0 or np.any(roots[1:]<=roots[:-1]) or not seed_roots or np.any(np.isin(roots,list(seed_roots))):
        raise ValueError('bad component root lists')
    seen=np.zeros(len(roots),dtype=bool);seeds_seen=set();codes=set();land=0;by_root={};category_counts={}
    streams=[]
    try:
        for rowpath,runpath,columns in ((component_rows,component_runs,3),(physical_rows,physical_runs,2),(mainland_rows,mainland_runs,2)):
            streams.append(RowStream(rowpath,runpath,height,columns))
        next_guard=0
        for y in range(0,height,batch_rows):
            if y>=next_guard:guard();next_guard=y+128
            count=min(batch_rows,height-y)
            if count==1:
                components,physical,seed=(stream.next() for stream in streams)
                left,right,owner,phys,selected=overlay(width,components,physical,seed)
            else:
                fields=[value for stream in streams for value in stream.next_rows(count)]
                components=fields[1]
                left,right,owner,phys,selected=overlay_batch(width,*fields)
            present=owner>=0
            if np.any(present!=(phys==17)):
                at=int(np.flatnonzero(present!=(phys==17))[0]);raise ValueError('physical/component mismatch at row '+str(y+int(left[at])//width))
            if np.any((~present)&(selected!=0)):raise ValueError('seed outside physical land')
            root_values=components[:,2];is_seed=np.isin(root_values,list(seed_roots))
            position=np.searchsorted(roots,root_values)
            safe=np.minimum(position,len(roots)-1)
            if np.any((~is_seed)&((position==len(roots)) | (roots[safe]!=root_values))):raise ValueError('unknown nonseed root')
            seed_mask=np.zeros(len(left),dtype=bool)
            seed_mask[present]=is_seed[owner[present]]
            if np.any(seed_mask&(selected==0)):raise ValueError('seed root gap')
            if np.any(present&(~seed_mask)&(selected!=0)):raise ValueError('seed on nonseed root')
            seen[position[~is_seed]]=True
            seeds_seen.update(map(int,np.unique(root_values[is_seed])))
            codes.update(map(int,np.unique(selected[seed_mask])))
            lengths=right.astype(np.uint64)-left
            land+=int(lengths[present].sum(dtype=np.uint64))
            for root in np.unique(root_values[is_seed]):
                mask=seed_mask.copy();mask[present]&=root_values[owner[present]]==root
                totals=np.zeros(23,dtype=np.uint64);np.add.at(totals,selected[mask],lengths[mask])
                counts=by_root.setdefault(int(root),{})
                for code in np.flatnonzero(totals):
                    code=int(code);count=int(totals[code]);counts[code]=counts.get(code,0)+count
                    category_counts[code]=category_counts.get(code,0)+count
        for stream in streams:stream.finish()
        if seeds_seen!=seed_roots or not np.all(seen) or codes!=set(required_codes):raise ValueError('incomplete seed/root/category coverage')
        if seed_rules is not None:
            if not isinstance(seed_rules,list) or len(seed_rules)!=len(seed_roots):raise ValueError('invalid seed rule count')
            rules={rule['component_id_current_generation_only']:rule for rule in seed_rules}
            if len(rules)!=len(seed_rules) or set(rules)!=seed_roots:raise ValueError('seed rule root mismatch')
            if not isinstance(expected_rule_population,dict) or set(expected_rule_population)!={str(root) for root in seed_roots}:raise ValueError('seed rule population root mismatch')
            for root,rule in rules.items():
                inside,outside=rule['inside_code'],rule['outside_code'];counts=by_root[root]
                if rule['region_id'] is None:
                    if inside!=outside or set(counts)!={inside}:raise ValueError('whole-component seed category mismatch')
                    expected={'inside_cells':counts[inside],'outside_cells':0}
                else:
                    if inside==outside or set(counts)!={inside,outside}:raise ValueError('split-component seed category mismatch')
                    expected={'inside_cells':counts[inside],'outside_cells':counts[outside]}
                if expected_rule_population.get(str(root))!=expected:raise ValueError('seed rule population mismatch')
            if expected_category_counts!={str(k):v for k,v in category_counts.items()}:raise ValueError('seed category population mismatch')
        return {'land_cells':land,'nonseed_roots':len(roots),'seed_roots':sorted(seeds_seen),'seed_codes':sorted(codes),'seed_category_cells':{str(k):v for k,v in category_counts.items()}}
    finally:
        for stream in streams:stream.close()
