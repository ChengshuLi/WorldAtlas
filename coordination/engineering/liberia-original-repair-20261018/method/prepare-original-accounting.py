"""Exact original integer-key accounting only; no geometry or producer replay.
Usage: python prepare-original-accounting.py PACKAGE_DIRECTORY FRESH_OUTPUT_DIRECTORY
"""
import pathlib,json,gzip,collections,re,sys
D=pathlib.Path(sys.argv[1]);O=pathlib.Path(sys.argv[2]);O.mkdir(parents=True,exist_ok=False)
def load(n):return json.loads((D/n).read_text())
def save(n,d):(O/n).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def expand(rows):
 out={}
 for row in rows:
  for run in row['runs']:
   a,b,owner=run[:3]
   for x in range(a,b):
    key=(row['y'],x);assert key not in out;out[key]=owner
 return out
original={};rawrows=[]
for f in sorted((D/'original-intervals-001').glob('block*.json.gz')):
 for row in json.load(gzip.open(str(f),'rt')):
  y,a,b,owners,sources,cls=row;assert len(owners)==1 and cls=='land';rawrows.append(row)
  for x in range(a,b):assert(y,x)not in original;original[y,x]=owners[0]
scope=load('original-claim-scope.json');members={x['index']:x for x in scope['owners']};supported=expand(load('supported-inputs-001/native-patch.json')['rows']);held=expand(load('supported-inputs-001/held-original.json')['rows']);result=load('native-authority-supported-001/constructor-result.json');ledger=expand([r for part in result['ledger_rows']for r in part['native_rows']])
assert ledger==supported and not(set(supported)&set(held))and dict(list(supported.items())+list(held.items()))==original
assert len(original)==2026 and len(rawrows)==1005 and len(supported)==2025 and len(held)==1
assert set(original.values())==set(members)and len(members)==47 and all(x['source_atoms']==[x['id']]for x in members.values())
a=load('source-evidence-001/source-evidence.json');b=load('supported-inputs-001/source-evidence.json');assert set(a)==set(b)and all(a[k]==b[k]for k in a if k!='targets');original_targets={t['pixelIndex']:t for t in a['targets']};surviving_targets={t['pixelIndex']:t for t in b['targets']};assert set(surviving_targets)==set(supported.values())and len(surviving_targets)==47
assert all({k:v for k,v in t.items()if k!='coverage_rows'}=={k:v for k,v in original_targets[o].items()if k!='coverage_rows'}for o,t in surviving_targets.items())
assert len(result['ledger_rows'])==len(result['component_ids'])==47
owners=[]
for owner,m in sorted(members.items()):owners.append(dict(owner=owner,id=m['id'],name=m['name'],source_atoms=m['source_atoms'],original_cells=sum(v==owner for v in original.values()),qualified_cells=sum(v==owner for v in supported.values()),stock_held_cells=sum(v==owner for v in held.values())))
reasons=collections.Counter()
for row in load('supported-inputs-001/held-original.json')['rows']:
 for run in row['runs']:reasons[run[3]]+=run[1]-run[0]
assert dict(reasons)=={'territorial_exclusion_cells':1}and held=={(126219,124938):26987}
research=[];groups=[]
for issue in [802,813]:
 body=load('source-review/prepared-input-context/issue-'+str(issue)+'.json')['body'];atoms=set(re.findall(r'gb:LBR:ADM2:[A-Za-z0-9]+',body));subset=[x for x in owners if x['id']in atoms];groups.append(set(x['owner']for x in subset));research.append(dict(issue='https://github.com/ChengshuLi/WorldAtlas/issues/'+str(issue),state_at_read='open',original_owner_atoms=len(subset),original_cells=sum(x['original_cells']for x in subset),stock_qualified_cells=sum(x['qualified_cells']for x in subset),stock_held_cells=sum(x['stock_held_cells']for x in subset),owners=subset,acceptance='Separate2021-to-LISGIS2022 source crosswalk obligations remain unresolved; native accounting does not close or replace this research.'))
assert[len(g)for g in groups]==[43,4]and not(groups[0]&groups[1])and(groups[0]|groups[1])==set(members)
save('unchanged-source-research-scopes.json',dict(version=1,package_id=scope['package_id'],original_cells=2026,original_owner_atoms=47,research_scopes=research,other_source_parent_followup='https://github.com/ChengshuLi/WorldAtlas/issues/1077',limits=['These are existing source-research scopes, not an invented native held partition or admission approval.','Only the genuine one-cell stock held partition changes positive coverage; no manual source veto or restoration was applied.','Historical source-relative qualification does not establish modern legal roles, regional approval or current boundary correctness.']))
held_context=[row for row in rawrows if row[0]==126219 and row[1]<=124938<row[2]and row[3]==[26987]];assert len(held_context)==1
save('exact-original-conservation.json',dict(version=1,package_id=scope['package_id'],method='Exact immutable integer-row/owner key joins only; no geometry or producer replay.',original_cells=2026,original_land_cells=2026,original_water_cells=0,original_intervals=1005,original_owners=47,all_original_source_atoms=47,qualified_cells=2025,stock_held_cells=1,qualified_components=47,ledger_equals_supported_patch=True,partition_disjoint=True,partition_exact_original_union=True,owner_reassignments=0,all_original_classes_land=True,all_non_target_source_fields_identical=True,surviving_targets_identical_except_coverage_rows=True,all_territorial_operands_preserved=True,all_original_owners=owners,fully_stock_held_owners=[],stock_hold_reasons=dict(reasons),complete_stock_held_rows=load('supported-inputs-001/held-original.json')['rows'],complete_held_original_interval_context=held_context,stock_per_key_causal_foreign_feature='Not identified by the stock diagnostic; independent review evidence is distinct.',new_accepted_cells=0,limits=['All47 original source atoms, physical records and full136domestic/617foreign source context remain preserved.','Constructor qualification is not actual current-owner-zero, final selected-output acceptance, legal/territorial clearance, integration or delivery.','Existing research802/813andparent-source1077acceptance remains separate.']))
print(json.dumps(dict(original=len(original),qualified=len(supported),held=len(held),components=len(result['component_ids']),fullyheld=0,research=[{k:x[k]for k in ['issue','original_owner_atoms','original_cells','stock_qualified_cells','stock_held_cells']}for x in research]),indent=2))
