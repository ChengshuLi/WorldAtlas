"""Retain exact ordinary inputs and original result bindings; no geometry operations."""
import pathlib,json,gzip,subprocess,hashlib,collections
ROOT=pathlib.Path(__file__).resolve().parents[4];CASE=pathlib.Path(__file__).resolve().parent
PRIVATE=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.cache/repair-readiness-1231-20261006/direct-source-coverage-screen')
CORPUS='1c4b606d35614bd7c4990bb9da1098fa181c7fe8';HEAD='a26f8d8b50e7349054b86e70d1e6e552a9a2b0fd';M='79ffb2ed04702e16f009e4675a8d74ef9bd09d4f';S='7c7cdf2388e0e7200b937c2cfb440b53165d9d98';H='549cc2a863d4a487a662c2613e4d02888e39b5ba';I='c6a26e1caba54e1b81a89fbda3a64fff56da323d'
def canon(v):return(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def read(c,p):
 tree=subprocess.check_output(['git','ls-tree',c,'--',p],cwd=ROOT);assert tree.split()[0]in(b'100644',b'100755');return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
def write(p,b):
 p=CASE/p;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==b
 else:p.write_bytes(b)
 return str(p.relative_to(CASE))
scope_raw=(PRIVATE/'complete-family-package-measure/package-002-author-scope.json').read_bytes();assert sha(scope_raw)=='af192697fb6af9e7d6af503129f86e9badf391d0c75e2c17f97192a0645ca751';scope=json.loads(scope_raw);write('scope.json',scope_raw);target=set(scope['complete_component_ids']);assert len(target)==12427
aliases=[]
fullpins=list(scope['full_input_pins'])
if 'gb:IND:ADM3' in scope['source_ids']:
 p='data/global-sources/IND-ADM3-metadata.json';b=read(M,p);fullpins.append({'commit':M,'path':p,'bytes':len(b),'sha256':sha(b)})
for p in fullpins:
 # Source corpus parts are retained below with their full original raw relation.
 if 'commit'not in p:continue
 b=read(p['commit'],p['path']);assert len(b)==p['bytes']and sha(b)==p['sha256'];raw=gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b;assert max(len(b),len(raw))<=32*1024*1024
 name='inputs/immutable/'+p['sha256']+('.json.gz'if b[:2]==b'\x1f\x8b'else'.json');write(name,b);aliases.append({**p,'alias':name,'decoded_bytes':len(raw),'decoded_sha256':sha(raw)})
catpath='coordination/engineering/original-geography-source-corpus-20261006/catalogue.json';catraw=read(CORPUS,catpath);write('source-catalogue.json',catraw);catalogue=json.loads(catraw);products=[]
for product in catalogue['products']:
 if product['key']not in scope['source_ids']:continue
 parts=[];offset=0;digest=hashlib.sha256()
 for p in product['parts']:
  b=read(CORPUS,p['path']);assert len(b)==p['bytes']and sha(b)==p['sha256'];raw=gzip.decompress(b);assert len(raw)==p['uncompressed_bytes']and sha(raw)==p['uncompressed_sha256'];assert p['offset']==offset;offset+=len(raw);digest.update(raw);assert max(len(b),len(raw))<=32*1024*1024
  name='inputs/sources/'+p['sha256']+'.bin.gz';write(name,b);parts.append({**p,'alias':name,'original_corpus_commit':CORPUS})
 assert offset==product['original_bytes']and digest.hexdigest()==product['original_sha256'];products.append({**product,'parts':parts})
assert {p['key']for p in products}==set(scope['source_ids'])
# Bind each complete expected historical record to whole original files/ordinal.
# Embedded versus object-ref union representation remains per original cohort.
expected=[];sourcebindings={};historic=[]
names=['initial251','additive-admin-partition-0','additive-admin-partition-1','additive-india-refinement','next-administrative-single-edge','next-administrative-zero-edge','next-distinct-India-refinement-single-edge','next-distinct-India-refinement-zero-edge']
for name in names:
 d=PRIVATE if name=='initial251'else PRIVATE/name;receipt_raw=(d/'receipt.json').read_bytes();receipt=json.loads(receipt_raw);write('historical/'+name+'-actual-receipt.json.gz',gzip.compress(receipt_raw,mtime=0));historic.append({'cohort':name,'actual_scientific_executions':1,'immutable_executed_git_commit':None,'private_producer_sha256':receipt['script_sha256'],'original_receipt_sha256':sha(receipt_raw)})
 for x in json.loads((d/'complete-source-inputs.json').read_bytes())['source_products']:
  if x['source_id']in scope['source_ids']:
   if x['source_id']in sourcebindings:assert canon(sourcebindings[x['source_id']]['complete_features'])==canon(x['complete_features'])
   else:sourcebindings[x['source_id']]=x
 for pin in receipt['outputs']:
  p=pathlib.Path(pin['path']);p=p if p.is_absolute() else PRIVATE.parents[2]/p
  b=p.read_bytes();assert len(b)==pin['bytes']and sha(b)==pin['sha256'];raw=gzip.decompress(b);assert sha(raw)==pin['decoded_sha256'];rows=json.loads(raw)
  for ordinal,row in enumerate(rows):
   if row['component']in target:expected.append({'component':row['component'],'family':row['family'],'cohort':name,'whole_original_file':pin,'original_ordinal':ordinal,'original_canonical_row_sha256':sha(canon(row)),'union_transport':'embedded'if name=='initial251'else'object-ref','expected_geometry_hashes':{k:v['geometry_sha256']for k,v in row.items()if isinstance(v,dict)and'geometry_sha256'in v}})
 assert receipt['script_sha256']==sha((PRIVATE/('screen.py'if name=='initial251'else'screen-additive.py')).read_bytes())
assert len(expected)==len(target)and {x['component']for x in expected}==target
write('historical/expected-complete-records.json.gz',gzip.compress(canon(sorted(expected,key=lambda x:x['component'])),mtime=0))
# Exact source feature binding evidence uses existing ordinary JSON/gzip shards.
rows=[];size=0;n=0;sourcepins=[]
def flush():
 global rows,size,n
 if not rows:return
 raw=canon(rows);name='historical/source-feature-bindings-%03d.json.gz'%n;b=gzip.compress(raw,mtime=0);write(name,b);sourcepins.append({'alias':name,'bytes':len(b),'sha256':sha(b),'decoded_bytes':len(raw),'decoded_sha256':sha(raw)});rows=[];size=0;n+=1
for key,x in sorted(sourcebindings.items()):
 # Every feature retained; original custody p is historical rather than current alias.
 row={'source_id':key,**x};length=len(canon(row))
 if rows and size+length>8*1024*1024:flush()
 assert length<32*1024*1024;rows.append(row);size+=length
flush()
write('historical/private-initial-kernel.py',(PRIVATE/'screen.py').read_bytes());write('historical/private-additive-kernel.py',(PRIVATE/'screen-additive.py').read_bytes())
# Retain complete witness and numerical-uncertainty records independently of old status.
w=[x for x in json.loads((PRIVATE/'complete-current-unique-witness-dispatch.json').read_bytes())['all_rows']if x['component']in target];u=[{'component':x['full_record']['component'],**x}for x in json.loads((PRIVATE/'operation-consistency-diagnosis.json').read_bytes())['rows']]
for name in names[1:]:u+=json.loads((PRIVATE/name/'complete-whole-output-readback.json').read_bytes())['operation_consistency_unknowns']
u=[x for x in u if x['component']in target];assert len(w)==276 and len(u)==41
write('historical/full-witness-joins.json.gz',gzip.compress(canon(w),mtime=0));write('historical/operation-unknowns.json.gz',gzip.compress(canon(u),mtime=0))
config={'package':2,'complete_components':12427,'complete_families':2332,'scope_sha256':sha(scope_raw),'baseline_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'original_components_commit':M,'original_contexts_commit':H,'inventory_commit':I,'current_component_successor_commit':S,'native_snapshot_commit':HEAD,'source_corpus_commit':CORPUS,'source_catalogue_sha256':sha(catraw),'immutable_aliases':aliases,'source_products':products,'historical_execution_provenance':historic,'historical_source_bindings':sourcepins,'original_expected_records':'historical/expected-complete-records.json.gz','global_complete_components':95173,'global_complete_families':15610,'global_screened_components':57785,'global_screened_families':9587,'global_remaining_components':37388,'global_remaining_families':6023,'remaining_plan_sha256':'c1fbd02007b403e064b5ac02e2eea4a06652c1ae56a78aef33cc7a375d25e990','limits':['Actual original snapshot custody only; accepted pending artifacts are not selected production.','Old historical receipts each represent one actual private-SHA scientific execution; final immutable producer executions remain separate.']};write('input-config.json',canon(config));print('prepared',len(aliases),'immutable aliases',len(products),'whole sources',len(expected),'expected rows',len(w),'witnesses',len(u),'unknowns')
