"""Project request-only class intervals, retaining all 334 complete context targets.
Usage: python bind-supported-coverage.py REPO NEW_CONFIG NEW_REPORT
Every source, geometry, physical issue, competitor, negative and non-request field
stays literal. Original full-scope evidence and supported/held partition remain pinned.
"""
import collections,copy,hashlib,json,pathlib,subprocess,sys
W=pathlib.Path(sys.argv[1]);P='coordination/engineering/russia-repair-delivery-20261017/';E='a8c114c829646ac2191e21bbb9f4f15fec710787';H='44b0b0d71e853ad0bebca4fffdd26b74c0a92e0c'
def raw(c,p):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',c+':'+p])
def pin(c,p):
 b=raw(c,p);return {'commit':c,'path':p,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
old=json.loads(raw(E,P+'native-inputs-002/source-evidence.json'));new=copy.deepcopy(old);patch=json.loads(raw(H,P+'native-partition-preaccept-001/supported-native-patch.json'));reconciliation=json.loads(raw(H,P+'native-partition-preaccept-001/whole-scope-reconciliation.json'));expected={r['owner']:r for r in reconciliation['per_owner']};support=collections.defaultdict(dict)
for row in patch['rows']:
 for a,z,o in row['runs']:support[o].setdefault(row['y'],[]).append([a,z])
records=[];classes=collections.Counter()
for t in new['targets']:
 owner=t['pixelIndex'];original=t['coverage_rows'];rows=[];counts=collections.Counter();original_count=sum(z-a for r in original for a,z,k in r['runs'])
 for row in original:
  runs=[]
  for a,z,kind in row['runs']:
   for x,y in support[owner].get(row['y'],[]):
    lo,hi=max(a,x),min(z,y)
    if lo<hi:
     if runs and runs[-1][1]==lo and runs[-1][2]==kind:runs[-1][1]=hi
     else:runs.append([lo,hi,kind])
     counts[kind]+=hi-lo
  if runs:rows.append({'y':row['y'],'runs':runs})
 assert sum(counts.values())==expected[owner]['supported'] and original_count==expected[owner]['requested']
 if rows:t['coverage_rows']=rows
 else:
  assert len(t['coverage_classes'])==1,'Context-only mixed-class interpretation would need separate handling'
  del t['coverage_rows']
 classes.update(counts);records.append({'id':t['id'],'owner':owner,'original_requested_cells':original_count,'supported_requested_cells':sum(counts.values()),'held_cells':expected[owner]['held'],'supported_class_cells':dict(counts),'context_only':not bool(rows)})
# Exact key/value identity of all scientific and context content, beyond only
# this optional per-request class binding, is mandatory for all original targets.
assert len(old['targets'])==len(new['targets'])==334
for a,b in zip(old['targets'],new['targets']):assert {k:v for k,v in a.items() if k!='coverage_rows'}=={k:v for k,v in b.items() if k!='coverage_rows'}
assert {k:v for k,v in old.items() if k!='targets'}=={k:v for k,v in new.items() if k!='targets'}
assert sum(classes.values())==2557516 and sum(r['held_cells'] for r in records)==9451 and sum(r['context_only'] for r in records)==7
config={'version':1,'selector':{'commit':'9d564cf4083cb5499b00d6fb4ceb6fc724fdf01c','path':'data/ownership-selection.json'},'source_evidence':new};report={'version':1,'original_evidence':pin(E,P+'native-inputs-002/source-evidence.json'),'supported_patch':pin(H,P+'native-partition-preaccept-001/supported-native-patch.json'),'whole_partition':pin(H,P+'native-partition-preaccept-001/whole-scope-reconciliation.json'),'original_targets':334,'supported_targets':327,'context_only_targets':7,'original_cells':2566967,'supported_cells':2557516,'held_cells':9451,'supported_class_cells':dict(classes),'all_non_request_fields_literal_equal':True,'per_owner':records,'limits':['Only explicit class intervals binding the supported native request are projected. All original full-scope class rows remain in immutable native-inputs-002 and full diagnostic.','No source feature, negative operand, physical input/output, whole-target geometry, target identity, declared class, or source-membership field is removed, clipped or changed.','The seven wholly held owners remain complete context targets with no requested native cells; the optional coverage_rows field is absent only for those seven.']}
for path,value in [(sys.argv[2],config),(sys.argv[3],report)]:
 with pathlib.Path(path).open('x') as f:json.dump(value,f,ensure_ascii=False,separators=(',',':'));f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['per_owner','original_evidence','supported_patch','whole_partition','limits']}))
