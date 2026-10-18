import pathlib,json,gzip,collections,hashlib,sys
w=pathlib.Path(sys.argv[1]);p=w/'coordination/engineering/kenya-original-repair-20261018'
def j(n):return json.loads((p/n).read_text())
def rows(obj):
 keys={}
 for row in obj['rows']:
  for run in row['runs']:
   assert len(run) in [3,4]
   if len(run)==4:assert run[3]=='territorial_exclusion_cells'
   a,b,o=run[:3]
   for x in range(a,b):
    key=row['y'],x
    assert key not in keys
    keys[key]=o
 return keys
original={};classes={}
for block in [31,32]:
 for y,a,b,owners,sources,kind in json.loads(gzip.decompress((p/('original-intervals/block-%03d.json.gz'%block)).read_bytes())):
  assert len(owners)==1 and kind in ['land','inland-water']
  for x in range(a,b):
   assert (y,x) not in original
   original[y,x]=owners[0];classes[y,x]=kind
requested=rows(j('native-request-001/native-requested-patch.json'));supported=rows(j('supported-inputs-001/native-patch.json'));held=rows(j('supported-inputs-001/held-original.json'));assert requested==original and len(original)==5156 and len(supported)==4941 and len(held)==215
assert not supported.keys()&held.keys() and {**supported,**held}==original
constructor=j('native-authority-supported-001/constructor-result.json');ledger={}
for r in constructor['ledger_rows']:
 ks=rows({'rows':r['native_rows']});assert len(ks)==r['native_cells'] and set(ks.values())=={r['pixelIndex']}
 assert not ledger.keys()&ks.keys();ledger.update(ks)
assert ledger==supported and len(constructor['ledger_rows'])==len(constructor['component_ids'])==38
before=j('source-evidence-001/source-evidence.json');after=j('supported-inputs-001/source-evidence.json');assert {k:v for k,v in before.items() if k!='targets'}=={k:v for k,v in after.items() if k!='targets'}
a={r['id']:r for r in before['targets']};b={r['id']:r for r in after['targets']};assert set(a)==set(b) and len(a)==38
for k in a:assert {x:v for x,v in a[k].items() if x!='coverage_rows'}=={x:v for x,v in b[k].items() if x!='coverage_rows'}
# Independent raw original class/owner accounting, not diagnostics' stored counters.
owners=collections.defaultdict(lambda:collections.Counter());classcounts={}
for label,ks in [('original',original),('qualified',supported),('held',held)]:
 c=collections.Counter(classes[k] for k in ks);classcounts[label]=dict(c)
 for key,owner in ks.items():owners[owner][label]+=1
assert classcounts=={'original':{'land':5090,'inland-water':66},'qualified':{'land':4901,'inland-water':40},'held':{'land':189,'inland-water':26}}
for owner,c in owners.items():assert c['original']==c['qualified']+c['held']
result={'version':1,'kind':'exact-Kenya-original-owner-key-accounting','original_cells':len(original),'qualified_cells':len(ledger),'held_cells':len(held),'original_owners':len(owners),'qualified_components':len(constructor['component_ids']),'literal_constructor_ledger_rows':len(constructor['ledger_rows']),'class_cells':classcounts,'per_owner':dict(owners),'checks':['Actual original interval owner/key union equals the original requested patch.','Supported and held owner/key unions are disjoint and exactly equal all originals.','Actual literal constructor rows equal the supported owner/key patch.','Every38owner retains original=qualified+held accounting.','Whole source, physical, ancestry and negative operands unchanged; only positive requested coverage_rows narrowed.'],'accepted_cells':0,'limits':['Native qualification is historical source-relative support, not current-owner-zero, selected acceptance, source/legal approval or full package completion.']}
print(json.dumps(result,indent=2))
