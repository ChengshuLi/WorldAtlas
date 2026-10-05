#!/usr/bin/env python3
"""Compare the pinned 53-name candidate roster with SURS table 0214809S at 2017H1/H2.

The API payload's municipality labels are a static dimension, not archived names by
half-year. The script therefore reports temporal compatibility and preserves that
limitation rather than treating current dimension labels as historical proof.
"""
import csv, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = pathlib.Path(__file__).resolve().parents[2] / 'regional-review-d282e62cf0209796'
BASELINE_COMMIT = '3042d1278e87dae00c26924c339e940c9fba240e'
feature_bytes = subprocess.run(['git','show',f'{BASELINE_COMMIT}:data/geography/part-22.json'],check=True,capture_output=True).stdout
features = json.loads(feature_bytes)['features']
atlas = {f.get('id') or f.get('properties',{}).get('id'):f for f in features}
src = json.loads((ROOT/'source/sistat-0214809S-2017-area.json').read_text(encoding='utf-8'))
gurs_path = BASE/'source/gurs-municipal-boundaries.geojson'
gurs = json.loads(gurs_path.read_text(encoding='utf-8'))
gurs_by_code = {str(f['properties']['SIFRA']).zfill(3):f['properties'] for f in gurs['features']}
rows = list(csv.DictReader((BASE/'slovenia-name-correction-candidates.csv').open(encoding='utf-8-sig', newline='')))
ids = [r['location_id'] for r in rows]
assert len(rows) == 53 and len(set(ids)) == 53, f'expected 53 unique candidates; got {len(rows)}'
assert all(r['location_id'] == 'gb:SVN:ADM2:'+r['source_shape_id'] for r in rows)
assert all(r['location_id'] in atlas for r in rows), 'candidate absent from baseline geography part-22'
assert all(atlas[r['location_id']]['properties'].get('name') == r['atlas_name'] for r in rows), 'candidate Atlas name differs from pinned geography baseline'
assert src['size'] == [213, 2, 1]
assert src['id'] == ['OBČINE','POLLETJE','MERITVE']
assert src['dimension']['POLLETJE']['category']['index'] == {'2017H1':0,'2017H2':1}
assert src['dimension']['MERITVE']['category']['label']['1'] == 'Area [sq. km]'
idx = src['dimension']['OBČINE']['category']['index']
labels = src['dimension']['OBČINE']['category']['label']
values = src['value']
assert len(values) == 213*2
out=[]
for r in rows:
    code = str(int(r['current_GURS_code'])).zfill(3)
    assert code in idx, f"GURS municipality code {code} absent from SURS dimension for {r['location_id']}"
    i=idx[code]
    h1,h2=values[i*2:i*2+2]
    assert h1 is not None and h2 is not None, f"missing 2017 area for {code} {r['location_id']}"
    current=gurs_by_code[code]
    assert current['NAZIV'] == r['current_GURS_name'], f"current GURS name mismatch for {code}"
    assert str(current['DATUM_SYS']) == r['GURS_feature_date'], f"current GURS vintage mismatch for {code}"
    official=labels[code]
    out.append({
      'location_id':r['location_id'],'source_shape_id':r['source_shape_id'],'baseline_atlas_name':atlas[r['location_id']]['properties']['name'],
      'municipality_code':code,'atlas_2017_reference_name':r['atlas_name'],
      'candidate_packet_current_gurs_name':r['current_GURS_name'],
      'sistat_dimension_label_at_retrieval':official,
      'gurs_current_feature_date':current['DATUM_SYS'],
      'sistat_area_2017H1_km2':h1,'sistat_area_2017H2_km2':h2,
      '2017_entity_presence':'supported-by-2017-statistical-series',
      '2017_official_name':'unresolved-static-dimension-is-not-time-vintaged',
      'name_correction':'not-proposed-pending-dated-RPE-register-record'
    })
with (ROOT/'2017-name-assessment.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=out[0].keys(),lineterminator='\n');w.writeheader();w.writerows(out)
summary={
 'method':'Join the 53 pinned candidate rows to the SURS 0214809S 2017H1/H2 municipality-code dimension; reproduce existence from non-null municipality area cells and retain SURS labels as non-dated labels only.',
 'baseline_commit':BASELINE_COMMIT,'baseline_geography_path':'data/geography/part-22.json','baseline_geography_sha256':__import__('hashlib').sha256(feature_bytes).hexdigest(),
 'candidate_count':len(rows),'unique_subject_count':len(set(ids)),'baseline_subjects_present_and_names_match':sum(1 for r in rows if atlas[r['location_id']]['properties'].get('name')==r['atlas_name']),
 'current_GURS_code_name_vintage_matches':len(out),'code_matches':len(out),'non_null_2017H1_H2_area_pairs':sum(1 for x in out if x['sistat_area_2017H1_km2'] is not None and x['sistat_area_2017H2_km2'] is not None),
 'historical_name_confirmed':0,'historical_name_unresolved':len(out),
 'name_corrections_proposed':0,
 'limitation':'The SURS table reports a half-year time series for area/territorial counts but uses one static municipality label per code; neither those labels nor the 2017 national count article independently establishes each official name effective on the Atlas 2017 reference date.',
 'subjects_sha256_ordered_source_ids':ids
}
(ROOT/'reproduction-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='subjects_sha256_ordered_source_ids'},indent=2))
