exec(open('.cache/shared-edge-991/exact-export.py').read().split('export={};')[0])
from exact_arrangement import boundaries,export_rings,point,signed_area
from shapely.geometry import shape

def collapse(ring):
 raw=[(float(x),float(y))for x,y in ring];sequence=[]
 for p in raw:
  if not sequence or p!=sequence[-1]:sequence.append(p)
 if sequence and sequence[0]==sequence[-1]:sequence.pop()
 stack=[];index={};loops=[]
 for p in sequence+[sequence[0]]:
  if p in index:
   begin=index[p];loop=stack[begin:]
   if loop:loops.append(loop)
   stack=stack[:begin+1];index={v:n for n,v in enumerate(stack)}
  else:index[p]=len(stack);stack.append(p)
 if len(stack)!=1:raise ValueError('Rounded traversal did not close')
 return loops
result={'diagnostic_only':True,'policy':'Exact coordinate equality/zero exact binary-rational loop only; no area cutoff, proximity, snapping or MakeValid. Every collapsed walk retained as diagnostic; exact topology remains primary and unapproved.','candidates':{},'collapses':{},'summaries':{}}
for id in d['subject_ids']:
 exact=boundaries(arrangement['faces'],labels,id);kept=[];collapsed=[]
 for n,r in enumerate(exact):
  loops=collapse(r)
  for loop in loops:
   rational=[point(p)for p in loop];area=signed_area(rational)
   if len(set(loop))<3 or area==0:collapsed.append({'exact_cycle':n,'rounded_cycle':[list(p)for p in loop],'exact_original_cycle':[[str(x),str(y)]for x,y in r]})
   else:kept.append(rational)
 geometry=export_rings(kept);g=shape(geometry);result['candidates'][id]=geometry;result['collapses'][id]=collapsed;result['summaries'][id]={'kept_cycles':len(kept),'collapsed_walks':len(collapsed),'rounded_valid':g.is_valid,'type':g.geom_type}
pathlib.Path('.cache/shared-edge-991/rounded-cycles-v1.json').write_text(json.dumps(result)+'\n');print(json.dumps(result['summaries']))
