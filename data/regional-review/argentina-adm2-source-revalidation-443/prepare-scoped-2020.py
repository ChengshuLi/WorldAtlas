#!/usr/bin/env python3
"""Partition the exact 214 issue-scoped features from the retained 2020 source."""
import csv,gzip,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[3]
OWN=ROOT/'data/regional-review/argentina-adm2-source-revalidation-443'
PARENT=ROOT/'data/regional-review/regional-review-7cf674a63057d43f'
archive=PARENT/'source/geoBoundaries-ARG/geoBoundaries-ARG-ADM2.geojson.gz'
expected_archive_sha='aaf34413713c3b75175d04b6b7cafa4910ebdca762d2637a6547024466e3e07e'
expected_raw_sha='f35dae5a257302dea5bd1549ae135baf82e7ee7491918854c3db9bbdec890177'
raw_bytes=gzip.decompress(archive.read_bytes())
assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected_archive_sha
assert hashlib.sha256(raw_bytes).hexdigest()==expected_raw_sha
full=json.loads(raw_bytes)
assert len(full['features'])==525
with (PARENT/'findings/scoped-location-review.csv').open(encoding='utf-8',newline='') as f:
    scope={r['original_id'] for r in csv.DictReader(f) if r['location_id'].startswith('gb:ARG:ADM2:')}
assert len(scope)==214
by_id={ft['properties']['shapeID']:ft for ft in full['features']}
assert len(by_id)==525 and scope<=set(by_id)
result={'type':'FeatureCollection','name':'geoBoundaries 2020 ARG ADM2 scoped 214','features':[by_id[x] for x in sorted(scope)]}
out=OWN/'source/geoBoundaries-2020-scoped-214.geojson'
data=(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
if out.exists(): assert out.read_bytes()==data, 'Refusing to replace a different retained partition'
else: out.write_bytes(data)
summary={'archive_sha256':expected_archive_sha,'restored_sha256':expected_raw_sha,
 'restored_bytes':len(raw_bytes),'national_features':len(by_id),'scoped_features':len(result['features']),
 'partition_sha256':hashlib.sha256(data).hexdigest(),'partition_bytes':len(data)}
(OWN/'findings/source-partition-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
