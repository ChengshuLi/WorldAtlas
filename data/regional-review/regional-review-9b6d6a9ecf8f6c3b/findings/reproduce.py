#!/usr/bin/env python3
"""Reproduce exact scope, source-hash, name-linkage, and recorded geometry-screen checks.
This does not test legal or positional boundary correctness.
"""
import csv, gzip, hashlib, json, argparse, tempfile, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]
scope=json.loads((ROOT/'scope/embedded-workload-scope.json').read_text())
ids=scope['member_location_ids']
assert len(ids)==scope['location_count']==215 and len(set(ids))==215
assert hashlib.sha256('\n'.join(ids).encode()).hexdigest()==scope['member_location_ids_sha256']
found={}
for n in (2,20,28):
 data=json.loads((REPO/f'data/geography/part-{n}.json').read_text())
 for feature in data['features']:
  fid=feature['properties']['id']
  if fid in ids:
   assert fid not in found
   found[fid]=feature
assert set(found)==set(ids)
parents={f['properties'].get('parent_id') for f in found.values()}
assert len(parents)==39
rows=list(csv.DictReader((ROOT/'findings/crosswalk.csv').open(encoding='utf8')))
assert len(rows)==215 and {r['location_id'] for r in rows}==set(ids)
assert sum(r['source_id']=='gb:CHL:ADM3' for r in rows)==167
assert sum(r['source_id']=='gb:PRY:ADM2' for r in rows)==47
assert sum(r['location_id']=='atlas:city:PRY-4837' for r in rows)==1
assert all(r['name_exact_match']=='True' for r in rows if r['source_id'] in ('gb:CHL:ADM3','gb:PRY:ADM2'))
assert all(r['review_classification']=='insufficient-evidence' for r in rows)
provinces=list(csv.DictReader((ROOT/'findings/province-review.csv').open(encoding='utf8')))
areas=list(csv.DictReader((ROOT/'findings/area-review.csv').open(encoding='utf8')))
assert len(provinces)==len(scope['province_scopes'])==39 and all(p['classification']=='insufficient-evidence' for p in provinces)
assert len(areas)==len(scope['area_scopes'])==5 and all(a['classification']=='insufficient-evidence' for a in areas)
assert all(r['ine_2022_name'] and r['ine_2022_district_code'] and r['ine_2022_parent'] for r in rows if r['source_id']=='gb:PRY:ADM2')
register=json.loads((ROOT/'source/source-register.json').read_text())
meta_hashes={'CHL':'658356bb413f8b284b260360d1309527781e1b0c46027e1ae0a4c58da1c99409','PRY':'d78f4e8a966cf3b077e62a33e8544e8c4bc08aab269da52f3b8d3602875851aa'}
for country, digest in meta_hashes.items():
 raw=(ROOT/f'source/geoBoundaries-{country}-ADM{3 if country=="CHL" else 2}-metaData.json').read_bytes()
 assert hashlib.sha256(raw).hexdigest()==digest
restoration=register['restoration_only_sources']
assert len([x for x in restoration if x.get('source_id','').startswith('gb:')])==2
parser=argparse.ArgumentParser();parser.add_argument('--restore-sources',action='store_true');args=parser.parse_args()
restored=0
if args.restore_sources:
 by_source={}
 for row in rows:
  if row['source_id'].startswith('gb:'): by_source.setdefault(row['source_id'],[]).append(row)
 for item in restoration:
  sid=item.get('source_id')
  if sid not in by_source: continue
  h=hashlib.sha256(); size=0
  with tempfile.NamedTemporaryFile() as tmp:
   request=urllib.request.Request(item['url'],headers={'User-Agent':'WorldAtlas evidence reproduction'})
   with urllib.request.urlopen(request,timeout=120) as response:
    while chunk:=response.read(1024*1024): h.update(chunk);size+=len(chunk);tmp.write(chunk)
   assert h.hexdigest()==item['original_sha256'] and size==item['original_size_bytes'],sid
   tmp.flush();source=json.load(open(tmp.name,encoding='utf8'))
  by_id={f['properties']['shapeID']:f for f in source['features']}
  for row in by_source[sid]:
   feature=by_id[row['source_shape_id']]
   assert feature['properties']['shapeName']==row['source_name']==row['name']
  restored+=1
print(json.dumps({'scope_ids':len(ids),'baseline_parts':[2,20,28],'baseline_matches':len(found),'distinct_parent_ids':len(parents),'chile_rows':167,'paraguay_rows':47,'asuncion_city_aggregate_rows':1,'exact_source_name_links':214,'paraguay_ine_2022_candidate_roster_matches':47,'individual_classifications':len(rows),'province_classifications':len(provinces),'area_reviews':len(areas),'retained_metadata_hashes_verified':2,'restoration_source_hashes_reverified':restored,'result':'identity/source/scope checks pass; legal and positional boundaries not validated'},indent=2))
