"""Read-only verification of the retained macro source pack; no live imports."""
from pathlib import Path
import json,gzip,hashlib,struct,tarfile
from shapely import from_wkb
from shapely.geometry import shape

D=Path(__file__).resolve().parents[1]
R=D.parents[2]
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest=json.loads((D/'manifest.json').read_bytes())
for f in manifest['files']:
 b=(D/f['path']).read_bytes()
 assert len(b)==f['bytes'] and sha(b)==f['sha256'], f['path']
with tarfile.open(D/'wikipedia-pages.tar.gz') as archive:
 wiki=json.loads((D/'gazetteer-source-inventory.json').read_bytes())
 for source in wiki:
  if source.get('status')!=200:continue
  b=archive.extractfile(source['path']).read()
  assert len(b)==source['bytes'] and sha(b)==source['sha256']
with tarfile.open(D/'geonames-country-dumps.tar.gz') as archive:
 inventories=json.loads((D/'geonames-source-inventory.json').read_bytes())+json.loads((D/'geonames-source-inventory-extra.json').read_bytes())
 for source in inventories:
  if source.get('status')!=200:continue
  b=archive.extractfile(source['file']).read()
  assert len(b)==source['bytes'] and sha(b)==source['sha256']
geofabrik=json.loads((D/'osm-geofabrik-source.json').read_bytes())
assert sha((D/'osm/greenland-latest.osm.pbf').read_bytes())==geofabrik['sha256']
for source in json.loads((D/'osm-source-inventory.json').read_bytes()):
 if source.get('status')==200:
  b=gzip.decompress((D/'osm/inaccessible.json.gz').read_bytes())
  assert len(b)==source['bytes'] and sha(b)==source['sha256']
report=json.loads((D/'report.json').read_bytes())
expected=json.loads((R/'data/macro-foundation/approved-boundary-decisions.json').read_bytes())
units={g['id']:g for g in expected['groups']}
original=[]
for r in expected['named_land_routing']:
 g=units[r['region_id']]
 while g.get('parent_id'):g=units[g['parent_id']]
 if g.get('current_name',g.get('name')) in ('Africa','North America','South America'):original.append(r)
assert len(report['entries'])==25 and {r['name'] for r in report['entries']}=={r['name'] for r in original}
assert all(next(r for r in original if r['name']==e['name'])['region_id']==e['region_id'] for e in report['entries'])
assert report['input_pins']['approved_decisions_sha256']==sha((R/'data/macro-foundation/approved-boundary-decisions.json').read_bytes())
assert report['input_pins']['macro_certificate_sha256']==sha((R/'data/macro-foundation/macro-certificate.json').read_bytes())
assert report['input_pins']['envelope_index_sha256']==sha((R/'data/macro-foundation/envelopes-v3/envelope-index.json').read_bytes())
counts=[]
for prefix,indexfile,lev in [('selected-gshhg-source-records','source-record-index.json.gz',1),('selected-gshhg-water-records','water-record-index.json.gz',2)]:
 raw=(D/(prefix+'.bin.gz')).read_bytes();data=gzip.decompress(raw);index=json.loads(gzip.decompress((D/indexfile).read_bytes()))
 assert sha(raw)==index['record_pack_sha256']
 seen=set();last=0
 for row in index['records']:
  assert row['pack_offset']==last
  b=data[last:last+row['source_bytes']];v=struct.unpack('>11i',b[:44])
  assert v[0]==row['id'] and v[0] not in seen and (v[2]&255)==lev
  assert len(b)==44+v[1]*8==row['source_bytes'] and sha(b)==row['sha256']
  seen.add(v[0]);last+=len(b)
 assert last==len(data)
 counts.append(len(seen))
components=json.loads(gzip.decompress((D/'components-dry-land.json.gz').read_bytes()))['components']
assert len(components)==35902 and len({c['gshhg_id'] for c in components})==33753
assert counts==[33753,393]
assert all(c['dry_land_area_km2']>=0 for c in components)
assert all(not c['dry_land_majority_region'] or 0<=c['dry_land_majority_region']['share']<=1 for c in components)
grl_raw=gzip.decompress((D/'original-grl-adm1-source.geojson.gz').read_bytes())
grli=json.loads((D/'original-grl-adm1-source-inventory.json').read_bytes())
assert sha(grl_raw)==grli['sha256'] and len(grl_raw)==grli['bytes']
original_grl_units=[shape(f['geometry']) for f in json.loads(grl_raw)['features']]
for name in ('disko','milne-land'):
 g=from_wkb(gzip.decompress((D/'osm'/(name+'-footprint.wkb.gz')).read_bytes()))
 assert not any(g.intersection(unit).area>0 for unit in original_grl_units)
osm=json.loads((D/'osm-correspondence.json').read_bytes());ei=json.loads((R/'data/macro-foundation/envelopes-v3/envelope-index.json').read_bytes())
regions=[from_wkb(gzip.decompress((R/'data/macro-foundation/envelopes-v3'/r['path']).read_bytes())) for r in ei['groups'] if r['level']=='region']
for r in osm['results']:
 assert r['status']=='missing-footprint-independently-confirmed'
 name=r['name'].split(' / ')[0].lower().replace(' ','-');g=from_wkb(gzip.decompress((D/'osm'/(name+'-footprint.wkb.gz')).read_bytes()))
 assert g.is_valid and not g.is_empty and g.area>0 and sha(g.wkb)==r['footprint_sha256']
 assert not any(g.intersection(e).area>0 for e in regions)
assert len(osm['results'])==3
assert not report['hierarchy_mutated'] and not report['published_geography_mutated'] and not report['source_coverage_complete']
print(json.dumps({'ok':True,'source_files':len(manifest['files']),'original_routes':25,'source_rows':len(components),'source_coastal_records':counts[0],'source_water_records':counts[1],'confirmed_current_missing_footprints':3,'geography_mutated':False}))
