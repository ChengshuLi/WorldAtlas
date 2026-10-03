#!/usr/bin/env python3
"""Extract only #485's exact current baseline features and parent-chain material."""
import gzip, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
scope=json.loads((ROOT/'scope.json').read_text())
ids=set(scope['member_location_ids'])
features={}
for part in json.loads((REPO/'data/world-index.json').read_text())['parts']:
    fc=json.loads((REPO/'data'/part).read_text())
    for f in fc['features']:
        fid=f.get('properties',{}).get('id')
        if fid in ids: features[fid]=f
missing=ids-set(features)
if missing: raise SystemExit(f'Missing {len(missing)} assigned features: {sorted(missing)[:5]}')
inventory=json.load(gzip.open(REPO/'data/macro-foundation/current-membership-inventory.json.gz','rt'))
units={r['id']:r for r in inventory}
hierarchy={r['id']:r for r in json.loads((REPO/'data/hierarchy.json').read_text())}
rows=[]
for fid in scope['member_location_ids']:
    f=features[fid]; chain=[f['properties']]; parent=f['properties'].get('parent_id'); seen={fid}
    while parent:
        if parent in seen: raise SystemExit(f'Parent cycle at {fid}')
        seen.add(parent)
        if parent not in units: raise SystemExit(f'Missing parent inventory record {parent} for {fid}')
        row=units[parent]; definition=hierarchy.get(parent,{})
        chain.append({'id':row['id'],'name':row['name'],'level':row['level'],'parent_id':row['parent_id'],'member_location_ids':row['member_location_ids'] if row['level'] in ('province','area') else None,'metadata':definition.get('metadata',{})})
        parent=row['parent_id']
    rows.append({'feature':f,'parent_chain':chain})
path=ROOT/'sources'/'current-scope-and-parents.geojson.gz'
payload={'type':'FeatureCollection','features':[r['feature'] for r in rows]}
raw=(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n').encode()
with gzip.open(path,'wb',compresslevel=9) as out: out.write(raw)
chain_path=ROOT/'sources'/'current-parent-chains.json.gz'
raw=(json.dumps([{'id':r['feature']['properties']['id'],'parent_chain':r['parent_chain']} for r in rows],ensure_ascii=False,separators=(',',':'))+'\n').encode()
with gzip.open(chain_path,'wb',compresslevel=9) as out: out.write(raw)
report={'scope_ids':len(ids),'features_saved':len(payload['features']),'chains_saved':len(rows),'feature_data':{'path':str(path.relative_to(ROOT)),'compressed_bytes':path.stat().st_size,'compressed_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'uncompressed_bytes':len(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()+b'\n'),'uncompressed_sha256':hashlib.sha256(raw if False else gzip.open(path,'rb').read()).hexdigest()},'chain_data':{'path':str(chain_path.relative_to(ROOT)),'compressed_bytes':chain_path.stat().st_size,'compressed_sha256':hashlib.sha256(chain_path.read_bytes()).hexdigest(),'uncompressed_bytes':len(gzip.open(chain_path,'rb').read()),'uncompressed_sha256':hashlib.sha256(gzip.open(chain_path,'rb').read()).hexdigest()}}
(ROOT/'baseline-extract-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
