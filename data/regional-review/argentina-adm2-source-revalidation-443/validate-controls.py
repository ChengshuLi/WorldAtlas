#!/usr/bin/env python3
"""Positive/negative controls for source extraction and polygon-overlay calculations."""
import csv,hashlib,json,pathlib
from shapely.geometry import box
ROOT=pathlib.Path(__file__).resolve().parents[3]
OWN=ROOT/'data/regional-review/argentina-adm2-source-revalidation-443'
PARENT=ROOT/'data/regional-review/regional-review-7cf674a63057d43f'
findings=OWN/'findings'; findings.mkdir(exist_ok=True)
with (PARENT/'findings/scoped-location-review.csv').open(encoding='utf-8',newline='') as f:
    ids={r['original_id'] for r in csv.DictReader(f) if r['location_id'].startswith('gb:ARG:ADM2:')}
features=json.load(open(OWN/'source/geoBoundaries-2020-scoped-214.geojson'))['features']
actual={f['properties']['shapeID'] for f in features}
assert len(ids)==214 and len(actual)==214 and actual==ids
positive={'method_id':'source-partition','kind':'positive-control','outcome':'passed','control':'Exact 214-ID positive roster round trip','expected_count':214,'observed_count':len(actual),'ids_sha256':hashlib.sha256(json.dumps(sorted(actual),separators=(',',':')).encode()).hexdigest()}
# Negative input control: deleting one scoped feature must fail the exact-set comparison.
bad=actual-{next(iter(actual))}
try: assert bad==ids
except AssertionError: rejected=True
else: rejected=False
assert rejected
negative={'method_id':'source-partition','kind':'negative-control','outcome':'passed','control':'Negative roster control rejects one missing scoped feature','mutated_count':len(bad),'expected_count':len(ids),'rejection_observed':rejected}
(findings/'source-partition-positive.json').write_text(json.dumps(positive,indent=2,sort_keys=True)+'\n')
(findings/'source-partition-negative.json').write_text(json.dumps(negative,indent=2,sort_keys=True)+'\n')
# Analytic positive: 2x2 polygon intersecting 1x2 has 2 square projected units.
a=box(0,0,2,2); b=box(1,0,3,2)
ratio=a.intersection(b).area/a.area
assert ratio==0.5
pos={'method_id':'polygon-overlay','kind':'positive-control','outcome':'passed','control':'Analytic equal-plane 50% overlap','expected_share':0.5,'observed_share':ratio}
# Negative: polygons sharing only a boundary have zero positive-area intersection.
c=box(0,0,1,1); d=box(1,0,2,1)
area=c.intersection(d).area
assert area==0
neg={'method_id':'polygon-overlay','kind':'negative-control','outcome':'passed','control':'Shared-edge negative control has zero intersected area','expected_area':0,'observed_area':area}
(findings/'polygon-overlay-positive.json').write_text(json.dumps(pos,indent=2,sort_keys=True)+'\n')
(findings/'polygon-overlay-negative.json').write_text(json.dumps(neg,indent=2,sort_keys=True)+'\n')
print(json.dumps({'source_positive':positive,'source_negative':negative,'overlay_positive':pos,'overlay_negative':neg},indent=2))
