#!/usr/bin/env python3
"""Build an evidence-only 2018-to-2024 Alaska county-equivalent crosswalk."""
import csv, gzip, hashlib, html, json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).parent
BASE = Path('data/regional-review/regional-review-93f8f3bee8e205be')
SUBJECT = 'gb:USA:ADM2:52423323B16539688175930'
OUT = ROOT / 'successor-crosswalk.json'
BASE_COMMIT = '276d72e1f316ad58d52c8fea7974a873c2ec9387'

def load(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def feature_collection(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f: return json.load(f)
def main():
    assessment = load(BASE / 'assessment.json')
    row = next(x for x in assessment['locations'] if x['location_id'] == SUBJECT)
    assert row['name'] == 'Valdez-Cordova' and row['state_fips'] == '02'
    state = assessment['complete_state_parent_cohorts']['Alaska']
    gb_path = 'data/regional-review/regional-review-93f8f3bee8e205be/sources/geoboundaries-USA-ADM2.geojson'
    gb_raw = subprocess.check_output(['git','show',f'{BASE_COMMIT}:{gb_path}'])
    gb = json.loads(gb_raw)
    source_feature = next(f for f in gb['features'] if f['properties'].get('shapeID') == '52423323B16539688175930')
    assert source_feature['properties']['shapeName'] == 'Valdez-Cordova' and source_feature['properties']['shapeType'] == 'ADM2'
    metadata_path = 'data/regional-review/regional-review-93f8f3bee8e205be/sources/geoboundaries-USA-ADM2-metadata.json'
    metadata = json.loads(subprocess.check_output(['git','show',f'{BASE_COMMIT}:{metadata_path}']))
    overlays = state['2018_source_to_2024_tiger_crosswalk']['52423323B16539688175930']
    text_path = ROOT / 'sources/census-ak-county-changes-2014-2020.txt'
    with text_path.open(encoding='utf-8-sig', newline='') as f:
        events = list(csv.DictReader(f, delimiter='|'))
    direct = []
    for code, expected_name in [('063','Chugach Census Area'),('066','Copper River Census Area')]:
        matches = [x for x in events if x['Entity Name'].strip() == expected_name and x['Entity Code'].strip() == code and x['Type of Change'].strip() == 'New Entity']
        assert len(matches) == 1, (expected_name, len(matches))
        e = matches[0]
        assert e['Effective Date'].strip() == '01-02-2019' and 'Valdez-Cordova Census Area (261)' in e['Description of Change']
        direct.append({'name': expected_name, 'state_fips': '02', 'county_fips': code, 'geoid': '02' + code,
            'effective_date': '2019-01-02', 'type': e['Type of Change'].strip(),
            'official_description': e['Description of Change'].strip(), 'source_of_change': e['Source of Change'].strip(),
            'date_submitted': e['Date Submitted'].strip(), 'ansi_code': e['ANSI Code'].strip()})
    with gzip.open(ROOT / 'sources/census-2019-geography-changes.html.gz', 'rt', encoding='utf-8') as f: page = f.read()
    page_text = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', page)))
    phrase = 'Alaska has announced the split of 02261 Valdez-Cordova borough into two new census areas, 02063 Chugach and 02066 Copper River.'
    assert phrase in page_text
    census_scope = feature_collection(BASE / 'sources/current-scope-and-parents.geojson.gz')
    feature = next(f for f in census_scope['features'] if (f.get('id') or f.get('properties',{}).get('id')) == SUBJECT)
    tiger = feature_collection(BASE / 'sources/tigerline-2024-western-county-neighbors.geojson.gz')
    targets = []
    for e in direct:
        f = next(f for f in tiger['features'] if f['properties']['GEOID'] == e['geoid'])
        p = f['properties']
        assert p['NAMELSAD'] == e['name'] and p['CLASSFP'] == 'H5'
        targets.append({'geoid': p['GEOID'], 'name': p['NAME'], 'namelsad': p['NAMELSAD'], 'classfp': p['CLASSFP'],
                        'aland_m2': int(p['ALAND']), 'awater_m2': int(p['AWATER']),
                        'identity_source': '2024 TIGER/Line county-equivalent candidate; not itself the transition authority'})
    byid = {x['geoid']: x for x in overlays}
    assert {x['geoid'] for x in overlays if x['geoid'] in {'02063','02066'}} == {'02063','02066'}
    successor_share = round(sum(byid[x]['source_intersection_pct'] for x in ('02063','02066')), 6)
    ancillary = round(sum(x['source_intersection_pct'] for x in overlays if x['geoid'] not in {'02063','02066'}), 6)
    parents = [{'id': x['id'], 'name': x['name'], 'level': x.get('level')} for x in row['full_parent_chain']]
    settlement = row['settlement_screen']
    result = {
      'version': 1,
      'subject': {'id': SUBJECT, 'name': row['name'], 'source_vintage': 2018,
        'source_identity': {'source_shape_id':source_feature['properties']['shapeID'],'source_name':source_feature['properties']['shapeName'],'source_tier':source_feature['properties']['shapeType'],'source_vintage':metadata['boundaryYear'],'source_provider':metadata['boundarySource'],'source_role':metadata['boundaryCanonical'],'license':metadata['boundaryLicense'],'pinned_source_sha256':hashlib.sha256(gb_raw).hexdigest(),'source_path_at_baseline':gb_path},
        'baseline_parent_chain': parents},
      'official_successor_event': {
        'source_census_page': 'https://www.census.gov/programs-surveys/acs/technical-documentation/table-and-geography-changes/2019/geography-changes.html',
        'quoted_event': phrase,
        'source_change_table': 'https://www2.census.gov/geo/docs/reference/bndrychange/st02_ak_gcn_2014_2020.txt',
        'predecessor': {'name':'Valdez-Cordova Census Area','geoid':'02261','vintage':2018},
        'event': 'split', 'effective_date':'2019-01-02',
        'successors': direct,
        'interpretation':'The Census Bureau directly records these two new Census Areas as formed from the split of former Valdez-Cordova Census Area. They are 2024 county-equivalent statistical geographies (TIGER CLASSFP H5); this is not a claim that either is a municipal government or a political-ownership ruling.'
      },
      '2024_tiger_identity_check': {'source_path':'data/regional-review/regional-review-93f8f3bee8e205be/sources/tigerline-2024-western-county-neighbors.geojson.gz', 'target_features':targets},
      'inherited_geometry_screen': {'baseline_assessment':'data/regional-review/regional-review-93f8f3bee8e205be/assessment.json',
        'method':'The original #486 source-vintage screen intersects the pinned 2018 geoBoundaries polygon with 2024 TIGER county-equivalent polygons in EPSG:3338. Values are a source-area screening ratio, not the Census transition record and not a boundary adjudication.',
        'source_overlap_pct_by_2024_geoid':{x['geoid']:x['source_intersection_pct'] for x in overlays},
        'ancillary_neighbor_candidates':[{'geoid':x['geoid'],'name':x['name'],'namelsad':x['namelsad'],'source_overlap_pct':x['source_intersection_pct']} for x in overlays if x['geoid'] not in {'02063','02066'}],
        'combined_overlap_pct_to_official_successor_pair':successor_share,
        'overlap_pct_to_other_2024_county_equivalents':ancillary,
        'interpretation':'The two officially named successor candidates cover 99.947342% of the 2018 source shape in this retained overlay screen; minor overlap to four other county-equivalents remains a vintage/edge lead, not proof of additional successor identity.'},
      'location_review_context': {'baseline_decision':row['decision'], 'baseline_decision_basis':row['decision_basis'],
        'settlement_screen': {'source':settlement['polygon_source'], '2024_place_polygon_intersections':settlement['intersecting_place_count'],
          'GNIS_populated_place_hits':settlement['gnis_populated_place_hit_count'],
          'named_examples_from_pinned_screen':['Chenega','Chisana','Chitina','Cordova','Copper Center','Glennallen','Valdez','Whittier'],
          'limitation':'These are inherited screening hits only; they do not certify current settlement completeness or assign political ownership.'},
        'physical_land_screen':row['physical_land_screen'],
        'unresolved_baseline_questions':row['unresolved']},
      'proposed_treatment': {'status':'evidence-backed crosswalk proposal',
        'record':'Preserve the 2018 geoBoundaries ID and geometry as a distinct historical source identity; add a versioned one-to-many crosswalk to Census GEOIDs 02063 and 02066 with effective date 2019-01-02 and citations to the direct Census change records.',
        'limits':['Do not rename the 2018 feature as either single successor.', 'Do not assert that successor polygons are exact, complete, disjoint replacements for the 2018 source shape; retained overlay differences remain visible.', 'Do not edit shared membership/geometry or transfer dated attributes; engineering decides if/when a versioned crosswalk is integrated.', 'The Census change record establishes statistical county-equivalent lineage. It does not determine sovereign ownership or local political control.']},
      'metrics': {'direct_successor_count':len(direct), 'source_overlap_pct_to_official_successor_pair':successor_share,
        'source_overlap_pct_to_other_2024_county_equivalents':ancillary},
      'source_checks': {'official_change_events':len(direct),'target_tiger_features':len(targets),'retained_parent_feature_found':feature is not None,
        'assessment_subject_count':sum(x['location_id']==SUBJECT for x in assessment['locations'])}
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'output':str(OUT),'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(), 'successor_count':len(direct),
      'successor_ids':[x['geoid'] for x in targets], 'successor_pair_overlap_pct':successor_share,
      'ancillary_overlap_pct':ancillary},indent=2))
if __name__ == '__main__': main()
