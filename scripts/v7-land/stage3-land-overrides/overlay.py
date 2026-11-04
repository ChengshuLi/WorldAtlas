"""Streaming land-only overlay core for authenticated source-derived decisions.

This pure core does not authenticate Neon, sources, or claim resolvers. Component
IDs and per-row region spans must be freshly resolved from those decisions by
its caller. Historical comparison spans are never accepted as decisions.
"""
def need(ok,msg):
 if not ok:raise ValueError(msg)

def _claim(c):
 need(isinstance(c,dict) and set(c)=={'affiliation_id','entry_ids','code'} and isinstance(c['affiliation_id'],str) and c['affiliation_id'] and isinstance(c['entry_ids'],list) and c['entry_ids'] and all(isinstance(x,str) and x for x in c['entry_ids']) and c['entry_ids']==sorted(set(c['entry_ids'])) and type(c['code']) is int and 17<=c['code']<=22,'invalid claim')
 return c

def validate_component_claims(component_claims):
 """Validate global component claims once before processing rows."""
 need(isinstance(component_claims,dict),'invalid component claims')
 for root,claims in component_claims.items():
  need(type(root) is int and 0<=root<0xffffffff and isinstance(claims,list) and claims,'invalid component claims')
  for claim in claims:_claim(claim)
 return component_claims

def overlay_row(width,physical,baseline,components,component_claims,region_claims,stats,emit_change):
 """Return normalized (exclusive_end,code) runs, updating decision statistics.

 physical: (start,end,1|17), baseline: (end,0|17..22), components:
 (start,end,ephemeral_root). component_claims maps root to one or more
 authenticated claims validated once with `validate_component_claims`. region_claims are `{claim,roots,spans}` with sorted,
 non-overlapping source-rasterized `(start,end)` spans and a nonempty set of
 freshly resolved eligible roots. Water coverage by a region is ignored; it
 can never receive a land code. `emit_change` receives half-open changed spans
 `(start,end,old,new,affiliation_ids,entry_ids)` for audit, never as input.
 """
 need(type(width) is int and width>0 and isinstance(component_claims,dict) and isinstance(region_claims,list) and len(region_claims)<=1000 and isinstance(stats,dict) and callable(emit_change),'invalid overlay inputs')
 x=0
 for a,b,c in physical:need(a==x and a<b<=width and c in (1,17),'invalid physical row');x=b
 need(x==width,'incomplete physical row');x=0
 for end,c in baseline:need(x<end<=width and (c==0 or 17<=c<=22),'invalid baseline row');x=end
 need(x==width,'incomplete baseline row');last=0
 for a,b,root in components:need(type(root) is int and 0<=root<0xffffffff and last<=a<b<=width,'invalid component row');last=b
 normalized=[]
 for item in region_claims:
  need(isinstance(item,dict) and set(item)=={'claim','roots','spans'} and isinstance(item['roots'],(set,frozenset)) and item['roots'] and all(type(x) is int and 0<=x<0xffffffff for x in item['roots']) and isinstance(item['spans'],list),'invalid region claim')
  _claim(item['claim']);last=0
  for a,b in item['spans']:need(type(a) is int and type(b) is int and last<=a<b<=width,'invalid source-region row spans');last=b
  normalized.append([item,0])
 out=[];pi=bi=ci=x=0
 def emit(end,code):
  if out and out[-1][1]==code:out[-1]=(end,code)
  else:out.append((end,code))
 while x<width:
  pa,pb,pc=physical[pi];be,bc=baseline[bi];active=[];end=min(pb,be)
  for item in normalized:
   region,j=item;spans=region['spans']
   while j<len(spans) and spans[j][1]<=x:j+=1
   item[1]=j
   if j<len(spans):
    a,b=spans[j]
    if a<=x<b:end=min(end,b);active.append(region)
    elif x<a:end=min(end,a)
  if pc==1:
   need(bc==0,'baseline assigns land to physical water');need(ci==len(components) or components[ci][0]>=pb,'component overlaps physical water');emit(end,0)
  else:
   need(17<=bc<=22 and ci<len(components),'missing baseline land or component');ca,cb,root=components[ci];need(ca<=x<cb and ca>=pa and cb<=pb,'component and physical land disagree');end=min(end,cb)
   claims=list(component_claims.get(root,[]))+[r['claim'] for r in active if root in r['roots']]
   by_id={}
   for claim in claims:
    _claim(claim);aid=claim['affiliation_id']
    need(aid not in by_id or by_id[aid]==claim,'inconsistent duplicate affiliation claim');by_id[aid]=claim
   codes={v['code'] for v in by_id.values()};need(len(codes)<=1,'conflicting selected affiliation targets');new=next(iter(codes)) if codes else bc;n=end-x
   for aid,claim in by_id.items():
    counter=stats.setdefault(aid,{'applied_cells':0,'changed_cells':0,'from_codes':{}});counter['applied_cells']+=n;counter['changed_cells']+=n if new!=bc else 0;counter['from_codes'][str(bc)]=counter['from_codes'].get(str(bc),0)+n
   if new!=bc:
    aids=tuple(sorted(by_id));entries=tuple(sorted({v for claim in by_id.values() for v in claim['entry_ids']}));need(aids and entries,'changed span has no traceable decision');emit_change(x,end,bc,new,aids,entries)
   emit(end,new)
  need(end>x,'non-advancing overlay');x=end
  if x==pb:pi+=1
  if x==be:bi+=1
  if ci<len(components) and x==components[ci][1]:ci+=1
 need(pi==len(physical) and bi==len(baseline) and ci==len(components),'row has trailing intervals')
 return out
