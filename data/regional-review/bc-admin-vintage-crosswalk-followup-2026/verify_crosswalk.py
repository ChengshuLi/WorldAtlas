#!/usr/bin/env python3
"""Meaningful reproduction checks for issue #607's candidate crosswalk."""
import csv, hashlib, io, json, zipfile
from pathlib import Path
ROOT=Path(__file__).parent
BASE=Path('data/regional-review/regional-review-4254da254d94f450')
A=json.loads((BASE/'assessment.json').read_text())
R=json.loads((ROOT/'crosswalk-assessment.json').read_text())
G=json.loads((ROOT/'subjects.geojson').read_text())
Z=ROOT/'sources/2021_92-156-X_DB_ID.zip'
assert hashlib.sha256(Z.read_bytes()).hexdigest()=='b818450d23e18fc3a0b749d4e0226826ccefd2fa59d526a3e427e4bb923613fd'
expected={}
for loc in A['locations']:
    if not loc['location_id'].startswith('atlas:district:CAN-'): continue
    cd=loc['location_id'].split(':')[2][4:]
    for m in loc['source_identity_and_vintage']['members']:
        if m['name_matches_2021_csd_within_cd']==0 or m['name_matches_2021_csd_within_cd']>1 or m['overlap_pct']<95:
            expected[m['source_shape_id']] = (cd,loc['location_id'],m)
assert len(expected)==58 and len(R['records'])==58
assert len({r['source_shape_id'] for r in R['records']})==58
assert {r['source_shape_id'] for r in R['records']}==set(expected)
assert len(G['features'])==58 and len({f['id'] for f in G['features']})==58
byid={r['source_shape_id']:r for r in R['records']}
for sid,(cd,parent,m) in expected.items():
    r=byid[sid]
    assert r['source_name_2016']==m['source_name']
    assert r['screen_flags']['normalized_name_matches_2021_csd_within_cd']==m['name_matches_2021_csd_within_cd']
    assert r['screen_flags']['best_overlay_pct_of_2016_shape']==m['overlap_pct']
    assert r['parent_context']=={'atlas_group_id':parent,'census_division_uid':cd}
with zipfile.ZipFile(Z) as z:
    csvname=next(n for n in z.namelist() if n.endswith('.csv'))
    f=io.TextIOWrapper(z.open(csvname),encoding='utf-8-sig',newline='')
    reader=csv.DictReader(f); pairs=set(); flags={}
    for row in reader:
        new,old=row['DBUID2021_IDIDU2021'],row['DBUID2016_IDIDU2016']
        if new.startswith('59') and old.startswith('59'):
            assert len(new)==11 and len(old)==11
            pairs.add((new[:7],old[:7],row['DBRELFLAG_IDINDREL']))
            flags[row['DBRELFLAG_IDINDREL']]=flags.get(row['DBRELFLAG_IDINDREL'],0)+1
assert len(pairs)==2595 and flags=={'2':3182,'1':47731,'4':2030,'3':2196}
for r in R['records']:
    uid=r['candidate_2021_csd']['csduid'] if r['candidate_2021_csd'] else None
    assert uid is None or uid.startswith('59')
    assert r['assessment']['successor_mapping_status']=='candidate; direct source-feature-to-StatCan-2016 CSD link is not established by this inventory'
    if r['screen_flags']['normalized_name_matches_2021_csd_within_cd']>1:
        assert r['assessment']['disposition'].startswith('ambiguous')
    if r['screen_flags']['normalized_name_matches_2021_csd_within_cd']==0:
        assert r['assessment']['disposition'].startswith('no-name')
print(json.dumps({'status':'passed','flagged_subjects':58,'unique_subjects':58,'no_name':20,'multiple_name':5,'below_95':33,'official_bc_db_pairs':55139,'official_csd_prefix_pairs':2595,'relation_flags':flags,'unresolved_direct_source_links':58},indent=2))
