#!/usr/bin/env python3
"""Reproduce packet scope, hashes, parent-chain closure, and frozen-envelope checks."""
import gzip, hashlib, json, sys
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.wkb import loads

out=Path(__file__).resolve().parent
repo=out.parents[2]
issue=json.loads((out/'issue-metadata.json').read_text())
base=json.loads((out/'baseline-extract.json').read_text())
assessment=json.loads((out/'assessment.json').read_text())
manifest=json.loads((out/'sources-manifest.json').read_text())
expected=set(json.loads(issue['body'].split('```json\n',1)[1].split('\n```',1)[0])['member_location_ids'])
actual=set(base['scope_location_ids'])
assert actual==expected, (actual,expected)
assert set(base['complete_parent_chains'])==expected
for ident,chain in base['complete_parent_chains'].items():
 assert chain[0]['id']==ident and chain[-1]['id']=='framework:continent:oceania:48580dd0c4b4'
 assert all(chain[n]['parent_id']==chain[n+1]['id'] for n in range(len(chain)-1))
assert len(assessment['location_assessments'])==3
assert len(assessment['province_assessments'])==3
assert len(assessment['area_assessments'])==2
for x in manifest['retained_sources']:
 p=out/x['path']; b=p.read_bytes()
 assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256'], x['path']
for x in base['baseline_files']:
 p=repo/x['path']; b=p.read_bytes()
 assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256'], x['path']
envmeta=base['region']['envelope']; ep=repo/'data/macro-foundation/envelopes-v5'/envmeta['path']; raw=ep.read_bytes()
assert hashlib.sha256(raw).hexdigest()==envmeta['sha256']
env=loads(gzip.decompress(raw))
locs=[shape(base['locations'][i]['geometry']) for i in sorted(expected)]
u=unary_union(locs)
assert env.equals(u) and env.symmetric_difference(u).area==0
kir=json.loads((out/'sources/geoBoundaries-KIR-ADM1.geojson').read_text())
nru=json.loads((out/'sources/geoBoundaries-NRU-ADM1.geojson').read_text())
assert len(kir['features'])==3 and len(nru['features'])==14
screen=json.loads((out/'gshhg-land-screen.json').read_text())
assert screen['source']['candidate_land_records_in_declared_windows']==243
assert screen['source']['candidate_land_records_intersecting_any_assigned_location']==22
assert len(screen['candidate_land_features_intersecting_assigned_locations'])==22
print(json.dumps({'status':'PASS','exact_locations':sorted(expected),'complete_parent_chains':len(base['complete_parent_chains']),'province_assessments':3,'area_assessments':2,'retained_source_hashes':len(manifest['retained_sources']),'baseline_file_hashes':len(base['baseline_files']),'KIR_source_features':len(kir['features']),'NRU_district_features':len(nru['features']),'GSHHG_window_candidates':243,'GSHHG_positive_overlap_records':22,'frozen_envelope_equals_bottom_up_union':True},indent=2))
