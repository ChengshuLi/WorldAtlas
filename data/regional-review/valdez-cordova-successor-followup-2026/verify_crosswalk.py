#!/usr/bin/env python3
"""Verify the official one-to-many event against retained records and negative controls."""
import csv, gzip, hashlib, html, json, platform, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).parent
BASE=Path('data/regional-review/regional-review-93f8f3bee8e205be')
SUBJECT='gb:USA:ADM2:52423323B16539688175930'
EXPECTED=['02063','02066']
def load(p):return json.loads(p.read_text())
def gzjson(p):
    with gzip.open(p,'rt',encoding='utf-8') as f:return json.load(f)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def successor_set_valid(values):return len(values)==2 and len(set(values))==2 and set(values)==set(EXPECTED)

def main():
    build=ROOT/'build_crosswalk.py'
    subprocess.run([sys.executable,str(build)],check=True)
    run_one=sha(ROOT/'successor-crosswalk.json')
    subprocess.run([sys.executable,str(build)],check=True)
    run_two=sha(ROOT/'successor-crosswalk.json')
    assert run_one==run_two
    packet=load(ROOT/'successor-crosswalk.json')
    baseline=load(BASE/'assessment.json')
    rows=[x for x in baseline['locations'] if x['location_id']==SUBJECT]
    assert len(rows)==1 and packet['subject']['id']==SUBJECT
    row=rows[0]
    with gzip.open(ROOT/'sources/census-2019-geography-changes.html.gz','rt',encoding='utf-8') as f: page=f.read()
    page_text=html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',page)))
    quote='Alaska has announced the split of 02261 Valdez-Cordova borough into two new census areas, 02063 Chugach and 02066 Copper River.'
    assert quote in page_text and packet['official_successor_event']['quoted_event']==quote
    with gzip.open(ROOT/'sources/census-ak-county-changes-2014-2020.txt.gz','rt',encoding='utf-8-sig',newline='') as f:
        events=list(csv.DictReader(f,delimiter='|'))
    selected=[]
    for code,name in [('063','Chugach Census Area'),('066','Copper River Census Area')]:
        hits=[e for e in events if e['Entity Code'].strip()==code and e['Entity Name'].strip()==name and e['Type of Change'].strip()=='New Entity']
        assert len(hits)==1
        assert hits[0]['Effective Date'].strip()=='01-02-2019'
        assert 'Valdez-Cordova Census Area (261)' in hits[0]['Description of Change']
        selected.append('02'+code)
    assert successor_set_valid(selected)
    # Negative controls: a wrong code, duplicated record or one-to-one mapping must not pass.
    negatives={'wrong_successor_code_rejected':not successor_set_valid(['02063','02064']),
               'duplicate_successor_rejected':not successor_set_valid(['02063','02063']),
               'one_to_one_alias_rejected':not successor_set_valid(['02066'])}
    assert all(negatives.values())
    tiger=gzjson(BASE/'sources/tigerline-2024-western-county-neighbors.geojson.gz')
    features={f['properties']['GEOID']:f['properties'] for f in tiger['features']}
    expected_names={'02063':'Chugach Census Area','02066':'Copper River Census Area'}
    for geoid,name in expected_names.items():
        p=features[geoid];assert p['NAMELSAD']==name and p['CLASSFP']=='H5'
    rosters=gzjson(BASE/'sources/current-scope-and-parents.geojson.gz')
    assert any((f.get('id') or f.get('properties',{}).get('id'))==SUBJECT for f in rosters['features'])
    over=packet['inherited_geometry_screen']['source_overlap_pct_by_2024_geoid']
    assert round(over['02063']+over['02066'],6)==99.947342
    assert round(sum(v for k,v in over.items() if k not in EXPECTED),6)==0.040571
    assert packet['location_review_context']['physical_land_screen']['current_polygon_components']==9
    assert packet['location_review_context']['settlement_screen']['2024_place_polygon_intersections']==28
    assert packet['location_review_context']['settlement_screen']['GNIS_populated_place_hits']==46
    assert len(packet['subject']['baseline_parent_chain'])==6
    report={'version':1,'method_id':'crosswalk-build','kind':'generator','outcome':'passed',
      'run_one_sha256':run_one,'run_two_sha256':run_two,
      'positive_control':{'description':'Both federal 2019 change sources identify the exact Valdez-Cordova predecessor and the two distinct new entities; each matches a 2024 TIGER GEOID/name/H5 record.','outcome':'passed'},
      'negative_controls':negatives,
      'checks':{'baseline_subject_count':len(rows),'successors':EXPECTED,'effective_date':'2019-01-02','parent_chain_nodes':6,
        'place_polygon_hits':28,'GNIS_populated_place_hits':46,'historical_geometry_ratio_pct_to_successor_pair':99.947342,
        'historical_geometry_ratio_pct_to_other_counties':0.040571},
      'inputs':{'census_page_gzip_sha256':sha(ROOT/'sources/census-2019-geography-changes.html.gz'),
        'change_table_gzip_sha256':sha(ROOT/'sources/census-ak-county-changes-2014-2020.txt.gz'),
        'successor_crosswalk_sha256':sha(ROOT/'successor-crosswalk.json')},
      'environment':{'python':platform.python_version()},
      'limitations':['These checks establish agreement among the retained official event records, Census successor identifiers, and inherited identity/screen data. They do not prove complete historical legal boundaries or political control.']}
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':'passed','successors':EXPECTED,'negative_controls':negatives,'validation_sha256':sha(ROOT/'validation.json')},indent=2))
if __name__=='__main__':main()
