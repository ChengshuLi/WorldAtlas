#!/usr/bin/env python3
"""Compare the 53-name candidate roster with SURS and GURS historical RPE evidence."""
import csv, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = pathlib.Path(__file__).resolve().parents[2] / 'regional-review-d282e62cf0209796'
BASELINE_COMMIT = '3042d1278e87dae00c26924c339e940c9fba240e'
feature_bytes = subprocess.run(['git','show',f'{BASELINE_COMMIT}:data/geography/part-22.json'],check=True,capture_output=True).stdout
features = json.loads(feature_bytes)['features']
atlas = {f.get('id') or f.get('properties',{}).get('id'):f for f in features}
src = json.loads((ROOT/'source/sistat-0214809S-2017-area.json').read_text(encoding='utf-8'))
history = json.loads((ROOT/'source/gurs-obcine-h-53-codes-2017.json').read_text(encoding='utf-8'))['features']
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
    dated_names={}
    for date in ('2017-01-01T00:00:00Z','2017-07-01T00:00:00Z'):
        matches=[]
        for feature in history:
            p=feature['properties']
            if str(int(r['current_GURS_code'])) != str(p['SIFRA']): continue
            start=p.get('DATUM_OD')
            end=p.get('DATUM_DO')
            if start and start <= date and (not end or end > date): matches.append((feature,p))
        assert len(matches)==1, f"expected one effective GURS history feature for {code} at {date}; got {len(matches)}"
        dated_names[date]=(matches[0][0],matches[0][1])
    name_jan=dated_names['2017-01-01T00:00:00Z'][1]['NAZIV']
    name_jul=dated_names['2017-07-01T00:00:00Z'][1]['NAZIV']
    ids_jan=dated_names['2017-01-01T00:00:00Z'][0]['id']
    ids_jul=dated_names['2017-07-01T00:00:00Z'][0]['id']
    out.append({
      'location_id':r['location_id'],'source_shape_id':r['source_shape_id'],'baseline_atlas_name':atlas[r['location_id']]['properties']['name'],
      'municipality_code':code,'atlas_2017_reference_name':r['atlas_name'],
      'candidate_packet_current_gurs_name':r['current_GURS_name'],
      'sistat_dimension_label_at_retrieval':official,
      'gurs_current_feature_date':current['DATUM_SYS'],
      'sistat_area_2017H1_km2':h1,'sistat_area_2017H2_km2':h2,
      '2017_entity_presence':'supported-by-2017-statistical-series',
      'gurs_official_name_2017_01_01':name_jan,'gurs_validity_2017_01_01_feature_id':ids_jan,
      'gurs_official_name_2017_07_01':name_jul,'gurs_validity_2017_07_01_feature_id':ids_jul,
      'official_names_same_at_both_2017_dates':name_jan==name_jul,
      'current_GURS_name_matches_2017':r['current_GURS_name']==name_jan==name_jul,
      'atlas_name_matches_official_2017_name':r['atlas_name']==name_jan==name_jul,
      '2017_official_name':'verified-from-GURS-OBCINE_H-effective-interval',
      'engineering_handoff':'For approved official-Slovene display policy, replace Atlas reference spelling with this dated official name; preserve stable ID and old source spelling as alias/provenance pending source-lineage review.' if r['atlas_name']!=name_jan or r['atlas_name']!=name_jul else 'no-name-difference-at-2017-reference-dates'
    })
with (ROOT/'2017-name-assessment.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=out[0].keys(),lineterminator='\n');w.writeheader();w.writerows(out)
summary={
 'method':'Join the exact 53 pinned candidate rows to SURS 0214809S 2017H1/H2 by code and to retained GURS OBCINE_H history by SIFRA; evaluate each half-open DATUM_OD/DATUM_DO interval at 2017-01-01 and 2017-07-01.',
 'baseline_commit':BASELINE_COMMIT,'baseline_geography_path':'data/geography/part-22.json','baseline_geography_sha256':__import__('hashlib').sha256(feature_bytes).hexdigest(),
 'candidate_count':len(rows),'unique_subject_count':len(set(ids)),'baseline_subjects_present_and_names_match':sum(1 for r in rows if atlas[r['location_id']]['properties'].get('name')==r['atlas_name']),
 'current_GURS_code_name_vintage_matches':len(out),'code_matches':len(out),'non_null_2017H1_H2_area_pairs':sum(1 for x in out if x['sistat_area_2017H1_km2'] is not None and x['sistat_area_2017H2_km2'] is not None),
 'gurs_history_feature_count_in_retained_response':len(history),
 'official_names_resolved_at_2017_01_01':sum(1 for x in out if x['gurs_official_name_2017_01_01']),
 'official_names_resolved_at_2017_07_01':sum(1 for x in out if x['gurs_official_name_2017_07_01']),
 'names_stable_between_2017_dates':sum(1 for x in out if x['official_names_same_at_both_2017_dates']),
 'current_GURS_names_match_2017_names':sum(1 for x in out if x['current_GURS_name_matches_2017']),
 'atlas_names_exactly_match_both_dates':sum(1 for x in out if x['atlas_name_matches_official_2017_name']),
 'atlas_names_differ_from_official_2017':sum(1 for x in out if not x['atlas_name_matches_official_2017_name']),
 'historical_name_unresolved':0,
 'name_corrections_proposed':sum(1 for x in out if not x['atlas_name_matches_official_2017_name']),
 'name_correction_proposals_are_core_edits':False,
 'engineering_handoffs':sum(1 for x in out if not x['atlas_name_matches_official_2017_name']),
 'limitation':'GURS historical municipality name/validity features resolve the two requested reference dates for all 53 codes. The dated register evidence does not determine the product locale/name policy, validate Atlas polygons, establish neighboring granularity, or authorize core edits; no correction is applied in this research packet.',
 'subjects_sha256_ordered_source_ids':ids
}
(ROOT/'reproduction-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='subjects_sha256_ordered_source_ids'},indent=2))
