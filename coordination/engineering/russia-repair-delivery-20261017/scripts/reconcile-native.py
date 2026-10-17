"""Reconcile the full unchanged denominator before extracting qualified rows.
Usage: Python reconcile-native.py REPO DIAGNOSTIC_PATH OUTPUT_DIRECTORY
This extracts stock decisions; it does not override or recompute authority.
"""
import collections,gzip,hashlib,json,pathlib,sys
W=pathlib.Path(sys.argv[1]);D=W/sys.argv[2];OUT=W/sys.argv[3];P=W/'coordination/engineering/russia-repair-delivery-20261017'
def read(p):return json.loads(p.read_bytes())
def count(rows):return sum(z-a for r in rows for a,z,*_ in r['runs'])
def merge(rows):
 result=[]
 for r in rows:
  rs=[]
  for a,z,o in sorted(r['runs']):
   if rs:assert a>=rs[-1][1]
   if rs and rs[-1][1]==a and rs[-1][2]==o:rs[-1][1]=z
   else:rs.append([a,z,o])
  if rs:result.append({'y':r['y'],'runs':rs})
 return result
original=read(P/'source-stage/native-patch.json')['rows'];d=read(D)
assert d['requested_rows']==original and count(original)==d['requested_cells']==2566967
assert d['supported_cells']+d['held_cells']==2566967
owners={r['owner']:r for r in read(P/'source-review/current-targets.json')};byrow={r['y']:r['runs'] for r in d['decision_rows']};reasons=collections.Counter();perowner={o:{'owner':o,'id':v['id'],'name':v['current_target']['properties']['name'],'requested':0,'supported':0,'held':0,'reasons':collections.Counter(),'foreign_source_contact_cells':0} for o,v in owners.items()}
supported=[];held=[]
for r in original:
 dec=byrow.pop(r['y']);assert all(len(x)==4 for x in dec);expected=merge([{'y':r['y'],'runs':[x[:3] for x in dec]}]);assert expected==merge([r]);s=[];h=[]
 for a,z,o,reason in dec:
  assert o in owners;n=z-a;reasons[reason]+=n;perowner[o]['requested']+=n;perowner[o]['reasons'][reason]+=n;key='supported' if reason=='assigned_cells' else 'held';perowner[o][key]+=n;(s if reason=='assigned_cells' else h).append([a,z,o])
 if s:supported.append({'y':r['y'],'runs':s})
 if h:held.append({'y':r['y'],'runs':h})
assert not byrow and len(perowner)==334 and all(r['requested']>0 for r in perowner.values())
assert merge(supported)==d['supported_rows'] and merge(held)==d['held_rows'];assert count(d['supported_rows'])==d['supported_cells'];assert count(d['held_rows'])==d['held_cells']
heldmap={r['y']:r['runs'] for r in d['held_rows']};declared={r['y']:r['runs'] for r in d['decision_rows']}
foreign=read(P/'source-review/source-competitor-native-counts.json')['non_russian_original_competitor_intervals']
for y,a,z,o,ids in foreign:
 n=sum(max(0,min(z,zz)-max(a,aa)) for aa,zz,oo in heldmap.get(y,[]) if oo==o);assert n==z-a,(y,a,z,o,'foreign contact escaped hold');perowner[o]['foreign_source_contact_cells']+=n
hist=read(P/'source-review/historical-component-intersections.json');historical=[]
for item in hist['exact_repair_intersections']:
 outcomes=collections.Counter();intervals=[]
 for y,a,z,o in item['intervals']:
  for aa,zz,oo,reason in declared[y]:
   lo,hi=max(a,aa),min(z,zz)
   if lo<hi and oo==o:outcomes[reason]+=hi-lo;intervals.append([y,lo,hi,o,reason])
 assert sum(outcomes.values())==item['cells'];historical.append({'scope':item['scope'],'component_id':item['component_id'],'original_intersection_cells':item['cells'],'outcomes':dict(outcomes),'decision_intervals':intervals,'whole_component_disposition':'original unresolved source-fitness question retained unchanged'})
assert sum(r['original_intersection_cells'] for r in historical)==135
classes={'supported':collections.Counter(),'held':collections.Counter()}
for block in sorted((P/'source-stage').glob('frozen-block-*.gz')):
 for y,a,z,os,ss,kind in json.loads(gzip.decompress(block.read_bytes())):
  for aa,zz,o,reason in declared[y]:
   lo,hi=max(a,aa),min(z,zz)
   if lo<hi and o==os[0]:classes['supported' if reason=='assigned_cells' else 'held'][kind]+=hi-lo
assert sum(sum(c.values()) for c in classes.values())==2566967
OUT.mkdir(parents=True,exist_ok=False)
for name,rows in [('supported-native-patch.json',d['supported_rows']),('held-native-patch.json',d['held_rows'])]:(OUT/name).write_text(json.dumps({'rows':rows},separators=(',',':'))+'\n')
report={'version':1,'whole_original_denominator':2566967,'original_target_count':334,'supported_cells':d['supported_cells'],'held_cells':d['held_cells'],'reasons':dict(reasons),'class_outcomes':{k:dict(v) for k,v in classes.items()},'complete_foreign_source_contact_cells_held':sum(r[2]-r[1] for r in foreign),'all_original_rows_partitioned_exactly':True,'per_owner':list(perowner.values()),'historical_components':historical,'diagnostic_sha256':hashlib.sha256(D.read_bytes()).hexdigest(),'source_evidence':d['original_pins']['source_evidence'],'original_patch':d['original_pins']['native_patch'],'limits':['Stock diagnostic decisions only: no authority, accepted owner-zero or emitted-output proof.','All original source and physical issues and historical whole-component dispositions remain unresolved at their original scope.','The supported patch is an explicit partition of the full original denominator, never a redefined scope.']}
(OUT/'whole-scope-reconciliation.json').write_text(json.dumps(report,separators=(',',':'),ensure_ascii=False)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['per_owner','historical_components','source_evidence','original_patch']}))
