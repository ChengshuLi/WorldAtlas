"""Reproduce original target ownership semantics from exact executed dependencies."""
import collections,hashlib,importlib.util,json,pathlib,sqlite3,sys
sys.dont_write_bytecode=True
root=pathlib.Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('incremental',root/'scripts/prepare-ownership-incremental.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
prefix=root/'coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22'
snapshot=prefix/'ownership-inputs-v2'
output=prefix/'ownership-before-verification-v1.json'
if output.exists():raise ValueError('Fresh output required')
index=m.load(root/'data/ownership-history/index.json');helpers=m.exact_helpers(root/'data/ownership-history',index)
pi,chunks=m.checked_sources(root/'data/cliopatria',index)
features=m.feature_snapshot(snapshot/'before/world.json')
if m.published_footprint_hash(features)!=index['footprints_sha256']:raise ValueError('Wrong baseline footprint')
versions,fingerprint,_=m.boundary_versions(snapshot/'boundaries.json',helpers.canonical,features)
if fingerprint!=index['inputs']['boundary_versions']:raise ValueError('Wrong dated footprint inputs')
ids=set(m.load(snapshot/'migration-receipt.json')['changed_ids'])
dbpath=root/'.cache/reference-repair-991/ownership-before-v1.sqlite'
if dbpath.exists():raise ValueError('Fresh scratch required')
db=sqlite3.connect(dbpath)
geos,totals,count=m.measure_changed(ids,features,versions,root/'data/cliopatria',chunks,helpers,db)
evidence=[]
for part in index['evidence_parts']:
 asset=root/'data/ownership-history'/part['path']
 if m.sha(asset)!=part['sha256']:raise ValueError('Evidence checksum mismatch')
 evidence.extend(m.load(asset))
original={}
for part in index['parts']:
 asset=root/'data/ownership-history'/part['path']
 if m.sha(asset)!=part['sha256']:raise ValueError('Interval checksum mismatch')
 for id,rows in m.load(asset):
  if id not in ids:continue
  semantic=[]
  for a,b,o,s,ei in rows:
   label,share,coverage,claims,records,dated=evidence[ei]
   semantic.append([a,b,index['owner_ids'][o] if o is not None else None,index['statuses_order'][s],{'owner_name':index['labels'][label] if label is not None else None,'share':share,'coverage':coverage,'candidates':[[index['owner_ids'][owner],amount] for owner,amount in claims],'source_record_ids':[index['source_ids'][i] for i in records],'footprint':'dated' if dated else 'reference'}])
  original[id]=semantic
computed={id:m.derive_location(id,geos[id],totals[id],versions[id],helpers,db) for id in sorted(ids)}
if computed!=original:raise ValueError('Baseline target ownership semantic reproduction mismatch')
proof={'version':1,'original_index_sha256':m.sha(root/'data/ownership-history/index.json'),'before_footprints_sha256':index['footprints_sha256'],'changed_ids':sorted(ids),'source_records_scanned':count,'original_before_values_exactly_reproduced':True,'target_intervals':{id:len(rows) for id,rows in original.items()},'computed':computed,'source_representation':'exact hash-pinned baseline prepared ClioPatria features, not raw upstream ZIP','installed':False,'published':False}
output.write_text(m.dump(proof)+'\n');db.close()
print(m.dump({k:v for k,v in proof.items() if k!='computed'}))
