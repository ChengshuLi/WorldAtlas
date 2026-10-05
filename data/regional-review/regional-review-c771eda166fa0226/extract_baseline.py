#!/usr/bin/env python3
"""Rebuild #471's scoped features and parent chains from immutable main."""
import csv, gzip, hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OWN=Path(__file__).resolve().parent
COMMIT='7ffd4e35364ec8246b9add7459378b3f971fcd72'

def blob(path):
    return subprocess.check_output(['git','-C',str(ROOT),'show',f'{COMMIT}:{path}'])

def sha(b): return hashlib.sha256(b).hexdigest()
def canon(x): return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def geometry_stats(g):
    if not g: return {'type':None,'parts':0,'vertices':0,'bbox':None}
    typ=g.get('type'); coords=g.get('coordinates') or []
    polygons=[coords] if typ=='Polygon' else coords if typ=='MultiPolygon' else []
    vertices=[p for poly in polygons for ring in poly for p in ring]
    return {'type':typ,'parts':len(polygons),'vertices':len(vertices),
            'bbox':[min(p[0] for p in vertices),min(p[1] for p in vertices),max(p[0] for p in vertices),max(p[1] for p in vertices)] if vertices else None}

scope=json.loads((OWN/'issue-scope-pinned.json').read_text())
ids=scope['member_location_ids']
assert len(ids)==216 and len(set(ids))==216
idxraw=blob('data/world-index.json'); idx=json.loads(idxraw)
selected=set(ids); wanted=set(ids); byid={}; containing={}; read_receipts=[]
# The fixed main index names every source part; scan each to establish real feature identity/path.
for rel in idx['parts']:
    path='data/'+rel
    raw=blob(path)
    read_receipts.append({'path':path,'bytes':len(raw),'sha256':sha(raw)})
    data=json.loads(raw)
    for f in data.get('features',[]):
        p=f.get('properties') or {}; fid=f.get('id') or p.get('id')
        if fid in wanted:
            if fid in byid: raise SystemExit('duplicate subject '+fid)
            byid[fid]=f; containing[fid]=path
assert set(byid)==selected, 'missing ids '+repr(sorted(selected-set(byid)))
# Parent tiers are nonspatial records in the separately pinned hierarchy file.
hierraw=blob('data/hierarchy.json'); hier=json.loads(hierraw)
nodes={x['id']:x for x in hier}
if len(nodes)!=len(hier): raise SystemExit('duplicate hierarchy IDs')
parent_ids=set()
for sid in sorted(ids):
    cur=(byid[sid].get('properties') or {}).get('parent_id'); seen={sid}
    while cur:
        if cur in seen: raise SystemExit('parent cycle '+sid)
        seen.add(cur); node=nodes.get(cur)
        if not node: raise SystemExit('missing hierarchy parent '+cur+' for '+sid)
        parent_ids.add(cur); cur=node.get('parent_id')
raw_members=canon({'type':'FeatureCollection','features':[byid[x] for x in sorted(ids)]})
with open(OWN/'baseline-members.geojson.gz','wb') as out:
    with gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0,compresslevel=9) as z: z.write(raw_members)
raw_context=canon({'version':1,'baseline_commit':COMMIT,'parents':[nodes[x] for x in sorted(parent_ids)]})
(OWN/'baseline-parent-context.json').write_bytes(raw_context)
# Extract lineage paths, stop only at roots and fail if an issue's recorded parent is absent.
rows=[]
for sid in sorted(ids):
    f=byid[sid]; p=f.get('properties') or {}; md=p.get('metadata') or {}
    chain=[]; cur=sid; seen=set()
    while cur:
        if cur in seen: raise SystemExit('parent cycle '+sid)
        seen.add(cur)
        if cur==sid: ap=p; am=md; anc=f
        else: anc=nodes[cur]; ap=anc; am=anc.get('metadata') or {}
        chain.append({'id':cur,'level':ap.get('level') or 'location','name':ap.get('name'),'parent_id':ap.get('parent_id'),
                      'source_id':am.get('source_id'),'source_role':am.get('source_role'),
                      'source_url':am.get('source_url'),'source_vintage':am.get('reference_year'),
                      'source_license':am.get('license'),'source_level':am.get('administrative_level'),
                      'source_parent_level':am.get('parent_source_level'),
                      'source_original_id':am.get('original_id'),
                      'area_code':am.get('geographic_area_code'),'region_code':am.get('geographic_region_code'),
                      'semantic_status':((am.get('semantic_review') or ap.get('semantic_review') or {}).get('status')),
                      'geometry':geometry_stats(anc.get('geometry')) if cur==sid else None})
        cur=ap.get('parent_id')
    rows.append({'id':sid,'name':p.get('name'),'parent_id':p.get('parent_id'),'reference_owner':p.get('reference_owner'),
                 'source_id':md.get('source_id'),'source_name':md.get('source_name'),'source_url':md.get('source_url'),
                 'source_role':md.get('source_role'),'source_vintage':md.get('reference_year'),
                 'source_license':md.get('license'),'source_level':md.get('administrative_level'),
                 'source_parent_level':md.get('parent_source_level'),'original_source_id':md.get('original_id'),
                 'parent_match':md.get('parent_match'),'selection_reason':md.get('selection_reason'),
                 'semantic_status':((md.get('semantic_review') or p.get('semantic_review') or {}).get('status')),
                 'geometry':geometry_stats(f.get('geometry')),'ancestry':chain})
