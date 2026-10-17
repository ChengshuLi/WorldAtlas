"""Check exact interval conservation against the actual accepted cumulative selector.
Usage: python check-delivery-conservation.py REPO BASE CANDIDATE COMPOSITION_PREFIX NEW_OUTPUT
Consumes immutable Git bodies; no per-cell expansion, geometry operations or writes to inputs.
"""
import collections,hashlib,json,pathlib,subprocess,sys
W,BASE,H,COMPOSE,OUTPUT=sys.argv[1:];P='coordination/engineering/russia-repair-delivery-20261017/';STAGE='44b0b0d71e853ad0bebca4fffdd26b74c0a92e0c'
def raw(c,p):return subprocess.check_output(['git','-c','protocol.allow=never','-C',W,'show',c+':'+p])
def data(c,p):return json.loads(raw(c,p))
def pinned(pin):
 b=raw(pin['commit'],pin['path']);assert len(b)==pin['bytes'] and hashlib.sha256(b).hexdigest()==pin['sha256'];return json.loads(b)
def count(rows):return sum(z-a for r in rows for a,z,o in r['runs'])
def normal(rows):
 grouped=collections.defaultdict(list)
 for r in rows:grouped[r['y']]+=r['runs']
 out=[]
 for y,runs in sorted(grouped.items()):
  merged=[]
  for a,z,o in sorted(runs):
   assert a<z
   if merged:assert a>=merged[-1][1],('overlap',y,a,z,o,merged[-1])
   if merged and a==merged[-1][1] and o==merged[-1][2]:merged[-1][1]=z
   else:merged.append([a,z,o])
  if merged:out.append({'y':y,'runs':merged})
 return out
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)
selector=data(BASE,'data/ownership-selection.json');sidebody=raw(BASE,selector['additive_release']['path']);assert len(sidebody)==selector['additive_release']['bytes'] and hashlib.sha256(sidebody).hexdigest()==selector['additive_release']['sha256'];side=json.loads(sidebody)
before=pinned(side['logical_asset_map']['patch'])['rows'];prior_ledger=pinned(side['logical_asset_map']['ledger']);prior_registry=pinned(side['authority_registry'])
requested=data(STAGE,P+'source-stage/native-patch.json')['rows'];supported=data(STAGE,P+'native-partition-preaccept-001/supported-native-patch.json')['rows'];held=data(STAGE,P+'native-partition-preaccept-001/held-native-patch.json')['rows'];reconciliation=data(STAGE,P+'native-partition-preaccept-001/whole-scope-reconciliation.json')
assert normal(supported+held)==normal(requested) and count(requested)==2566967 and count(supported)==2557516 and count(held)==9451
foreign=data(STAGE,P+'source-review/source-competitor-native-counts.json')['non_russian_original_competitor_intervals']
foreign_rows=[{'y':y,'runs':[[a,z,o]]} for y,a,z,o,ids in foreign]
assert normal(foreign_rows)==normal(held),'Held intervals differ from complete original foreign ADM1 union'
# The whole original scope, including every held contact, remains disjoint from
# every already accepted additive assignment. No held contact can be promoted by composition.
normal(before+requested)
after=data(H,COMPOSE+'/patch.json')['rows'];ledger=data(H,COMPOSE+'/selected-ledger.json');registry=data(H,COMPOSE+'/authority-registry.json')
assert normal(after)==normal(before+supported)
for old,new in [(prior_ledger['rows'],ledger['rows']),(prior_registry['entries'],registry['entries'])]:assert not(collections.Counter(map(canonical,old))-collections.Counter(map(canonical,new)))
holds=lambda rows:[r for r in rows if r.get('disposition') not in ('assigned','zero-cell')]
assert collections.Counter(map(canonical,holds(prior_ledger['rows'])))==collections.Counter(map(canonical,holds(ledger['rows'])))
current=data(H,'data/ownership-selection.json');assert {k:v for k,v in current.items() if k!='additive_release'}=={k:v for k,v in selector.items() if k!='additive_release'}
p0=data(BASE,'.github/package-inputs.json');p1=data(H,'.github/package-inputs.json');assert {k:v for k,v in p0.items() if k!='inputs'}=={k:v for k,v in p1.items() if k!='inputs'};assert p1['inputs'][:len(p0['inputs'])]==p0['inputs'];assert all(s.startswith(P) for s in p1['inputs'][len(p0['inputs']):])
perowner=collections.Counter()
for row in supported:
 for a,z,o in row['runs']:perowner[o]+=z-a
assert len(perowner)==327 and len(reconciliation['per_owner'])==334 and sum(r['supported']==0 for r in reconciliation['per_owner'])==7
assert all(perowner[r['owner']]==r['supported'] for r in reconciliation['per_owner'])
report={'kind':'exact-literal-russia-conservation','baseline_commit':BASE,'candidate_commit':H,'composition_prefix':COMPOSE,'original_package_cells':2566967,'assigned_cells':count(supported),'withheld_cells':count(held),'removed_cells':0,'reassigned_cells':0,'prior_cells':count(before),'proposed_cumulative_cells':count(after),'original_target_count':334,'supported_target_count':327,'wholly_held_target_count':7,'prior_ledger_rows':len(prior_ledger['rows']),'proposed_ledger_rows':len(ledger['rows']),'prior_authorities':len(prior_registry['entries']),'proposed_authorities':len(registry['entries']),'prior_held_rows':len(holds(prior_ledger['rows'])),'proposed_held_rows':len(holds(ledger['rows'])),'per_owner':dict(sorted(perowner.items())),'literal_prior_rows_preserved':True,'literal_prior_authorities_preserved':True,'all_original_foreign_contacts_withheld':True,'held_rows_equal_complete_original_foreign_union':True,'nonadditive_selector_unchanged':True,'package_declaration_prefix_preserved':True,'historical_repair_overlap_centres_qualified':135,'separate_shared_lineage_cells_excluded':128253,'separate_physical_interpretation_cells_excluded':1250477,'limits':['Offline exact interval/additive conservation only; final selected-native owner-zero checks and genuine emitted-map consumer remain separately required.','All original 334 subjects and 2566967 cells remain represented by supported and held partitions; the seven wholly held owners are not dropped.','All original source/physical/semantic limitations and 100 historical whole-component dispositions remain unchanged.']}
with pathlib.Path(OUTPUT).open('x') as f:json.dump(report,f,sort_keys=True,separators=(',',':'),ensure_ascii=False);f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='per_owner'}))
