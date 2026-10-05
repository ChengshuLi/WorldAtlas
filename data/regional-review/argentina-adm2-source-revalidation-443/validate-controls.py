#!/usr/bin/env python3
"""Positive/negative controls for source extraction and polygon-overlay calculations."""
import csv,hashlib,json,pathlib,math
from shapely.geometry import box
from pyproj import Transformer
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
# EPSG:6933 is the ellipsoidal Lambert Cylindrical Equal Area CRS with standard
# parallel 30 degrees and easting/northing output. See https://epsg.io/6933.
# This independent ellipsoidal formula gives a non-symmetric lon/lat transform control.
a=6378137.0
inverse_flattening=298.257223563
flattening=1.0/inverse_flattening
eccentricity_squared=flattening*(2-flattening)
eccentricity=math.sqrt(eccentricity_squared)
longitude=math.radians(10.0)
latitude=math.radians(20.0)
standard_parallel=math.radians(30.0)
def authalic_q(phi):
    sine=math.sin(phi)
    return (1-eccentricity_squared)*(sine/(1-eccentricity_squared*sine*sine)-math.log((1-eccentricity*sine)/(1+eccentricity*sine))/(2*eccentricity))
m=math.cos(standard_parallel)/math.sqrt(1-eccentricity_squared*math.sin(standard_parallel)**2)
expected_x=a*m*longitude
expected_y=a*authalic_q(latitude)/(2*m)
project=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True)
observed_x,observed_y=project.transform(10.0,20.0)
assert abs(observed_x-expected_x)<0.001 and abs(observed_y-expected_y)<0.001
pos={'method_id':'polygon-overlay','kind':'positive-control','outcome':'passed','control':'Asymmetric longitude/latitude to EPSG:6933 coordinates match independent ellipsoidal formula','input_longitude':10.0,'input_latitude':20.0,'expected_easting_m':expected_x,'observed_easting_m':observed_x,'expected_northing_m':expected_y,'observed_northing_m':observed_y}
# Axis-order negative: feeding (latitude,longitude) to the always-XY transform must
# produce a materially different point, so the swapped-axis regression cannot pass.
swapped_x,swapped_y=project.transform(20.0,10.0)
axis_separation=math.hypot(swapped_x-expected_x,swapped_y-expected_y)
assert axis_separation>100000
neg={'method_id':'polygon-overlay','kind':'negative-control','outcome':'passed','control':'Shared-edge area is zero and swapped longitude/latitude axes are rejected','expected_shared_edge_area':0,'observed_shared_edge_area':0.0,'swapped_axis_easting_m':swapped_x,'swapped_axis_northing_m':swapped_y,'swapped_axis_separation_m':axis_separation,'axis_order_mutation_rejected':True}
# Analytic polygon positive: 2x2 polygon intersecting 1x2 has 2 square projected units.
a=box(0,0,2,2); b=box(1,0,3,2)
ratio=a.intersection(b).area/a.area
assert ratio==0.5
# Negative: polygons sharing only a boundary have zero positive-area intersection.
c=box(0,0,1,1); d=box(1,0,2,1)
area=c.intersection(d).area
assert area==0
pos.update({'analytic_overlap_expected_share':0.5,'analytic_overlap_observed_share':ratio})
neg.update({'expected_area':0,'observed_area':area})
(findings/'polygon-overlay-positive.json').write_text(json.dumps(pos,indent=2,sort_keys=True)+'\n')
(findings/'polygon-overlay-negative.json').write_text(json.dumps(neg,indent=2,sort_keys=True)+'\n')
print(json.dumps({'source_positive':positive,'source_negative':negative,'overlay_positive':pos,'overlay_negative':neg},indent=2))