# Write row-level audit products.
with open(OWN/'baseline-feature-inventory.csv','w',newline='') as stream:
    cols=['id','name','parent_id','reference_owner','source_id','source_name','source_url','source_role','source_vintage','source_license','source_level','source_parent_level','original_source_id','parent_match','selection_reason','semantic_status','geometry_type','geometry_parts','geometry_vertices','bbox']
    w=csv.DictWriter(stream,fieldnames=cols); w.writeheader()
    for r in rows:
        w.writerow({**{k:r.get(k) for k in cols if not k.startswith('geometry_')},
                    'geometry_type':r['geometry']['type'],'geometry_parts':r['geometry']['parts'],
                    'geometry_vertices':r['geometry']['vertices'],'bbox':json.dumps(r['geometry']['bbox'])})
(OWN/'baseline-source-lineage.json').write_bytes(canon({'version':1,'baseline_commit':COMMIT,'subjects':rows}))
# Output paths used for each subject and all retained hashes needed to reconstruct the scan.
used_paths=sorted(set(containing.values()))
used=[r for r in read_receipts if r['path'] in used_paths]
base={'version':1,'issue':471,'baseline_commit':COMMIT,'world_index':{'path':'data/world-index.json','bytes':len(idxraw),'sha256':sha(idxraw)},
      'hierarchy':{'path':'data/hierarchy.json','bytes':len(hierraw),'sha256':sha(hierraw)},
      'scanned_parts':read_receipts,'subject_files':{k:containing[k] for k in sorted(ids)},
      'subject_count':len(ids),'ancestor_count':len(parent_ids),
      'issue_pins':{'region_release':'geography:review:df86cbaeaf2e18f16ddf2906ef089768baac22f4428e28ed0a4724296cbb413e','hierarchy_sha256':'03d23534f87cdd0582bcb228780f00f65090bec2e8a760acbab528383f28549d','footprints_sha256':'2ac42eeb9fef8af923a0d4c4e55af49ca0a103de891ffbfb2c1181ad75950286','macro_certificate_sha256':'979afaf22e10dc936ecfe80a8cd288b2ef33d8c7bf509aba9fae4255e3d94d6e','frozen_region_geometry_sha256':scope['frozen_region_geometry_sha256'],'frozen_region_member_ids_sha256':scope['frozen_region_member_ids_sha256']},
      'extracted_members':{'path':'data/regional-review/regional-review-c771eda166fa0226/baseline-members.geojson.gz','compressed_bytes':(OWN/'baseline-members.geojson.gz').stat().st_size,'compressed_sha256':sha((OWN/'baseline-members.geojson.gz').read_bytes()),'uncompressed_bytes':len(raw_members),'uncompressed_sha256':sha(raw_members)},
      'extracted_parent_context':{'path':'data/regional-review/regional-review-c771eda166fa0226/baseline-parent-context.json','bytes':len(raw_context),'sha256':sha(raw_context)}}
(OWN/'baseline-receipt.json').write_bytes(canon(base))
print(json.dumps({'subjects':len(rows),'ancestors':len(parent_ids),'subject_files':used_paths,'extracted_gzip_bytes':(OWN/'baseline-members.geojson.gz').stat().st_size,'parent_context_bytes':len(raw_context)},indent=2))
